"""Safe subprocess wrapper. Streams output to files, never buffers in memory."""

from __future__ import annotations

import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CommandResult:
    command: str
    exit_code: int
    passed: bool
    timed_out: bool
    wall_time_seconds: float
    stdout_log: str
    stderr_log: str
    stdout_bytes: int
    stderr_bytes: int
    parsed: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def run_command(
    command: str,
    cwd: Path,
    timeout_seconds: float,
    stdout_path: Path,
    stderr_path: Path,
    env: dict[str, str] | None = None,
    log_relative_to: Path | None = None,
    append: bool = False,
) -> CommandResult:
    """Run ``command`` (shell) in ``cwd``, capturing output to files.

    Output is written directly to file handles so large output never lands in
    process memory. Exit code, timeout, and byte counts are recorded. When
    ``append`` is set the log files are opened in append mode and the reported
    byte counts reflect only the bytes written by this command.
    """
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)

    out_before = stdout_path.stat().st_size if (append and stdout_path.exists()) else 0
    err_before = stderr_path.stat().st_size if (append and stderr_path.exists()) else 0

    mode = "ab" if append else "wb"
    timed_out = False
    start = time.monotonic()
    with stdout_path.open(mode) as out_fh, stderr_path.open(mode) as err_fh:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd),
                stdout=out_fh,
                stderr=err_fh,
                timeout=timeout_seconds,
                env=env,
            )
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = -1
    wall = time.monotonic() - start

    stdout_bytes = (stdout_path.stat().st_size if stdout_path.exists() else 0) - out_before
    stderr_bytes = (stderr_path.stat().st_size if stderr_path.exists() else 0) - err_before

    def _rel(p: Path) -> str:
        if log_relative_to is not None:
            try:
                return p.relative_to(log_relative_to).as_posix()
            except ValueError:
                pass
        return p.as_posix()

    return CommandResult(
        command=command,
        exit_code=exit_code,
        passed=(exit_code == 0 and not timed_out),
        timed_out=timed_out,
        wall_time_seconds=round(wall, 4),
        stdout_log=_rel(stdout_path),
        stderr_log=_rel(stderr_path),
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
    )
