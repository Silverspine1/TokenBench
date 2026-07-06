from pathlib import Path

from tokenbench.doctor.suite_doctor import doctor_suite

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "benchmark/suites/v0_5_lite.json"


def test_suite_doctor_all_tasks_valid():
    report = doctor_suite(SUITE, ROOT)
    assert report["tasks_total"] == 10
    assert report["tasks_valid"] == 10
    assert report["tasks_invalid"] == 0
    assert report["errors_total"] == 0
    assert report["status"] == "valid"
