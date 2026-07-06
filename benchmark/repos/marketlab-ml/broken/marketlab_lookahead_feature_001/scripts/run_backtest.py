"""Tiny example entry point: build labels and report metrics on sample data."""

from __future__ import annotations

import csv
from pathlib import Path

from marketlab.backtest import compute_metrics
from marketlab.labels import make_labels

HERE = Path(__file__).resolve().parent
CANDLES = HERE.parent / "fixtures" / "candles_small.csv"


def load_closes(path: Path) -> list[float]:
    with path.open(newline="") as fh:
        return [float(row["close"]) for row in csv.DictReader(fh)]


def main() -> None:
    closes = load_closes(CANDLES)
    labels = make_labels(closes, horizon=2)
    metrics = compute_metrics(closes)
    print("labels:", labels)
    print("metrics:", metrics)


if __name__ == "__main__":
    main()
