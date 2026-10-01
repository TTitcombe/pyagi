"""
The seam between the harness and an agent. To evaluate a new agent design,
write an `AgentAdapter` and register it in `AGENTS`; select it with `agent.type`
in a run config.

Adapters are imported lazily so a broken agent can't stop `bench list` or
`bench validate` from working.
"""
import importlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable

from pyagi_bench.config import RunConfig
from pyagi_bench.env.tools import ToolSpec

AGENTS = {
    "basic_loop": "pyagi_bench.agents.basic_loop:BasicLoopAdapter",
    "oracle": "pyagi_bench.agents.baselines:OracleAdapter",
    "noop": "pyagi_bench.agents.baselines:NoopAdapter",
}


@dataclass
class TaskContext:
    preamble: str                             # who the agent acts for + the frozen current time
    tools: list[ToolSpec]                     # name, description, JSON schema; present them however you like
    call_tool: Callable[[str, dict], Any]     # the only way to touch the world
    reference: list[dict] | None = None       # oracle steps; only given to adapters with needs_reference


class AgentAdapter(ABC):
    """
    One instance per trial, so nothing leaks between trials. The harness drives
    the conversation: `respond` gets a user message and must return the message
    shown to the user once the agent hands control back.
    """
    needs_reference = False

    def __init__(self, config: RunConfig):
        self.config = config

    @abstractmethod
    def start(self, ctx: TaskContext) -> None: ...

    @abstractmethod
    def respond(self, message: str) -> str: ...

    def new_session(self) -> None:
        """A later conversation with the same user (multi-session tasks). Memory should survive this; context shouldn't."""

    def transcript(self) -> list[dict]:
        """Raw model-facing messages, saved for debugging."""
        return []

    def usage(self) -> dict:
        """Cost/latency counters, e.g. model_calls, model_seconds, input_tokens, output_tokens."""
        return {}


def make_agent(config: RunConfig) -> AgentAdapter:
    kind = config.agent["type"]
    if kind not in AGENTS:
        raise ValueError(f"Unknown agent type '{kind}'. Known: {sorted(AGENTS)}")
    module, _, cls = AGENTS[kind].partition(":")
    return getattr(importlib.import_module(module), cls)(config)
