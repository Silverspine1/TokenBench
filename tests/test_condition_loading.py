from pathlib import Path

import pytest

from tokenbench.conditions.loader import load_condition, load_conditions

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ROOT / "benchmark" / "conditions"


def test_loads_all_shipped_conditions():
    conds = load_conditions(CONDITIONS)
    assert set(conds) == {
        "claude_code_baseline",
        "claude_code_graphify",
        "claude_code_caveman",
        "claude_code_haiku_baseline",
        "claude_code_opus_4_8_baseline",
        "manual_generic_ide",
        "manual_cursor_baseline",
        "manual_windsurf_baseline",
        "manual_vscode_agent_baseline",
    }


def test_baseline_fields():
    c = load_condition(CONDITIONS / "claude_code_baseline.json")
    assert c.condition_id == "claude_code_baseline"
    assert c.agent == "claude-code"
    assert c.model == "opus-4.8"
    assert c.tools == []
    assert c.cost_basis == "provider_reported"
    assert c.official is False


def test_graphify_has_tool():
    c = load_condition(CONDITIONS / "claude_code_graphify.json")
    assert "graphify" in c.tools


def test_rejects_unknown_field(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"condition_id":"x","agent":"a","model":"m","bogus":1}', encoding="utf-8")
    with pytest.raises(Exception):
        load_condition(p)
