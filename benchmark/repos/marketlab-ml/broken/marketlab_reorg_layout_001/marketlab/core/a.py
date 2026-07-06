"""Carried over from an earlier migration: a grab-bag of evaluation routines.

This file mixes the per-fill P&L arithmetic, the equity-curve summary, and the
per-window return statistics that used to live in separate places. Everything
is exported under short internal names; the registry re-maps them to the names
callers expect.

The equity-curve summary (``q1``) and the per-window drawdown (``q5``) both
defer to the shared peak-to-trough scan in :mod:`..util.misc`, so the two never
disagree about how a drawdown is measured. Splitting these routines apart means
keeping a single owner of that scan rather than copying it into two places.
"""

from __future__ import annotations

from ..portfolio import equity_curve
from ..util.misc import _pk


def q0(g, n, fr, sr):
    f = n * fr
    s = n * sr
    return g - f - s


def q1(curve):
    if not curve:
        return {
            "final_equity": 0.0,
            "total_return": 0.0,
            "num_periods": 0,
            "max_drawdown": 0.0,
        }
    initial = curve[0]
    final = curve[-1]
    total_return = (final - initial) / initial if initial else 0.0
    return {
        "final_equity": final,
        "total_return": total_return,
        "num_periods": len(curve) - 1,
        "max_drawdown": _pk(curve),
    }


def q3(xs):
    if not xs:
        return 0.0
    return sum(xs) / len(xs)


def q4(xs):
    if not xs:
        return 0.0
    wins = sum(1 for r in xs if r > 0)
    return wins / len(xs)


def q5(xs, initial=1.0):
    curve = equity_curve(initial, list(xs))
    return _pk(curve)
