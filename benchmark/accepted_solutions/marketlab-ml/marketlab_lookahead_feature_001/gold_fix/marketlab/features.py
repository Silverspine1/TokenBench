"""Rolling feature engineering.

Signal features must be causal: the feature at row ``i`` may only use rows
strictly before ``i``. Using row ``i`` itself (or any later row) leaks the
present/future into a signal that is supposed to be tradeable at row ``i``.
"""


def rolling_mean_prior(values: list[float], window: int) -> list:
    """Rolling mean over the ``window`` rows STRICTLY BEFORE each row.

    ``out[i]`` is the mean of ``values[i-window : i]`` (rows ``< i`` only).
    ``out[0]`` has no prior rows and is ``None``.
    """
    out: list = []
    for i in range(len(values)):
        start = max(0, i - window)
        prior = values[start:i]  # rows strictly before i
        out.append(sum(prior) / len(prior) if prior else None)
    return out
