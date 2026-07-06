"""Visible smoke checks for walk-forward evaluation."""

from marketlab.evaluation import walk_forward_eval, walk_forward_windows


def test_windows_are_sequential_and_non_overlapping():
    windows = walk_forward_windows(n_rows=8, train_size=2, test_size=2)
    tests = [te for _tr, te in windows]
    assert tests == [(2, 4), (4, 6), (6, 8)]


def test_eval_reports_num_windows():
    returns = [0.1, -0.05, 0.2, 0.0, 0.15, -0.1, 0.05, 0.3]
    out = walk_forward_eval(returns, train_size=2, test_size=2)
    assert out["aggregate"]["num_windows"] == len(out["windows"]) == 3
