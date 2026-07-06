"""Efficiency proxy scoring (V0.5).

Proxy based on output volume and wall time. Replaced later by canonical token
accounting.
"""

from __future__ import annotations


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def efficiency_score(total_log_bytes: int, wall_time_seconds: float, allowed_runtime_seconds: float) -> float:
    """Legacy V0.5 proxy. Retained for reference; V0.2 uses the components below."""
    score = 100.0
    score -= min(40.0, total_log_bytes / 250000.0)
    if allowed_runtime_seconds > 0:
        score -= min(30.0, wall_time_seconds / allowed_runtime_seconds * 30.0)
    return clamp(score)


def file_churn_score(
    changed_scored_files: int,
    expected_changed_files_max: int | None = None,
) -> float:
    """Score scored-file churn.

    When the manifest declares ``expected_changed_files_max``, changes within
    that budget are not penalized; each scored file beyond it costs 10 points.
    Without a declared max, fall back to the generic 5-points-per-file taper.
    """
    if expected_changed_files_max is not None:
        if changed_scored_files <= expected_changed_files_max:
            return 100.0
        over = changed_scored_files - expected_changed_files_max
        return clamp(100.0 - min(100.0, over * 10.0))
    return clamp(100.0 - min(100.0, changed_scored_files * 5.0))


def efficiency_components(
    total_wall_time_seconds: float,
    allowed_runtime_seconds: float,
    total_log_bytes: int,
    log_budget_bytes: int,
    changed_scored_files: int,
    dependency_download_events: int,
    expected_changed_files_max: int | None = None,
) -> dict:
    """Named V0.2 efficiency components, each clamped to [0, 100]."""
    if allowed_runtime_seconds and allowed_runtime_seconds > 0:
        wall = 100.0 - min(100.0, total_wall_time_seconds / allowed_runtime_seconds * 100.0)
    else:
        wall = 100.0

    if log_budget_bytes and log_budget_bytes > 0:
        logv = 100.0 - min(100.0, total_log_bytes / log_budget_bytes * 100.0)
    else:
        logv = 100.0

    churn = file_churn_score(changed_scored_files, expected_changed_files_max)
    dep = 100.0 - min(100.0, dependency_download_events * 25.0)

    return {
        "wall_time_score": round(clamp(wall), 4),
        "log_volume_score": round(clamp(logv), 4),
        "file_churn_score": round(clamp(churn), 4),
        "dependency_score": round(clamp(dep), 4),
    }


def composite_efficiency(components: dict) -> float:
    """Weighted blend of the four efficiency components."""
    return clamp(
        0.35 * components["wall_time_score"]
        + 0.35 * components["log_volume_score"]
        + 0.15 * components["file_churn_score"]
        + 0.15 * components["dependency_score"]
    )
