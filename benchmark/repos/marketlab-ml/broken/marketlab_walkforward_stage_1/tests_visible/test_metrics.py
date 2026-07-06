from marketlab.backtest import compute_metrics


def test_existing_metrics_preserved():
    m = compute_metrics([100, 110, 121])
    # Existing metric names and values must not change.
    assert m["final_equity"] == 121
    assert m["num_periods"] == 2
    assert abs(m["total_return"] - 0.21) < 1e-9
