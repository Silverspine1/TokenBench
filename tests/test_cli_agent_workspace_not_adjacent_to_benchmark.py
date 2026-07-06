import json
from pathlib import Path

from tokenbench.agents.loader import load_agent
from tokenbench.cli import execute_run
from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.cli_agent import CliAgentRunner

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "benchmark" / "agents"
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_isolated_workspace_is_outside_benchmark_tree(tmp_path):
    manifest = load_manifest(MARKETLAB)
    runner = CliAgentRunner(load_agent(AGENTS, "dry_run_echo"))

    runs_root = tmp_path / "runs"
    iso_root = tmp_path / "iso"
    report = execute_run(
        manifest,
        ROOT,
        runner,
        condition_id="dry_run_echo",
        trial_index=0,
        overwrite=True,
        runs_root=runs_root,
        isolated_runs_root=iso_root,
    )
    assert report["runner"] == "cli-agent"

    # Artifacts live under runs_root.
    run_dir = next(runs_root.glob("*/"))
    assert (run_dir / "score.json").exists()
    assert (run_dir / "candidate").exists()

    # The agent workspace lives under the isolated root, NOT under the project
    # tree, so `../` cannot reach benchmark/tests or benchmark/accepted_solutions.
    meta = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    workspace = Path(meta["workspace_path"]).resolve()
    assert iso_root.resolve() in workspace.parents
    assert ROOT.resolve() not in workspace.parents
    # No sibling benchmark/ next to the workspace's run root.
    assert not (workspace.parent.parent / "benchmark").exists()
