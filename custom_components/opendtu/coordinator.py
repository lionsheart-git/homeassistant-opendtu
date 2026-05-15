"""
Home Assistant data coordinator for OpenDTU.

The coordinator separates fast live-data updates from slower diagnostic
updates. This keeps production sensors responsive without polling every
diagnostic endpoint on each refresh.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OpenDtuApiClientAuthenticationError,
    OpenDtuApiClientError,
)

if TYPE_CHECKING:
    from logging import Logger

    from homeassistant.core import HomeAssistant

    from .data import OpenDtuConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class OpenDtuDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinate OpenDTU polling for all entities in one config entry."""

    config_entry: OpenDtuConfigEntry
    _last_diagnostic_update: datetime | None

    def __init__(
        self,
        *,
        hass: HomeAssistant,
        logger: Logger,
        name: str,
        update_interval: timedelta,
        diagnostic_update_interval: timedelta,
    ) -> None:
        """
        Initialize the coordinator.

        Args:
            hass: Home Assistant instance.
            logger: Logger used by `DataUpdateCoordinator`.
            name: Coordinator name shown in Home Assistant logs.
            update_interval: Live-data polling interval.
            diagnostic_update_interval: Optional diagnostics polling interval.

        """
        super().__init__(
            hass=hass,
            logger=logger,
            name=name,
            update_interval=update_interval,
        )
        self._diagnostic_update_interval = diagnostic_update_interval
        self._last_diagnostic_update = None

    async def _async_update_data(self) -> Any:
        """
        Fetch a fresh coordinator payload.

        Returns:
            OpenDTU data for the current update. Diagnostic payloads are either
            refreshed or carried forward from the previous update.

        Raises:
            ConfigEntryAuthFailed: OpenDTU rejected authentication for a
                required endpoint.
            UpdateFailed: A required OpenDTU endpoint could not be refreshed.

        """
        include_diagnostics = self._should_update_diagnostics()
        try:
            data = await self.config_entry.runtime_data.client.async_get_data(
                include_diagnostics=include_diagnostics,
            )
        except OpenDtuApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except OpenDtuApiClientError as exception:
            raise UpdateFailed(exception) from exception

        if include_diagnostics:
            self._last_diagnostic_update = datetime.now(UTC)
        else:
            _merge_previous_diagnostics(data, self.data)
        return data

    def _should_update_diagnostics(self) -> bool:
        """
        Return whether diagnostics should be refreshed on this update.

        Returns:
            `True` for the first update and whenever the diagnostic interval has
            elapsed.

        """
        if self.data is None or self._last_diagnostic_update is None:
            return True
        return (
            datetime.now(UTC) - self._last_diagnostic_update
            >= self._diagnostic_update_interval
        )


def _merge_previous_diagnostics(data: Any, previous_data: Any) -> None:
    """
    Carry diagnostics forward when this update only refreshed live data.

    Args:
        data: New mutable live-data response.
        previous_data: Previous coordinator payload that may contain diagnostic
            fields.

    """
    if not isinstance(data, dict) or not isinstance(previous_data, dict):
        return

    if "_status" in previous_data:
        data["_status"] = previous_data["_status"]

    previous_inverters = _get_inverters_by_serial(previous_data)
    inverters = data.get("inverters")
    if not isinstance(inverters, list):
        return

    for inverter in inverters:
        if not isinstance(inverter, dict):
            continue
        previous_inverter = previous_inverters.get(str(inverter.get("serial")))
        if previous_inverter is None:
            continue
        for key in ("_eventlog", "_limit_status"):
            if key in previous_inverter:
                inverter[key] = previous_inverter[key]


def _get_inverters_by_serial(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Return inverter data keyed by serial.

    Args:
        data: Coordinator payload containing an optional `inverters` list.

    Returns:
        Dict keyed by stringified inverter serial.

    """
    inverters = data.get("inverters")
    if not isinstance(inverters, list):
        return {}
    return {
        str(inverter["serial"]): inverter
        for inverter in inverters
        if isinstance(inverter, dict) and inverter.get("serial") is not None
    }
