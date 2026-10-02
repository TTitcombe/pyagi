"""
Adapter for pyagi's BasicLoopAgent.

BasicLoopAgent.run_iteration reads from input(), so this drives the agent one
level down (context_manager + iteration) with the same loop, minus the prompt.
If the agent grows a `respond(message) -> str` method, this can shrink to a call.
"""
import os

from pyagi.agent.basic import BasicLoopAgent
from pyagi.models.ollama import OllamaDirect
from pyagi.tools.base import Toolset
from pyagi.tools.manager import ToolManager

from pyagi_bench.agents import AgentAdapter, TaskContext

DEFAULT_SYSTEM = "You are an agent helping with personal tasks"


class EnvToolset(Toolset):
    """Exposes the mock world's tools through pyagi's Toolset interface."""

    def __init__(self, ctx: TaskContext):
        self.ctx = ctx
        self.names = {t.name for t in ctx.tools}

    @property
    def tools(self):
        return [
            {
                "tool_name": t.name,
                "description": t.description,
                "parameters": {
                    name: f"{p.type}{'' if p.required else ' (optional)'}: {p.description}"
                    for name, p in t.params.items()
                },
            }
            for t in self.ctx.tools
        ]

    @property
    def tool_mapping(self):
        return {name: lambda n=name, **kw: self.ctx.call_tool(n, kw) for name in self.names}

    def invoke(self, tool_name: str, params: dict):
        if tool_name not in self.names:
            return False, None
        return True, self.ctx.call_tool(tool_name, params)


class BasicLoopAdapter(AgentAdapter):
    def start(self, ctx: TaskContext) -> None:
        url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        model = OllamaDirect(self.config.model["name"], ollama_url=f"{url}/api/chat")
        self.max_steps = self.config.agent.get("max_steps", 6)

        tools = ToolManager()
        tools.register(EnvToolset(ctx))
        system = f"{self.config.agent.get('system_prompt', DEFAULT_SYSTEM)}\n\n{ctx.preamble}"
        self.agent = BasicLoopAgent(model, tools, system=system)

    def respond(self, message: str) -> str:
        context = self.agent.context_manager
        context.add({"role": "user", "content": message})
        output = ""
        for _ in range(self.max_steps):
            output, new_messages, call_model = self.agent.iteration()
            context.add(new_messages)
            if not call_model:
                break
        return output

    def transcript(self) -> list[dict]:
        return list(self.agent.context_manager.messages)
