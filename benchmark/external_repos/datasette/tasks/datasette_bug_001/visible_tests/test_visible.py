"""Visible tests for datasette_bug_001: pagination continuity.

These tests confirm that basic pagination works and that the next-page
link is present when rows exceed the page size. They do not fully
verify row-skipping (that is covered by hidden tests).
"""
import pytest
from datasette.app import Datasette


@pytest.mark.asyncio
async def test_pagination_has_next_link():
    """A table with more rows than page_size should return a next link."""
    ds = Datasette(memory=True, settings={"default_page_size": 5, "max_returned_rows": 1000})
    db = ds.add_memory_database("vdb1")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    for i in range(15):
        await db.execute_write("INSERT INTO t VALUES (?, ?)", [i + 1, f"val{i + 1}"])

    client = ds.client
    r = await client.get("/vdb1/t.json?_size=5")
    assert r.status_code == 200
    data = r.json()
    assert data.get("next") is not None, "Expected a next-page token for page 1"


@pytest.mark.asyncio
async def test_pagination_first_page_correct():
    """First page returns exactly page_size rows with correct IDs."""
    ds = Datasette(memory=True, settings={"default_page_size": 5, "max_returned_rows": 1000})
    db = ds.add_memory_database("vdb2")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    for i in range(20):
        await db.execute_write("INSERT INTO t VALUES (?, ?)", [i + 1, f"val{i + 1}"])

    client = ds.client
    r = await client.get("/vdb2/t.json?_size=5")
    assert r.status_code == 200
    data = r.json()
    rows = data["rows"]
    assert len(rows) == 5
    ids = [row["id"] for row in rows]
    assert ids == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_small_table_no_next_link():
    """A table with fewer rows than page_size returns no next link."""
    ds = Datasette(memory=True, settings={"default_page_size": 10, "max_returned_rows": 1000})
    db = ds.add_memory_database("vdb3")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    for i in range(3):
        await db.execute_write("INSERT INTO t VALUES (?, ?)", [i + 1, f"val{i + 1}"])

    client = ds.client
    r = await client.get("/vdb3/t.json?_size=10")
    assert r.status_code == 200
    data = r.json()
    assert data.get("next") is None, "Small table should have no next link"
