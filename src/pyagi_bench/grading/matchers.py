"""
Matching record fields / reply text against expectations written in task YAML.

    "Bob@x.example"           scalar: case-insensitive equality (datetimes compared as datetimes);
                              against a list value, matches if any element equals it
    {contains: "boiler"}      substring, case-insensitive; a list means every item must appear
    {contains_any: [a, b]}    at least one substring
    {regex: "..."}            re.search, case-insensitive
"""
import re
from datetime import datetime
from typing import Any


def _as_datetime(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _equal(value: Any, expected: Any) -> bool:
    dv, de = _as_datetime(value), _as_datetime(expected)
    if dv and de:
        return dv == de
    if isinstance(value, str) and isinstance(expected, str):
        return value.strip().lower() == expected.strip().lower()
    return value == expected


def _text(value: Any) -> str:
    return " ".join(map(str, value)).lower() if isinstance(value, list) else str(value).lower()


def _items(x: Any) -> list:
    return x if isinstance(x, list) else [x]


OPERATORS = {
    "contains": lambda v, e: all(str(x).lower() in _text(v) for x in _items(e)),
    "contains_any": lambda v, e: any(str(x).lower() in _text(v) for x in _items(e)),
    "regex": lambda v, e: re.search(e, _text(v), re.IGNORECASE) is not None,
}


def match(value: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        unknown = set(expected) - set(OPERATORS)
        if unknown:
            raise ValueError(f"Unknown matcher(s) {sorted(unknown)}; known: {sorted(OPERATORS)}")
        return all(OPERATORS[op](value, arg) for op, arg in expected.items())
    if isinstance(value, list):
        return any(_equal(v, expected) for v in value)
    return _equal(value, expected)


def match_record(record: dict, where: dict) -> bool:
    return all(field in record and match(record[field], expected) for field, expected in where.items())
