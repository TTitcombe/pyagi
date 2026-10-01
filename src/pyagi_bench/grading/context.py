from dataclasses import dataclass, field
from functools import cached_property

from pyagi_bench.env.world import RECORD_KEYS, diff
from pyagi_bench.tasks import Task


@dataclass
class CheckResult:
    check: str
    status: str  # pass | fail | pending | error
    detail: str = ""
    grader: str = "auto"  # auto | llm:<model> | human
    group: str | None = None
    index: int = -1

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class GradeContext:
    """Everything a check may look at. Built from a saved trajectory, so runs can be re-graded."""
    task: Task
    initial: dict
    final: dict
    events: list[dict]
    judge: object | None = field(default=None)

    @cached_property
    def diff(self) -> dict:
        return diff(self.initial, self.final)

    def records(self, collection: str, scope: str = "final") -> list[dict]:
        final = self.final["collections"].get(collection, {})
        initial = self.initial["collections"].get(collection, {})
        changes = self.diff.get(collection, {})
        if scope == "final":
            return list(final.values())
        if scope == "added":
            return [final[k] for k in changes.get("add", [])]
        if scope == "updated":
            return [final[k] for k in changes.get("update", {})]
        if scope == "deleted":
            return [initial[k] for k in changes.get("delete", [])]
        raise ValueError(f"Unknown scope '{scope}'")

    def record_key(self, collection: str, record: dict) -> str:
        return record[RECORD_KEYS.get(collection, "id")]

    def agent_messages(self, session: int | None = None) -> list[str]:
        return [
            e["content"] for e in self.events
            if e["type"] == "agent" and (session is None or e["session"] == session)
        ]

    def tool_calls(self, name: str | None = None, *, ok_only: bool = True) -> list[dict]:
        return [
            e for e in self.events
            if e["type"] == "tool_call" and (name is None or e["name"] == name) and not (ok_only and "error" in e)
        ]

    @property
    def last_session(self) -> int:
        return len(self.task.sessions) - 1
