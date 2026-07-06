"""End-to-end validation of a single benchmark task.

A task is admitted only when:
  * gold passes both visible and hidden tests
  * the broken snapshot fails at least one hidden test
  * hidden tests live outside the candidate (scored) workspace
  * the prompt is fair: it leaks neither hidden commands nor private solution notes
  * path policies are internally consistent

Anything that breaks those guarantees is a hard error. Softer concerns (missing
accepted-solution snapshot, suspicious file-count bounds) are warnings.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from ..core.paths import is_junk_component
from ..core.workspace import copy_tree
from ..manifests.loader import load_manifest
from ..manifests.schema import TaskManifest
from ..manifests.validator import validate_manifest
from ..scoring.tests import run_hidden_tests, run_visible_tests
from .leakage import has_critical_leakage, scan_broken_snapshot_leakage
from .pathspec import (
    command_path_tokens,
    path_under,
    patterns_overlap,
)

# Cap per-command runtime during doctoring so a wedged snapshot cannot hang the
# whole validation pass on a task that declares a large allowed_runtime_seconds.
DOCTOR_TIMEOUT_CAP_SECONDS = 120

# Substrings that mean a visible command could not be *located/run* at all (as
# opposed to running and failing an assertion). These make a visible command
# invalid even though visible failures on the broken snapshot are allowed.
_MISSING_PATH_MARKERS = (
    "no such file or directory",
    "file or directory not found",
    "cannot find module",
    "can't open file",
    "errno 2",
)


def _missing_path_marker(text: str) -> str:
    low = text.lower()
    for marker in _MISSING_PATH_MARKERS:
        if marker in low:
            return marker
    return ""


def _all_passed(results: list) -> bool:
    """Command-level pass: every command exited 0 (empty list == passed)."""
    return all(r.passed for r in results)


def _run_snapshot(manifest: TaskManifest, base: Path, snapshot: Path) -> dict:
    """Materialize ``snapshot`` into a temp workspace and run visible+hidden tests."""
    tmp = Path(tempfile.mkdtemp(prefix="tb_doctor_"))
    capped = _capped_manifest(manifest)
    try:
        ws = tmp / "workspace"
        copy_tree(snapshot, ws)
        logs = tmp / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        v_out, v_err = logs / "v.out", logs / "v.err"
        visible = run_visible_tests(capped, base, ws, tmp, v_out, v_err)
        hidden = run_hidden_tests(
            capped, base, ws, tmp, logs / "h.out", logs / "h.err"
        )
        visible_log = _safe_read(v_out) + "\n" + _safe_read(v_err)
        v_out_bytes = v_out.stat().st_size if v_out.exists() else 0
        v_err_bytes = v_err.stat().st_size if v_err.exists() else 0
        return {
            "visible_passed": _all_passed(visible),
            "hidden_passed": _all_passed(hidden),
            "visible_missing_path": _missing_path_marker(visible_log),
            "visible_output_bytes": v_out_bytes + v_err_bytes,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _capped_manifest(manifest: TaskManifest) -> TaskManifest:
    if manifest.allowed_runtime_seconds <= DOCTOR_TIMEOUT_CAP_SECONDS:
        return manifest
    return manifest.model_copy(update={"allowed_runtime_seconds": DOCTOR_TIMEOUT_CAP_SECONDS})


def _check_path_policies(manifest: TaskManifest, errors: list[str]) -> None:
    for f in manifest.forbidden_paths:
        for s in manifest.scored_paths:
            if patterns_overlap(f, s):
                errors.append(f"forbidden path '{f}' overlaps scored path '{s}'")
    for i in manifest.ignored_paths:
        for f in manifest.forbidden_paths:
            if patterns_overlap(i, f):
                errors.append(f"ignored path '{i}' overlaps forbidden path '{f}'")


def _check_test_locations(
    manifest: TaskManifest, errors: list[str], warnings: list[str]
) -> None:
    def classify(commands: list[str], is_hidden: bool) -> None:
        for cmd in commands:
            for tok in command_path_tokens(cmd):
                under_scored = any(path_under(tok, s) for s in manifest.scored_paths)
                under_forbidden = any(
                    path_under(tok, f) for f in manifest.forbidden_paths
                )
                kind = "hidden" if is_hidden else "visible"
                if under_scored:
                    msg = (
                        f"{kind} test path '{tok}' is inside a scored "
                        f"(candidate-editable) path"
                    )
                    if is_hidden:
                        errors.append(msg)
                    else:
                        warnings.append(msg + " (intentionally visible?)")
                elif not under_forbidden and is_hidden:
                    # Hidden tests must live outside candidate-editable space.
                    # Visible commands are workspace-relative by design.
                    warnings.append(
                        f"{kind} test path '{tok}' is not under any forbidden path"
                    )

    classify(manifest.visible_commands, is_hidden=False)
    classify(manifest.hidden_commands, is_hidden=True)


def _check_prompt(manifest: TaskManifest, errors: list[str]) -> None:
    """Render the agent prompt and assert it leaks nothing private.

    The prompt is the only thing the agent sees. It must not expose hidden test
    commands/paths, private author notes, the expected-failure summary, the
    root-cause file list, or accepted-solution / hidden-test directory paths.
    """
    from ..runners.prompt_builder import build_prompt

    prompt = build_prompt(manifest, manifest.broken_snapshot)
    low = prompt.lower()

    if "hidden test" in low or "hidden command" in low:
        errors.append("prompt mentions hidden tests")
    for cmd in manifest.hidden_commands:
        if cmd and cmd in prompt:
            errors.append("prompt leaks a hidden test command")
            break
    if manifest.task_author_notes and manifest.task_author_notes in prompt:
        errors.append("prompt leaks private task_author_notes")
    if manifest.expected_failure_summary and manifest.expected_failure_summary in prompt:
        errors.append("prompt leaks the private expected_failure_summary")
    for rcf in manifest.root_cause_files:
        if rcf and rcf in prompt:
            errors.append(f"prompt leaks a private root_cause_file: {rcf}")
            break
    if "accepted_solutions" in low:
        errors.append("prompt leaks an accepted_solutions path")
    if "benchmark/tests" in low.replace("\\", "/"):
        errors.append("prompt leaks an external hidden-test path (benchmark/tests)")

    # The manifest's own prompt text is what build_prompt embeds; also guard it
    # directly so an authored prompt can never smuggle these in past rendering.
    raw = manifest.prompt
    if manifest.task_author_notes and manifest.task_author_notes in raw:
        errors.append("prompt text contains private task_author_notes")


def _check_metadata(manifest: TaskManifest, errors: list[str], warnings: list[str]) -> None:
    # category/difficulty/dependency_policy are enum-typed and always present.
    if manifest.allowed_runtime_seconds <= 0:
        errors.append("allowed_runtime_seconds must be positive")
    lo, hi = manifest.expected_changed_files_min, manifest.expected_changed_files_max
    if lo is not None and lo < 0:
        warnings.append("expected_changed_files_min is negative")
    if lo is not None and hi is not None and lo > hi:
        warnings.append("expected_changed_files_min > expected_changed_files_max")


def scan_generated_artifacts(root: Path) -> list[str]:
    """Return sorted relative dirs under ``root`` that are generated artifacts.

    A committed snapshot should hold source only — generated build/cache dirs
    (``*.egg-info``, ``__pycache__``, ``.pytest_cache``, ``node_modules``,
    ``.next``, ``dist``, ``build``, etc.) indicate the snapshot was captured
    after a build/test run and should be cleaned. Only the top generated dir is
    reported, not its children.
    """
    if not root.exists():
        return []
    found: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        if is_junk_component(path.name):
            found.add(path.relative_to(root).as_posix())
    # Drop nested dirs already covered by a reported parent.
    top = {d for d in found if not any(d != o and d.startswith(o + "/") for o in found)}
    return sorted(top)


def _check_snapshot_artifacts(manifest: TaskManifest, base: Path, warnings: list[str]) -> None:
    for label, rel in (("gold", manifest.gold_snapshot), ("broken", manifest.broken_snapshot)):
        for d in scan_generated_artifacts(base / rel):
            warnings.append(
                f"{label} snapshot contains generated artifact directory '{d}' "
                f"(should be cleaned; ignored as generated noise in run candidates)"
            )


def _accepted_solution_present(manifest: TaskManifest, base: Path) -> bool:
    snap = (
        base
        / "benchmark"
        / "accepted_solutions"
        / manifest.repo_id
        / manifest.task_id
        / "gold_fix"
    )
    script = base / "scripts" / "fixes" / f"{manifest.task_id}_fix.py"
    return snap.exists() or script.exists()


OUTPUT_STRESS_HARD_CEILING_BYTES = 1_000_000


def _check_structure_contract(
    manifest: TaskManifest, base: Path, errors: list[str], warnings: list[str]
) -> None:
    """Reorg tasks must carry a deterministic, gold-satisfiable structure contract."""
    if manifest.category.value != "reorg":
        if manifest.structure_contract is not None:
            warnings.append("structure_contract set on a non-reorg task (ignored by scorer)")
        return

    sc = manifest.structure_contract
    if sc is None:
        errors.append("reorg task has no structure_contract")
        return

    # A reorg contract is only meaningful with concrete targets to reach and
    # concrete opaque paths to dismantle.
    if not sc.required_paths:
        errors.append("reorg structure_contract has no required_paths")
    if not sc.forbidden_paths:
        errors.append("reorg structure_contract has no forbidden_paths")

    gold = base / manifest.gold_snapshot
    broken = base / manifest.broken_snapshot

    # The gold layout is the target: every required path must exist there.
    for p in sc.required_paths:
        if not (gold / p).exists():
            errors.append(f"structure_contract required path missing from gold: {p}")
    for p in sc.public_entrypoints:
        if not (gold / p).exists():
            errors.append(f"structure_contract public_entrypoint missing from gold: {p}")
    # There must be something to reorganize: the opaque files exist in broken.
    for p in sc.forbidden_paths:
        if not (broken / p).exists():
            warnings.append(
                f"structure_contract forbidden/opaque path '{p}' is absent from the "
                f"broken snapshot (nothing to reorganize there)"
            )


def _check_staged_linkage(
    manifest: TaskManifest, errors: list[str], warnings: list[str]
) -> None:
    """Validate staged-implementation linkage metadata."""
    if manifest.category.value != "staged_implementation":
        return
    if manifest.stage not in (1, 2):
        errors.append("staged_implementation task must declare stage 1 or 2")
    if not manifest.stage_group_id:
        errors.append("staged_implementation task must declare a stage_group_id")
    if manifest.stage == 1 and not manifest.next_stage_task_id:
        warnings.append("stage 1 task has no next_stage_task_id")
    if manifest.stage == 2:
        if not manifest.previous_stage_task_id:
            errors.append("stage 2 task must declare previous_stage_task_id")
        if manifest.input_source != "previous_candidate":
            errors.append(
                "stage 2 task must set input_source='previous_candidate' "
                f"(got '{manifest.input_source}')"
            )


def _check_output_stress(
    manifest: TaskManifest, broken_visible_bytes: int, errors: list[str], warnings: list[str]
) -> None:
    """Bound the long-output fixture: within the declared band, under 1 MB."""
    os_cfg = manifest.output_stress
    if os_cfg is None or not os_cfg.enabled:
        return
    n = broken_visible_bytes
    if n > OUTPUT_STRESS_HARD_CEILING_BYTES:
        errors.append(
            f"output_stress visible output {n} bytes exceeds the 1 MB hard ceiling"
        )
    elif n < os_cfg.expected_visible_output_bytes_min:
        warnings.append(
            f"output_stress visible output {n} bytes is below the declared minimum "
            f"{os_cfg.expected_visible_output_bytes_min}"
        )
    elif n > os_cfg.expected_visible_output_bytes_max:
        warnings.append(
            f"output_stress visible output {n} bytes is above the declared maximum "
            f"{os_cfg.expected_visible_output_bytes_max}"
        )


def doctor_task(manifest_path: Path, base: Path) -> dict:
    """Validate one task end-to-end. Returns the doctor report dict."""
    manifest_path = Path(manifest_path)
    errors: list[str] = []
    warnings: list[str] = []

    try:
        manifest = load_manifest(manifest_path)
    except Exception as e:  # malformed JSON or schema violation
        return {
            "task_id": manifest_path.stem,
            "status": "invalid",
            "gold_visible_passed": False,
            "gold_hidden_passed": False,
            "broken_visible_passed": False,
            "broken_hidden_passed": False,
            "hidden_failure_required": False,
            "leakage_findings": [],
            "warnings": [],
            "errors": [f"manifest failed to load: {e}"],
        }

    # Schema-valid; now semantic + authoring checks.
    errors.extend(validate_manifest(manifest, base))
    _check_path_policies(manifest, errors)
    _check_test_locations(manifest, errors, warnings)
    _check_prompt(manifest, errors)
    _check_metadata(manifest, errors, warnings)
    _check_structure_contract(manifest, base, errors, warnings)
    _check_staged_linkage(manifest, errors, warnings)

    if not _accepted_solution_present(manifest, base):
        warnings.append("no accepted-solution snapshot or fix script found")

    _check_snapshot_artifacts(manifest, base, warnings)

    gold = (base / manifest.gold_snapshot)
    broken = (base / manifest.broken_snapshot)

    # Confession-style markers inside the broken candidate workspace invalidate
    # the task: the source must not name the planted defect.
    leakage_findings = scan_broken_snapshot_leakage(broken)
    if has_critical_leakage(leakage_findings):
        for f in leakage_findings:
            if f["severity"] == "critical":
                errors.append(
                    f"broken snapshot leaks the answer: {f['path']}:{f['line']} "
                    f"matched '{f['pattern']}'"
                )

    gold_vis = gold_hid = False
    broken_vis = broken_hid = False

    if gold.exists():
        r = _run_snapshot(manifest, base, gold)
        gold_vis, gold_hid = r["visible_passed"], r["hidden_passed"]
        if not gold_vis:
            errors.append("gold snapshot fails visible tests")
        if not gold_hid:
            errors.append("gold snapshot fails hidden tests")
        if r["visible_missing_path"]:
            errors.append(
                "visible command is not runnable against the gold workspace: "
                f"{r['visible_missing_path']}"
            )
    else:
        errors.append(f"gold snapshot does not exist: {gold}")

    if broken.exists():
        r = _run_snapshot(manifest, base, broken)
        broken_vis, broken_hid = r["visible_passed"], r["hidden_passed"]
        if broken_hid:
            errors.append("broken snapshot passes all hidden tests (must fail >=1)")
        # Visible tests may FAIL on broken, but they must still be runnable.
        if r["visible_missing_path"]:
            errors.append(
                "visible command is not runnable against the broken workspace: "
                f"{r['visible_missing_path']}"
            )
        _check_output_stress(manifest, r.get("visible_output_bytes", 0), errors, warnings)
    else:
        errors.append(f"broken snapshot does not exist: {broken}")

    hidden_failure_required = broken.exists() and not broken_hid

    status = "valid" if not errors else "invalid"
    return {
        "task_id": manifest.task_id,
        "status": status,
        "gold_visible_passed": gold_vis,
        "gold_hidden_passed": gold_hid,
        "broken_visible_passed": broken_vis,
        "broken_hidden_passed": broken_hid,
        "hidden_failure_required": hidden_failure_required,
        "leakage_findings": leakage_findings,
        "warnings": warnings,
        "errors": errors,
    }
