"""Manual runner: no AI agent. Lets a human edit the workspace, or skip."""

from __future__ import annotations

from pathlib import Path

from ..core.ids import utc_now
from ..manifests.schema import TaskManifest
from .base import RunnerResult


class ManualRunner:
    name = "manual"

    def __init__(self, skip_agent: bool = False, console=None):
        self.skip_agent = skip_agent
        self.console = console

    def _print(self, msg: str) -> None:
        if self.console is not None:
            self.console.print(msg)
        else:
            print(msg)

    def run(
        self,
        task: TaskManifest,
        workspace: Path,
        logs_dir: Path,
    ) -> RunnerResult:
        started = utc_now()

        self._print("")
        self._print("=== MANUAL RUN ===")
        self._print(f"Task:      {task.task_id}")
        self._print(f"Repo:      {task.repo_id}")
        self._print(f"Prompt:    {task.prompt}")
        self._print(f"Workspace: {workspace}")
        self._print("")

        # Always create empty agent logs so usage accounting is consistent.
        (logs_dir / "agent.stdout.log").touch()
        (logs_dir / "agent.stderr.log").touch()

        if not self.skip_agent:
            self._print(
                "Edit the workspace now, then press Enter to continue to scoring..."
            )
            try:
                input()
            except EOFError:
                # Non-interactive context: behave like --skip-agent.
                pass

        finished = utc_now()
        return RunnerResult(
            exit_code=0,
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            wall_time_seconds=round((finished - started).total_seconds(), 4),
            final_message="manual run (skipped)" if self.skip_agent else "manual run",
            provider_metadata={"runner": self.name, "skip_agent": self.skip_agent},
        )
