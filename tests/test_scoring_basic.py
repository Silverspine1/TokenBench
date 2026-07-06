from pathlib import Path

from tokenbench.manifests.loader import load_manifest
from tokenbench.scoring.efficiency import composite_efficiency, efficiency_components
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


def _cmd(passed: bool, *, stdout=0, stderr=0, wall=0.0, timed_out=False):
    return {
        "command": "pytest",
        "exit_code": 0 if passed else 1,
        "passed": passed,
        "timed_out": timed_out,
        "wall_time_seconds": wall,
        "stdout_log": "logs/x",
        "stderr_log": "logs/y",
        "stdout_bytes": stdout,
        "stderr_bytes": stderr,
    }


def _run_state(visible, hidden, agent=None):
    return {
        "run_id": "test_run",
        "runner": "manual",
        "agent": agent or {"stdout_bytes": 0, "stderr_bytes": 0, "wall_time_seconds": 0.0, "timed_out": False},
        "visible": visible,
        "hidden": hidden,
        "paths": {"run_dir": "runs/test_run"},
    }


def test_passing_hidden_command_gives_high_quality():
    manifest = load_manifest(MARKETLAB)
    rs = _run_state([_cmd(True)], [_cmd(True)])
    report = build_score(rs, manifest, EMPTY_CHANGES, 0)
    assert report["quality_score"] == 100.0


def test_failing_hidden_command_gives_low_quality():
    # V0.2: hidden fails (0.85*0), visible passes (0.10*100), empty patch with
    # failing hidden drops artifact integrity to 90 (0.05*90) => 14.5.
    manifest = load_manifest(MARKETLAB)
    rs = _run_state([_cmd(True)], [_cmd(False)])
    report = build_score(rs, manifest, EMPTY_CHANGES, 0)
    assert report["quality_score"] == 14.5
    assert report["quality_components"]["artifact_integrity_score"] == 90.0


def test_forbidden_path_modified_zeroes_quality():
    manifest = load_manifest(MARKETLAB)
    changes = dict(EMPTY_CHANGES, forbidden_modified=["tests/test_x.py"])
    rs = _run_state([_cmd(True)], [_cmd(True)])
    report = build_score(rs, manifest, changes, 0)
    assert report["quality_score"] == 0.0


def test_final_score_uses_gated_efficiency_formula():
    manifest = load_manifest(MARKETLAB)
    rs = _run_state(
        [_cmd(True, stdout=1000, wall=1.0)],
        [_cmd(True, stdout=1000, wall=1.0)],
        agent={"stdout_bytes": 5000, "stderr_bytes": 0, "wall_time_seconds": 10.0, "timed_out": False},
    )
    report = build_score(rs, manifest, EMPTY_CHANGES, 0)

    q = report["quality_score"]
    total_bytes = report["usage_proxy"]["total_log_bytes"]
    total_wall = report["timing"]["total_wall_time_seconds"]
    components = efficiency_components(
        total_wall_time_seconds=total_wall,
        allowed_runtime_seconds=manifest.allowed_runtime_seconds,
        total_log_bytes=total_bytes,
        log_budget_bytes=manifest.log_budget_bytes,
        changed_scored_files=0,
        dependency_download_events=0,
    )
    eff = composite_efficiency(components)
    expected_gated = round(eff * min(q / 80.0, 1.0), 4)
    expected_final = round(0.5 * q + 0.5 * (eff * min(q / 80.0, 1.0)), 4)

    assert report["efficiency_score"] == round(eff, 4)
    assert report["efficiency_components"] == components
    assert report["efficiency_gated"] == expected_gated
    assert report["final_score"] == expected_final
