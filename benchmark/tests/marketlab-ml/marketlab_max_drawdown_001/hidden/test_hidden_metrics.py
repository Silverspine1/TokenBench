from marketlab.backtest import compute_metrics


def test_max_drawdown_present_and_correct():
    m = compute_metrics([100, 120, 90, 130, 80])
    assert "max_drawdown" in m
    # Largest peak-to-trough decline: peak 130 -> trough 80 => 50/130.
    assert abs(m["max_drawdown"] - (50.0 / 130.0)) < 1e-9


def test_monotonic_curve_has_zero_drawdown():
    m = compute_metrics([100, 110, 120, 130])
    assert abs(m["max_drawdown"] - 0.0) < 1e-9


def test_existing_metrics_still_present():
    m = compute_metrics([100, 110, 121])
    assert m["final_equity"] == 121
    assert m["num_periods"] == 2
    assert abs(m["total_return"] - 0.21) < 1e-9
