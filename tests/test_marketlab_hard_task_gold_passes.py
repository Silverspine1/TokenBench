from pathlib import Path

import pytest

from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "benchmark/manifests/marketlab-ml"

HARD_TASKS = [
    "marketlab_cost_contract_001.json",
    "marketlab_multi_asset_split_001.json",
    "marketlab_warmup_alignment_001.json",
    "marketlab_walkforward_eval_001.json",
    "marketlab_report_consistency_001.json",
]


@pytest.mark.parametrize("name", HARD_TASKS, ids=lambda n: n[:-5])
def test_marketlab_hard_gold_passes_visible_and_hidden(name):
    report = doctor_task(MANIFEST_DIR / name, ROOT)
    assert report["status"] == "valid", report["errors"]
    assert report["gold_visible_passed"] is True
    assert report["gold_hidden_passed"] is True
