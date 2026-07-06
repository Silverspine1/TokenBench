"""Visible smoke checks for the cost model."""

from marketlab.costs import trade_costs


def test_trade_costs_components_sum_to_total():
    cb = trade_costs(1000.0, fee_rate=0.001, slippage_rate=0.0005, spread_rate=0.0002)
    assert cb.fee == 1.0
    assert cb.slippage == 0.5
    assert cb.spread == 0.2
    assert abs(cb.total - (cb.fee + cb.slippage + cb.spread)) < 1e-12
