"""
Shared access to the mock world's state, used by the service CLIs (cal, ...) and by check.py.

State lives in STATE_DIR as one JSON file per service, each a list of records with an "id"
(calendar.json, later mail.json, ...), plus world.json for the frozen clock and the user.
SEED_DIR holds an untouched copy of the starting state so checkers can diff against it.
"""
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

STATE_DIR = Path(os.environ.get("WORLD_STATE_DIR", "/var/lib/world"))
SEED_DIR = Path(os.environ.get("WORLD_SEED_DIR", "/opt/world/seed"))


def load(name: str, root: Path = STATE_DIR):
    return json.loads((root / f"{name}.json").read_text())


def save(name: str, data) -> None:
    path = STATE_DIR / f"{name}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def now() -> datetime:
    return datetime.fromisoformat(load("world")["now"])


def parse_time(value: str, *, end_of_day: bool = False) -> datetime:
    """YYYY-MM-DD or YYYY-MM-DDTHH:MM. A bare date as a range end means the whole day."""
    try:
        if len(value) == 10:
            day = datetime.combine(date.fromisoformat(value), datetime.min.time())
            return day + timedelta(days=1) if end_of_day else day
        return datetime.fromisoformat(value).replace(second=0, microsecond=0)
    except ValueError:
        fail(f"Could not parse time '{value}'. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM.")


def fmt(dt: datetime) -> str:
    return dt.isoformat(timespec="minutes")


def next_id(records: list[dict], prefix: str) -> str:
    """Deterministic ids for new records (ev-new-1, ev-new-2, ...) so runs are reproducible."""
    taken = {r["id"] for r in records}
    n = 1
    while f"{prefix}-new-{n}" in taken:
        n += 1
    return f"{prefix}-new-{n}"


def matches_words(query: str, *fields) -> bool:
    """Every word of the query appears in at least one field (case-insensitive)."""
    text = " ".join(" ".join(f) if isinstance(f, list) else str(f or "") for f in fields).lower()
    return all(word in text for word in query.lower().split())


def output(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def fail(message: str):
    """Errors go to stderr with a non-zero exit; the agent sees the message as the tool result."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)
