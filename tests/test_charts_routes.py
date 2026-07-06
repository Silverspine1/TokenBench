import pytest

pytest.importorskip("fastapi")
from pathlib import Path  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from tokenbench.manual.service import (  # noqa: E402
    attach_manual_cost,
    create_manual_run,
    submit_manual_run,
)
from tokenbench.ui.app import create_app  # noqa: E402


def _client_with_data(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(base, demo_task["manifest"], condition_id="manual_generic_ide")
    run_dir = Path(rec["run_dir"])
    demo_task["edit_to_gold"](run_dir)
    submit_manual_run(base, run_dir)
    attach_manual_cost(run_dir, {"cost_usd": 0.1, "total_tokens": 1234}, source="manual_estimate")
    app = create_app(base, db_path=base / "tokenbench.db")
    c = TestClient(app)
    c.post("/db/rebuild")
    return c


def test_chart_options_and_data(demo_task):
    c = _client_with_data(demo_task)

    opts = c.get("/charts/options").json()
    assert any(m["key"] == "total_tokens" for m in opts["metrics"])
    assert "manual_generic_ide" in opts["conditions"]

    data = c.get("/charts/data", params={"metric": "total_tokens", "mode": "cumulative"}).json()
    assert data["metric"] == "total_tokens"
    assert data["series"]
    assert data["series"][0]["points"][0]["value"] == 1234


def test_chart_data_rejects_bad_metric(demo_task):
    c = _client_with_data(demo_task)
    assert c.get("/charts/data", params={"metric": "nope"}).status_code == 400


def test_charts_page_renders(demo_task):
    c = _client_with_data(demo_task)
    page = c.get("/charts")
    assert page.status_code == 200
    assert "Chart builder" in page.text
    assert "charts.js" in page.text
