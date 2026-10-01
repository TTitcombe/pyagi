"""
Tool registry for the mock world.

The benchmark owns the tool *API* (names, parameters, behaviour) so every agent
config faces the same surface. How tools are presented to a model (prompt
format, native tool calling, descriptions) is the agent's business.
"""
from dataclasses import dataclass, field
from typing import Any, Callable

JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


@dataclass(frozen=True)
class Param:
    type: str
    description: str
    required: bool = True
    items: str | None = None
    enum: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    service: str
    description: str
    params: dict[str, Param]
    handler: Callable[..., Any] = field(repr=False)
    mutates: bool = False

    def json_schema(self) -> dict:
        properties = {}
        for name, p in self.params.items():
            prop: dict[str, Any] = {"type": p.type, "description": p.description}
            if p.items:
                prop["items"] = {"type": p.items}
            if p.enum:
                prop["enum"] = list(p.enum)
            properties[name] = prop
        return {
            "type": "object",
            "properties": properties,
            "required": [n for n, p in self.params.items() if p.required],
        }


class ToolError(Exception):
    """A mistake the agent made (bad id, invalid date...). Returned to the agent, not raised."""


TOOLS: dict[str, ToolSpec] = {}


def tool(name: str, service: str, description: str, /, *, mutates: bool = False, **params: Param):
    def register(fn: Callable) -> Callable:
        if name in TOOLS:
            raise ValueError(f"Duplicate tool name: {name}")
        TOOLS[name] = ToolSpec(name, service, description, params, fn, mutates)
        return fn

    return register


def _is_type(value: Any, json_type: str) -> bool:
    # bool is a subclass of int, which would let `true` through as an integer.
    if json_type in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, JSON_TYPES[json_type])


def validate_args(spec: ToolSpec, args: dict) -> str | None:
    unknown = sorted(set(args) - set(spec.params))
    if unknown:
        return f"Unknown parameter(s) {unknown} for {spec.name}. Expected: {sorted(spec.params)}"

    for name, p in spec.params.items():
        if name not in args:
            if p.required:
                return f"Missing required parameter '{name}' for {spec.name}"
            continue
        value = args[name]
        if not _is_type(value, p.type):
            return f"Parameter '{name}' must be of type {p.type}, got {type(value).__name__}"
        if p.items and not all(_is_type(v, p.items) for v in value):
            return f"Parameter '{name}' must be an array of {p.items}"
        if p.enum and value not in p.enum:
            return f"Parameter '{name}' must be one of {list(p.enum)}"

    return None


def all_tools() -> list[ToolSpec]:
    # Importing the services registers their tools.
    from pyagi_bench.env import calendar, contacts, documents, email, shop  # noqa: F401

    return list(TOOLS.values())
