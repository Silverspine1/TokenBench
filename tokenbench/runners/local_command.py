"""Local command runner: executes a supplied command inside the workspace.

This is a test adapter for validating the harness, not a real model runner.
"""

from __future__ import annotations

from pathlib import Path

from ..core.ids import utc_now
from ..core.subprocess_runner import run_command
from ..manifests.schema import TaskManifest
from .base import RunnerResult


class LocalCommandRunner:
    name = "local-command"

    def __init__(self, command: str):
        if not command or not command.strip():
            raise ValueError("local-command runner requires a non-empty --command")
        self.command = command

    def run(
        self,
        task: TaskManifest,
        workspace: Path,
        logs_dir: Path,
    ) -> RunnerResult:
        started = utc_now()
        result = run_command(
            command=self.command,
            cwd=workspace,
            timeout_seconds=task.allowed_runtime_seconds,
            stdout_path=logs_dir / "agent.stdout.log",
            stderr_path=logs_dir / "agent.stderr.log",
        )
        finished = utc_now()
        return RunnerResult(
            exit_code=result.exit_code,
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            wall_time_seconds=result.wall_time_seconds,
            final_message=self.command,
            provider_metadata={"runner": self.name, "command": self.command},
            stdout_bytes=result.stdout_bytes,
            stderr_bytes=result.stderr_bytes,
            timed_out=result.timed_out,
        )
