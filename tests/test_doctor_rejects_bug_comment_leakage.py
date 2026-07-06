import json
from pathlib import Path

from tokenbench.core.workspace import copy_tree
from tokenbench.doctor.leakage import scan_broken_snapshot_leakage
from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
SRC_MANIFEST = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"
REAL_BROKEN = ROOT / "benchmark/repos/marketlab-ml/broken/marketlab_fee_slippage_001"


def _leaky_task(tmp_path, rel_name, content):
    """Clone the real broken snapshot, inject one leaky file, point a manifest at it."""
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


def test_scanner_flags_bug_comment(tmp_path):
    broken, _ = _leaky_task(tmp_path, "marketlab/extra.py", "# BUG: fee applied twice\n")
    findings = scan_broken_snapshot_leakage(broken)
    assert any(f["severity"] == "critical" and f["pattern"].upper() == "BUG" for f in findings)


def test_doctor_rejects_bug_comment(tmp_path):
    _, mpath = _leaky_task(tmp_path, "marketlab/extra.py", "# BUG: applies the fee twice\n")
    report = doctor_task(mpath, ROOT)
    assert report["status"] == "invalid"
    assert any("leaks the answer" in e for e in report["errors"])
    assert report["leakage_findings"]
