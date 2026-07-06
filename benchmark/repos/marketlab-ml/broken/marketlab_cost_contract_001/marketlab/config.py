"""Backtest configuration.

A plain dataclass with defaults so tests and scripts can construct it without
reading a file. ``from_dict`` accepts a parsed config mapping (e.g. loaded from
one of the YAML files under ``configs/``) and ignores unknown keys.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass
class Config:
    fee_rate: float = 0.0005
    slippage_rate: float = 0.0002
    spread_rate: float = 0.0001
    window: int = 3
    horizon: int = 1
    test_size: float = 0.2
    train_size: int = 4
    walk_test_size: int = 2
    initial_equity: float = 10000.0

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def rates(self) -> dict:
        return {
            "fee_rate": self.fee_rate,
            "slippage_rate": self.slippage_rate,
            "spread_rate": self.spread_rate,
        }
