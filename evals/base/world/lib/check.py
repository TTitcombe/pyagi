"""
Checker library for task verifiers. Compares the world's seed state with its final state.

    from check import *

    event_exists(title_contains="Priya", start="2026-10-06T13:00", end="2026-10-06T14:00")
    only_changed({"calendar.update": 1})
    finish()

For checks the library doesn't have, use the building blocks (new_events, sent_emails,
clashes, mentions_date, mentions_time, ...) and record the result with expect(name, passed, detail).

Each check records a pass/fail with a reason. finish() prints them, writes them to
/logs/verifier/checks.json, and writes 1 (all passed) or 0 to /logs/verifier/reward.txt.
"""
import json
from datetime import datetime
from pathlib import Path

from world import SEED_DIR, STATE_DIR, load

VERIFIER_DIR = Path("/logs/verifier")
REPLY_PATH = Path("/logs/agent/response.txt")

_results: list[dict] = []


def expect(name: str, passed: bool, detail: str = "") -> bool:
    """Record a custom check."""
    _results.append({"check": name, "passed": passed, "detail": detail})
    return passed


def _collections(root: Path) -> dict[str, dict[str, dict]]:
    """Every service's records keyed by id, e.g. {"calendar": {"ev-lunch": {...}}}."""
    return {
        path.stem: {record["id"]: record for record in json.loads(path.read_text())}
        for path in sorted(root.glob("*.json"))
        if path.stem != "world"
    }


def changes() -> dict[str, dict[str, list[str]]]:
    """What the agent changed: {"calendar": {"add": [ids], "update": [ids], "delete": [ids]}}."""
    seed, final = _collections(SEED_DIR), _collections(STATE_DIR)
    out = {}
    for name in sorted(set(seed) | set(final)):
        old, new = seed.get(name, {}), final.get(name, {})
        diff = {
            "add": sorted(set(new) - set(old)),
            "update": sorted(k for k in set(old) & set(new) if old[k] != new[k]),
            "delete": sorted(set(old) - set(new)),
        }
        if any(diff.values()):
            out[name] = diff
    return out


# --- Calendar ----------------------------------------------------------------

def _same_time(a: str, b: str) -> bool:
    return datetime.fromisoformat(a) == datetime.fromisoformat(b)


def _event_matches(event: dict, title_contains=None, start=None, end=None, attendees_include=None, location_contains=None) -> bool:
    attendees = [a.lower() for a in event.get("attendees", [])]
    return (
        (title_contains is None or title_contains.lower() in event["title"].lower())
        and (start is None or _same_time(event["start"], start))
        and (end is None or _same_time(event["end"], end))
        and (attendees_include is None or all(a.lower() in attendees for a in attendees_include))
        and (location_contains is None or location_contains.lower() in event.get("location", "").lower())
    )


def _matching_events(new_only: bool, **criteria) -> list[dict]:
    events = load("calendar")
    if new_only:
        added = set(changes().get("calendar", {}).get("add", []))
        events = [e for e in events if e["id"] in added]
    return [e for e in events if _event_matches(e, **criteria)]


def event_exists(*, count: int | None = None, new_only: bool = False, **criteria) -> bool:
    """An event in the final calendar matches. `count`: exactly that many. `new_only`: created by the agent."""
    hits = _matching_events(new_only, **criteria)
    passed = len(hits) >= 1 if count is None else len(hits) == count
    return expect(f"event_exists({criteria})", passed, f"{len(hits)} matching event(s)")


def event_absent(**criteria) -> bool:
    hits = _matching_events(False, **criteria)
    return expect(f"event_absent({criteria})", not hits, f"found {[e['id'] for e in hits]}" if hits else "")


# --- Email -------------------------------------------------------------------

def _texts(value: str | list[str] | None) -> list[str]:
    return [] if value is None else [value] if isinstance(value, str) else value


def _email_matches(email: dict, to=None, cc=None, subject_contains=None, body_contains=None, in_reply_to=None) -> bool:
    """`to`/`cc`: each address must be a recipient. `*_contains`: each text must appear (case-insensitive)."""
    recipients = {a.lower() for a in email["to"]}
    copied = {a.lower() for a in email["cc"]}
    return (
        all(a.lower() in recipients for a in _texts(to))
        and all(a.lower() in copied for a in _texts(cc))
        and all(t.lower() in email["subject"].lower() for t in _texts(subject_contains))
        and all(t.lower() in email["body"].lower() for t in _texts(body_contains))
        and (in_reply_to is None or email["in_reply_to"] == in_reply_to)
    )


def _new_emails(folder: str, **criteria) -> list[dict]:
    added = set(changes().get("mail", {}).get("add", []))
    return [e for e in load("mail") if e["id"] in added and e["folder"] == folder and _email_matches(e, **criteria)]


def email_sent(*, count: int | None = None, **criteria) -> bool:
    """The agent sent an email matching to/cc/subject_contains/body_contains/in_reply_to. `count`: exactly that many."""
    hits = _new_emails("sent", **criteria)
    passed = len(hits) >= 1 if count is None else len(hits) == count
    return expect(f"email_sent({criteria})", passed, f"{len(hits)} matching email(s) sent")


def email_not_sent(**criteria) -> bool:
    """No sent email matches. With no criteria: the agent sent nothing at all."""
    hits = _new_emails("sent", **criteria)
    return expect(f"email_not_sent({criteria})", not hits, f"sent {[e['id'] for e in hits]}" if hits else "")


def draft_saved(*, count: int | None = None, **criteria) -> bool:
    hits = _new_emails("drafts", **criteria)
    passed = len(hits) >= 1 if count is None else len(hits) == count
    return expect(f"draft_saved({criteria})", passed, f"{len(hits)} matching draft(s)")


def email_in_folder(email_id: str, folder: str) -> bool:
    """An existing email ended up in `folder` (e.g. archived)."""
    actual = next((e["folder"] for e in load("mail") if e["id"] == email_id), None)
    return expect(f"email_in_folder({email_id!r}, {folder!r})", actual == folder, f"it is in {actual!r}")


# --- Building blocks for custom checks --------------------------------------

def new_events() -> list[dict]:
    """Events the agent created."""
    added = set(changes().get("calendar", {}).get("add", []))
    return [e for e in load("calendar") if e["id"] in added]


def sent_emails() -> list[dict]:
    """Emails the agent sent (not drafts)."""
    added = set(changes().get("mail", {}).get("add", []))
    return [e for e in load("mail") if e["id"] in added and e["folder"] == "sent"]


def clashes(event: dict) -> list[dict]:
    """Other events in the final calendar that overlap this one."""
    start, end = datetime.fromisoformat(event["start"]), datetime.fromisoformat(event["end"])
    return [
        e for e in load("calendar")
        if e["id"] != event["id"]
        and datetime.fromisoformat(e["start"]) < end and datetime.fromisoformat(e["end"]) > start
    ]


def mentions_date(text: str, when: str) -> bool:
    """Free text names this date: the weekday, '10 October', '10th', '10/10'..."""
    d = datetime.fromisoformat(when)
    text = text.lower()
    patterns = [f"{d:%A}".lower(), f"{d.day}th", f"{d.day}st", f"{d.day}nd", f"{d.day}rd",
                f"{d.day} {d:%B}".lower(), f"{d.day} {d:%b}".lower(), f"{d.day}/{d.month}", f"{d:%Y-%m-%d}"]
    return any(p in text for p in patterns)


def mentions_time(text: str, when: str) -> bool:
    """Free text names this time of day: '19:30', '7:30pm', '7.30 pm', '7pm'..."""
    d = datetime.fromisoformat(when)
    text = text.lower().replace(" ", "")
    hour12 = d.hour % 12 or 12
    suffix = "pm" if d.hour >= 12 else "am"
    patterns = [f"{d:%H:%M}", f"{d:%H}.{d:%M}", f"{hour12}:{d:%M}{suffix}", f"{hour12}.{d:%M}{suffix}"]
    if d.minute == 0:
        patterns.append(f"{hour12}{suffix}")
    return any(p in text for p in patterns)


def file_text(path: str) -> str:
    p = Path(path)
    return p.read_text() if p.exists() else ""


# --- Side effects ------------------------------------------------------------

def only_changed(allowed: dict[str, int | str]) -> bool:
    """
    Every change must fit the budget, e.g. {"calendar.update": 1, "calendar.add": "any"}.
    Anything not listed is collateral damage.
    """
    violations = []
    for name, diff in changes().items():
        for op, ids in diff.items():
            budget = allowed.get(f"{name}.{op}", 0)
            if ids and budget != "any" and len(ids) > budget:
                violations.append(f"{name}.{op}: {ids} (allowed {budget})")
    return expect(f"only_changed({allowed})", not violations, "; ".join(violations))


def nothing_changed() -> bool:
    """For ask and refuse tasks: the agent must not have touched the world."""
    return only_changed({})


# --- The agent's final reply -------------------------------------------------

def reply() -> str:
    return REPLY_PATH.read_text() if REPLY_PATH.exists() else ""


def reply_contains(*texts: str, any_of: bool = False) -> bool:
    """Case-insensitive. All texts must appear, or at least one with any_of=True."""
    text = reply().lower()
    found = [t for t in texts if t.lower() in text]
    passed = bool(found) if any_of else len(found) == len(texts)
    return expect(f"reply_contains({texts}, any_of={any_of})", passed, f"reply was: {reply()[:200]!r}")


# --- Result ------------------------------------------------------------------

def finish() -> None:
    passed = bool(_results) and all(r["passed"] for r in _results)
    for r in _results:
        print(f"{'PASS' if r['passed'] else 'FAIL'}  {r['check']}  {r['detail']}")
    VERIFIER_DIR.mkdir(parents=True, exist_ok=True)
    (VERIFIER_DIR / "checks.json").write_text(json.dumps(_results, indent=2))
    (VERIFIER_DIR / "reward.txt").write_text("1\n" if passed else "0\n")
