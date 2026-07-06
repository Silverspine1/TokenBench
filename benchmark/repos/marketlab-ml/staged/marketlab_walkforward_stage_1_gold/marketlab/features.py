"""Rolling feature engineering for causal signals."""


def rolling_mean_prior(values: list[float], window: int) -> list:
    """Rolling mean of the ``window`` rows preceding each row.

    ``out[i]`` averages the prior ``window`` rows; ``out[0]`` has no prior
    rows and is ``None``.
    """
    out: list = []
    for i in range(len(values)):
        start = max(0, i - window)
        prior = values[start:i]
        out.append(sum(prior) / len(prior) if prior else None)
    return out
