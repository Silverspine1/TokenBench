"""Unit tests for the V0.7 doctor checks: structure contract, staged linkage, output stress."""

from __future__ import annotations

from tokenbench.doctor.task_doctor import (
    _check_output_stress,
    _check_staged_linkage,
    _check_structure_contract,
)
from tokenbench.manifests.schema import TaskManifest


def _m(**extra) -> TaskManifest:
    data = {
        "task_id": "t", "repo_id": "r", "mode": "atomic", "category": "bugfix",
        "difficulty": "medium", "prompt": "p", "broken_snapshot": "broken",
        "gold_snapshot": "gold", "hidden_commands": ["echo"],
        "allowed_runtime_seconds": 60, "forbidden_paths": [],
    }
    data.update(extra)
    return TaskManifest.model_validate(data)


# --- staged linkage --------------------------------------------------------

def test_stage2_requires_previous_and_input_source():
    errors, warnings = [], []
    m = _m(category="staged_implementation", stage=2, stage_group_id="g")
    _check_staged_linkage(m, errors, warnings)
    assert any("previous_stage_task_id" in e for e in errors)
    assert any("previous_candidate" in e for e in errors)


def test_valid_stage2_passes():
    errors, warnings = [], []
    m = _m(category="staged_implementation", stage=2, stage_group_id="g",
           previous_stage_task_id="g_stage_1", input_source="previous_candidate")
    _check_staged_linkage(m, errors, warnings)
    assert errors == []


# --- output stress ---------------------------------------------------------

def test_output_stress_over_ceiling_errors():
    errors, warnings = [], []
    m = _m(output_stress={"enabled": True})
    _check_output_stress(m, 2_000_000, errors, warnings)
    assert any("1 MB" in e for e in errors)


def test_output_stress_below_min_warns():
    errors, warnings = [], []
    m = _m(output_stress={"enabled": True, "expected_visible_output_bytes_min": 50000,
                          "expected_visible_output_bytes_max": 300000})
    _check_output_stress(m, 1000, errors, warnings)
    assert errors == []
    assert any("below the declared minimum" in w for w in warnings)


def test_output_stress_in_band_clean():
    errors, warnings = [], []
    m = _m(output_stress={"enabled": True, "expected_visible_output_bytes_min": 50000,
                          "expected_visible_output_bytes_max": 300000})
    _check_output_stress(m, 120000, errors, warnings)
    assert errors == [] and warnings == []


# --- structure contract ----------------------------------------------------

def test_reorg_without_contract_errors(tmp_path):
    errors, warnings = [], []
    m = _m(category="reorg")
    _check_structure_contract(m, tmp_path, errors, warnings)
    assert any("no structure_contract" in e for e in errors)


def test_required_path_must_exist_in_gold(tmp_path):
    (tmp_path / "gold").mkdir()
    (tmp_path / "broken").mkdir()
    errors, warnings = [], []
    m = _m(category="reorg", structure_contract={"required_paths": ["src/new.js"]})
    _check_structure_contract(m, tmp_path, errors, warnings)
    assert any("required path missing from gold" in e for e in errors)
