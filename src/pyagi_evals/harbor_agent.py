"""
Harbor adapter for BasicLoopAgent.

Runs as a Harbor "external" agent: the agent loop runs here on the host (so it
can reach Ollama on localhost), and its tools act on the task container through
`environment.exec`.

    uv run harbor run -p evals/tasks -a pyagi_evals.harbor_agent:PyagiAgent -m qwen3:14b -n 1

pyagi is synchronous and Harbor is async, so the agent runs in a worker thread
and each tool call hops back onto Harbor's event loop to run its command.
"""
import asyncio
import base64
import contextlib
import json
import os
import shlex
from typing import Callable

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment, ExecResult
from harbor.models.agent.context import AgentContext

from pyagi.agent.basic import BasicLoopAgent
from pyagi.models.ollama import OllamaDirect
from pyagi.tools.base import Toolset
from pyagi.tools.manager import ToolManager

# Model calls per task before giving up (BasicLoopAgent's own backstop is 5).
MAX_STEPS = 6

Shell = Callable[[str], ExecResult]


class ContainerFileToolset(Toolset):
    """pyagi's file tools, operating inside the task container instead of on the host."""

    def __init__(self, shell: Shell):
        self.shell = shell

    def edit_file(self, filepath: str, content: str) -> str:
        # base64 so any content survives the shell untouched.
        encoded = base64.b64encode(content.encode()).decode()
        result = self.shell(f"printf %s {encoded} | base64 -d >> {shlex.quote(filepath)}")
        return f"{filepath} edited." if result.return_code == 0 else f"Error: {result.stderr}"

    def read_file(self, filepath: str) -> str:
        result = self.shell(f"cat -- {shlex.quote(filepath)}")
        return (result.stdout or "") if result.return_code == 0 else f"Error: {result.stderr}"

    def list_files(self) -> str:
        result = self.shell("echo \"CWD: $(pwd)\"; ls -p")
        return result.stdout or ""

    @property
    def tools(self):
        return [
            {
                "tool_name": "edit_file",
                "description": "Edit part of a file by appending text to the end. Creates the file if it does not exist.",
                "parameters": {"filepath": "str", "content": "str"},
            },
            {
                "tool_name": "read_file",
                "description": "Read the content of the given filepath.",
                "parameters": {"filepath": "str"},
            },
            {
                "tool_name": "list_files",
                "description": "List files in the current working directory, and the cwd itself.",
                "parameters": {},
            },
        ]

    @property
    def tool_mapping(self):
        return {"edit_file": self.edit_file, "read_file": self.read_file, "list_files": self.list_files}

    def invoke(self, tool_name: str, params: dict):
        # Overrides Toolset.invoke, which passes params positionally and raises on unknown names.
        fn = self.tool_mapping.get(tool_name)
        if fn is None:
            return False, None
        try:
            return True, fn(**params)
        except TypeError as e:
            return True, f"Error: bad parameters for {tool_name}: {e}"


def run_task(agent: BasicLoopAgent, instruction: str) -> str:
    """BasicLoopAgent.run_iteration minus input(): one user turn, looping while the model calls tools."""
    context = agent.context_manager
    context.add({"role": "user", "content": instruction})
    output = ""
    for _ in range(MAX_STEPS):
        output, new_messages, call_model = agent.iteration()
        context.add(new_messages)
        if not call_model:
            break
    return output


class PyagiAgent(BaseAgent):
    @staticmethod
    def name() -> str:
        return "pyagi"

    def version(self) -> str | None:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        loop = asyncio.get_running_loop()

        def shell(command: str) -> ExecResult:
            return asyncio.run_coroutine_threadsafe(environment.exec(command), loop).result()

        tools = ToolManager()
        tools.register(ContainerFileToolset(shell))
        if self._parsed_model_name is None:
            raise ValueError("pass an Ollama model with -m, e.g. -m qwen3:14b")
        # `-m qwen3:14b` and `-m ollama/qwen3:14b` both work.
        model_name = self._parsed_model_name
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        agent = BasicLoopAgent(OllamaDirect(model_name, ollama_url=f"{ollama_url}/api/chat"), tools)

        def run_logged() -> str:
            # OllamaDirect prints every request; keep that in the trial's log rather than Harbor's console.
            with (self.logs_dir / "agent.log").open("w") as log, contextlib.redirect_stdout(log):
                return run_task(agent, instruction)

        try:
            response = await asyncio.to_thread(run_logged)
            # logs_dir is mounted at /logs/agent/ in the container, so verifiers can grade the final reply.
            (self.logs_dir / "response.txt").write_text(response)
        finally:
            messages = agent.context_manager.messages
            (self.logs_dir / "messages.json").write_text(json.dumps(messages, indent=2))
            context.metadata = {"messages": len(messages)}
