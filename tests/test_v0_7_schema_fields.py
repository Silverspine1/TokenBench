"""V0.7 manifest schema: new reorg/staged/output-stress fields load and default."""

from __future__ import annotations

from tokenbench.manifests.schema import TaskManifest


def _base(**extra) -> dict:
    data = {
        "task_id": "t",
        "repo_id": "r",
        "mode": "atomic",
        "category": "bugfix",
        "difficulty": "easy",
        "prompt": "p",
        "broken_snapshot": "b",
        "gold_snapshot": "g",
        "hidden_commands": ["echo hi"],
        "allowed_runtime_seconds": 60,
        "forbidden_paths": [],
    }
    data.update(extra)
    return data


def test_legacy_manifest_defaults_new_fields_empty():
    m = TaskManifest.model_validate(_base())
    assert m.structure_contract is None
    assert m.output_stress is None
    assert m.stage is None
    assert m.stage_group_id == ""
    assert m.expected_behavior == []


def test_staged_implementation_category_and_linkage():
    m = TaskManifest.model_validate(
        _base(
            category="staged_implementation",
            stage=2,
            stage_group_id="grp",
            previous_stage_task_id="grp_stage_1",
            input_source="previous_candidate",
        )
    )
    assert m.category.value == "staged_implementation"
    assert m.stage == 2
    assert m.input_source == "previous_candidate"


def test_structure_contract_and_output_stress_load():
    m = TaskManifest.model_validate(
        _base(
            category="reorg",
            expected_behavior=["totals unchanged", "import still works"],
            structure_contract={
                "required_paths": ["src/a.js"],
                "forbidden_paths": ["src/m1.js"],
                "public_entrypoints": ["src/index.js"],
                "compatibility_imports": ["src/index.js"],
            },
            output_stress={
                "enabled": True,
                "expected_visible_output_bytes_min": 50000,
                "expected_visible_output_bytes_max": 300000,
            },
        )
    )
    assert m.structure_contract.required_paths == ["src/a.js"]
    assert m.structure_contract.shim_max_bytes == 400
    assert m.output_stress.enabled is True
    assert m.expected_behavior[0] == "totals unchanged"
