from pathlib import Path

from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.prompt_builder import build_prompt

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_prompt_includes_task_metadata():
    manifest = load_manifest(MARKETLAB)
    prompt = build_prompt(manifest, Path("/tmp/ws"))
    assert manifest.prompt in prompt
    assert manifest.repo_id in prompt
    assert manifest.task_id in prompt
    assert manifest.category.value in prompt
    assert manifest.difficulty.value in prompt
    assert str(manifest.allowed_runtime_seconds) in prompt
    assert manifest.dependency_policy.value in prompt
    assert "/tmp/ws" in prompt.replace("\\", "/")


def test_prompt_includes_visible_but_not_hidden_commands():
    manifest = load_manifest(MARKETLAB)
    prompt = build_prompt(manifest, Path("/tmp/ws"))
    for cmd in manifest.visible_commands:
        assert cmd in prompt
    # Hidden commands must never leak into the agent prompt.
    for cmd in manifest.hidden_commands:
        assert cmd not in prompt


def test_prompt_lists_forbidden_paths():
    manifest = load_manifest(MARKETLAB)
    prompt = build_prompt(manifest, Path("/tmp/ws"))
    for fp in manifest.forbidden_paths:
        assert fp in prompt
