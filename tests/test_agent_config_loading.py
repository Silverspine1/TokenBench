from pathlib import Path

import pytest

from tokenbench.agents.loader import AgentConfigError, load_agent, load_agent_config

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "benchmark" / "agents"


def test_loads_all_shipped_agents():
    for agent_id in ("claude_code", "dry_run_echo"):
        cfg = load_agent(AGENTS, agent_id)
        assert cfg.agent_id == agent_id
        assert cfg.kind == "cli_agent"
        assert cfg.command_template  # non-empty


def test_claude_code_fields():
    cfg = load_agent(AGENTS, "claude_code")
    assert cfg.display_name == "Claude Code"
    assert cfg.command_template == ["claude", "--print"]
    assert cfg.supports_stdin_prompt is True
    assert cfg.default_timeout_seconds == 900


def test_missing_agent_raises():
    with pytest.raises(AgentConfigError):
        load_agent(AGENTS, "does_not_exist")


def test_rejects_unknown_field(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(
        '{"agent_id":"x","kind":"cli_agent","command_template":["x"],"bogus":1}',
        encoding="utf-8",
    )
    with pytest.raises(AgentConfigError):
        load_agent_config(p)


def test_rejects_non_cli_agent_kind(tmp_path):
    p = tmp_path / "k.json"
    p.write_text('{"agent_id":"x","kind":"api_agent","command_template":["x"]}', encoding="utf-8")
    with pytest.raises(AgentConfigError):
        load_agent_config(p)


def test_rejects_empty_command_template(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"agent_id":"x","kind":"cli_agent","command_template":[]}', encoding="utf-8")
    with pytest.raises(AgentConfigError):
        load_agent_config(p)


def test_rejects_non_positive_timeout(tmp_path):
    p = tmp_path / "t.json"
    p.write_text(
        '{"agent_id":"x","kind":"cli_agent","command_template":["x"],"default_timeout_seconds":0}',
        encoding="utf-8",
    )
    with pytest.raises(AgentConfigError):
        load_agent_config(p)
