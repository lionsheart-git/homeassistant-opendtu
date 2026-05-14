"""Custom types for opendtu."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import OpenDtuApiClient
    from .coordinator import OpenDtuDataUpdateCoordinator


type OpenDtuConfigEntry = ConfigEntry[OpenDtuData]


@dataclass
class OpenDtuData:
    """Data for the OpenDTU integration."""

    client: OpenDtuApiClient
    coordinator: OpenDtuDataUpdateCoordinator
    integration: Integration
