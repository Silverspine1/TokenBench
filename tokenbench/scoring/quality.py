"""Quality score (V0.2).

    quality_score =
        0.85 * hidden_test_case_pass_rate
      + 0.10 * visible_test_case_pass_rate
      + 0.05 * artifact_integrity_score

Pass rates are fractions in [0, 1]; artifact integrity is in [0, 100]. The
result is clamped to [0, 100]. Modifying a forbidden path is a hard zero.
"""

from __future__ import annotations

from .efficiency import clamp


def artifact_integrity_score(
    file_changes: dict,
    *,
    patch_empty: bool,
    hidden_failed: bool,
) -> float:
    """Start at 100 and apply integrity penalties.

    0 if forbidden paths modified
    -20 if deleted files outside scored paths
    -10 if ignored/log fixture files modified unnecessarily
    -10 if patch is empty and hidden tests fail
    """
    if file_changes.get("forbidden_modified"):
        return 0.0

    score = 100.0
    scored = set(file_changes.get("scored_modified", []))
    deleted_outside = [d for d in file_changes.get("deleted", []) if d not in scored]
    if deleted_outside:
        score -= 20.0
    if file_changes.get("ignored_modified"):
        score -= 10.0
    if patch_empty and hidden_failed:
        score -= 10.0
    return clamp(score)


def quality_score_v02(
    hidden_pass_rate: float,
    visible_pass_rate: float,
    artifact_integrity: float,
    *,
    forbidden_modified: bool,
) -> float:
    """Weighted quality score. Forbidden path modification overrides to 0."""
    if forbidden_modified:
        return 0.0
    q = (
        0.85 * hidden_pass_rate * 100.0
        + 0.10 * visible_pass_rate * 100.0
        + 0.05 * artifact_integrity
    )
    return clamp(q)
