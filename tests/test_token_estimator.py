from tokenbench.telemetry.token_estimator import ESTIMATOR_NAME, estimate_tokens


def test_zero_and_negative_estimate_to_zero():
    assert estimate_tokens(0) == 0
    assert estimate_tokens(-10) == 0


def test_ceil_division_by_four():
    assert estimate_tokens(4) == 1
    assert estimate_tokens(5) == 2
    assert estimate_tokens(2200) == 550
    assert estimate_tokens(13950) == 3488


def test_estimator_name_is_marked_as_estimate():
    assert ESTIMATOR_NAME == "chars_div_4_v1"
