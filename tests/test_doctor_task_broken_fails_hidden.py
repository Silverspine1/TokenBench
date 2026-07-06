from pathlib import Path

from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_broken_snapshot_fails_at_least_one_hidden_test():
    report = doctor_task(MANIFEST, ROOT)
    # The broken snapshot must fail >=1 hidden test for the task to be admitted.
    assert report["broken_hidden_passed"] is False
    assert report["hidden_failure_required"] is True
    assert report["status"] == "valid"
