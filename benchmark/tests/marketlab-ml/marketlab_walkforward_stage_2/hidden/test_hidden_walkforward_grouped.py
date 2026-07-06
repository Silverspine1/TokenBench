"""Hidden tests: grouped multi-symbol walk-forward report (staged group, stage 2).

Builds on the single-series walk-forward report by reporting per symbol and
rolling the windows up into an overall summary. Imports are lazy inside each
test so a missing feature fails only its own cases.
"""


def _by_symbol():
    return {
        "AAA": [0.0, 0.0, 0.10, -0.10, 0.0, 0.0, 0.20, 0.20],
        "BBB": [0.0, 0.0, 0.0, 0.0],
        "CCC": [0.0, 0.0, 0.1, 0.3],
    }


def test_grouped_report_has_one_group_per_symbol_in_order():
    from marketlab import grouped_walk_forward_report

    rep = grouped_walk_forward_report(_by_symbol(), train_size=2, test_size=2)
    assert [g["symbol"] for g in rep["groups"]] == ["AAA", "BBB", "CCC"]


def test_grouped_report_groups_carry_their_own_rows_and_summary():
    from marketlab import grouped_walk_forward_report

    rep = grouped_walk_forward_report(_by_symbol(), train_size=2, test_size=2)
    aaa = rep["groups"][0]
    assert aaa["symbol"] == "AAA"
    assert aaa["summary"]["num_windows"] == 3
    assert len(aaa["rows"]) == 3
    bbb = rep["groups"][1]
    assert bbb["summary"]["num_windows"] == 1


def test_grouped_overall_counts_symbols_and_windows():
    from marketlab import grouped_walk_forward_report

    rep = grouped_walk_forward_report(_by_symbol(), train_size=2, test_size=2)
    overall = rep["overall"]
    assert overall["num_symbols"] == 3
    # AAA contributes 3 windows, BBB 1, CCC 1 -> 5 total.
    assert overall["num_windows"] == 5


def test_grouped_overall_aggregates_across_all_windows():
    from marketlab import grouped_walk_forward_report

    by_symbol = {
        "AAA": [0.0, 0.0, 0.1, -0.1],  # one window: mean 0.0, win 0.5, dd 0.1/1.1
        "BBB": [0.0, 0.0, 0.2, 0.2],   # one window: mean 0.2, win 1.0, dd 0.0
    }
    rep = grouped_walk_forward_report(by_symbol, train_size=2, test_size=2)
    overall = rep["overall"]
    assert overall["num_windows"] == 2
    assert abs(overall["mean_return"] - (0.0 + 0.2) / 2) < 1e-9
    assert abs(overall["win_rate"] - (0.5 + 1.0) / 2) < 1e-9
    assert abs(overall["max_drawdown"] - (0.10 / 1.10)) < 1e-9


def test_grouped_text_mentions_each_symbol_and_overall():
    from marketlab import grouped_walk_forward_report

    rep = grouped_walk_forward_report(_by_symbol(), train_size=2, test_size=2)
    text = rep["text"]
    assert isinstance(text, str)
    for sym in ("AAA", "BBB", "CCC"):
        assert sym in text
    assert "overall" in text


def test_grouped_empty_mapping_is_zeroed():
    from marketlab import grouped_walk_forward_report

    rep = grouped_walk_forward_report({}, train_size=2, test_size=2)
    assert rep["groups"] == []
    assert rep["overall"]["num_symbols"] == 0
    assert rep["overall"]["num_windows"] == 0


def test_grouped_single_symbol_matches_single_series_report():
    from marketlab import grouped_walk_forward_report, walk_forward_report

    returns = [0.0, 0.0, 0.10, -0.10, 0.0, 0.0, 0.20, 0.20]
    grouped = grouped_walk_forward_report({"AAA": returns}, train_size=2, test_size=2)
    single = walk_forward_report(returns, train_size=2, test_size=2)
    g = grouped["groups"][0]
    assert g["summary"] == single["summary"]
    assert [r["mean_return"] for r in g["rows"]] == [r["mean_return"] for r in single["rows"]]
