"""Backtest report assembly.

``build_report`` reconciles three views of the same run so they cannot drift:

  * the cost breakdown (fee / slippage / spread, each summed once),
  * the trade table totals (gross and net P&L), and
  * the equity curve (built from the same net P&L stream).

Invariants the report must satisfy:

    net_pnl      == gross_pnl - cost_breakdown["total"]
    equity_delta == net_pnl
    cost_breakdown["total"] == fee + slippage + spread

Every monetary figure in the report is on the **net** basis except the
explicitly named ``gross_pnl`` field, so equity metrics and trade totals agree.
"""

from __future__ import annotations

from .costs import trade_costs
from .metrics import compute_metrics
from .portfolio import equity_curve, equity_delta


def build_report(trades: list[dict], rates: dict, initial_equity: float) -> dict:
    """Assemble a reconciled backtest report.

    ``trades`` is a list of dicts with ``notional`` and ``gross_pnl``. ``rates``
    holds ``fee_rate``, ``slippage_rate``, ``spread_rate``. Trade order is
    preserved throughout.
    """
    fee_total = 0.0
    slippage_total = 0.0
    spread_total = 0.0
    gross_total = 0.0
    net_pnls: list[float] = []
    trade_rows: list[dict] = []

    for tr in trades:
        cb = trade_costs(tr["notional"], **rates)
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

    total_cost = fee_total + slippage_total
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
        "metrics": compute_metrics(curve),
    }
