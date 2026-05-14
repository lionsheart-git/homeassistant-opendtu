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
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.util import slugify

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
    measurement_path: tuple[str, str, str] | None = None


INVERTER_MEASUREMENT_GROUPS = ("AC", "DC", "INV")
MEASUREMENT_NAMES = {
    "Efficiency": "Efficiency",
    "Frequency": "Frequency",
    "Irradiation": "Irradiation",
    "Power DC": "DC power",
    "PowerFactor": "Power factor",
    "ReactivePower": "Reactive power",
    "Temperature": "Temperature",
    "YieldDay": "Yield day",
    "YieldTotal": "Yield total",
}


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
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(data, ("limit_relative",)),
    ),
    OpenDtuSensorEntityDescription(
        key="limit_absolute",
        name="Limit absolute",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(data, ("limit_absolute",)),
    ),
    OpenDtuSensorEntityDescription(
        key="max_power",
        name="Maximum power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(data, ("_limit_status", "max_power")),
    ),
    OpenDtuSensorEntityDescription(
        key="limit_set_status",
        name="Limit status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(data, ("_limit_status", "limit_set_status")),
    ),
    OpenDtuSensorEntityDescription(
        key="events",
        name="Event count",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_event_count(data),  # noqa: PLW0108
    ),
    OpenDtuSensorEntityDescription(
        key="last_event_message_id",
        name="Last event message ID",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(_get_last_event(data), ("message_id",)),
    ),
    OpenDtuSensorEntityDescription(
        key="last_event_message",
        name="Last event message",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _get_value(_get_last_event(data), ("message",)),
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
    async_add_entities(
        OpenDtuInverterSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
            inverter_index=inverter_index,
            inverter=inverter,
        )
        for inverter_index, inverter in enumerate(inverters)
        for entity_description in _get_inverter_measurement_descriptions(inverter)
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
        self._measurement_path = entity_description.measurement_path
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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes from OpenDTU measurements."""
        if self._measurement_path is None:
            return None

        inverter = _get_inverter(self.coordinator.data, self._inverter_index)
        measurement = _get_value(inverter, self._measurement_path)
        if not isinstance(measurement, dict):
            return None

        attributes = {
            key: value
            for key, value in measurement.items()
            if key not in {"v", "u", "d"}
        }
        return attributes or None


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


def _round_value(value: Any, precision: int | None) -> int | float | None:
    """Round a numeric value."""
    if not isinstance(value, int | float):
        return None
    if precision is None:
        return value
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


def _get_event_count(inverter: Any) -> int | None:
    """Return the inverter event count."""
    count = _get_value(inverter, ("_eventlog", "count"))
    if isinstance(count, int):
        return count

    events = _get_value(inverter, ("events",))
    if isinstance(events, int):
        return events
    return None


def _get_last_event(inverter: Any) -> Any:
    """Return the newest event log entry."""
    events = _get_value(inverter, ("_eventlog", "events"))
    if not isinstance(events, list) or not events:
        return None
    return events[-1]


def _get_inverter_measurement_descriptions(
    inverter: Any,
) -> list[OpenDtuSensorEntityDescription]:
    """Return sensor descriptions for detailed inverter measurements."""
    descriptions: list[OpenDtuSensorEntityDescription] = []
    for group in INVERTER_MEASUREMENT_GROUPS:
        channels = _get_value(inverter, (group,))
        if not isinstance(channels, dict):
            continue

        channel_count = len(channels)
        for channel in sorted(channels, key=_sort_channel_key):
            measurements = channels[channel]
            if not isinstance(measurements, dict):
                continue

            for metric, measurement in measurements.items():
                if not _is_measurement_value(measurement):
                    continue
                descriptions.append(
                    _get_inverter_measurement_description(
                        group=group,
                        channel=str(channel),
                        channel_count=channel_count,
                        metric=str(metric),
                        measurement=measurement,
                    )
                )

    return descriptions


def _get_inverter_measurement_description(
    group: str,
    channel: str,
    channel_count: int,
    metric: str,
    measurement: dict[str, Any],
) -> OpenDtuSensorEntityDescription:
    """Return a sensor description for an inverter measurement."""
    measurement_path = (group, channel, metric)
    precision = _get_precision(measurement)
    return OpenDtuSensorEntityDescription(
        key=slugify(f"{group}_{channel}_{metric}"),
        name=_format_measurement_entity_name(
            group=group,
            channel=channel,
            channel_count=channel_count,
            metric=metric,
        ),
        native_unit_of_measurement=_get_unit_of_measurement(measurement),
        device_class=_get_device_class(metric, measurement),
        state_class=_get_state_class(metric, measurement),
        suggested_display_precision=precision,
        value_fn=lambda data, path=measurement_path, decimals=precision: _round_value(
            _get_value(data, (*path, "v")),
            decimals,
        ),
        measurement_path=measurement_path,
    )


def _is_measurement_value(value: Any) -> bool:
    """Return whether a value is an OpenDTU measurement object."""
    return isinstance(value, dict) and "v" in value


def _get_precision(measurement: dict[str, Any]) -> int | None:
    """Return the suggested precision for a measurement."""
    precision = measurement.get("d")
    if isinstance(precision, int):
        return precision
    return None


def _get_unit_of_measurement(measurement: dict[str, Any]) -> str | None:
    """Return the Home Assistant unit for an OpenDTU measurement."""
    unit = measurement.get("u")
    if unit in (None, ""):
        return None

    return {
        "%": PERCENTAGE,
        "A": UnitOfElectricCurrent.AMPERE,
        "Hz": UnitOfFrequency.HERTZ,
        "V": UnitOfElectricPotential.VOLT,
        "W": UnitOfPower.WATT,
        "Wh": UnitOfEnergy.WATT_HOUR,
        "kWh": UnitOfEnergy.KILO_WATT_HOUR,
        "var": UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        "°C": UnitOfTemperature.CELSIUS,
    }.get(str(unit), str(unit))


def _get_device_class(
    metric: str,
    measurement: dict[str, Any],
) -> SensorDeviceClass | None:
    """Return the Home Assistant device class for an OpenDTU measurement."""
    if metric == "PowerFactor":
        return SensorDeviceClass.POWER_FACTOR

    unit = measurement.get("u")
    if not isinstance(unit, str):
        return None
    if unit in ("Wh", "kWh"):
        return SensorDeviceClass.ENERGY
    return {
        "A": SensorDeviceClass.CURRENT,
        "Hz": SensorDeviceClass.FREQUENCY,
        "V": SensorDeviceClass.VOLTAGE,
        "W": SensorDeviceClass.POWER,
        "var": SensorDeviceClass.REACTIVE_POWER,
        "°C": SensorDeviceClass.TEMPERATURE,
    }.get(unit)


def _get_state_class(
    metric: str,
    measurement: dict[str, Any],
) -> SensorStateClass | None:
    """Return the Home Assistant state class for an OpenDTU measurement."""
    if metric in {"YieldDay", "YieldTotal"}:
        return SensorStateClass.TOTAL_INCREASING
    if measurement.get("u") not in (None, ""):
        return SensorStateClass.MEASUREMENT
    if metric == "PowerFactor":
        return SensorStateClass.MEASUREMENT
    return None


def _format_measurement_name(metric: str) -> str:
    """Return a human readable measurement name."""
    return MEASUREMENT_NAMES.get(metric, metric.replace("_", " "))


def _format_measurement_entity_name(
    group: str,
    channel: str,
    channel_count: int,
    metric: str,
) -> str:
    """Return a Home Assistant friendly measurement entity name."""
    measurement_name = _format_measurement_name(metric)
    channel_number = _format_channel_number(channel)

    if group == "AC":
        prefix = "AC" if channel_count == 1 else f"AC phase {channel_number}"
    elif group == "DC":
        prefix = "" if channel_count == 1 else f"String {channel_number}"
    elif group == "INV":
        prefix = (
            "Inverter" if channel_count == 1 else f"Inverter channel {channel_number}"
        )
    else:
        prefix = group if channel_count == 1 else f"{group} {channel_number}"

    if prefix == "":
        return measurement_name
    return f"{prefix} {measurement_name}"


def _format_channel_number(channel: str) -> str:
    """Return a human readable one-based channel number."""
    if channel.isdecimal():
        return str(int(channel) + 1)
    return channel


def _sort_channel_key(value: Any) -> tuple[int, str]:
    """Sort numeric channel keys naturally."""
    value_string = str(value)
    if value_string.isdecimal():
        return (int(value_string), value_string)
    return (9999, value_string)
