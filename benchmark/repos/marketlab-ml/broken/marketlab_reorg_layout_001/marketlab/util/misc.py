"""Assorted helpers left over from an earlier migration.

This module is a catch-all that the migration never untangled. It holds two
unrelated families of helper that happen to have ended up side by side:

* the per-fill cost component functions (``cm_*``), each proportional to the
  absolute traded notional; and
* a low-level peak-to-trough scan (``_pk``) that several summary routines lean
  on. It is reached from more than one place through the registry, so it cannot
  simply be inlined where it is used today.
"""

from __future__ import annotations


def cm_a(notional, fee_rate):
    return abs(notional) * fee_rate


def cm_b(notional, slippage_rate):
    return abs(notional) * slippage_rate


def cm_c(notional, spread_rate):
    return abs(notional) * spread_rate


def _pk(curve):
    """Largest peak-to-trough fractional decline of ``curve`` (>= 0).

    Shared by the equity-curve summary and by the per-window drawdown routine;
    both feed it a cumulative curve and read the single number back.
    """
    peak = curve[0]
    worst = 0.0
    for value in curve:
        if value > peak:
            peak = value
        if peak > 0:
            d = (peak - value) / peak
            if d > worst:
                worst = d
    return worst
