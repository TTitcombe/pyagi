"""
Declarative matching of record fields / text against expectations in task YAML.

    "Bob@x.example"              scalar: case-insensitive equality; datetimes compared as datetimes;
                                 against a list value, matches if any element equals it
    ["a@x", "b@x"]               list: same elements as the value, ignoring order and case
    {contains: "boiler"}         substring; a list means every item must appear
    {contains_any: [a, b]}       at least one substring
    {not_contains: ...}          none of the substrings
    {regex: "..."}               re.search, case-insensitive
    {includes: [...]}            list value contains (a match for) every item
    {excludes: [...]}            list value contains none of them
    {gte: x} / {lte: x}          numeric or datetime bounds
    {any_of: [spec, ...]}        any sub-spec matches
    {equals: x}                  strict equality
Operators in one mapping combine with AND.
"""
import operator
import re
from datetime import datetime
from typing import Any


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, str) and len(value) >= 10 and value[4] == "-":
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _norm(value: Any) -> Any:
    return value.strip().lower() if isinstance(value, str) else value


def _scalar_equal(value: Any, expected: Any) -> bool:
    dv, de = _as_datetime(value), _as_datetime(expected)
    if dv and de:
        return dv == de
    return _norm(value) == _norm(expected)


def _text(value: Any) -> str:
    return " ".join(map(str, value)).lower() if isinstance(value, list) else str(value).lower()


def _items(x: Any) -> list:
    return x if isinstance(x, list) else [x]


def _compare(value: Any, limit: Any, op) -> bool:
    if value is None:
        return False
    dv, dl = _as_datetime(value), _as_datetime(limit)
    return op(dv, dl) if dv and dl else op(value, limit)


OPERATORS = {
    "equals": lambda v, e: v == e,
    "contains": lambda v, e: all(str(x).lower() in _text(v) for x in _items(e)),
    "contains_any": lambda v, e: any(str(x).lower() in _text(v) for x in _items(e)),
    "not_contains": lambda v, e: not any(str(x).lower() in _text(v) for x in _items(e)),
    "regex": lambda v, e: re.search(e, _text(v), re.IGNORECASE) is not None,
    "includes": lambda v, e: isinstance(v, list) and all(any(match(x, item) for x in v) for item in _items(e)),
    "excludes": lambda v, e: not isinstance(v, list) or not any(match(x, item) for x in v for item in _items(e)),
    "gte": lambda v, e: _compare(v, e, operator.ge),
    "lte": lambda v, e: _compare(v, e, operator.le),
    "any_of": lambda v, e: any(match(v, spec) for spec in e),
}


def is_operator_spec(expected: Any) -> bool:
    return isinstance(expected, dict) and bool(expected) and set(expected) <= set(OPERATORS)


def match(value: Any, expected: Any) -> bool:
    if is_operator_spec(expected):
        return all(OPERATORS[op](value, arg) for op, arg in expected.items())
    if isinstance(expected, list):
        return isinstance(value, list) and sorted(map(_norm, value)) == sorted(map(_norm, expected))
    if isinstance(value, list):
        return any(_scalar_equal(v, expected) for v in value)
    return _scalar_equal(value, expected)


def match_record(record: dict, where: dict) -> bool:
    return all(field in record and match(record[field], expected) for field, expected in where.items())
