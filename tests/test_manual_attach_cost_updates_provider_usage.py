import json
from pathlib import Path

from tokenbench.manual.service import (
    attach_manual_cost,
    create_manual_run,
    run_status,
    submit_manual_run,
)


def _submit(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(base, demo_task["manifest"], condition_id="manual_generic_ide")
    run_dir = Path(rec["run_dir"])
    demo_task["edit_to_gold"](run_dir)
    submit_manual_run(base, run_dir)
    return run_dir


def test_attach_cost_updates_telemetry_provider_usage(demo_task):
    run_dir = _submit(demo_task)
    assert run_status(run_dir) == "cost_missing"

    out = attach_manual_cost(
        run_dir,
        {"cost_usd": 0.12, "input_tokens": 1000, "output_tokens": 500},
        source="provider_dashboard",
        confidence="medium",
        notes="from dashboard",
    )
    pu = out["provider_usage"]
    assert pu["available"] is True
    assert pu["cost_usd"] == 0.12
    assert pu["input_tokens"] == 1000
    assert pu["total_tokens"] == 1500

    # Persisted to telemetry.json and manual_cost.json.
    tel = json.loads((run_dir / "telemetry.json").read_text(encoding="utf-8"))
    assert tel["provider_usage"]["cost_usd"] == 0.12
    mc = json.loads((run_dir / "manual_cost.json").read_text(encoding="utf-8"))
    assert mc["source"] == "provider_dashboard"
    assert mc["confidence"] == "medium"

    assert run_status(run_dir) == "complete"


def test_attach_cost_rejects_unknown_source(demo_task):
    run_dir = _submit(demo_task)
    try:
        attach_manual_cost(run_dir, {"cost_usd": 1.0}, source="made_up")
        assert False, "expected ValueError"
    except ValueError:
        pass
