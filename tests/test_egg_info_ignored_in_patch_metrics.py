from tokenbench.core.artifacts import filter_patch_text
from tokenbench.telemetry.collector import patch_metrics

# A real git --no-index diff: one genuine source edit plus egg-info / cache noise.
RAW_DIFF = '''diff --git "a/x/candidate/marketlab/backtest.py" "b/x/candidate/marketlab/backtest.py"
index 6438680..b40fbc7 100644
--- "a/x/candidate/marketlab/backtest.py"
+++ "b/x/candidate/marketlab/backtest.py"
@@ -10,7 +10,7 @@ def net_pnl(...):
-    return gross_pnl - fee - fee
+    return gross_pnl - fee - slippage
diff --git "a/x/candidate/marketlab_ml.egg-info/PKG-INFO" "b/x/candidate/marketlab_ml.egg-info/PKG-INFO"
new file mode 100644
index 0000000..254be0d
--- /dev/null
+++ "b/x/candidate/marketlab_ml.egg-info/PKG-INFO"
@@ -0,0 +1,5 @@
+Metadata-Version: 2.4
+Name: marketlab-ml
+Version: 0.1.0
+Summary: Backtesting toolkit.
+Requires-Python: >=3.10
diff --git "a/x/candidate/marketlab/__pycache__/backtest.cpython-313.pyc" "b/x/candidate/marketlab/__pycache__/backtest.cpython-313.pyc"
new file mode 100644
index 0000000..627bb8a
Binary files /dev/null and "b/x/candidate/marketlab/__pycache__/backtest.cpython-313.pyc" differ
diff --git "a/x/candidate/.pytest_cache/CACHEDIR.TAG" "b/x/candidate/.pytest_cache/CACHEDIR.TAG"
new file mode 100644
index 0000000..fce15ad
--- /dev/null
+++ "b/x/candidate/.pytest_cache/CACHEDIR.TAG"
@@ -0,0 +1,1 @@
+Signature: 8a477f597d28d172789f06886806bc55
'''


def test_filter_patch_drops_only_generated_sections():
    filtered = filter_patch_text(RAW_DIFF)
    assert "marketlab/backtest.py" in filtered
    assert "egg-info" not in filtered
    assert "__pycache__" not in filtered
    assert ".pytest_cache" not in filtered
    # The genuine edit's content lines remain.
    assert "+    return gross_pnl - fee - slippage" in filtered
    assert "Metadata-Version" not in filtered


def test_patch_metrics_churn_excludes_generated(tmp_path):
    p = tmp_path / "patch.diff"
    p.write_text(filter_patch_text(RAW_DIFF), encoding="utf-8")
    # file_changes already excludes junk (built from filtered hashes).
    changes = {
        "added": [],
        "modified": ["marketlab/backtest.py"],
        "deleted": [],
        "scored_modified": ["marketlab/backtest.py"],
        "ignored_modified": [],
        "forbidden_modified": [],
    }
    m = patch_metrics(p, changes)
    # Only the single real source line edit counts (1 add / 1 delete).
    assert m["lines_added"] == 1
    assert m["lines_deleted"] == 1
    assert m["line_churn"] == 2
    assert m["changed_files_total"] == 1
    assert m["changed_scored_files"] == 1
