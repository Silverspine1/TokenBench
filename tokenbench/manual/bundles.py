"""Export/import bundles for running a task on another machine (Mode B).

The export bundle carries only what an operator needs to solve the task — the
broken workspace, the prompt, the visible commands, and a whitelisted public
manifest — and is asserted to contain no hidden tests, accepted solutions, or
private manifest notes. Import reverses it: a candidate zip is extracted with
strict path-traversal defence, then scored through the normal submit path.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from ..manifests.schema import TaskManifest
from .public import PRIVATE_MANIFEST_FIELDS, public_manifest
from .service import _read_manual_ide, _write_manual_ide, submit_manual_run

# Run artifacts that must never be placed in an export bundle.
_FORBIDDEN_BUNDLE_NAMES = {
    "task_manifest.json",
    "run_state.json",
    "score.json",
    "telemetry.json",
    "manual_cost.json",
    "hidden_tests.stdout.log",
    "hidden_tests.stderr.log",
}

_README = """# TokenBench task bundle

This bundle contains a broken software workspace and a task to fix.

1. Read `prompt.txt` for the task.
2. Edit files under `workspace/` to solve it.
3. Run the commands in `visible_commands.txt` to check your work.
4. When done, zip the `workspace/` directory and submit it back through the
   TokenBench UI ("Import candidate").

Do not look for hidden tests — there are none in this bundle. Your submission is
scored by the harness after import.
"""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _add_dir(zf: zipfile.ZipFile, src: Path, arc_prefix: str) -> None:
    """Add every file under ``src`` to the zip beneath ``arc_prefix``."""
    src = Path(src)
    for path in sorted(src.rglob("*")):
        if path.is_file():
            arcname = f"{arc_prefix}/{path.relative_to(src).as_posix()}"
            zf.write(path, arcname)


def export_bundle(base: Path, run_dir: Path, out_zip: Path) -> dict:
    """Write an operator-safe task bundle zip. Returns the bundle metadata."""
    base = Path(base)
    run_dir = Path(run_dir)
    out_zip = Path(out_zip)
    record = _read_manual_ide(run_dir)

    manifest = TaskManifest.model_validate_json(
        (run_dir / "task_manifest.json").read_text(encoding="utf-8")
    )
    pub = public_manifest(manifest)

    # Firewall: the public manifest must carry no private key.
    leaked = set(pub) & set(PRIVATE_MANIFEST_FIELDS)
    if leaked:
        raise ValueError(f"public manifest leaks private fields: {sorted(leaked)}")

    workspace = run_dir / "workspace"
    if not workspace.exists():
        raise FileNotFoundError(f"no workspace to export: {workspace}")

    prompt = (run_dir / "prompt.txt").read_text(encoding="utf-8") if (
        run_dir / "prompt.txt"
    ).exists() else ""
    visible = "\n".join(manifest.visible_commands)

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        _add_dir(zf, workspace, "workspace")
        zf.writestr("prompt.txt", prompt)
        zf.writestr("visible_commands.txt", visible)
        zf.writestr("README_INSTRUCTIONS.md", _README)
        zf.writestr("public_manifest.json", json.dumps(pub, indent=2))

        # Firewall: no benchmark-internal file may appear anywhere in the zip.
        for name in zf.namelist():
            base_name = name.rsplit("/", 1)[-1]
            if base_name in _FORBIDDEN_BUNDLE_NAMES:
                raise ValueError(f"bundle would leak internal artifact: {name}")

    bundle_hash = _sha256_file(out_zip)
    from ..core.ids import utc_now

    record["bundle_hash"] = bundle_hash
    record["bundle_exported_at"] = utc_now().isoformat()
    _write_manual_ide(run_dir, record)

    return {
        "bundle_path": out_zip.as_posix(),
        "bundle_hash": bundle_hash,
        "files": [
            "workspace/",
            "prompt.txt",
            "visible_commands.txt",
            "README_INSTRUCTIONS.md",
            "public_manifest.json",
        ],
    }


def _is_unsafe_member(name: str) -> bool:
    """True when a zip member name would escape the extraction root."""
    if not name or name.endswith("/"):
        # Directory entries are harmless on their own; still reject traversal.
        pass
    norm = name.replace("\\", "/")
    if norm.startswith("/"):
        return True
    # Windows absolute path / drive letter, e.g. "C:/x" or "C:\\x".
    if len(norm) >= 2 and norm[1] == ":":
        return True
    parts = [p for p in norm.split("/") if p not in ("", ".")]
    return any(p == ".." for p in parts)


def safe_extract(zip_path: Path, dest: Path) -> None:
    """Extract a zip into ``dest``, rejecting absolute paths and ``..`` traversal."""
    zip_path = Path(zip_path)
    dest = Path(dest)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if _is_unsafe_member(info.filename):
                raise ValueError(f"unsafe path in zip: {info.filename!r}")
        dest.mkdir(parents=True, exist_ok=True)
        zf.extractall(dest)


def _resolve_workspace_root(extracted: Path) -> Path:
    """Pick the workspace root inside an extracted candidate tree.

    Operators zip either the ``workspace/`` directory itself or its contents; a
    single top-level ``workspace`` dir is treated as the root either way.
    """
    candidate = extracted / "workspace"
    if candidate.is_dir():
        return candidate
    return extracted


def import_candidate(base: Path, run_dir: Path, candidate_zip: Path) -> dict:
    """Import an externally-produced candidate zip and score it.

    Replaces the run's ``workspace/`` with the operator's edited tree (extracted
    safely), records provenance, then runs the normal submit + score path.
    """
    base = Path(base)
    run_dir = Path(run_dir)
    candidate_zip = Path(candidate_zip)
    record = _read_manual_ide(run_dir)

    tmp = Path(tempfile.mkdtemp(prefix="tokenbench-import-"))
    try:
        safe_extract(candidate_zip, tmp)
        workspace_root = _resolve_workspace_root(tmp)

        target = run_dir / "workspace"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(workspace_root, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    from ..core.ids import utc_now

    record["candidate_source"] = "bundle_import"
    record["candidate_zip_hash"] = _sha256_file(candidate_zip)
    record["candidate_imported_at"] = utc_now().isoformat()
    _write_manual_ide(run_dir, record)

    return submit_manual_run(base, run_dir)
