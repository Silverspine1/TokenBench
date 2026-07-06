"""Validate every task in a suite. The suite is valid iff every task is valid."""

from __future__ import annotations

from pathlib import Path

from ..suites.loader import load_suite
from .task_doctor import doctor_task


def doctor_suite(suite_path: Path, base: Path) -> dict:
    """Run ``doctor_task`` for every task in a suite and aggregate the results."""
    suite = load_suite(Path(suite_path))
    task_reports: list[dict] = []
    for task_rel in suite.tasks:
        task_reports.append(doctor_task(base / task_rel, base))

    valid = sum(1 for r in task_reports if r["status"] == "valid")
    invalid = len(task_reports) - valid
    warnings_total = sum(len(r["warnings"]) for r in task_reports)
    errors_total = sum(len(r["errors"]) for r in task_reports)

    return {
        "suite_id": suite.suite_id,
        "status": "valid" if invalid == 0 else "invalid",
        "tasks_total": len(task_reports),
        "tasks_valid": valid,
        "tasks_invalid": invalid,
        "warnings_total": warnings_total,
        "errors_total": errors_total,
        "tasks": task_reports,
    }
