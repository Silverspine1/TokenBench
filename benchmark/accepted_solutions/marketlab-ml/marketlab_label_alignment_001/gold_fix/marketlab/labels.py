"""Forward-looking classification labels.

The label at row ``i`` describes the move over the next ``horizon`` periods:
it is ``1`` when ``price[i + horizon] > price[i]`` and ``0`` otherwise. The
final ``horizon`` rows have no future point and are labelled ``None``.

Getting the horizon offset exactly right matters: ``i + horizon - 1`` and
``i + horizon + 1`` are both plausible-looking but wrong.
"""

# Number of trailing rows that necessarily lack a forward label, per unit horizon.
TRAILING_UNLABELLED_PER_HORIZON = 1


def make_labels(prices: list[float], horizon: int) -> list:
    """Binary up/down labels over ``horizon`` periods ahead.

    ``labels[i] = 1`` if ``prices[i + horizon] > prices[i]`` else ``0``;
    ``None`` for the final ``horizon`` rows.
    """
    labels: list = []
    n = len(prices)
    for i in range(n):
        j = i + horizon
        if j < n:
            labels.append(1 if prices[j] > prices[i] else 0)
        else:
            labels.append(None)
    return labels
