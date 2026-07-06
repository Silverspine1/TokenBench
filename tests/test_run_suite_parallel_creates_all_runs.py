"""Parallel suite scheduling produces one isolated atomic run per work item."""

from pathlib import Path

from tokenbench.cli import schedule_suite_runs
from tokenbench.manifests.loader import load_manifest

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "benchmark" / "manifests" / "marketlab-ml"
TASKS = [
    "marketlab_fee_slippage_001",
    "marketlab_lookahead_feature_001",
    "marketlab_split_leakage_001",
]


def _work():
    items = []
    for t in TASKS:
        rel = f"benchmark/manifests/marketlab-ml/{t}.json"
        items.append((rel, load_manifest(MANIFESTS / f"{t}.json"), 0))
    return items


def test_parallel_creates_all_runs(tmp_path):
    runs_root = tmp_path / "runs"
    results = schedule_suite_runs(
        _work(), base=ROOT, condition="dry_run_echo_baseline", runner="cli-agent",
        command=None, agent="dry_run_echo", skip_agent=True, overwrite=True,
        iso=tmp_path / "ws", max_concurrency=3, runs_root=runs_root,
    )

    # One status per work item, all completed.
    assert len(results) == len(TASKS)
    assert all(r["status"] == "ok" for r in results), results

    # Each run produced its own isolated artifacts.
    score_files = list(runs_root.glob("*/score.json"))
    telemetry_files = list(runs_root.glob("*/telemetry.json"))
    assert len(score_files) == len(TASKS)
    assert len(telemetry_files) == len(TASKS)

    # Every scheduled task appears exactly once.
    seen = {r["task_id"] for r in results}
    assert seen == set(TASKS)
