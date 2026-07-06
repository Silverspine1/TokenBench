"""Deterministic-ish, sortable run id generation."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_stamp(dt: datetime | None = None) -> str:
    """UTC timestamp formatted for run ids: YYYYMMDD_HHMMSS."""
    dt = dt or utc_now()
    return dt.astimezone(timezone.utc).strftime("%Y%m%d_%H%M%S")


def short_random(n: int = 6) -> str:
    # hex chars, lowercase, collision-resistant enough for a run suffix.
    return secrets.token_hex(8)[:n]


def generate_run_id(
    repo_id: str,
    task_id: str,
    dt: datetime | None = None,
    suffix: str | None = None,
) -> str:
    """YYYYMMDD_HHMMSS_<repo_id>_<task_id>_<short_random>."""
    stamp = utc_stamp(dt)
    suffix = suffix or short_random()
    return f"{stamp}_{repo_id}_{task_id}_{suffix}"
