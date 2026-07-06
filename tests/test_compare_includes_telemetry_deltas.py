import json
from pathlib import Path

from tokenbench.analysis.compare import compare_conditions


def _write(runs_dir: Path, run_id, cid, task, *, est_tokens, log_bytes, agent_wall, churn):
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "score.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "trial_index": 0,
        "repo_id": "m", "task_id": task,
        "quality_score": 100.0, "efficiency_score": 80.0, "final_score": 90.0,
        "success": True,
        "timing": {"total_wall_time_seconds": agent_wall, "agent_wall_time_seconds": agent_wall},
        "usage_proxy": {"total_log_bytes": log_bytes},
    }), encoding="utf-8")
    (d / "telemetry.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "repo_id": "m", "task_id": task,
        "timing": {"agent_wall_time_seconds": agent_wall},
        "patch": {"line_churn": churn},
        "estimates": {"estimated_total_observed_tokens": est_tokens},
    }), encoding="utf-8")


def test_compare_includes_telemetry_deltas_and_savings(tmp_path):
    # Baseline A vs B; B uses fewer tokens / less runtime / fewer log bytes.
    _write(tmp_path, "a1", "A", "t1", est_tokens=1000, log_bytes=10000, agent_wall=40.0, churn=10)
    _write(tmp_path, "b1", "B", "t1", est_tokens=800, log_bytes=6000, agent_wall=20.0, churn=4)

    out = compare_conditions(tmp_path, "A", "B")
    assert out["paired_tasks"] == 1

    # Deltas are B - A.
    assert out["mean_estimated_tokens_delta"] == -200.0
    assert out["mean_runtime_delta"] == -20.0
    assert out["mean_log_bytes_delta"] == -4000.0
    assert out["mean_line_churn_delta"] == -6.0

    # Percent savings of B relative to A's baseline.
    assert out["estimated_token_savings_percent"] == 20.0
    assert out["runtime_savings_percent"] == 50.0
    assert out["log_byte_savings_percent"] == 40.0


def test_compare_savings_none_when_no_pairs(tmp_path):
    _write(tmp_path, "a1", "A", "t1", est_tokens=1000, log_bytes=10, agent_wall=1.0, churn=1)
    _write(tmp_path, "b1", "B", "t2", est_tokens=1000, log_bytes=10, agent_wall=1.0, churn=1)
    out = compare_conditions(tmp_path, "A", "B")
    assert out["paired_tasks"] == 0
    assert out["estimated_token_savings_percent"] is None
    assert out["runtime_savings_percent"] is None
