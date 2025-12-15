"""File-based persistence for multipliers and settings snapshots.

The previous version stored everything in MySQL. To simplify setup and keep
data co-located with the GUI settings, this module now persists multipliers in
``~/.aviator_bot/multipliers.json`` (or a custom ``data_path``). The JSON file
is append-friendly and rewritten on every insert to keep things simple and
resilient.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence

from . import config


def _data_path(settings=None) -> Path:
    cfg = settings or config.get_settings()
    return Path(cfg.data_path)


def initialize_schema(settings=None) -> None:
    path = _data_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps({"multipliers": []}, indent=2), encoding="utf-8")


def ping(settings=None) -> None:
    """File-based check to mimic the old MySQL readiness call."""

    path = _data_path(settings)
    initialize_schema(settings)
    path.touch(exist_ok=True)


def _load_all(settings=None) -> List[float]:
    initialize_schema(settings)
    path = _data_path(settings)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        values = raw.get("multipliers", [])
        return [float(v) for v in values]
    except json.JSONDecodeError:
        # fallback to empty when the file was partially written
        return []


def insert_multipliers(values: Sequence[float], settings=None) -> int:
    if not values:
        return 0
    existing = _load_all(settings)
    existing.extend(float(v) for v in values)
    path = _data_path(settings)
    path.write_text(json.dumps({"multipliers": existing}, indent=2), encoding="utf-8")
    return len(values)


def fetch_recent_multipliers(limit: int, settings=None) -> List[float]:
    values = list(reversed(_load_all(settings)))
    if limit <= 0:
        return []
    return values[:limit]


def count_multipliers(settings=None) -> int:
    return len(_load_all(settings))
