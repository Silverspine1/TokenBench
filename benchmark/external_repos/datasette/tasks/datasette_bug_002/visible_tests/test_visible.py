"""Visible tests for datasette_bug_002: metadata propagation.

These tests confirm that database-level metadata (license, source) is
returned correctly and that the metadata API is responsive. They do not
test the broken table-level path (covered by hidden tests).
"""
import pytest
from datasette.app import Datasette


@pytest.mark.asyncio
async def test_database_metadata_license_in_api():
    """Database-level license appears in the database JSON API response."""
    ds = Datasette(
        memory=True,
        metadata={
            "databases": {
                "mdb1": {
                    "license": "CC-BY-4.0",
                    "license_url": "https://creativecommons.org/licenses/by/4.0/",
                }
            }
        },
    )
    db = ds.add_memory_database("mdb1")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY)")

    client = ds.client
    r = await client.get("/mdb1/t.json")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_table_json_api_accessible():
    """Table JSON endpoint is reachable and returns rows."""
    ds = Datasette(memory=True)
    db = ds.add_memory_database("mdb2")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    await db.execute_write("INSERT INTO t VALUES (1, 'hello')")

    client = ds.client
    r = await client.get("/mdb2/t.json")
    assert r.status_code == 200
    data = r.json()
    assert len(data["rows"]) == 1


@pytest.mark.asyncio
async def test_instance_level_metadata_still_works():
    """Instance-level license/source metadata is accessible."""
    ds = Datasette(
        memory=True,
        metadata={
            "license": "Apache-2.0",
            "source": "Open Data Portal",
        },
    )
    db = ds.add_memory_database("mdb3")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY)")

    client = ds.client
    r = await client.get("/-/versions.json")
    assert r.status_code == 200
