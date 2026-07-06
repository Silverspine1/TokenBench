"""Runner interface. Provider-agnostic by design."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

from ..manifests.schema import TaskManifest


@dataclass
class RunnerResult:
    exit_code: int
    started_at: str
    finished_at: str
    wall_time_seconds: float
    final_message: str = ""
    provider_metadata: dict = field(default_factory=dict)
    # Byte counts of agent output, filled from log files after the run.
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    timed_out: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class AgentRunner(Protocol):
    name: str

    def run(
        self,
        task: TaskManifest,
        workspace: Path,
        logs_dir: Path,
    ) -> RunnerResult:
        ...
