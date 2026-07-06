import json
from pathlib import Path

from tokenbench.telemetry.reports import calibration_report


def _write(runs_dir: Path, run_id, cid, task, *, quality, success, agent_wall,
           log_bytes, est_tokens, scored, churn):
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "score.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid, "trial_index": 0,
        "repo_id": "pulseboard-saas", "task_id": task,
        "quality_score": quality, "efficiency_score": 80.0, "final_score": 90.0,
        "success": success,
        "timing": {"total_wall_time_seconds": agent_wall, "agent_wall_time_seconds": agent_wall},
        "usage_proxy": {"total_log_bytes": log_bytes},
    }), encoding="utf-8")
    (d / "telemetry.json").write_text(json.dumps({
        "run_id": run_id, "condition_id": cid,
        "repo_id": "pulseboard-saas", "task_id": task,
        "timing": {"agent_wall_time_seconds": agent_wall},
        "logs": {"total_log_bytes": log_bytes},
        "patch": {"line_churn": churn, "changed_scored_files": scored},
        "estimates": {"estimated_total_observed_tokens": est_tokens},
    }), encoding="utf-8")


def test_calibration_report_groups_by_task(tmp_path):
    _write(tmp_path, "r1", "claude_code_baseline", "task_a", quality=100, success=True,
           agent_wall=36.0, log_bytes=13000, est_tokens=4000, scored=1, churn=8)
    _write(tmp_path, "r2", "claude_code_baseline", "task_a", quality=100, success=True,
           agent_wall=40.0, log_bytes=15000, est_tokens=4800, scored=1, churn=10)
    _write(tmp_path, "r3", "claude_code_baseline", "task_b", quality=80, success=False,
           agent_wall=50.0, log_bytes=20000, est_tokens=6000, scored=2, churn=20)
    # Different condition is excluded.
    _write(tmp_path, "r4", "other", "task_a", quality=0, success=False,
           agent_wall=99.0, log_bytes=1, est_tokens=1, scored=9, churn=99)

    rep = calibration_report(tmp_path, "claude_code_baseline")
    assert rep["condition_id"] == "claude_code_baseline"
    assert [t["task_id"] for t in rep["tasks"]] == ["task_a", "task_b"]

    a = rep["tasks"][0]
    assert a["trials"] == 2
    assert a["success_rate"] == 1.0
    assert a["median_quality_score"] == 100.0
    assert a["median_agent_wall_time_seconds"] == 38.0
    assert a["median_total_log_bytes"] == 14000.0
    assert a["median_estimated_total_observed_tokens"] == 4400.0
    assert a["median_changed_scored_files"] == 1.0
    assert a["median_line_churn"] == 9.0

    b = rep["tasks"][1]
    assert b["trials"] == 1
    assert b["success_rate"] == 0.0
    assert b["median_line_churn"] == 20.0


def test_calibration_report_empty_condition(tmp_path):
    rep = calibration_report(tmp_path, "nope")
    assert rep == {"condition_id": "nope", "tasks": []}
