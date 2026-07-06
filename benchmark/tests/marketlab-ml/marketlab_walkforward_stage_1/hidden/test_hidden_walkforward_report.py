"""Hidden tests: walk-forward report output (staged group, stage 1).

A structured walk-forward report over a single return series: one row per
evaluation window plus a summary over the windows. Imports are lazy inside each
test so a missing feature fails only its own cases (graceful partial credit).
"""


def test_report_exposes_rows_and_summary():
    from marketlab import walk_forward_report

    rep = walk_forward_report([0.0, 0.0, 0.1, -0.1, 0.0, 0.0, 0.2, 0.2], train_size=2, test_size=2)
    assert set(rep) >= {"rows", "summary"}
    assert len(rep["rows"]) == 3
    assert rep["summary"]["num_windows"] == 3


def test_report_rows_carry_per_window_metrics():
    from marketlab import walk_forward_report

    rep = walk_forward_report([0.0, 0.0, 0.1, -0.1, 0.0, 0.0, 0.2, 0.2], train_size=2, test_size=2)
    r0 = rep["rows"][0]
    assert r0["test_start"] == 2 and r0["test_end"] == 4
    assert abs(r0["mean_return"] - 0.0) < 1e-9
    assert abs(r0["win_rate"] - 0.5) < 1e-9
    assert abs(r0["max_drawdown"] - (0.10 / 1.10)) < 1e-9


def test_report_summary_aggregates_windows_exactly():
    from marketlab import walk_forward_report

    rep = walk_forward_report([0.0, 0.0, 0.10, -0.10, 0.0, 0.0, 0.20, 0.20], train_size=2, test_size=2)
    s = rep["summary"]
    # window mean returns: 0.0, 0.0, 0.20 -> mean 0.0666...
    assert abs(s["mean_return"] - (0.0 + 0.0 + 0.20) / 3) < 1e-9
    # window win rates: 0.5, 0.0, 1.0 -> mean 0.5
    assert abs(s["win_rate"] - 0.5) < 1e-9
    # worst window drawdown comes from [0.10,-0.10]
    assert abs(s["max_drawdown"] - (0.10 / 1.10)) < 1e-9


def test_report_rows_are_indexed_in_order():
    from marketlab import walk_forward_report

    rep = walk_forward_report([0.1, -0.05, 0.2, 0.0, 0.15, -0.1, 0.05, 0.3], train_size=2, test_size=2)
    assert [r["window"] for r in rep["rows"]] == [0, 1, 2]
    starts = [r["test_start"] for r in rep["rows"]]
    assert starts == sorted(starts)


def test_report_text_is_rendered():
    from marketlab import walk_forward_report

    rep = walk_forward_report([0.0, 0.0, 0.1, -0.1, 0.0, 0.0, 0.2, 0.2], train_size=2, test_size=2)
    assert isinstance(rep["text"], str)
    assert "summary" in rep["text"]
    # One header line, one column line, one row per window, one summary line.
    assert rep["text"].count("\n") >= 3


def test_report_empty_when_series_too_short():
    from marketlab import walk_forward_report

    rep = walk_forward_report([0.1, 0.2], train_size=2, test_size=2)
    assert rep["rows"] == []
    assert rep["summary"]["num_windows"] == 0
    assert rep["summary"]["mean_return"] == 0.0


def test_report_win_rate_counts_only_strictly_positive():
    from marketlab import walk_forward_report

    rep = walk_forward_report([0.0, 0.0, 0.0, 0.0], train_size=2, test_size=2)
    assert rep["rows"][0]["win_rate"] == 0.0
    assert rep["summary"]["win_rate"] == 0.0
