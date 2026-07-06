"""Manual-IDE run lifecycle: create, submit, score, attach cost, inspect.

Splits an atomic run in time. ``create_manual_run`` materializes the broken
workspace and renders the prompt; the operator then edits it in their IDE;
``submit_manual_run`` freezes the result and scores it through the same
``finalize_run`` path a CLI-agent run uses. State lives in ``manual_ide.json``
beside the standard run artifacts.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.ids import generate_run_id, utc_now
from ..core.paths import RunPaths
from ..core.workspace import materialize_workspace
from ..manifests.schema import TaskManifest
from ..runners.base import RunnerResult
from ..runners.finalize import finalize_run
from ..telemetry.cost_import import attach_cost_to_run
from .public import public_manifest, safe_prompt

RUNNER_NAME = "manual-ide"

# Allowed provenance for a manually-entered cost figure.
COST_SOURCES = (
    "provider_dashboard",
    "ide_usage_panel",
    "api_response",
    "claude_cli_json",
    "manual_estimate",
    "unknown",
)


def _manual_ide_path(run_dir: Path) -> Path:
    return Path(run_dir) / "manual_ide.json"


def _read_manual_ide(run_dir: Path) -> dict:
    p = _manual_ide_path(run_dir)
    if not p.exists():
        raise FileNotFoundError(f"not a manual run (no manual_ide.json): {run_dir}")
    return json.loads(p.read_text(encoding="utf-8"))


def _write_manual_ide(run_dir: Path, data: dict) -> None:
    _manual_ide_path(run_dir).write_text(json.dumps(data, indent=2), encoding="utf-8")


def create_manual_run(
    base: Path,
    manifest: TaskManifest,
    *,
    condition_id: str,
    ide_name: str = "",
    ide_version: Optional[str] = None,
    model_name: str = "user-entered",
    operator_notes: str = "",
    runs_root: Optional[Path] = None,
    overwrite: bool = False,
    override_snapshot: Optional[Path] = None,
    mode: str = "local_workspace",
    stage: Optional[int] = None,
    stage_group_id: str = "",
    previous_run_id: str = "",
) -> dict:
    """Materialize the workspace and prompt for a manual run. No scoring yet.

    Returns a record with the run_id, key paths, the safe prompt, and the public
    manifest. The agent-editable workspace lives inside the run dir so submit can
    always find it.
    """
    base = Path(base)
    run_id = generate_run_id(manifest.repo_id, manifest.task_id)
    runs_root = Path(runs_root) if runs_root else (base / "runs")
    run_paths = RunPaths(runs_root / run_id)

    # Source tree: the broken snapshot, unless a staged Stage 2 overrides it with
    # Stage 1's candidate output.
    materialize_workspace(
        manifest, run_paths, base, overwrite=overwrite, override_snapshot=override_snapshot
    )

    # Persist the manifest used for this run (full manifest — this file is a
    # benchmark artifact, never served to the operator UI).
    run_paths.task_manifest.write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )

    # Render and persist the operator-facing prompt (safe — no hidden commands).
    prompt = safe_prompt(manifest, run_paths.workspace)
    (run_paths.run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    # Empty agent logs keep byte/usage accounting consistent with a real run.
    run_paths.agent_stdout.touch()
    run_paths.agent_stderr.touch()

    baseline = (override_snapshot or (base / manifest.broken_snapshot)).resolve()
    started = utc_now().isoformat()
    record = {
        "run_id": run_id,
        "mode": mode,
        "ide_name": ide_name,
        "ide_version": ide_version,
        "model_name": model_name,
        "condition_id": condition_id,
        "operator_notes": operator_notes,
        "started_at": started,
        "submitted_at": None,
        "workspace_path": run_paths.workspace.as_posix(),
        "candidate_source": "workspace",
        "baseline_snapshot": baseline.as_posix(),
        "stage": stage,
        "stage_group_id": stage_group_id,
        "previous_run_id": previous_run_id,
    }
    _write_manual_ide(run_paths.run_dir, record)

    return {
        "run_id": run_id,
        "run_dir": run_paths.run_dir.as_posix(),
        "workspace_path": run_paths.workspace.as_posix(),
        "prompt": prompt,
        "public_manifest": public_manifest(manifest),
        "manual_ide": record,
    }


def submit_manual_run(base: Path, run_dir: Path) -> dict:
    """Freeze the operator's workspace and score it. Returns the score report."""
    base = Path(base)
    run_dir = Path(run_dir)
    record = _read_manual_ide(run_dir)

    manifest = TaskManifest.model_validate_json(
        (run_dir / "task_manifest.json").read_text(encoding="utf-8")
    )
    run_paths = RunPaths(run_dir)
    if not run_paths.workspace.exists():
        raise FileNotFoundError(f"no workspace to submit: {run_paths.workspace}")

    started_at = record.get("started_at")
    finished = utc_now()
    try:
        started_dt = datetime.fromisoformat(started_at) if started_at else finished
        wall = max(0.0, (finished - started_dt).total_seconds())
    except ValueError:
        wall = 0.0

    result = RunnerResult(
        exit_code=0,
        started_at=started_at or finished.isoformat(),
        finished_at=finished.isoformat(),
        wall_time_seconds=round(wall, 4),
        final_message="manual IDE submission",
        provider_metadata={
            "runner": RUNNER_NAME,
            "ide_name": record.get("ide_name"),
            "model_name": record.get("model_name"),
            "candidate_source": record.get("candidate_source", "workspace"),
        },
    )

    baseline = Path(record.get("baseline_snapshot") or (base / manifest.broken_snapshot))
    report = finalize_run(
        run_paths, manifest, base, result,
        condition_id=record.get("condition_id", "unspecified"),
        trial_index=0,
        runner_name=RUNNER_NAME,
        baseline_snapshot=baseline,
    )

    record["submitted_at"] = finished.isoformat()
    _write_manual_ide(run_dir, record)
    return report


def attach_manual_cost(
    run_dir: Path,
    fields: dict,
    *,
    source: str = "manual_estimate",
    confidence: str = "low",
    notes: str = "",
) -> dict:
    """Attach an operator-entered USD cost to the run's telemetry + manual_cost.json.

    Reuses ``attach_cost_to_run`` so ``provider_usage`` stays the single cost
    schema; ``manual_cost.json`` records provenance (source/confidence/notes).
    """
    run_dir = Path(run_dir)
    if source not in COST_SOURCES:
        raise ValueError(f"unknown cost source: {source!r}; allowed: {COST_SOURCES}")

    telemetry = attach_cost_to_run(run_dir, fields)

    manual_cost = {
        "source": source,
        "confidence": confidence,
        "available": True,
        "notes": notes,
        "entered_at": utc_now().isoformat(),
        "fields": {k: v for k, v in fields.items() if v is not None},
    }
    (run_dir / "manual_cost.json").write_text(
        json.dumps(manual_cost, indent=2), encoding="utf-8"
    )
    return {
        "provider_usage": telemetry.get("provider_usage"),
        "manual_cost": manual_cost,
    }


def run_status(run_dir: Path) -> str:
    """Derive a coarse lifecycle status from the artifacts present on disk."""
    run_dir = Path(run_dir)
    if not _manual_ide_path(run_dir).exists():
        return "not_started"
    if not (run_dir / "score.json").exists():
        workspace = run_dir / "workspace"
        return "workspace_created" if workspace.exists() else "not_started"
    # Scored. Distinguish whether provider cost has been attached.
    tel_path = run_dir / "telemetry.json"
    if tel_path.exists():
        try:
            tel = json.loads(tel_path.read_text(encoding="utf-8"))
            if (tel.get("provider_usage") or {}).get("available"):
                return "complete"
        except (OSError, json.JSONDecodeError):
            pass
    return "cost_missing"


def _score_summary(run_dir: Path) -> Optional[dict]:
    score_path = run_dir / "score.json"
    if not score_path.exists():
        return None
    try:
        s = json.loads(score_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "success": s.get("success"),
        "quality_score": s.get("quality_score"),
        "final_score": s.get("final_score"),
        "hidden_tests": s.get("hidden_tests"),
        "visible_tests": s.get("visible_tests"),
    }


def _public_manifest(run_dir: Path) -> Optional[dict]:
    tm_path = run_dir / "task_manifest.json"
    if not tm_path.exists():
        return None
    try:
        manifest = TaskManifest.model_validate_json(tm_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return public_manifest(manifest)


def get_run(run_dir: Path) -> dict:
    """Return a combined view of one manual run for the console/results screens.

    Includes only the whitelisted ``public`` manifest fields — never the full
    manifest (which carries hidden commands and root-cause notes).
    """
    run_dir = Path(run_dir)
    record = _read_manual_ide(run_dir)
    cost = None
    cost_path = run_dir / "manual_cost.json"
    if cost_path.exists():
        try:
            cost = json.loads(cost_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cost = None
    return {
        "run_id": record.get("run_id", run_dir.name),
        "run_dir": run_dir.as_posix(),
        "status": run_status(run_dir),
        "manual_ide": record,
        "public": _public_manifest(run_dir),
        "score": _score_summary(run_dir),
        "manual_cost": cost,
    }


def list_manual_runs(runs_root: Path) -> list[dict]:
    """Summaries of every manual run under ``runs_root`` (newest run_id first)."""
    runs_root = Path(runs_root)
    if not runs_root.exists():
        return []
    out: list[dict] = []
    for ide_path in runs_root.glob("*/manual_ide.json"):
        run_dir = ide_path.parent
        try:
            out.append(get_run(run_dir))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    out.sort(key=lambda r: r["run_id"], reverse=True)
    return out
