"""Visible tests for datasette_bug_005: streaming CSV.

These tests confirm that the streaming CSV endpoint responds and that
non-streaming CSV is unaffected. They do not test multi-page streaming
row counts (covered by hidden tests).
"""
import pytest
from datasette.app import Datasette


@pytest.mark.asyncio
async def test_streaming_csv_endpoint_responds():
    """?_stream=1 returns 200 for a table with data."""
    ds = Datasette(
        memory=True,
        settings={"allow_csv_stream": True, "default_page_size": 5, "max_returned_rows": 1000},
    )
    db = ds.add_memory_database("stm1")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    for i in range(1, 8):
        await db.execute_write("INSERT INTO t VALUES (?, ?)", [i, f"v{i}"])

    client = ds.client
    r = await client.get("/stm1/t.csv?_stream=1")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_non_streaming_csv_unaffected():
    """Non-streaming CSV export still works correctly."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("stm2")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    for i in range(1, 4):
        await db.execute_write("INSERT INTO t VALUES (?, ?)", [i, f"v{i}"])

    client = ds.client
    r = await client.get("/stm2/t.csv")
    assert r.status_code == 200
    lines = [l for l in r.text.strip().split("\n") if l]
    assert len(lines) == 4  # 1 header + 3 rows


@pytest.mark.asyncio
async def test_streaming_csv_single_page_complete():
    """Streaming CSV with data <= page_size returns all rows."""
    ds = Datasette(
        memory=True,
        settings={"allow_csv_stream": True, "default_page_size": 10, "max_returned_rows": 1000},
    )
    db = ds.add_memory_database("stm3")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    for i in range(1, 6):  # 5 rows < page_size=10
        await db.execute_write("INSERT INTO t VALUES (?, ?)", [i, f"v{i}"])

    client = ds.client
    r = await client.get("/stm3/t.csv?_stream=1")
    assert r.status_code == 200
    lines = [l for l in r.text.strip().split("\n") if l]
    assert len(lines) == 6  # 1 header + 5 rows
