"""Render a strict task prompt for a CLI agent.

Hidden test commands MUST NOT appear here. The agent only ever sees the task,
the workspace, and the visible test command(s).
"""

from __future__ import annotations

from pathlib import Path

from ..manifests.schema import TaskManifest


def _bullets(items: list[str]) -> str:
    if not items:
        return "  (none)"
    return "\n".join(f"  - {x}" for x in items)


def task_statement(manifest: TaskManifest) -> str:
    """The agent-facing task description.

    When a task carries SWE-bench-style issue framing it reads as an issue
    report (``Issue: <title>`` + body); otherwise it is the raw ``prompt``. The
    body defaults to ``prompt`` so legacy manifests render unchanged. This is the
    single text the agent (and the prompt-hardness audit) should treat as the
    task — boilerplate like workspace/paths is not part of it.
    """
    title = manifest.issue_title.strip()
    body = (manifest.issue_body or manifest.prompt).strip()
    statement = f"Issue: {title}\n\n{body}" if title else body
    expected = [e.strip() for e in manifest.expected_behavior if e.strip()]
    if expected:
        statement += "\n\nExpected:\n" + "\n".join(f"- {e}" for e in expected)
    return statement


def _graphify_block(workspace_path: Path) -> str:
    """Tool block, present only when the harness built a graph into the workspace.

    The presence of ``graphify-out/graph.json`` *is* the treatment signal — no
    flag needs to reach the runner. Empty string in the control condition.
    """
    if not (Path(workspace_path) / "graphify-out" / "graph.json").exists():
        return ""
    return """

Knowledge graph:
A prebuilt knowledge graph of this workspace is at graphify-out/graph.json.
Prefer querying it over reading files blind to locate relevant code:
  - `python -m graphify query "<question about the codebase>"`
  - `python -m graphify explain "<symbol>"` / `python -m graphify path "<A>" "<B>"`
Use it to find where to make the fix before opening files."""


def build_prompt(manifest: TaskManifest, workspace_path: Path) -> str:
    """Build the agent prompt. Never includes hidden commands."""
    visible = "\n".join(manifest.visible_commands) if manifest.visible_commands else "(none)"

    return f"""You are working on a small software project.

Task:
{task_statement(manifest)}

Workspace:
{Path(workspace_path)}{_graphify_block(workspace_path)}

Repo ID: {manifest.repo_id}
Task ID: {manifest.task_id}
Category: {manifest.category.value}
Difficulty: {manifest.difficulty.value}
Allowed runtime: {manifest.allowed_runtime_seconds} seconds
Dependency policy: {manifest.dependency_policy.value}

Forbidden paths (do not modify):
{_bullets(manifest.forbidden_paths)}

Visible test command(s):
{visible}

Rules:
- Fix only the task described.
- Do not edit files outside the project workspace.
- Do not modify test or evaluation files.
- Do not install dependencies unless absolutely required.
- Run the relevant visible test/build after editing.
- When finished, stop. Additional checks will be run after submission.
{_prompt_suffix()}"""


def _prompt_suffix() -> str:
    # DORMANT. Was a one-off A/B injector (env TOKENBENCH_PROMPT_SUFFIX) for the
    # ponytail-skill probe; that experiment found no effect, so it's disabled to
    # keep benchmark prompts identical for everyone. To revive: return
    # os.environ.get("TOKENBENCH_PROMPT_SUFFIX", "").strip() wrapped in newlines.
    return ""
