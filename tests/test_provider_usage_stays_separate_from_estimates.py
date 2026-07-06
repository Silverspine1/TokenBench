import json
from pathlib import Path

from tokenbench.agents.loader import load_agent
from tokenbench.cli import execute_run
from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.cli_agent import CliAgentRunner

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "benchmark" / "agents"
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def _telemetry(tmp_path) -> dict:
    manifest = load_manifest(MARKETLAB)
    runner = CliAgentRunner(load_agent(AGENTS, "dry_run_echo"))
    execute_run(
        manifest, ROOT, runner,
        condition_id="dry_run_echo_baseline", trial_index=0,
        overwrite=True, runs_root=tmp_path,
    )
    run_dir = next(p for p in tmp_path.glob("*/") if (p / "score.json").exists())
    return json.loads((run_dir / "telemetry.json").read_text(encoding="utf-8"))


def test_provider_usage_unavailable_even_when_estimates_exist(tmp_path):
    data = _telemetry(tmp_path)
    te = data["token_estimates"]
    pu = data["provider_usage"]

    # Estimates are real numbers...
    assert te["total_observed_tokens"] > 0

    # ...but provider usage stays unavailable and is NOT filled from estimates.
    assert pu["available"] is False
    assert pu["source"] is None
    for key in (
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_write_tokens",
        "reasoning_tokens",
        "total_tokens",
        "cost_usd",
    ):
        assert pu[key] is None
    assert pu["raw"] == {}


def test_provider_total_not_equal_to_estimated_total(tmp_path):
    data = _telemetry(tmp_path)
    # The estimate must never leak into the provider total.
    assert data["provider_usage"]["total_tokens"] is None
    assert data["token_estimates"]["total_observed_tokens"] > 0
