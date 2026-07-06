import json
from pathlib import Path

from tokenbench.manifests.loader import load_manifest
from tokenbench.scoring.scorer import score_run

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"

CHANGES = {
    "added": [],
    "modified": ["marketlab/backtest.py"],
    "deleted": [],
    "forbidden_modified": [],
    "ignored_modified": [],
    "scored_modified": ["marketlab/backtest.py"],
}


def _cmd(passed):
    return {
        "command": "pytest -q",
        "exit_code": 0 if passed else 1,
        "passed": passed,
        "timed_out": False,
        "wall_time_seconds": 1.0,
        "stdout_bytes": 10,
        "stderr_bytes": 0,
        "parsed": None,
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
        "run_id": "link_run",
        "condition_id": "claude_code_baseline",
        "trial_index": 0,
        "runner": "manual",
        "agent": {"stdout_bytes": 10, "stderr_bytes": 0, "wall_time_seconds": 3.0, "timed_out": False},
        "visible": [_cmd(True)],
        "hidden": [_cmd(True)],
        "paths": {"run_dir": "runs/link_run"},
    }
    (run_dir / "run_state.json").write_text(json.dumps(run_state), encoding="utf-8")
    (run_dir / "file_changes.json").write_text(json.dumps(CHANGES), encoding="utf-8")
    (run_dir / "patch.diff").write_text(
        "--- a/marketlab/backtest.py\n"
        "+++ b/marketlab/backtest.py\n"
        "@@ -1 +1,2 @@\n"
        "-old\n+new\n+extra\n",
        encoding="utf-8",
    )


def test_score_links_and_writes_telemetry(tmp_path):
    rd = tmp_path / "link_run"
    _build_run(rd)
    manifest = load_manifest(MARKETLAB)

    report = score_run(rd, manifest)

    # score.json carries provisional efficiency labelling + telemetry link.
    assert report["telemetry_path"] == "telemetry.json"
    assert report["efficiency_score_kind"] == "proxy_v0_2"
    # Backward-compatible alias preserved alongside the original field.
    assert report["efficiency_proxy_score"] == report["efficiency_score"]

    assert (rd / "telemetry.json").exists()
    tel = json.loads((rd / "telemetry.json").read_text(encoding="utf-8"))
    # Patch line churn captured from patch.diff (+new +extra -old).
    assert tel["patch"]["lines_added"] == 2
    assert tel["patch"]["lines_deleted"] == 1
    assert tel["patch"]["line_churn"] == 3
    assert tel["patch"]["changed_scored_files"] == 1
