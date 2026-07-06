"""Hidden tests: rolling feature warmup alignment (M3).

Features must be causal (prior rows only — never the current or a later row),
warmup rows must be dropped correctly, and labels must stay aligned to the
post-warmup rows across gaps and multiple horizons.
"""

from marketlab.data_loader import build_dataset
from marketlab.features import rolling_mean_prior
from marketlab.labels import make_labels


def _candles(closes, ts=None):
    ts = ts if ts is not None else list(range(len(closes)))
    return [{"t": t, "symbol": "AAA", "close": c} for t, c in zip(ts, closes)]


def test_feature_excludes_current_and_future():
    closes = [10.0, 11.0, 12.0, 13.0, 14.0]
    feats = rolling_mean_prior(closes, window=2)
    # feats[i] must equal the mean of the two prior closes, not include closes[i].
    assert feats[2] == (closes[0] + closes[1]) / 2
    assert feats[3] == (closes[1] + closes[2]) / 2
    # Strictly-increasing series: prior-only mean is below the current close.
    assert feats[4] < closes[4]


def test_warmup_rows_dropped_at_window_boundary():
    rows = build_dataset(_candles([10, 11, 12, 13, 14, 15]), window=2, horizon=1)
    # First retained row is at index == window (not window-1).
    assert [r["t"] for r in rows] == [2, 3, 4]


def test_labels_align_with_post_warmup_rows():
    closes = [10, 11, 9, 12, 8, 13]
    rows = build_dataset(_candles(closes), window=2, horizon=1)
    expected = make_labels(closes, horizon=1)
    for r in rows:
        assert r["label"] == expected[r["t"]]


def test_alignment_survives_gaps():
    # Time index has gaps; alignment is by row position, not by t arithmetic.
    closes = [100, 101, 102, 99, 100.5, 103, 101]
    ts = [1, 2, 3, 6, 7, 8, 9]
    rows = build_dataset(_candles(closes, ts), window=2, horizon=1)
    assert [r["t"] for r in rows] == [3, 6, 7, 8]


def test_horizon_three_drops_three_trailing_rows():
    closes = [10, 11, 12, 13, 14, 15, 16]
    rows = build_dataset(_candles(closes), window=2, horizon=3)
    # warmup drops i<2; trailing horizon=3 drops i where i+3 >= n(=7) -> i>=4.
    assert [r["t"] for r in rows] == [2, 3]
    # feature still causal at horizon 3.
    for r in rows:
        assert r["feature"] == (closes[r["t"] - 2] + closes[r["t"] - 1]) / 2


def test_window_one_uses_single_prior_close():
    feats = rolling_mean_prior([5.0, 7.0, 11.0, 13.0], window=1)
    assert feats[0] is None
    assert feats[1] == 5.0
    assert feats[2] == 7.0
    assert feats[3] == 11.0


def test_first_window_rows_are_never_emitted():
    # No output row may reference a warmup index (< window), even with horizon 0
    # unavailable; the first retained t is exactly `window`.
    rows = build_dataset(_candles([10, 11, 12, 13, 14]), window=3, horizon=1)
    assert min(r["t"] for r in rows) == 3


def test_feature_never_peeks_at_current_or_future_close():
    closes = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    rows = build_dataset(_candles(closes), window=2, horizon=1)
    for r in rows:
        i = r["t"]
        # Prior-only mean is strictly below the current close on a rising series.
        assert r["feature"] < closes[i]
        assert r["feature"] == (closes[i - 2] + closes[i - 1]) / 2


def test_labels_align_across_gaps_by_position():
    # With gaps, label must still reflect close[i+horizon] > close[i] by position.
    closes = [100, 101, 102, 99, 100.5, 103, 101]
    ts = [1, 2, 3, 6, 7, 8, 9]
    rows = build_dataset(_candles(closes, ts), window=2, horizon=1)
    pos_by_t = {t: idx for idx, t in enumerate(ts)}
    for r in rows:
        i = pos_by_t[r["t"]]
        assert r["label"] == (1 if closes[i + 1] > closes[i] else 0)
