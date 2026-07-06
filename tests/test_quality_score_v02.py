from tokenbench.scoring.quality import artifact_integrity_score, quality_score_v02

EMPTY = {
    "added": [],
    "modified": [],
    "deleted": [],
    "forbidden_modified": [],
    "ignored_modified": [],
    "scored_modified": [],
}


def test_perfect_quality():
    q = quality_score_v02(1.0, 1.0, 100.0, forbidden_modified=False)
    assert q == 100.0


def test_weighting_split():
    # 0.85*100 + 0.10*100 + 0.05*100 = 100; drop hidden to 0.5 -> 42.5+10+5
    q = quality_score_v02(0.5, 1.0, 100.0, forbidden_modified=False)
    assert q == 57.5


def test_forbidden_override_zero():
    q = quality_score_v02(1.0, 1.0, 100.0, forbidden_modified=True)
    assert q == 0.0


def test_artifact_clean_is_100():
    assert artifact_integrity_score(EMPTY, patch_empty=False, hidden_failed=False) == 100.0


def test_artifact_forbidden_is_zero():
    changes = dict(EMPTY, forbidden_modified=["tests/x.py"])
    assert artifact_integrity_score(changes, patch_empty=False, hidden_failed=False) == 0.0


def test_artifact_deleted_outside_scored():
    changes = dict(EMPTY, deleted=["docs/readme.md"], scored_modified=[])
    assert artifact_integrity_score(changes, patch_empty=False, hidden_failed=False) == 80.0


def test_artifact_deleted_inside_scored_is_fine():
    changes = dict(EMPTY, deleted=["src/a.py"], scored_modified=["src/a.py"])
    assert artifact_integrity_score(changes, patch_empty=False, hidden_failed=False) == 100.0


def test_artifact_ignored_modified():
    changes = dict(EMPTY, ignored_modified=["fixtures/logs/x.log"])
    assert artifact_integrity_score(changes, patch_empty=False, hidden_failed=False) == 90.0


def test_artifact_empty_patch_and_hidden_fail():
    assert artifact_integrity_score(EMPTY, patch_empty=True, hidden_failed=True) == 90.0


def test_artifact_penalties_stack_and_clamp():
    changes = dict(EMPTY, deleted=["docs/x"], ignored_modified=["fixtures/logs/y"])
    # 100 - 20 - 10 - 10 = 60
    assert artifact_integrity_score(changes, patch_empty=True, hidden_failed=True) == 60.0
