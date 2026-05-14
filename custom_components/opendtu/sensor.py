"""Sensor platform for opendtu."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)

from .entity import OpenDtuEntity, get_inverter_device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OpenDtuDataUpdateCoordinator
    from .data import OpenDtuConfigEntry


type OpenDtuValueFn = Callable[[Any], int | float | str | None]


@dataclass(frozen=True, kw_only=True)
class OpenDtuSensorEntityDescription(SensorEntityDescription):
    """Description for an OpenDTU sensor."""

    value_fn: OpenDtuValueFn


TOTAL_SENSOR_DESCRIPTIONS = (
    OpenDtuSensorEntityDescription(
        key="total_power",
        name="Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: _round_value(
            _get_value(data, ("total", "Power", "v")), 1
        ),
    ),
    OpenDtuSensorEntityDescription(
        key="total_yield_day",
        name="Yield day",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda data: _round_value(
            _get_value(data, ("total", "YieldDay", "v")),
            0,
        ),
    ),
    OpenDtuSensorEntityDescription(
        key="total_yield_total",
        name="Yield total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        value_fn=lambda data: _round_value(
            _get_value(data, ("total", "YieldTotal", "v")),
            3,
        ),
    ),
)

INVERTER_SENSOR_DESCRIPTIONS = (
    OpenDtuSensorEntityDescription(
        key="serial",
        name="Serial",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(data, ("serial",)),
    ),
    OpenDtuSensorEntityDescription(
        key="name",
        name="Name",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(data, ("name",)),
    ),
    OpenDtuSensorEntityDescription(
        key="order",
        name="Order",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(data, ("order",)),
    ),
    OpenDtuSensorEntityDescription(
        key="data_age",
        name="Data age",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(data, ("data_age",)),
    ),
    OpenDtuSensorEntityDescription(
        key="limit_relative",
        name="Limit relative",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(data, ("limit_relative",)),
    ),
    OpenDtuSensorEntityDescription(
        key="limit_absolute",
        name="Limit absolute",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(data, ("limit_absolute",)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: OpenDtuConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        OpenDtuTotalSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in TOTAL_SENSOR_DESCRIPTIONS
    )

    inverters = _get_inverters(entry.runtime_data.coordinator.data)
    async_add_entities(
        OpenDtuInverterSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
            inverter_index=inverter_index,
            inverter=inverter,
        )
        for inverter_index, inverter in enumerate(inverters)
        for entity_description in INVERTER_SENSOR_DESCRIPTIONS
    )


class OpenDtuTotalSensor(OpenDtuEntity, SensorEntity):
    """OpenDTU total sensor."""

    def __init__(
        self,
        coordinator: OpenDtuDataUpdateCoordinator,
        entity_description: OpenDtuSensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._value_fn = entity_description.value_fn
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def native_value(self) -> int | float | str | None:
        """Return the native value of the sensor."""
        return self._value_fn(self.coordinator.data)


class OpenDtuInverterSensor(OpenDtuEntity, SensorEntity):
    """OpenDTU inverter sensor."""

    def __init__(
        self,
        coordinator: OpenDtuDataUpdateCoordinator,
        entity_description: OpenDtuSensorEntityDescription,
        inverter_index: int,
        inverter: Any,
    ) -> None:
        """Initialize the sensor class."""
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
    def native_value(self) -> int | float | str | None:
        """Return the native value of the sensor."""
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


def _round_value(value: Any, precision: int) -> int | float | None:
    """Round a numeric value."""
    if not isinstance(value, int | float):
        return None
    rounded = round(value, precision)
    if precision == 0:
        return int(rounded)
    return rounded


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
