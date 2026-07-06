import glob
from pathlib import Path

from tokenbench.core.workspace import copy_tree
from tokenbench.manifests.loader import load_manifest
from tokenbench.scoring.tests import run_visible_tests

ROOT = Path(__file__).resolve().parents[1]


def _manifests():
    return [load_manifest(Path(f)) for f in glob.glob(str(ROOT / "benchmark/manifests/*/*.json"))]


def test_visible_commands_do_not_reference_benchmark_tree():
    for m in _manifests():
        assert m.visible_commands, f"{m.task_id} has no visible commands"
        for cmd in m.visible_commands:
            norm = cmd.replace("\\", "/")
            assert "benchmark/" not in norm, f"{m.task_id}: visible cmd references benchmark tree"
            assert "tests_visible" in norm, f"{m.task_id}: visible cmd not under tests_visible"


def _run_gold(tmp_path, manifest):
    gold = ROOT / manifest.gold_snapshot
    ws = tmp_path / "workspace"
    copy_tree(gold, ws)
    logs = tmp_path / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return run_visible_tests(manifest, ROOT, ws, tmp_path, logs / "v.out", logs / "v.err")


def test_python_visible_command_runs_from_workspace(tmp_path):
    m = load_manifest(ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json")
    results = _run_gold(tmp_path, m)
    assert results and all(r.passed for r in results)


def test_node_visible_command_runs_from_workspace(tmp_path):
    m = load_manifest(ROOT / "benchmark/manifests/pulseboard-saas/pulseboard_summary_001.json")
    results = _run_gold(tmp_path, m)
    assert results and all(r.passed for r in results)
