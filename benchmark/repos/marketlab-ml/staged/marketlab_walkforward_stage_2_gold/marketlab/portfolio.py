"""Equity-curve construction from per-trade net P&L.

The equity curve starts at ``initial_equity`` and accumulates each trade's net
P&L in order. The final point minus the first point equals the sum of net P&L
(the equity delta invariant).
"""

from __future__ import annotations


def equity_curve(initial_equity: float, net_pnls: list[float]) -> list[float]:
    """Cumulative equity starting at ``initial_equity``.

    ``curve[0] == initial_equity`` and ``curve[k]`` adds the first ``k`` net
    P&L values in order.
    """
    curve = [initial_equity]
    equity = initial_equity
    for pnl in net_pnls:
        equity += pnl
        curve.append(equity)
    return curve


def equity_delta(curve: list[float]) -> float:
    """Final minus initial equity. Zero for an empty/degenerate curve."""
    if len(curve) < 2:
        return 0.0
    return curve[-1] - curve[0]
