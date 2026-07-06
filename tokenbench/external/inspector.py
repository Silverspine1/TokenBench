"""File-count and health inspection for external repos."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .schema import ExternalRepoSource

FILE_COUNT_LOW = 500
FILE_COUNT_HIGH = 1200
FILE_COUNT_IDEAL_LOW = 500
FILE_COUNT_IDEAL_HIGH = 900

_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
    ".go", ".rs", ".cpp", ".c", ".h", ".hpp",
    ".cs", ".java", ".kt", ".dart", ".rb", ".php",
    ".html", ".css", ".scss", ".less",
    ".json", ".yaml", ".yml", ".toml",
    ".md", ".txt",
}


def _is_junk(rel_parts: tuple[str, ...], junk_paths: list[str]) -> bool:
    for part in rel_parts:
        if part in junk_paths:
            return True
        for junk in junk_paths:
            if junk.startswith("*.") and part.endswith(junk[1:]):
                return True
    return False


def count_files(repo_dir: Path, source: ExternalRepoSource) -> dict:
    """Count meaningful, test, source, and junk files under repo_dir."""
    total = 0
    meaningful = 0
    test_files = 0
    source_files = 0
    junk_files = 0

    for p in sorted(repo_dir.rglob("*")):
        if not p.is_file():
            continue
        total += 1
        rel_parts = p.relative_to(repo_dir).parts
        if _is_junk(rel_parts, source.junk_paths):
            junk_files += 1
            continue
        meaningful += 1
        name = p.name.lower()
        if "test" in name or any("test" in part.lower() for part in rel_parts):
            test_files += 1
        elif p.suffix.lower() in _SOURCE_EXTENSIONS:
            source_files += 1

    return {
        "total": total,
        "meaningful": meaningful,
        "test_files": test_files,
        "source_files": source_files,
        "junk_files": junk_files,
    }


def load_source(source_path: Path) -> ExternalRepoSource:
    data = json.loads(source_path.read_text(encoding="utf-8"))
    return ExternalRepoSource(**data)


def inspect_external_repo(source_path: Path) -> dict:
    """Return inspection report for an external repo source.json."""
    source = load_source(source_path)
    clone_dir = source_path.parent / "cache" / ".git_clone"

    result: dict = {
        "repo_id": source.repo_id,
        "pinned_commit": source.pinned_commit,
        "license": source.license,
        "clone_dir": clone_dir.as_posix(),
        "clone_exists": clone_dir.exists(),
        "meaningful_file_count": None,
        "test_file_count": None,
        "source_file_count": None,
        "junk_file_count": None,
        "file_count_note": source.file_count_note or "",
        "setup_status": "not_checked",
        "smoke_status": "not_checked",
        "warnings": [],
    }

    if not clone_dir.exists():
        result["warnings"].append(f"Clone not found at {clone_dir}")
        return result

    counts = count_files(clone_dir, source)
    result["meaningful_file_count"] = counts["meaningful"]
    result["test_file_count"] = counts["test_files"]
    result["source_file_count"] = counts["source_files"]
    result["junk_file_count"] = counts["junk_files"]

    mf = counts["meaningful"]
    if mf < FILE_COUNT_LOW:
        result["warnings"].append(
            f"meaningful_file_count={mf} is below the {FILE_COUNT_LOW}-{FILE_COUNT_HIGH} range. "
            "Review suitability before expanding beyond the pilot."
        )
    elif mf > FILE_COUNT_HIGH:
        result["warnings"].append(
            f"meaningful_file_count={mf} exceeds the {FILE_COUNT_HIGH} upper bound. "
            "Consider adding additional junk_paths or choosing a smaller repo."
        )

    return result
