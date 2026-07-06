"""build_score recomposes quality for reorg tasks: 0.70 hidden + 0.25 structure + 0.05 artifact."""

from __future__ import annotations

from tokenbench.manifests.schema import TaskManifest
from tokenbench.scoring.scorer import build_score


def _reorg_manifest() -> TaskManifest:
    return TaskManifest.model_validate(
        {
            "task_id": "t",
            "repo_id": "r",
            "mode": "atomic",
            "category": "reorg",
            "difficulty": "medium",
            "prompt": "p",
            "broken_snapshot": "b",
            "gold_snapshot": "g",
            "hidden_commands": ["echo"],
            "allowed_runtime_seconds": 60,
            "forbidden_paths": [],
            "structure_contract": {"required_paths": ["src/a.js"]},
        }
    )


def _run_state(hidden_total: int, hidden_passed: int) -> dict:
    return {
        "run_id": "r:t",
        "agent": {"wall_time_seconds": 1.0},
        "visible": [],
        "hidden": [
            {"passed": hidden_passed == hidden_total,
             "parsed": {"tests_total": hidden_total, "tests_passed": hidden_passed,
                        "tests_failed": hidden_total - hidden_passed, "tests_skipped": 0}}
        ],
        "paths": {},
    }


_FILE_CHANGES = {
    "added": ["src/a.js"], "modified": [], "deleted": [],
    "scored_modified": ["src/a.js"], "forbidden_modified": [], "ignored_modified": [],
}


def test_reorg_quality_uses_structure_weighting():
    m = _reorg_manifest()
    structure = {
        "required_paths_score": 80.0, "forbidden_paths_score": 80.0,
        "public_entrypoint_score": 80.0, "compatibility_score": 80.0,
        "structure_contract_score": 80.0,
    }
    rep = build_score(_run_state(10, 10), m, _FILE_CHANGES, 0, structure)
    # 0.70*100 + 0.25*80 + 0.05*100 = 95
    assert rep["quality_score"] == 95.0
    assert rep["structure_components"]["structure_contract_score"] == 80.0


def test_reorg_broken_behavior_drops_quality_below_threshold():
    m = _reorg_manifest()
    structure = {"required_paths_score": 100.0, "forbidden_paths_score": 100.0,
                 "public_entrypoint_score": 100.0, "compatibility_score": 100.0,
                 "structure_contract_score": 100.0}
    rep = build_score(_run_state(10, 5), m, _FILE_CHANGES, 0, structure)
    # 0.70*50 + 0.25*100 + 0.05*100 = 65 -> below 80, not a success
    assert rep["quality_score"] == 65.0
    assert rep["success"] is False


def test_non_reorg_ignores_structure_result():
    m = _reorg_manifest().model_copy(update={"category": "bugfix"}, deep=True)
    m = TaskManifest.model_validate(m.model_dump())
    rep = build_score(_run_state(10, 10), m, _FILE_CHANGES, 0, None)
    assert rep["structure_components"] is None
    # plain quality v0.2: 0.85*100 + 0.10*1.0(no visible) + 0.05*100 ~ 100
    assert rep["quality_score"] == 100.0
