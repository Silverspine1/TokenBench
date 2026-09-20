"""Visible tests for datasette_bug_003: CSV export encoding.

These tests confirm that the CSV endpoint responds and that columns
are correct. They do not test the exact character encoding (hidden tests).
"""
import pytest
from datasette.app import Datasette


@pytest.mark.asyncio
async def test_csv_endpoint_returns_200():
    """CSV endpoint returns 200 for a table with data."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("csv1")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    await db.execute_write("INSERT INTO t VALUES (1, 'Alice')")
    await db.execute_write("INSERT INTO t VALUES (2, 'Bob')")

    client = ds.client
    r = await client.get("/csv1/t.csv")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_csv_has_correct_column_headers():
    """CSV export includes the correct column headers as the first row."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("csv2")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT, score REAL)")
    await db.execute_write("INSERT INTO t VALUES (1, 'Alice', 9.5)")

    client = ds.client
    r = await client.get("/csv2/t.csv")
    assert r.status_code == 200
    lines = r.text.strip().split("\n")
    header = lines[0].strip()
    assert "id" in header
    assert "name" in header
    assert "score" in header


@pytest.mark.asyncio
async def test_csv_plain_ascii_values():
    """Simple ASCII values appear verbatim in CSV output."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("csv3")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    await db.execute_write("INSERT INTO t VALUES (1, 'hello world')")
    await db.execute_write("INSERT INTO t VALUES (2, 'foo bar')")

    client = ds.client
    r = await client.get("/csv3/t.csv")
    assert r.status_code == 200
    assert "hello world" in r.text
    assert "foo bar" in r.text
