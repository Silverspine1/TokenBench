import json
from pathlib import Path

from tokenbench.agents.loader import load_agent
from tokenbench.cli import execute_run
from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.cli_agent import CliAgentRunner

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "benchmark" / "agents"
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_agent_metadata_records_provider_and_model(tmp_path):
    manifest = load_manifest(MARKETLAB)
    runner = CliAgentRunner(load_agent(AGENTS, "dry_run_echo"))

    execute_run(
        manifest, ROOT, runner,
        condition_id="dry_run_echo_baseline", trial_index=0,
        overwrite=True, runs_root=tmp_path,
    )

    run_dir = next(p for p in tmp_path.glob("*/") if (p / "score.json").exists())
    meta = json.loads((run_dir / "agent_metadata.json").read_text(encoding="utf-8"))

    assert meta["agent_id"] == "dry_run_echo"
    assert meta["provider"] == "dry_run"
    assert meta["model_requested"] == "none"
    # Resolved model stays null: the CLI does not reliably report what ran.
    assert meta["model_resolved"] is None
    assert meta["model_resolution_source"] == "configured"
    assert "exit_code" in meta
    assert meta["timed_out"] is False
