"""graphify treatment condition: build a graph into a workspace, prompt picks it up."""

import shutil
from pathlib import Path

from tokenbench.core.paths import is_junk_component
from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.graphify_build import build_graph
from tokenbench.runners.prompt_builder import build_prompt

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "benchmark/repos/logforge-cpp/broken/logforge_stats_minmax_001"
MANIFEST = ROOT / "benchmark/manifests/logforge-cpp/logforge_stats_minmax_001.json"


def test_graphify_out_is_junk():
    # Must never count as an agent edit in the candidate diff.
    assert is_junk_component("graphify-out")


def test_build_and_prompt_toggle(tmp_path):
    ws = tmp_path / "workspace"
    shutil.copytree(SNAPSHOT, ws)
    manifest = load_manifest(MANIFEST)

    # Control: no graph -> no block.
    assert "Knowledge graph:" not in build_prompt(manifest, ws)

    # Treatment: build graph -> block appears, free (AST-only) and on disk.
    stats = build_graph(ws)
    assert stats["nodes"] > 0
    assert (ws / "graphify-out" / "graph.json").exists()
    assert "Knowledge graph:" in build_prompt(manifest, ws)


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        test_graphify_out_is_junk()
        test_build_and_prompt_toggle(Path(d))
    print("ok")
