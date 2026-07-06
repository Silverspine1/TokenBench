"""Run directory layout. All paths are explicit and derived from the run dir."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Directory names that are never hashed or copied as meaningful state. These are
# generated build/cache artifacts, not candidate source edits, so they must not
# count toward file_changes, patch metrics, churn, or aggregate change metrics.
JUNK_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    # .NET build artifacts (SharpTS and any future C# repo). No benchmark repo
    # tracks a meaningful source dir named bin/ or obj/.
    "bin",
    "obj",
    ".dart_tool",
    "target",
    ".gradle",
    "__pycache__",
    ".pytest_cache",
    "coverage",
    # Knowledge graph the harness builds into the workspace for the graphify
    # treatment condition; must never count as an agent edit (see runners.graphify_build).
    "graphify-out",
}


def is_junk_component(part: str) -> bool:
    """True when a single path component is a generated-artifact dir name.

    Matches the fixed ``JUNK_DIRS`` names plus any component ending in
    ``.egg-info`` (e.g. ``marketlab_ml.egg-info``), which is a Python packaging
    artifact whose exact name varies per project. Component-level matching means
    a *file* like ``coverage.py`` or ``build.js`` is never treated as junk; only
    a directory component named exactly ``coverage`` / ``build`` is.
    """
    return part in JUNK_DIRS or part.endswith(".egg-info")


def is_junk_path(rel: str) -> bool:
    """True when any component of a (posix or windows) relative path is junk."""
    rel = rel.replace("\\", "/")
    return any(is_junk_component(seg) for seg in rel.split("/") if seg)


@dataclass(frozen=True)
class RunPaths:
    """Canonical layout of a single run directory.

    Run artifacts (metadata, candidate, logs, score) always live under
    ``run_dir``. The agent-editable ``workspace`` normally sits inside it too,
    but may be relocated to ``workspace_base`` so the agent's working directory
    is not adjacent to the benchmark tree (``benchmark/tests``,
    ``benchmark/accepted_solutions``). See ``--isolated-runs-root``.
    """

    run_dir: Path
    workspace_base: Path | None = None

    @property
    def metadata(self) -> Path:
        return self.run_dir / "metadata.json"

    @property
    def task_manifest(self) -> Path:
        return self.run_dir / "task_manifest.json"

    @property
    def workspace(self) -> Path:
        return (self.workspace_base or self.run_dir) / "workspace"

    @property
    def candidate(self) -> Path:
        return self.run_dir / "candidate"

    @property
    def logs(self) -> Path:
        return self.run_dir / "logs"

    @property
    def patch(self) -> Path:
        return self.run_dir / "patch.diff"

    @property
    def file_changes(self) -> Path:
        return self.run_dir / "file_changes.json"

    @property
    def score(self) -> Path:
        return self.run_dir / "score.json"

    @property
    def run_state(self) -> Path:
        # Raw measured facts captured during a run, used to recompute score.json.
        return self.run_dir / "run_state.json"

    # --- log files -------------------------------------------------------
    @property
    def agent_stdout(self) -> Path:
        return self.logs / "agent.stdout.log"

    @property
    def agent_stderr(self) -> Path:
        return self.logs / "agent.stderr.log"

    @property
    def visible_stdout(self) -> Path:
        return self.logs / "visible_tests.stdout.log"

    @property
    def visible_stderr(self) -> Path:
        return self.logs / "visible_tests.stderr.log"

    @property
    def hidden_stdout(self) -> Path:
        return self.logs / "hidden_tests.stdout.log"

    @property
    def hidden_stderr(self) -> Path:
        return self.logs / "hidden_tests.stderr.log"

    def ensure_dirs(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
