# Copyright 2026 Ponder
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Unit tests for dwe.registry — pure functions only, no network."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from dwe.registry import (
    fetch_adapter_metadata,
    get_adapter,
    get_adapter_catalog,
    list_adapters,
    load_registry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_ADAPTERS = {
    "dwe_test": {
        "url": "https://github.com/example/dwe_test",
        "hub_name": "test",
        "type": "git",
        "display_name": "Test Adapter",
        "description": "A test adapter",
        "required_secrets": [{"key": "SECRET_KEY", "destination": "ci"}],
        "optional_secrets": [],
    }
}


@pytest.fixture()
def registry_file(tmp_path, monkeypatch):
    """Write a fake adapters.json and point REGISTRY_PATH at it."""
    path = tmp_path / "adapters.json"
    path.write_text(json.dumps(FAKE_ADAPTERS))
    monkeypatch.setattr("dwe.registry.REGISTRY_PATH", path)
    return path


# ---------------------------------------------------------------------------
# load_registry — pure, no network
# ---------------------------------------------------------------------------

def test_load_registry_returns_dict(registry_file):
    result = load_registry()
    assert isinstance(result, dict)
    assert "dwe_test" in result


def test_load_registry_no_network_call(registry_file):
    """load_registry() must never make a network request."""
    import urllib.request

    def _fail(*args, **kwargs):
        raise AssertionError("load_registry() made a network call")

    with patch.object(urllib.request, "urlopen", side_effect=_fail):
        result = load_registry()

    assert result == FAKE_ADAPTERS


def test_load_registry_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("dwe.registry.REGISTRY_PATH", tmp_path / "nonexistent.json")
    assert load_registry() == {}


# ---------------------------------------------------------------------------
# get_adapter / list_adapters
# ---------------------------------------------------------------------------

def test_get_adapter_known(registry_file):
    info = get_adapter("dwe_test")
    assert info is not None
    assert info["hub_name"] == "test"


def test_get_adapter_unknown(registry_file):
    assert get_adapter("dwe_missing") is None


def test_list_adapters(registry_file):
    names = list_adapters()
    assert names == ["dwe_test"]


# ---------------------------------------------------------------------------
# fetch_adapter_metadata — explicit network boundary
# ---------------------------------------------------------------------------

def test_fetch_adapter_metadata_local(tmp_path):
    """For local adapters, fetch_adapter_metadata reads from disk, no network."""
    copier_yml = tmp_path / "copier.yml"
    copier_yml.write_text("_dwe_hub:\n  hub_name: localtest\n  description: Local adapter\n")

    result = fetch_adapter_metadata({"path": str(tmp_path)})
    assert result["hub_name"] == "localtest"
    assert result["description"] == "Local adapter"


def test_fetch_adapter_metadata_missing_dwe_hub_section(tmp_path):
    """Returns {} when copier.yml has no _dwe_hub key."""
    (tmp_path / "copier.yml").write_text("project_name:\n  default: myproject\n")
    assert fetch_adapter_metadata({"path": str(tmp_path)}) == {}


def test_fetch_adapter_metadata_no_path_no_url():
    """Returns {} gracefully when adapter has neither url nor path."""
    assert fetch_adapter_metadata({}) == {}


# ---------------------------------------------------------------------------
# get_adapter_catalog — structural checks (no network since local adapter)
# ---------------------------------------------------------------------------

def test_get_adapter_catalog_structure(registry_file, tmp_path):
    """Catalog entries have the expected keys even for git adapters (network stubbed)."""
    with patch("dwe.registry._load_copier_yml", return_value={}):
        catalog = get_adapter_catalog()

    assert "dwe_test" in catalog
    entry = catalog["dwe_test"]
    for key in ("name", "hub_name", "url", "type", "required_secrets", "ci_secrets"):
        assert key in entry, f"Missing key: {key}"


def test_get_adapter_catalog_ci_secrets_split(registry_file):
    """ci_secrets must only contain secrets whose destination includes 'ci'."""
    with patch("dwe.registry._load_copier_yml", return_value={}):
        catalog = get_adapter_catalog()

    entry = catalog["dwe_test"]
    assert any(s["key"] == "SECRET_KEY" for s in entry["ci_secrets"])
