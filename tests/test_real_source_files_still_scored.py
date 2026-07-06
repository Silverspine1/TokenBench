from pathlib import Path

from tokenbench.core.artifacts import compute_file_changes
from tokenbench.core.paths import is_junk_path
from tokenbench.manifests.loader import load_manifest

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"

# Real source paths that must NEVER be treated as generated junk.
REAL_SOURCE = [
    "marketlab/backtest.py",
    "marketlab/split.py",
    "src/export.js",
    "src/pagination.js",
    "configs/model.yaml",
    "package.json",
    "pyproject.toml",
    # Files whose names merely resemble junk dir names must still count.
    "coverage.py",
    "build.js",
    "dist_helper.py",
]


def _make_tree(base: Path, files: dict[str, str]):
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def test_real_source_paths_not_junk():
    for rel in REAL_SOURCE:
        assert not is_junk_path(rel), f"{rel} wrongly flagged as junk"


def test_generated_dirs_are_junk():
    assert is_junk_path("marketlab_ml.egg-info/PKG-INFO")
    assert is_junk_path("marketlab/__pycache__/x.pyc")
    assert is_junk_path(".pytest_cache/CACHEDIR.TAG")
    assert is_junk_path("node_modules/lib/index.js")
    assert is_junk_path("coverage/index.html")
    assert is_junk_path("build/out.o")
    # Windows-style separators handled too.
    assert is_junk_path("marketlab\\__pycache__\\x.pyc")


def test_real_source_edit_still_modified_and_scored(tmp_path):
    manifest = load_manifest(MARKETLAB)
    broken = tmp_path / "broken"
    candidate = tmp_path / "candidate"
    _make_tree(broken, {"marketlab/backtest.py": "old\n"})
    _make_tree(
        candidate,
        {
            "marketlab/backtest.py": "new\n",
            "marketlab_ml.egg-info/PKG-INFO": "noise\n",
        },
    )
    changes = compute_file_changes(broken, candidate, manifest)
    assert "marketlab/backtest.py" in changes["modified"]
    assert "marketlab/backtest.py" in changes["scored_modified"]
