"""Dependency-install detection via simple substring scanning of logs."""

from __future__ import annotations

from pathlib import Path

# Obvious install/download markers. V0.5: deliberately simple substring match.
INSTALL_MARKERS = (
    "npm install",
    "pnpm install",
    "yarn add",
    "pip install",
    "poetry add",
    "cargo add",
    "go get",
    "composer install",
    "composer require",
    "flutter pub add",
    "gradle dependency download",
)


def detect_install_events(text: str) -> int:
    """Count occurrences of known install/download markers in ``text``."""
    lowered = text.lower()
    return sum(lowered.count(marker) for marker in INSTALL_MARKERS)


def count_dependency_events(log_paths: list[Path]) -> int:
    """Scan log files for install markers; return total event count."""
    total = 0
    for path in log_paths:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total += detect_install_events(text)
    return total


def detected_markers(text: str) -> list[str]:
    """Return the distinct install/download markers present in ``text``."""
    lowered = text.lower()
    return [marker for marker in INSTALL_MARKERS if marker in lowered]


def collect_install_markers(log_paths: list[Path]) -> list[str]:
    """Scan log files; return the sorted, deduplicated markers observed."""
    found: set[str] = set()
    for path in log_paths:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        found.update(detected_markers(text))
    return sorted(found)
