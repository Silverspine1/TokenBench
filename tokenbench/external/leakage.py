"""Leakage scanning for external-repo task patches and prompts."""

from __future__ import annotations

import re
from pathlib import Path

# Hard-fail terms in defect patches (comment content, variable names, etc.)
_PATCH_HARD_TERMS: list[tuple[str, str]] = [
    (r"\bBUG\b", "critical"),
    (r"\bFIXME\b", "critical"),
    (r"\bintentional\b", "critical"),
    (r"\binjected\b", "critical"),
    (r"\bbenchmark\b", "critical"),
    (r"\bhidden\b", "critical"),
    (r"\bTokenBench\b", "critical"),
    (r"wrong on purpose", "critical"),
    (r"\bbroken\b", "critical"),
    (r"\bdefect\b", "critical"),
    (r"\bTODO\b", "warning"),
    (r"\bHACK\b", "warning"),
]

# Hard-fail terms in agent-facing content (prompt, public manifest, visible tests)
_PROMPT_HARD_TERMS: list[tuple[str, str]] = [
    (r"TokenBench hidden", "critical"),
    (r"accepted solution", "critical"),
    (r"root cause", "critical"),
    (r"injected bug", "critical"),
    (r"defect\.patch", "critical"),
    (r"hidden_tests", "critical"),
    (r"private_notes", "critical"),
]

_PATCH_PATTERNS = [(re.compile(p, re.IGNORECASE), s) for p, s in _PATCH_HARD_TERMS]
_PROMPT_PATTERNS = [(re.compile(p, re.IGNORECASE), s) for p, s in _PROMPT_HARD_TERMS]


def _scan_text(text: str, patterns: list[tuple[re.Pattern, str]], source: str) -> list[dict]:
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for regex, severity in patterns:
            m = regex.search(line)
            if m:
                findings.append({
                    "source": source,
                    "line": lineno,
                    "pattern": m.group(0),
                    "text": line.strip()[:200],
                    "severity": severity,
                })
    return findings


def scan_defect_patch(patch_file: Path) -> list[dict]:
    """Scan a defect.patch file for banned markers."""
    if not patch_file.exists():
        return []
    text = patch_file.read_text(encoding="utf-8", errors="replace")
    # Only scan comment lines and added lines in the patch (lines starting with + or #)
    relevant_lines = []
    for line in text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            relevant_lines.append(line[1:])  # strip leading +
        elif line.startswith("#"):
            relevant_lines.append(line)
    return _scan_text("\n".join(relevant_lines), _PATCH_PATTERNS, str(patch_file))


def scan_agent_facing_content(text: str, source: str = "prompt") -> list[dict]:
    """Scan agent-visible text for hard-fail leakage patterns."""
    return _scan_text(text, _PROMPT_PATTERNS, source)


def scan_task_for_leakage(task_dir: Path) -> dict:
    """Run all leakage scans for a task directory.

    Checks:
    - defect.patch for banned markers
    - manifest.json prompt/issue_body for root-cause hints
    - visible_tests/ for hidden-test names or private metadata
    """
    findings: list[dict] = []

    # Scan defect patch
    patch_file = task_dir / "defect.patch"
    findings.extend(scan_defect_patch(patch_file))

    # Scan manifest prompt
    manifest_file = task_dir / "manifest.json"
    if manifest_file.exists():
        import json
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        for field in ("prompt", "issue_body", "issue_title"):
            val = manifest.get(field, "")
            if val:
                findings.extend(scan_agent_facing_content(val, source=f"manifest.{field}"))

    # Scan visible tests
    visible_dir = task_dir / "visible_tests"
    if visible_dir.exists():
        for f in sorted(visible_dir.rglob("*")):
            if f.is_file() and f.suffix in {".py", ".js", ".ts"}:
                text = f.read_text(encoding="utf-8", errors="replace")
                findings.extend(scan_agent_facing_content(text, source=str(f.relative_to(task_dir))))

    has_critical = any(f["severity"] == "critical" for f in findings)
    return {
        "task_dir": task_dir.as_posix(),
        "findings": findings,
        "has_critical": has_critical,
        "passed": not has_critical,
    }
