import json
from pathlib import Path

from tokenbench.manual.service import create_manual_run, submit_manual_run


def test_submit_runs_hidden_tests_and_scores(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(base, demo_task["manifest"], condition_id="manual_generic_ide")
    run_dir = Path(rec["run_dir"])
    demo_task["edit_to_gold"](run_dir)

    report = submit_manual_run(base, run_dir)

    # score.json + telemetry.json written through the same path a CLI run uses.
    assert (run_dir / "score.json").exists()
    assert (run_dir / "telemetry.json").exists()

    # Hidden tests actually executed (one command, passing).
    assert report["hidden"]["commands_total"] >= 1
    assert report["hidden_tests"]["tests_total"] >= 1
    assert report["hidden_tests"]["pass_rate"] == 1.0
    assert report["success"] is True


def test_hidden_logs_written(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(base, demo_task["manifest"], condition_id="manual_generic_ide")
    run_dir = Path(rec["run_dir"])
    submit_manual_run(base, run_dir)
    score = json.loads((run_dir / "score.json").read_text(encoding="utf-8"))
    assert "hidden_tests" in score
    assert (run_dir / "logs" / "hidden_tests.stdout.log").exists()
