"""OpenDTUEntity class."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import OpenDtuDataUpdateCoordinator

INVERTER_MODEL_PREFIXES: tuple[tuple[tuple[str, ...], str | None, str], ...] = (
    (("1361",), "Hoymiles", "HMT-1600/1800/2000-4T"),
    (("1382",), "Hoymiles", "HMT-1800/2250-6T"),
    (("1164", "1166", "1420"), "Hoymiles", "HMS-1600/1800/2000-4T"),
    (("1143", "1144", "114a", "1410"), "Hoymiles", "HMS-600/700/800/900/1000-2T"),
    (("1125", "1400"), "Hoymiles", "HMS-450/500-1T v2"),
    (("1124",), "Hoymiles", "HMS-300/350/400/450/500-1T"),
    (("2841",), "E-Star", "HERF-300-1T"),
    (("2821",), "E-Star", "HERF-600/800-2T"),
    (("2801",), "E-Star", "HERF-1600/1800-4T"),
    (("1121", "1022"), None, "HM/SOL/TSOL 1T series"),
    (("1141", "1042"), None, "HM/SOL/TSOL 2T series"),
    (("1161", "1062"), None, "HM/TSOL 4T series"),
    (("12",), "Hoymiles", "HM-300/350/400-1T"),
    (("14",), "Hoymiles", "HM-600/700/800-2T"),
    (("16",), "Hoymiles", "HM-1000/1200/1500-4T"),
)


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
    identifier = serial or f"{coordinator.config_entry.entry_id}_{inverter_index}"
    model = _get_inverter_model(inverter, serial)
    manufacturer = _get_inverter_manufacturer(model, serial)

    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"inverter_{identifier}")},
        name=_get_inverter_device_name(serial, inverter_index),
        via_device=get_dtu_device_identifier(coordinator),
    )
    if manufacturer is not None:
        device_info["manufacturer"] = manufacturer
    if model is not None:
        device_info["model"] = model
    if serial is not None:
        device_info["serial_number"] = serial
    if (model_id := _get_inverter_model_id(inverter)) is not None:
        device_info["model_id"] = model_id
    if (hw_version := _get_inverter_hw_version(inverter)) is not None:
        device_info["hw_version"] = hw_version
    if (sw_version := _get_inverter_sw_version(inverter)) is not None:
        device_info["sw_version"] = sw_version

    return device_info


def get_dtu_device_info(coordinator: OpenDtuDataUpdateCoordinator) -> DeviceInfo:
    """Return device info for the OpenDTU itself."""
    device_info = DeviceInfo(
        identifiers={get_dtu_device_identifier(coordinator)},
        name=get_dtu_hostname(coordinator.data) or "OpenDTU",
        manufacturer="OpenDTU",
        configuration_url=_get_configuration_url(coordinator),
    )
    if (mac_address := _get_dtu_mac_address(coordinator.data)) is not None:
        device_info["connections"] = {(CONNECTION_NETWORK_MAC, mac_address)}
    if (serial_number := _get_dtu_serial_number(coordinator.data)) is not None:
        device_info["serial_number"] = serial_number
    if (chip_model := _get_dtu_chip_model(coordinator.data)) is not None:
        device_info["model"] = chip_model
    if (chip_revision := _get_dtu_chip_revision(coordinator.data)) is not None:
        device_info["hw_version"] = f"Chip revision {chip_revision}"
    if (sw_version := _get_dtu_sw_version(coordinator.data)) is not None:
        device_info["sw_version"] = sw_version
    if (model_id := _get_dtu_model_id(coordinator.data)) is not None:
        device_info["model_id"] = model_id

    return device_info


def get_dtu_hostname(data: Any) -> str | None:
    """Return the hostname from the OpenDTU network status data."""
    hostname = _get_first_value(
        data,
        (
            ("_status", "network", "hostname"),
            ("_status", "network", "network_hostname"),
            ("_status", "network", "ap_hostname"),
            ("_status", "network", "host_name"),
            ("network", "hostname"),
            ("network", "network_hostname"),
            ("hostname",),
        ),
    )
    if hostname in (None, ""):
        return None
    return str(hostname)


def _get_dtu_mac_address(data: Any) -> str | None:
    """Return the network MAC address from OpenDTU status data."""
    return _get_first_string_value(
        data,
        (
            ("_status", "network", "mac"),
            ("_status", "network", "mac_address"),
            ("_status", "network", "wifi_mac"),
            ("_status", "network", "sta_mac"),
            ("_status", "system", "mac"),
            ("network", "mac"),
            ("network", "mac_address"),
        ),
    )


def _get_dtu_serial_number(data: Any) -> str | None:
    """Return the DTU serial number from OpenDTU status data."""
    return _get_first_string_value(
        data,
        (
            ("_status", "system", "dtu_serial"),
            ("_status", "system", "dtu_serial_number"),
            ("_status", "system", "serial_number"),
            ("_status", "system", "serial"),
            ("_status", "power", "serial"),
        ),
    )


def _get_dtu_chip_model(data: Any) -> str | None:
    """Return the OpenDTU chip model."""
    return _get_first_string_value(
        data,
        (
            ("_status", "system", "chipmodel"),
            ("_status", "system", "chip_model"),
            ("_status", "system", "chip", "model"),
        ),
    )


def _get_dtu_chip_revision(data: Any) -> str | None:
    """Return the OpenDTU chip revision."""
    return _get_first_string_value(
        data,
        (
            ("_status", "system", "chiprevision"),
            ("_status", "system", "chip_revision"),
            ("_status", "system", "chip", "revision"),
        ),
    )


def _get_dtu_sw_version(data: Any) -> str | None:
    """Return the OpenDTU firmware version."""
    return _get_first_string_value(
        data,
        (
            ("_status", "system", "firmware_version"),
            ("_status", "system", "sw_version"),
            ("_status", "system", "version"),
            ("_status", "system", "git_hash"),
        ),
    )


def _get_dtu_model_id(data: Any) -> str | None:
    """Return the OpenDTU firmware environment or board identifier."""
    return _get_first_string_value(
        data,
        (
            ("_status", "system", "pioenv"),
            ("_status", "system", "pio_environment"),
            ("_status", "system", "board"),
        ),
    )


class OpenDtuEntity(CoordinatorEntity[OpenDtuDataUpdateCoordinator]):
    """OpenDTUEntity class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: OpenDtuDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id
        self._attr_device_info = get_dtu_device_info(coordinator)


def _get_configuration_url(coordinator: OpenDtuDataUpdateCoordinator) -> str:
    """Return the configured OpenDTU web UI URL."""
    host = coordinator.config_entry.data[CONF_HOST].strip()
    if host.startswith(("http://", "https://")):
        return host.rstrip("/")
    return f"http://{host}".rstrip("/")


def _get_inverter_device_name(serial: str | None, inverter_index: int) -> str:
    """Return a stable user-facing inverter device name."""
    if serial is not None:
        return f"Inverter {serial}"
    return f"Inverter {inverter_index + 1}"


def _get_inverter_model(inverter: Any, serial: str | None) -> str | None:
    """Return the inverter model from API data or serial prefix."""
    model = _get_first_string_value(
        inverter,
        (
            ("type",),
            ("model",),
            ("device", "type"),
            ("device", "model"),
            ("device", "model_name"),
        ),
    )
    if model not in (None, "Unknown"):
        return model
    return _get_inverter_model_from_serial(serial)


def _get_inverter_manufacturer(model: str | None, serial: str | None) -> str | None:
    """Return the inverter manufacturer from model or serial prefix."""
    if model is not None:
        model_key = model.casefold()
        if model_key.startswith(("hm-", "hms-", "hmt-")):
            return "Hoymiles"
        if model_key.startswith(("tsol-", "tsun")):
            return "TSUN"
        if model_key.startswith(("sol-", "solenso")):
            return "Solenso"
        if model_key.startswith(("herf-", "e-star")):
            return "E-Star"

    if serial is not None:
        serial_key = serial.casefold()
        for prefixes, manufacturer, _model in INVERTER_MODEL_PREFIXES:
            if serial_key.startswith(prefixes):
                return manufacturer
    return None


def _get_inverter_model_from_serial(serial: str | None) -> str | None:
    """Return a conservative inverter model family from the serial prefix."""
    if serial is None:
        return None
    serial_key = serial.casefold()
    for prefixes, _manufacturer, model in INVERTER_MODEL_PREFIXES:
        if serial_key.startswith(prefixes):
            return model
    return None


def _get_inverter_model_id(inverter: Any) -> str | None:
    """Return the inverter hardware part number."""
    return _get_first_string_value(
        inverter,
        (
            ("device", "hwpartnumber"),
            ("device", "hw_part_number"),
            ("hwpartnumber",),
            ("hw_part_number",),
        ),
    )


def _get_inverter_hw_version(inverter: Any) -> str | None:
    """Return the inverter hardware version."""
    return _get_first_string_value(
        inverter,
        (
            ("device", "hwversion"),
            ("device", "hw_version"),
            ("hwversion",),
            ("hw_version",),
        ),
    )


def _get_inverter_sw_version(inverter: Any) -> str | None:
    """Return the inverter firmware version."""
    return _get_first_string_value(
        inverter,
        (
            ("device", "fwbuildversion"),
            ("device", "fw_build_version"),
            ("fwbuildversion",),
            ("fw_build_version",),
        ),
    )


def _get_value(data: Any, path: tuple[str, ...]) -> Any:
    """Return a nested value from OpenDTU API data."""
    value = data
    for part in path:
        if not isinstance(value, dict):
            return None
        value = _get_dict_value(value, part)
    return value


def _get_first_value(data: Any, paths: tuple[tuple[str, ...], ...]) -> Any:
    """Return the first available nested value from OpenDTU API data."""
    for path in paths:
        value = _get_value(data, path)
        if value not in (None, ""):
            return value
    return None


def _get_first_string_value(
    data: Any, paths: tuple[tuple[str, ...], ...]
) -> str | None:
    """Return the first available value as a string."""
    value = _get_first_value(data, paths)
    if value in (None, ""):
        return None
    return str(value)


def _get_dict_value(data: dict[str, Any], key: str) -> Any:
    """Return a dict value using exact or normalized key matching."""
    if key in data:
        return data[key]
    normalized_key = _normalize_key(key)
    for data_key, value in data.items():
        if _normalize_key(str(data_key)) == normalized_key:
            return value
    return None


def _normalize_key(value: str) -> str:
    """Normalize OpenDTU API key variants for metadata extraction."""
    return "".join(character for character in value.casefold() if character.isalnum())


def _get_inverter_value(inverter: Any, key: str) -> str | None:
    """Return a string value from inverter data."""
    if not isinstance(inverter, dict):
        return None
    value = inverter.get(key)
    if value in (None, ""):
        return None
    return str(value)
