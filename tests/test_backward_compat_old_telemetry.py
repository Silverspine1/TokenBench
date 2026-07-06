"""Old telemetry/score files (pre token-breakdown) must still aggregate.

The analysis layer reads telemetry as plain dicts with safe getters, so an
artifact lacking ``token_estimates`` or ``provider_usage`` must not crash — the
new metrics fall back to 0 (estimates) or null (provider).
"""

import json
from pathlib import Path

from tokenbench.analysis.aggregate import aggregate_runs
from tokenbench.analysis.compare import compare_conditions
from tokenbench.telemetry.reports import calibration_report


def _write_old(runs_dir: Path, run_id, cid, task):
    """A pre-V0.4.3 run: no token_estimates, no provider_usage section."""
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "score.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "trial_index": 0,
        "repo_id": "m", "task_id": task,
        "quality_score": 100.0, "efficiency_score": 80.0, "final_score": 90.0,
        "success": True,
        "timing": {"total_wall_time_seconds": 10.0, "agent_wall_time_seconds": 10.0},
        "usage_proxy": {"total_log_bytes": 5000},
        "penalties": {"dependency_download_events": 0},
    }), encoding="utf-8")
    (d / "telemetry.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "repo_id": "m", "task_id": task,
        "timing": {"agent_wall_time_seconds": 10.0},
        "logs": {"total_log_bytes": 5000},
        "patch": {"line_churn": 6, "changed_scored_files": 1},
        "estimates": {"estimated_total_observed_tokens": 1500},
    }), encoding="utf-8")


def test_aggregate_tolerates_old_telemetry(tmp_path):
    _write_old(tmp_path, "r1", "A", "t1")
    a = aggregate_runs(tmp_path)[0]
    # Legacy metric still works.
    assert a["mean_estimated_total_observed_tokens"] == 1500.0
    # New breakdown metrics default to 0 when the section is absent.
    assert a["mean_prompt_input_tokens"] == 0.0
    assert a["mean_total_observed_tokens"] == 0.0
    # Provider means null, not zero.
    assert a["provider_usage_available_rate"] == 0.0
    assert a["mean_provider_total_tokens"] is None


def test_compare_tolerates_old_telemetry(tmp_path):
    _write_old(tmp_path, "a1", "A", "t1")
    _write_old(tmp_path, "b1", "B", "t1")
    out = compare_conditions(tmp_path, "A", "B")
    assert out["paired_tasks"] == 1
    assert out["mean_total_observed_token_delta"] == 0.0
    # Baseline is 0 for the absent breakdown -> savings null.
    assert out["total_observed_token_savings_percent"] is None


def test_calibration_tolerates_old_telemetry(tmp_path):
    _write_old(tmp_path, "r1", "test_condition_baseline", "t1")
    rep = calibration_report(tmp_path, "test_condition_baseline")
    a = rep["tasks"][0]
    assert a["median_estimated_total_observed_tokens"] == 1500.0
    assert a["median_total_observed_tokens"] == 0.0
    assert a["median_provider_total_tokens"] is None
