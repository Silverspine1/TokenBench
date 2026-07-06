"""Deterministic reorg structure-contract scoring."""

from __future__ import annotations

from tokenbench.manifests.schema import StructureContract
from tokenbench.scoring.structure import structure_contract_score


def _write(p, text=""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_full_contract_satisfied(tmp_path):
    _write(tmp_path / "src/invoices/filters.js", "x")
    _write(tmp_path / "src/index.js", "export * from './invoices/filters.js'")
    contract = StructureContract(
        required_paths=["src/invoices/filters.js"],
        forbidden_paths=["src/m1.js"],  # absent -> cleared
        public_entrypoints=["src/index.js"],
        compatibility_imports=["src/index.js"],
    )
    r = structure_contract_score(contract, tmp_path)
    assert r["structure_contract_score"] == 100.0


def test_required_missing_lowers_score(tmp_path):
    _write(tmp_path / "src/index.js")
    contract = StructureContract(
        required_paths=["src/invoices/filters.js", "src/invoices/export.js"],
        public_entrypoints=["src/index.js"],
    )
    r = structure_contract_score(contract, tmp_path)
    assert r["required_paths_score"] == 0.0
    assert r["public_entrypoint_score"] == 100.0


def test_opaque_file_as_thin_shim_counts_as_cleared(tmp_path):
    _write(tmp_path / "src/m1.js", "export * from './invoices/filters.js';\n")  # tiny shim
    _write(tmp_path / "src/m2.js", "x" * 5000)  # still fat -> not cleared
    contract = StructureContract(forbidden_paths=["src/m1.js", "src/m2.js"], shim_max_bytes=400)
    r = structure_contract_score(contract, tmp_path)
    assert r["forbidden_paths_score"] == 50.0


def test_deterministic(tmp_path):
    _write(tmp_path / "src/a.js")
    contract = StructureContract(required_paths=["src/a.js"], forbidden_paths=["src/m1.js"])
    a = structure_contract_score(contract, tmp_path)
    b = structure_contract_score(contract, tmp_path)
    assert a == b
