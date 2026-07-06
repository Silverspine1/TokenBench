"""Task-hardness audit.

Reports structural signals that correlate with a task being discriminative
(rather than a trivial single-file smoke task) and warns when a task labelled
``hard``/``frontier_hard`` looks too easy. These are advisory signals, not hard
errors: ``doctor`` decides validity; this decides whether a task is likely to
separate strong models from weak ones.

Signals per task:
  * expected_changed_files_min / expected_changed_files_max
  * hidden_test_count          (test cases discovered in the hidden command(s))
  * visible_test_count         (test cases discovered in the visible command(s))
  * root_cause_file_count      (len(root_cause_files))
  * repo_file_count            (files in the gold snapshot, junk excluded)
  * prompt_mentions_file_paths (does the prompt name any source file?)

Warnings (only for hard / frontier_hard unless noted):
  * root_cause_file_count < 2
  * hidden_test_count < 6
  * expected_changed_files_max <= 1 (or unset)
  * repo_file_count < 25

Prompt-fairness warnings (ANY difficulty) — a prompt should describe a
user-visible symptom, never the diagnosis or the fix:
  * prompt names one of the root-cause files
  * prompt contains a forbidden diagnostic term (lookahead, leakage, adapter,
    cache key, off-by-one, partial fix, ...) that points at the bug class
  * prompt names a root-cause function/symbol (derived from task_author_notes)
  * prompt is too short to describe user-visible behaviour

These are advisory: difficulty is not raised by a confusing prompt, and a
warning never invalidates a task. ``doctor`` owns validity; this owns the
"is the prompt an answer key?" question. The success threshold (held at 0.9 in
the scorer) is deliberately NOT the primary difficulty lever — coupled
multi-file defects and partial-fix-killing hidden cases are.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core.paths import is_junk_component
from ..manifests.loader import load_manifest
from ..manifests.schema import TaskManifest
from ..runners.prompt_builder import task_statement
from ..suites.loader import load_suite

HARD_DIFFICULTIES = {"hard", "frontier_hard"}
MIN_HIDDEN_CASES = 6
MIN_ROOT_CAUSE_FILES = 2
MIN_REPO_FILES = 25
MIN_PROMPT_WORDS = 20

# Root-cause / diagnostic vocabulary an agent-facing prompt must not contain.
# These name the bug class or the fix strategy rather than the user-visible
# symptom; their presence turns the prompt into a partial answer key. Phrases
# are matched whole and case-insensitively, with non-word/hyphen boundaries so
# "boundary bug" trips but a plain "day boundary" symptom does not.
FORBIDDEN_DIAGNOSTIC_TERMS = (
    "lookahead",
    "look-ahead",
    "leakage",
    "adapter",
    "cache key",
    "off-by-one",
    "off by one",
    "boundary",
    "warmup",
    "warm-up",
    "contract drift",
    "strict-positive",
    "strictly positive",
    "nested response",
    "partial fix",
    "partial payment",
    "partial payments",
    "credit memo",
    "double-count",
    "double count",
    "double-counting",
    "gross/net",
    "gross / net",
    "root cause",
    "root-cause",
    # V0.7 reorg/staged additions: these name a mechanism or fix locus.
    "rollback",
    "join bug",
    "parser state",
    "quoted trailing text",
    "half-away rounding",
    "tenant",
)

_FILE_PATH_RE = re.compile(r"[\w./\\-]+\.(?:py|js|ts|tsx|jsx|json|ya?ml|csv)\b")
_PY_TEST_RE = re.compile(r"def\s+test\w*\s*\(")
_JS_TEST_RE = re.compile(r"\btest\s*\(")
_JS_ASSERT_RE = re.compile(r"\bassert\.")

# Code-like identifiers (dotted member, camelCase, snake_case) used to lift the
# root-cause function/symbol names out of the private task_author_notes so we
# can check the public prompt never repeats them. Plain English words have none
# of these shapes, so this does not false-positive on prose.
_DOTTED_RE = re.compile(r"\b[A-Za-z_]\w*\.[A-Za-z_]\w+\b")
_CAMEL_RE = re.compile(r"\b[a-z][a-z0-9]*[A-Z]\w*\b")
_SNAKE_RE = re.compile(r"\b[a-z][a-z0-9]*_\w+\b")
_MIN_SYMBOL_LEN = 5


def _resolve_command_paths(command: str, base: Path) -> list[Path]:
    """Whitespace tokens of ``command`` that resolve to an existing path."""
    found: list[Path] = []
    for tok in command.replace("\\", "/").split():
        p = (base / tok).resolve()
        if p.exists():
            found.append(p)
    return found


def _iter_test_files(path: Path):
    if path.is_file():
        yield path
        return
    for p in path.rglob("*"):
        if not p.is_file():
            continue
        if any(is_junk_component(part) for part in p.relative_to(path).parts):
            continue
        if p.suffix in (".py", ".js"):
            yield p


def _count_cases(path: Path) -> int:
    total = 0
    for f in _iter_test_files(path):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if f.suffix == ".py":
            total += len(_PY_TEST_RE.findall(text))
        else:
            c = len(_JS_TEST_RE.findall(text))
            if c == 0:
                c = len(_JS_ASSERT_RE.findall(text))
            total += c
    return total


def _command_case_count(commands: list[str], base: Path) -> int:
    total = 0
    for cmd in commands:
        for p in _resolve_command_paths(cmd, base):
            total += _count_cases(p)
    return total


def _repo_file_count(root: Path) -> int:
    if not root.exists():
        return 0
    n = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(is_junk_component(part) for part in p.relative_to(root).parts):
            continue
        n += 1
    return n


def _prompt_file_mentions(prompt: str) -> list[str]:
    return _FILE_PATH_RE.findall(prompt)


def _forbidden_terms_in_prompt(prompt: str) -> list[str]:
    """Forbidden diagnostic terms present in ``prompt`` (case-insensitive)."""
    low = prompt.lower()
    hits: list[str] = []
    for term in FORBIDDEN_DIAGNOSTIC_TERMS:
        # Hyphen counts as part of a token so "boundary bug" matches but a bare
        # "boundary" symptom does not, and "adapter" does not match "adapters".
        pat = r"(?<![\w-])" + re.escape(term) + r"(?![\w-])"
        if re.search(pat, low):
            hits.append(term)
    return hits


def _root_cause_symbols(notes: str | None) -> list[str]:
    """Code-like identifiers (functions/symbols) named in author notes."""
    if not notes:
        return []
    found: set[str] = set()
    for rx in (_DOTTED_RE, _CAMEL_RE, _SNAKE_RE):
        for tok in rx.findall(notes):
            if len(tok) >= _MIN_SYMBOL_LEN:
                found.add(tok)
    return sorted(found)


def _symbols_leaked_in_prompt(prompt: str, notes: str | None) -> list[str]:
    """Root-cause symbols repeated verbatim in the (public) prompt."""
    return [s for s in _root_cause_symbols(notes) if s in prompt]


def audit_task(manifest: TaskManifest, base: Path) -> dict:
    difficulty = manifest.difficulty.value
    is_hard = difficulty in HARD_DIFFICULTIES

    hidden_count = _command_case_count(manifest.hidden_commands, base)
    visible_count = _command_case_count(manifest.visible_commands, base / manifest.gold_snapshot)
    root_cause_count = len(manifest.root_cause_files)
    repo_files = _repo_file_count(base / manifest.gold_snapshot)
    # The agent sees the issue-framed statement (or raw prompt); audit that, not
    # the boilerplate-wrapped full prompt (which contains forbidden_paths etc.).
    statement = task_statement(manifest)
    prompt_paths = _prompt_file_mentions(statement)
    cf_max = manifest.expected_changed_files_max
    forbidden_terms = _forbidden_terms_in_prompt(statement)
    leaked_symbols = _symbols_leaked_in_prompt(statement, manifest.task_author_notes)
    prompt_word_count = len(statement.split())

    warnings: list[str] = []

    # --- prompt fairness (any difficulty): symptom report, not an answer key ---
    # Prompt must not name a root-cause file.
    prompt_lc = statement.lower().replace("\\", "/")
    for rcf in manifest.root_cause_files:
        rcf_norm = rcf.replace("\\", "/").lower()
        base_name = rcf_norm.rsplit("/", 1)[-1]
        if rcf_norm in prompt_lc or base_name in prompt_lc:
            warnings.append(f"prompt names a root-cause file: {rcf}")
    # Prompt must not name the bug class or fix strategy.
    for term in forbidden_terms:
        warnings.append(f"prompt contains forbidden diagnostic term: '{term}'")
    # Prompt must not name a root-cause function/symbol.
    for sym in leaked_symbols:
        warnings.append(f"prompt names a root-cause symbol: '{sym}'")
    # Prompt must actually describe user-visible behaviour.
    if prompt_word_count < MIN_PROMPT_WORDS:
        warnings.append(
            f"prompt is too short ({prompt_word_count} words < {MIN_PROMPT_WORDS}) "
            f"to describe user-visible behaviour"
        )

    if is_hard:
        if root_cause_count < MIN_ROOT_CAUSE_FILES:
            warnings.append(
                f"root_cause_file_count={root_cause_count} < {MIN_ROOT_CAUSE_FILES} for {difficulty} task"
            )
        if hidden_count < MIN_HIDDEN_CASES:
            warnings.append(
                f"hidden_test_count={hidden_count} < {MIN_HIDDEN_CASES} for {difficulty} task"
            )
        if cf_max is None or cf_max <= 1:
            warnings.append(
                f"expected_changed_files_max={cf_max} <= 1 for {difficulty} task"
            )
        if repo_files < MIN_REPO_FILES:
            warnings.append(
                f"repo_file_count={repo_files} < {MIN_REPO_FILES}"
            )

    return {
        "task_id": manifest.task_id,
        "repo_id": manifest.repo_id,
        "difficulty": difficulty,
        "expected_changed_files_min": manifest.expected_changed_files_min,
        "expected_changed_files_max": cf_max,
        "hidden_test_count": hidden_count,
        "visible_test_count": visible_count,
        "root_cause_file_count": root_cause_count,
        "repo_file_count": repo_files,
        "prompt_word_count": prompt_word_count,
        "prompt_mentions_file_paths": bool(prompt_paths),
        "prompt_file_mentions": prompt_paths,
        "prompt_forbidden_terms": forbidden_terms,
        "prompt_leaked_symbols": leaked_symbols,
        "warnings": warnings,
    }


def audit_suite(suite_path: Path, base: Path) -> dict:
    suite = load_suite(Path(suite_path))
    tasks: list[dict] = []
    for task_rel in suite.tasks:
        manifest = load_manifest(base / task_rel)
        tasks.append(audit_task(manifest, base))
    warnings_total = sum(len(t["warnings"]) for t in tasks)
    return {
        "suite_id": suite.suite_id,
        "tasks_total": len(tasks),
        "warnings_total": warnings_total,
        "tasks": tasks,
    }
