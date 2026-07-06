"""marketlab public API.

The evaluation building blocks are re-exported from one place so callers import
from ``marketlab`` rather than reaching into individual modules:

    from marketlab import build_report, compute_metrics, trade_costs

The names are wired up through the core registry.
"""

from __future__ import annotations

from .core.registry import (
    CostBreakdown,
    build_report,
    compute_metrics,
    fee_cost,
    max_drawdown_from_returns,
    mean_return,
    net_pnl,
    slippage_cost,
    spread_cost,
    trade_costs,
    win_rate,
)

__all__ = [
    "build_report",
    "compute_metrics",
    "net_pnl",
    "mean_return",
    "win_rate",
    "max_drawdown_from_returns",
    "CostBreakdown",
    "trade_costs",
    "fee_cost",
    "slippage_cost",
    "spread_cost",
]
