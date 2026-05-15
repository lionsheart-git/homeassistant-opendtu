"""
Runtime data types for the OpenDTU integration.

Home Assistant stores this dataclass on each config entry so platforms can
access the API client, coordinator, and loaded integration metadata without
global state.
"""

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
    """
    Runtime data attached to an OpenDTU config entry.

    Attributes:
        client: OpenDTU REST API client for this config entry.
        coordinator: Shared data update coordinator for all entities.
        integration: Loaded Home Assistant integration metadata.

    """

    client: OpenDtuApiClient
    coordinator: OpenDtuDataUpdateCoordinator
    integration: Integration
