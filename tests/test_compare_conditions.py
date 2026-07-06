import json
from pathlib import Path

from tokenbench.analysis.compare import compare_conditions


def _write_score(runs_dir: Path, run_id, condition_id, repo_id, task_id, trial,
                 quality, efficiency, final):
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    score = {
        "run_id": run_id,
        "condition_id": condition_id,
        "trial_index": trial,
        "repo_id": repo_id,
        "task_id": task_id,
        "quality_score": quality,
        "efficiency_score": efficiency,
        "final_score": final,
    }
    (d / "score.json").write_text(json.dumps(score), encoding="utf-8")


def _fixture(runs_dir: Path):
    # task t1: B beats A. task t2: A beats B.
    _write_score(runs_dir, "a1", "A", "m", "t1", 0, 80.0, 60.0, 70.0)
    _write_score(runs_dir, "b1", "B", "m", "t1", 0, 84.0, 66.0, 75.0)
    _write_score(runs_dir, "a2", "A", "m", "t2", 0, 90.0, 70.0, 80.0)
    _write_score(runs_dir, "b2", "B", "m", "t2", 0, 88.0, 64.0, 76.0)
    # unpaired cell for B only -> ignored.
    _write_score(runs_dir, "b3", "B", "m", "t3", 0, 50.0, 50.0, 50.0)


def test_compare_paired(tmp_path):
    _fixture(tmp_path)
    out = compare_conditions(tmp_path, "A", "B")
    assert out["condition_a"] == "A"
    assert out["condition_b"] == "B"
    assert out["paired_tasks"] == 2
    # final deltas (B-A): t1 +5, t2 -4 -> mean 0.5
    assert out["mean_final_delta"] == 0.5
    # quality deltas: +4, -2 -> 1.0
    assert out["mean_quality_delta"] == 1.0
    # efficiency deltas: +6, -6 -> 0.0
    assert out["mean_efficiency_delta"] == 0.0
    assert out["wins_b"] == 1
    assert out["wins_a"] == 1
    assert out["ties"] == 0
    assert out["final_delta_pvalue"] is None


def test_compare_no_overlap(tmp_path):
    _write_score(tmp_path, "a1", "A", "m", "t1", 0, 80.0, 60.0, 70.0)
    _write_score(tmp_path, "b1", "B", "m", "t2", 0, 80.0, 60.0, 70.0)
    out = compare_conditions(tmp_path, "A", "B")
    assert out["paired_tasks"] == 0
    assert out["mean_final_delta"] == 0.0
