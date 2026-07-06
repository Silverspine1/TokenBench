from pathlib import Path

from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_gold_passes_visible_and_hidden():
    report = doctor_task(MANIFEST, ROOT)
    assert report["status"] == "valid"
    assert report["gold_visible_passed"] is True
    assert report["gold_hidden_passed"] is True
    assert report["errors"] == []
