"""Prompt builder renders expected_behavior and never leaks hidden commands."""

from __future__ import annotations

from pathlib import Path

from tokenbench.manifests.schema import TaskManifest
from tokenbench.runners.prompt_builder import build_prompt, task_statement


def _m(**extra) -> TaskManifest:
    data = {
        "task_id": "t", "repo_id": "r", "mode": "atomic", "category": "reorg",
        "difficulty": "medium", "prompt": "Body text.", "issue_title": "Hard to maintain",
        "broken_snapshot": "b", "gold_snapshot": "g",
        "hidden_commands": ["pytest secret_hidden_suite.py"],
        "allowed_runtime_seconds": 60, "forbidden_paths": [],
        "expected_behavior": ["report totals unchanged", "import entrypoint still works"],
    }
    data.update(extra)
    return TaskManifest.model_validate(data)


def test_expected_block_rendered():
    s = task_statement(_m())
    assert "Issue: Hard to maintain" in s
    assert "Expected:" in s
    assert "- report totals unchanged" in s


def test_empty_expected_behavior_omits_block():
    s = task_statement(_m(expected_behavior=[]))
    assert "Expected:" not in s


def test_hidden_command_not_in_prompt():
    p = build_prompt(_m(), Path("/tmp/ws"))
    assert "secret_hidden_suite" not in p
