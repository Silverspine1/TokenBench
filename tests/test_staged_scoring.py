"""Staged scoring: friction bands, weighting, and the low-stage2 cap."""

from __future__ import annotations

import json

import pytest

from tokenbench.staged.scoring import (
    extension_friction_score,
    staged_metrics,
    staged_score,
)


@pytest.mark.parametrize(
    "ratio,expected",
    [(0.5, 100.0), (1.0, 100.0), (1.5, 80.0), (2.0, 80.0), (3.0, 60.0), (4.0, 60.0), (9.0, 30.0)],
)
def test_friction_bands(ratio, expected):
    assert extension_friction_score(ratio) == expected


def test_staged_score_weighting():
    # stage1=90, stage2=90, friction 1.0 -> efs 100
    # 0.30*90 + 0.45*90 + 0.25*100 = 92.5
    r = staged_score(90.0, 90.0, 1.0)
    assert r["staged_score"] == 92.5
    assert r["extension_friction_score"] == 100.0


def test_low_stage2_caps_friction_score():
    # stage2 < 80 caps efs at 50 even when churn was tiny (ratio 0.2 -> band 100)
    r = staged_score(90.0, 40.0, 0.2)
    assert r["extension_friction_score"] == 50.0
    # 0.30*90 + 0.45*40 + 0.25*50 = 27 + 18 + 12.5 = 57.5
    assert r["staged_score"] == 57.5


def test_staged_metrics_from_run_dirs(tmp_path):
    s1 = tmp_path / "s1"
    s2 = tmp_path / "s2"
    s1.mkdir()
    s2.mkdir()
    (s1 / "telemetry.json").write_text(json.dumps(
        {"patch": {"line_churn": 40, "changed_files_total": 2}}), encoding="utf-8")
    (s1 / "file_changes.json").write_text(json.dumps(
        {"added": ["a.js"], "modified": ["b.js"], "deleted": []}), encoding="utf-8")
    (s2 / "telemetry.json").write_text(json.dumps(
        {"patch": {"line_churn": 120, "changed_files_total": 3, "added_files": 1,
                   "changed_forbidden_files": 0, "patch_estimated_tokens": 99}}), encoding="utf-8")
    (s2 / "file_changes.json").write_text(json.dumps(
        {"added": ["c.js"], "modified": ["b.js"], "deleted": []}), encoding="utf-8")

    m = staged_metrics(s1, s2)
    assert m["stage1_line_churn"] == 40
    assert m["stage2_line_churn"] == 120
    assert m["extension_friction"] == 3.0  # 120 / 40
    assert m["stage2_touched_stage1_files"] == 1  # b.js in both
    assert m["stage2_new_files"] == 1
