"""Sensor platform for opendtu."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription

from .entity import OpenDtuEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OpenDtuDataUpdateCoordinator
    from .data import OpenDtuConfigEntry

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="opendtu",
        name="OpenDTU Status",
        icon="mdi:solar-power",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: OpenDtuConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        OpenDtuSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class OpenDtuSensor(OpenDtuEntity, SensorEntity):
    """opendtu Sensor class."""

    def __init__(
        self,
        coordinator: OpenDtuDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        if self.coordinator.data:
            return "online"
        return None
