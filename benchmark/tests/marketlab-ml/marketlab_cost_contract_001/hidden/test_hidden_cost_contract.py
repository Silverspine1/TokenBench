"""Hidden tests: cost-model contract drift (M1).

Gold passes all. A broken snapshot that drops spread, double-counts a
component, or reverts reporting to a fee-only total must fail at least one.
"""

from marketlab.costs import legacy_fee_only, trade_costs
from marketlab.reports import build_report

RATES = {"fee_rate": 0.001, "slippage_rate": 0.0005, "spread_rate": 0.0002}


def test_total_includes_all_three_components():
    cb = trade_costs(1000.0, **RATES)
    assert cb.fee == 1.0
    assert cb.slippage == 0.5
    assert cb.spread == 0.2
    # total must be the sum of all three, counted once.
    assert abs(cb.total - 1.7) < 1e-9


def test_no_double_counting_single_fill():
    cb = trade_costs(5000.0, fee_rate=0.001, slippage_rate=0.0, spread_rate=0.0)
    # only fee is non-zero; total must equal the fee exactly, not twice.
    assert abs(cb.total - 5.0) < 1e-9


def test_report_breakdown_is_separate_and_reconciles():
    trades = [
        {"symbol": "AAA", "notional": 1000.0, "gross_pnl": 20.0},
        {"symbol": "BBB", "notional": 2000.0, "gross_pnl": -5.0},
    ]
    report = build_report(trades, RATES, initial_equity=10000.0)
    cb = report["cost_breakdown"]
    # Each component reported separately and non-zero.
    assert cb["fee"] > 0 and cb["slippage"] > 0 and cb["spread"] > 0
    # Total is the sum of the parts.
    assert abs(cb["total"] - (cb["fee"] + cb["slippage"] + cb["spread"])) < 1e-9
    # Net reconciles with gross and the full cost total.
    assert abs(report["net_pnl"] - (report["gross_pnl"] - cb["total"])) < 1e-9


def test_full_cost_differs_from_fee_only_when_other_costs_present():
    # Guards a wrong fix that makes the whole pipeline fee-only again.
    notional = 1000.0
    cb = trade_costs(notional, **RATES)
    fee_only = legacy_fee_only(notional, RATES["fee_rate"])
    assert cb.total > fee_only
    assert abs(cb.total - (fee_only + cb.slippage + cb.spread)) < 1e-9


def test_legacy_fee_only_still_returns_just_the_fee():
    # Backward compatibility for the old fee-only call site.
    assert abs(legacy_fee_only(1000.0, 0.001) - 1.0) < 1e-9


def test_costs_use_absolute_notional():
    # A short fill has negative notional; cost is on |notional|, never negative.
    cb = trade_costs(-1000.0, **RATES)
    assert cb.fee == 1.0
    assert cb.slippage == 0.5
    assert cb.spread == 0.2
    assert cb.total > 0


def test_as_dict_total_matches_components():
    cb = trade_costs(1234.0, **RATES)
    d = cb.as_dict()
    assert abs(d["total"] - (d["fee"] + d["slippage"] + d["spread"])) < 1e-9
    assert abs(d["total"] - cb.total) < 1e-9


def test_zero_notional_is_costless():
    cb = trade_costs(0.0, **RATES)
    assert cb.fee == 0.0 and cb.slippage == 0.0 and cb.spread == 0.0
    assert cb.total == 0.0


def test_per_row_cost_equals_full_breakdown_total():
    # Each trade row's reported cost must be the full three-component cost for
    # that fill, not the fee alone.
    trades = [{"symbol": "AAA", "notional": 1000.0, "gross_pnl": 0.0}]
    report = build_report(trades, RATES, initial_equity=0.0)
    row = report["trades"][0]
    assert abs(row["cost"] - 1.7) < 1e-9
