from pathlib import Path

from tokenbench.analysis.sqlite_store import connect, ingest_runs
from tokenbench.manual.service import (
    attach_manual_cost,
    create_manual_run,
    submit_manual_run,
)


def _make_run(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(base, demo_task["manifest"], condition_id="manual_generic_ide")
    run_dir = Path(rec["run_dir"])
    demo_task["edit_to_gold"](run_dir)
    submit_manual_run(base, run_dir)
    return run_dir


def test_ingest_creates_run_row(demo_task, tmp_path):
    run_dir = _make_run(demo_task)
    db = tmp_path / "tb.db"
    totals = ingest_runs(demo_task["base"] / "runs", db)

    assert totals["runs"] == 1
    assert totals["manual"] == 1

    conn = connect(db)
    row = conn.execute(
        "SELECT task_id, success, final_score, runner FROM runs WHERE run_id=?",
        (run_dir.name,),
    ).fetchone()
    assert row["task_id"] == "demo_fix_001"
    assert row["success"] == 1
    assert row["runner"] == "manual-ide"
    conn.close()


def test_ingest_is_idempotent_and_captures_cost(demo_task, tmp_path):
    run_dir = _make_run(demo_task)
    attach_manual_cost(
        run_dir, {"cost_usd": 0.25, "input_tokens": 100},
        source="provider_dashboard", confidence="medium",
    )
    db = tmp_path / "tb.db"
    ingest_runs(demo_task["base"] / "runs", db)
    ingest_runs(demo_task["base"] / "runs", db)  # second pass must not duplicate

    conn = connect(db)
    n = conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
    assert n == 1
    cost = conn.execute(
        "SELECT cost_usd, available, manual_source FROM provider_cost WHERE run_id=?",
        (run_dir.name,),
    ).fetchone()
    assert cost["cost_usd"] == 0.25
    assert cost["available"] == 1
    assert cost["manual_source"] == "provider_dashboard"

    # The convenience view joins it all.
    view = conn.execute(
        "SELECT cost_usd, success FROM run_results WHERE run_id=?", (run_dir.name,)
    ).fetchone()
    assert view["cost_usd"] == 0.25
    assert view["success"] == 1
    conn.close()


def test_ingest_empty_runs_dir(tmp_path):
    totals = ingest_runs(tmp_path / "no_runs", tmp_path / "tb.db")
    assert totals["run_dirs_scanned"] == 0
    assert totals["runs"] == 0
