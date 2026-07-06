from pathlib import Path

import pytest

from tokenbench.suites.loader import load_suite

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "benchmark" / "suites" / "v0_5_lite.json"


def test_loads_v0_5_lite():
    s = load_suite(SUITE)
    assert s.suite_id == "v0_5_lite"
    assert len(s.tasks) == 10
    assert s.required_trials == 2
    assert s.official is False


def test_suite_task_paths_exist():
    s = load_suite(SUITE)
    for t in s.tasks:
        assert (ROOT / t).exists(), t


def test_rejects_empty_tasks(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('{"suite_id":"x","tasks":[]}', encoding="utf-8")
    with pytest.raises(Exception):
        load_suite(p)
