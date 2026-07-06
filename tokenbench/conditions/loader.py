"""Loading of condition JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Condition


def load_condition(path: Path) -> Condition:
    """Load and parse a single condition JSON file."""
    raw = Path(path).read_text(encoding="utf-8")
    return Condition.model_validate(json.loads(raw))


def load_conditions(conditions_dir: Path) -> dict[str, Condition]:
    """Load every ``*.json`` condition under ``conditions_dir``, keyed by id.

    Deterministic: files are read in sorted path order.
    """
    out: dict[str, Condition] = {}
    for path in sorted(Path(conditions_dir).glob("*.json")):
        cond = load_condition(path)
        out[cond.condition_id] = cond
    return out
