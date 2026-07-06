from marketlab.features import rolling_mean_prior


def test_shape_and_constant_series():
    # A flat series is uninformative either way; this only checks basic shape.
    out = rolling_mean_prior([5, 5, 5, 5], 2)
    assert isinstance(out, list)
    assert len(out) == 4
    assert out[1] == 5
    assert out[2] == 5
