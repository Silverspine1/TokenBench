from marketlab.features import rolling_mean_prior


def test_first_row_has_no_prior():
    out = rolling_mean_prior([1, 2, 3], 2)
    assert out[0] is None


def test_uses_only_prior_rows():
    # window=2, strictly-prior mean.
    out = rolling_mean_prior([1, 2, 3, 4, 5], 2)
    assert out == [None, 1.0, 1.5, 2.5, 3.5]


def test_no_lookahead_on_current_row():
    # The feature at row i must not depend on values[i] (the current candle)
    # or any later row. Changing the current/future values leaves earlier
    # features unchanged.
    base = [10, 20, 30, 40, 50]
    spiked = [10, 20, 30, 999, 50]  # change rows >= 3 only
    a = rolling_mean_prior(base, 2)
    b = rolling_mean_prior(spiked, 2)
    # Features for rows 0..3 use only rows < i, so rows 0..3 are unaffected.
    assert a[:4] == b[:4]
