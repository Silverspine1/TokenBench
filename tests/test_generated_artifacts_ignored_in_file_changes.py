from pathlib import Path

from tokenbench.core.artifacts import compute_file_changes
from tokenbench.manifests.loader import load_manifest

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def _make_tree(base: Path, files: dict[str, str]):
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def test_egg_info_and_caches_excluded_from_file_changes(tmp_path):
    manifest = load_manifest(MARKETLAB)
    broken = tmp_path / "broken"
    candidate = tmp_path / "candidate"
    _make_tree(broken, {"marketlab/backtest.py": "old\n"})
    # Candidate edits the real file and leaves behind generated packaging/cache noise.
    _make_tree(
        candidate,
        {
            "marketlab/backtest.py": "new\n",
            "marketlab_ml.egg-info/PKG-INFO": "Metadata-Version: 2.4\n",
            "marketlab_ml.egg-info/SOURCES.txt": "marketlab/backtest.py\n",
            "marketlab_ml.egg-info/dependency_links.txt": "\n",
            "marketlab_ml.egg-info/top_level.txt": "marketlab\n",
            "marketlab/__pycache__/backtest.cpython-313.pyc": "bytecode\n",
            ".pytest_cache/CACHEDIR.TAG": "tag\n",
            "coverage/index.html": "<html>\n",
        },
    )

    changes = compute_file_changes(broken, candidate, manifest)

    # Only the real source edit survives.
    assert changes["modified"] == ["marketlab/backtest.py"]
    assert changes["added"] == []
    assert changes["deleted"] == []
    assert changes["scored_modified"] == ["marketlab/backtest.py"]

    flat = changes["added"] + changes["modified"] + changes["deleted"]
    assert not any("egg-info" in p for p in flat)
    assert not any("__pycache__" in p for p in flat)
    assert not any(p.startswith(".pytest_cache") for p in flat)
    assert not any(p.startswith("coverage/") for p in flat)
