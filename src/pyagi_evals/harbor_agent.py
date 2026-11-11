"""
Harbor adapter for BasicLoopAgent.

Runs as a Harbor "external" agent: the agent loop runs here on the host (so it
can reach Ollama on localhost). The agent uses the same toolsets as in real use:
the task container's files and world state are copied to a temp dir on the host,
the toolsets work on that copy, and it is copied back before the verifier runs.

    uv run harbor run -p evals/tasks -a pyagi_evals.harbor_agent:PyagiAgent -m qwen3:14b -n 1

pyagi is synchronous and Harbor is async, so the agent runs in a worker thread.
"""
import asyncio
import contextlib
import json
import os
import tempfile
import threading
from pathlib import Path

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from pyagi.agent.basic import BasicLoopAgent
from pyagi.models.ollama import OllamaDirect
from pyagi.tools.calendar import MockCalendar
from pyagi.tools.email import MockEmail
from pyagi.tools.file_io import FileToolset
from pyagi.tools.manager import ToolManager

# Model calls per task before giving up (BasicLoopAgent's own backstop is 5).
MAX_STEPS = 6

# Container dirs the tools work on (see evals/base/Dockerfile): the user's files, and the mock services' state.
APP_DIR = "/app"
WORLD_DIR = "/var/lib/world"


def run_task(agent: BasicLoopAgent, instruction: str, stop: threading.Event) -> str:
    """BasicLoopAgent.run_iteration minus input(): one user turn, looping while the model calls tools."""
    context = agent.context_manager
    context.add({"role": "user", "content": instruction})
    output = ""
    for _ in range(MAX_STEPS):
        if stop.is_set():
            break
        output, new_messages, call_model = agent.iteration()
        context.add(new_messages)
        if not call_model:
            break
    return output


def read_records(world_dir: Path) -> dict[str, list[dict]]:
    """Each service's records (calendar.json, mail.json, ...), skipping world.json, which isn't a list."""
    services = {path.stem: json.loads(path.read_text()) for path in world_dir.glob("*.json")}
    return {name: records for name, records in services.items() if isinstance(records, list)}


def world_changes(before: dict[str, list[dict]], world_dir: Path) -> dict:
    """What the agent changed in each service, by record id, with full records so a failed check can be read directly."""
    changes = {}
    for name, records in before.items():
        try:
            after = json.loads((world_dir / f"{name}.json").read_text())
        except json.JSONDecodeError as e:
            changes[name] = f"invalid JSON after the run: {e}"
            continue
        old, new = {r["id"]: r for r in records}, {r["id"]: r for r in after}
        diff = {
            "add": [new[i] for i in new.keys() - old.keys()],
            "update": [{"before": old[i], "after": new[i]} for i in old.keys() & new.keys() if old[i] != new[i]],
            "delete": [old[i] for i in old.keys() - new.keys()],
        }
        if any(diff.values()):
            changes[name] = diff
    return changes


class PyagiAgent(BaseAgent):
    @staticmethod
    def name() -> str:
        return "pyagi"

    def version(self) -> str | None:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        if self._parsed_model_name is None:
            raise ValueError("pass an Ollama model with -m, e.g. -m qwen3:14b")

        with tempfile.TemporaryDirectory(prefix="pyagi-") as tmp:
            app_dir, world_dir = Path(tmp) / "app", Path(tmp) / "world"
            await environment.download_dir(APP_DIR, app_dir)
            await environment.download_dir(WORLD_DIR, world_dir)
            before = read_records(world_dir)
            try:
                await self._run_agent(instruction, app_dir, world_dir, context)
            finally:
                # Checkers diff the container's state against the seed, so the agent's changes go back in.
                await environment.upload_dir(app_dir, APP_DIR)
                await environment.upload_dir(world_dir, WORLD_DIR)
                changes = world_changes(before, world_dir)
                (self.logs_dir / "world_changes.json").write_text(json.dumps(changes, indent=2))

    async def _run_agent(self, instruction: str, app_dir: Path, world_dir: Path, context: AgentContext) -> None:
        # The world's clock is frozen, so the agent needs to be told "now" to resolve "tomorrow" etc.
        world = json.loads((world_dir / "world.json").read_text())
        user = world["user"]

        tools = ToolManager()
        tools.register(FileToolset(str(app_dir)))
        tools.register(MockCalendar(world_dir / "calendar.json", user["email"], False))
        tools.register(MockEmail(world_dir / "mail.json", user["email"]))

        system = (
            "You are an agent helping with personal tasks.\n\n"
            f"The current time is {world['now']} ({world['timezone']}). "
            f"You are acting for {user['name']} ({user['email']})."
        )
        # `-m qwen3:14b` and `-m ollama/qwen3:14b` both work.
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        agent = BasicLoopAgent(OllamaDirect(self._parsed_model_name, ollama_url=f"{ollama_url}/api/chat"), tools, system)

        stop = threading.Event()

        def run_logged() -> str:
            # OllamaDirect prints every request; keep that in the trial's log rather than Harbor's console.
            with (self.logs_dir / "agent.log").open("w") as log, contextlib.redirect_stdout(log):
                return run_task(agent, instruction, stop)

        try:
            response = await asyncio.to_thread(run_logged)
            # logs_dir is mounted at /logs/agent/ in the container, so verifiers can grade the final reply.
            (self.logs_dir / "response.txt").write_text(response)
        finally:
            # On timeout Harbor cancels this coroutine, but the worker thread can't be cancelled. Stop it after
            # its current model call so it doesn't keep competing with later trials for Ollama.
            stop.set()
            messages = agent.context_manager.messages
            (self.logs_dir / "messages.json").write_text(json.dumps(messages, indent=2))
            context.metadata = {"messages": len(messages)}
