from pathlib import Path

from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.prompt_builder import build_prompt

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_prompt_has_no_meta_leaky_wording():
    manifest = load_manifest(MARKETLAB)
    low = build_prompt(manifest, Path("/tmp/ws")).lower()
    for bad in (
        "hidden test",
        "hidden command",
        "benchmark repo",
        "benchmark metadata",
        "run externally",
        "accepted_solutions",
        "benchmark/tests",
    ):
        assert bad not in low, f"prompt leaks meta wording: {bad!r}"


def test_prompt_still_describes_the_task():
    manifest = load_manifest(MARKETLAB)
    prompt = build_prompt(manifest, Path("/tmp/ws"))
    assert manifest.prompt in prompt
    assert "Additional checks will be run after submission." in prompt
