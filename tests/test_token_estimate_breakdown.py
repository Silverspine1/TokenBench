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


def test_token_estimates_section_present_and_validates(tmp_path):
    data = _telemetry(tmp_path)
    Telemetry.model_validate(data)
    te = data["token_estimates"]
    assert te["estimator"] == "chars_div_4_v1"


def test_input_output_tool_patch_are_split(tmp_path):
    te = _telemetry(tmp_path)["token_estimates"]
    # The four buckets exist as distinct fields.
    for key in (
        "prompt_input_tokens",
        "agent_stdout_output_tokens",
        "agent_stderr_output_tokens",
        "agent_total_output_tokens",
        "visible_test_output_tokens",
        "hidden_test_output_tokens",
        "tool_test_output_tokens",
        "patch_tokens",
        "total_observed_tokens",
    ):
        assert key in te
        assert isinstance(te[key], int)

    # Prompt is measured for a CLI agent.
    assert te["prompt_input_tokens"] > 0


def test_breakdown_subtotals_reconcile(tmp_path):
    te = _telemetry(tmp_path)["token_estimates"]
    assert te["agent_total_output_tokens"] == (
        te["agent_stdout_output_tokens"] + te["agent_stderr_output_tokens"]
    )
    assert te["tool_test_output_tokens"] == (
        te["visible_test_output_tokens"] + te["hidden_test_output_tokens"]
    )
    assert te["total_observed_tokens"] == (
        te["prompt_input_tokens"]
        + te["agent_total_output_tokens"]
        + te["tool_test_output_tokens"]
        + te["patch_tokens"]
    )
