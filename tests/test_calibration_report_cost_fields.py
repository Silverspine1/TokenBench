"""Calibration report exposes per-task provider cost and an unavailable note."""

import json
from pathlib import Path

from tokenbench.telemetry.reports import calibration_report

CID = "claude_code_opus_4_8_baseline"


def _write(runs_dir: Path, run_id, task, *, provider=None):
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "score.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": CID, "trial_index": 0,
        "repo_id": "m", "task_id": task,
        "quality_score": 100.0, "final_score": 90.0, "success": True,
        "timing": {"agent_wall_time_seconds": 1.0},
        "usage_proxy": {"total_log_bytes": 100},
    }), encoding="utf-8")
    tel = {
        "run_id": run_id, "condition_id": CID, "repo_id": "m", "task_id": task,
        "token_estimates": {
            "prompt_input_tokens": 100, "agent_total_output_tokens": 200,
            "tool_test_output_tokens": 300, "patch_tokens": 40,
            "total_observed_tokens": 640,
        },
        "estimates": {"estimated_total_observed_tokens": 640},
        "provider_usage": provider or {"available": False, "total_tokens": None,
                                       "cost_usd": None},
    }
    (d / "telemetry.json").write_text(json.dumps(tel), encoding="utf-8")


def test_cost_fields_present_when_available(tmp_path):
    _write(tmp_path, "r1", "t1", provider={
        "available": True, "total_tokens": 1000, "cost_usd": 0.10})
    _write(tmp_path, "r2", "t1", provider={
        "available": True, "total_tokens": 3000, "cost_usd": 0.30})

    rep = calibration_report(tmp_path, CID)
    task = rep["tasks"][0]
    assert task["provider_usage_available_rate"] == 1.0
    assert task["provider_cost_status"] == "provider cost available"
    assert task["median_provider_cost_usd"] == 0.20
    assert task["mean_provider_cost_usd"] == 0.20
    assert task["median_provider_total_tokens"] == 2000.0


def test_unavailable_is_explicit_not_silent(tmp_path):
    _write(tmp_path, "r1", "t1")
    rep = calibration_report(tmp_path, CID)
    task = rep["tasks"][0]
    assert task["provider_usage_available_rate"] == 0.0
    # The report must SAY cost is unavailable, not silently show estimates.
    assert task["provider_cost_status"] == "provider cost unavailable"
    assert task["median_provider_cost_usd"] is None
    assert task["mean_provider_cost_usd"] is None
    # Estimated tokens are still reported separately, never as provider cost.
    assert task["median_total_observed_tokens"] == 640.0
