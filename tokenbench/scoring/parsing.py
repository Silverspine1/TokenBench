"""Structured test-result parsing (V0.2).

Turns raw test-command output into a per-command result record:

    {
      "framework": "pytest",
      "command": "pytest ...",
      "command_passed": true,
      "tests_total": 12,
      "tests_passed": 11,
      "tests_failed": 1,
      "tests_skipped": 0,
      "parse_confidence": "structured"
    }

When no framework summary can be parsed it falls back to command-level, where the
whole command counts as one test case:

    {
      "framework": "generic",
      "command": "npm test",
      "command_passed": false,
      "tests_total": 1,
      "tests_passed": 0,
      "tests_failed": 1,
      "tests_skipped": 0,
      "parse_confidence": "command_level"
    }
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# pytest summary tokens, e.g. "11 passed, 1 failed, 2 skipped in 0.35s".
_PYTEST_TOKEN = re.compile(
    r"(\d+)\s+(passed|failed|errors?|skipped|xfailed|xpassed)\b"
)

# Language-agnostic per-check marker emitted by TokenBench hidden/visible test
# drivers (any language): "TOKENBENCH_CHECKS passed=<n> total=<n>". Highest
# precedence so a single test process can report partial per-check counts even
# when the framework summary would otherwise collapse to one pass/fail case.
_TOKENBENCH_CHECKS = re.compile(
    r"TOKENBENCH_CHECKS\s+passed=(\d+)\s+total=(\d+)", re.IGNORECASE
)


def _parse_tokenbench_checks(text: str) -> tuple[int, int, int, int] | None:
    matches = list(_TOKENBENCH_CHECKS.finditer(text))
    if not matches:
        return None
    m = matches[-1]
    passed, total = int(m.group(1)), int(m.group(2))
    if total < passed:
        total = passed
    return total, passed, total - passed, 0


def pytest_json_report_available() -> bool:
    """True when the ``pytest-json-report`` plugin can be imported.

    Preferred when present; otherwise the text parser below is used.
    """
    try:  # pragma: no cover - depends on environment
        import pytest_jsonreport  # noqa: F401

        return True
    except Exception:
        return False


def parse_pytest_json(report_path: Path) -> dict | None:
    """Parse a ``pytest --json-report`` file into count fields, or None."""
    try:
        data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    summary = data.get("summary") or {}
    passed = int(summary.get("passed", 0))
    failed = int(summary.get("failed", 0)) + int(summary.get("error", 0))
    skipped = int(summary.get("skipped", 0)) + int(summary.get("xfailed", 0))
    total = int(summary.get("total", passed + failed + skipped))
    return {
        "tests_total": total,
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_skipped": skipped,
    }


def _detect_framework(command: str) -> str:
    c = command.lower()
    if "pytest" in c:
        return "pytest"
    if "vitest" in c:
        return "vitest"
    if "node" in c:
        return "node"
    return "generic"


def _parse_pytest(text: str) -> tuple[int, int, int, int] | None:
    passed = failed = skipped = 0
    found = False
    for m in _PYTEST_TOKEN.finditer(text):
        n, kind = int(m.group(1)), m.group(2)
        if kind in ("passed", "xpassed"):
            passed += n
        elif kind in ("failed", "error", "errors"):
            failed += n
        elif kind in ("skipped", "xfailed"):
            skipped += n
        found = True
    if not found:
        return None
    return passed + failed + skipped, passed, failed, skipped


def _parse_node(text: str) -> tuple[int, int, int, int] | None:
    """node:test TAP-style summary (# tests / # pass / # fail / # skipped)."""
    p = re.search(r"#\s*pass\s+(\d+)", text)
    f = re.search(r"#\s*fail\s+(\d+)", text)
    s = re.search(r"#\s*skipped\s+(\d+)", text)
    t = re.search(r"#\s*tests\s+(\d+)", text)
    if not (p or f or t):
        return None
    passed = int(p.group(1)) if p else 0
    failed = int(f.group(1)) if f else 0
    skipped = int(s.group(1)) if s else 0
    total = int(t.group(1)) if t else passed + failed + skipped
    return total, passed, failed, skipped


def _parse_vitest(text: str) -> tuple[int, int, int, int] | None:
    m = re.search(r"Tests\s+(.+)", text)
    if not m:
        return None
    line = m.group(1)

    def grab(word: str) -> int:
        mm = re.search(r"(\d+)\s+" + word, line)
        return int(mm.group(1)) if mm else 0

    passed, failed, skipped = grab("passed"), grab("failed"), grab("skipped")
    if passed + failed + skipped == 0:
        return None
    return passed + failed + skipped, passed, failed, skipped


def parse_test_output(
    command: str,
    passed: bool,
    stdout_text: str = "",
    stderr_text: str = "",
) -> dict:
    """Parse one test command's output into a structured result record."""
    framework = _detect_framework(command)
    text = (stdout_text or "") + "\n" + (stderr_text or "")

    # Highest precedence: explicit TOKENBENCH_CHECKS marker (any language).
    checks = _parse_tokenbench_checks(text)
    if checks is not None:
        total, p, f, s = checks
        return {
            "framework": "tokenbench_checks",
            "command": command,
            "command_passed": bool(passed),
            "tests_total": total,
            "tests_passed": p,
            "tests_failed": f,
            "tests_skipped": s,
            "parse_confidence": "structured",
        }

    parsed: tuple[int, int, int, int] | None = None
    if framework == "pytest":
        parsed = _parse_pytest(text)
    elif framework == "node":
        parsed = _parse_node(text)
    elif framework == "vitest":
        parsed = _parse_vitest(text)

    if parsed is not None:
        total, p, f, s = parsed
        return {
            "framework": framework,
            "command": command,
            "command_passed": bool(passed),
            "tests_total": total,
            "tests_passed": p,
            "tests_failed": f,
            "tests_skipped": s,
            "parse_confidence": "structured",
        }

    # Fallback: the command itself is the single test case.
    return {
        "framework": "generic",
        "command": command,
        "command_passed": bool(passed),
        "tests_total": 1,
        "tests_passed": 1 if passed else 0,
        "tests_failed": 0 if passed else 1,
        "tests_skipped": 0,
        "parse_confidence": "command_level",
    }
