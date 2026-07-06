from marketlab.labels import make_labels


def test_shape_and_value_domain():
    prices = [10, 11, 9, 12, 8, 13, 7]
    labels = make_labels(prices, 2)
    assert len(labels) == len(prices)
    for v in labels:
        assert v in (0, 1, None)
