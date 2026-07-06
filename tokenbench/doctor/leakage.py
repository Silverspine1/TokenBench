"""Broken-snapshot leakage detection.

A broken candidate workspace must read like a normal project with an issue to
fix — not a benchmark with the answer written next to the bug. This module scans
the materialized source of a broken snapshot for confession-style markers
(``BUG``, ``intentional bug``, ``hidden test`` ...) and reports each hit.

Any ``critical`` finding makes the task invalid.
"""

from __future__ import annotations

import re
from pathlib import Path

# Source-ish extensions worth scanning. Binary/junk is skipped by extension.
SCANNED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json",
    ".md", ".txt", ".yaml", ".yml", ".toml",
    ".php", ".go", ".rs", ".cpp", ".h", ".hpp",
    ".dart", ".kt", ".xml", ".html", ".css",
}

# Directories never worth scanning even if they slip into a snapshot.
_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", ".next", "target",
}

# Forbidden leakage patterns. Each is (compiled regex, severity). These are the
# phrases an injected-bug author tends to leave behind; inside a broken workspace
# they almost always confess the planted defect.
_PATTERN_SPECS: list[tuple[str, str]] = [
    (r"\bBUG\b", "critical"),
    (r"\bBROKEN\b", "critical"),
    (r"\bINTENTIONAL\b", "critical"),
    (r"intentional bug", "critical"),
    (r"wrong on purpose", "critical"),
    (r"on purpose", "critical"),
    (r"lookahead", "critical"),
    (r"look-ahead", "critical"),
    (r"leakage", "critical"),
    (r"\bleaks?\b", "critical"),
    (r"off[\s-]?by[\s-]?one", "critical"),
    (r"applied twice", "critical"),
    (r"subtracted twice", "critical"),
    (r"charged twice", "critical"),
    (r"fee applied twice", "critical"),
    (r"bad split", "critical"),
    (r"future rows", "critical"),
    (r"hidden test", "critical"),
    (r"expected failure", "critical"),
    (r"\bfix ?me\b", "critical"),
    (r"this is the task", "critical"),
    (r"\bTODO\b", "warning"),
]

_PATTERNS = [(re.compile(p, re.IGNORECASE), sev) for p, sev in _PATTERN_SPECS]


def _iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in _SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.suffix.lower() not in SCANNED_EXTENSIONS:
            continue
        yield p


def scan_broken_snapshot_leakage(snapshot_dir: Path) -> list[dict]:
    """Scan ``snapshot_dir`` and return one finding per matched line.

    Each finding: ``{path, line, pattern, text, severity}``. ``path`` is POSIX,
    relative to the snapshot root.
    """
    root = Path(snapshot_dir)
    findings: list[dict] = []
    if not root.exists():
        return findings

    for path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for regex, severity in _PATTERNS:
                m = regex.search(line)
                if m:
                    findings.append(
                        {
                            "path": rel,
                            "line": lineno,
                            "pattern": m.group(0),
                            "text": line.strip()[:200],
                            "severity": severity,
                        }
                    )
    return findings


def has_critical_leakage(findings: list[dict]) -> bool:
    return any(f.get("severity") == "critical" for f in findings)
