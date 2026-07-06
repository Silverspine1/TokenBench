import json
from pathlib import Path

from tokenbench.analysis.aggregate import aggregate_runs


def _write(runs_dir: Path, run_id, cid, task, *, prompt, agent_out, tool_out, patch,
           total, provider=None):
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
            "prompt_input_tokens": prompt,
            "agent_total_output_tokens": agent_out,
            "tool_test_output_tokens": tool_out,
            "patch_tokens": patch,
            "total_observed_tokens": total,
        },
        "provider_usage": provider or {"available": False, "total_tokens": None},
    }
    (d / "telemetry.json").write_text(json.dumps(tel), encoding="utf-8")


def test_aggregate_includes_token_breakdown(tmp_path):
    _write(tmp_path, "r1", "A", "t1", prompt=100, agent_out=200, tool_out=300, patch=40, total=640)
    _write(tmp_path, "r2", "A", "t2", prompt=200, agent_out=400, tool_out=500, patch=60, total=1160)

    a = aggregate_runs(tmp_path)[0]
    assert a["mean_prompt_input_tokens"] == 150.0
    assert a["median_prompt_input_tokens"] == 150.0
    assert a["mean_agent_output_tokens"] == 300.0
    assert a["mean_tool_test_output_tokens"] == 400.0
    assert a["mean_patch_tokens"] == 50.0
    assert a["mean_total_observed_tokens"] == 900.0
    assert a["median_total_observed_tokens"] == 900.0


def test_provider_means_null_when_unavailable(tmp_path):
    _write(tmp_path, "r1", "A", "t1", prompt=100, agent_out=200, tool_out=300, patch=40, total=640)
    a = aggregate_runs(tmp_path)[0]
    assert a["provider_usage_available_rate"] == 0.0
    # Null, NOT zero, when no provider usage exists.
    assert a["mean_provider_input_tokens"] is None
    assert a["mean_provider_output_tokens"] is None
    assert a["mean_provider_total_tokens"] is None
    assert a["mean_provider_cost_usd"] is None


def test_provider_means_use_available_runs_only(tmp_path):
    _write(tmp_path, "r1", "A", "t1", prompt=100, agent_out=200, tool_out=300, patch=40, total=640,
           provider={"available": True, "input_tokens": 500, "output_tokens": 1000,
                     "total_tokens": 1500, "cost_usd": 0.02})
    _write(tmp_path, "r2", "A", "t2", prompt=100, agent_out=200, tool_out=300, patch=40, total=640)

    a = aggregate_runs(tmp_path)[0]
    assert a["provider_usage_available_rate"] == 0.5
    # Mean over the single available run, not diluted by the unavailable one.
    assert a["mean_provider_input_tokens"] == 500.0
    assert a["mean_provider_total_tokens"] == 1500.0
    assert a["mean_provider_cost_usd"] == 0.02
