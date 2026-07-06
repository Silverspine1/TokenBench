import json
from pathlib import Path

from tokenbench.doctor.task_doctor import doctor_task

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def _manifest_with(tmp_path, **overrides):
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data.update(overrides)
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_prompt_mentioning_hidden_tests_is_rejected(tmp_path):
    p = _manifest_with(
        tmp_path,
        prompt="Fix the bug, then run the hidden tests to confirm it works.",
    )
    report = doctor_task(p, ROOT)
    assert report["status"] == "invalid"
    assert any("hidden test" in e for e in report["errors"])


def test_prompt_leaking_author_notes_is_rejected(tmp_path):
    secret = "Correct fix: return gross_pnl - fee - slippage."
    p = _manifest_with(
        tmp_path,
        prompt=f"Fix the backtester. {secret}",
        task_author_notes=secret,
    )
    report = doctor_task(p, ROOT)
    assert report["status"] == "invalid"
    assert any("task_author_notes" in e for e in report["errors"])


def test_hidden_test_inside_scored_path_is_rejected(tmp_path):
    # A hidden test under a scored (candidate-editable) path is a hard error:
    # the agent could tamper with it.
    p = _manifest_with(
        tmp_path,
        hidden_commands=["pytest -q marketlab/_hidden/test_secret.py"],
    )
    report = doctor_task(p, ROOT)
    assert report["status"] == "invalid"
    assert any("scored" in e for e in report["errors"])
