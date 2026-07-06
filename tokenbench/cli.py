"""TokenBench CLI (V0.2). Provider-agnostic, CLI-first."""

from __future__ import annotations

import concurrent.futures
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .agents.loader import AgentConfigError, load_agent
from .analysis.aggregate import aggregate_runs
from .analysis.compare import compare_conditions
from .core.ids import generate_run_id
from .core.paths import RunPaths
from .core.workspace import copy_tree, materialize_workspace
from .doctor.coverage import build_coverage
from .doctor.hardness import audit_suite
from .doctor.suite_doctor import doctor_suite
from .doctor.task_doctor import doctor_task
from .external.doctor import (
    doctor_external_repo,
    doctor_external_task,
    doctor_external_suite,
)
from .external.inspector import inspect_external_repo, load_source
from .manifests.loader import load_manifest
from .manifests.schema import TaskManifest
from .manifests.validator import validate_manifest
from .manual.bundles import export_bundle, import_candidate
from .manual.service import (
    attach_manual_cost,
    create_manual_run,
    submit_manual_run,
)
from .reports.summary import render_summary
from .runners.base import AgentRunner, RunnerResult
from .runners.cli_agent import CliAgentRunner
from .runners.finalize import finalize_run
from .runners.local_command import LocalCommandRunner
from .runners.manual import ManualRunner
from .scoring.scorer import score_run
from .suites.loader import load_suite
from .telemetry.cost_import import attach_cost_csv, attach_cost_to_run
from .telemetry.reports import calibration_report

app = typer.Typer(add_completion=False, help="TokenBench.ai harness (V0.2)")
console = Console()


def _base_dir() -> Path:
    return Path.cwd()


def _make_runner(
    runner: str,
    command: Optional[str],
    skip_agent: bool,
    agent: Optional[str],
    base: Path,
) -> AgentRunner:
    if runner == "manual":
        return ManualRunner(skip_agent=skip_agent, console=console)
    if runner == "local-command":
        if not command:
            console.print("[red]--command is required for local-command runner[/red]")
            raise typer.Exit(code=1)
        return LocalCommandRunner(command=command)
    if runner == "cli-agent":
        if not agent:
            console.print("[red]--agent is required for cli-agent runner[/red]")
            raise typer.Exit(code=1)
        try:
            config = load_agent(base / "benchmark" / "agents", agent)
        except AgentConfigError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(code=1)
        return CliAgentRunner(config)
    console.print(f"[red]Unknown runner: {runner}[/red]")
    raise typer.Exit(code=1)


# Default external root for isolated agent workspaces.
DEFAULT_ISOLATED_RUNS_ROOT = Path(tempfile.gettempdir()) / "tokenbench-runs"


def _resolve_isolated_root(
    runner: str, isolated_runs_root: Optional[str], isolated: bool
) -> Optional[Path]:
    """Decide where agent workspaces are materialized.

    CLI-agent runs default to an external, non-adjacent root so the agent's
    working directory cannot reach ``benchmark/`` via ``../``. Manual and
    local-command runs keep the workspace beside the artifacts for compatibility
    unless an explicit root is requested.
    """
    if isolated_runs_root:
        return Path(isolated_runs_root)
    if isolated and runner == "cli-agent":
        return DEFAULT_ISOLATED_RUNS_ROOT
    return None


def execute_run(
    manifest: TaskManifest,
    base: Path,
    agent_runner: AgentRunner,
    condition_id: str,
    trial_index: int,
    overwrite: bool,
    runs_root: Optional[Path] = None,
    isolated_runs_root: Optional[Path] = None,
    quiet: bool = False,
    override_snapshot: Optional[Path] = None,
    graphify: bool = False,
    cleanup_workspace: bool = True,
) -> dict:
    """Materialize, run, archive, test, and score one task. Returns the report.

    Run artifacts are written under ``runs_root``. When ``isolated_runs_root`` is
    given the agent-editable workspace is materialized under it instead of next
    to the artifacts, so the agent's working directory is not adjacent to the
    benchmark tree.

    ``quiet`` suppresses the per-run score print and run-directory line. The
    parallel suite runner sets it so concurrent runs do not interleave their
    output on the console; each run's artifacts are written to its own run_dir
    regardless.

    ``cleanup_workspace`` (default on) deletes the isolated temp workspace after
    scoring. ``finalize_run`` has already archived the durable copy into
    ``run_dir/candidate`` (and staged Stage 2 reads from there, not the live
    workspace), so the multi-hundred-MB materialized tree under
    ``isolated_runs_root/<run_id>`` is dead weight that would otherwise
    accumulate and fill the disk over a sweep. Pass ``False`` to keep it for
    debugging.
    """
    run_id = generate_run_id(manifest.repo_id, manifest.task_id)
    runs_root = runs_root or (base / "runs")
    workspace_base = (isolated_runs_root / run_id) if isolated_runs_root else None
    run_paths = RunPaths(runs_root / run_id, workspace_base=workspace_base)

    # 1. Materialize workspace. External-repo tasks use a patch-overlay model;
    #    internal tasks copy a pre-built broken snapshot. Staged Stage 2 overrides
    #    the source with Stage 1's candidate tree.
    from .manifests.schema import RepoKind
    broken_baseline_copy: Optional[Path] = None
    if manifest.repo_kind == RepoKind.external_github and override_snapshot is None:
        from .external.workspace import materialize_external_workspace
        source_path = base / manifest.source_ref
        source = load_source(source_path)
        task_dir = source_path.parent / "tasks" / manifest.task_id
        materialize_external_workspace(source, task_dir, run_paths, overwrite=overwrite)
        # Snapshot the broken state so finalize_run can diff against it.
        broken_baseline = run_paths.run_dir / "broken_baseline"
        copy_tree(run_paths.workspace, broken_baseline)
        broken_baseline_copy = broken_baseline
        baseline_snapshot = broken_baseline
    else:
        materialize_workspace(
            manifest, run_paths, base, overwrite=overwrite, override_snapshot=override_snapshot
        )
        baseline_snapshot = override_snapshot or (base / manifest.broken_snapshot)

    # 1b. Treatment condition: build an AST-only knowledge graph into the
    #     workspace (free, deterministic). build_prompt detects it and tells the
    #     agent to query it; graphify-out is a JUNK_DIRS name so it never scores.
    if graphify:
        from .runners.graphify_build import build_graph
        build_graph(run_paths.workspace)

    # 2. Persist the manifest used for this run.
    run_paths.task_manifest.write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )

    # 3. Run the agent inside the workspace, then finalize. The workspace is only
    #    needed through finalize_run (which archives candidate/ and runs tests);
    #    afterwards delete the isolated temp tree so per-run copies don't pile up
    #    and fill the disk over a sweep. Done in finally so a crashed run cleans
    #    up too. Only the isolated workspace_base is removed; non-isolated
    #    workspaces live inside the kept run_dir and are left as artifacts.
    try:
        result: RunnerResult = agent_runner.run(manifest, run_paths.workspace, run_paths.logs)
        report = finalize_run(
            run_paths, manifest, base, result,
            condition_id=condition_id,
            trial_index=trial_index,
            runner_name=agent_runner.name,
            baseline_snapshot=baseline_snapshot,
        )
    finally:
        if cleanup_workspace:
            if workspace_base is not None and workspace_base.exists():
                shutil.rmtree(workspace_base, ignore_errors=True)
            # External-repo diff baseline: a full repo copy needed only until
            # finalize_run wrote patch.diff/file_changes.json. Drop it too so it
            # doesn't pile up in runs/ across a sweep.
            if broken_baseline_copy is not None and broken_baseline_copy.exists():
                shutil.rmtree(broken_baseline_copy, ignore_errors=True)
    if not quiet:
        _print_score(report)
        console.print(f"\nRun directory: {run_paths.run_dir}")
    return report


@app.command("validate-manifest")
def validate_manifest_cmd(manifest_path: str) -> None:
    """Validate a single manifest file."""
    base = _base_dir()
    manifest = load_manifest(Path(manifest_path))
    errors = validate_manifest(manifest, base)
    if errors:
        console.print(f"[red]INVALID[/red] {manifest_path}")
        for e in errors:
            console.print(f"  - {e}")
        raise typer.Exit(code=1)
    console.print(f"[green]VALID[/green] {manifest.task_id} ({manifest.repo_id})")


@app.command("doctor-task")
def doctor_task_cmd(manifest_path: str) -> None:
    """Validate a single task end-to-end (gold passes, broken fails hidden, fair prompt)."""
    base = _base_dir()
    report = doctor_task(Path(manifest_path), base)
    print(json.dumps(report, indent=2))
    if report["status"] != "valid":
        raise typer.Exit(code=1)


@app.command("doctor-suite")
def doctor_suite_cmd(suite_path: str) -> None:
    """Validate every task in a suite. Valid only if every task is valid."""
    base = _base_dir()
    report = doctor_suite(Path(suite_path), base)
    console.print(f"[bold]Suite {report['suite_id']}[/bold]")
    console.print(f"  tasks_total   : {report['tasks_total']}")
    console.print(f"  tasks_valid   : {report['tasks_valid']}")
    console.print(f"  tasks_invalid : {report['tasks_invalid']}")
    console.print(f"  warnings_total: {report['warnings_total']}")
    console.print(f"  errors_total  : {report['errors_total']}")
    for t in report["tasks"]:
        color = "green" if t["status"] == "valid" else "red"
        console.print(f"  [{color}]{t['status'].upper()}[/{color}] {t['task_id']}")
        for e in t["errors"]:
            console.print(f"      [red]error[/red]: {e}")
        for w in t["warnings"]:
            console.print(f"      [yellow]warn[/yellow]: {w}")
    if report["status"] != "valid":
        raise typer.Exit(code=1)


@app.command("audit-suite")
def audit_suite_cmd(suite_path: str) -> None:
    """Report task-hardness signals and warn on too-easy hard/frontier tasks."""
    base = _base_dir()
    report = audit_suite(Path(suite_path), base)
    console.print(f"[bold]Hardness audit — {report['suite_id']}[/bold] ({report['tasks_total']} tasks)")
    console.print(f"  warnings_total: {report['warnings_total']}\n")
    for t in report["tasks"]:
        flag = "yes" if t["prompt_mentions_file_paths"] else "no"
        console.print(
            f"  [bold]{t['task_id']}[/bold] ({t['difficulty']})\n"
            f"      root_cause_files={t['root_cause_file_count']} "
            f"changed_files={t['expected_changed_files_min']}..{t['expected_changed_files_max']} "
            f"hidden_cases={t['hidden_test_count']} visible_cases={t['visible_test_count']} "
            f"repo_files={t['repo_file_count']} prompt_names_files={flag}"
        )
        for w in t["warnings"]:
            console.print(f"      [yellow]warn[/yellow]: {w}")
    if report["warnings_total"] == 0:
        console.print("\n[green]No hardness warnings.[/green]")


@app.command("coverage")
def coverage_cmd(suite_path: str) -> None:
    """Report task coverage by repo, category, difficulty, skills, and runtime."""
    base = _base_dir()
    cov = build_coverage(Path(suite_path), base)
    console.print(f"[bold]Coverage — {cov['suite_id']}[/bold] ({cov['tasks_total']} tasks)\n")

    def _section(title: str, counts: dict) -> None:
        console.print(f"{title}:")
        for k, v in counts.items():
            console.print(f"  {k}: {v}")
        console.print("")

    _section("Repo coverage", cov["repo_id"])
    _section("Category", cov["category"])
    _section("Difficulty", cov["difficulty"])
    _section("Skills tested", cov["skills_tested"])
    _section("Allowed runtime (s)", cov["allowed_runtime_seconds"])


@app.command("run")
def run_cmd(
    manifest_path: str,
    runner: str = typer.Option("manual", help="manual | local-command | cli-agent"),
    command: Optional[str] = typer.Option(None, help="command for local-command runner"),
    agent: Optional[str] = typer.Option(None, help="agent_id for cli-agent runner"),
    condition: str = typer.Option("unspecified", help="condition_id recorded on the run"),
    trial_index: int = typer.Option(0, help="trial index for paired comparison"),
    overwrite: bool = typer.Option(False, help="overwrite an existing workspace"),
    skip_agent: bool = typer.Option(False, help="manual runner: skip the edit pause"),
    isolated_runs_root: Optional[str] = typer.Option(
        None, help="materialize agent workspaces under this external root"
    ),
    isolated: bool = typer.Option(
        True, help="isolate cli-agent workspaces outside the benchmark tree"
    ),
    graphify: bool = typer.Option(
        False, help="build an AST knowledge graph into the workspace (treatment condition)"
    ),
    keep_workspace: bool = typer.Option(
        False, help="keep the temp workspace after scoring (debugging; default deletes it)"
    ),
) -> None:
    """Run one benchmark task and produce a score.json."""
    base = _base_dir()
    manifest = load_manifest(Path(manifest_path))
    errors = validate_manifest(manifest, base)
    if errors:
        console.print(f"[red]Manifest invalid:[/red] {'; '.join(errors)}")
        raise typer.Exit(code=1)

    iso = _resolve_isolated_root(runner, isolated_runs_root, isolated)
    agent_runner = _make_runner(runner, command, skip_agent, agent, base)
    execute_run(
        manifest, base, agent_runner, condition, trial_index, overwrite,
        isolated_runs_root=iso, graphify=graphify,
        cleanup_workspace=not keep_workspace,
    )


@app.command("run-suite")
def run_suite_cmd(
    suite_path: str,
    condition: str = typer.Option("unspecified", help="condition_id recorded on every run"),
    runner: str = typer.Option("manual", help="manual | local-command | cli-agent"),
    command: Optional[str] = typer.Option(None, help="command for local-command runner"),
    agent: Optional[str] = typer.Option(None, help="agent_id for cli-agent runner"),
    overwrite: bool = typer.Option(False, help="overwrite existing workspaces"),
    skip_agent: bool = typer.Option(True, help="manual runner: skip the edit pause"),
    isolated_runs_root: Optional[str] = typer.Option(
        None, help="materialize agent workspaces under this external root"
    ),
    isolated: bool = typer.Option(
        True, help="isolate cli-agent workspaces outside the benchmark tree"
    ),
    trial_index: Optional[int] = typer.Option(
        None, help="accepted for compatibility; suites run all required_trials"
    ),
    max_concurrency: int = typer.Option(
        1, help="number of atomic runs to schedule at once (1-10)"
    ),
    graphify: bool = typer.Option(
        False, help="build an AST knowledge graph into each workspace (treatment condition)"
    ),
) -> None:
    """Run every task in a suite, ``required_trials`` times each.

    With ``--max-concurrency > 1`` independent atomic runs are scheduled in
    parallel. Each run stays a fresh, isolated atomic run (own run_id, workspace,
    logs, score.json, telemetry.json); parallelism only changes wall-clock time,
    not benchmark semantics. A single run's failure does not stop the others.
    """
    base = _base_dir()

    # Concurrency validation is a harness-level precondition: fail fast and loud.
    try:
        validate_max_concurrency(max_concurrency)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2)

    suite = load_suite(Path(suite_path))
    console.print(
        f"[bold]Suite {suite.suite_id}[/bold] — {len(suite.tasks)} task(s) "
        f"x {suite.required_trials} trial(s), condition={condition}, "
        f"max_concurrency={max_concurrency}"
    )

    iso = _resolve_isolated_root(runner, isolated_runs_root, isolated)

    # Validate every manifest up front. An invalid manifest is a scheduling
    # failure (not a low score), so it aborts before any run starts.
    work: list[tuple[str, TaskManifest, int]] = []
    for task_rel in suite.tasks:
        manifest = load_manifest(base / task_rel)
        errors = validate_manifest(manifest, base)
        if errors:
            console.print(f"[red]Manifest invalid ({task_rel}):[/red] {'; '.join(errors)}")
            raise typer.Exit(code=1)
        for trial in range(suite.required_trials):
            work.append((task_rel, manifest, trial))

    # Surface runner/agent config errors once, up front (scheduling failure),
    # before any work is dispatched. A fresh runner is still built per run.
    _make_runner(runner, command, skip_agent, agent, base)

    results = schedule_suite_runs(
        work, base=base, condition=condition, runner=runner, command=command,
        agent=agent, skip_agent=skip_agent, overwrite=overwrite, iso=iso,
        max_concurrency=max_concurrency, graphify=graphify,
    )
    _print_suite_status(results)


@app.command("run-staged")
def run_staged_cmd(
    suite_path: str,
    stage_group: str = typer.Option(..., "--stage-group", help="stage_group_id to run"),
    condition: str = typer.Option("unspecified", help="condition_id recorded on the runs"),
    runner: str = typer.Option("manual", help="manual | local-command | cli-agent"),
    command: Optional[str] = typer.Option(None, help="command for local-command runner"),
    agent: Optional[str] = typer.Option(None, help="agent_id for cli-agent runner"),
    trial_index: int = typer.Option(0, help="trial index for paired comparison"),
    overwrite: bool = typer.Option(False, help="overwrite existing workspaces"),
    skip_agent: bool = typer.Option(True, help="manual runner: skip the edit pause"),
    isolated_runs_root: Optional[str] = typer.Option(
        None, help="materialize agent workspaces under this external root"
    ),
    isolated: bool = typer.Option(
        True, help="isolate cli-agent workspaces outside the benchmark tree"
    ),
    graphify: bool = typer.Option(
        False, help="build an AST knowledge graph into each stage workspace (treatment condition)"
    ),
) -> None:
    """Run a staged group: Stage 1, then Stage 2 on Stage 1's candidate output.

    Stage 2 runs as a fresh agent process (default mode) seeded with the files
    Stage 1 produced — no shared chat history. Emits staged_score.json with
    extension-friction telemetry beside Stage 2's artifacts.
    """
    base = _base_dir()
    suite = load_suite(Path(suite_path))

    stage1: Optional[TaskManifest] = None
    stage2: Optional[TaskManifest] = None
    for task_rel in suite.tasks:
        m = load_manifest(base / task_rel)
        if m.stage_group_id != stage_group:
            continue
        if m.stage == 1:
            stage1 = m
        elif m.stage == 2:
            stage2 = m
    if stage1 is None or stage2 is None:
        console.print(
            f"[red]stage group '{stage_group}' needs both a stage-1 and a "
            f"stage-2 manifest in {suite.suite_id}[/red]"
        )
        raise typer.Exit(code=1)

    for m in (stage1, stage2):
        errors = validate_manifest(m, base)
        if errors:
            console.print(f"[red]Manifest invalid ({m.task_id}):[/red] {'; '.join(errors)}")
            raise typer.Exit(code=1)

    iso = _resolve_isolated_root(runner, isolated_runs_root, isolated)
    agent_runner = _make_runner(runner, command, skip_agent, agent, base)

    from .staged.runner import run_staged_group

    report = run_staged_group(
        base, stage1, stage2, agent_runner, condition, trial_index, overwrite,
        isolated_runs_root=iso, graphify=graphify,
    )
    _print_staged(report)


def _print_staged(report: dict) -> None:
    s = report["staged"]
    console.print(f"\n[bold]Staged group {report['stage_group_id']}[/bold]")
    console.print(
        f"  stage1 quality={report['stage1']['quality_score']} "
        f"success={report['stage1']['success']}"
    )
    console.print(
        f"  stage2 quality={report['stage2']['quality_score']} "
        f"success={report['stage2']['success']}"
    )
    console.print(
        f"  extension_friction={s['extension_friction']} "
        f"(stage1_churn={s['stage1_line_churn']}, stage2_churn={s['stage2_line_churn']}, "
        f"touched_stage1_files={s['stage2_touched_stage1_files']})"
    )
    console.print(
        f"  [bold]staged_score={s['staged_score']}[/bold] "
        f"(friction_score={s['extension_friction_score']})"
    )


def validate_max_concurrency(n: int) -> None:
    """Raise ValueError unless ``1 <= n <= 10``."""
    if n < 1 or n > 10:
        raise ValueError(f"--max-concurrency must be between 1 and 10 (got {n})")


def schedule_suite_runs(
    work: list[tuple[str, TaskManifest, int]],
    *,
    base: Path,
    condition: str,
    runner: str,
    command: Optional[str],
    agent: Optional[str],
    skip_agent: bool,
    overwrite: bool,
    iso: Optional[Path],
    max_concurrency: int,
    runs_root: Optional[Path] = None,
    graphify: bool = False,
) -> list[dict]:
    """Execute every ``(task_rel, manifest, trial)`` item as an isolated atomic run.

    Runs concurrently when ``max_concurrency > 1``. Each run gets a fresh runner
    and its own run_id/workspace/logs/score/telemetry. A run that raises is
    captured as an ``error`` status and does not stop the others. Returns one
    status dict per work item.
    """

    def _run_one(item: tuple[str, TaskManifest, int]) -> dict:
        task_rel, manifest, trial = item
        status: dict = {
            "task_rel": task_rel,
            "repo_id": manifest.repo_id,
            "task_id": manifest.task_id,
            "trial": trial,
        }
        try:
            agent_runner = _make_runner(runner, command, skip_agent, agent, base)
            report = execute_run(
                manifest, base, agent_runner, condition, trial, overwrite,
                runs_root=runs_root, isolated_runs_root=iso, quiet=True,
                graphify=graphify,
            )
            status.update(
                status="ok",
                run_id=report.get("run_id"),
                final_score=report.get("final_score"),
                quality_score=report.get("quality_score"),
                success=bool(report.get("success", False)),
            )
        except Exception as e:  # one task failing must not stop the others
            status.update(status="error", error=f"{type(e).__name__}: {e}")
        return status

    results: list[dict] = []
    if max_concurrency == 1:
        for item in work:
            results.append(_run_one(item))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrency) as pool:
            futures = [pool.submit(_run_one, item) for item in work]
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())
    return results


def _print_suite_status(results: list[dict]) -> None:
    """Print a per-task status table after a suite run."""
    # Stable ordering by (repo, task, trial) regardless of completion order.
    ordered = sorted(
        results, key=lambda r: (r.get("repo_id") or "", r.get("task_id") or "", r.get("trial", 0))
    )
    ok = sum(1 for r in ordered if r.get("status") == "ok")
    errored = sum(1 for r in ordered if r.get("status") == "error")
    succeeded = sum(1 for r in ordered if r.get("success"))

    console.print("\n[bold]Suite run status[/bold]")
    for r in ordered:
        if r.get("status") == "ok":
            mark = "[green]ok[/green]" if r.get("success") else "[yellow]ok[/yellow]"
            console.print(
                f"  {mark}  {r['repo_id']}/{r['task_id']} trial={r['trial']} "
                f"final={r.get('final_score')} quality={r.get('quality_score')} "
                f"success={r.get('success')} [dim]{r.get('run_id')}[/dim]"
            )
        else:
            console.print(
                f"  [red]error[/red]  {r['repo_id']}/{r['task_id']} trial={r['trial']} "
                f"[red]{r.get('error')}[/red]"
            )
    console.print(
        f"\n[bold]{len(ordered)} run(s)[/bold]: {ok} completed, "
        f"{errored} errored, {succeeded} successful"
    )


@app.command("score")
def score_cmd(run_dir: str) -> None:
    """Recompute score.json for an existing run directory."""
    rd = Path(run_dir)
    manifest_path = rd / "task_manifest.json"
    if not manifest_path.exists():
        console.print(f"[red]No task_manifest.json in {run_dir}[/red]")
        raise typer.Exit(code=1)
    manifest = TaskManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    report = score_run(rd, manifest)
    _print_score(report)


@app.command("summarize")
def summarize_cmd(runs_dir: str = typer.Argument("runs")) -> None:
    """Print a ranked table from all score.json files."""
    render_summary(Path(runs_dir), console=console)


@app.command("aggregate")
def aggregate_cmd(
    runs_dir: str = typer.Argument("runs"),
    json_out: bool = typer.Option(True, "--json/--no-json", help="emit JSON"),
) -> None:
    """Aggregate trials grouped by condition_id (includes telemetry metrics)."""
    result = aggregate_runs(Path(runs_dir))
    print(json.dumps(result, indent=2))


@app.command("compare")
def compare_cmd(
    runs_dir: str = typer.Argument("runs"),
    condition_a: str = typer.Option(..., "--condition-a", help="baseline condition_id"),
    condition_b: str = typer.Option(..., "--condition-b", help="comparison condition_id"),
) -> None:
    """Paired comparison of two conditions over matching (repo, task, trial)."""
    result = compare_conditions(Path(runs_dir), condition_a, condition_b)
    print(json.dumps(result, indent=2))


@app.command("calibration-report")
def calibration_report_cmd(
    runs_dir: str = typer.Argument("runs"),
    condition: str = typer.Option(..., "--condition", help="condition_id to calibrate"),
) -> None:
    """Per-task median telemetry for one (baseline) condition."""
    result = calibration_report(Path(runs_dir), condition)
    print(json.dumps(result, indent=2))


@app.command("attach-cost")
def attach_cost_cmd(
    run_dir: str,
    cost_usd: Optional[float] = typer.Option(None, help="provider-reported cost in USD"),
    input_tokens: Optional[int] = typer.Option(None, help="provider input tokens"),
    output_tokens: Optional[int] = typer.Option(None, help="provider output tokens"),
    cache_read_tokens: Optional[int] = typer.Option(None, help="provider cache-read tokens"),
    cache_write_tokens: Optional[int] = typer.Option(None, help="provider cache-write tokens"),
    reasoning_tokens: Optional[int] = typer.Option(None, help="provider reasoning tokens"),
    total_tokens: Optional[int] = typer.Option(
        None, help="provider total tokens (defaults to the sum of the parts)"
    ),
) -> None:
    """Attach manually-sourced provider cost/usage to one run's telemetry.json."""
    fields = {
        "cost_usd": cost_usd,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
    }
    try:
        telemetry = attach_cost_to_run(Path(run_dir), fields)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    print(json.dumps(telemetry["provider_usage"], indent=2))


@app.command("build-db")
def build_db_cmd(
    runs_dir: str = typer.Argument("runs", help="runs directory holding <run_id>/ dirs"),
    db: str = typer.Option("tokenbench.db", help="output SQLite database path"),
) -> None:
    """Ingest all run JSON artifacts into a queryable SQLite database."""
    from .analysis.sqlite_store import ingest_runs

    totals = ingest_runs(Path(runs_dir), Path(db))
    console.print(f"[green]ingested[/green] {totals['run_dirs_scanned']} run dir(s) -> {totals['db_path']}")
    console.print(
        f"  runs={totals['runs']} telemetry={totals['telemetry']} "
        f"cost={totals['cost']} manual={totals['manual']} staged={totals['staged']}"
    )
    console.print("\nQuery example:")
    console.print(f'  sqlite3 {db} "SELECT task_id, success, final_score, cost_usd FROM run_results ORDER BY final_score DESC;"')



@app.command("attach-cost-csv")
def attach_cost_csv_cmd(
    csv_path: str,
    runs_dir: str = typer.Option("runs", help="runs directory holding <run_id>/ dirs"),
) -> None:
    """Batch-attach provider cost/usage from a CSV keyed by run_id."""
    results = attach_cost_csv(Path(csv_path), Path(runs_dir))
    ok = sum(1 for r in results if r["status"] == "ok")
    errored = len(results) - ok
    for r in results:
        if r["status"] == "ok":
            console.print(f"  [green]ok[/green]    {r['run_id']}")
        else:
            console.print(f"  [red]error[/red] {r['run_id']}: {r.get('error')}")
    console.print(f"\n[bold]{len(results)} row(s)[/bold]: {ok} attached, {errored} errored")
    if errored:
        raise typer.Exit(code=1)


@app.command("manual-start")
def manual_start_cmd(
    manifest_path: str,
    condition: str = typer.Option("manual_generic_ide", help="condition_id for the run"),
    ide: str = typer.Option("", help="IDE/ADE name (e.g. Cursor)"),
    model: str = typer.Option("user-entered", help="model name, recorded only"),
    notes: str = typer.Option("", help="operator notes"),
    overwrite: bool = typer.Option(False, help="overwrite an existing workspace"),
) -> None:
    """Create a manual-IDE run: materialize the workspace and render the prompt."""
    base = _base_dir()
    manifest = load_manifest(Path(manifest_path))
    errors = validate_manifest(manifest, base)
    if errors:
        console.print(f"[red]Manifest invalid:[/red] {'; '.join(errors)}")
        raise typer.Exit(code=1)
    record = create_manual_run(
        base, manifest, condition_id=condition, ide_name=ide, model_name=model,
        operator_notes=notes, overwrite=overwrite,
    )
    console.print(f"[green]manual run created[/green] {record['run_id']}")
    console.print(f"  workspace : {record['workspace_path']}")
    console.print(f"  run dir   : {record['run_dir']}")
    console.print("\nEdit the workspace, then run:")
    console.print(f"  tokenbench manual-submit {record['run_dir']}")


@app.command("manual-submit")
def manual_submit_cmd(run_dir: str) -> None:
    """Freeze a manual run's workspace, run hidden tests, and score it."""
    base = _base_dir()
    try:
        report = submit_manual_run(base, Path(run_dir))
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    _print_score(report)
    console.print(f"\nRun directory: {run_dir}")


@app.command("manual-cost")
def manual_cost_cmd(
    run_dir: str,
    cost_usd: Optional[float] = typer.Option(None, help="provider-reported cost in USD"),
    input_tokens: Optional[int] = typer.Option(None),
    output_tokens: Optional[int] = typer.Option(None),
    cache_read_tokens: Optional[int] = typer.Option(None),
    cache_write_tokens: Optional[int] = typer.Option(None),
    reasoning_tokens: Optional[int] = typer.Option(None),
    total_tokens: Optional[int] = typer.Option(None),
    source: str = typer.Option("manual_estimate", help="cost provenance"),
    confidence: str = typer.Option("low", help="high | medium | low"),
    notes: str = typer.Option("", help="free-text note"),
) -> None:
    """Attach an operator-entered USD cost to a manual run's telemetry."""
    fields = {
        "cost_usd": cost_usd,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
    }
    try:
        result = attach_manual_cost(
            Path(run_dir), fields, source=source, confidence=confidence, notes=notes,
        )
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    print(json.dumps(result["provider_usage"], indent=2))


@app.command("bundle-export")
def bundle_export_cmd(
    run_dir: str,
    out: Optional[str] = typer.Option(None, help="output zip path (default: <run_dir>/bundle.zip)"),
) -> None:
    """Export an operator-safe task bundle zip for an external IDE."""
    base = _base_dir()
    out_zip = Path(out) if out else (Path(run_dir) / "bundle.zip")
    try:
        info = export_bundle(base, Path(run_dir), out_zip)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]bundle written[/green] {info['bundle_path']}")
    console.print(f"  sha256: {info['bundle_hash']}")


@app.command("bundle-import")
def bundle_import_cmd(run_dir: str, candidate_zip: str) -> None:
    """Import an external candidate zip into a manual run and score it."""
    base = _base_dir()
    try:
        report = import_candidate(base, Path(run_dir), Path(candidate_zip))
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    _print_score(report)


@app.command("external-repo")
def external_repo_cmd(
    subcommand: str = typer.Argument(..., help="Subcommand: inspect"),
    source_path: str = typer.Argument(..., help="Path to source.json"),
) -> None:
    """Inspect an external repo source.json (file counts, setup status, warnings)."""
    base = _base_dir()
    sp = Path(source_path)
    if not sp.is_absolute():
        sp = base / sp
    if not sp.exists():
        console.print(f"[red]source.json not found: {sp}[/red]")
        raise typer.Exit(code=1)

    if subcommand != "inspect":
        console.print(f"[red]Unknown subcommand: {subcommand}. Use 'inspect'.[/red]")
        raise typer.Exit(code=1)

    report = inspect_external_repo(sp)
    console.print(f"\n[bold]External Repo Inspection[/bold]: {report['repo_id']}")
    console.print(f"  pinned_commit        : {report['pinned_commit']}")
    console.print(f"  license              : {report['license']}")
    console.print(f"  meaningful_file_count: {report.get('meaningful_file_count', 'N/A')}")
    console.print(f"  test_file_count      : {report.get('test_file_count', 'N/A')}")
    console.print(f"  source_file_count    : {report.get('source_file_count', 'N/A')}")
    console.print(f"  junk_file_count      : {report.get('junk_file_count', 'N/A')}")
    console.print(f"  clone_exists         : {report['clone_exists']}")

    mf = report.get("meaningful_file_count")
    if mf is not None:
        if mf < 500:
            console.print(f"\n[yellow]WARNING: {mf} meaningful files is below the 500-900 target range.[/yellow]")
            if report.get("file_count_note"):
                console.print(f"  note: {report['file_count_note']}")
        elif mf > 1200:
            console.print(f"\n[yellow]WARNING: {mf} meaningful files exceeds 1200 upper bound.[/yellow]")
        else:
            console.print(f"\n[green]File count {mf} is within the 500-900 target range.[/green]")

    for w in report.get("warnings", []):
        console.print(f"[yellow]  warning: {w}[/yellow]")


@app.command("doctor-external-repo")
def doctor_external_repo_cmd(source_path: str) -> None:
    """Validate an external repo source.json (commit, license, file count)."""
    base = _base_dir()
    sp = Path(source_path)
    if not sp.is_absolute():
        sp = base / sp

    report = doctor_external_repo(sp)
    console.print(f"\n[bold]doctor-external-repo[/bold]: {report.get('repo_id', 'unknown')}")
    for e in report.get("errors", []):
        console.print(f"  [red]error: {e}[/red]")
    for w in report.get("warnings", []):
        console.print(f"  [yellow]warning: {w}[/yellow]")

    if report["passed"]:
        console.print("[green]PASSED[/green]")
    else:
        console.print("[red]FAILED[/red]")
        raise typer.Exit(code=1)


@app.command("doctor-external-task")
def doctor_external_task_cmd(manifest_path: str) -> None:
    """Validate an external-repo task manifest (leakage, tests, patches)."""
    base = _base_dir()
    mp = Path(manifest_path)
    if not mp.is_absolute():
        mp = base / mp

    report = doctor_external_task(mp, base_dir=base)
    task_id = report.get("task_id", "unknown")
    console.print(f"\n[bold]doctor-external-task[/bold]: {task_id}")
    for e in report.get("errors", []):
        console.print(f"  [red]error: {e}[/red]")
    for w in report.get("warnings", []):
        console.print(f"  [yellow]warning: {w}[/yellow]")
    leakage = report.get("leakage", {})
    if leakage.get("findings"):
        for f in leakage["findings"]:
            sev = "[red]CRITICAL[/red]" if f["severity"] == "critical" else "[yellow]warning[/yellow]"
            console.print(f"  leakage {sev}: {f['source']}:{f['line']}: {f['pattern']!r}")

    if report["passed"]:
        console.print("[green]PASSED[/green]")
    else:
        console.print("[red]FAILED[/red]")
        raise typer.Exit(code=1)


@app.command("doctor-external-suite")
def doctor_external_suite_cmd(suite_path: str) -> None:
    """Validate all external tasks in a suite."""
    base = _base_dir()
    sp = Path(suite_path)
    if not sp.is_absolute():
        sp = base / sp

    report = doctor_external_suite(sp, base_dir=base)
    suite_id = report.get("suite_id", "unknown")
    console.print(f"\n[bold]doctor-external-suite[/bold]: {suite_id}")
    console.print(
        f"  tasks: {report['tasks_valid']}/{report['tasks_total']} valid  "
        f"({report['tasks_invalid']} invalid, "
        f"{report['errors_total']} errors, "
        f"{report['warnings_total']} warnings)"
    )
    for tr in report.get("task_results", []):
        tid = tr.get("task_id") or tr.get("task_path", "?")
        status = "[green]OK[/green]" if tr.get("passed") else "[red]FAIL[/red]"
        console.print(f"  {status} {tid}")
        for e in tr.get("errors", []):
            console.print(f"       [red]{e}[/red]")

    if report["passed"]:
        console.print("[green]SUITE PASSED[/green]")
    else:
        console.print("[red]SUITE FAILED[/red]")
        raise typer.Exit(code=1)


@app.command("ui")
def ui_cmd(
    host: str = typer.Option("127.0.0.1", help="bind host"),
    port: int = typer.Option(8765, help="bind port"),
) -> None:
    """Start the local manual-IDE web UI (requires the 'ui' extra)."""
    try:
        import uvicorn

        from .ui.app import create_app
    except ImportError:
        console.print(
            "[red]UI dependencies missing.[/red] Install with: "
            "pip install -e \".[ui]\""
        )
        raise typer.Exit(code=1)
    app_instance = create_app(_base_dir())
    console.print(f"[bold]TokenBench manual UI[/bold] -> http://{host}:{port}")
    uvicorn.run(app_instance, host=host, port=port)


def _print_score(report: dict) -> None:
    console.print("")
    console.print(
        f"[bold]{report['task_id']}[/bold] ({report['repo_id']}) "
        f"[dim]condition={report['condition_id']} trial={report['trial_index']}[/dim]"
    )
    console.print(f"  quality    : {report['quality_score']}")
    console.print(f"  efficiency : {report['efficiency_score']}")
    console.print(f"  gated      : {report['efficiency_gated']}")
    console.print(f"  [bold]final      : {report['final_score']}[/bold]")
    ok = report.get("success", False)
    console.print(f"  success    : {'[green]yes[/green]' if ok else '[red]no[/red]'}")
    ht = report["hidden_tests"]
    vt = report["visible_tests"]
    console.print(f"  hidden tests : {ht['tests_passed']}/{ht['tests_total']}")
    console.print(f"  visible tests: {vt['tests_passed']}/{vt['tests_total']}")


if __name__ == "__main__":
    app()
