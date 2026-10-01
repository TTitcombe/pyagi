"""
Sanity baselines for the benchmark itself, not agents to compare against:
    oracle  replays each task's reference solution; every task should pass,
            proving it is solvable and its checks are right
    noop    does nothing; every task should fail, otherwise a check is passing vacuously
"""
from pyagi_bench.agents import AgentAdapter, TaskContext


class OracleError(RuntimeError):
    pass


class OracleAdapter(AgentAdapter):
    """
    Oracle steps are a flat list: `{call: tool, args: {...}}` runs a tool, and
    `{say: text}` ends the agent's turn with that message.
    """
    needs_reference = True

    def start(self, ctx: TaskContext) -> None:
        if not ctx.reference:
            raise OracleError("Task has no oracle solution")
        self.ctx = ctx
        self.steps = list(ctx.reference)

    def respond(self, message: str) -> str:
        while self.steps:
            step = self.steps.pop(0)
            if "say" in step:
                return step["say"]
            result = self.ctx.call_tool(step["call"], step.get("args", {}))
            if isinstance(result, dict) and "error" in result:
                raise OracleError(f"Oracle step {step} failed: {result['error']}")
        return "Done."


class NoopAdapter(AgentAdapter):
    def start(self, ctx: TaskContext) -> None:
        pass

    def respond(self, message: str) -> str:
        return "Okay."
