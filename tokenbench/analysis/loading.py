"""Shared loading of score.json records across a runs directory."""

from __future__ import annotations

import json
from pathlib import Path


def load_scores(runs_dir: Path) -> list[dict]:
    """Load every ``*/score.json`` under ``runs_dir``.

    Sorted by run_id for deterministic downstream ordering.
    """
    out: list[dict] = []
    for path in sorted(Path(runs_dir).glob("*/score.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    out.sort(key=lambda s: s.get("run_id", ""))
    return out


def load_telemetry(runs_dir: Path) -> dict[str, dict]:
    """Load every ``*/telemetry.json`` under ``runs_dir``, keyed by run_id."""
    out: dict[str, dict] = {}
    for path in sorted(Path(runs_dir).glob("*/telemetry.json")):
        try:
            t = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rid = t.get("run_id")
        if rid:
            out[rid] = t
    return out


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    n = len(xs)
    mid = n // 2
    if n % 2:
        return float(xs[mid])
    return (xs[mid - 1] + xs[mid]) / 2.0


def _nested(score: dict, *keys: str) -> float:
    cur: object = score
    for k in keys:
        if not isinstance(cur, dict):
            return 0.0
        cur = cur.get(k, 0.0)
    return float(cur) if isinstance(cur, (int, float)) else 0.0
