import json
from pathlib import Path

from tokenbench.agents.schema import AgentConfig
from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.cli_agent import CliAgentRunner

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_agent_timeout_is_recorded(tmp_path):
    manifest = load_manifest(MARKETLAB)
    cfg = AgentConfig(
        agent_id="sleeper",
        kind="cli_agent",
        command_template=["python", "-c", "import time; time.sleep(30)"],
        supports_stdin_prompt=True,
        default_timeout_seconds=1,
    )
    workspace = tmp_path / "run" / "workspace"
    logs = tmp_path / "run" / "logs"
    workspace.mkdir(parents=True)
    logs.mkdir(parents=True)

    result = CliAgentRunner(cfg).run(manifest, workspace, logs)

    assert result.timed_out is True
    assert result.exit_code == -1

    meta = json.loads((logs.parent / "agent_metadata.json").read_text(encoding="utf-8"))
    assert meta["timed_out"] is True
