"""Assemble telemetry.json from a scored run's artifacts.

Reads the raw facts already written to a run directory (run_state, file_changes,
patch.diff, prompt.txt, logs) plus the computed score report, and produces the
telemetry record. Pure with respect to the filesystem inputs: same artifacts in,
same telemetry out. Does not load whole log files — log volume comes from the
already-measured byte counts in the score report.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..scoring.penalties import collect_install_markers
from .provider_usage import collect_provider_usage
from .schema import (
    ProviderUsage,
    Telemetry,
    TelemetryCommands,
    TelemetryEstimates,
    TelemetryLogs,
    TelemetryPatch,
    TelemetryPrompt,
    TelemetryResults,
    TelemetryTiming,
    TelemetryTokenEstimates,
)
from .token_estimator import ESTIMATOR_NAME, estimate_tokens

# Diff lines that describe structure, not content, and must not count as churn.
_DIFF_HEADER_PREFIXES = ("+++", "---", "@@")


def count_diff_lines(patch_text: str) -> tuple[int, int]:
    """Count added/deleted content lines in a unified diff.

    ``+``/``-`` lines count as additions/deletions. File headers (``+++``,
    ``---``) and hunk headers (``@@``) are ignored.
    """
    added = deleted = 0
    for line in patch_text.splitlines():
        if line.startswith(_DIFF_HEADER_PREFIXES):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            deleted += 1
    return added, deleted


def patch_metrics(patch_path: Path, file_changes: dict) -> dict:
    """Compute patch byte/line/file metrics. Missing patch => zeroed metrics."""
    if patch_path and patch_path.exists():
        text = patch_path.read_text(encoding="utf-8", errors="replace")
        patch_bytes = patch_path.stat().st_size
        lines_added, lines_deleted = count_diff_lines(text)
    else:
        patch_bytes = 0
        lines_added = lines_deleted = 0

    added = file_changes.get("added", [])
    modified = file_changes.get("modified", [])
    deleted = file_changes.get("deleted", [])
    changed_total = len(set(added) | set(modified) | set(deleted))

    return {
        "changed_files_total": changed_total,
        "changed_scored_files": len(file_changes.get("scored_modified", [])),
        "changed_ignored_files": len(file_changes.get("ignored_modified", [])),
        "changed_forbidden_files": len(file_changes.get("forbidden_modified", [])),
        "added_files": len(added),
        "modified_files": len(modified),
        "deleted_files": len(deleted),
        "patch_bytes": patch_bytes,
        "patch_estimated_tokens": estimate_tokens(patch_bytes),
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "line_churn": lines_added + lines_deleted,
    }


def prompt_metrics(prompt_path: Path) -> dict:
    """Compute prompt size metrics. Missing prompt => zeroed metrics."""
    if prompt_path and prompt_path.exists():
        text = prompt_path.read_text(encoding="utf-8", errors="replace")
        prompt_chars = len(text)
        prompt_bytes = prompt_path.stat().st_size
    else:
        prompt_chars = 0
        prompt_bytes = 0
    return {
        "prompt_chars": prompt_chars,
        "prompt_bytes": prompt_bytes,
        "prompt_estimated_tokens": estimate_tokens(prompt_bytes),
    }


def _agent_command(run_dir: Path, run_state: dict) -> tuple[list[str], str | None]:
    """Recover the agent command and agent_id without provider-specific logic."""
    meta_path = run_dir / "agent_metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        command = list(meta.get("command_template", []) or [])
        return command, meta.get("agent_id")

    prov = run_state.get("agent", {}).get("provider_metadata", {}) or {}
    if prov.get("command_template"):
        return list(prov["command_template"]), prov.get("agent_id")
    if isinstance(prov.get("command"), str):
        return [prov["command"]], prov.get("agent_id")
    return [], None


def build_telemetry(run_dir: Path, report: dict) -> Telemetry:
    """Build the telemetry record from a run dir and its score report."""
    run_dir = Path(run_dir)

    def _load(name: str) -> dict:
        p = run_dir / name
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    run_state = _load("run_state.json")
    file_changes = _load("file_changes.json")

    timing = report.get("timing", {})
    usage = report.get("usage_proxy", {})
    penalties = report.get("penalties", {})
    visible_tests = report.get("visible_tests", {})
    hidden_tests = report.get("hidden_tests", {})

    total_log_bytes = int(usage.get("total_log_bytes", 0))

    pm = patch_metrics(run_dir / "patch.diff", file_changes)
    prm = prompt_metrics(run_dir / "prompt.txt")

    logs_dir = run_dir / "logs"
    install_markers = collect_install_markers(
        [
            logs_dir / "agent.stdout.log",
            logs_dir / "agent.stderr.log",
            logs_dir / "visible_tests.stdout.log",
            logs_dir / "visible_tests.stderr.log",
            logs_dir / "hidden_tests.stdout.log",
            logs_dir / "hidden_tests.stderr.log",
        ]
    )

    agent_command, agent_id = _agent_command(run_dir, run_state)

    visible_n = len(run_state.get("visible", []))
    hidden_n = len(run_state.get("hidden", []))

    estimated_log_tokens = estimate_tokens(total_log_bytes)
    estimated_total = (
        prm["prompt_estimated_tokens"]
        + estimated_log_tokens
        + pm["patch_estimated_tokens"]
    )

    # --- token breakdown (input / output / tool / patch) ------------------
    agent_stdout_bytes = int(usage.get("agent_stdout_bytes", 0))
    agent_stderr_bytes = int(usage.get("agent_stderr_bytes", 0))
    visible_bytes = int(usage.get("visible_stdout_bytes", 0)) + int(
        usage.get("visible_stderr_bytes", 0)
    )
    hidden_bytes = int(usage.get("hidden_stdout_bytes", 0)) + int(
        usage.get("hidden_stderr_bytes", 0)
    )

    prompt_input_tokens = prm["prompt_estimated_tokens"]
    agent_stdout_tokens = estimate_tokens(agent_stdout_bytes)
    agent_stderr_tokens = estimate_tokens(agent_stderr_bytes)
    agent_total_output_tokens = agent_stdout_tokens + agent_stderr_tokens
    visible_test_tokens = estimate_tokens(visible_bytes)
    hidden_test_tokens = estimate_tokens(hidden_bytes)
    tool_test_tokens = visible_test_tokens + hidden_test_tokens
    patch_tokens = pm["patch_estimated_tokens"]
    # Sum the per-source token estimates so the total reconciles exactly with
    # its parts (each part is independently ceil-rounded).
    total_observed_tokens = (
        prompt_input_tokens
        + agent_total_output_tokens
        + tool_test_tokens
        + patch_tokens
    )

    token_estimates = TelemetryTokenEstimates(
        estimator=ESTIMATOR_NAME,
        prompt_input_tokens=prompt_input_tokens,
        agent_stdout_output_tokens=agent_stdout_tokens,
        agent_stderr_output_tokens=agent_stderr_tokens,
        agent_total_output_tokens=agent_total_output_tokens,
        visible_test_output_tokens=visible_test_tokens,
        hidden_test_output_tokens=hidden_test_tokens,
        tool_test_output_tokens=tool_test_tokens,
        patch_tokens=patch_tokens,
        total_observed_tokens=total_observed_tokens,
    )

    provider_usage: ProviderUsage = collect_provider_usage(
        run_dir, {"agent_id": agent_id, "agent_command": agent_command}
    )

    return Telemetry(
        run_id=report.get("run_id", run_state.get("run_id", "")),
        repo_id=report.get("repo_id", ""),
        task_id=report.get("task_id", ""),
        condition_id=report.get("condition_id", "unspecified"),
        agent_id=agent_id,
        trial_index=int(report.get("trial_index", run_state.get("trial_index", 0))),
        timing=TelemetryTiming(
            agent_wall_time_seconds=float(timing.get("agent_wall_time_seconds", 0.0)),
            visible_test_wall_time_seconds=float(
                timing.get("visible_test_wall_time_seconds", 0.0)
            ),
            hidden_test_wall_time_seconds=float(
                timing.get("hidden_test_wall_time_seconds", 0.0)
            ),
            total_wall_time_seconds=float(timing.get("total_wall_time_seconds", 0.0)),
        ),
        prompt=TelemetryPrompt(**prm),
        logs=TelemetryLogs(
            agent_stdout_bytes=int(usage.get("agent_stdout_bytes", 0)),
            agent_stderr_bytes=int(usage.get("agent_stderr_bytes", 0)),
            visible_stdout_bytes=int(usage.get("visible_stdout_bytes", 0)),
            visible_stderr_bytes=int(usage.get("visible_stderr_bytes", 0)),
            hidden_stdout_bytes=int(usage.get("hidden_stdout_bytes", 0)),
            hidden_stderr_bytes=int(usage.get("hidden_stderr_bytes", 0)),
            total_log_bytes=total_log_bytes,
            estimated_log_tokens=estimated_log_tokens,
        ),
        patch=TelemetryPatch(**pm),
        commands=TelemetryCommands(
            agent_command=agent_command,
            visible_commands_run=visible_n,
            hidden_commands_run=hidden_n,
            test_commands_total=visible_n + hidden_n,
            dependency_download_events=int(
                penalties.get("dependency_download_events", 0)
            ),
            detected_install_markers=install_markers,
        ),
        results=TelemetryResults(
            visible_pass_rate=float(visible_tests.get("pass_rate", 0.0)),
            hidden_pass_rate=float(hidden_tests.get("pass_rate", 0.0)),
            quality_score=float(report.get("quality_score", 0.0)),
            success=bool(report.get("success", False)),
            final_score=float(report.get("final_score", 0.0)),
        ),
        provider_usage=provider_usage,
        token_estimates=token_estimates,
        estimates=TelemetryEstimates(
            estimated_total_observed_tokens=estimated_total,
            token_estimator=ESTIMATOR_NAME,
        ),
    )


def write_telemetry(run_dir: Path, report: dict) -> dict:
    """Build telemetry, write ``telemetry.json``, and return it as a dict."""
    run_dir = Path(run_dir)
    telemetry = build_telemetry(run_dir, report)
    data = telemetry.model_dump()
    (run_dir / "telemetry.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    return data
