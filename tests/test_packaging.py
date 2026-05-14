"""Tests for HACS/release packaging metadata."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_and_project_versions_match() -> None:
    """Test integration versions are kept in sync."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    manifest = json.loads(
        (ROOT / "custom_components/opendtu/manifest.json").read_text(),
    )

    assert manifest["version"] == pyproject["project"]["version"]


def test_hacs_zip_release_metadata() -> None:
    """Test HACS is configured for release zip installation."""
    hacs = json.loads((ROOT / "hacs.json").read_text())

    assert hacs["name"] == "OpenDTU"
    assert hacs["zip_release"] is True
    assert hacs["filename"] == "opendtu.zip"


def test_required_integration_files_exist() -> None:
    """Test the HACS package includes the files HA needs to load."""
    integration_dir = ROOT / "custom_components/opendtu"

    for filename in (
        "__init__.py",
        "manifest.json",
        "config_flow.py",
        "sensor.py",
        "binary_sensor.py",
        "translations/en.json",
    ):
        assert (integration_dir / filename).is_file()
