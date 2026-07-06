"""Return and risk metrics.

The canonical equity-curve metric (``compute_metrics``) lives in
:mod:`marketlab.backtest`; this module re-exports it and adds the per-window
metrics used by walk-forward evaluation. Keeping one definition of
``compute_metrics`` avoids two drifting copies of ``max_drawdown``.
"""

from __future__ import annotations

from .backtest import compute_metrics
from .portfolio import equity_curve

__all__ = [
    "compute_metrics",
    "mean_return",
    "win_rate",
    "max_drawdown_from_returns",
]


def mean_return(returns: list[float]) -> float:
    """Arithmetic mean of per-period returns. Zero for an empty series."""
    if not returns:
        return 0.0
    return sum(returns) / len(returns)


def win_rate(returns: list[float]) -> float:
    """Fraction of strictly positive returns. Zero for an empty series."""
    if not returns:
        return 0.0
    wins = sum(1 for r in returns if r > 0)
    return wins / len(returns)


def max_drawdown_from_returns(returns: list[float], initial: float = 1.0) -> float:
    """Max drawdown of the equity curve implied by additive ``returns``."""
    curve = equity_curve(initial, list(returns))
    return compute_metrics(curve)["max_drawdown"]
