import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from tokenbench.ui.app import create_app  # noqa: E402


@pytest.fixture
def client(demo_task):
    app = create_app(demo_task["base"])
    return TestClient(app), demo_task


def test_suites_and_tasks_list(client):
    c, demo = client
    suites = c.get("/suites").json()
    assert any(s["suite_id"] == "demo" for s in suites)

    tasks = c.get("/suites/demo/tasks").json()
    assert tasks and tasks[0]["task_id"] == "demo_fix_001"
    assert tasks[0]["status"] == "not_started"


def test_unknown_suite_404(client):
    c, _ = client
    assert c.get("/suites/nope/tasks").status_code == 404


def test_full_manual_flow_and_no_private_leak(client):
    c, demo = client
    token = demo["private_token"]

    start = c.post(
        "/runs/manual/start",
        json={"task_rel": demo["task_rel"], "condition_id": "manual_generic_ide"},
    )
    assert start.status_code == 200, start.text
    run_id = start.json()["run_id"]
    assert token not in start.text

    # Prompt + run detail must not leak the private token or hidden command.
    prompt = c.get(f"/runs/{run_id}/prompt")
    assert token not in prompt.text and "sys.exit" not in prompt.text

    detail = c.get(f"/runs/{run_id}").json()
    assert "hidden_commands" not in detail["public"]
    assert token not in c.get(f"/runs/{run_id}").text

    # HTML pages must not leak either.
    for path in (f"/console/{run_id}", f"/result/{run_id}", "/", "/queue/demo"):
        page = c.get(path)
        assert page.status_code == 200
        assert token not in page.text

    # Submit + score through the API.
    submit = c.post(f"/runs/{run_id}/submit")
    assert submit.status_code == 200, submit.text
    assert "score" not in submit.text or token not in submit.text

    results = c.get("/results").json()
    assert any(r["run_id"] == run_id for r in results)

    # Attach cost via API.
    cost = c.post(
        f"/runs/{run_id}/cost",
        json={"cost_usd": 0.05, "source": "manual_estimate", "confidence": "low"},
    )
    assert cost.status_code == 200
    assert cost.json()["provider_usage"]["cost_usd"] == 0.05
