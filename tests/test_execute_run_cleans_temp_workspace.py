"""Isolated temp workspaces must not survive a finished run.

Per-run materialized trees (a full repo copy, plus any graphify graph / builds)
live under ``isolated_runs_root/<run_id>``. ``finalize_run`` already archives the
durable copy into ``run_dir/candidate``, so once a run is scored the temp tree is
dead weight. Left behind, these copies accumulate over a sweep and fill the disk
(OSError: [Errno 28]). ``execute_run`` deletes them by default.
"""

from pathlib import Path

from tokenbench.agents.loader import load_agent
from tokenbench.cli import execute_run
from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.cli_agent import CliAgentRunner

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "benchmark" / "agents"
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def _run(tmp_path, **kwargs):
    manifest = load_manifest(MARKETLAB)
    runner = CliAgentRunner(load_agent(AGENTS, "dry_run_echo"))
    return execute_run(
        manifest,
        ROOT,
        runner,
        condition_id="dry_run_echo",
        trial_index=0,
        overwrite=True,
        runs_root=tmp_path / "runs",
        isolated_runs_root=tmp_path / "iso",
        **kwargs,
    )


def test_temp_workspace_is_removed_after_run(tmp_path):
    report = _run(tmp_path)
    iso_root = tmp_path / "iso"
    # The isolated workspace tree is gone...
    assert not any(iso_root.glob("*/workspace")), "temp workspace not cleaned up"
    # ...but the durable candidate archive in the kept run_dir remains.
    run_dir = (tmp_path / "runs") / report["run_id"]
    assert (run_dir / "candidate").exists()
    assert (run_dir / "score.json").exists()


def test_cleanup_can_be_disabled_for_debugging(tmp_path):
    report = _run(tmp_path, cleanup_workspace=False)
    iso_root = tmp_path / "iso"
    workspace = (iso_root / report["run_id"]) / "workspace"
    assert workspace.exists(), "workspace should persist when cleanup is disabled"
