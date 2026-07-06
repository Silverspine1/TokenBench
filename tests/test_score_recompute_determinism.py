import json
from pathlib import Path

from tokenbench.analysis.aggregate import aggregate_runs
from tokenbench.analysis.compare import compare_conditions
from tokenbench.manifests.loader import load_manifest
from tokenbench.scoring.scorer import score_run

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"

EMPTY_CHANGES = {
    "added": [],
    "modified": ["marketlab/backtest.py"],
    "deleted": [],
    "forbidden_modified": [],
    "ignored_modified": [],
    "scored_modified": ["marketlab/backtest.py"],
}


def _cmd(passed, parsed=None):
    return {
        "command": "pytest -q",
        "exit_code": 0 if passed else 1,
        "passed": passed,
        "timed_out": False,
        "wall_time_seconds": 1.5,
        "stdout_log": "logs/x",
        "stderr_log": "logs/y",
        "stdout_bytes": 1234,
        "stderr_bytes": 0,
        "parsed": parsed,
    }


def _build_run(run_dir: Path):
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    for name in (
        "agent.stdout.log", "agent.stderr.log",
        "visible_tests.stdout.log", "visible_tests.stderr.log",
        "hidden_tests.stdout.log", "hidden_tests.stderr.log",
    ):
        (run_dir / "logs" / name).write_text("", encoding="utf-8")

    run_state = {
        "run_id": "det_run",
        "condition_id": "claude_code_baseline",
        "trial_index": 0,
        "runner": "manual",
        "agent": {"stdout_bytes": 100, "stderr_bytes": 0, "wall_time_seconds": 5.0, "timed_out": False},
        "visible": [_cmd(True, {"framework": "pytest", "command": "pytest", "command_passed": True,
                                "tests_total": 4, "tests_passed": 4, "tests_failed": 0,
                                "tests_skipped": 0, "parse_confidence": "structured"})],
        "hidden": [_cmd(True, {"framework": "pytest", "command": "pytest", "command_passed": True,
                               "tests_total": 4, "tests_passed": 3, "tests_failed": 1,
                               "tests_skipped": 0, "parse_confidence": "structured"})],
        "paths": {"run_dir": "runs/det_run"},
    }
    (run_dir / "run_state.json").write_text(json.dumps(run_state, indent=2), encoding="utf-8")
    (run_dir / "file_changes.json").write_text(json.dumps(EMPTY_CHANGES, indent=2), encoding="utf-8")


def test_score_recompute_is_byte_identical(tmp_path):
    rd = tmp_path / "det_run"
    _build_run(rd)
    manifest = load_manifest(MARKETLAB)

    score_run(rd, manifest)
    first = (rd / "score.json").read_bytes()
    score_run(rd, manifest)
    second = (rd / "score.json").read_bytes()
    assert first == second


def test_score_recompute_structured_components_present(tmp_path):
    rd = tmp_path / "det_run"
    _build_run(rd)
    manifest = load_manifest(MARKETLAB)
    report = score_run(rd, manifest)

    assert report["hidden_tests"]["tests_total"] == 4
    assert report["hidden_tests"]["tests_passed"] == 3
    assert "wall_time_score" in report["efficiency_components"]
    assert "artifact_integrity_score" in report["quality_components"]


def _two_conditions(runs_dir: Path):
    for rid, cid, task, q, e, f in [
        ("r1", "A", "t1", 90.0, 60.0, 75.0),
        ("r2", "A", "t2", 70.0, 80.0, 70.0),
        ("r3", "B", "t1", 88.0, 50.0, 72.0),
        ("r4", "B", "t2", 60.0, 90.0, 70.0),
    ]:
        d = runs_dir / rid
        d.mkdir(parents=True, exist_ok=True)
        (d / "score.json").write_text(json.dumps({
            "run_id": rid, "condition_id": cid, "trial_index": 0,
            "repo_id": "m", "task_id": task,
            "quality_score": q, "efficiency_score": e, "final_score": f,
            "timing": {"total_wall_time_seconds": 1.0},
            "usage_proxy": {"total_log_bytes": 10},
        }), encoding="utf-8")


def test_aggregate_ordering_is_stable(tmp_path):
    _two_conditions(tmp_path)
    assert aggregate_runs(tmp_path) == aggregate_runs(tmp_path)


def test_compare_ordering_is_stable(tmp_path):
    _two_conditions(tmp_path)
    a = compare_conditions(tmp_path, "A", "B")
    b = compare_conditions(tmp_path, "A", "B")
    assert a == b
