"""Visible tests for datasette_bug_004: settings precedence.

These tests confirm that the settings API is accessible and that defaults
work. They do not test the constructor-vs-config override path (hidden).
"""
import pytest
from datasette.app import Datasette


def test_default_setting_applies():
    """A default setting value is applied when nothing overrides it."""
    ds = Datasette(memory=True)
    assert ds.setting("default_page_size") == 100


def test_explicit_setting_via_constructor():
    """Settings passed via constructor are applied."""
    ds = Datasette(memory=True, settings={"default_page_size": 25})
    assert ds.setting("default_page_size") == 25


def test_config_only_setting_applies():
    """A setting in the config dict is applied when no constructor override."""
    ds = Datasette(
        memory=True,
        config={"settings": {"default_page_size": 42}},
    )
    assert ds.setting("default_page_size") == 42


@pytest.mark.asyncio
async def test_settings_endpoint_accessible():
    """The settings JSON endpoint is reachable."""
    ds = Datasette(memory=True, settings={"default_page_size": 15})
    client = ds.client
    r = await client.get("/-/settings.json")
    assert r.status_code == 200
    data = r.json()
    assert "default_page_size" in data
