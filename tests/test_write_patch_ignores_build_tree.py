"""Regression: write_patch must diff real source even beside a build tree.

A whole-tree ``git diff --no-index`` walks generated output (``target/``,
``node_modules/``) and aborts with empty stdout the moment it hits an
inaccessible artifact (e.g. a Rust ``target/`` path past the Windows path
limit), silently zeroing line-churn. write_patch diffs only the classified
changed files, so a junk build tree can never erase a real source diff.
"""

from tokenbench.core.artifacts import write_patch
from tokenbench.telemetry.collector import count_diff_lines


def test_source_churn_survives_a_junk_build_tree(tmp_path):
    broken = tmp_path / "broken"
    candidate = tmp_path / "candidate"
    for root in (broken, candidate):
        (root / "src").mkdir(parents=True)
        (root / "target" / "debug").mkdir(parents=True)

    (broken / "src" / "app.rs").write_text("fn main() {}\n", encoding="utf-8")
    (candidate / "src" / "app.rs").write_text(
        "fn main() {\n    run();\n}\n", encoding="utf-8"
    )
    # Generated build noise present in both trees — must be ignored entirely.
    (broken / "target" / "debug" / "app.o").write_text("OLD", encoding="utf-8")
    (candidate / "target" / "debug" / "app.o").write_text("NEW", encoding="utf-8")

    file_changes = {
        "added": [],
        "modified": ["src/app.rs"],
        "deleted": [],
    }
    patch_path = tmp_path / "patch.diff"
    assert write_patch(broken, candidate, patch_path, file_changes) is True

    text = patch_path.read_text(encoding="utf-8")
    added, deleted = count_diff_lines(text)
    assert added + deleted > 0, "real source edit produced zero churn"
    assert "app.rs" in text
    assert "target" not in text
