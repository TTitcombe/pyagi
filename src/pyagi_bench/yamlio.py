from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> Any:
    with path.open() as fp:
        return normalise(yaml.safe_load(fp))


def normalise(value: Any) -> Any:
    """
    YAML parses unquoted timestamps into datetime objects. Everything in the
    world must stay plain JSON, so convert them back to ISO strings.
    """
    if isinstance(value, datetime):
        return value.isoformat(timespec="minutes")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): normalise(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalise(v) for v in value]
    return value
