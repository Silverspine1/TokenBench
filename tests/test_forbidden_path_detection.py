from pathlib import Path

from tokenbench.core.artifacts import compute_file_changes
from tokenbench.manifests.loader import load_manifest
from tokenbench.scoring.scorer import build_score

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def _cmd(passed):
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


def _run_state(changes_unused=None):
    return {
        "run_id": "r",
        "runner": "manual",
        "agent": {"stdout_bytes": 0, "stderr_bytes": 0, "wall_time_seconds": 0.0, "timed_out": False},
        "visible": [_cmd(True)],
        "hidden": [_cmd(True)],
        "paths": {"run_dir": "runs/r"},
    }


def _make_tree(base: Path, files: dict[str, str]):
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def test_modifying_forbidden_file_makes_quality_zero(tmp_path):
    manifest = load_manifest(MARKETLAB)
    broken = tmp_path / "broken"
    candidate = tmp_path / "candidate"
    _make_tree(broken, {"marketlab/backtest.py": "ok\n", "tests/secret.py": "a\n"})
    _make_tree(candidate, {"marketlab/backtest.py": "ok\n", "tests/secret.py": "TAMPERED\n"})

    changes = compute_file_changes(broken, candidate, manifest)
    assert "tests/secret.py" in changes["forbidden_modified"]

    report = build_score(_run_state(), manifest, changes, 0)
    assert report["penalties"]["forbidden_path_modified"] is True
    assert report["quality_score"] == 0.0


def test_modifying_ignored_file_is_recorded_not_fatal(tmp_path):
    manifest = load_manifest(MARKETLAB)
    broken = tmp_path / "broken"
    candidate = tmp_path / "candidate"
    _make_tree(broken, {"marketlab/backtest.py": "ok\n", "docs/readme.md": "a\n"})
    _make_tree(candidate, {"marketlab/backtest.py": "ok\n", "docs/readme.md": "CHANGED\n"})

    changes = compute_file_changes(broken, candidate, manifest)
    assert "docs/readme.md" in changes["ignored_modified"]
    assert changes["forbidden_modified"] == []

    report = build_score(_run_state(), manifest, changes, 0)
    assert report["penalties"]["forbidden_path_modified"] is False
    # V0.2: ignored-file mod is non-fatal but costs 10 of artifact integrity:
    # 0.85*100 + 0.10*100 + 0.05*90 = 99.5 (vs 0 for a forbidden mod).
    assert report["quality_components"]["artifact_integrity_score"] == 90.0
    assert report["quality_score"] == 99.5
