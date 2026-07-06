from marketlab.backtest import net_pnl


def test_basic_costs():
    # gross 100, notional 1000, fee 1%, slippage 0.5% -> 100 - 10 - 5 = 85
    assert net_pnl(100, 1000, 0.01, 0.005) == 85
