"""Validate repository metadata for HACS releases."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "opendtu"
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def main() -> int:
    """Validate HACS and Home Assistant package metadata."""
    errors: list[str] = []

    pyproject = _load_toml(ROOT / "pyproject.toml", errors)
    hacs = _load_json(ROOT / "hacs.json", errors)
    manifest = _load_json(ROOT / f"custom_components/{DOMAIN}/manifest.json", errors)

    integration_dir = ROOT / "custom_components" / DOMAIN
    for required_file in (
        "__init__.py",
        "manifest.json",
        "config_flow.py",
        "const.py",
        "coordinator.py",
        "api.py",
        "entity.py",
        "sensor.py",
        "binary_sensor.py",
        "translations/en.json",
    ):
        if not (integration_dir / required_file).is_file():
            errors.append(f"Missing integration file: {required_file}")

    project_version = pyproject.get("project", {}).get("version")
    manifest_version = manifest.get("version")
    if manifest_version != project_version:
        errors.append(
            "custom_components/opendtu/manifest.json version must match "
            "pyproject.toml project.version",
        )
    if not isinstance(manifest_version, str) or not SEMVER_PATTERN.match(
        manifest_version,
    ):
        errors.append("Integration manifest version must be SemVer-like")

    if manifest.get("domain") != DOMAIN:
        errors.append(f"Integration manifest domain must be {DOMAIN!r}")
    for key in ("name", "documentation", "issue_tracker", "codeowners", "iot_class"):
        if key not in manifest:
            errors.append(f"Integration manifest is missing {key!r}")

    if hacs.get("name") != "OpenDTU":
        errors.append("hacs.json name must be 'OpenDTU'")
    if hacs.get("zip_release") is not True:
        errors.append("hacs.json must set zip_release to true")
    if hacs.get("filename") != "opendtu.zip":
        errors.append("hacs.json filename must be 'opendtu.zip'")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("HACS metadata looks good.")
    return 0


def _load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    """Load a JSON file and collect validation errors."""
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        errors.append(f"Missing file: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as err:
        errors.append(f"Invalid JSON in {path.relative_to(ROOT)}: {err}")
    return {}


def _load_toml(path: Path, errors: list[str]) -> dict[str, Any]:
    """Load a TOML file and collect validation errors."""
    try:
        return tomllib.loads(path.read_text())
    except FileNotFoundError:
        errors.append(f"Missing file: {path.relative_to(ROOT)}")
    except tomllib.TOMLDecodeError as err:
        errors.append(f"Invalid TOML in {path.relative_to(ROOT)}: {err}")
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
