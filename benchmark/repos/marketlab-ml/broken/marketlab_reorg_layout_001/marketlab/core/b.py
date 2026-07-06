"""Carried over from an earlier migration: cost-and-report grab-bag.

Holds the per-fill cost decomposition object plus the report assembly that ties
the cost breakdown, the trade table, and the equity curve together. Cost
component helpers themselves live in ``util/misc.py`` and are pulled in here.
The report summary reuses the equity-curve metric from the sibling grab-bag.
Exported under short internal names that the registry re-maps.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..portfolio import equity_curve, equity_delta
from ..util.misc import cm_a, cm_b, cm_c
from .a import q1


@dataclass(frozen=True)
class Bx:
    fee: float
    slippage: float
    spread: float

    @property
    def total(self) -> float:
        return self.fee + self.slippage + self.spread

    def as_dict(self) -> dict:
        return {
            "fee": self.fee,
            "slippage": self.slippage,
            "spread": self.spread,
            "total": self.total,
        }


def w0(notional, fee_rate, slippage_rate, spread_rate):
    return Bx(
        fee=cm_a(notional, fee_rate),
        slippage=cm_b(notional, slippage_rate),
        spread=cm_c(notional, spread_rate),
    )


def w1(trades, rates, initial_equity):
    fee_total = 0.0
    slippage_total = 0.0
    spread_total = 0.0
    gross_total = 0.0
    net_pnls = []
    trade_rows = []
    for tr in trades:
        cb = w0(tr["notional"], **rates)
        fee_total += cb.fee
        slippage_total += cb.slippage
        spread_total += cb.spread
        gross_total += tr["gross_pnl"]
        net = tr["gross_pnl"] - cb.total
        net_pnls.append(net)
        trade_rows.append(
            {
                "symbol": tr.get("symbol"),
                "gross_pnl": tr["gross_pnl"],
                "cost": cb.total,
                "net_pnl": net,
            }
        )
    total_cost = fee_total + slippage_total + spread_total
    net_total = gross_total - total_cost
    curve = equity_curve(initial_equity, net_pnls)
    return {
        "trades": trade_rows,
        "gross_pnl": gross_total,
        "net_pnl": net_total,
        "cost_breakdown": {
            "fee": fee_total,
            "slippage": slippage_total,
            "spread": spread_total,
            "total": total_cost,
        },
        "equity_curve": curve,
        "equity_delta": equity_delta(curve),
        "metrics": q1(curve),
    }
