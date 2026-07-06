"""Hidden tests for datasette_bug_003: CSV encoding matrix.

Verifies that CSV exports write raw values without HTML entity encoding
across a variety of character types. The injected defect applies
EscapeHtmlWriter in the normal (non-trace) CSV path, turning & into &amp;,
< into &lt;, etc.

This test file generates a large output matrix to exercise the output_stress
requirement and provide unambiguous pass/fail signal.
"""
import io
import csv
import pytest
from datasette.app import Datasette


ENCODING_MATRIX = [
    # (description, input_value, expected_substring_in_csv)
    ("ampersand", "A & B", "A & B"),
    ("less_than", "x < y", "x < y"),
    ("greater_than", "x > y", "x > y"),
    ("double_quote", 'say "hi"', '"say ""hi"""'),  # RFC 4180 quoting
    ("apostrophe", "it's fine", "it's fine"),
    ("html_entity_not_doubled", "&amp; already", "&amp; already"),
    ("unicode_euro", "price: €100", "price: €100"),
    ("unicode_cjk", "中文", "中文"),
    ("unicode_emoji", "café", "café"),
    ("newline_in_value", "line1\nline2", "line1\nline2"),
    ("comma_in_value", "a, b, c", "a, b, c"),
    ("null_like", "NULL", "NULL"),
    ("empty_string", "", ""),
    ("number_like", "42.5", "42.5"),
]


async def _make_ds_with_matrix(db_name):
    ds = Datasette(memory=True)
    db = ds.add_memory_database(db_name)
    await db.execute_write(
        "CREATE TABLE enc_test (id INTEGER PRIMARY KEY, label TEXT, value TEXT)"
    )
    for i, (label, value, _expected) in enumerate(ENCODING_MATRIX):
        await db.execute_write(
            "INSERT INTO enc_test VALUES (?, ?, ?)", [i + 1, label, value]
        )
    return ds


@pytest.mark.asyncio
async def test_ampersand_not_html_escaped():
    """Ampersand is written as-is, not as &amp;."""
    ds = await _make_ds_with_matrix("encdb1")
    client = ds.client
    r = await client.get("/encdb1/enc_test.csv?_size=max")
    assert r.status_code == 200
    content = r.text
    # 'A & B' should appear as-is, not as 'A &amp; B'
    assert "A &amp; B" not in content, (
        "Ampersand in 'A & B' should not be HTML-escaped to '&amp;'"
    )
    assert "A & B" in content, "Raw ampersand value should appear in CSV"


@pytest.mark.asyncio
async def test_less_than_not_html_escaped():
    """< is written as-is, not as &lt;."""
    ds = await _make_ds_with_matrix("encdb2")
    client = ds.client
    r = await client.get("/encdb2/enc_test.csv?_size=max")
    assert r.status_code == 200
    assert "&lt;" not in r.text, "CSV should not contain HTML entity &lt;"
    assert "x < y" in r.text


@pytest.mark.asyncio
async def test_greater_than_not_html_escaped():
    """> is written as-is, not as &gt;."""
    ds = await _make_ds_with_matrix("encdb3")
    client = ds.client
    r = await client.get("/encdb3/enc_test.csv?_size=max")
    assert r.status_code == 200
    assert "&gt;" not in r.text, "CSV should not contain HTML entity &gt;"


@pytest.mark.asyncio
async def test_unicode_preserved():
    """Unicode characters (euro sign, CJK) appear verbatim in CSV."""
    ds = await _make_ds_with_matrix("encdb4")
    client = ds.client
    r = await client.get("/encdb4/enc_test.csv?_size=max")
    assert r.status_code == 200
    assert "€" in r.text, "Euro sign should appear in CSV"
    assert "中文" in r.text, "CJK characters should appear in CSV"


@pytest.mark.asyncio
async def test_csv_is_parseable_by_stdlib():
    """The CSV output is parseable by the standard library csv module."""
    ds = await _make_ds_with_matrix("encdb5")
    client = ds.client
    r = await client.get("/encdb5/enc_test.csv?_size=max")
    assert r.status_code == 200
    reader = csv.reader(io.StringIO(r.text))
    rows = list(reader)
    assert len(rows) >= 2, "Should have header + at least one data row"


@pytest.mark.asyncio
async def test_large_encoding_matrix_no_html_entities():
    """Full matrix of values: none should appear as HTML entities."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("encdb6")
    await db.execute_write("CREATE TABLE big (id INTEGER PRIMARY KEY, val TEXT)")

    specials = ["A & B", "x < y", "x > y", 'q"r', "€", "中", "café"]
    for i in range(1000):
        val = specials[i % len(specials)] + f"_{i}"
        await db.execute_write("INSERT INTO big VALUES (?, ?)", [i + 1, val])

    client = ds.client
    r = await client.get("/encdb6/big.csv?_size=max")
    assert r.status_code == 200
    content = r.text
    assert len(content) > 10000, "Expected large output for stress test"
    assert "&amp;" not in content
    assert "&lt;" not in content
    assert "&gt;" not in content
    assert "&#" not in content, "No numeric HTML entities expected"


@pytest.mark.asyncio
async def test_column_order_unchanged():
    """Column order in CSV matches the table column definition order."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("encdb7")
    await db.execute_write("CREATE TABLE cols (c INTEGER PRIMARY KEY, b TEXT, a TEXT)")
    await db.execute_write("INSERT INTO cols VALUES (1, 'bee', 'ay')")

    client = ds.client
    r = await client.get("/encdb7/cols.csv?_size=max")
    assert r.status_code == 200
    header = r.text.splitlines()[0]
    cols = [c.strip() for c in header.split(",")]
    assert cols[0] == "c", f"First column should be 'c', got: {cols}"
    assert cols[1] == "b", f"Second column should be 'b', got: {cols}"
    assert cols[2] == "a", f"Third column should be 'a', got: {cols}"
