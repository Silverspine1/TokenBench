"""Walk-forward report output.

Turns a return series into a human-readable / structured walk-forward report:
a row per evaluation window plus a summary line over the windows.

The report is built from a small, reusable shape:

    build_window_rows(returns, train_size, test_size)  -> list[dict]
    summarize_rows(rows)                               -> dict

so the same machinery can be reused to report over any single series. The
public ``walk_forward_report`` ties them together and renders the text block.
"""

from __future__ import annotations

from .evaluation import walk_forward_eval

REPORT_COLUMNS = ("window", "test_start", "test_end", "mean_return", "win_rate", "max_drawdown")


def build_window_rows(returns: list[float], train_size: int, test_size: int) -> list[dict]:
    """Per-window report rows for one return series.

    Each row carries the window index, its test range, and the window metrics.
    This is the single-series building block the report renders.
    """
    out = walk_forward_eval(returns, train_size=train_size, test_size=test_size)
    rows: list[dict] = []
    for i, w in enumerate(out["windows"]):
        rows.append(
            {
                "window": i,
                "test_start": w["test"][0],
                "test_end": w["test"][1],
                "mean_return": w["mean_return"],
                "win_rate": w["win_rate"],
                "max_drawdown": w["max_drawdown"],
            }
        )
    return rows


def summarize_rows(rows: list[dict]) -> dict:
    """Aggregate a list of window rows into a summary record.

    Mean window return, mean window win rate, worst (max) window drawdown, and
    the window count. Empty input yields a fully zeroed summary.
    """
    n = len(rows)
    if n == 0:
        return {
            "num_windows": 0,
            "mean_return": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
        }
    return {
        "num_windows": n,
        "mean_return": sum(r["mean_return"] for r in rows) / n,
        "win_rate": sum(r["win_rate"] for r in rows) / n,
        "max_drawdown": max(r["max_drawdown"] for r in rows),
    }


def render_report(rows: list[dict], summary: dict, title: str = "walk-forward") -> str:
    """Render rows + summary as a plain-text block."""
    lines = [f"# {title} report", "\t".join(REPORT_COLUMNS)]
    for r in rows:
        lines.append(
            "\t".join(
                str(r[c]) if c in ("window", "test_start", "test_end") else f"{r[c]:.6f}"
                for c in REPORT_COLUMNS
            )
        )
    lines.append(
        "summary\t"
        f"num_windows={summary['num_windows']}\t"
        f"mean_return={summary['mean_return']:.6f}\t"
        f"win_rate={summary['win_rate']:.6f}\t"
        f"max_drawdown={summary['max_drawdown']:.6f}"
    )
    return "\n".join(lines)


def walk_forward_report(
    returns: list[float],
    train_size: int,
    test_size: int,
    title: str = "walk-forward",
) -> dict:
    """Structured walk-forward report for one return series.

    Returns ``{"title", "rows", "summary", "text"}``.
    """
    rows = build_window_rows(returns, train_size, test_size)
    summary = summarize_rows(rows)
    return {
        "title": title,
        "rows": rows,
        "summary": summary,
        "text": render_report(rows, summary, title),
    }


def grouped_walk_forward_report(
    returns_by_symbol: dict[str, list[float]],
    train_size: int,
    test_size: int,
) -> dict:
    """Walk-forward report grouped per symbol, with an overall rollup.

    ``returns_by_symbol`` maps a symbol to its return series. Each symbol is
    reported independently using the same single-series machinery, then an
    overall summary aggregates across every symbol's windows. Symbol order is
    preserved (insertion order of the input mapping).

    Returns ``{"groups", "overall", "text"}`` where ``groups`` is a list of
    ``{"symbol", "rows", "summary"}`` records in input order.
    """
    groups: list[dict] = []
    all_rows: list[dict] = []
    for symbol, returns in returns_by_symbol.items():
        rows = build_window_rows(returns, train_size, test_size)
        groups.append(
            {
                "symbol": symbol,
                "rows": rows,
                "summary": summarize_rows(rows),
            }
        )
        all_rows.extend(rows)

    overall = summarize_rows(all_rows)
    overall["num_symbols"] = len(groups)

    text_blocks = []
    for g in groups:
        text_blocks.append(render_report(g["rows"], g["summary"], title=f"symbol {g['symbol']}"))
    text_blocks.append(
        "overall\t"
        f"num_symbols={overall['num_symbols']}\t"
        f"num_windows={overall['num_windows']}\t"
        f"mean_return={overall['mean_return']:.6f}\t"
        f"win_rate={overall['win_rate']:.6f}\t"
        f"max_drawdown={overall['max_drawdown']:.6f}"
    )

    return {
        "groups": groups,
        "overall": overall,
        "text": "\n\n".join(text_blocks),
    }
