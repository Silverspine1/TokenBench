import json
from pathlib import Path

from tokenbench.agents.loader import load_agent
from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.cli_agent import CliAgentRunner

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "benchmark" / "agents"
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def _dirs(tmp_path: Path):
    workspace = tmp_path / "run" / "workspace"
    logs = tmp_path / "run" / "logs"
    workspace.mkdir(parents=True)
    logs.mkdir(parents=True)
    return workspace, logs


def test_dry_run_agent_exits_zero(tmp_path):
    manifest = load_manifest(MARKETLAB)
    cfg = load_agent(AGENTS, "dry_run_echo")
    workspace, logs = _dirs(tmp_path)

    result = CliAgentRunner(cfg).run(manifest, workspace, logs)

    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.stdout_bytes > 0


def test_dry_run_writes_prompt_and_metadata(tmp_path):
    manifest = load_manifest(MARKETLAB)
    cfg = load_agent(AGENTS, "dry_run_echo")
    workspace, logs = _dirs(tmp_path)
    run_dir = logs.parent

    CliAgentRunner(cfg).run(manifest, workspace, logs)

    prompt = (run_dir / "prompt.txt").read_text(encoding="utf-8")
    assert manifest.prompt in prompt

    meta = json.loads((run_dir / "agent_metadata.json").read_text(encoding="utf-8"))
    assert meta["agent_id"] == "dry_run_echo"
    assert meta["command_template"] == cfg.command_template
    assert meta["exit_code"] == 0
    assert meta["timed_out"] is False
    assert "started_at" in meta and "finished_at" in meta


def test_dry_run_streams_output_to_logs(tmp_path):
    manifest = load_manifest(MARKETLAB)
    cfg = load_agent(AGENTS, "dry_run_echo")
    workspace, logs = _dirs(tmp_path)

    CliAgentRunner(cfg).run(manifest, workspace, logs)

    stdout = (logs / "agent.stdout.log").read_text(encoding="utf-8")
    assert "DRY_RUN_ECHO_AGENT" in stdout


def test_missing_command_does_not_crash(tmp_path):
    """A command that cannot be launched yields a non-zero exit, not an exception."""
    manifest = load_manifest(MARKETLAB)
    cfg = load_agent(AGENTS, "dry_run_echo").model_copy(
        update={"command_template": ["tokenbench_no_such_binary_zzz"]}
    )
    workspace, logs = _dirs(tmp_path)

    result = CliAgentRunner(cfg).run(manifest, workspace, logs)

    assert result.exit_code != 0
    assert result.timed_out is False
