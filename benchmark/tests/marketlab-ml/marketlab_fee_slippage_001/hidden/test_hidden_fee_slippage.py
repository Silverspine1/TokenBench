from marketlab.backtest import net_pnl


def test_zero_costs():
    assert net_pnl(50, 1000, 0.0, 0.0) == 50


def test_fee_and_slippage_separate():
    # gross 0, notional 2000, fee 2%, slippage 1% -> -(40 + 20)
    assert net_pnl(0, 2000, 0.02, 0.01) == -(40 + 20)


def test_no_double_fee():
    assert net_pnl(100, 1000, 0.01, 0.005) == 85


def test_slippage_applied():
    # slippage must not be dropped
    assert net_pnl(100, 1000, 0.0, 0.01) == 90
