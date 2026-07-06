"""Walk-forward evaluation over sequential, non-overlapping test windows.

The series is partitioned into windows that advance in time. Each window trains
on ``train_size`` rows and evaluates on the following ``test_size`` rows. The
test windows do not overlap (``step`` defaults to ``test_size``), so no row is
scored twice and chronological order is preserved.

Per-window metrics: mean return, max drawdown, win rate. The aggregate reports
the mean window return, the worst (max) window drawdown, and the mean window
win rate, plus the window count.
"""

from __future__ import annotations

from .core.registry import max_drawdown_from_returns, mean_return, win_rate


def walk_forward_windows(
    n_rows: int, train_size: int, test_size: int, step: int | None = None
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Return ``[((train_lo, train_hi), (test_lo, test_hi)), ...]``.

    Bounds are half-open. Windows advance by ``step`` (default ``test_size``);
    with the default the test ranges tile the series without overlap.
    """
    if train_size <= 0 or test_size <= 0:
        return []
    step = test_size if step is None else step
    windows = []
    start = 0
    while start + train_size + test_size <= n_rows:
        train = (start, start + train_size)
        test = (start + train_size, start + train_size + test_size)
        windows.append((train, test))
        start += step
    return windows


def walk_forward_eval(
    returns: list[float],
    train_size: int,
    test_size: int,
    step: int | None = None,
) -> dict:
    """Evaluate ``returns`` window-by-window and aggregate the results."""
    windows = walk_forward_windows(len(returns), train_size, test_size, step)
    per_window: list[dict] = []
    for (tr_lo, tr_hi), (te_lo, te_hi) in windows:
        test = returns[te_lo:te_hi]
        per_window.append(
            {
                "train": [tr_lo, tr_hi],
                "test": [te_lo, te_hi],
                "mean_return": mean_return(test),
                "max_drawdown": max_drawdown_from_returns(test),
                "win_rate": win_rate(test),
            }
        )

    window_returns = [w["mean_return"] for w in per_window]
    window_winrates = [w["win_rate"] for w in per_window]
    window_drawdowns = [w["max_drawdown"] for w in per_window]
    aggregate = {
        "mean_return": mean_return(window_returns),
        "max_drawdown": max(window_drawdowns) if window_drawdowns else 0.0,
        "win_rate": mean_return(window_winrates),
        "num_windows": len(per_window),
    }
    return {"windows": per_window, "aggregate": aggregate}
