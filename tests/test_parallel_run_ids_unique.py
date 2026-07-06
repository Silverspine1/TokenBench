"""Concurrent runs of the same task still get distinct run_ids and run dirs."""

from pathlib import Path

from tokenbench.cli import schedule_suite_runs
from tokenbench.manifests.loader import load_manifest

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "benchmark" / "manifests" / "marketlab-ml"
TASK = "marketlab_fee_slippage_001"
REL = f"benchmark/manifests/marketlab-ml/{TASK}.json"


def test_parallel_run_ids_unique(tmp_path):
    runs_root = tmp_path / "runs"
    manifest = load_manifest(MANIFESTS / f"{TASK}.json")
    # Same task, four trials, scheduled concurrently — the hardest case for
    # run_id collisions (same repo/task, same wall-clock second).
    work = [(REL, manifest, trial) for trial in range(4)]

    results = schedule_suite_runs(
        work, base=ROOT, condition="dry_run_echo_baseline", runner="cli-agent",
        command=None, agent="dry_run_echo", skip_agent=True, overwrite=True,
        iso=tmp_path / "ws", max_concurrency=4, runs_root=runs_root,
    )

    run_ids = [r["run_id"] for r in results if r["status"] == "ok"]
    assert len(run_ids) == 4
    assert len(set(run_ids)) == 4, f"run_ids collided: {run_ids}"
    # One isolated run directory per run_id.
    assert len(list(runs_root.glob("*/score.json"))) == 4
