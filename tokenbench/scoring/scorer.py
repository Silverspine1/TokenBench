"""Deterministic V0.2 scorer.

Pure: given the raw measured facts of a run (``run_state``), the manifest, the
file-change classification, and the dependency-event count, it produces the
canonical ``score.json`` dict. The same inputs always yield the same output.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..manifests.schema import TaskManifest
from .efficiency import composite_efficiency, efficiency_components
from .penalties import count_dependency_events
from .quality import artifact_integrity_score, quality_score_v02
from .schema import ScoreReport
from ..telemetry.collector import write_telemetry

# Success policy thresholds. A run succeeds only when quality and hidden-test
# pass rate both clear the bar and no forbidden path was touched.
#
# hidden_pass_rate is held at 0.9 (not higher): with ~10 hidden cases per hard
# task, 0.9 lets a strong agent miss a single edge case but fails an incomplete
# fix that drops 2+. Pushing it toward 1.0 would make a lone flaky/edge case
# flip the flag, turning success into noise rather than a capability signal.
QUALITY_THRESHOLD = 80.0
HIDDEN_PASS_RATE_THRESHOLD = 0.9


def _phase_counts(results: list[dict]) -> tuple[int, int]:
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    return total, passed


def _test_counts(results: list[dict]) -> tuple[int, int, int, int]:
    """Aggregate per-command parsed test-case counts across a phase.

    Commands without a structured parse count as a single command-level case.
    """
    total = passed = failed = skipped = 0
    for r in results:
        parsed = r.get("parsed")
        if parsed:
            total += int(parsed.get("tests_total", 0))
            passed += int(parsed.get("tests_passed", 0))
            failed += int(parsed.get("tests_failed", 0))
            skipped += int(parsed.get("tests_skipped", 0))
        else:
            total += 1
            if r.get("passed"):
                passed += 1
            else:
                failed += 1
    return total, passed, failed, skipped


def build_score(
    run_state: dict,
    manifest: TaskManifest,
    file_changes: dict,
    dependency_events: int,
    structure_result: dict | None = None,
) -> dict:
    """Compute the score dict from raw facts. Pure and deterministic.

    ``structure_result`` is the deterministic structure-contract scoring for a
    reorg task (see ``scoring.structure``). When present and the task is a reorg,
    quality is recomposed as
    ``0.70*hidden_behavior + 0.25*structure_contract_score + 0.05*artifact``.
    """
    agent = run_state.get("agent", {})
    visible = run_state.get("visible", [])
    hidden = run_state.get("hidden", [])

    v_total, v_passed = _phase_counts(visible)
    h_total, h_passed = _phase_counts(hidden)

    # --- test-case level counts -----------------------------------------
    h_tt, h_tp, h_tf, h_ts = _test_counts(hidden)
    v_tt, v_tp, v_tf, v_ts = _test_counts(visible)
    hidden_pass_rate = (h_tp / h_tt) if h_tt else 0.0
    # No visible tests => neutral full credit on the 0.10 visible weight.
    visible_pass_rate = (v_tp / v_tt) if v_tt else 1.0
    hidden_failed = h_tt > 0 and h_tp < h_tt

    # --- flags -----------------------------------------------------------
    forbidden_modified = len(file_changes.get("forbidden_modified", [])) > 0
    visible_failed = v_total > 0 and v_passed < v_total
    hidden_all_passed = h_total > 0 and h_passed == h_total
    visible_failed_hidden_passed = visible_failed and hidden_all_passed

    agent_timed_out = bool(agent.get("timed_out", False))
    tests_timed_out = any(r.get("timed_out") for r in visible + hidden)
    timed_out = agent_timed_out or tests_timed_out

    patch_empty = not (
        file_changes.get("added")
        or file_changes.get("modified")
        or file_changes.get("deleted")
    )

    # --- quality ---------------------------------------------------------
    artifact = artifact_integrity_score(
        file_changes, patch_empty=patch_empty, hidden_failed=hidden_failed
    )
    quality = quality_score_v02(
        hidden_pass_rate,
        visible_pass_rate,
        artifact,
        forbidden_modified=forbidden_modified,
    )

    # --- reorg quality override -----------------------------------------
    # A reorg task is graded on preserved behaviour + reached structure, not on
    # the visible/hidden split a bugfix uses. Forbidden-path edits remain a hard
    # zero (handled below via the artifact term going to 0 + the success flag).
    reorg_structure = manifest.category.value == "reorg" and structure_result is not None
    if reorg_structure:
        if forbidden_modified:
            quality = 0.0
        else:
            hidden_behavior = hidden_pass_rate * 100.0
            quality = (
                0.70 * hidden_behavior
                + 0.25 * float(structure_result["structure_contract_score"])
                + 0.05 * artifact
            )
            quality = max(0.0, min(100.0, quality))

    # --- usage / timing --------------------------------------------------
    def _sum_bytes(results: list[dict], key: str) -> int:
        return sum(int(r.get(key, 0)) for r in results)

    agent_stdout = int(agent.get("stdout_bytes", 0))
    agent_stderr = int(agent.get("stderr_bytes", 0))
    visible_stdout = _sum_bytes(visible, "stdout_bytes")
    visible_stderr = _sum_bytes(visible, "stderr_bytes")
    hidden_stdout = _sum_bytes(hidden, "stdout_bytes")
    hidden_stderr = _sum_bytes(hidden, "stderr_bytes")
    total_log_bytes = (
        agent_stdout + agent_stderr + visible_stdout + visible_stderr + hidden_stdout + hidden_stderr
    )

    agent_wall = float(agent.get("wall_time_seconds", 0.0))
    visible_wall = sum(float(r.get("wall_time_seconds", 0.0)) for r in visible)
    hidden_wall = sum(float(r.get("wall_time_seconds", 0.0)) for r in hidden)
    total_wall = agent_wall + visible_wall + hidden_wall

    # --- efficiency ------------------------------------------------------
    changed_scored_files = len(file_changes.get("scored_modified", []))
    eff_components = efficiency_components(
        total_wall_time_seconds=total_wall,
        allowed_runtime_seconds=manifest.allowed_runtime_seconds,
        total_log_bytes=total_log_bytes,
        log_budget_bytes=manifest.log_budget_bytes,
        changed_scored_files=changed_scored_files,
        dependency_download_events=dependency_events,
        expected_changed_files_max=manifest.expected_changed_files_max,
    )
    eff = composite_efficiency(eff_components)
    eff_gated = eff * min(quality / 80.0, 1.0)
    final = 0.5 * quality + 0.5 * eff_gated

    # --- success ---------------------------------------------------------
    success = (
        quality >= QUALITY_THRESHOLD
        and hidden_pass_rate >= HIDDEN_PASS_RATE_THRESHOLD
        and not forbidden_modified
    )

    paths = run_state.get("paths", {})

    def _rate(p: int, t: int) -> float:
        return round((p / t) if t else 0.0, 4)

    report = {
        "run_id": run_state["run_id"],
        "condition_id": run_state.get("condition_id", "unspecified"),
        "trial_index": int(run_state.get("trial_index", 0)),
        "repo_id": manifest.repo_id,
        "task_id": manifest.task_id,
        "mode": manifest.mode.value,
        "category": manifest.category.value,
        "difficulty": manifest.difficulty.value,
        "runner": run_state.get("runner", "unknown"),
        "success": bool(success),
        "success_policy": {
            "quality_threshold": QUALITY_THRESHOLD,
            "hidden_pass_rate_threshold": HIDDEN_PASS_RATE_THRESHOLD,
        },
        "quality_score": round(quality, 4),
        "efficiency_score": round(eff, 4),
        # Backward-compatible alias. The efficiency number is a PROXY, not a
        # token-efficiency formula; both names carry the same provisional value.
        "efficiency_proxy_score": round(eff, 4),
        "efficiency_score_kind": "proxy_v0_2",
        "efficiency_gated": round(eff_gated, 4),
        "final_score": round(final, 4),
        "quality_components": {
            "hidden_test_pass_rate": round(hidden_pass_rate, 4),
            "visible_test_pass_rate": round(visible_pass_rate, 4),
            "artifact_integrity_score": round(artifact, 4),
        },
        # Present only for reorg tasks that carry a structure contract.
        "structure_components": structure_result if reorg_structure else None,
        "efficiency_components": eff_components,
        "visible": {"commands_total": v_total, "commands_passed": v_passed},
        "hidden": {"commands_total": h_total, "commands_passed": h_passed},
        "visible_tests": {
            "tests_total": v_tt,
            "tests_passed": v_tp,
            "tests_failed": v_tf,
            "tests_skipped": v_ts,
            "pass_rate": _rate(v_tp, v_tt),
        },
        "hidden_tests": {
            "tests_total": h_tt,
            "tests_passed": h_tp,
            "tests_failed": h_tf,
            "tests_skipped": h_ts,
            "pass_rate": _rate(h_tp, h_tt),
        },
        "penalties": {
            "forbidden_path_modified": forbidden_modified,
            "visible_failed_hidden_passed": visible_failed_hidden_passed,
            "dependency_download_events": dependency_events,
            "timed_out": timed_out,
        },
        "timing": {
            "agent_wall_time_seconds": round(agent_wall, 4),
            "visible_test_wall_time_seconds": round(visible_wall, 4),
            "hidden_test_wall_time_seconds": round(hidden_wall, 4),
            "total_wall_time_seconds": round(total_wall, 4),
        },
        "usage_proxy": {
            "agent_stdout_bytes": agent_stdout,
            "agent_stderr_bytes": agent_stderr,
            "visible_stdout_bytes": visible_stdout,
            "visible_stderr_bytes": visible_stderr,
            "hidden_stdout_bytes": hidden_stdout,
            "hidden_stderr_bytes": hidden_stderr,
            "total_log_bytes": total_log_bytes,
        },
        "paths": {
            "run_dir": paths.get("run_dir", ""),
            "workspace": paths.get("workspace", ""),
            "candidate": paths.get("candidate", ""),
            "patch": paths.get("patch", ""),
            "file_changes": paths.get("file_changes", ""),
        },
        # Raw telemetry lives beside the score; scoring is interpretation, the
        # telemetry artifact is evidence.
        "telemetry_path": "telemetry.json",
    }

    # Validate shape before returning.
    ScoreReport.model_validate(report)
    return report


def score_run(run_dir: Path, manifest: TaskManifest) -> dict:
    """Recompute score.json for an existing run directory from stored artifacts."""
    run_dir = Path(run_dir)
    run_state = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
    file_changes = json.loads((run_dir / "file_changes.json").read_text(encoding="utf-8"))

    logs = run_dir / "logs"
    dependency_events = count_dependency_events(
        [
            logs / "agent.stdout.log",
            logs / "agent.stderr.log",
            logs / "visible_tests.stdout.log",
            logs / "visible_tests.stderr.log",
            logs / "hidden_tests.stdout.log",
            logs / "hidden_tests.stderr.log",
        ]
    )

    structure_result = None
    if manifest.category.value == "reorg" and manifest.structure_contract is not None:
        from .structure import structure_contract_score

        candidate_dir = run_dir / "candidate"
        if candidate_dir.exists():
            structure_result = structure_contract_score(
                manifest.structure_contract, candidate_dir
            )

    report = build_score(
        run_state, manifest, file_changes, dependency_events, structure_result
    )
    (run_dir / "score.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Raw telemetry artifact (separate from scoring). score.json links to it.
    write_telemetry(run_dir, report)
    return report
