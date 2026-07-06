from pathlib import Path

import pytest

from tokenbench.doctor.hardness import audit_task
from tokenbench.manifests.loader import load_manifest
from tokenbench.suites.loader import load_suite

ROOT = Path(__file__).resolve().parents[1]
HARD_SUITE = ROOT / "benchmark/suites/v0_5_hard.json"

SUITE = load_suite(HARD_SUITE)
TASK_RELS = list(SUITE.tasks)


def test_hard_suite_has_ten_tasks():
    assert len(TASK_RELS) == 10


@pytest.mark.parametrize("task_rel", TASK_RELS, ids=lambda p: Path(p).stem)
def test_hard_task_has_at_least_six_hidden_cases(task_rel):
    # V0.5.1 raised the floor to 6: a hard task needs enough hidden cases that a
    # plausible partial fix drops 2+ and falls below the 0.9 success gate.
    manifest = load_manifest(ROOT / task_rel)
    report = audit_task(manifest, ROOT)
    assert report["hidden_test_count"] >= 6, (
        manifest.task_id,
        report["hidden_test_count"],
    )


@pytest.mark.parametrize("task_rel", TASK_RELS, ids=lambda p: Path(p).stem)
def test_hard_task_requires_multiple_root_cause_files(task_rel):
    manifest = load_manifest(ROOT / task_rel)
    report = audit_task(manifest, ROOT)
    assert report["root_cause_file_count"] >= 2, manifest.task_id
    assert (report["expected_changed_files_max"] or 0) >= 2, manifest.task_id
