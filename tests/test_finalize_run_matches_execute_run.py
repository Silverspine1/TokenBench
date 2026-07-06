"""Guard: the manual submit path scores identically to cli.execute_run.

Both go through ``finalize_run``; starting from the same broken snapshot with no
edits, the deterministic quality/test components must match exactly (timing-based
efficiency may differ by wall-clock, so it is not compared).
"""

from pathlib import Path

from tokenbench.cli import execute_run
from tokenbench.manual.service import create_manual_run, submit_manual_run
from tokenbench.runners.manual import ManualRunner


def test_manual_submit_matches_execute_run_scoring(demo_task):
    base = demo_task["base"]
    manifest = demo_task["manifest"]

    cli_report = execute_run(
        manifest, base, ManualRunner(skip_agent=True),
        condition_id="cli", trial_index=0, overwrite=False, quiet=True,
    )

    rec = create_manual_run(base, manifest, condition_id="manual_generic_ide")
    manual_report = submit_manual_run(base, Path(rec["run_dir"]))

    assert manual_report["quality_score"] == cli_report["quality_score"]
    assert manual_report["hidden_tests"]["pass_rate"] == cli_report["hidden_tests"]["pass_rate"]
    assert manual_report["visible_tests"]["pass_rate"] == cli_report["visible_tests"]["pass_rate"]
    assert manual_report["success"] == cli_report["success"]
    assert manual_report["runner"] == "manual-ide"
