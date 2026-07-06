import json
from pathlib import Path

from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
SRC_MANIFEST = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def _manifest_with(tmp_path, **overrides):
    data = json.loads(SRC_MANIFEST.read_text(encoding="utf-8"))
    data.update(overrides)
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_missing_visible_path_is_hard_error(tmp_path):
    # Point the visible command at a directory that does not exist in the
    # workspace: pytest reports "file or directory not found" -> hard error.
    p = _manifest_with(tmp_path, visible_commands=["pytest -q tests_visible_does_not_exist"])
    report = doctor_task(p, ROOT)
    assert report["status"] == "invalid"
    assert any("not runnable" in e for e in report["errors"])


def test_real_task_visible_command_is_runnable():
    # The shipped task's visible command must NOT trip the missing-path check.
    report = doctor_task(SRC_MANIFEST, ROOT)
    assert report["status"] == "valid"
    assert not any("not runnable" in e for e in report["errors"])
