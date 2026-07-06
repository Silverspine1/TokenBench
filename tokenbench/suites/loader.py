"""Loading of suite JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Suite


def load_suite(path: Path) -> Suite:
    """Load and parse a single suite JSON file."""
    raw = Path(path).read_text(encoding="utf-8")
    return Suite.model_validate(json.loads(raw))
