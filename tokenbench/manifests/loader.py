"""Manifest loading from JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import TaskManifest


def load_manifest(path: Path) -> TaskManifest:
    """Load and parse a manifest JSON file into a TaskManifest.

    Raises pydantic.ValidationError on schema violations and
    json.JSONDecodeError on malformed JSON.
    """
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    return TaskManifest.model_validate(data)
