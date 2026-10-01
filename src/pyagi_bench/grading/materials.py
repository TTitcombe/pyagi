"""Render a trial for a grader (LLM judge or human). Both see exactly the same view."""
import json

import yaml

from pyagi_bench.grading.context import GradeContext


class _Dumper(yaml.SafeDumper):
    """Multi-line strings (email bodies, documents) as readable blocks rather than escaped one-liners."""


_Dumper.add_representer(
    str, lambda d, s: d.represent_scalar("tag:yaml.org,2002:str", s, style="|" if "\n" in s else None)
)


def readable(record: dict) -> str:
    return yaml.dump(record, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=100).rstrip()


def render(ctx: GradeContext, sections: list[str] | None = None) -> str:
    sections = sections or ["conversation", "changes"]
    parts = []
    if "conversation" in sections:
        parts.append("## Conversation\n" + _conversation(ctx))
    if "tool_calls" in sections:
        parts.append("## Tool calls\n" + _tool_calls(ctx))
    if "changes" in sections:
        parts.append("## Changes the agent made to the world\n" + _changes(ctx))
    return "\n\n".join(parts)


def _conversation(ctx: GradeContext) -> str:
    lines = []
    for e in ctx.events:
        if e["type"] == "session":
            lines.append(f"--- session {e['session'] + 1} ---")
        elif e["type"] in ("user", "agent"):
            lines.append(f"[{e['type'].upper()}] {e['content']}")
    return "\n".join(lines) or "(none)"


def _tool_calls(ctx: GradeContext) -> str:
    lines = [
        f"- {e['name']}({json.dumps(e['args'])})" + (f"  -> ERROR {e['error']}" if "error" in e else "")
        for e in ctx.events if e["type"] == "tool_call"
    ]
    return "\n".join(lines) or "(none)"


def _changes(ctx: GradeContext) -> str:
    lines = []
    for collection in ctx.diff:
        for scope, label in (("added", "ADDED"), ("updated", "UPDATED"), ("deleted", "DELETED")):
            for record in ctx.records(collection, scope):
                lines.append(f"{label} {collection}:\n{readable(record)}\n")
    return "\n".join(lines) or "(no changes)"
