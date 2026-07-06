from marketlab.labels import make_labels


def test_exact_horizon_alignment():
    # label[i] = 1 if prices[i + horizon] > prices[i] else 0; last `horizon`
    # rows are None. This exact sequence rejects both i+horizon-1 and
    # i+horizon+1 off-by-one fixes.
    prices = [10, 11, 9, 12, 8, 13, 7]
    assert make_labels(prices, 2) == [0, 1, 0, 1, 0, None, None]


def test_trailing_unlabelled_equals_horizon():
    prices = [1, 2, 3, 4, 5, 6]
    labels = make_labels(prices, 3)
    # Exactly the final `horizon` rows lack a forward point.
    assert labels[-3:] == [None, None, None]
    assert labels[:-3] == [1, 1, 1]


def test_compares_correct_future_point():
    # horizon=1: each label compares the very next price.
    assert make_labels([5, 6, 4, 7], 1) == [1, 0, 1, None]
