"""Visible smoke checks for report assembly on simple input."""

from marketlab.reports import build_report

RATES = {"fee_rate": 0.0005, "slippage_rate": 0.0002, "spread_rate": 0.0001}


def test_report_net_matches_gross_minus_cost():
    trades = [{"symbol": "AAA", "notional": 1000.0, "gross_pnl": 20.0}]
    report = build_report(trades, RATES, initial_equity=10000.0)
    cb = report["cost_breakdown"]
    assert abs(report["net_pnl"] - (report["gross_pnl"] - cb["total"])) < 1e-9
    assert abs(report["equity_delta"] - report["net_pnl"]) < 1e-9
