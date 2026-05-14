"""Tests for OpenDTU entity descriptions."""

from __future__ import annotations

from homeassistant.const import EntityCategory

from custom_components.opendtu.binary_sensor import (
    HINT_BINARY_SENSOR_DESCRIPTIONS,
    INVERTER_BINARY_SENSOR_DESCRIPTIONS,
)
from custom_components.opendtu.sensor import (
    INVERTER_SENSOR_DESCRIPTIONS,
    TOTAL_SENSOR_DESCRIPTIONS,
    _get_inverter_measurement_descriptions,
)


def test_total_sensor_values_are_rounded() -> None:
    """Test total sensor value extraction and display precision."""
    data = {
        "total": {
            "Power": {"v": 123.456, "u": "W", "d": 1},
            "YieldDay": {"v": 789.9, "u": "Wh", "d": 0},
            "YieldTotal": {"v": 12.34567, "u": "kWh", "d": 3},
        },
    }

    values = {
        description.key: description.value_fn(data)
        for description in TOTAL_SENSOR_DESCRIPTIONS
    }

    assert values == {
        "total_power": 123.5,
        "total_yield_day": 790,
        "total_yield_total": 12.346,
    }


def test_single_dc_channel_has_plain_friendly_names() -> None:
    """Test that a single DC string does not add noisy channel labels."""
    descriptions = _get_inverter_measurement_descriptions(
        {
            "DC": {
                "0": {
                    "Current": {"v": 1.23, "u": "A", "d": 2},
                    "Power": {"v": 120.1, "u": "W", "d": 1},
                    "YieldTotal": {"v": 12.345, "u": "kWh", "d": 3},
                },
            },
        },
    )

    assert [description.name for description in descriptions] == [
        "Current",
        "Power",
        "Yield total",
    ]


def test_multiple_dc_channels_are_disambiguated() -> None:
    """Test that multiple DC strings retain string numbers."""
    descriptions = _get_inverter_measurement_descriptions(
        {
            "DC": {
                "0": {"Power": {"v": 100, "u": "W", "d": 1}},
                "1": {"Power": {"v": 110, "u": "W", "d": 1}},
            },
        },
    )

    assert [description.name for description in descriptions] == [
        "String 1 Power",
        "String 2 Power",
    ]


def test_measurement_descriptions_set_home_assistant_metadata() -> None:
    """Test generated sensors have useful HA metadata and values."""
    descriptions = _get_inverter_measurement_descriptions(
        {
            "AC": {
                "0": {
                    "Power": {"v": 123.456, "u": "W", "d": 1},
                    "PowerFactor": {"v": 0.9876, "u": "", "d": 3},
                },
            },
            "INV": {
                "0": {
                    "Temperature": {"v": 42.22, "u": "°C", "d": 1},
                },
            },
        },
    )

    by_key = {description.key: description for description in descriptions}

    assert by_key["ac_0_power"].name == "AC Power"
    assert by_key["ac_0_power"].native_unit_of_measurement == "W"
    assert (
        by_key["ac_0_power"].value_fn({"AC": {"0": {"Power": {"v": 123.456}}}}) == 123.5
    )
    assert by_key["ac_0_powerfactor"].name == "AC Power factor"
    assert by_key["inv_0_temperature"].name == "Inverter Temperature"


def test_read_only_entities_are_never_config_category() -> None:
    """Test read-only entities avoid invalid config category."""
    descriptions = (
        *TOTAL_SENSOR_DESCRIPTIONS,
        *INVERTER_SENSOR_DESCRIPTIONS,
        *HINT_BINARY_SENSOR_DESCRIPTIONS,
        *INVERTER_BINARY_SENSOR_DESCRIPTIONS,
    )

    assert all(
        description.entity_category is not EntityCategory.CONFIG
        for description in descriptions
    )
