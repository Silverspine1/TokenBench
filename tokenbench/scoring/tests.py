"""Execution of visible and hidden test commands against the workspace."""

from __future__ import annotations

import os
from pathlib import Path

from ..core.subprocess_runner import CommandResult, run_command
from ..manifests.schema import TaskManifest
from .parsing import parse_test_output


def _read_slice(path: Path, start: int) -> str:
    """Read the text appended to ``path`` from byte offset ``start``."""
    if not path.exists():
        return ""
    try:
        with path.open("rb") as fh:
            fh.seek(start)
            return fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _test_env(workspace: Path) -> dict[str, str]:
    """Environment so test commands can import/locate the candidate code.

    ``PYTHONPATH`` is prepended with the workspace so ``import <pkg>`` resolves
    to the candidate copy. ``TOKENBENCH_WORKSPACE`` / ``WORKSPACE`` let
    non-Python tests locate the workspace explicitly.
    """
    env = dict(os.environ)
    ws = str(workspace.resolve())
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = ws + (os.pathsep + existing if existing else "")
    env["TOKENBENCH_WORKSPACE"] = ws
    env["WORKSPACE"] = ws
    return env


def _run_commands(
    commands: list[str],
    cwd: Path,
    workspace: Path,
    timeout_each: float,
    stdout_path: Path,
    stderr_path: Path,
    run_dir: Path,
) -> list[CommandResult]:
    env = _test_env(workspace)
    results: list[CommandResult] = []
    # Truncate phase logs once, then append each command's output.
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_bytes(b"")
    stderr_path.write_bytes(b"")
    for cmd in commands:
        out_before = stdout_path.stat().st_size if stdout_path.exists() else 0
        err_before = stderr_path.stat().st_size if stderr_path.exists() else 0
        result = run_command(
            command=cmd,
            cwd=cwd,
            timeout_seconds=timeout_each,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            env=env,
            log_relative_to=run_dir,
            append=True,
        )
        # Parse just this command's slice of the phase log into a result record.
        result.parsed = parse_test_output(
            command=cmd,
            passed=result.passed,
            stdout_text=_read_slice(stdout_path, out_before),
            stderr_text=_read_slice(stderr_path, err_before),
        )
        results.append(result)
    return results


def run_visible_tests(
    manifest: TaskManifest,
    base_dir: Path,
    workspace: Path,
    run_dir: Path,
    stdout_path: Path,
    stderr_path: Path,
) -> list[CommandResult]:
    # Visible commands are workspace-relative: the agent can run them itself, so
    # they must resolve with the workspace as the working directory.
    return _run_commands(
        manifest.visible_commands,
        workspace,
        workspace,
        manifest.allowed_runtime_seconds,
        stdout_path,
        stderr_path,
        run_dir,
    )


def run_hidden_tests(
    manifest: TaskManifest,
    base_dir: Path,
    workspace: Path,
    run_dir: Path,
    stdout_path: Path,
    stderr_path: Path,
) -> list[CommandResult]:
    # Hidden commands are harness-resolved (external paths) and run from the
    # benchmark base, never from the agent-visible workspace.
    return _run_commands(
        manifest.hidden_commands,
        base_dir,
        workspace,
        manifest.allowed_runtime_seconds,
        stdout_path,
        stderr_path,
        run_dir,
    )
