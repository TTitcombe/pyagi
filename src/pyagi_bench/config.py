"""
Run configs: YAML files describing the agent under test. Supports
    extends: other.yaml          deep-merge on top of another config (relative path)
    ${VAR} / ${VAR:-default}     environment interpolation in strings
    --set a.b=value              CLI overrides (value parsed as YAML)
The fully resolved config is stored with every run.
"""
import hashlib
import json
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pyagi_bench.yamlio import load_yaml

ENV_VAR = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")


class ConfigError(ValueError):
    pass


@dataclass
class RunConfig:
    name: str
    raw: dict

    @property
    def agent(self) -> dict:
        return self.raw["agent"]

    @property
    def model(self) -> dict:
        return self.raw.get("model") or {}

    @property
    def judge(self) -> dict | None:
        return self.raw.get("judge")

    @property
    def user_simulator(self) -> dict | None:
        return self.raw.get("user_simulator")

    @property
    def hash(self) -> str:
        return hashlib.sha256(json.dumps(self.raw, sort_keys=True).encode()).hexdigest()[:8]


def deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for key, value in override.items():
        out[key] = deep_merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def _interpolate(value: Any) -> Any:
    if isinstance(value, str):
        return ENV_VAR.sub(lambda m: os.environ.get(m.group(1), m.group(2) or ""), value)
    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v) for v in value]
    return value


def _load_raw(path: Path, seen: tuple[Path, ...] = ()) -> dict:
    path = path.resolve()
    if path in seen:
        raise ConfigError(f"Circular 'extends' in {path}")
    raw = load_yaml(path) or {}
    parent = raw.pop("extends", None)
    return deep_merge(_load_raw(path.parent / parent, (*seen, path)), raw) if parent else raw


def apply_override(raw: dict, assignment: str) -> None:
    key, sep, value = assignment.partition("=")
    if not sep:
        raise ConfigError(f"--set expects key.path=value, got '{assignment}'")
    *parents, leaf = key.split(".")
    node = raw
    for part in parents:
        node = node.setdefault(part, {})
    node[leaf] = yaml.safe_load(value)


def load_config(path: Path, overrides: list[str] | None = None) -> RunConfig:
    raw = _load_raw(path)
    for assignment in overrides or []:
        apply_override(raw, assignment)
    raw = _interpolate(raw)

    if "agent" not in raw or "type" not in raw["agent"]:
        raise ConfigError(f"{path}: config needs agent.type")
    raw.setdefault("name", path.stem)
    return RunConfig(raw["name"], raw)
