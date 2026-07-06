from pathlib import Path

import pytest

from tokenbench.agents.loader import AgentConfigError, load_agent, load_agent_config

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "benchmark" / "agents"


def test_claude_provider_and_default_model():
    cfg = load_agent(AGENTS, "claude_code")
    assert cfg.provider == "claude"
    assert cfg.model == "default"
    assert cfg.model_resolution == "configured"


def test_dry_run_provider_fields():
    cfg = load_agent(AGENTS, "dry_run_echo")
    assert cfg.provider == "dry_run"
    assert cfg.model == "none"
    assert cfg.model_resolution == "configured"


def test_backward_compat_config_without_new_fields(tmp_path):
    p = tmp_path / "legacy.json"
    p.write_text(
        '{"agent_id":"legacy","kind":"cli_agent","command_template":["x"]}',
        encoding="utf-8",
    )
    cfg = load_agent_config(p)
    # Defaults keep older configs loading.
    assert cfg.provider == "unknown"
    assert cfg.model == "unknown"
    assert cfg.model_resolution == "configured"


def test_rejects_unsupported_provider(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(
        '{"agent_id":"x","kind":"cli_agent","command_template":["x"],"provider":"openai"}',
        encoding="utf-8",
    )
    with pytest.raises(AgentConfigError):
        load_agent_config(p)


def test_rejects_unsupported_model_resolution(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(
        '{"agent_id":"x","kind":"cli_agent","command_template":["x"],"model_resolution":"guessed"}',
        encoding="utf-8",
    )
    with pytest.raises(AgentConfigError):
        load_agent_config(p)
