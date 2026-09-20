"""Hidden tests for datasette_bug_002: table-level license/source in API.

The injected defect skips storing license/license_url/source/source_url
in the metadata_resources table during startup, so they never appear in
API responses at the table level.
"""
import pytest
from datasette.app import Datasette


async def _setup(db_name):
    ds = Datasette(
        memory=True,
        metadata={
            "databases": {
                db_name: {
                    "license": "DB-License",
                    "source": "DB-Source",
                    "tables": {
                        "mytable": {
                            "license": "Table-License",
                            "license_url": "https://example.com/table-license",
                            "source": "Table-Source",
                            "source_url": "https://example.com/table-source",
                        }
                    },
                }
            }
        },
    )
    db = ds.add_memory_database(db_name)
    await db.execute_write("CREATE TABLE mytable (id INTEGER PRIMARY KEY, v TEXT)")
    await db.execute_write("INSERT INTO mytable VALUES (1, 'x')")
    # Trigger startup via client
    await ds.client.get(f"/{db_name}/mytable.json")
    return ds, db_name


@pytest.mark.asyncio
async def test_table_license_in_metadata_api():
    """Table-level license field is stored and retrievable."""
    ds, db_name = await _setup("tdb1")
    table_meta = await ds.get_resource_metadata(db_name, "mytable")
    assert table_meta.get("license") == "Table-License", (
        f"table_metadata.license should be 'Table-License', got: {table_meta}"
    )


@pytest.mark.asyncio
async def test_table_source_in_metadata_api():
    """Table-level source field is stored and retrievable."""
    ds, db_name = await _setup("tdb2")
    table_meta = await ds.get_resource_metadata(db_name, "mytable")
    assert table_meta.get("source") == "Table-Source", (
        f"table_metadata.source should be 'Table-Source', got: {table_meta}"
    )


@pytest.mark.asyncio
async def test_table_license_url_in_metadata_api():
    """Table-level license_url field is stored and retrievable."""
    ds, db_name = await _setup("tdb3")
    table_meta = await ds.get_resource_metadata(db_name, "mytable")
    assert "license_url" in table_meta, (
        f"table_metadata.license_url is missing: {table_meta}"
    )
    assert table_meta["license_url"] == "https://example.com/table-license"


@pytest.mark.asyncio
async def test_database_license_unaffected():
    """Database-level license/source is still returned correctly."""
    ds, db_name = await _setup("tdb4")
    db_meta = await ds.get_database_metadata(db_name)
    assert db_meta.get("license") == "DB-License", (
        f"Database license should be 'DB-License', got: {db_meta}"
    )
    assert db_meta.get("source") == "DB-Source"


@pytest.mark.asyncio
async def test_table_other_metadata_not_dropped():
    """Non-license/source table metadata (description) is still stored."""
    ds = Datasette(
        memory=True,
        metadata={
            "databases": {
                "tdb5": {
                    "tables": {
                        "t": {
                            "description": "My special table",
                            "license": "MIT",
                        }
                    }
                }
            }
        },
    )
    db = ds.add_memory_database("tdb5")
    await db.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    await ds.client.get("/tdb5/t.json")

    table_meta = await ds.get_resource_metadata("tdb5", "t")
    assert table_meta.get("description") == "My special table", (
        f"description should not be dropped: {table_meta}"
    )
