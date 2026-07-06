"""Aggregate emits provider cost fields, null when no provider usage exists."""

import json
from pathlib import Path

from tokenbench.analysis.aggregate import aggregate_runs


def _write(runs_dir: Path, run_id, cid, task, *, provider=None):
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "score.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "trial_index": 0,
        "repo_id": "m", "task_id": task,
        "quality_score": 100.0, "efficiency_score": 80.0, "final_score": 90.0,
        "success": True,
        "timing": {"total_wall_time_seconds": 1.0, "agent_wall_time_seconds": 1.0},
        "usage_proxy": {"total_log_bytes": 100},
    }), encoding="utf-8")
    tel = {
        "run_id": run_id, "condition_id": cid, "repo_id": "m", "task_id": task,
        "token_estimates": {
            "prompt_input_tokens": 100, "agent_total_output_tokens": 200,
            "tool_test_output_tokens": 300, "patch_tokens": 40,
            "total_observed_tokens": 640,
        },
        "provider_usage": provider or {"available": False, "total_tokens": None,
                                       "cost_usd": None},
    }
    (d / "telemetry.json").write_text(json.dumps(tel), encoding="utf-8")


def test_cost_fields_present_and_aggregated(tmp_path):
    _write(tmp_path, "r1", "A", "t1", provider={
        "available": True, "total_tokens": 1000, "cost_usd": 0.10})
    _write(tmp_path, "r2", "A", "t2", provider={
        "available": True, "total_tokens": 3000, "cost_usd": 0.30})

    a = aggregate_runs(tmp_path)[0]
    assert a["provider_usage_available_rate"] == 1.0
    assert a["total_provider_cost_usd"] == 0.40
    assert a["mean_provider_cost_usd"] == 0.20
    assert a["median_provider_cost_usd"] == 0.20
    assert a["mean_provider_total_tokens"] == 2000.0
    assert a["median_provider_total_tokens"] == 2000.0


def test_cost_fields_null_when_unavailable(tmp_path):
    _write(tmp_path, "r1", "A", "t1")
    a = aggregate_runs(tmp_path)[0]
    assert a["provider_usage_available_rate"] == 0.0
    # Null, never 0 — a missing cost is not "free".
    assert a["total_provider_cost_usd"] is None
    assert a["mean_provider_cost_usd"] is None
    assert a["median_provider_cost_usd"] is None
    assert a["median_provider_total_tokens"] is None


def test_cost_uses_available_runs_only(tmp_path):
    _write(tmp_path, "r1", "A", "t1", provider={
        "available": True, "total_tokens": 1000, "cost_usd": 0.10})
    _write(tmp_path, "r2", "A", "t2")  # unavailable

    a = aggregate_runs(tmp_path)[0]
    assert a["provider_usage_available_rate"] == 0.5
    # Total/mean computed over the one available run, not diluted by the other.
    assert a["total_provider_cost_usd"] == 0.10
    assert a["mean_provider_cost_usd"] == 0.10
