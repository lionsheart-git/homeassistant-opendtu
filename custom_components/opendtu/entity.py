"""OpenDTUEntity class."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import OpenDtuDataUpdateCoordinator


def get_dtu_device_identifier(
    coordinator: OpenDtuDataUpdateCoordinator,
) -> tuple[str, str]:
    """Return the OpenDTU device identifier."""
    return (coordinator.config_entry.domain, coordinator.config_entry.entry_id)


def get_inverter_device_info(
    coordinator: OpenDtuDataUpdateCoordinator,
    inverter_index: int,
    inverter: Any,
) -> DeviceInfo:
    """Return device info for an inverter."""
    serial = _get_inverter_value(inverter, "serial")
    inverter_name = _get_inverter_value(inverter, "name")
    identifier = serial or f"{coordinator.config_entry.entry_id}_{inverter_index}"

    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"inverter_{identifier}")},
        name=inverter_name or f"Inverter {inverter_index + 1}",
        via_device=get_dtu_device_identifier(coordinator),
    )
    if serial is not None:
        device_info["serial_number"] = serial

    return device_info


class OpenDtuEntity(CoordinatorEntity[OpenDtuDataUpdateCoordinator]):
    """OpenDTUEntity class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: OpenDtuDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={get_dtu_device_identifier(coordinator)},
            name="OpenDTU",
            manufacturer="OpenDTU",
            configuration_url=_get_configuration_url(coordinator),
        )


def _get_configuration_url(coordinator: OpenDtuDataUpdateCoordinator) -> str:
    """Return the configured OpenDTU web UI URL."""
    host = coordinator.config_entry.data[CONF_HOST].strip()
    if host.startswith(("http://", "https://")):
        return host.rstrip("/")
    return f"http://{host}".rstrip("/")


def _get_inverter_value(inverter: Any, key: str) -> str | None:
    """Return a string value from inverter data."""
    if not isinstance(inverter, dict):
        return None
    value = inverter.get(key)
    if value in (None, ""):
        return None
    return str(value)
