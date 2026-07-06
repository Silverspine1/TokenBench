from pathlib import Path

import pytest

from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "benchmark/manifests/pulseboard-saas"

HARD_TASKS = [
    "pulseboard_filter_export_contract_001.json",
    "pulseboard_datefilter_boundary_001.json",
    "pulseboard_status_summary_001.json",
    "pulseboard_api_adapter_001.json",
    "pulseboard_cache_invalidation_001.json",
]


@pytest.mark.parametrize("name", HARD_TASKS, ids=lambda n: n[:-5])
def test_pulseboard_hard_broken_fails_at_least_one_hidden(name):
    report = doctor_task(MANIFEST_DIR / name, ROOT)
    assert report["status"] == "valid", report["errors"]
    # The planted bug must be caught: broken snapshot fails >=1 hidden test.
    assert report["broken_hidden_passed"] is False
