import json
from pathlib import Path

from tokenbench.analysis.aggregate import aggregate_runs


def _write_score(runs_dir: Path, run_id: str, **fields) -> None:
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    score = {
        "run_id": run_id,
        "condition_id": fields.get("condition_id", "unspecified"),
        "trial_index": fields.get("trial_index", 0),
        "repo_id": fields.get("repo_id", "repo"),
        "task_id": fields.get("task_id", "task"),
        "quality_score": fields.get("quality_score", 0.0),
        "efficiency_score": fields.get("efficiency_score", 0.0),
        "final_score": fields.get("final_score", 0.0),
        "timing": {"total_wall_time_seconds": fields.get("wall", 0.0)},
        "usage_proxy": {"total_log_bytes": fields.get("log_bytes", 0)},
    }
    (d / "score.json").write_text(json.dumps(score), encoding="utf-8")


def _fixture(runs_dir: Path) -> None:
    _write_score(runs_dir, "r1", condition_id="A", repo_id="m", task_id="t1",
                 quality_score=90.0, efficiency_score=60.0, final_score=75.0, wall=400.0, log_bytes=100000)
    _write_score(runs_dir, "r2", condition_id="A", repo_id="m", task_id="t2",
                 quality_score=70.0, efficiency_score=80.0, final_score=70.0, wall=600.0, log_bytes=300000)
    _write_score(runs_dir, "r3", condition_id="B", repo_id="m", task_id="t1",
                 quality_score=88.0, efficiency_score=50.0, final_score=72.0, wall=420.0, log_bytes=180000)


def test_aggregate_groups_by_condition(tmp_path):
    _fixture(tmp_path)
    out = aggregate_runs(tmp_path)
    assert [g["condition_id"] for g in out] == ["A", "B"]

    a = out[0]
    assert a["tasks_attempted"] == 2
    assert a["trials_total"] == 2
    assert a["mean_quality_score"] == 80.0
    assert a["mean_efficiency_score"] == 70.0
    assert a["mean_final_score"] == 72.5
    assert a["success_rate_quality_80"] == 0.5  # only one of two >= 80
    assert a["mean_wall_time_seconds"] == 500.0
    assert a["mean_total_log_bytes"] == 200000.0


def test_aggregate_empty_dir(tmp_path):
    assert aggregate_runs(tmp_path) == []
