"""Deterministic structure-contract scoring for reorg tasks (V0.7).

A reorg task declares a ``StructureContract``: the module layout the candidate
must reach. Scoring is purely objective — file existence and byte size, no
subjective architecture judgement:

    structure_contract_score = mean(
        required_paths_score,      # required modules now exist
        forbidden_paths_score,     # opaque files gone or reduced to thin shims
        public_entrypoint_score,   # public entrypoints survive
        compatibility_score,       # back-compat re-export paths survive
    )

Same candidate tree in, same scores out.
"""

from __future__ import annotations

from pathlib import Path

from ..manifests.schema import StructureContract
from .efficiency import clamp


def _fraction_present(paths: list[str], candidate_dir: Path) -> float:
    """Percent of ``paths`` that exist as files/dirs under ``candidate_dir``."""
    if not paths:
        return 100.0
    present = sum(1 for p in paths if (candidate_dir / p).exists())
    return 100.0 * present / len(paths)


def _fraction_cleared(paths: list[str], candidate_dir: Path, shim_max_bytes: int) -> float:
    """Percent of opaque ``paths`` removed or reduced to a thin shim.

    An opaque path is "cleared" when it no longer exists, or still exists but is
    no larger than ``shim_max_bytes`` (a back-compat re-export shim is allowed).
    """
    if not paths:
        return 100.0
    cleared = 0
    for p in paths:
        target = candidate_dir / p
        if not target.exists():
            cleared += 1
        elif target.is_file() and target.stat().st_size <= shim_max_bytes:
            cleared += 1
    return 100.0 * cleared / len(paths)


def structure_contract_score(contract: StructureContract, candidate_dir: Path) -> dict:
    """Score a candidate tree against a reorg structure contract.

    Returns the four sub-scores plus their equal-weighted mean, each clamped to
    [0, 100]. ``candidate_dir`` is the archived candidate workspace.
    """
    candidate_dir = Path(candidate_dir)

    required = clamp(_fraction_present(contract.required_paths, candidate_dir))
    forbidden = clamp(
        _fraction_cleared(contract.forbidden_paths, candidate_dir, contract.shim_max_bytes)
    )
    entrypoint = clamp(_fraction_present(contract.public_entrypoints, candidate_dir))
    compatibility = clamp(_fraction_present(contract.compatibility_imports, candidate_dir))

    overall = (required + forbidden + entrypoint + compatibility) / 4.0

    return {
        "required_paths_score": round(required, 4),
        "forbidden_paths_score": round(forbidden, 4),
        "public_entrypoint_score": round(entrypoint, 4),
        "compatibility_score": round(compatibility, 4),
        "structure_contract_score": round(clamp(overall), 4),
    }
