"""Visible tests for datasette_export_hooks_stage_1.

These tests verify that the hook infrastructure exists and that existing
exports work without any hook registered.
"""
import pytest
from datasette.app import Datasette


def test_export_row_transform_hookspec_exists():
    """The export_row_transform hookspec is defined in datasette.hookspecs."""
    from datasette import hookspecs as hs
    assert hasattr(hs, "export_row_transform"), (
        "export_row_transform hookspec must be defined in datasette/hookspecs.py"
    )


@pytest.mark.asyncio
async def test_csv_export_unchanged_without_hook():
    """Existing CSV export still works when no hook is registered."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("exh1v1")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    await db.execute_write("INSERT INTO t VALUES (1, 'hello')")
    await db.execute_write("INSERT INTO t VALUES (2, 'world')")

    r = await ds.client.get("/exh1v1/t.csv?_size=max")
    assert r.status_code == 200
    assert "hello" in r.text
    assert "world" in r.text


@pytest.mark.asyncio
async def test_json_export_unchanged_without_hook():
    """Existing JSON export still works when no hook is registered."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("exh1v2")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    await db.execute_write("INSERT INTO t VALUES (1, 'alpha')")

    r = await ds.client.get("/exh1v2/t.json?_size=max")
    assert r.status_code == 200
    data = r.json()
    assert len(data["rows"]) == 1
