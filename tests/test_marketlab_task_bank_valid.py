from pathlib import Path

import pytest

from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "benchmark/manifests/marketlab-ml"
MANIFESTS = sorted(MANIFEST_DIR.glob("*.json"))


def test_marketlab_tasks_exist():
    # 5 lite + 5 hard + 3 V0.7 (1 reorg + a 2-stage walk-forward group).
    assert len(MANIFESTS) == 13


@pytest.mark.parametrize("manifest", MANIFESTS, ids=lambda p: p.stem)
def test_marketlab_task_valid(manifest):
    report = doctor_task(manifest, ROOT)
    assert report["status"] == "valid", report["errors"]
    assert report["gold_visible_passed"] is True
    assert report["gold_hidden_passed"] is True
    assert report["broken_hidden_passed"] is False
