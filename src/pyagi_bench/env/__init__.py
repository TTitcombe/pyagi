import traceback
from typing import Any

from pyagi_bench.env.tools import ToolError, all_tools, validate_args
from pyagi_bench.env.world import World


class Environment:
    """
    One fresh world per trial. Every tool call is appended to `events`, the
    trial's shared timeline (the runner appends user/agent messages to it too).

    Failures come back to the agent as {"error": ...} rather than exceptions, and
    the event records *why* so tool-use mistakes can be measured:
        unknown_tool / invalid_args / tool_error   the agent's fault
        env_bug                                    ours: fix the environment
    """

    def __init__(self, data: dict, events: list[dict]):
        self.world = World(data)
        self.initial = self.world.snapshot()
        self.events = events
        self.tools = {t.name: t for t in all_tools()}

    def call(self, name: str, args: dict | None) -> Any:
        # Local models often send explicit nulls for optional params; treat them as omitted.
        args = {k: v for k, v in (args or {}).items() if v is not None}
        event: dict[str, Any] = {"type": "tool_call", "name": name, "args": args}
        spec = self.tools.get(name)

        if spec is None:
            event["error"] = "unknown_tool"
            result = {"error": f"Unknown tool '{name}'. Available tools: {sorted(self.tools)}"}
        elif message := validate_args(spec, args):
            event["error"] = "invalid_args"
            result = {"error": message}
        else:
            try:
                result = spec.handler(self.world, **args)
            except ToolError as e:
                event["error"] = "tool_error"
                result = {"error": str(e)}
            except Exception:
                event["error"] = "env_bug"
                event["traceback"] = traceback.format_exc()
                result = {"error": "Internal error in the tool"}

        event["result"] = result
        self.events.append(event)
        return result

    def preamble(self) -> str:
        user = self.world.user
        now = self.world.now
        return (
            f"You are acting on behalf of {user['name']} <{user['email']}>. "
            f"The current date and time is {now:%A} {now.day} {now:%B %Y, %H:%M} ({self.world.data['timezone']})."
        )
