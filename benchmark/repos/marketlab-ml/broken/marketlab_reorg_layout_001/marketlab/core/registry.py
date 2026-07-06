"""Indirection layer that maps the short internal names from the migration
grab-bags back to the public API names the rest of the package imports.

Callers go through here instead of reaching into ``core/a``, ``core/b`` and
``util/misc`` directly. The mapping is the only place that knows which internal
symbol backs each public name, so every consumer in the package imports the
public name from here.
"""

from __future__ import annotations

from ..util.misc import cm_a, cm_b, cm_c
from .a import q0, q1, q3, q4, q5
from .b import Bx, w0

# public name -> internal implementation
net_pnl = q0
compute_metrics = q1
mean_return = q3
win_rate = q4
max_drawdown_from_returns = q5

CostBreakdown = Bx
trade_costs = w0
fee_cost = cm_a
slippage_cost = cm_b
spread_cost = cm_c


def build_report(trades, rates, initial_equity):
    from .b import w1

    return w1(trades, rates, initial_equity)
