"""Visible tests for datasette_export_hooks_stage_2: batch hook.

These tests verify that the Stage 1 single-row hook still works
and that the batch hook infrastructure is in place.
"""
import pytest
from datasette.app import Datasette
from datasette import hookimpl


def test_export_rows_transform_hookspec_exists():
    """The export_rows_transform hookspec is defined in datasette.hookspecs."""
    from datasette import hookspecs as hs
    assert hasattr(hs, "export_rows_transform"), (
        "export_rows_transform hookspec must be defined in datasette/hookspecs.py"
    )


@pytest.mark.asyncio
async def test_stage1_single_row_hook_still_works():
    """Stage 1 export_row_transform hook still applies after Stage 2 additions."""
    class SingleRowPlugin:
        @hookimpl
        def export_row_transform(self, database, table, row, export_format):
            new_row = dict(row)
            new_row["v"] = new_row["v"].upper()
            return new_row

    ds = Datasette(memory=True)
    plugin = SingleRowPlugin()
    ds.pm.register(plugin, name="stage2v_single")
    try:
        db = ds.add_memory_database("exh2v1")
        await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        await db.execute_write("INSERT INTO t VALUES (1, 'hello')")

        r = await ds.client.get("/exh2v1/t.csv?_size=max")
        assert r.status_code == 200
        assert "HELLO" in r.text, "Stage 1 hook should still uppercase values"
    finally:
        ds.pm.unregister(plugin, name="stage2v_single")


@pytest.mark.asyncio
async def test_no_hook_export_unchanged():
    """Export output is unchanged when no hook is registered."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("exh2v2")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    await db.execute_write("INSERT INTO t VALUES (1, 'untouched')")

    r = await ds.client.get("/exh2v2/t.csv?_size=max")
    assert r.status_code == 200
    assert "untouched" in r.text
