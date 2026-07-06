"""Visible smoke checks for dataset assembly on contiguous data."""

from marketlab.data_loader import build_dataset


def _candles(closes):
    return [{"t": i, "symbol": "AAA", "close": c} for i, c in enumerate(closes)]


def test_contiguous_dataset_drops_warmup_and_tail():
    closes = [10, 11, 12, 13, 14, 15]
    rows = build_dataset(_candles(closes), window=2, horizon=1)
    # first 2 warmup rows dropped, last 1 (no forward label) dropped -> ts 2,3,4
    assert [r["t"] for r in rows] == [2, 3, 4]
    assert all(r["feature"] is not None for r in rows)
