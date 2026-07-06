"""Summary table across all runs."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table


def collect_scores(runs_dir: Path) -> list[dict]:
    """Load every score.json under ``runs_dir``, sorted by final_score desc."""
    scores: list[dict] = []
    for score_path in sorted(Path(runs_dir).glob("*/score.json")):
        try:
            scores.append(json.loads(score_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    scores.sort(key=lambda s: s.get("final_score", 0.0), reverse=True)
    return scores


def render_summary(runs_dir: Path, console: Console | None = None) -> list[dict]:
    console = console or Console()
    scores = collect_scores(runs_dir)

    table = Table(title=f"TokenBench runs — {runs_dir}")
    table.add_column("rank", justify="right")
    table.add_column("final", justify="right")
    table.add_column("quality", justify="right")
    table.add_column("efficiency", justify="right")
    table.add_column("runner")
    table.add_column("repo")
    table.add_column("task")
    table.add_column("run_id")

    for i, s in enumerate(scores, start=1):
        table.add_row(
            str(i),
            f"{s.get('final_score', 0):.2f}",
            f"{s.get('quality_score', 0):.2f}",
            f"{s.get('efficiency_score', 0):.2f}",
            s.get("runner", ""),
            s.get("repo_id", ""),
            s.get("task_id", ""),
            s.get("run_id", ""),
        )

    if not scores:
        console.print(f"No score.json files found under {runs_dir}")
    else:
        console.print(table)
    return scores
