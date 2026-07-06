from pathlib import Path

import pytest

from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "benchmark/manifests/pulseboard-saas"
MANIFESTS = sorted(MANIFEST_DIR.glob("*.json"))


def test_pulseboard_tasks_exist():
    # 5 original lite tasks + 5 hard tasks + 3 V0.7 tasks
    # (1 reorg + a 2-stage adjustments/refunds group).
    assert len(MANIFESTS) == 13


@pytest.mark.parametrize("manifest", MANIFESTS, ids=lambda p: p.stem)
def test_pulseboard_task_valid(manifest):
    report = doctor_task(manifest, ROOT)
    assert report["status"] == "valid", report["errors"]
    assert report["gold_visible_passed"] is True
    assert report["gold_hidden_passed"] is True
    assert report["broken_hidden_passed"] is False
