from dataclasses import dataclass
from functools import cached_property

from pyagi_bench.env.world import diff
from pyagi_bench.tasks import Task


@dataclass
class CheckResult:
    check: str
    status: str  # pass | fail | pending (needs a human) | error (the check itself crashed)
    detail: str = ""
    group: str | None = None
    index: int = -1

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class GradeContext:
    """Everything a check may look at: the world before and after, and the trial's timeline."""
    task: Task
    initial: dict
    final: dict
    events: list[dict]

    @cached_property
    def diff(self) -> dict:
        return diff(self.initial, self.final)

    def records(self, collection: str, scope: str = "final") -> list[dict]:
        """scope: final (whole collection after the trial) or added (records the agent created)."""
        final = self.final["collections"].get(collection, {})
        if scope == "final":
            return list(final.values())
        if scope == "added":
            return [final[k] for k in self.diff.get(collection, {}).get("add", [])]
        raise ValueError(f"Unknown scope '{scope}'")

    def agent_messages(self) -> list[str]:
        return [e["content"] for e in self.events if e["type"] == "agent"]
