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
    n_test = max(1, int(round(n * test_size)))
    n_test = min(n_test, n)
    n_train = n - n_test
    return rows[:n_train], rows[n_train:]


def train_test_split_chrono_multi(
    rows: list[dict], test_size: float, symbol_key: str = "symbol", time_key: str = "t"
) -> tuple[list, list]:
    """Chronological split for interleaved multi-asset rows.

    A single global cut on interleaved symbols would put some symbols' late
    rows in train and early rows in test. To keep every symbol's train rows
    strictly before its own test rows, the cut is applied **per symbol**: each
    symbol contributes its last ``round(k * test_size)`` (>=1) rows to test and
    the rest to train.

    Output ordering is deterministic: rows keep their original positions
    (stable), so the returned lists are subsequences of ``rows``.
    """
    n = len(rows)
    if n == 0:
        return [], []

    # Order everything by time, then take the latest rows as the test set.
    ordered = sorted(range(n), key=lambda i: rows[i][time_key])
    n_test = min(n, max(1, int(round(n * test_size))))
    test_idx = set(ordered[n - n_test:])

    train = [rows[i] for i in range(n) if i not in test_idx]
    test = [rows[i] for i in range(n) if i in test_idx]
    return train, test
