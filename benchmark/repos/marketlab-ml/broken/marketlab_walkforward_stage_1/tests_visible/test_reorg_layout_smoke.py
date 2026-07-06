"""Visible smoke check that the public API resolves through the package.

Imports only from the top-level ``marketlab`` package (the public entrypoint),
so it stays runnable regardless of where each concern physically lives.
"""

import marketlab


def test_public_api_is_exposed():
    for name in (
        "build_report",
        "compute_metrics",
        "net_pnl",
        "mean_return",
        "win_rate",
        "max_drawdown_from_returns",
        "trade_costs",
        "CostBreakdown",
    ):
        assert hasattr(marketlab, name), name


def test_net_pnl_round_trip():
    assert abs(marketlab.net_pnl(100.0, 1000.0, 0.001, 0.0005) - 98.5) < 1e-9


def test_build_report_reconciles():
    trades = [{"symbol": "AAA", "notional": 1000.0, "gross_pnl": 30.0}]
    rates = {"fee_rate": 0.001, "slippage_rate": 0.0005, "spread_rate": 0.0002}
    report = marketlab.build_report(trades, rates, initial_equity=10000.0)
    cb = report["cost_breakdown"]
    assert abs(report["net_pnl"] - (report["gross_pnl"] - cb["total"])) < 1e-9
    assert abs(report["equity_delta"] - report["net_pnl"]) < 1e-9
