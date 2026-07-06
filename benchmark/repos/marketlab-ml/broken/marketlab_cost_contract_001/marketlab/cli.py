"""Tiny command-line entry for running a backtest report from a fixture.

Not a full CLI — enough to wire config + data + report together for manual
inspection. ``python -m marketlab.cli <candles.csv>``.
"""

from __future__ import annotations

import csv
import json
import sys

from .config import Config
from .data_loader import build_dataset, load_candles
from .reports import build_report


def _read_candles(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = []
        for row in reader:
            rows.append(
                {
                    "t": int(row["t"]),
                    "symbol": row.get("symbol", "NA"),
                    "close": float(row["close"]),
                }
            )
    return rows


def _dataset_to_trades(dataset: list[dict], notional: float = 1000.0) -> list[dict]:
    """Toy mapping from labelled rows to trades for reporting purposes."""
    trades = []
    for row in dataset:
        gross = notional * 0.01 if row["label"] == 1 else -notional * 0.01
        trades.append({"symbol": "NA", "notional": notional, "gross_pnl": gross})
    return trades


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m marketlab.cli <candles.csv>", file=sys.stderr)
        return 2
    cfg = Config()
    candles = load_candles(_read_candles(argv[0]))
    dataset = build_dataset(candles, cfg.window, cfg.horizon)
    trades = _dataset_to_trades(dataset)
    report = build_report(trades, cfg.rates(), cfg.initial_equity)
    print(json.dumps(report["cost_breakdown"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
