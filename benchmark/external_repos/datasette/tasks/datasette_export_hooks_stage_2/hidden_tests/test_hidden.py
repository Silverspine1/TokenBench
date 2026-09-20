"""Hidden tests for datasette_export_hooks_stage_2: batch export_rows_transform.

These tests verify:
1. export_rows_transform receives a list and returns a list.
2. Batch hook is preferred over single-row hook when both are on the same plugin.
3. Single-row hook still works when no batch hook.
4. No-hook behavior unchanged.

Plugins are registered through ds.pm and always unregistered in a finally block.
"""
import pytest
from datasette.app import Datasette
from datasette import hookimpl


class BatchRedactPlugin:
    @hookimpl
    def export_rows_transform(self, database, table, rows, export_format):
        result = []
        for row in rows:
            new_row = dict(row)
            if "secret" in new_row:
                new_row["secret"] = "***"
            result.append(new_row)
        return result


@pytest.mark.asyncio
async def test_batch_hook_transforms_rows():
    """export_rows_transform receives list and its returned list is used."""
    ds = Datasette(memory=True)
    plugin = BatchRedactPlugin()
    ds.pm.register(plugin, name="batch_redact")
    try:
        db = ds.add_memory_database("exh2a")
        await db.execute_write(
            "CREATE TABLE t (id INTEGER PRIMARY KEY, secret TEXT, pub TEXT)"
        )
        await db.execute_write("INSERT INTO t VALUES (1, 'supersecret', 'public')")
        await db.execute_write("INSERT INTO t VALUES (2, 'topsecret', 'open')")

        r = await ds.client.get("/exh2a/t.csv?_size=max")
        assert r.status_code == 200
        assert "***" in r.text, "Batch hook should redact secrets"
        assert "supersecret" not in r.text
        assert "public" in r.text
    finally:
        ds.pm.unregister(plugin, name="batch_redact")


@pytest.mark.asyncio
async def test_batch_hook_receives_list_argument():
    """export_rows_transform receives a list, not a single row."""
    captured = []

    class CaptureBatch:
        @hookimpl
        def export_rows_transform(self, database, table, rows, export_format):
            captured.append({"type": type(rows).__name__, "len": len(rows)})
            return rows

    ds = Datasette(memory=True)
    plugin = CaptureBatch()
    ds.pm.register(plugin, name="capture_batch")
    try:
        db = ds.add_memory_database("exh2b")
        await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        for i in range(3):
            await db.execute_write("INSERT INTO t VALUES (?, ?)", [i + 1, f"v{i+1}"])

        await ds.client.get("/exh2b/t.csv?_size=max")
        assert captured, "Batch hook should have been called"
        assert captured[0]["type"] == "list", f"Expected list, got {captured[0]['type']}"
        assert captured[0]["len"] == 3, f"Expected 3 rows in batch, got {captured[0]['len']}"
    finally:
        ds.pm.unregister(plugin, name="capture_batch")


@pytest.mark.asyncio
async def test_batch_preferred_over_single_same_plugin():
    """A plugin implementing both hooks uses the batch hook, not the single hook."""
    calls = {"single": 0, "batch": 0}

    class BothHooks:
        @hookimpl
        def export_row_transform(self, database, table, row, export_format):
            calls["single"] += 1
            return row

        @hookimpl
        def export_rows_transform(self, database, table, rows, export_format):
            calls["batch"] += 1
            return rows

    ds = Datasette(memory=True)
    plugin = BothHooks()
    ds.pm.register(plugin, name="both_hooks")
    try:
        db = ds.add_memory_database("exh2c")
        await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        for i in range(4):
            await db.execute_write("INSERT INTO t VALUES (?, ?)", [i + 1, f"v{i+1}"])

        await ds.client.get("/exh2c/t.csv?_size=max")
        assert calls["batch"] >= 1, "Batch hook should be used"
        assert calls["single"] == 0, (
            f"Single-row hook must NOT be called when batch is implemented on the "
            f"same plugin; got {calls['single']} single calls"
        )
    finally:
        ds.pm.unregister(plugin, name="both_hooks")


@pytest.mark.asyncio
async def test_single_row_hook_still_works_without_batch():
    """When only export_row_transform is implemented, it is called per row."""

    class SingleOnly:
        @hookimpl
        def export_row_transform(self, database, table, row, export_format):
            new_row = dict(row)
            new_row["v"] = new_row["v"] + "_TAGGED"
            return new_row

    ds = Datasette(memory=True)
    plugin = SingleOnly()
    ds.pm.register(plugin, name="single_only")
    try:
        db = ds.add_memory_database("exh2d")
        await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        await db.execute_write("INSERT INTO t VALUES (1, 'test')")

        r = await ds.client.get("/exh2d/t.csv?_size=max")
        assert r.status_code == 200
        assert "test_TAGGED" in r.text
    finally:
        ds.pm.unregister(plugin, name="single_only")


@pytest.mark.asyncio
async def test_no_hook_output_unchanged():
    """Without any hook, CSV output is correct and untransformed."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("exh2e")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    await db.execute_write("INSERT INTO t VALUES (1, 'plain')")

    r = await ds.client.get("/exh2e/t.csv?_size=max")
    assert r.status_code == 200
    assert "plain" in r.text
    assert "_TAGGED" not in r.text
    assert "***" not in r.text
