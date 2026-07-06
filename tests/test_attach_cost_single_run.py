"""attach-cost writes manual provider cost/usage into one run's telemetry."""

import json
from pathlib import Path

import pytest

from tokenbench.telemetry.cost_import import attach_cost_to_run


def _run(tmp_path: Path, run_id="r1") -> Path:
    d = tmp_path / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "telemetry.json").write_text(json.dumps({
        "run_id": run_id, "repo_id": "m", "task_id": "t1",
        "token_estimates": {"total_observed_tokens": 640},
        "provider_usage": {"available": False, "source": None, "cost_usd": None},
    }), encoding="utf-8")
    return d


def test_attach_cost_marks_manual_and_fills_fields(tmp_path):
    d = _run(tmp_path)
    attach_cost_to_run(d, {
        "cost_usd": 0.123, "input_tokens": 10000, "output_tokens": 2000,
        "reasoning_tokens": 3000,
    })
    pu = json.loads((d / "telemetry.json").read_text(encoding="utf-8"))["provider_usage"]
    assert pu["available"] is True
    assert pu["source"] == "manual"
    assert pu["cost_usd"] == 0.123
    assert pu["input_tokens"] == 10000
    assert pu["output_tokens"] == 2000
    assert pu["reasoning_tokens"] == 3000
    # total defaults to the sum of supplied token parts when not given.
    assert pu["total_tokens"] == 15000


def test_explicit_total_tokens_wins(tmp_path):
    d = _run(tmp_path)
    attach_cost_to_run(d, {"cost_usd": 0.05, "input_tokens": 100,
                           "output_tokens": 200, "total_tokens": 999})
    pu = json.loads((d / "telemetry.json").read_text(encoding="utf-8"))["provider_usage"]
    assert pu["total_tokens"] == 999


def test_estimates_untouched_by_attach(tmp_path):
    d = _run(tmp_path)
    attach_cost_to_run(d, {"cost_usd": 0.05})
    tel = json.loads((d / "telemetry.json").read_text(encoding="utf-8"))
    # The attach path must not derive cost from, or alter, the estimates.
    assert tel["token_estimates"]["total_observed_tokens"] == 640


def test_missing_telemetry_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        attach_cost_to_run(tmp_path / "nope", {"cost_usd": 0.1})
