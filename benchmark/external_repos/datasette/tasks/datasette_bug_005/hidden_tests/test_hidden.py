"""Hidden tests for datasette_bug_005: streaming CSV returns all rows.

The injected defect uses data.get('next_url') instead of data.get('next')
to get the next-page token, so the while loop exits after page 1.
"""
import pytest
from datasette.app import Datasette


async def _make_ds(db_name, row_count=25, page_size=10):
    ds = Datasette(
        memory=True,
        settings={
            "allow_csv_stream": True,
            "default_page_size": page_size,
            "max_returned_rows": row_count + 100,
        },
    )
    db = ds.add_memory_database(db_name)
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    for i in range(1, row_count + 1):
        await db.execute_write("INSERT INTO t VALUES (?, ?)", [i, f"value{i}"])
    return ds


@pytest.mark.asyncio
async def test_streaming_csv_returns_all_rows_two_pages():
    """Streaming CSV returns all rows when there are exactly 2 pages."""
    row_count = 15
    page_size = 10
    ds = await _make_ds("sdb1", row_count=row_count, page_size=page_size)
    client = ds.client

    r = await client.get("/sdb1/t.csv?_stream=1")
    assert r.status_code == 200
    lines = [l for l in r.text.strip().split("\n") if l]
    data_lines = lines[1:]  # skip header
    assert len(data_lines) == row_count, (
        f"Expected {row_count} data rows in streaming CSV, got {len(data_lines)}. "
        f"First few lines: {lines[:5]}"
    )


@pytest.mark.asyncio
async def test_streaming_csv_returns_all_rows_many_pages():
    """Streaming CSV returns all rows across many pages."""
    row_count = 55
    page_size = 10
    ds = await _make_ds("sdb2", row_count=row_count, page_size=page_size)
    client = ds.client

    r = await client.get("/sdb2/t.csv?_stream=1")
    assert r.status_code == 200
    lines = [l for l in r.text.strip().split("\n") if l]
    data_lines = lines[1:]
    assert len(data_lines) == row_count, (
        f"Expected {row_count} data rows, got {len(data_lines)}"
    )


@pytest.mark.asyncio
async def test_streaming_csv_row_values_correct():
    """All row values in the streaming CSV are correct and in order."""
    row_count = 12
    page_size = 5
    ds = await _make_ds("sdb3", row_count=row_count, page_size=page_size)
    client = ds.client

    r = await client.get("/sdb3/t.csv?_stream=1")
    assert r.status_code == 200
    lines = [l for l in r.text.strip().split("\n") if l]
    data_lines = lines[1:]
    assert len(data_lines) == row_count

    for i, line in enumerate(data_lines):
        expected_id = str(i + 1)
        expected_val = f"value{i + 1}"
        assert expected_id in line, f"Row {i+1}: expected id={expected_id} in {line!r}"
        assert expected_val in line, f"Row {i+1}: expected val={expected_val} in {line!r}"


@pytest.mark.asyncio
async def test_large_streaming_csv_for_output_stress():
    """Generate large streaming CSV output (>50KB) to satisfy output stress."""
    row_count = 500
    page_size = 100
    ds = Datasette(
        memory=True,
        settings={
            "allow_csv_stream": True,
            "default_page_size": page_size,
            "max_returned_rows": row_count + 100,
        },
    )
    db = ds.add_memory_database("sdb4")
    await db.execute_write(
        "CREATE TABLE big (id INTEGER PRIMARY KEY, name TEXT, description TEXT, value REAL)"
    )
    for i in range(1, row_count + 1):
        await db.execute_write(
            "INSERT INTO big VALUES (?, ?, ?, ?)",
            [i, f"item_{i:04d}", f"description of item number {i} with some padding text", i * 1.5],
        )

    client = ds.client
    r = await client.get("/sdb4/big.csv?_stream=1")
    assert r.status_code == 200

    content = r.text
    assert len(content.encode("utf-8")) > 30_000, (
        f"Expected > 30KB output, got {len(content.encode('utf-8'))} bytes"
    )
    lines = [l for l in content.strip().split("\n") if l]
    data_lines = lines[1:]
    assert len(data_lines) == row_count, (
        f"Expected {row_count} data rows in large streaming CSV, got {len(data_lines)}"
    )
