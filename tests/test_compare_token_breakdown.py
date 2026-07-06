import json
from pathlib import Path

from tokenbench.analysis.compare import compare_conditions


def _write(runs_dir: Path, run_id, cid, task, *, prompt, agent_out, tool_out, patch, total):
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "score.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "trial_index": 0,
        "repo_id": "m", "task_id": task,
        "quality_score": 100.0, "efficiency_score": 80.0, "final_score": 90.0,
        "success": True,
        "timing": {"total_wall_time_seconds": 1.0, "agent_wall_time_seconds": 1.0},
        "usage_proxy": {"total_log_bytes": 1},
    }), encoding="utf-8")
    (d / "telemetry.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "repo_id": "m", "task_id": task,
        "token_estimates": {
            "prompt_input_tokens": prompt,
            "agent_total_output_tokens": agent_out,
            "tool_test_output_tokens": tool_out,
            "patch_tokens": patch,
            "total_observed_tokens": total,
        },
    }), encoding="utf-8")


def test_compare_token_breakdown_deltas_and_savings(tmp_path):
    # A = baseline, B = cheaper.
    _write(tmp_path, "a1", "A", "t1", prompt=100, agent_out=400, tool_out=500, patch=50, total=1050)
    _write(tmp_path, "b1", "B", "t1", prompt=80, agent_out=300, tool_out=250, patch=40, total=670)

    out = compare_conditions(tmp_path, "A", "B")
    assert out["paired_tasks"] == 1

    # Deltas are B - A.
    assert out["mean_prompt_input_token_delta"] == -20.0
    assert out["mean_agent_output_token_delta"] == -100.0
    assert out["mean_tool_test_output_token_delta"] == -250.0
    assert out["mean_patch_token_delta"] == -10.0
    assert out["mean_total_observed_token_delta"] == -380.0

    # Percent savings of B vs A.
    assert out["prompt_input_token_savings_percent"] == 20.0
    assert out["agent_output_token_savings_percent"] == 25.0
    assert out["tool_test_output_token_savings_percent"] == 50.0
    assert out["total_observed_token_savings_percent"] == round(380 / 1050 * 100.0, 4)


def test_compare_savings_none_when_no_pairs(tmp_path):
    _write(tmp_path, "a1", "A", "t1", prompt=100, agent_out=1, tool_out=1, patch=1, total=103)
    _write(tmp_path, "b1", "B", "t2", prompt=100, agent_out=1, tool_out=1, patch=1, total=103)
    out = compare_conditions(tmp_path, "A", "B")
    assert out["paired_tasks"] == 0
    assert out["prompt_input_token_savings_percent"] is None
    assert out["total_observed_token_savings_percent"] is None
