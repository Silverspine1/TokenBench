from pathlib import Path

from tokenbench.analysis.public_export import build_public_payload
from tokenbench.analysis.sqlite_store import connect, create_schema


def _seed(db_path: Path):
    """Two configs over two tasks; caveman is cheaper, base is the reference."""
    conn = connect(db_path)
    create_schema(conn)
    rows = [
        # run_id, cond, task, cost, in_tok, out_tok, total, final, quality, success, wall
        ("20260101_000001_b_t1", "base",    "t1", 0.10, 800, 200, 1000, 0.90, 0.92, 1, 30.0),
        ("20260101_000002_b_t2", "base",    "t2", 0.20, 1600, 400, 2000, 0.80, 0.81, 1, 50.0),
        ("20260101_000003_c_t1", "caveman", "t1", 0.05, 300, 100, 400, 0.88, 0.70, 1, 20.0),
        ("20260101_000004_c_t2", "caveman", "t2", 0.05, 300, 100, 400, 0.70, 0.60, 0, 25.0),
    ]
    for run_id, cond, task, cost, itok, otok, total, final, quality, success, wall in rows:
        conn.execute(
            "INSERT INTO runs (run_id, condition_id, task_id, final_score, quality_score, "
            "success, total_wall_time_seconds) VALUES (?,?,?,?,?,?,?)",
            (run_id, cond, task, final, quality, success, wall),
        )
        conn.execute(
            "INSERT INTO provider_cost (run_id, available, cost_usd, input_tokens, output_tokens, total_tokens) "
            "VALUES (?,1,?,?,?,?)", (run_id, cost, itok, otok, total),
        )
    conn.commit()
    conn.close()


def test_baseline_auto_picks_base(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    p = build_public_payload(db, generated_at="2026-06-21 10:00")
    assert p["baseline"] == "base"
    assert p["generated_at"] == "2026-06-21 10:00"
    assert p["conditions"] == ["base", "caveman"]


def test_cost_leaderboard_savings(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    cost = build_public_payload(db)["leaderboards"]["cost"]
    # cheapest per task first
    assert cost[0]["condition"] == "caveman"
    # base cost/task = (0.10+0.20)/2 = 0.15 ; caveman = 0.05 ; saving = 66.7%
    cav = next(r for r in cost if r["condition"] == "caveman")
    assert cav["savings_pct"] == 66.7
    base = next(r for r in cost if r["condition"] == "base")
    assert base["is_baseline"] is True and base["savings_pct"] == 0.0
    assert base["cost_total"] == 0.30


def test_quality_leaderboard_sorted_by_value(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    q = build_public_payload(db)["leaderboards"]["quality"]
    # value = quality / cost-per-task. caveman 0.65/0.05=13.0 beats base 0.865/0.15=5.77
    assert q[0]["condition"] == "caveman"
    assert q[0]["value_per_usd"] >= q[1]["value_per_usd"]
    cav = next(r for r in q if r["condition"] == "caveman")
    assert cav["success_rate"] == 50.0  # one of two tasks succeeded


def test_explicit_baseline_override(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    cost = build_public_payload(db, baseline="caveman")["leaderboards"]["cost"]
    base = next(r for r in cost if r["condition"] == "caveman")
    assert base["is_baseline"] is True
    # base config is now pricier => negative saving
    other = next(r for r in cost if r["condition"] == "base")
    assert other["savings_pct"] < 0


def test_excludes_headroom(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    conn = connect(db)
    conn.execute(
        "INSERT INTO runs (run_id, condition_id, task_id, final_score, quality_score, success) "
        "VALUES ('20260101_000099_h_t1','sonnet_headroom','t1',0.5,0.5,1)"
    )
    conn.execute("INSERT INTO provider_cost (run_id, available, cost_usd) VALUES ('20260101_000099_h_t1',1,0.4)")
    conn.commit(); conn.close()
    p = build_public_payload(db)
    assert "sonnet_headroom" not in p["conditions"]
    assert all("headroom" not in r["condition"] for r in p["leaderboards"]["cost"])
    assert all("headroom" not in s["condition"] for s in p["charts"]["data"]["cost_usd"]["series"])


def test_chart_metrics_are_cost_quality_wall_total(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    charts = build_public_payload(db)["charts"]
    keys = {m["key"] for m in charts["metrics"]}
    assert keys == {"cost_usd", "wall_time_seconds", "line_churn",
                    "total_tokens", "hidden_pass_rate", "quality_score"}
    block = charts["data"]["total_tokens"]
    assert block["x_labels"] == ["t1", "t2"]
    assert any(s["condition"] == "base" for s in block["series"])


def test_quality_per_dollar_and_suggestions(tmp_path):
    db = tmp_path / "tb.db"
    _seed(db)
    p = build_public_payload(db)
    cav = next(r for r in p["leaderboards"]["quality"] if r["condition"] == "caveman")
    # caveman quality mean 0.65 / cost-per-task 0.05 = 13.0 quality per $
    assert cav["value_per_usd"] == 13.0
    picks = {s["pick"]: s["condition"] for s in p["suggestions"]}
    assert set(picks) == {"Best value", "Cheapest", "Highest quality"}
    assert picks["Best value"] == "caveman"      # cheap + decent quality
    assert picks["Cheapest"] == "caveman"
    assert picks["Highest quality"] == "base"
