from datetime import date, datetime, timedelta

from pyagi_bench.env.tools import ToolError


def matches_query(query: str, *fields) -> bool:
    """Every whitespace-separated word of the query appears in at least one field (case-insensitive)."""
    haystack = " ".join(_flatten(fields)).lower()
    return all(word in haystack for word in query.lower().split())


def _flatten(fields) -> list[str]:
    out = []
    for f in fields:
        if isinstance(f, list):
            out.extend(str(x) for x in f)
        elif f is not None:
            out.append(str(f))
    return out


def parse_when(value: str, *, end_of_day: bool = False) -> datetime:
    """Accept YYYY-MM-DD or YYYY-MM-DDTHH:MM. A bare date as a range end means the whole day."""
    try:
        if len(value) == 10:
            day = date.fromisoformat(value)
            start = datetime(day.year, day.month, day.day)
            return start + timedelta(days=1) if end_of_day else start
        return datetime.fromisoformat(value).replace(tzinfo=None, second=0, microsecond=0)
    except ValueError:
        raise ToolError(f"Could not parse '{value}'. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM (local time).")


def fmt(dt: datetime) -> str:
    return dt.isoformat(timespec="minutes")
