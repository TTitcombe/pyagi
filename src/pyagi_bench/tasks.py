"""
Tasks are YAML files under `benchmark/tasks/<category>/<name>.yaml`. The task id
is the path without the extension (e.g. `email/reply-landlord`), so ids and
categories can't drift from the file layout. See benchmark/README.md for the schema.
"""
import hashlib
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from pyagi_bench.env.world import load_world, upsert
from pyagi_bench.yamlio import load_yaml

SPLITS = ("dev", "test")
TASK_KEYS = {"description", "split", "setup", "prompt", "replies", "side_effects", "checks", "oracle"}


class TaskError(ValueError):
    pass


@dataclass
class Task:
    id: str
    category: str
    split: str
    description: str
    prompt: str
    replies: list[str]                 # scripted user replies, one per time the agent hands back
    setup: dict[str, list[dict]]       # extra/replacement world records for this task only
    side_effects: dict[str, int | str] | str
    checks: list[dict]
    oracle: list[dict] | None
    path: Path

    @property
    def max_turns(self) -> int:
        return len(self.replies) + 1

    def build_world(self, world_dir: Path) -> dict:
        data = load_world(world_dir)
        for collection, records in self.setup.items():
            upsert(data["collections"], collection, records)
        return data


def parse_task(raw: dict, path: Path, tasks_dir: Path) -> Task:
    task_id = str(path.relative_to(tasks_dir).with_suffix(""))
    if unknown := set(raw) - TASK_KEYS:
        raise TaskError(f"{task_id}: unknown keys {sorted(unknown)}")
    if not raw.get("prompt"):
        raise TaskError(f"{task_id}: missing prompt")
    if raw.get("split", "dev") not in SPLITS:
        raise TaskError(f"{task_id}: split must be one of {SPLITS}")
    checks = raw.get("checks") or []
    if not checks or not all(isinstance(c, dict) and len(c) == 1 for c in checks):
        raise TaskError(f"{task_id}: checks must be a non-empty list of single-key mappings")

    return Task(
        id=task_id,
        category=task_id.split("/")[0],
        split=raw.get("split", "dev"),
        description=raw.get("description", "").strip(),
        prompt=raw["prompt"],
        replies=list(raw.get("replies", [])),
        setup=raw.get("setup") or {},
        side_effects=raw.get("side_effects") or {},
        checks=checks,
        oracle=raw.get("oracle"),
        path=path,
    )


def load_tasks(tasks_dir: Path) -> list[Task]:
    from pyagi_bench.grading.checks import CHECKS

    tasks = [parse_task(load_yaml(p), p, tasks_dir) for p in sorted(tasks_dir.rglob("*.yaml"))]
    for task in tasks:
        for check in task.checks:
            if (name := next(iter(check))) not in CHECKS:
                raise TaskError(f"{task.id}: unknown check '{name}'. Known: {sorted(CHECKS)}")
    return tasks


def select(tasks: list[Task], ids: list[str] | None = None, split: str | None = None) -> list[Task]:
    """Ids accept globs, e.g. 'email/*'."""
    return [
        t for t in tasks
        if (not ids or any(fnmatch(t.id, pattern) for pattern in ids))
        and (split is None or t.split == split)
    ]


def benchmark_version(benchmark_dir: Path) -> str:
    """Content hash of every task and world file: results are only comparable at the same version."""
    digest = hashlib.sha256()
    for path in sorted(p for p in benchmark_dir.rglob("*.yaml")):
        digest.update(str(path.relative_to(benchmark_dir)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]
