"""File-change detection and patch generation.

Compares the pristine broken snapshot against the post-agent candidate tree and
classifies every change against the manifest's scored / ignored / forbidden
globs. Does not require either tree to be a git repository.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from fnmatch import fnmatch
from pathlib import Path

from ..manifests.schema import TaskManifest
from .hashing import file_hashes
from .paths import is_junk_path


def _match_any(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch(rel, pat) for pat in patterns)


def _diff_header_is_junk(header_line: str) -> bool:
    """True when a ``diff --git`` section header references a generated artifact.

    The header carries both the ``a/`` and ``b/`` paths (on Windows these use
    backslashes and absolute prefixes). A section is dropped when any path
    component is a junk/generated-artifact name, so patch.diff — and the bytes/
    line-churn derived from it — exclude build and cache noise.
    """
    return is_junk_path(header_line)


def filter_patch_text(patch_text: str) -> str:
    """Drop whole ``diff --git`` sections that touch only generated artifacts.

    Keeps every section for real source files intact (headers, hunks, content).
    A section runs from one ``diff --git`` line up to the next.
    """
    out: list[str] = []
    skipping = False
    for line in patch_text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            skipping = _diff_header_is_junk(line)
        if not skipping:
            out.append(line)
    return "".join(out)


def snapshot_candidate(workspace: Path, candidate: Path) -> None:
    """Archive the post-agent workspace as the immutable candidate tree."""
    if candidate.exists():
        shutil.rmtree(candidate)
    shutil.copytree(workspace, candidate)


def compute_file_changes(
    broken_snapshot: Path,
    candidate: Path,
    manifest: TaskManifest,
) -> dict:
    """Diff broken vs candidate; classify changes by manifest path policy."""
    before = file_hashes(broken_snapshot)
    after = file_hashes(candidate)

    before_keys = set(before)
    after_keys = set(after)

    # file_hashes already drops junk via the shared predicate; filter again here
    # so compute_file_changes is self-contained and robust to callers that pass
    # pre-built hash maps containing generated artifacts.
    added = sorted(k for k in (after_keys - before_keys) if not is_junk_path(k))
    deleted = sorted(k for k in (before_keys - after_keys) if not is_junk_path(k))
    modified = sorted(
        k
        for k in (before_keys & after_keys)
        if before[k] != after[k] and not is_junk_path(k)
    )

    changed = sorted(set(added) | set(deleted) | set(modified))

    forbidden_modified = [r for r in changed if _match_any(r, manifest.forbidden_paths)]
    ignored_modified = [r for r in changed if _match_any(r, manifest.ignored_paths)]
    scored_modified = [r for r in changed if _match_any(r, manifest.scored_paths)]

    return {
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "forbidden_modified": forbidden_modified,
        "ignored_modified": ignored_modified,
        "scored_modified": scored_modified,
    }


def write_file_changes(changes: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(changes, indent=2), encoding="utf-8")


def _git_diff_file(old_path: Path, new_path: Path) -> str:
    """Return a ``git diff --no-index`` for a single file pair, or "".

    Either side may be ``os.devnull`` to express an add (old is null) or a
    delete (new is null). Git returns exit 1 when the files differ and 0 when
    identical; any higher exit code is a real error for *this* file and is
    skipped (its content simply does not contribute churn) rather than aborting
    the whole patch.
    """
    proc = subprocess.run(
        ["git", "diff", "--no-index", "--", str(old_path), str(new_path)],
        capture_output=True,
        text=True,
    )
    return proc.stdout if proc.returncode in (0, 1) else ""


def write_patch(
    broken_snapshot: Path,
    candidate: Path,
    patch_path: Path,
    file_changes: dict | None = None,
) -> bool:
    """Write a unified diff of the changed source files to ``patch_path``.

    Diffs only the files ``compute_file_changes`` already classified as
    added/modified/deleted — which excludes junk (``target``, ``node_modules``,
    ``dist``, …). This is the key reason it diffs per file rather than handing
    git two directory trees: ``git diff --no-index`` over a whole tree walks into
    generated build output and aborts with empty stdout the moment it cannot
    access a file (e.g. a Rust ``target/`` artifact past the Windows path limit),
    silently zeroing line-churn. Per-file diffing never touches those paths.

    When ``file_changes`` is omitted, falls back to a whole-tree diff for
    backward compatibility. Falls back to a note if git is missing.
    """
    try:
        if file_changes is None:
            proc = subprocess.run(
                ["git", "diff", "--no-index", "--",
                 str(broken_snapshot), str(candidate)],
                capture_output=True,
                text=True,
            )
            patch_path.write_text(filter_patch_text(proc.stdout), encoding="utf-8")
            return True

        null = Path(os.devnull)
        sections: list[str] = []
        for rel in file_changes.get("added", []):
            sections.append(_git_diff_file(null, candidate / rel))
        for rel in file_changes.get("modified", []):
            sections.append(_git_diff_file(broken_snapshot / rel, candidate / rel))
        for rel in file_changes.get("deleted", []):
            sections.append(_git_diff_file(broken_snapshot / rel, null))

        patch_path.write_text(
            filter_patch_text("".join(s for s in sections if s)), encoding="utf-8"
        )
        return True
    except FileNotFoundError:
        patch_path.write_text(
            "# git not available; patch.diff omitted. See file_changes.json.\n",
            encoding="utf-8",
        )
        return False
