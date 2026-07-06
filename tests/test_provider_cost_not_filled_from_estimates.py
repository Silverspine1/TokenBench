"""Provider cost is parsed from the provider's own output or stays null.

Estimated tokens must never be promoted into provider cost/usage.
"""

import json
from pathlib import Path

from tokenbench.telemetry.provider_usage import collect_provider_usage


def _run_with_stdout(tmp_path: Path, text: str) -> Path:
    logs = tmp_path / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "agent.stdout.log").write_text(text, encoding="utf-8")
    return tmp_path


def test_non_json_stdout_stays_unavailable(tmp_path):
    # A plain-text agent transcript carries no provider accounting.
    run_dir = _run_with_stdout(tmp_path, "DRY_RUN_ECHO_AGENT: no edits made.\n")
    pu = collect_provider_usage(run_dir, {})
    assert pu.available is False
    assert pu.source is None
    assert pu.cost_usd is None
    assert pu.total_tokens is None
    assert pu.raw == {}


def test_missing_stdout_stays_unavailable(tmp_path):
    pu = collect_provider_usage(tmp_path, {})
    assert pu.available is False
    assert pu.cost_usd is None


def test_claude_json_populates_from_provider_not_estimates(tmp_path):
    # A real Claude Code --output-format json result: cost and usage come from
    # the provider, not from any local estimate.
    result = {
        "type": "result", "subtype": "success", "is_error": False,
        "total_cost_usd": 0.0531,
        "usage": {
            "input_tokens": 1200, "output_tokens": 340,
            "cache_read_input_tokens": 50, "cache_creation_input_tokens": 10,
        },
    }
    run_dir = _run_with_stdout(tmp_path, json.dumps(result))
    pu = collect_provider_usage(run_dir, {})
    assert pu.available is True
    assert pu.source == "claude_cli_json"
    assert pu.cost_usd == 0.0531
    assert pu.input_tokens == 1200
    assert pu.output_tokens == 340
    assert pu.cache_read_tokens == 50
    assert pu.cache_write_tokens == 10
    # total = sum of the provider's own token parts (1200+340+50+10).
    assert pu.total_tokens == 1600
    # Claude reports no separate reasoning-token count in this payload.
    assert pu.reasoning_tokens is None


def test_stream_json_last_result_wins(tmp_path):
    lines = [
        json.dumps({"type": "assistant", "message": "working"}),
        json.dumps({"type": "result", "total_cost_usd": 0.02,
                    "usage": {"input_tokens": 10, "output_tokens": 5}}),
    ]
    run_dir = _run_with_stdout(tmp_path, "\n".join(lines))
    pu = collect_provider_usage(run_dir, {})
    assert pu.available is True
    assert pu.cost_usd == 0.02
    assert pu.total_tokens == 15
