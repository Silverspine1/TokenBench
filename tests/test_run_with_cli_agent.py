from pathlib import Path

from tokenbench.agents.loader import load_agent
from tokenbench.cli import execute_run
from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.cli_agent import CliAgentRunner

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "benchmark" / "agents"
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_end_to_end_cli_agent_produces_scored_run(tmp_path):
    manifest = load_manifest(MARKETLAB)
    cfg = load_agent(AGENTS, "dry_run_echo")
    runner = CliAgentRunner(cfg)

    report = execute_run(
        manifest,
        ROOT,
        runner,
        condition_id="dry_run_echo_baseline",
        trial_index=0,
        overwrite=True,
        runs_root=tmp_path,
    )

    # The run is fully scored even though the dry-run agent made no edits.
    assert report["runner"] == "cli-agent"
    assert "success" in report
    assert isinstance(report["success"], bool)
    assert "success_policy" in report
    assert report["condition_id"] == "dry_run_echo_baseline"

    # The harness froze the candidate and wrote agent artifacts.
    run_dirs = list(tmp_path.glob("*/"))
    assert run_dirs
    run_dir = run_dirs[0]
    assert (run_dir / "prompt.txt").exists()
    assert (run_dir / "agent_metadata.json").exists()
    assert (run_dir / "candidate").exists()
    assert (run_dir / "score.json").exists()
