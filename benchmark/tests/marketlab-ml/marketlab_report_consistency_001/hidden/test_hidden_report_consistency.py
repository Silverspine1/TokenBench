"""Hidden tests: report net/gross consistency (M5, frontier-hard).

Equity metrics and trade-table totals must share one net basis. Total net P&L
must equal the equity delta, the cost breakdown must reconcile, and trade order
must be preserved. Fixing only one of the two planted inconsistencies leaves a
reconciliation failure.
"""

from marketlab.reports import build_report

RATES = {"fee_rate": 0.001, "slippage_rate": 0.0005, "spread_rate": 0.0002}


def _trades():
    return [
        {"symbol": "AAA", "notional": 1000.0, "gross_pnl": 30.0},
        {"symbol": "BBB", "notional": 2000.0, "gross_pnl": -12.0},
        {"symbol": "CCC", "notional": 1500.0, "gross_pnl": 18.0},
    ]


def test_net_equals_gross_minus_total_cost():
    report = build_report(_trades(), RATES, initial_equity=10000.0)
    cb = report["cost_breakdown"]
    assert abs(report["net_pnl"] - (report["gross_pnl"] - cb["total"])) < 1e-9


def test_total_pnl_equals_equity_delta():
    report = build_report(_trades(), RATES, initial_equity=10000.0)
    assert abs(report["net_pnl"] - report["equity_delta"]) < 1e-9


def test_cost_breakdown_reconciles_with_components():
    report = build_report(_trades(), RATES, initial_equity=10000.0)
    cb = report["cost_breakdown"]
    # Components are independent and the total is their plain sum (no double add).
    assert abs(cb["total"] - (cb["fee"] + cb["slippage"] + cb["spread"])) < 1e-9
    # Per-row net costs sum to the reported total cost.
    row_costs = sum(r["cost"] for r in report["trades"])
    assert abs(row_costs - cb["total"]) < 1e-9


def test_trade_order_preserved():
    report = build_report(_trades(), RATES, initial_equity=10000.0)
    assert [r["symbol"] for r in report["trades"]] == ["AAA", "BBB", "CCC"]


def test_per_trade_net_consistent_with_table_total():
    report = build_report(_trades(), RATES, initial_equity=10000.0)
    table_net = sum(r["net_pnl"] for r in report["trades"])
    assert abs(table_net - report["net_pnl"]) < 1e-9


def test_exact_gross_cost_and_net_values():
    # Pins the absolute figures so an inflated cost component or a gross-based
    # net total is caught, not just internal consistency.
    report = build_report(_trades(), RATES, initial_equity=10000.0)
    cb = report["cost_breakdown"]
    assert abs(report["gross_pnl"] - 36.0) < 1e-9
    assert abs(cb["fee"] - 4.5) < 1e-9
    assert abs(cb["slippage"] - 2.25) < 1e-9
    assert abs(cb["spread"] - 0.9) < 1e-9
    assert abs(cb["total"] - 7.65) < 1e-9
    assert abs(report["net_pnl"] - 28.35) < 1e-9
    assert abs(report["equity_delta"] - 28.35) < 1e-9


def test_exact_values_second_fixture():
    # A second absolute-figure fixture: a partial fix that nails one fixture's
    # numbers (or only one of the two planted defects) still misses these.
    trades = [
        {"symbol": "AAA", "notional": 4000.0, "gross_pnl": 50.0},
        {"symbol": "BBB", "notional": 1000.0, "gross_pnl": -10.0},
    ]
    report = build_report(trades, RATES, initial_equity=20000.0)
    cb = report["cost_breakdown"]
    assert abs(report["gross_pnl"] - 40.0) < 1e-9
    assert abs(cb["fee"] - 5.0) < 1e-9
    assert abs(cb["slippage"] - 2.5) < 1e-9
    assert abs(cb["spread"] - 1.0) < 1e-9
    assert abs(cb["total"] - 8.5) < 1e-9
    assert abs(report["net_pnl"] - 31.5) < 1e-9
    assert abs(report["equity_delta"] - 31.5) < 1e-9
    assert abs(report["metrics"]["final_equity"] - (20000.0 + 31.5)) < 1e-9


def test_final_equity_reconciles_with_net_total():
    initial = 10000.0
    report = build_report(_trades(), RATES, initial_equity=initial)
    # Equity metrics share the net basis: final equity == initial + net P&L.
    assert abs(report["metrics"]["final_equity"] - (initial + report["net_pnl"])) < 1e-9
    assert abs(report["equity_delta"] - report["net_pnl"]) < 1e-9


def test_empty_report_is_zeroed_and_reconciles():
    report = build_report([], RATES, initial_equity=5000.0)
    cb = report["cost_breakdown"]
    assert report["trades"] == []
    assert abs(report["gross_pnl"] - 0.0) < 1e-9
    assert abs(cb["total"] - 0.0) < 1e-9
    assert abs(report["net_pnl"] - 0.0) < 1e-9
    assert abs(report["equity_delta"] - 0.0) < 1e-9


def test_single_trade_table_and_equity_agree():
    trades = [{"symbol": "AAA", "notional": 1000.0, "gross_pnl": 10.0}]
    report = build_report(trades, RATES, initial_equity=1000.0)
    row = report["trades"][0]
    assert abs(row["net_pnl"] - report["net_pnl"]) < 1e-9
    assert abs(row["net_pnl"] - (row["gross_pnl"] - row["cost"])) < 1e-9
    assert abs(report["equity_delta"] - report["net_pnl"]) < 1e-9


def test_loss_dominant_run_keeps_net_below_gross():
    trades = [
        {"symbol": "AAA", "notional": 5000.0, "gross_pnl": -40.0},
        {"symbol": "BBB", "notional": 3000.0, "gross_pnl": 5.0},
    ]
    report = build_report(trades, RATES, initial_equity=10000.0)
    cb = report["cost_breakdown"]
    assert report["net_pnl"] < report["gross_pnl"]
    assert abs(report["net_pnl"] - (report["gross_pnl"] - cb["total"])) < 1e-9
    assert abs(report["equity_delta"] - report["net_pnl"]) < 1e-9
