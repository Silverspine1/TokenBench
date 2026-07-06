import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from tokenbench.manual.service import create_manual_run, submit_manual_run  # noqa: E402
from tokenbench.ui.app import create_app  # noqa: E402


@pytest.fixture
def client_with_run(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(base, demo_task["manifest"], condition_id="manual_generic_ide")
    from pathlib import Path

    run_dir = Path(rec["run_dir"])
    demo_task["edit_to_gold"](run_dir)
    submit_manual_run(base, run_dir)
    app = create_app(base, db_path=base / "tokenbench.db")
    return TestClient(app), rec["run_id"]


def test_db_browse_edit_delete(client_with_run):
    c, run_id = client_with_run

    # Build the DB from runs/.
    rebuild = c.post("/db/rebuild").json()
    assert rebuild["runs"] == 1

    tables = c.get("/db/tables").json()
    assert {"name": "runs", "count": 1} in [{"name": t["name"], "count": t["count"]} for t in tables]

    rows = c.get("/db/runs").json()
    assert rows["rows"][0]["run_id"] == run_id
    assert "task_id" in rows["columns"]

    # Edit a field.
    upd = c.post("/db/update", json={
        "table": "runs", "run_id": run_id, "updates": {"task_id": "EDITED"},
    })
    assert upd.json()["changed"] == 1
    assert c.get("/db/runs").json()["rows"][0]["task_id"] == "EDITED"

    # Delete the row.
    dele = c.post("/db/delete", json={"table": "runs", "run_id": run_id})
    assert dele.json()["deleted"] == 1
    assert c.get("/db/runs").json()["rows"] == []


def test_db_rejects_unknown_table(client_with_run):
    c, _ = client_with_run
    c.post("/db/rebuild")
    assert c.get("/db/sqlite_master").status_code == 404
    bad = c.post("/db/update", json={"table": "evil", "run_id": "x", "updates": {"a": 1}})
    assert bad.status_code == 400


def test_database_page_renders(client_with_run):
    c, _ = client_with_run
    page = c.get("/database")
    assert page.status_code == 200
    assert "Results database" in page.text
