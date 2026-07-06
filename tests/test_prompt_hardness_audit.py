"""Prompt-fairness signals of the hardness audit (V0.5.1, Phase 6).

A hard prompt must read as a user-visible symptom report, never as an answer
key: no forbidden diagnostic vocabulary, no root-cause symbol names, and long
enough to actually describe the behaviour.
"""

from pathlib import Path

from tokenbench.doctor.hardness import (
    audit_suite,
    _forbidden_terms_in_prompt,
    _symbols_leaked_in_prompt,
)

ROOT = Path(__file__).resolve().parents[1]
HARD_SUITE = ROOT / "benchmark/suites/v0_5_hard.json"


def test_forbidden_terms_flagged_with_word_boundaries():
    assert "adapter" in _forbidden_terms_in_prompt("fix the adapter")
    assert "cache key" in _forbidden_terms_in_prompt("the cache key is wrong")
    assert "lookahead" in _forbidden_terms_in_prompt("this has lookahead in it")
    assert "boundary" in _forbidden_terms_in_prompt("a day boundary problem")
    assert "credit memo" in _forbidden_terms_in_prompt("handle a credit memo here")
    # A clean symptom with none of the diagnostic vocabulary stays empty.
    assert _forbidden_terms_in_prompt("invoices near the end of the day") == []
    # "adapter" must not match inside another word.
    assert _forbidden_terms_in_prompt("adapters are fine to mention") == []


def test_root_cause_symbol_leak_detected():
    notes = "adaptInvoices must normalize; schema.normalizeInvoice reads amount.cents"
    assert _symbols_leaked_in_prompt("call adaptInvoices then done", notes) == [
        "adaptInvoices"
    ]
    # Prose that merely shares an English word must not be read as a symbol leak.
    assert _symbols_leaked_in_prompt("read the invoice amount in cents", notes) == []
    assert _symbols_leaked_in_prompt("anything", None) == []


def test_hard_suite_prompts_are_symptom_reports():
    report = audit_suite(HARD_SUITE, ROOT)
    for t in report["tasks"]:
        assert t["prompt_forbidden_terms"] == [], (
            t["task_id"],
            t["prompt_forbidden_terms"],
        )
        assert t["prompt_leaked_symbols"] == [], (
            t["task_id"],
            t["prompt_leaked_symbols"],
        )
        assert t["prompt_word_count"] >= 20, (t["task_id"], t["prompt_word_count"])
