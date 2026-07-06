"""Shared data shapes for the backtest pipeline.

These are light dataclasses used across data loading, feature/label building,
cost accounting, and reporting. They carry no behaviour beyond construction so
that every stage agrees on field names (the data contract).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candle:
    """One OHLCV bar for a single symbol at time ``t`` (integer period index)."""

    t: int
    symbol: str
    close: float


@dataclass(frozen=True)
class Trade:
    """A round-trip trade. ``notional`` is the absolute traded value.

    ``gross_pnl`` is profit before any transaction cost. Costs are accounted
    separately so they can be itemized by component.
    """

    symbol: str
    entry_t: int
    exit_t: int
    notional: float
    gross_pnl: float
