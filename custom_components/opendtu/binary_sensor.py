"""Binary sensor platform for opendtu."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.util import slugify

from .entity import OpenDtuEntity, get_inverter_device_info
from .naming import format_dtu_status_name, should_skip_dtu_status_path

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OpenDtuDataUpdateCoordinator
    from .data import OpenDtuConfigEntry


type OpenDtuBinaryValueFn = Callable[[Any], bool | None]


@dataclass(frozen=True, kw_only=True)
class OpenDtuBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Description for an OpenDTU binary sensor."""

    value_fn: OpenDtuBinaryValueFn


HINT_BINARY_SENSOR_DESCRIPTIONS = (
    OpenDtuBinarySensorEntityDescription(
        key="hints_time_sync",
        name="Time sync",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _to_bool(_get_value(data, ("hints", "time_sync"))),
    ),
    OpenDtuBinarySensorEntityDescription(
        key="hints_radio_problem",
        name="Radio problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _to_bool(_get_value(data, ("hints", "radio_problem"))),
    ),
    OpenDtuBinarySensorEntityDescription(
        key="hints_default_password",
        name="Default password",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _to_bool(_get_value(data, ("hints", "default_password"))),
    ),
    OpenDtuBinarySensorEntityDescription(
        key="hints_pin_mapping_issue",
        name="Pin mapping issue",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _to_bool(
            _get_value(data, ("hints", "pin_mapping_issue"))
        ),
    ),
)

INVERTER_BINARY_SENSOR_DESCRIPTIONS = (
    OpenDtuBinarySensorEntityDescription(
        key="poll_enabled",
        name="Poll enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _to_bool(_get_value(data, ("poll_enabled",))),
    ),
    OpenDtuBinarySensorEntityDescription(
        key="reachable",
        name="Reachable",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _to_bool(_get_value(data, ("reachable",))),
    ),
    OpenDtuBinarySensorEntityDescription(
        key="producing",
        name="Producing",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _to_bool(_get_value(data, ("producing",))),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: OpenDtuConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    async_add_entities(
        OpenDtuHintBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in HINT_BINARY_SENSOR_DESCRIPTIONS
    )
    async_add_entities(
        OpenDtuHintBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in _get_dtu_status_binary_sensor_descriptions(
            entry.runtime_data.coordinator.data,
        )
    )

    inverters = _get_inverters(entry.runtime_data.coordinator.data)
    async_add_entities(
        OpenDtuInverterBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
            inverter_index=inverter_index,
            inverter=inverter,
        )
        for inverter_index, inverter in enumerate(inverters)
        for entity_description in INVERTER_BINARY_SENSOR_DESCRIPTIONS
    )


class OpenDtuHintBinarySensor(OpenDtuEntity, BinarySensorEntity):
    """OpenDTU hint binary sensor."""

    def __init__(
        self,
        coordinator: OpenDtuDataUpdateCoordinator,
        entity_description: OpenDtuBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._value_fn = entity_description.value_fn
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._value_fn(self.coordinator.data)


class OpenDtuInverterBinarySensor(OpenDtuEntity, BinarySensorEntity):
    """OpenDTU inverter binary sensor."""

    def __init__(
        self,
        coordinator: OpenDtuDataUpdateCoordinator,
        entity_description: OpenDtuBinarySensorEntityDescription,
        inverter_index: int,
        inverter: Any,
    ) -> None:
        """Initialize the binary sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._value_fn = entity_description.value_fn
        self._inverter_index = inverter_index
        self._attr_device_info = get_inverter_device_info(
            coordinator,
            inverter_index,
            inverter,
        )
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_inverter_"
            f"{_get_inverter_identifier(inverter, inverter_index)}_"
            f"{entity_description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        inverter = _get_inverter(self.coordinator.data, self._inverter_index)
        if inverter is None:
            return None
        return self._value_fn(inverter)


def _get_value(data: Any, path: tuple[str | int, ...]) -> Any:
    """Return a nested value from OpenDTU API data."""
    value = data
    for part in path:
        if isinstance(part, int):
            if not isinstance(value, list) or len(value) <= part:
                return None
            value = value[part]
            continue

        if not isinstance(value, dict):
            return None
        value = value.get(part)

    return value


def _get_dtu_status_binary_sensor_descriptions(
    data: Any,
) -> list[OpenDtuBinarySensorEntityDescription]:
    """Return binary sensor descriptions for DTU status endpoint values."""
    descriptions: list[OpenDtuBinarySensorEntityDescription] = []
    status_data = _get_value(data, ("_status",))
    if not isinstance(status_data, dict):
        return descriptions

    for endpoint in sorted(status_data):
        endpoint_data = status_data[endpoint]
        for path, value in _iter_scalar_values(endpoint_data):
            if should_skip_dtu_status_path(str(endpoint), path):
                continue
            if not isinstance(value, bool):
                continue

            full_path = ("_status", str(endpoint), *path)
            descriptions.append(
                OpenDtuBinarySensorEntityDescription(
                    key=slugify(f"dtu_status_{endpoint}_{'_'.join(path)}"),
                    name=format_dtu_status_name(str(endpoint), path),
                    entity_category=EntityCategory.DIAGNOSTIC,
                    entity_registry_enabled_default=False,
                    value_fn=lambda data, value_path=full_path: _to_bool(
                        _get_value(data, value_path),
                    ),
                )
            )

    return descriptions


def _to_bool(value: Any) -> bool | None:
    """Convert OpenDTU API values to a boolean state."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.casefold()
        if normalized in {"true", "on", "1"}:
            return True
        if normalized in {"false", "off", "0"}:
            return False
    return None


def _get_inverters(data: Any) -> list[Any]:
    """Return inverter data from OpenDTU API data."""
    inverters = _get_value(data, ("inverters",))
    if isinstance(inverters, list):
        return inverters
    return []


def _get_inverter(data: Any, inverter_index: int) -> Any:
    """Return a single inverter from OpenDTU API data."""
    inverters = _get_inverters(data)
    if len(inverters) <= inverter_index:
        return None
    return inverters[inverter_index]


def _get_inverter_identifier(inverter: Any, inverter_index: int) -> str:
    """Return a stable identifier for an inverter entity."""
    serial = _get_value(inverter, ("serial",))
    if serial not in (None, ""):
        return str(serial)
    return str(inverter_index)


def _iter_scalar_values(
    data: Any,
    prefix: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], Any]]:
    """Return scalar values from nested OpenDTU status data."""
    values: list[tuple[tuple[str, ...], Any]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            values.extend(_iter_scalar_values(value, (*prefix, str(key))))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            values.extend(_iter_scalar_values(value, (*prefix, str(index))))
    else:
        values.append((prefix, data))
    return values
