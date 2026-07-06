"""CLI agent runner: launches a real CLI coding agent as a subprocess.

The runner knows it is launching a CLI process. The scorer does not — it only
ever sees the frozen candidate and the test results. Keep that boundary intact:
nothing provider-specific leaves this module.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from ..agents.schema import AgentConfig
from ..core.ids import utc_now
from ..manifests.schema import TaskManifest
from .base import RunnerResult
from .prompt_builder import build_prompt

# Exit code used when the command itself cannot be launched (e.g. not found).
LAUNCH_FAILED_EXIT = 127


class CliAgentRunner:
    name = "cli-agent"

    def __init__(self, config: AgentConfig):
        self.config = config

    def _timeout(self, task: TaskManifest) -> int:
        # The task budget and the agent default both bound the run; use the
        # tighter of the two.
        return min(self.config.default_timeout_seconds, task.allowed_runtime_seconds)

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update(self.config.env)
        # pip --user installs console scripts (the `graphify` CLI the graphify
        # treatment leans on) into the per-user scripts dir, which is NOT on PATH
        # by default on Windows (%APPDATA%\Python\Python3xx\Scripts). Prepend it so
        # an agent that calls bare `graphify ...` (e.g. via the /graphify skill)
        # resolves it. Benign for other conditions: no graph, no reason to call it.
        import sysconfig

        user_scripts = sysconfig.get_path("scripts", f"{os.name}_user")
        if user_scripts and user_scripts not in env.get("PATH", ""):
            env["PATH"] = user_scripts + os.pathsep + env.get("PATH", "")
        return env

    def run(
        self,
        task: TaskManifest,
        workspace: Path,
        logs_dir: Path,
    ) -> RunnerResult:
        workspace = Path(workspace)
        logs_dir = Path(logs_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
        run_dir = logs_dir.parent

        prompt = build_prompt(task, workspace)
        (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

        argv = list(self.config.command_template)
        # Resolve the executable on PATH. On Windows this turns an npm shim name
        # like "claude" into its launchable "claude.CMD"; subprocess.Popen will
        # not do that resolution itself. No-op when already an absolute path or
        # when resolution fails (the original name is kept so the error surfaces).
        if argv:
            resolved = shutil.which(argv[0])
            if resolved:
                argv[0] = resolved
        # When stdin is not used, hand the prompt over as a trailing argument.
        if not self.config.supports_stdin_prompt:
            argv = argv + [prompt]

        cwd = str(workspace) if self.config.supports_workspace_cwd else None
        timeout = self._timeout(task)
        stdout_path = logs_dir / "agent.stdout.log"
        stderr_path = logs_dir / "agent.stderr.log"

        started = utc_now()
        exit_code = LAUNCH_FAILED_EXIT
        timed_out = False
        launch_error = ""

        start = time.monotonic()
        with stdout_path.open("wb") as out_fh, stderr_path.open("wb") as err_fh:
            try:
                proc = subprocess.Popen(
                    argv,
                    cwd=cwd,
                    env=self._env(),
                    stdin=subprocess.PIPE if self.config.supports_stdin_prompt else None,
                    stdout=out_fh,
                    stderr=err_fh,
                )
            except (FileNotFoundError, OSError) as e:
                launch_error = f"failed to launch {argv[0]!r}: {e}"
                err_fh.write((launch_error + "\n").encode("utf-8"))
                proc = None

            if proc is not None:
                stdin_bytes = (
                    prompt.encode("utf-8") if self.config.supports_stdin_prompt else None
                )
                try:
                    proc.communicate(input=stdin_bytes, timeout=timeout)
                    exit_code = proc.returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
                    proc.kill()
                    proc.communicate()
                    exit_code = -1
        wall = time.monotonic() - start
        finished = utc_now()

        stdout_bytes = stdout_path.stat().st_size if stdout_path.exists() else 0
        stderr_bytes = stderr_path.stat().st_size if stderr_path.exists() else 0

        metadata = {
            "agent_id": self.config.agent_id,
            "provider": self.config.provider,
            # Requested model is whatever the config declared. Resolved model
            # stays null: the CLIs do not reliably report what actually ran, and
            # scraping noisy logs is out of scope.
            "model_requested": self.config.model,
            "model_resolved": None,
            "model_resolution_source": self.config.model_resolution,
            "command_template": list(self.config.command_template),
            "exit_code": exit_code,
            "timed_out": timed_out,
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": stderr_bytes,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
        }
        if launch_error:
            metadata["launch_error"] = launch_error
        (run_dir / "agent_metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

        return RunnerResult(
            exit_code=exit_code,
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            wall_time_seconds=round(wall, 4),
            final_message=launch_error or f"cli-agent {self.config.agent_id} exit={exit_code}",
            provider_metadata=metadata,
            stdout_bytes=stdout_bytes,
            stderr_bytes=stderr_bytes,
            timed_out=timed_out,
        )
