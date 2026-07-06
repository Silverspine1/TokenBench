import json
from pathlib import Path

from tokenbench.telemetry.reports import calibration_report


def _write(runs_dir: Path, run_id, cid, task, *, prompt, agent_out, tool_out, patch, total,
           provider=None):
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "score.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "trial_index": 0,
        "repo_id": "pulseboard-saas", "task_id": task,
        "quality_score": 100.0, "efficiency_score": 80.0, "final_score": 90.0,
        "success": True,
        "timing": {"total_wall_time_seconds": 1.0, "agent_wall_time_seconds": 1.0},
        "usage_proxy": {"total_log_bytes": 1},
    }), encoding="utf-8")
    (d / "telemetry.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid,
        "repo_id": "pulseboard-saas", "task_id": task,
        "token_estimates": {
            "prompt_input_tokens": prompt,
            "agent_total_output_tokens": agent_out,
            "tool_test_output_tokens": tool_out,
            "patch_tokens": patch,
            "total_observed_tokens": total,
        },
        "provider_usage": provider or {"available": False, "total_tokens": None},
    }), encoding="utf-8")


def test_calibration_report_token_breakdown_medians(tmp_path):
    _write(tmp_path, "r1", "test_condition_baseline", "task_a",
           prompt=100, agent_out=200, tool_out=300, patch=40, total=640)
    _write(tmp_path, "r2", "test_condition_baseline", "task_a",
           prompt=200, agent_out=400, tool_out=500, patch=60, total=1160)

    rep = calibration_report(tmp_path, "test_condition_baseline")
    a = rep["tasks"][0]
    assert a["median_prompt_input_tokens"] == 150.0
    assert a["median_agent_output_tokens"] == 300.0
    assert a["median_tool_test_output_tokens"] == 400.0
    assert a["median_patch_tokens"] == 50.0
    assert a["median_total_observed_tokens"] == 900.0
    # No provider usage -> rate 0 and medians null.
    assert a["provider_usage_available_rate"] == 0.0
    assert a["median_provider_total_tokens"] is None
    assert a["median_provider_cost_usd"] is None


def test_calibration_report_provider_medians_when_available(tmp_path):
    _write(tmp_path, "r1", "test_condition_baseline", "task_a",
           prompt=100, agent_out=200, tool_out=300, patch=40, total=640,
           provider={"available": True, "total_tokens": 1500, "cost_usd": 0.03})
    rep = calibration_report(tmp_path, "test_condition_baseline")
    a = rep["tasks"][0]
    assert a["provider_usage_available_rate"] == 1.0
    assert a["median_provider_total_tokens"] == 1500.0
    assert a["median_provider_cost_usd"] == 0.03
