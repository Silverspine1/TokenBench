from pathlib import Path

from tokenbench.doctor.task_doctor import (
    _check_snapshot_artifacts,
    scan_generated_artifacts,
)
from tokenbench.manifests.loader import load_manifest

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def _make_tree(base: Path, files: dict[str, str]):
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def test_scan_reports_top_level_generated_dirs(tmp_path):
    _make_tree(
        tmp_path,
        {
            "marketlab/backtest.py": "x\n",
            "marketlab_ml.egg-info/PKG-INFO": "x\n",
            "marketlab/__pycache__/x.pyc": "x\n",
            ".pytest_cache/v/cache/lastfailed": "{}\n",
        },
    )
    found = scan_generated_artifacts(tmp_path)
    assert "marketlab_ml.egg-info" in found
    assert "marketlab/__pycache__" in found
    assert ".pytest_cache" in found
    # Nested cache children are not reported separately.
    assert ".pytest_cache/v/cache" not in found


def test_scan_clean_snapshot_has_no_findings(tmp_path):
    _make_tree(tmp_path, {"marketlab/backtest.py": "x\n", "pyproject.toml": "x\n"})
    assert scan_generated_artifacts(tmp_path) == []


def test_check_snapshot_artifacts_emits_warnings(tmp_path):
    manifest = load_manifest(MARKETLAB).model_copy(
        update={"gold_snapshot": "gold", "broken_snapshot": "broken"}
    )
    _make_tree(tmp_path / "gold", {"marketlab/backtest.py": "x\n"})
    _make_tree(
        tmp_path / "broken",
        {"marketlab/backtest.py": "x\n", "marketlab_ml.egg-info/PKG-INFO": "x\n"},
    )

    warnings: list[str] = []
    _check_snapshot_artifacts(manifest, tmp_path, warnings)

    assert len(warnings) == 1
    assert "broken snapshot" in warnings[0]
    assert "marketlab_ml.egg-info" in warnings[0]
    # Clean gold produces no warning.
    assert not any("gold snapshot" in w for w in warnings)
