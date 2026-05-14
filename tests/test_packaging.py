"""Tests for HACS/release packaging metadata."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

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


def test_hacs_package_zip_has_integration_files_at_root(tmp_path: Path) -> None:
    """Test the HACS zip does not include nested custom_components paths."""
    source = ROOT / "custom_components/opendtu"
    package = tmp_path / "opendtu.zip"

    with ZipFile(package, "w", ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source))

    with ZipFile(package) as archive:
        names = set(archive.namelist())

    assert "manifest.json" in names
    assert "sensor.py" in names
    assert "translations/en.json" in names
    assert "custom_components/opendtu/manifest.json" not in names
