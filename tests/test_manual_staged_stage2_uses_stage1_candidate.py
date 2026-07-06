from pathlib import Path

from tokenbench.manual.service import create_manual_run, submit_manual_run
from tokenbench.manual.staged import create_stage2_manual, finalize_staged_group


def _stage_manifests(base_manifest):
    stage1 = base_manifest.model_copy(
        update={"task_id": "demo_stage_1", "stage": 1, "stage_group_id": "demo_group"}
    )
    stage2 = base_manifest.model_copy(
        update={"task_id": "demo_stage_2", "stage": 2, "stage_group_id": "demo_group"}
    )
    return stage1, stage2


def test_stage2_workspace_is_stage1_candidate(demo_task):
    base = demo_task["base"]
    stage1, stage2 = _stage_manifests(demo_task["manifest"])

    # Stage 1: operator applies the fix, submit.
    rec1 = create_manual_run(base, stage1, condition_id="manual_generic_ide")
    run1 = Path(rec1["run_dir"])
    demo_task["edit_to_gold"](run1)
    # Leave a stage-1 marker so we can prove carryover of the actual candidate.
    (run1 / "workspace" / "demo" / "stage1_marker.py").write_text("# s1\n", encoding="utf-8")
    submit_manual_run(base, run1)

    stage1_candidate_app = (run1 / "candidate" / "demo" / "app.py").read_text(encoding="utf-8")

    # Stage 2 created from Stage 1's candidate (not gold, not broken).
    rec2 = create_stage2_manual(base, run1, stage2)
    run2 = Path(rec2["run_dir"])

    ws2_app = run2 / "workspace" / "demo" / "app.py"
    assert ws2_app.read_text(encoding="utf-8") == stage1_candidate_app
    assert (run2 / "workspace" / "demo" / "stage1_marker.py").exists()

    import json

    record2 = json.loads((run2 / "manual_ide.json").read_text(encoding="utf-8"))
    assert record2["stage"] == 2
    assert record2["previous_run_id"] == rec1["run_id"]


def test_finalize_staged_group_writes_staged_score(demo_task):
    base = demo_task["base"]
    stage1, stage2 = _stage_manifests(demo_task["manifest"])

    rec1 = create_manual_run(base, stage1, condition_id="manual_generic_ide")
    run1 = Path(rec1["run_dir"])
    demo_task["edit_to_gold"](run1)
    submit_manual_run(base, run1)

    rec2 = create_stage2_manual(base, run1, stage2)
    run2 = Path(rec2["run_dir"])
    submit_manual_run(base, run2)

    report = finalize_staged_group(run1, run2)
    assert (run2 / "staged_score.json").exists()
    assert report["stage_group_id"] == "demo_group"
    assert "staged_score" in report["staged"]
    assert report["stage2"]["previous_run_id"] == rec1["run_id"]
