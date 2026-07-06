from pathlib import Path

from tokenbench.doctor.suite_doctor import doctor_suite

ROOT = Path(__file__).resolve().parents[1]
HARD_SUITE = ROOT / "benchmark/suites/v0_5_hard.json"


def test_hard_suite_has_ten_valid_tasks():
    report = doctor_suite(HARD_SUITE, ROOT)
    assert report["suite_id"] == "v0_5_hard"
    assert report["tasks_total"] == 10
    assert report["tasks_valid"] == 10, [t for t in report["tasks"] if t["errors"]]
    assert report["tasks_invalid"] == 0
    assert report["errors_total"] == 0
