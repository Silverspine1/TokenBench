import json
from pathlib import Path

from tokenbench.core.workspace import copy_tree
from tokenbench.doctor.leakage import scan_broken_snapshot_leakage
from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
SRC_MANIFEST = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"
REAL_BROKEN = ROOT / "benchmark/repos/marketlab-ml/broken/marketlab_fee_slippage_001"


def _leaky_task(tmp_path, rel_name, content):
    broken = tmp_path / "broken"
    copy_tree(REAL_BROKEN, broken)
    leak = broken / rel_name
    leak.parent.mkdir(parents=True, exist_ok=True)
    leak.write_text(content, encoding="utf-8")

    data = json.loads(SRC_MANIFEST.read_text(encoding="utf-8"))
    data["broken_snapshot"] = str(broken)
    mpath = tmp_path / "m.json"
    mpath.write_text(json.dumps(data), encoding="utf-8")
    return broken, mpath


def test_scanner_flags_hidden_test_reference(tmp_path):
    # A README that names the hidden test confesses the existence/shape of it.
    broken, _ = _leaky_task(
        tmp_path,
        "README.md",
        "# notes\n\nThe hidden test asserts the fee is charged once.\n",
    )
    findings = scan_broken_snapshot_leakage(broken)
    assert any(f["pattern"].lower() == "hidden test" for f in findings)


def test_doctor_rejects_hidden_test_reference(tmp_path):
    _, mpath = _leaky_task(tmp_path, "README.md", "The hidden test checks the exit fee.\n")
    report = doctor_task(mpath, ROOT)
    assert report["status"] == "invalid"
    assert any("leaks the answer" in e for e in report["errors"])
