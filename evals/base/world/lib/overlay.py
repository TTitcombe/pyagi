"""
Apply an overlay to the world at image build time (not available to the agent).

    python3 /opt/world/lib/overlay.py DIR

DIR holds <service>.json files, each a list of records. A record replaces the one with the same id, or is added.
Applied to both the live state and the seed copy, so checkers diff against the overlay's starting point.
"""
import json
import sys
from pathlib import Path

from world import SEED_DIR, STATE_DIR


def apply(overlay_dir: Path) -> None:
    for patch in sorted(overlay_dir.glob("*.json")):
        records = json.loads(patch.read_text())
        for root in (STATE_DIR, SEED_DIR):
            path = root / patch.name
            existing = json.loads(path.read_text()) if path.exists() else []
            by_id = {r["id"]: r for r in existing}
            by_id.update({r["id"]: r for r in records})
            merged = sorted(by_id.values(), key=lambda r: r.get("start") or r.get("date") or r["id"])
            path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
        print(f"overlay: {patch.name}: {len(records)} record(s)")


if __name__ == "__main__":
    apply(Path(sys.argv[1]))
