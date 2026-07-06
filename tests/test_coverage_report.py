from pathlib import Path

from tokenbench.doctor.coverage import build_coverage

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "benchmark/suites/v0_5_lite.json"


def test_coverage_counts():
    cov = build_coverage(SUITE, ROOT)
    assert cov["tasks_total"] == 10
    assert cov["repo_id"] == {"marketlab-ml": 5, "pulseboard-saas": 5}
    # Every task contributes a category and difficulty.
    assert sum(cov["category"].values()) == 10
    assert sum(cov["difficulty"].values()) == 10
    # Categories are not all bugfix — the suite has implementation and contract too.
    assert cov["category"].get("implementation", 0) >= 1
    assert cov["category"].get("contract", 0) >= 1
    # Difficulty spread includes the frontier-hard task.
    assert cov["difficulty"].get("frontier_hard", 0) == 1
    assert cov["skills_tested"]  # non-empty
