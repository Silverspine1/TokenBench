import json
from pathlib import Path

from tokenbench.core.workspace import copy_tree
from tokenbench.doctor.leakage import scan_broken_snapshot_leakage
from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
SRC_MANIFEST = ROOT / "benchmark/manifests/pulseboard-saas/pulseboard_contract_001.json"
REAL_BROKEN = ROOT / "benchmark/repos/pulseboard-saas/broken/pulseboard_contract_001"


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


def test_scanner_flags_intentional_bug_and_purpose(tmp_path):
    broken, _ = _leaky_task(
        tmp_path,
        "src/notes.js",
        "// intentional bug below\nconst x = 1; // wrong on purpose\n",
    )
    findings = scan_broken_snapshot_leakage(broken)
    patterns = {f["pattern"].lower() for f in findings if f["severity"] == "critical"}
    assert any("intentional" in p for p in patterns)
    assert any("on purpose" in p for p in patterns)


def test_doctor_rejects_intentional_bug(tmp_path):
    _, mpath = _leaky_task(tmp_path, "src/notes.js", "// intentional bug: returns raw shape\n")
    report = doctor_task(mpath, ROOT)
    assert report["status"] == "invalid"
    assert any("leaks the answer" in e for e in report["errors"])
