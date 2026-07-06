from pathlib import Path

import pytest

from tokenbench.core.hashing import hash_directory
from tokenbench.core.paths import RunPaths
from tokenbench.core.workspace import WorkspaceExistsError, materialize_workspace
from tokenbench.manifests.loader import load_manifest

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def _manifest():
    return load_manifest(MARKETLAB)


def test_copies_broken_snapshot(tmp_path):
    manifest = _manifest()
    rp = RunPaths(tmp_path / "run")
    materialize_workspace(manifest, rp, ROOT)
    assert (rp.workspace / "marketlab" / "backtest.py").exists()


def test_does_not_modify_source_snapshot(tmp_path):
    manifest = _manifest()
    src = (ROOT / manifest.broken_snapshot)
    before = hash_directory(src)
    rp = RunPaths(tmp_path / "run")
    materialize_workspace(manifest, rp, ROOT)
    # Mutate the workspace copy.
    (rp.workspace / "marketlab" / "backtest.py").write_text("# changed\n")
    after = hash_directory(src)
    assert before == after


def test_creates_metadata(tmp_path):
    manifest = _manifest()
    rp = RunPaths(tmp_path / "run")
    meta = materialize_workspace(manifest, rp, ROOT)
    assert rp.metadata.exists()
    assert meta["task_id"] == manifest.task_id
    assert meta["repo_id"] == manifest.repo_id
    assert "source_snapshot_hash" in meta
    assert "start_time" in meta


def test_refuses_existing_workspace(tmp_path):
    manifest = _manifest()
    rp = RunPaths(tmp_path / "run")
    materialize_workspace(manifest, rp, ROOT)
    with pytest.raises(WorkspaceExistsError):
        materialize_workspace(manifest, rp, ROOT)
    # Overwrite is allowed.
    materialize_workspace(manifest, rp, ROOT, overwrite=True)


def test_hashes_directory_deterministically(tmp_path):
    src = (ROOT / _manifest().broken_snapshot)
    assert hash_directory(src) == hash_directory(src)
