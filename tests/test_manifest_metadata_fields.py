from pathlib import Path

from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.prompt_builder import build_prompt

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_optional_metadata_fields_parse():
    m = load_manifest(MANIFEST)
    assert m.expected_failure_summary
    assert "fee accounting" in m.skills_tested
    assert m.root_cause_files == ["marketlab/backtest.py"]
    assert m.expected_changed_files_min == 1
    assert m.expected_changed_files_max == 1
    assert m.task_author_notes


def test_metadata_defaults_when_absent():
    # A manifest without the optional fields still loads with safe defaults.
    import json

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in (
        "expected_failure_summary",
        "skills_tested",
        "root_cause_files",
        "expected_changed_files_min",
        "expected_changed_files_max",
        "task_author_notes",
    ):
        data.pop(key, None)
    from tokenbench.manifests.schema import TaskManifest

    m = TaskManifest.model_validate(data)
    assert m.expected_failure_summary == ""
    assert m.skills_tested == []
    assert m.task_author_notes == ""


def test_prompt_never_leaks_private_metadata_or_hidden_commands():
    m = load_manifest(MANIFEST)
    prompt = build_prompt(m, ROOT / "workspace")
    assert m.task_author_notes not in prompt
    assert m.expected_failure_summary not in prompt
    # The hidden test *commands* themselves must never appear in the prompt.
    # (The wrapper may state that hidden tests run externally; that is not a leak.)
    for cmd in m.hidden_commands:
        assert cmd not in prompt
