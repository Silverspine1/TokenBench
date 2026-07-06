"""Deterministic content hashing of a directory tree."""

from __future__ import annotations

import hashlib
from fnmatch import fnmatch
from pathlib import Path

from .paths import is_junk_path


def _rel_posix(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_junk(rel: str) -> bool:
    return is_junk_path(rel)


def _ignored(rel: str, ignored_patterns: list[str]) -> bool:
    return any(fnmatch(rel, pat) for pat in ignored_patterns)


def iter_files(root: Path, ignored_patterns: list[str] | None = None):
    """Yield (rel_posix_path, abs_path) for non-junk, non-ignored files, sorted."""
    ignored_patterns = ignored_patterns or []
    root = root.resolve()
    out: list[tuple[str, Path]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = _rel_posix(root, path)
        if _is_junk(rel):
            continue
        if _ignored(rel, ignored_patterns):
            continue
        out.append((rel, path))
    out.sort(key=lambda t: t[0])
    return out


def file_hashes(root: Path, ignored_patterns: list[str] | None = None) -> dict[str, str]:
    """Map of rel path -> sha256 of file content (deterministic)."""
    result: dict[str, str] = {}
    for rel, path in iter_files(root, ignored_patterns):
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        result[rel] = h.hexdigest()
    return result


def hash_directory(path: Path, ignored_patterns: list[str] | None = None) -> str:
    """SHA-256 over sorted (path, content-hash) pairs. Stable across runs."""
    hashes = file_hashes(path, ignored_patterns)
    digest = hashlib.sha256()
    for rel in sorted(hashes):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashes[rel].encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()
