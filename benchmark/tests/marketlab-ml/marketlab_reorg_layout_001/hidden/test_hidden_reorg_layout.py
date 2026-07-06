"""Hidden behaviour tests for the evaluation-layout reorganization.

Each test imports the concern it exercises from its canonical module path
inside the test body, so a module that is missing or misplaced fails only its
own cases (graceful partial credit) rather than aborting the whole file.

The canonical layout under test:
    marketlab/backtest.py  -> net_pnl, compute_metrics
    marketlab/metrics.py   -> mean_return, win_rate, max_drawdown_from_returns
    marketlab/costs.py     -> trade_costs, CostBreakdown
    marketlab/reports.py   -> build_report

Behaviour must be identical to the public API.
"""

RATES = {"fee_rate": 0.001, "slippage_rate": 0.0005, "spread_rate": 0.0002}


def test_backtest_net_pnl_at_canonical_path():
    from marketlab.backtest import net_pnl

    assert abs(net_pnl(100.0, 1000.0, 0.001, 0.0005) - 98.5) < 1e-9
    assert abs(net_pnl(0.0, 2000.0, 0.001, 0.0005) - (-3.0)) < 1e-9


def test_backtest_compute_metrics_at_canonical_path():
    from marketlab.backtest import compute_metrics

    m = compute_metrics([100.0, 110.0, 105.0])
    assert m["num_periods"] == 2
    assert abs(m["max_drawdown"] - (5.0 / 110.0)) < 1e-9
    assert abs(m["final_equity"] - 105.0) < 1e-9


def test_metrics_mean_return_at_canonical_path():
    from marketlab.metrics import mean_return

    assert abs(mean_return([0.1, -0.1, 0.2, 0.0]) - 0.05) < 1e-9
    assert mean_return([]) == 0.0


def test_metrics_win_rate_counts_strictly_positive():
    from marketlab.metrics import win_rate

    assert win_rate([0.1, 0.0, -0.2, 0.3]) == 0.5
    assert win_rate([0.0, 0.0]) == 0.0


def test_metrics_max_drawdown_from_returns_at_canonical_path():
    from marketlab.metrics import max_drawdown_from_returns

    assert abs(max_drawdown_from_returns([0.10, -0.10]) - (0.10 / 1.10)) < 1e-9


def test_costs_trade_costs_at_canonical_path():
    from marketlab.costs import trade_costs

    cb = trade_costs(1000.0, **RATES)
    assert abs(cb.fee - 1.0) < 1e-9
    assert abs(cb.slippage - 0.5) < 1e-9
    assert abs(cb.spread - 0.2) < 1e-9
    assert abs(cb.total - 1.7) < 1e-9


def test_costs_breakdown_type_at_canonical_path():
    from marketlab.costs import CostBreakdown, trade_costs

    cb = trade_costs(2000.0, **RATES)
    assert isinstance(cb, CostBreakdown)
    d = cb.as_dict()
    assert abs(d["total"] - (d["fee"] + d["slippage"] + d["spread"])) < 1e-9


def test_reports_build_report_reconciles_at_canonical_path():
    from marketlab.reports import build_report

    trades = [
        {"symbol": "AAA", "notional": 1000.0, "gross_pnl": 30.0},
        {"symbol": "BBB", "notional": 2000.0, "gross_pnl": -12.0},
        {"symbol": "CCC", "notional": 1500.0, "gross_pnl": 18.0},
    ]
    report = build_report(trades, RATES, initial_equity=10000.0)
    cb = report["cost_breakdown"]
    assert abs(report["gross_pnl"] - 36.0) < 1e-9
    assert abs(cb["total"] - 7.65) < 1e-9
    assert abs(report["net_pnl"] - 28.35) < 1e-9
    assert abs(report["net_pnl"] - (report["gross_pnl"] - cb["total"])) < 1e-9
    assert abs(report["equity_delta"] - report["net_pnl"]) < 1e-9


def test_reports_trade_order_preserved_at_canonical_path():
    from marketlab.reports import build_report

    trades = [
        {"symbol": "AAA", "notional": 1000.0, "gross_pnl": 30.0},
        {"symbol": "BBB", "notional": 2000.0, "gross_pnl": -12.0},
        {"symbol": "CCC", "notional": 1500.0, "gross_pnl": 18.0},
    ]
    report = build_report(trades, RATES, initial_equity=10000.0)
    assert [r["symbol"] for r in report["trades"]] == ["AAA", "BBB", "CCC"]
