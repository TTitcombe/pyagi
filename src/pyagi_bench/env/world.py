"""
The world is everything the agent can read or change: mailbox, calendar,
contacts, documents, shop. It is held as plain JSON-compatible data so it can be
snapshotted, diffed and written to disk with no custom serialisation.

Layout of `data`:
    now, timezone, user        frozen clock + who the agent acts for
    collections                {collection_name: {record_key: record}}
    counters                   per-prefix counters for deterministic new ids
"""
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from pyagi_bench.yamlio import load_yaml

# Collections keyed by something other than `id`.
RECORD_KEYS = {"documents": "path"}
WORLD_FILE = "world.yaml"
DOCUMENTS_DIR = "documents"


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
        counters = self.data.setdefault("counters", {})
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}-new-{counters[prefix]}"

    def snapshot(self) -> dict:
        return deepcopy(self.data)


def load_world(worlds_dir: Path, name: str) -> dict:
    root = worlds_dir / name
    meta = load_yaml(root / WORLD_FILE)
    collections: dict[str, dict[str, dict]] = {}

    for path in sorted(root.glob("*.yaml")):
        if path.name == WORLD_FILE:
            continue
        collections[path.stem] = {}
        upsert(collections, path.stem, load_yaml(path) or [], source=str(path))

    docs_root = root / DOCUMENTS_DIR
    if docs_root.is_dir():
        collections["documents"] = {
            str(p.relative_to(docs_root)): {"path": str(p.relative_to(docs_root)), "content": p.read_text()}
            for p in sorted(docs_root.rglob("*"))
            if p.is_file()
        }

    return {
        "now": meta["now"],
        "timezone": meta["timezone"],
        "user": meta["user"],
        "collections": collections,
        "counters": {},
    }


def upsert(collections: dict, name: str, records: list[dict], source: str = "setup") -> None:
    key = RECORD_KEYS.get(name, "id")
    target = collections.setdefault(name, {})
    for record in records:
        if key not in record:
            raise ValueError(f"{source}: record in '{name}' is missing '{key}': {record}")
        target[record[key]] = record


def diff(before: dict, after: dict) -> dict[str, dict]:
    """Per collection: ids added, deleted, and updated (with the changed fields)."""
    changes: dict[str, dict] = {}
    names = set(before["collections"]) | set(after["collections"])

    for name in sorted(names):
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
