"""attach-cost-csv batch-attaches provider cost/usage keyed by run_id."""

import json
from pathlib import Path

from tokenbench.telemetry.cost_import import attach_cost_csv

CSV_HEADER = (
    "run_id,cost_usd,input_tokens,output_tokens,"
    "cache_read_tokens,cache_write_tokens,reasoning_tokens,total_tokens"
)


def _run(runs_dir: Path, run_id: str) -> Path:
    d = runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "telemetry.json").write_text(json.dumps({
        "run_id": run_id, "provider_usage": {"available": False},
    }), encoding="utf-8")
    return d


def _pu(runs_dir: Path, run_id: str) -> dict:
    return json.loads((runs_dir / run_id / "telemetry.json").read_text(
        encoding="utf-8"))["provider_usage"]


def test_csv_attaches_multiple_runs(tmp_path):
    runs = tmp_path / "runs"
    _run(runs, "a")
    _run(runs, "b")
    csv_path = tmp_path / "costs.csv"
    csv_path.write_text(
        CSV_HEADER + "\n"
        "a,0.123,10000,2000,0,0,3000,15000\n"
        "b,0.456,20000,4000,0,0,0,24000\n",
        encoding="utf-8",
    )

    results = attach_cost_csv(csv_path, runs)
    assert {r["status"] for r in results} == {"ok"}

    a = _pu(runs, "a")
    assert a["source"] == "manual" and a["available"] is True
    assert a["cost_usd"] == 0.123 and a["total_tokens"] == 15000
    assert a["reasoning_tokens"] == 3000

    b = _pu(runs, "b")
    assert b["cost_usd"] == 0.456 and b["total_tokens"] == 24000


def test_csv_missing_run_is_error_not_fatal(tmp_path):
    runs = tmp_path / "runs"
    _run(runs, "a")
    csv_path = tmp_path / "costs.csv"
    csv_path.write_text(
        CSV_HEADER + "\n"
        "a,0.1,1,2,0,0,0,3\n"
        "ghost,0.2,1,2,0,0,0,3\n",
        encoding="utf-8",
    )

    results = attach_cost_csv(csv_path, runs)
    by_id = {r["run_id"]: r for r in results}
    assert by_id["a"]["status"] == "ok"
    assert by_id["ghost"]["status"] == "error"
    # The good row still got written despite the bad one.
    assert _pu(runs, "a")["cost_usd"] == 0.1


def test_csv_blank_cells_skipped(tmp_path):
    runs = tmp_path / "runs"
    _run(runs, "a")
    csv_path = tmp_path / "costs.csv"
    # Only cost provided; token columns blank.
    csv_path.write_text(CSV_HEADER + "\n" + "a,0.5,,,,,,\n", encoding="utf-8")

    attach_cost_csv(csv_path, runs)
    pu = _pu(runs, "a")
    assert pu["cost_usd"] == 0.5
    assert pu["input_tokens"] is None
    assert pu["total_tokens"] is None
