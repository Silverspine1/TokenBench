import json
from pathlib import Path

import pytest

from tokenbench.manifests.loader import load_manifest
from tokenbench.manifests.validator import validate_manifest

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_loads_valid_manifest():
    manifest = load_manifest(MARKETLAB)
    assert manifest.task_id == "marketlab_fee_slippage_001"
    assert manifest.repo_id == "marketlab-ml"
    assert validate_manifest(manifest, ROOT) == []


def test_rejects_missing_broken_snapshot(tmp_path):
    data = json.loads(MARKETLAB.read_text())
    data["broken_snapshot"] = "benchmark/repos/does-not-exist"
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data))
    manifest = load_manifest(p)
    errors = validate_manifest(manifest, ROOT)
    assert any("broken_snapshot does not exist" in e for e in errors)


def test_rejects_empty_hidden_commands(tmp_path):
    data = json.loads(MARKETLAB.read_text())
    data["hidden_commands"] = []
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data))
    manifest = load_manifest(p)
    errors = validate_manifest(manifest, ROOT)
    assert any("at least one hidden command" in e for e in errors)
