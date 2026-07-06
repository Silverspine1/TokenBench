from pathlib import Path

from tokenbench.manual.service import create_manual_run, submit_manual_run


def test_submit_freezes_workspace_into_candidate(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(base, demo_task["manifest"], condition_id="manual_generic_ide")
    run_dir = Path(rec["run_dir"])

    demo_task["edit_to_gold"](run_dir)
    submit_manual_run(base, run_dir)

    candidate_app = run_dir / "candidate" / "demo" / "app.py"
    assert candidate_app.exists()
    assert "a + b" in candidate_app.read_text(encoding="utf-8")
    assert (run_dir / "file_changes.json").exists()
    assert (run_dir / "patch.diff").exists()
    assert (run_dir / "run_state.json").exists()


def test_submit_records_submitted_at(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(base, demo_task["manifest"], condition_id="manual_generic_ide")
    run_dir = Path(rec["run_dir"])
    submit_manual_run(base, run_dir)
    import json

    record = json.loads((run_dir / "manual_ide.json").read_text(encoding="utf-8"))
    assert record["submitted_at"] is not None
