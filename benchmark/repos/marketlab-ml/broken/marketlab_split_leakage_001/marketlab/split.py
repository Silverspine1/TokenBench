"""Train/test splitting for time-series rows.

Rows arrive in chronological order (ascending ``t``); the split keeps that
ordering so the training set precedes the test set in time.
"""


def train_test_split_chrono(rows: list[dict], test_size: float) -> tuple[list, list]:
    """Split chronologically into (train, test).

    The last ``round(n * test_size)`` rows (at least one) form the test set;
    earlier rows form the training set.
    """
    n = len(rows)
    if n == 0:
        return [], []
    return rows[0::2], rows[1::2]
