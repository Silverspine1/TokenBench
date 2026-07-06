import json
from pathlib import Path

from tokenbench.analysis.aggregate import aggregate_runs
from tokenbench.analysis.compare import compare_conditions


def _write_score(runs_dir: Path, run_id, condition_id, task_id, success, trial=0):
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    score = {
        "run_id": run_id,
        "condition_id": condition_id,
        "trial_index": trial,
        "repo_id": "m",
        "task_id": task_id,
        "success": success,
        "quality_score": 90.0 if success else 10.0,
        "efficiency_score": 50.0,
        "final_score": 70.0 if success else 20.0,
        "timing": {"total_wall_time_seconds": 1.0},
        "usage_proxy": {"total_log_bytes": 10},
    }
    (d / "score.json").write_text(json.dumps(score), encoding="utf-8")


def test_aggregate_reports_success_rate(tmp_path):
    _write_score(tmp_path, "r1", "A", "t1", True)
    _write_score(tmp_path, "r2", "A", "t2", False)
    _write_score(tmp_path, "r3", "A", "t3", True)
    out = aggregate_runs(tmp_path)
    assert len(out) == 1
    assert out[0]["condition_id"] == "A"
    assert out[0]["success_rate"] == round(2 / 3, 4)


def test_aggregate_missing_success_treated_as_failure(tmp_path):
    d = tmp_path / "r1"
    d.mkdir()
    (d / "score.json").write_text(
        json.dumps({"run_id": "r1", "condition_id": "A", "repo_id": "m", "task_id": "t1"}),
        encoding="utf-8",
    )
    out = aggregate_runs(tmp_path)
    assert out[0]["success_rate"] == 0.0


def test_compare_reports_success_deltas(tmp_path):
    # task t1: A succeeds, B fails. task t2: A fails, B succeeds.
    _write_score(tmp_path, "a1", "A", "t1", True)
    _write_score(tmp_path, "b1", "B", "t1", False)
    _write_score(tmp_path, "a2", "A", "t2", False)
    _write_score(tmp_path, "b2", "B", "t2", True)
    out = compare_conditions(tmp_path, "A", "B")
    assert out["paired_tasks"] == 2
    assert out["mean_success_delta"] == 0.0
    assert out["success_rate_a"] == 0.5
    assert out["success_rate_b"] == 0.5
