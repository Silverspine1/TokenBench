"""Hidden tests for datasette_bug_004: constructor settings override config.

The injected defect swaps the merge order so config_settings (from datasette.json)
overrides the explicitly passed `settings` dict. The correct behavior is that
the `settings` constructor parameter (representing CLI --setting flags) wins.
"""
import pytest
from datasette.app import Datasette


def test_constructor_setting_overrides_config():
    """Constructor settings win over config file settings."""
    ds = Datasette(
        memory=True,
        config={"settings": {"default_page_size": 50}},
        settings={"default_page_size": 20},
    )
    assert ds.setting("default_page_size") == 20, (
        "Constructor settings=20 should override config settings=50, "
        f"but got {ds.setting('default_page_size')}"
    )


def test_constructor_overrides_config_for_multiple_settings():
    """Constructor settings override config for all affected keys."""
    ds = Datasette(
        memory=True,
        config={"settings": {
            "default_page_size": 50,
            "max_returned_rows": 500,
        }},
        settings={
            "default_page_size": 10,
            "max_returned_rows": 200,
        },
    )
    assert ds.setting("default_page_size") == 10, (
        f"Expected 10, got {ds.setting('default_page_size')}"
    )
    assert ds.setting("max_returned_rows") == 200, (
        f"Expected 200, got {ds.setting('max_returned_rows')}"
    )


def test_config_only_setting_still_applies():
    """Settings only in config (no constructor override) are still applied."""
    ds = Datasette(
        memory=True,
        config={"settings": {"default_page_size": 77}},
        settings={},
    )
    assert ds.setting("default_page_size") == 77, (
        f"Config-only setting should be 77, got {ds.setting('default_page_size')}"
    )


def test_default_applies_when_neither_overrides():
    """Default setting applies when neither config nor constructor provides it."""
    ds = Datasette(
        memory=True,
        config={"settings": {}},
        settings={},
    )
    assert ds.setting("default_page_size") == 100, (
        f"Default should be 100, got {ds.setting('default_page_size')}"
    )


def test_allow_csv_stream_override():
    """allow_csv_stream can be overridden via constructor settings."""
    ds = Datasette(
        memory=True,
        config={"settings": {"allow_csv_stream": False}},
        settings={"allow_csv_stream": True},
    )
    assert ds.setting("allow_csv_stream") is True, (
        f"Constructor should set allow_csv_stream=True, got {ds.setting('allow_csv_stream')}"
    )


def test_max_csv_mb_override():
    """max_csv_mb can be overridden via constructor settings."""
    ds = Datasette(
        memory=True,
        config={"settings": {"max_csv_mb": 100}},
        settings={"max_csv_mb": 5},
    )
    assert ds.setting("max_csv_mb") == 5, (
        f"Constructor should set max_csv_mb=5, got {ds.setting('max_csv_mb')}"
    )
