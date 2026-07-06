"""Candle loading and dataset assembly.

The dataset aligns three things per output row:

  * a causal feature computed from the ``window`` rows **strictly before** the
    current row (never the current or any later row),
  * the current row's time index, and
  * a forward label describing the move ``horizon`` rows ahead.

Warmup rows (the first ``window`` rows, which lack a full prior window) and the
trailing ``horizon`` rows (which lack a forward point) are dropped. Rows are
processed in arrival order, so data with missing periods (gaps) aligns by row
position, not by arithmetic on the time index.
"""

from __future__ import annotations

from .features import rolling_mean_prior
from .labels import make_labels


def load_candles(rows: list[dict]) -> list[dict]:
    """Return candles sorted by ``t`` ascending (stable). Input is not mutated."""
    return sorted(rows, key=lambda r: r["t"])


def group_by_symbol(rows: list[dict]) -> dict:
    """Group candles by ``symbol``, preserving per-symbol order."""
    groups: dict = {}
    for r in rows:
        groups.setdefault(r["symbol"], []).append(r)
    return groups


def build_dataset(candles: list[dict], window: int, horizon: int) -> list[dict]:
    """Aligned (feature, label) rows for a single symbol.

    ``candles`` are dicts with at least ``t`` and ``close``; they are assumed to
    be in chronological order. The output drops the first ``window`` warmup rows
    and the final ``horizon`` rows.
    """
    closes = [c["close"] for c in candles]
    features = rolling_mean_prior(closes, window)
    labels = make_labels(closes, horizon)

    rows: list[dict] = []
    for i in range(len(candles)):
        if i < window - 1:
            # Warmup: no full prior window available.
            continue
        if labels[i] is None:
            # Trailing rows with no forward point.
            continue
        rows.append(
            {
                "t": candles[i]["t"],
                "feature": features[i],
                "label": labels[i],
            }
        )
    return rows
