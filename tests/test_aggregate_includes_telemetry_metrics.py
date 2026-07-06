import json
from pathlib import Path

from tokenbench.analysis.aggregate import aggregate_runs


def _write(runs_dir: Path, run_id, cid, task, *, churn, scored, est_tokens, log_bytes, agent_wall):
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "score.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "trial_index": 0,
        "repo_id": "m", "task_id": task,
        "quality_score": 100.0, "efficiency_score": 80.0, "final_score": 90.0,
        "success": True,
        "timing": {"total_wall_time_seconds": agent_wall, "agent_wall_time_seconds": agent_wall},
        "usage_proxy": {"total_log_bytes": log_bytes},
        "penalties": {"dependency_download_events": 0},
    }), encoding="utf-8")
    (d / "telemetry.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "repo_id": "m", "task_id": task,
        "timing": {"agent_wall_time_seconds": agent_wall},
        "logs": {"total_log_bytes": log_bytes},
        "patch": {"line_churn": churn, "changed_scored_files": scored},
        "estimates": {"estimated_total_observed_tokens": est_tokens},
    }), encoding="utf-8")


def test_aggregate_includes_telemetry_metrics(tmp_path):
    _write(tmp_path, "r1", "A", "t1", churn=8, scored=1, est_tokens=4000, log_bytes=10000, agent_wall=30.0)
    _write(tmp_path, "r2", "A", "t2", churn=12, scored=3, est_tokens=6000, log_bytes=20000, agent_wall=50.0)

    out = aggregate_runs(tmp_path)
    a = out[0]
    assert a["condition_id"] == "A"

    assert a["mean_line_churn"] == 10.0
    assert a["median_line_churn"] == 10.0
    assert a["mean_changed_scored_files"] == 2.0
    assert a["mean_estimated_total_observed_tokens"] == 5000.0
    assert a["median_estimated_total_observed_tokens"] == 5000.0
    assert a["mean_agent_wall_time_seconds"] == 40.0
    assert a["median_agent_wall_time_seconds"] == 40.0
    assert a["mean_total_log_bytes"] == 15000.0
    assert a["median_total_log_bytes"] == 15000.0
    assert a["mean_dependency_download_events"] == 0.0
    assert a["success_rate"] == 1.0


def test_aggregate_missing_telemetry_defaults_to_zero(tmp_path):
    # score.json only, no telemetry.json.
    d = tmp_path / "r1"
    d.mkdir(parents=True, exist_ok=True)
    (d / "score.json").write_text(json.dumps({
        "run_id": "r1", "condition_id": "A", "trial_index": 0,
        "repo_id": "m", "task_id": "t1",
        "quality_score": 50.0, "efficiency_score": 50.0, "final_score": 50.0,
        "timing": {"total_wall_time_seconds": 1.0},
        "usage_proxy": {"total_log_bytes": 5},
    }), encoding="utf-8")
    out = aggregate_runs(tmp_path)
    assert out[0]["mean_line_churn"] == 0.0
    assert out[0]["mean_estimated_total_observed_tokens"] == 0.0
