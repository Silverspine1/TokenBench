import json
from pathlib import Path

from tokenbench.agents.loader import load_agent
from tokenbench.cli import execute_run
from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.cli_agent import CliAgentRunner
from tokenbench.telemetry.schema import Telemetry

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "benchmark" / "agents"
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_cli_run_writes_telemetry(tmp_path):
    manifest = load_manifest(MARKETLAB)
    runner = CliAgentRunner(load_agent(AGENTS, "dry_run_echo"))

    report = execute_run(
        manifest, ROOT, runner,
        condition_id="dry_run_echo_baseline", trial_index=0,
        overwrite=True, runs_root=tmp_path,
    )

    run_dir = next(p for p in tmp_path.glob("*/") if (p / "score.json").exists())
    tel_path = run_dir / "telemetry.json"
    assert tel_path.exists()

    data = json.loads(tel_path.read_text(encoding="utf-8"))
    # Validates against the schema.
    Telemetry.model_validate(data)

    # Prompt was written for the CLI agent, so prompt size is measured.
    assert data["prompt"]["prompt_bytes"] > 0
    assert data["prompt"]["prompt_estimated_tokens"] > 0

    # Estimated observed tokens present and consistent with the parts.
    parts = (
        data["prompt"]["prompt_estimated_tokens"]
        + data["logs"]["estimated_log_tokens"]
        + data["patch"]["patch_estimated_tokens"]
    )
    assert data["estimates"]["estimated_total_observed_tokens"] == parts
    assert data["estimates"]["token_estimator"] == "chars_div_4_v1"

    # Provider usage exists but is unavailable.
    assert data["provider_usage"]["available"] is False

    # Identity matches the score report.
    assert data["run_id"] == report["run_id"]
    assert data["condition_id"] == "dry_run_echo_baseline"
