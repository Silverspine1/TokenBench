from pathlib import Path

from tokenbench.manifests.loader import load_manifest
from tokenbench.scoring.scorer import build_score

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"

EMPTY_CHANGES = {
    "added": [],
    "modified": [],
    "deleted": [],
    "forbidden_modified": [],
    "ignored_modified": [],
    "scored_modified": [],
}


def _cmd(passed: bool):
    return {
        "command": "pytest",
        "exit_code": 0 if passed else 1,
        "passed": passed,
        "timed_out": False,
        "wall_time_seconds": 0.0,
        "stdout_log": "logs/x",
        "stderr_log": "logs/y",
        "stdout_bytes": 0,
        "stderr_bytes": 0,
    }


def _run_state(visible, hidden):
    return {
        "run_id": "test_run",
        "runner": "cli-agent",
        "agent": {"stdout_bytes": 0, "stderr_bytes": 0, "wall_time_seconds": 0.0, "timed_out": False},
        "visible": visible,
        "hidden": hidden,
        "paths": {"run_dir": "runs/test_run"},
    }


def test_success_true_when_hidden_passes():
    manifest = load_manifest(MARKETLAB)
    report = build_score(_run_state([_cmd(True)], [_cmd(True)]), manifest, EMPTY_CHANGES, 0)
    assert report["success"] is True
    assert report["success_policy"]["quality_threshold"] == 80.0
    assert report["success_policy"]["hidden_pass_rate_threshold"] == 0.9


def test_success_false_when_hidden_fails():
    manifest = load_manifest(MARKETLAB)
    report = build_score(_run_state([_cmd(True)], [_cmd(False)]), manifest, EMPTY_CHANGES, 0)
    assert report["success"] is False


def test_success_false_when_forbidden_path_modified():
    manifest = load_manifest(MARKETLAB)
    changes = dict(EMPTY_CHANGES, forbidden_modified=["tests/test_x.py"])
    report = build_score(_run_state([_cmd(True)], [_cmd(True)]), manifest, changes, 0)
    assert report["success"] is False
