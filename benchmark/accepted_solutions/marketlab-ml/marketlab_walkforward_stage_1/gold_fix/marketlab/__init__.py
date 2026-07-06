"""marketlab public API.

The package exposes its evaluation building blocks from one place so callers
import from ``marketlab`` rather than reaching into individual modules:

    from marketlab import build_report, compute_metrics, trade_costs

Each name is re-exported from the single module that owns it.
"""

from __future__ import annotations

from .backtest import compute_metrics, net_pnl
from .costs import (
    CostBreakdown,
    fee_cost,
    slippage_cost,
    spread_cost,
    trade_costs,
)
from .metrics import max_drawdown_from_returns, mean_return, win_rate
from .reports import build_report
from .walkforward_report import walk_forward_report

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
    "walk_forward_report",
]
