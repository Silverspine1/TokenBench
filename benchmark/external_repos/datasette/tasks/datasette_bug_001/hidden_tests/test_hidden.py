"""Hidden tests for datasette_bug_001: no rows skipped across page boundaries.

These tests verify end-to-end row continuity when paginating through a table
using the _next cursor. Each row must appear exactly once across all pages.
"""
import pytest
import pytest_asyncio
from datasette.app import Datasette
try:
    import pysqlite3 as sqlite3
except ImportError:
    import sqlite3


async def _collect_all_rows(client, url):
    """Follow _next pagination and collect all rows."""
    rows = []
    next_token = None
    while True:
        full_url = url + (f"&_next={next_token}" if next_token else "")
        r = await client.get(full_url)
        assert r.status_code == 200, f"Unexpected status {r.status_code}"
        data = r.json()
        rows.extend(data["rows"])
        next_token = data.get("next")
        if not next_token:
            break
    return rows


@pytest.mark.asyncio
async def test_no_rows_skipped_pk_pagination():
    """All rows appear exactly once across all pages (PK cursor navigation)."""
    row_count = 13
    page_size = 5
    ds = Datasette(
        memory=True,
        settings={"default_page_size": page_size, "max_returned_rows": 1000},
    )
    db = ds.add_memory_database("db1")
    await db.execute_write("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
    for i in range(1, row_count + 1):
        await db.execute_write("INSERT INTO items VALUES (?, ?)", [i, f"item{i}"])

    client = ds.client
    rows = await _collect_all_rows(client, "/db1/items.json?_size=5")

    ids = [r["id"] for r in rows]
    assert len(ids) == row_count, f"Expected {row_count} rows, got {len(ids)}: {ids}"
    assert ids == list(range(1, row_count + 1)), f"Row IDs not sequential: {ids}"


@pytest.mark.asyncio
async def test_second_page_starts_where_first_left_off():
    """First row of page 2 is immediately after the last row of page 1."""
    page_size = 4
    ds = Datasette(
        memory=True,
        settings={"default_page_size": page_size, "max_returned_rows": 1000},
    )
    db = ds.add_memory_database("db2")
    await db.execute_write("CREATE TABLE items (id INTEGER PRIMARY KEY, v INTEGER)")
    for i in range(1, 11):
        await db.execute_write("INSERT INTO items VALUES (?, ?)", [i, i * 10])

    client = ds.client

    r1 = await client.get("/db2/items.json?_size=4")
    assert r1.status_code == 200
    d1 = r1.json()
    page1_ids = [row["id"] for row in d1["rows"]]
    next_token = d1.get("next")
    assert next_token is not None, "Expected next token after page 1"
    assert page1_ids == [1, 2, 3, 4], f"Page 1 IDs: {page1_ids}"

    r2 = await client.get(f"/db2/items.json?_size=4&_next={next_token}")
    assert r2.status_code == 200
    d2 = r2.json()
    page2_ids = [row["id"] for row in d2["rows"]]
    assert page2_ids[0] == 5, f"Expected page 2 to start at ID 5, got {page2_ids[0]}"
    assert page2_ids == [5, 6, 7, 8], f"Page 2 IDs: {page2_ids}"


@pytest.mark.asyncio
async def test_exact_page_boundary_no_skip():
    """Table with exactly page_size+1 rows: second page has exactly 1 row."""
    page_size = 5
    ds = Datasette(
        memory=True,
        settings={"default_page_size": page_size, "max_returned_rows": 1000},
    )
    db = ds.add_memory_database("db3")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    for i in range(1, 7):  # 6 rows, page_size=5
        await db.execute_write("INSERT INTO t VALUES (?, ?)", [i, f"v{i}"])

    client = ds.client
    rows = await _collect_all_rows(client, "/db3/t.json?_size=5")
    ids = [r["id"] for r in rows]
    assert ids == [1, 2, 3, 4, 5, 6], f"All rows: {ids}"


@pytest.mark.asyncio
async def test_offset_view_pagination_unaffected():
    """Offset-based pagination (SQL view) still works correctly."""
    page_size = 3
    ds = Datasette(
        memory=True,
        settings={"default_page_size": page_size, "max_returned_rows": 1000},
    )
    db = ds.add_memory_database("db4")
    await db.execute_write("CREATE TABLE src (id INTEGER PRIMARY KEY, v TEXT)")
    for i in range(1, 8):
        await db.execute_write("INSERT INTO src VALUES (?, ?)", [i, f"v{i}"])
    await db.execute_write(
        "CREATE VIEW vw AS SELECT id, v FROM src ORDER BY id"
    )

    client = ds.client
    rows = await _collect_all_rows(client, "/db4/vw.json?_size=3")
    ids = [r["id"] for r in rows]
    assert len(ids) == 7, f"Expected 7 rows from view, got {ids}"
    assert ids == list(range(1, 8)), f"View row IDs: {ids}"


@pytest.mark.asyncio
async def test_filtered_pagination_no_rows_skipped():
    """Filtering a table and paginating shows all matching rows exactly once."""
    page_size = 3
    ds = Datasette(
        memory=True,
        settings={"default_page_size": page_size, "max_returned_rows": 1000},
    )
    db = ds.add_memory_database("db5")
    await db.execute_write(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, category TEXT)"
    )
    for i in range(1, 15):
        cat = "A" if i % 2 == 0 else "B"
        await db.execute_write("INSERT INTO items VALUES (?, ?)", [i, cat])

    client = ds.client
    rows = await _collect_all_rows(client, "/db5/items.json?_size=3&category=A")
    ids = [r["id"] for r in rows]
    expected = [i for i in range(1, 15) if i % 2 == 0]
    assert sorted(ids) == expected, f"Filtered rows: {ids}, expected: {expected}"
    assert len(ids) == len(expected), "Duplicates or missing rows in filtered pagination"


@pytest.mark.asyncio
async def test_sorted_pagination_no_rows_skipped():
    """Sorting by a non-PK column and paginating shows every row exactly once."""
    page_size = 4
    ds = Datasette(
        memory=True,
        settings={"default_page_size": page_size, "max_returned_rows": 1000},
    )
    db = ds.add_memory_database("db6")
    await db.execute_write(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, score INTEGER)"
    )
    # Distinct, non-monotonic-with-id score values so sort order != pk order.
    scores = [50, 10, 90, 30, 70, 20, 80, 40, 60, 5, 95, 15, 85]
    for i, sc in enumerate(scores, start=1):
        await db.execute_write("INSERT INTO items VALUES (?, ?)", [i, sc])

    rows = await _collect_all_rows(client=ds.client, url="/db6/items.json?_size=4&_sort=score")
    ids = sorted(r["id"] for r in rows)
    assert ids == list(range(1, len(scores) + 1)), (
        f"Sorted pagination skipped or duplicated rows: got {len(ids)} unique ids: {ids}"
    )
    # And the rows must come back in ascending score order across page boundaries.
    returned_scores = [r["score"] for r in rows]
    assert returned_scores == sorted(scores), (
        f"Sorted pagination broke ordering across pages: {returned_scores}"
    )


@pytest.mark.asyncio
async def test_sort_desc_pagination_no_rows_skipped():
    """Descending sort pagination also returns every row exactly once."""
    page_size = 3
    ds = Datasette(
        memory=True,
        settings={"default_page_size": page_size, "max_returned_rows": 1000},
    )
    db = ds.add_memory_database("db7")
    await db.execute_write(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, score INTEGER)"
    )
    scores = [12, 7, 19, 3, 25, 9, 14, 1, 22, 16]
    for i, sc in enumerate(scores, start=1):
        await db.execute_write("INSERT INTO items VALUES (?, ?)", [i, sc])

    rows = await _collect_all_rows(client=ds.client, url="/db7/items.json?_size=3&_sort_desc=score")
    ids = sorted(r["id"] for r in rows)
    assert ids == list(range(1, len(scores) + 1)), (
        f"Descending sorted pagination skipped/duplicated rows: {ids}"
    )
