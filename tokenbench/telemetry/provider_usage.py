"""Provider-reported usage collection.

Provider usage is allowed to be unavailable: the default is an empty,
``available=False`` record. When a CLI agent emits a machine-readable result
(e.g. Claude Code's ``--output-format json``), we parse the provider-reported
cost and token usage out of the captured stdout log. Estimates are NEVER used
to fill these fields — an unparseable or absent result stays ``available=False``
with null figures.
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import ProviderUsage


def collect_provider_usage(run_dir: Path, agent_metadata: dict) -> ProviderUsage:
    """Return provider usage for a run.

    Looks for a Claude Code JSON result in ``logs/agent.stdout.log``. If found,
    populates cost and tokens from the provider's own accounting (``source =
    "claude_cli_json"``). Otherwise returns an unavailable record. No estimate
    ever leaks into these fields.
    """
    run_dir = Path(run_dir)
    stdout_log = run_dir / "logs" / "agent.stdout.log"
    parsed = _parse_claude_json(stdout_log)
    if parsed is None:
        return ProviderUsage(available=False, source=None, raw={})
    return parsed


def _parse_claude_json(stdout_log: Path) -> ProviderUsage | None:
    """Parse a Claude Code JSON result log into ProviderUsage, or None.

    Handles both ``--output-format json`` (one JSON object) and
    ``--output-format stream-json`` (one JSON object per line, last ``result``
    event wins). Returns None when the log is missing, not JSON, or carries no
    usage/cost accounting.
    """
    if not stdout_log.exists():
        return None
    try:
        text = stdout_log.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not text:
        return None

    result = _extract_result_object(text)
    if result is None:
        return None

    usage = result.get("usage")
    cost = result.get("total_cost_usd")
    has_usage = isinstance(usage, dict)
    has_cost = isinstance(cost, (int, float))
    if not has_usage and not has_cost:
        return None

    usage = usage if has_usage else {}
    input_tokens = _as_int(usage.get("input_tokens"))
    output_tokens = _as_int(usage.get("output_tokens"))
    cache_read = _as_int(usage.get("cache_read_input_tokens"))
    cache_write = _as_int(usage.get("cache_creation_input_tokens"))

    token_parts = [t for t in (input_tokens, output_tokens, cache_read, cache_write) if t is not None]
    total_tokens = sum(token_parts) if token_parts else None

    return ProviderUsage(
        available=True,
        source="claude_cli_json",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_write_tokens=cache_write,
        # Claude does not report a separate reasoning-token count in this payload.
        reasoning_tokens=None,
        total_tokens=total_tokens,
        cost_usd=float(cost) if has_cost else None,
        raw=result,
    )


def _extract_result_object(text: str) -> dict | None:
    """Find the result object in a json or stream-json transcript."""
    # Plain --output-format json: the whole log is one object.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # stream-json: newline-delimited objects; the final type=="result" wins.
    result: dict | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("type") == "result":
            result = obj
    return result


def _as_int(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None
