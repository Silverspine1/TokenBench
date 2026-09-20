"""Hidden tests for datasette_export_hooks_stage_1: export_row_transform hook.

These tests validate the full contract: hook receives correct arguments,
returned dict is used in output, and no-hook behavior is unchanged.

Plugins are registered through the Datasette plugin manager (ds.pm) and
always unregistered in a finally block so tests stay isolated.
"""
import pytest
from datasette.app import Datasette
from datasette import hookimpl


class RedactPlugin:
    @hookimpl
    def export_row_transform(self, database, table, row, export_format):
        new_row = dict(row)
        if "email" in new_row:
            new_row["email"] = "REDACTED"
        return new_row


class PassthroughPlugin:
    @hookimpl
    def export_row_transform(self, database, table, row, export_format):
        return row


@pytest.mark.asyncio
async def test_hook_transforms_csv_row():
    """Hook-returned values appear in CSV export output."""
    ds = Datasette(memory=True)
    plugin = RedactPlugin()
    ds.pm.register(plugin, name="redact_plugin")
    try:
        db = ds.add_memory_database("exh1a")
        await db.execute_write(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
        )
        await db.execute_write("INSERT INTO users VALUES (1, 'Alice', 'alice@example.com')")

        r = await ds.client.get("/exh1a/users.csv?_size=max")
        assert r.status_code == 200
        assert "REDACTED" in r.text, "Hook should have redacted the email"
        assert "alice@example.com" not in r.text, "Original email should not appear"
    finally:
        ds.pm.unregister(plugin, name="redact_plugin")


@pytest.mark.asyncio
async def test_hook_receives_correct_arguments():
    """Hook callback receives database, table, row (dict), and export_format."""
    captured = []

    class CapturingPlugin:
        @hookimpl
        def export_row_transform(self, database, table, row, export_format):
            captured.append({
                "database": database,
                "table": table,
                "row_type": type(row).__name__,
                "export_format": export_format,
            })
            return row

    ds = Datasette(memory=True)
    plugin = CapturingPlugin()
    ds.pm.register(plugin, name="capturing_plugin")
    try:
        db = ds.add_memory_database("exh1b")
        await db.execute_write("CREATE TABLE items (id INTEGER PRIMARY KEY, v TEXT)")
        await db.execute_write("INSERT INTO items VALUES (1, 'x')")

        await ds.client.get("/exh1b/items.csv?_size=max")

        assert len(captured) >= 1, "Hook should have been called at least once"
        call = captured[0]
        assert call["database"] == "exh1b", f"database arg: {call['database']}"
        assert call["table"] == "items", f"table arg: {call['table']}"
        assert call["row_type"] == "dict", f"row should be dict, got {call['row_type']}"
        assert call["export_format"] == "csv", f"export_format arg: {call['export_format']}"
    finally:
        ds.pm.unregister(plugin, name="capturing_plugin")


@pytest.mark.asyncio
async def test_no_hook_csv_unchanged():
    """Without a registered hook, CSV output is unchanged."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("exh1c")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    await db.execute_write("INSERT INTO t VALUES (1, 'hello')")

    r = await ds.client.get("/exh1c/t.csv?_size=max")
    assert r.status_code == 200
    assert "hello" in r.text


@pytest.mark.asyncio
async def test_passthrough_hook_preserves_output():
    """A hook that returns the row unchanged produces identical output."""
    ds = Datasette(memory=True)
    plugin = PassthroughPlugin()
    ds.pm.register(plugin, name="passthrough_plugin")
    try:
        db = ds.add_memory_database("exh1d")
        await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        await db.execute_write("INSERT INTO t VALUES (1, 'value1')")
        await db.execute_write("INSERT INTO t VALUES (2, 'value2')")

        r = await ds.client.get("/exh1d/t.csv?_size=max")
        assert r.status_code == 200
        assert "value1" in r.text
        assert "value2" in r.text
    finally:
        ds.pm.unregister(plugin, name="passthrough_plugin")


@pytest.mark.asyncio
async def test_hook_transforms_json_row():
    """Hook-returned values appear in JSON export output too."""
    ds = Datasette(memory=True)
    plugin = RedactPlugin()
    ds.pm.register(plugin, name="redact_plugin_json")
    try:
        db = ds.add_memory_database("exh1e")
        await db.execute_write(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)"
        )
        await db.execute_write("INSERT INTO users VALUES (1, 'bob@example.com')")

        r = await ds.client.get("/exh1e/users.json?_size=max")
        assert r.status_code == 200
        body = r.text
        assert "REDACTED" in body, "Hook should redact email in JSON export"
        assert "bob@example.com" not in body, "Original email should not appear in JSON"
    finally:
        ds.pm.unregister(plugin, name="redact_plugin_json")
