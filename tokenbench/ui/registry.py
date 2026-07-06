"""Non-HTTP helpers shared by the UI routers.

Enumerates suites, tasks, and conditions through the existing loaders and joins
each task to its latest manual run. Pure read helpers — nothing here mutates a
run; that is the manual service's job.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..conditions.loader import load_condition
from ..manifests.loader import load_manifest
from ..manifests.schema import TaskManifest
from ..manual.public import public_manifest
from ..manual.service import list_manual_runs
from ..suites.loader import load_suite


def suites_dir(base: Path) -> Path:
    return Path(base) / "benchmark" / "suites"


def conditions_dir(base: Path) -> Path:
    return Path(base) / "benchmark" / "conditions"


def runs_root(base: Path) -> Path:
    return Path(base) / "runs"


def list_suites(base: Path) -> list[dict]:
    """Every suite under ``benchmark/suites`` with task counts."""
    out: list[dict] = []
    for path in sorted(suites_dir(base).glob("*.json")):
        try:
            suite = load_suite(path)
        except Exception:  # a malformed suite file should not break the list
            continue
        out.append(
            {
                "suite_id": suite.suite_id,
                "description": suite.description,
                "task_count": len(suite.tasks),
                "required_trials": suite.required_trials,
                "official": suite.official,
                "path": path.name,
            }
        )
    return out


def _find_suite(base: Path, suite_id: str):
    for path in suites_dir(base).glob("*.json"):
        try:
            suite = load_suite(path)
        except Exception:
            continue
        if suite.suite_id == suite_id:
            return suite
    return None


def _latest_runs_by_task(base: Path) -> dict[str, dict]:
    """Map task_id -> its newest manual run summary (list is newest-first)."""
    by_task: dict[str, dict] = {}
    for run in list_manual_runs(runs_root(base)):
        manifest = run.get("manual_ide", {})
        # task_id is not on manual_ide; pull from the score summary when present.
        score = run.get("score") or {}
        task_id = score.get("task_id") or manifest.get("task_id")
        if not task_id:
            # Recover task_id from the run's persisted manifest.
            tm_path = Path(run["run_dir"]) / "task_manifest.json"
            if tm_path.exists():
                try:
                    task_id = json.loads(tm_path.read_text(encoding="utf-8")).get("task_id")
                except (OSError, json.JSONDecodeError):
                    task_id = None
        if task_id and task_id not in by_task:
            by_task[task_id] = run
    return by_task


def suite_tasks(base: Path, suite_id: str) -> Optional[list[dict]]:
    """Public task rows for a suite, joined to each task's latest manual run."""
    suite = _find_suite(base, suite_id)
    if suite is None:
        return None
    latest = _latest_runs_by_task(base)
    rows: list[dict] = []
    for task_rel in suite.tasks:
        try:
            manifest = load_manifest(Path(base) / task_rel)
        except Exception:
            continue
        pub = public_manifest(manifest)
        run = latest.get(manifest.task_id)
        rows.append(
            {
                "task_rel": task_rel,
                "task_id": pub["task_id"],
                "repo_id": pub["repo_id"],
                "category": pub["category"],
                "difficulty": pub["difficulty"],
                "status": run["status"] if run else "not_started",
                "latest_run_id": run["run_id"] if run else None,
                "latest_score": (run.get("score") if run else None),
            }
        )
    return rows


def load_task(base: Path, task_rel: str) -> TaskManifest:
    return load_manifest(Path(base) / task_rel)


def list_conditions(base: Path) -> list[dict]:
    """Manual conditions available to attach to a run."""
    out: list[dict] = []
    for path in sorted(conditions_dir(base).glob("*.json")):
        try:
            cond = load_condition(path)
        except Exception:
            continue
        out.append(
            {
                "condition_id": cond.condition_id,
                "description": cond.description,
                "official": cond.official,
            }
        )
    return out
