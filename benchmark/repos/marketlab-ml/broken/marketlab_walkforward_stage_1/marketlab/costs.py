"""Transaction cost model.

A fill incurs three separate cost components, each proportional to the traded
notional:

    fee      = notional * fee_rate
    slippage = notional * slippage_rate
    spread   = notional * spread_rate

``trade_costs`` returns all three as a :class:`CostBreakdown`. The total is the
sum of the three components and is counted exactly once per fill. Downstream
reporting consumes the breakdown so each component can be shown separately.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostBreakdown:
    """Per-fill cost decomposition. ``total`` is the sum of the parts."""

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


def fee_cost(notional: float, fee_rate: float) -> float:
    return abs(notional) * fee_rate


def slippage_cost(notional: float, slippage_rate: float) -> float:
    return abs(notional) * slippage_rate


def spread_cost(notional: float, spread_rate: float) -> float:
    return abs(notional) * spread_rate


def trade_costs(
    notional: float,
    fee_rate: float,
    slippage_rate: float,
    spread_rate: float,
) -> CostBreakdown:
    """Full cost breakdown for one fill of ``notional``."""
    return CostBreakdown(
        fee=fee_cost(notional, fee_rate),
        slippage=slippage_cost(notional, slippage_rate),
        spread=spread_cost(notional, spread_rate),
    )


# Legacy helper retained for the pre-breakdown reporting path. It returns only
# the fee component and must never be used as if it were the full cost.
def legacy_fee_only(notional: float, fee_rate: float) -> float:
    return fee_cost(notional, fee_rate)
