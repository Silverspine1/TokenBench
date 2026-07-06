import sys
from pathlib import Path

import pytest

# Ensure the project root (containing the `tokenbench` package) is importable.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tokenbench.manifests.schema import TaskManifest  # noqa: E402

# A private string planted in every private manifest field, so leak tests can
# assert this exact token never appears in a prompt, page, or bundle.
PRIVATE_TOKEN = "SECRET-ROOT-CAUSE-DO-NOT-LEAK"


def _write_snapshot(root: Path, value: str) -> None:
    pkg = root / "demo"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "app.py").write_text(f"def add(a, b):\n    return {value}\n", encoding="utf-8")


@pytest.fixture
def demo_task(tmp_path):
    """A self-contained benchmark base with one fast Python task.

    Visible and hidden commands trivially pass, so submit/score run quickly with
    no real toolchain. Every private manifest field carries ``PRIVATE_TOKEN`` so
    leak tests can assert the firewall holds. Also writes a suite and a manual
    condition so the UI can be exercised against this temp base.
    """
    base = tmp_path
    broken = base / "benchmark/repos/demo/broken/demo_fix_001"
    gold = base / "benchmark/repos/demo/gold"
    _write_snapshot(broken, "a - b")   # broken: subtraction
    _write_snapshot(gold, "a + b")     # gold: addition

    manifest = TaskManifest(
        task_id="demo_fix_001",
        repo_id="demo",
        mode="atomic",
        category="bugfix",
        difficulty="easy",
        prompt="Fix add() so it returns the sum of its arguments.",
        issue_title="add() returns the wrong result",
        issue_body="add(2, 3) should be 5.",
        expected_behavior=["add(2, 3) == 5"],
        broken_snapshot="benchmark/repos/demo/broken/demo_fix_001",
        gold_snapshot="benchmark/repos/demo/gold",
        visible_commands=['python -c "print(\'visible-ok\')"'],
        hidden_commands=['python -c "import sys; sys.exit(0)"'],
        allowed_runtime_seconds=60,
        forbidden_paths=["secret/**"],
        scored_paths=["demo/**"],
        # --- private fields, each tagged with the leak token ---
        expected_failure_summary=PRIVATE_TOKEN,
        root_cause_files=["demo/app.py"],
        task_author_notes=PRIVATE_TOKEN,
        skills_tested=[PRIVATE_TOKEN],
    )

    task_rel = "benchmark/manifests/demo/demo_fix_001.json"
    mpath = base / task_rel
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    suite = base / "benchmark/suites/demo.json"
    suite.parent.mkdir(parents=True, exist_ok=True)
    suite.write_text(
        '{"suite_id": "demo", "description": "demo", "tasks": ["%s"]}' % task_rel,
        encoding="utf-8",
    )

    cond = base / "benchmark/conditions/manual_generic_ide.json"
    cond.parent.mkdir(parents=True, exist_ok=True)
    cond.write_text(
        '{"condition_id": "manual_generic_ide", "agent": "manual-ide", '
        '"model": "user-entered", "official": false}',
        encoding="utf-8",
    )

    return {
        "base": base,
        "manifest": manifest,
        "manifest_path": mpath,
        "task_rel": task_rel,
        "private_token": PRIVATE_TOKEN,
        "edit_to_gold": edit_workspace_to_gold,
    }


def edit_workspace_to_gold(run_dir: Path) -> None:
    """Apply the fix in a run's workspace so submit yields a passing candidate."""
    app = Path(run_dir) / "workspace" / "demo" / "app.py"
    app.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
