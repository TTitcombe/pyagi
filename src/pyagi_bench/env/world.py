"""
The world is everything the agent can read or change. It is held as plain
JSON-compatible data so it can be snapshotted, diffed and saved with no custom
serialisation.

Layout of `data`:
    now, timezone, user        frozen clock + who the agent acts for
    collections                {collection_name: {record_id: record}}
    counters                   per-prefix counters for deterministic new ids
"""
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from pyagi_bench.yamlio import load_yaml

WORLD_FILE = "world.yaml"


class World:
    def __init__(self, data: dict):
        self.data = data

    @property
    def now(self) -> datetime:
        return datetime.fromisoformat(self.data["now"])

    @property
    def user(self) -> dict:
        return self.data["user"]

    def collection(self, name: str) -> dict[str, dict]:
        return self.data["collections"].setdefault(name, {})

    def new_id(self, prefix: str) -> str:
        counters = self.data["counters"]
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}-new-{counters[prefix]}"

    def snapshot(self) -> dict:
        return deepcopy(self.data)


def load_world(world_dir: Path) -> dict:
    """world.yaml holds the clock and user; every other <name>.yaml is a list of records for collection <name>."""
    meta = load_yaml(world_dir / WORLD_FILE)
    collections: dict[str, dict] = {}
    for path in sorted(world_dir.glob("*.yaml")):
        if path.name != WORLD_FILE:
            upsert(collections, path.stem, load_yaml(path) or [])
    return {**meta, "collections": collections, "counters": {}}


def upsert(collections: dict, name: str, records: list[dict]) -> None:
    target = collections.setdefault(name, {})
    for record in records:
        target[record["id"]] = record


def diff(before: dict, after: dict) -> dict[str, dict]:
    """Per collection: ids added, deleted, and updated (with the changed fields)."""
    changes: dict[str, dict] = {}
    for name in sorted(set(before["collections"]) | set(after["collections"])):
        old = before["collections"].get(name, {})
        new = after["collections"].get(name, {})
        added = sorted(set(new) - set(old))
        deleted = sorted(set(old) - set(new))
        updated = {
            key: sorted(f for f in set(old[key]) | set(new[key]) if old[key].get(f) != new[key].get(f))
            for key in sorted(set(old) & set(new))
            if old[key] != new[key]
        }
        if added or deleted or updated:
            changes[name] = {"add": added, "delete": deleted, "update": updated}
    return changes
