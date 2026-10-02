"""Run configs: a YAML file describing the agent under test. Stored in full with every run."""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pyagi_bench.yamlio import load_yaml


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
    def hash(self) -> str:
        return hashlib.sha256(json.dumps(self.raw, sort_keys=True).encode()).hexdigest()[:8]


def load_config(path: Path) -> RunConfig:
    raw = load_yaml(path) or {}
    if "type" not in raw.get("agent", {}):
        raise ValueError(f"{path}: config needs agent.type")
    raw.setdefault("name", path.stem)
    return RunConfig(raw["name"], raw)
