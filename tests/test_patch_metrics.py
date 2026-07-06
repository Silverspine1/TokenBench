from tokenbench.telemetry.collector import count_diff_lines, patch_metrics

SAMPLE_DIFF = """diff --git a/src/contract.js b/src/contract.js
index 111..222 100644
--- a/src/contract.js
+++ b/src/contract.js
@@ -1,4 +1,5 @@
 const x = 1;
-const amount = 10;
+const amount_cents = 1000;
+const tax = 0;
 module.exports = {};
"""

CHANGES = {
    "added": ["src/new.js"],
    "modified": ["src/contract.js"],
    "deleted": [],
    "scored_modified": ["src/contract.js"],
    "ignored_modified": [],
    "forbidden_modified": [],
}


def test_count_diff_lines_ignores_headers():
    added, deleted = count_diff_lines(SAMPLE_DIFF)
    # +amount_cents and +tax are additions; ---/+++/@@ headers ignored.
    assert added == 2
    assert deleted == 1


def test_patch_metrics_no_patch_is_zeroed(tmp_path):
    m = patch_metrics(tmp_path / "missing.diff", CHANGES)
    assert m["patch_bytes"] == 0
    assert m["lines_added"] == 0
    assert m["lines_deleted"] == 0
    assert m["line_churn"] == 0
    # File classification still comes from file_changes.
    assert m["changed_scored_files"] == 1
    assert m["added_files"] == 1


def test_patch_metrics_counts_from_diff(tmp_path):
    p = tmp_path / "patch.diff"
    p.write_text(SAMPLE_DIFF, encoding="utf-8")
    m = patch_metrics(p, CHANGES)
    assert m["lines_added"] == 2
    assert m["lines_deleted"] == 1
    assert m["line_churn"] == 3
    assert m["patch_bytes"] == p.stat().st_size
    assert m["changed_files_total"] == 2
    assert m["changed_scored_files"] == 1
    assert m["patch_estimated_tokens"] >= 1
