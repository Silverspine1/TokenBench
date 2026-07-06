from pathlib import Path

from tokenbench.doctor.hardness import audit_suite

ROOT = Path(__file__).resolve().parents[1]
HARD_SUITE = ROOT / "benchmark/suites/v0_5_hard.json"
SMOKE_SUITE = ROOT / "benchmark/suites/v0_5_smoke.json"


def test_hard_suite_has_no_hardness_warnings():
    report = audit_suite(HARD_SUITE, ROOT)
    assert report["warnings_total"] == 0, [
        (t["task_id"], t["warnings"]) for t in report["tasks"] if t["warnings"]
    ]


def test_smoke_suite_is_flagged_as_too_easy():
    # The audit must actually discriminate: the smoke suite's hard-labelled
    # single-file tasks should raise warnings.
    report = audit_suite(SMOKE_SUITE, ROOT)
    assert report["warnings_total"] > 0
