"""A single failing task is isolated; the other tasks still run and score."""

from pathlib import Path

from tokenbench.cli import schedule_suite_runs
from tokenbench.manifests.loader import load_manifest

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "benchmark" / "manifests" / "marketlab-ml"
GOOD = ["marketlab_fee_slippage_001", "marketlab_lookahead_feature_001"]
BAD = "marketlab_split_leakage_001"


def test_failure_does_not_stop_other_tasks(tmp_path):
    runs_root = tmp_path / "runs"
    work = []
    for t in GOOD:
        rel = f"benchmark/manifests/marketlab-ml/{t}.json"
        work.append((rel, load_manifest(MANIFESTS / f"{t}.json"), 0))

    # Break one task by pointing it at a snapshot that does not exist; its
    # materialize step raises, which must be captured, not propagated.
    bad_manifest = load_manifest(MANIFESTS / f"{BAD}.json").model_copy(
        update={"broken_snapshot": "benchmark/repos/marketlab-ml/broken/__nope__"}
    )
    work.append((f"benchmark/manifests/marketlab-ml/{BAD}.json", bad_manifest, 0))

    results = schedule_suite_runs(
        work, base=ROOT, condition="dry_run_echo_baseline", runner="cli-agent",
        command=None, agent="dry_run_echo", skip_agent=True, overwrite=True,
        iso=tmp_path / "ws", max_concurrency=3, runs_root=runs_root,
    )

    by_task = {r["task_id"]: r for r in results}
    # The broken task is recorded as an error...
    assert by_task[BAD]["status"] == "error"
    assert "error" in by_task[BAD]
    # ...while the healthy tasks completed and produced artifacts.
    for t in GOOD:
        assert by_task[t]["status"] == "ok"
    assert len(list(runs_root.glob("*/score.json"))) == len(GOOD)
