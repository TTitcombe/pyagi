"""
Tasks are YAML files under `benchmark/tasks/<category>/<name>.yaml`. The task id
is the path without the extension (e.g. `email/dentist-time`), so ids and
categories can never drift from the file layout. See benchmark/README.md for the
full schema.
"""
import hashlib
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from pyagi_bench.env.world import upsert
from pyagi_bench.yamlio import load_yaml

DIFFICULTIES = ("easy", "medium", "hard")
SPLITS = ("dev", "test")
TASK_KEYS = {
    "description", "difficulty", "split", "tags", "world", "now", "setup",
    "prompt", "user", "sessions", "side_effects", "checks", "oracle",
}


class TaskError(ValueError):
    pass


@dataclass
class Session:
    prompt: str
    # Scripted replies, consumed in order each time the agent hands back to the user.
    replies: list[str] = field(default_factory=list)
    # LLM-simulated user (persona/goal/knowledge) instead of scripted replies.
    simulator: dict | None = None
    max_turns: int = 1


@dataclass
class Task:
    id: str
    category: str
    difficulty: str
    split: str
    tags: list[str]
    description: str
    world: str
    now: str | None
    setup: dict[str, list[dict]]
    sessions: list[Session]
    side_effects: dict[str, int | str] | str
    checks: list[dict[str, Any]]
    oracle: list[dict] | None
    path: Path

    def build_world(self, worlds_dir: Path) -> dict:
        from pyagi_bench.env.world import load_world

        data = load_world(worlds_dir, self.world)
        if self.now:
            data["now"] = self.now
        for collection, records in self.setup.items():
            upsert(data["collections"], collection, records, source=str(self.path))
        return data


def _session(raw: dict, source: Path) -> Session:
    if not raw.get("prompt"):
        raise TaskError(f"{source}: every session needs a prompt")
    user = raw.get("user") or {}
    replies = list(user.get("replies", []))
    simulator = user.get("simulator")
    default_turns = 10 if simulator else len(replies) + 1
    return Session(raw["prompt"], replies, simulator, user.get("max_turns", default_turns))


def parse_task(raw: dict, path: Path, tasks_dir: Path) -> Task:
    task_id = str(path.relative_to(tasks_dir).with_suffix(""))
    unknown = set(raw) - TASK_KEYS
    if unknown:
        raise TaskError(f"{task_id}: unknown keys {sorted(unknown)}")

    raw_sessions = raw["sessions"] if "sessions" in raw else [{"prompt": raw.get("prompt"), "user": raw.get("user")}]
    sessions = [_session(s, path) for s in raw_sessions]

    difficulty = raw.get("difficulty", "medium")
    split = raw.get("split", "dev")
    if difficulty not in DIFFICULTIES:
        raise TaskError(f"{task_id}: difficulty must be one of {DIFFICULTIES}")
    if split not in SPLITS:
        raise TaskError(f"{task_id}: split must be one of {SPLITS}")

    checks = raw.get("checks") or []
    for check in checks:
        if not isinstance(check, dict) or len(check) != 1:
            raise TaskError(f"{task_id}: each check must be a single-key mapping, got {check!r}")
    if not checks:
        raise TaskError(f"{task_id}: a task needs at least one check")

    return Task(
        id=task_id,
        category=task_id.split("/")[0],
        difficulty=difficulty,
        split=split,
        tags=list(raw.get("tags", [])),
        description=raw.get("description", "").strip(),
        world=raw.get("world", "base"),
        now=raw.get("now"),
        setup=raw.get("setup") or {},
        sessions=sessions,
        side_effects=raw.get("side_effects") or {},
        checks=checks,
        oracle=raw.get("oracle"),
        path=path,
    )


def load_tasks(tasks_dir: Path) -> list[Task]:
    tasks = [parse_task(load_yaml(p), p, tasks_dir) for p in sorted(tasks_dir.rglob("*.yaml"))]
    _validate_checks(tasks)
    return tasks


def _validate_checks(tasks: list[Task]) -> None:
    from pyagi_bench.grading.checks import CHECKS

    for task in tasks:
        for check in task.checks:
            (name,) = check
            if name not in CHECKS:
                raise TaskError(f"{task.id}: unknown check '{name}'. Known: {sorted(CHECKS)}")


def select(
    tasks: list[Task],
    *,
    ids: list[str] | None = None,
    categories: list[str] | None = None,
    tags: list[str] | None = None,
    split: str | None = None,
    difficulty: str | None = None,
) -> list[Task]:
    """Filters combine with AND; values within one filter combine with OR. Ids accept globs."""
    return [
        t for t in tasks
        if (not ids or any(fnmatch(t.id, pattern) for pattern in ids))
        and (not categories or t.category in categories)
        and (not tags or set(tags) & set(t.tags))
        and (split is None or t.split == split)
        and (difficulty is None or t.difficulty == difficulty)
    ]


def benchmark_version(benchmark_dir: Path) -> str:
    """Content hash of every task and world file: results are only comparable at the same version."""
    digest = hashlib.sha256()
    for path in sorted(p for p in benchmark_dir.rglob("*") if p.is_file() and p.name != "README.md"):
        digest.update(str(path.relative_to(benchmark_dir)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]
