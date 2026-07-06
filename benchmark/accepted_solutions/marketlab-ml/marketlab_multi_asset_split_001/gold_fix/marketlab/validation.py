"""Invariant checks for splits and datasets.

These helpers are used both by the pipeline and by tests to assert the
correctness properties that names alone do not guarantee.
"""

from __future__ import annotations


def is_chronological(rows: list[dict], time_key: str = "t") -> bool:
    """True if ``rows`` are non-decreasing in ``time_key``."""
    times = [r[time_key] for r in rows]
    return all(a <= b for a, b in zip(times, times[1:]))


def no_symbol_time_overlap(
    train: list[dict],
    test: list[dict],
    symbol_key: str = "symbol",
    time_key: str = "t",
) -> bool:
    """True when, for every symbol, all train times precede all test times.

    This is the per-symbol causality property: a symbol must never have a
    training row at or after one of its own test rows.
    """
    max_train: dict = {}
    for r in train:
        sym = r[symbol_key]
        t = r[time_key]
        if sym not in max_train or t > max_train[sym]:
            max_train[sym] = t

    min_test: dict = {}
    for r in test:
        sym = r[symbol_key]
        t = r[time_key]
        if sym not in min_test or t < min_test[sym]:
            min_test[sym] = t

    for sym, lo in min_test.items():
        if sym in max_train and max_train[sym] >= lo:
            return False
    return True
