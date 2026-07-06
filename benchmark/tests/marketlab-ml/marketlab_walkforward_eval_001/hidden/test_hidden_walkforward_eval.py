"""Hidden tests: walk-forward evaluation (M4).

Sequential, non-overlapping test windows; exact per-window and aggregate
metrics; and the existing backtest APIs must be unchanged.
"""

from marketlab.backtest import compute_metrics, net_pnl
from marketlab.evaluation import walk_forward_eval, walk_forward_windows


def test_window_boundaries_tile_without_overlap():
    windows = walk_forward_windows(n_rows=8, train_size=2, test_size=2)
    assert windows == [((0, 2), (2, 4)), ((2, 4), (4, 6)), ((4, 6), (6, 8))]
    tests = [te for _tr, te in windows]
    # Disjoint, contiguous test ranges.
    for (lo1, hi1), (lo2, _hi2) in zip(tests, tests[1:]):
        assert hi1 == lo2


def test_multiple_windows_produced():
    returns = [0.1, -0.05, 0.2, 0.0, 0.15, -0.1, 0.05, 0.3]
    out = walk_forward_eval(returns, train_size=2, test_size=2)
    assert out["aggregate"]["num_windows"] == 3
    assert len(out["windows"]) == 3


def test_aggregate_metrics_exact():
    returns = [0.0, 0.0, 0.10, -0.10, 0.0, 0.0, 0.20, 0.20]
    out = walk_forward_eval(returns, train_size=2, test_size=2)
    agg = out["aggregate"]
    # Three test windows: [0.10,-0.10], [0.0,0.0], [0.20,0.20]
    # mean returns: 0.0, 0.0, 0.20 -> mean = 0.0666...
    assert abs(agg["mean_return"] - (0.0 + 0.0 + 0.20) / 3) < 1e-9
    # win rates: 0.5, 0.0, 1.0 -> mean = 0.5
    assert abs(agg["win_rate"] - 0.5) < 1e-9
    # worst window drawdown comes from [0.10,-0.10]: peak 1.10 -> 1.0 = ~0.0909
    assert abs(agg["max_drawdown"] - (0.10 / 1.10)) < 1e-9


def test_no_window_when_series_too_short():
    out = walk_forward_eval([0.1, 0.2], train_size=2, test_size=2)
    assert out["aggregate"]["num_windows"] == 0
    assert out["windows"] == []


def test_existing_backtest_apis_unchanged():
    # net_pnl and compute_metrics must keep their established contracts.
    assert abs(net_pnl(100.0, 1000.0, 0.001, 0.0005) - 98.5) < 1e-9
    m = compute_metrics([100.0, 110.0, 105.0])
    assert m["num_periods"] == 2
    assert abs(m["max_drawdown"] - (5.0 / 110.0)) < 1e-9


def test_remainder_rows_beyond_last_full_window_are_dropped():
    # 9 rows, train 2 + test 2 = 4 per stride of 2: windows at 0,2,4 then
    # start=6 needs rows[6:10] but only 9 exist -> stopped. Last row unused.
    windows = walk_forward_windows(n_rows=9, train_size=2, test_size=2)
    assert windows == [((0, 2), (2, 4)), ((2, 4), (4, 6)), ((4, 6), (6, 8))]


def test_explicit_step_allows_overlapping_train_windows():
    # step=1 advances one row at a time; test ranges then overlap by design.
    windows = walk_forward_windows(n_rows=6, train_size=2, test_size=2, step=1)
    assert windows == [((0, 2), (2, 4)), ((1, 3), (3, 5)), ((2, 4), (4, 6))]


def test_per_window_metrics_are_exact():
    returns = [0.0, 0.0, 0.10, -0.10, 0.0, 0.0, 0.20, 0.20]
    out = walk_forward_eval(returns, train_size=2, test_size=2)
    w0 = out["windows"][0]
    assert w0["test"] == [2, 4]
    assert abs(w0["mean_return"] - 0.0) < 1e-9
    assert abs(w0["win_rate"] - 0.5) < 1e-9
    assert abs(w0["max_drawdown"] - (0.10 / 1.10)) < 1e-9


def test_win_rate_counts_only_strictly_positive_returns():
    # A flat (0.0) test window scores a 0.0 win rate, not a win.
    out = walk_forward_eval([0.0, 0.0, 0.0, 0.0], train_size=2, test_size=2)
    assert out["aggregate"]["num_windows"] == 1
    assert out["windows"][0]["win_rate"] == 0.0


def test_zero_sizes_yield_no_windows():
    assert walk_forward_windows(n_rows=10, train_size=0, test_size=2) == []
    assert walk_forward_windows(n_rows=10, train_size=2, test_size=0) == []


def test_all_nonpositive_window_has_zero_win_rate():
    # Zeros and negatives are not wins; win rate must be 0.0, never counted via >=.
    out = walk_forward_eval([0.0, 0.0, -0.1, -0.2], train_size=2, test_size=2)
    assert out["aggregate"]["num_windows"] == 1
    assert out["windows"][0]["win_rate"] == 0.0


def test_aggregate_win_rate_is_mean_of_window_win_rates_strictly_positive():
    # tests: [0.1,-0.1] -> 0.5 ; [0.0,0.2] -> 0.5 (0.0 not a win) ; [0.0,0.0] -> 0.0
    returns = [0.0, 0.0, 0.1, -0.1, 0.0, 0.2, 0.0, 0.0]
    out = walk_forward_eval(returns, train_size=2, test_size=2)
    assert out["aggregate"]["num_windows"] == 3
    assert abs(out["aggregate"]["win_rate"] - (0.5 + 0.5 + 0.0) / 3) < 1e-9
