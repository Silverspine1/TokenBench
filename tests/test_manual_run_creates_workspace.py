from pathlib import Path

from tokenbench.manual.service import create_manual_run, run_status


def test_create_materializes_workspace_and_prompt(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(
        base, demo_task["manifest"], condition_id="manual_generic_ide", ide_name="Cursor"
    )
    run_dir = Path(rec["run_dir"])

    assert (run_dir / "workspace" / "demo" / "app.py").exists()
    assert (run_dir / "task_manifest.json").exists()
    assert (run_dir / "prompt.txt").exists()
    assert (run_dir / "manual_ide.json").exists()
    assert rec["prompt"]
    assert run_status(run_dir) == "workspace_created"


def test_manual_ide_record_fields(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(
        base, demo_task["manifest"], condition_id="manual_generic_ide",
        ide_name="Windsurf", model_name="claude-opus-4-8",
    )
    m = rec["manual_ide"]
    assert m["condition_id"] == "manual_generic_ide"
    assert m["ide_name"] == "Windsurf"
    assert m["model_name"] == "claude-opus-4-8"
    assert m["candidate_source"] == "workspace"
    assert m["submitted_at"] is None
