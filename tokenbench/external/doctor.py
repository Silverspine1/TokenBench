"""Doctor checks for external-repo tasks and suites."""

from __future__ import annotations

import json
import subprocess
import tempfile
import shutil
from pathlib import Path

from .inspector import load_source, inspect_external_repo
from .leakage import scan_task_for_leakage
from .workspace import materialize_external_workspace, ExternalWorkspaceError
from ..core.paths import RunPaths
from ..core.ids import generate_run_id


def _run_commands(commands: list[str], cwd: Path, timeout: int = 120) -> dict:
    results = []
    for cmd in commands:
        try:
            r = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            results.append({
                "command": cmd,
                "returncode": r.returncode,
                "passed": r.returncode == 0,
                "stdout": r.stdout[:2000],
                "stderr": r.stderr[:2000],
            })
        except subprocess.TimeoutExpired:
            results.append({
                "command": cmd,
                "returncode": -1,
                "passed": False,
                "stdout": "",
                "stderr": "TIMEOUT",
            })
    return {"commands": results, "all_passed": all(r["passed"] for r in results)}


def doctor_external_repo(source_path: Path) -> dict:
    """Validate that an external repo source is inspectable and functional."""
    report = inspect_external_repo(source_path)
    source = load_source(source_path)
    clone_dir = source_path.parent / "cache" / ".git_clone"

    errors = []
    warnings = list(report.get("warnings", []))

    if not report["clone_exists"]:
        errors.append(f"Clone not found: {clone_dir}")
        return {
            "source_path": source_path.as_posix(),
            "errors": errors,
            "warnings": warnings,
            "passed": False,
            **report,
        }

    # Check commit integrity
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=clone_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        actual_commit = result.stdout.strip()
        if not source.pinned_commit.startswith(actual_commit[:7]) and not actual_commit.startswith(source.pinned_commit[:7]):
            warnings.append(
                f"HEAD commit {actual_commit} differs from pinned {source.pinned_commit}"
            )
    except Exception as e:
        warnings.append(f"Could not verify commit: {e}")

    if not source.license:
        errors.append("license field is empty")

    mf = report.get("meaningful_file_count")
    if mf is not None and mf < 200:
        errors.append(f"meaningful_file_count={mf} is critically low (< 200)")
    elif mf is not None and mf < 500:
        warnings.append(f"meaningful_file_count={mf} below 500-900 target")

    return {
        "source_path": source_path.as_posix(),
        "errors": errors,
        "warnings": warnings,
        "passed": len(errors) == 0,
        **report,
    }


def doctor_external_task(manifest_path: Path, base_dir: Path | None = None) -> dict:
    """Validate a single external-repo task manifest."""
    if base_dir is None:
        base_dir = Path.cwd()

    errors: list[str] = []
    warnings: list[str] = []

    # Load manifest
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"manifest_path": str(manifest_path), "errors": [str(e)], "warnings": [], "passed": False}

    task_id = manifest.get("task_id", "unknown")
    task_dir = manifest_path.parent

    # Check source ref
    source_ref = manifest.get("source_ref", "")
    if not source_ref:
        errors.append("source_ref is missing")
    else:
        source_path = base_dir / source_ref
        if not source_path.exists():
            errors.append(f"source_ref not found: {source_path}")
        else:
            try:
                source = load_source(source_path)
            except Exception as e:
                errors.append(f"Could not load source.json: {e}")
                source = None

    # Check defect patch exists (bug-fix tasks)
    category = manifest.get("category", "")
    if category == "bugfix":
        defect_patch = task_dir / "defect.patch"
        if not defect_patch.exists():
            errors.append("defect.patch not found for bugfix task")

    # Check private_notes.json is not in manifest prompt or expected_behavior
    private_notes_path = task_dir / "private_notes.json"
    if not private_notes_path.exists():
        warnings.append("private_notes.json not found (recommended for task authors)")

    # Check visible tests exist
    visible_tests = task_dir / "visible_tests"
    if not visible_tests.exists() or not any(visible_tests.iterdir()):
        warnings.append("visible_tests/ is empty")

    # Check hidden tests exist
    hidden_tests = task_dir / "hidden_tests"
    if not hidden_tests.exists() or not any(hidden_tests.iterdir()):
        errors.append("hidden_tests/ is empty — hidden tests are required")

    # Prompt length check
    prompt = manifest.get("prompt", "")
    if len(prompt.split()) < 20:
        warnings.append(f"Prompt is very short ({len(prompt.split())} words)")

    # Leakage scan
    leakage = scan_task_for_leakage(task_dir)
    if leakage["has_critical"]:
        errors.append(
            f"Critical leakage detected in task files: "
            f"{[f['pattern'] for f in leakage['findings'] if f['severity'] == 'critical']}"
        )
    elif leakage["findings"]:
        warnings.append(
            f"Leakage warnings in task files: "
            f"{[f['pattern'] for f in leakage['findings'] if f['severity'] == 'warning']}"
        )

    return {
        "task_id": task_id,
        "manifest_path": manifest_path.as_posix(),
        "errors": errors,
        "warnings": warnings,
        "leakage": leakage,
        "passed": len(errors) == 0,
    }


def doctor_external_suite(suite_path: Path, base_dir: Path | None = None) -> dict:
    """Validate all external tasks listed in a suite."""
    if base_dir is None:
        base_dir = Path.cwd()

    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    tasks = suite.get("tasks", [])
    staged_groups = suite.get("staged_groups", [])

    all_task_paths = list(tasks)
    for sg in staged_groups:
        all_task_paths.extend(sg.get("stages", []))

    results = []
    errors_total = 0
    warnings_total = 0

    for task_path_str in all_task_paths:
        task_path = base_dir / task_path_str
        if not task_path.exists():
            results.append({
                "task_path": task_path_str,
                "errors": [f"Manifest not found: {task_path}"],
                "warnings": [],
                "passed": False,
            })
            errors_total += 1
            continue

        result = doctor_external_task(task_path, base_dir=base_dir)
        results.append(result)
        errors_total += len(result.get("errors", []))
        warnings_total += len(result.get("warnings", []))

    tasks_total = len(all_task_paths)
    tasks_valid = sum(1 for r in results if r.get("passed"))
    tasks_invalid = tasks_total - tasks_valid

    return {
        "suite_id": suite.get("suite_id", "unknown"),
        "tasks_total": tasks_total,
        "tasks_valid": tasks_valid,
        "tasks_invalid": tasks_invalid,
        "errors_total": errors_total,
        "warnings_total": warnings_total,
        "passed": tasks_invalid == 0,
        "task_results": results,
    }
