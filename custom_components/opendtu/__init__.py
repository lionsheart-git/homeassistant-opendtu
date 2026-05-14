"""
Custom integration to integrate opendtu with Home Assistant.

For more details about this integration, please refer to
https://github.com/pg/homeassistant-opendtu
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import OpenDtuApiClient
from .const import (
    CONF_DIAGNOSTIC_SCAN_INTERVAL,
    DEFAULT_DIAGNOSTIC_SCAN_INTERVAL_SECONDS,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    LOGGER,
)
from .coordinator import OpenDtuDataUpdateCoordinator
from .data import OpenDtuData
from .entity import get_dtu_hostname

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import OpenDtuConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: OpenDtuConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = OpenDtuDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(
            seconds=entry.options.get(
                CONF_SCAN_INTERVAL,
                DEFAULT_SCAN_INTERVAL_SECONDS,
            ),
        ),
        diagnostic_update_interval=timedelta(
            seconds=entry.options.get(
                CONF_DIAGNOSTIC_SCAN_INTERVAL,
                DEFAULT_DIAGNOSTIC_SCAN_INTERVAL_SECONDS,
            ),
        ),
    )
    entry.runtime_data = OpenDtuData(
        client=OpenDtuApiClient(
            host=entry.data[CONF_HOST],
            session=async_get_clientsession(hass),
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()
    if (
        hostname := get_dtu_hostname(coordinator.data)
    ) is not None and entry.title != hostname:
        hass.config_entries.async_update_entry(entry, title=hostname)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: OpenDtuConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: OpenDtuConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
