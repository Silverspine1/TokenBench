from pathlib import Path

import pytest

from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "benchmark/manifests/vaultdesk-tauri"
MANIFESTS = sorted(MANIFEST_DIR.glob("*.json"))


def test_vaultdesk_tasks_exist():
    # 5 atomic V0.8 tasks + 2 reorg + 2 staged groups (4 stage manifests).
    assert len(MANIFESTS) == 11


@pytest.mark.parametrize("manifest", MANIFESTS, ids=lambda p: p.stem)
def test_vaultdesk_task_valid(manifest):
    # Rust-backed: doctor builds via cargo (slow on a cold cache).
    report = doctor_task(manifest, ROOT)
    assert report["status"] == "valid", report["errors"]
    assert report["gold_visible_passed"] is True
    assert report["gold_hidden_passed"] is True
    assert report["broken_hidden_passed"] is False
