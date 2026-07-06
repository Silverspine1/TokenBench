from pathlib import Path

from tokenbench.analysis.charting import build_series, metric_catalog
from tokenbench.analysis.sqlite_store import connect, create_schema


def _seed(db_path: Path):
    """Two conditions x two tasks, with a duplicate trial to test aggregation.

    run_id is time-prefixed, so lexical order == chronological order.
    """
    conn = connect(db_path)
    create_schema(conn)
    rows = [
        # run_id, condition, task, cost, total_tokens, final, churn
        ("20260101_000001_demo_t1_a", "base",    "t1", 0.10, 100, 90, 10),
        ("20260101_000002_demo_t2_a", "base",    "t2", 0.20, 200, 80, 20),
        ("20260101_000003_demo_t1_b", "caveman", "t1", 0.05,  40, 88,  5),
        ("20260101_000004_demo_t2_a", "caveman", "t2", 0.06,  60, 70,  8),
        ("20260101_000005_demo_t2_b", "caveman", "t2", 0.04,  20, 72,  3),  # 2nd trial of t2
    ]
    for run_id, cond, task, cost, toks, final, churn in rows:
        conn.execute(
            "INSERT INTO runs (run_id, condition_id, task_id, final_score, quality_score) "
            "VALUES (?,?,?,?,?)", (run_id, cond, task, final, final),
        )
        conn.execute(
            "INSERT INTO provider_cost (run_id, available, cost_usd, total_tokens) "
            "VALUES (?,1,?,?)", (run_id, cost, toks),
        )
        conn.execute(
            "INSERT INTO telemetry (run_id, line_churn) VALUES (?,?)", (run_id, churn),
        )
    conn.commit()
    conn.close()


def test_per_test_sum_trials(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    out = build_series(db, "total_tokens", mode="per_test", agg="sum", x_mode="task")
    series = {s["condition"]: s for s in out["series"]}

    # caveman t2 has two trials (60 + 20) summed.
    cav = {p["label"]: p["value"] for p in series["caveman"]["points"]}
    assert cav["t1"] == 40
    assert cav["t2"] == 80
    base = {p["label"]: p["value"] for p in series["base"]["points"]}
    assert base["t1"] == 100 and base["t2"] == 200


def test_cumulative_running_total(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    out = build_series(db, "total_tokens", mode="cumulative", agg="sum", x_mode="time")
    series = {s["condition"]: s for s in out["series"]}

    base_vals = [p["value"] for p in series["base"]["points"]]
    assert base_vals == [100, 300]  # 100, then 100+200

    cav_vals = [p["value"] for p in series["caveman"]["points"]]
    assert cav_vals == [40, 120]  # t1=40, then +t2(80)=120


def test_conditions_filter_and_cost_metric(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    out = build_series(db, "cost_usd", conditions=["base"], agg="sum", x_mode="task")
    assert [s["condition"] for s in out["series"]] == ["base"]
    vals = [p["value"] for p in out["series"][0]["points"]]
    assert vals == [0.10, 0.20]


def test_mean_aggregation(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    out = build_series(db, "total_tokens", mode="per_test", agg="mean", x_mode="task")
    cav = {p["label"]: p["value"] for p in
           next(s for s in out["series"] if s["condition"] == "caveman")["points"]}
    assert cav["t2"] == 40  # mean(60, 20)


def test_metric_catalog_has_expected_keys():
    keys = {m["key"] for m in metric_catalog()}
    assert {"total_tokens", "cost_usd", "final_score", "line_churn"} <= keys
