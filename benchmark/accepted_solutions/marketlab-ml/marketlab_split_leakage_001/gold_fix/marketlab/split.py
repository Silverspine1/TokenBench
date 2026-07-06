"""Train/test splitting for time-series rows.

Rows arrive in chronological order (ascending ``t``). The split must be
chronological: every training row precedes every test row in time, with no
shuffling and no overlap. Shuffling or interleaving leaks future information
into training.
"""


def train_test_split_chrono(rows: list[dict], test_size: float) -> tuple[list, list]:
    """Split chronologically into (train, test).

    The last ``round(n * test_size)`` rows (at least one) form the test set;
    earlier rows form the training set.
    """
    n = len(rows)
    if n == 0:
        return [], []
    n_test = max(1, int(round(n * test_size)))
    n_test = min(n_test, n)
    n_train = n - n_test
    return rows[:n_train], rows[n_train:]
