"""Task-bank coverage report over a suite.

Tallies tasks by repo, category, difficulty, skill, and declared runtime so a
suite does not silently drift into (say) ten easy bugfixes.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..manifests.loader import load_manifest
from ..suites.loader import load_suite


def build_coverage(suite_path: Path, base: Path) -> dict:
    """Return coverage counts for every task in a suite."""
    suite = load_suite(Path(suite_path))

    repo: Counter[str] = Counter()
    category: Counter[str] = Counter()
    difficulty: Counter[str] = Counter()
    skills: Counter[str] = Counter()
    runtime: Counter[int] = Counter()

    for task_rel in suite.tasks:
        m = load_manifest(base / task_rel)
        repo[m.repo_id] += 1
        category[m.category.value] += 1
        difficulty[m.difficulty.value] += 1
        runtime[m.allowed_runtime_seconds] += 1
        for skill in m.skills_tested:
            skills[skill] += 1

    return {
        "suite_id": suite.suite_id,
        "tasks_total": len(suite.tasks),
        "repo_id": dict(repo),
        "category": dict(category),
        "difficulty": dict(difficulty),
        "skills_tested": dict(skills),
        "allowed_runtime_seconds": {str(k): v for k, v in sorted(runtime.items())},
    }
