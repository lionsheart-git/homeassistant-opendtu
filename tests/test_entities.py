"""Tests for OpenDTU entity descriptions."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from homeassistant.const import EntityCategory

from custom_components.opendtu.binary_sensor import (
    HINT_BINARY_SENSOR_DESCRIPTIONS,
    INVERTER_BINARY_SENSOR_DESCRIPTIONS,
    _get_dtu_status_binary_sensor_descriptions,
)
from custom_components.opendtu.entity import (
    get_dtu_device_info,
    get_dtu_hostname,
    get_inverter_device_info,
)
from custom_components.opendtu.sensor import (
    INVERTER_SENSOR_DESCRIPTIONS,
    TOTAL_SENSOR_DESCRIPTIONS,
    _get_dtu_status_sensor_descriptions,
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


def test_dtu_status_sensors_are_generated_from_scalar_values() -> None:
    """Test dynamic DTU status endpoint sensor generation."""
    long_certificate = "cert. version: 3\n" + ("x" * 300)
    descriptions = _get_dtu_status_sensor_descriptions(
        {
            "_status": {
                "network": {
                    "hostname": "opendtu",
                    "mac": "AA:BB:CC:DD:EE:FF",
                    "wifi_rssi": -60,
                    "connected": True,
                },
                "system": {
                    "chipmodel": "ESP32-D0WDQ6",
                    "chiprevision": 1,
                    "git_hash": "abc1234",
                    "uptime": 123,
                    "nested": {"version": "v25.2.3"},
                    "task_details": [
                        {
                            "name": "loop",
                            "priority": 1,
                            "stack_watermark": 2048,
                        },
                    ],
                },
                "power": {
                    "112184742793": {"power_set_status": "Ok"},
                },
                "mqtt": {
                    "mqtt_root_ca_cert_info": long_certificate,
                },
            },
        },
    )

    by_key = {description.key: description for description in descriptions}

    assert by_key["dtu_status_mqtt_mqtt_root_ca_cert_info"].name == (
        "MQTT Root CA Cert Info"
    )
    assert by_key["dtu_status_power_112184742793_power_set_status"].name == (
        "Power Inverter 112184742793 Set Status"
    )
    assert by_key["dtu_status_network_wifi_rssi"].native_unit_of_measurement == "dBm"
    assert by_key["dtu_status_system_uptime"].native_unit_of_measurement == "s"
    assert by_key["dtu_status_system_nested_version"].name == "System Nested Version"
    assert "dtu_status_network_hostname" not in by_key
    assert "dtu_status_network_mac" not in by_key
    assert "dtu_status_system_chipmodel" not in by_key
    assert "dtu_status_system_chiprevision" not in by_key
    assert "dtu_status_system_git_hash" not in by_key
    assert "dtu_status_system_task_details_0_name" not in by_key
    assert "dtu_status_system_task_details_0_priority" not in by_key
    assert "dtu_status_system_task_details_0_stack_watermark" not in by_key
    assert (
        by_key["dtu_status_power_112184742793_power_set_status"].value_fn(
            {"_status": {"power": {"112184742793": {"power_set_status": "Ok"}}}},
        )
        == "Ok"
    )
    assert by_key["dtu_status_power_112184742793_power_set_status"].device_class is None
    assert (
        by_key[
            "dtu_status_power_112184742793_power_set_status"
        ].native_unit_of_measurement
        is None
    )
    assert (
        by_key["dtu_status_mqtt_mqtt_root_ca_cert_info"].value_fn(
            {"_status": {"mqtt": {"mqtt_root_ca_cert_info": long_certificate}}},
        )
        == "available"
    )
    assert by_key["dtu_status_mqtt_mqtt_root_ca_cert_info"].attr_fn is not None
    assert by_key["dtu_status_mqtt_mqtt_root_ca_cert_info"].attr_fn(
        {"_status": {"mqtt": {"mqtt_root_ca_cert_info": long_certificate}}},
    ) == {"value": long_certificate}
    assert "dtu_status_network_connected" not in by_key


def test_dtu_status_binary_sensors_are_generated_from_boolean_values() -> None:
    """Test dynamic DTU status endpoint binary sensor generation."""
    descriptions = _get_dtu_status_binary_sensor_descriptions(
        {
            "_status": {
                "mqtt": {
                    "mqtt_connected": True,
                    "hostname": "broker",
                },
                "ntp": {
                    "ntp_server_reachable": False,
                },
                "system": {
                    "task_details": [
                        {
                            "running": True,
                        },
                    ],
                },
            },
        },
    )

    by_key = {description.key: description for description in descriptions}

    assert by_key["dtu_status_mqtt_mqtt_connected"].name == "MQTT Connected"
    assert (
        by_key["dtu_status_mqtt_mqtt_connected"].entity_registry_enabled_default
        is False
    )
    assert by_key["dtu_status_mqtt_mqtt_connected"].value_fn(
        {"_status": {"mqtt": {"mqtt_connected": True}}},
    )
    assert by_key["dtu_status_ntp_ntp_server_reachable"].name == "NTP Server Reachable"
    assert "dtu_status_system_task_details_0_running" not in by_key
    assert "dtu_status_mqtt_hostname" not in by_key


def test_dtu_device_name_uses_network_hostname() -> None:
    """Test the OpenDTU device uses metadata from status endpoints."""
    coordinator = SimpleNamespace(
        config_entry=SimpleNamespace(
            domain="opendtu",
            entry_id="entry-id",
            data={"host": "opendtu.local"},
        ),
        data={
            "_status": {
                "network": {
                    "hostname": "balcony-dtu",
                    "mac": "AA:BB:CC:DD:EE:FF",
                },
                "system": {
                    "chipmodel": "ESP32-D0WDQ6",
                    "chiprevision": 1,
                    "git_hash": "abc1234",
                    "pioenv": "opendtu-generic",
                    "serial": "123456789012",
                },
            },
        },
    )

    device_info = get_dtu_device_info(cast("Any", coordinator))

    assert device_info["name"] == "balcony-dtu"
    assert device_info["connections"] == {("mac", "AA:BB:CC:DD:EE:FF")}
    assert device_info["model"] == "ESP32-D0WDQ6"
    assert device_info["hw_version"] == "Chip revision 1"
    assert device_info["sw_version"] == "abc1234"
    assert device_info["model_id"] == "opendtu-generic"
    assert device_info["serial_number"] == "123456789012"


def test_dtu_hostname_supports_network_status_variants() -> None:
    """Test OpenDTU hostname extraction supports common network API shapes."""
    assert (
        get_dtu_hostname(
            {"_status": {"network": {"network_hostname": "OpenDTU-D22630"}}}
        )
        == "OpenDTU-D22630"
    )
    assert get_dtu_hostname({"network": {"hostname": "OpenDTU-D22630"}}) == (
        "OpenDTU-D22630"
    )


def test_inverter_device_name_uses_stable_serial() -> None:
    """Test inverter devices use serial-based names and API hardware metadata."""
    coordinator = SimpleNamespace(
        config_entry=SimpleNamespace(domain="opendtu", entry_id="entry-id"),
    )

    device_info = get_inverter_device_info(
        cast("Any", coordinator),
        0,
        {
            "serial": "112184742793",
            "name": "Balcony west",
            "type": "HM-600-2T",
            "device": {
                "fwbuildversion": "1.2.3",
                "hwpartnumber": "PN-123",
                "hwversion": "2.0",
            },
        },
    )

    assert device_info["name"] == "Inverter 112184742793"
    assert device_info["manufacturer"] == "Hoymiles"
    assert device_info["model"] == "HM-600-2T"
    assert device_info["model_id"] == "PN-123"
    assert device_info["hw_version"] == "2.0"
    assert device_info["sw_version"] == "1.2.3"
    assert device_info["serial_number"] == "112184742793"


def test_inverter_device_model_falls_back_to_serial_family() -> None:
    """Test inverter model metadata falls back to conservative serial prefixes."""
    coordinator = SimpleNamespace(
        config_entry=SimpleNamespace(domain="opendtu", entry_id="entry-id"),
    )

    device_info = get_inverter_device_info(
        cast("Any", coordinator),
        0,
        {"serial": "116412345678", "type": "Unknown"},
    )

    assert device_info["manufacturer"] == "Hoymiles"
    assert device_info["model"] == "HMS-1600/1800/2000-4T"


def test_ambiguous_inverter_serial_prefix_does_not_guess_manufacturer() -> None:
    """Test shared serial prefixes avoid incorrect manufacturer metadata."""
    coordinator = SimpleNamespace(
        config_entry=SimpleNamespace(domain="opendtu", entry_id="entry-id"),
    )

    device_info = get_inverter_device_info(
        cast("Any", coordinator),
        0,
        {"serial": "112112345678", "type": "Unknown"},
    )

    assert "manufacturer" not in device_info
    assert device_info["model"] == "HM/SOL/TSOL 1T series"


def test_hm_inverter_serial_format_uses_opendtu_range_logic() -> None:
    """Test HM-family serial formats beyond fixed first-four prefixes."""
    coordinator = SimpleNamespace(
        config_entry=SimpleNamespace(domain="opendtu", entry_id="entry-id"),
    )

    device_info = get_inverter_device_info(
        cast("Any", coordinator),
        0,
        {"serial": "12ff12345678", "type": "Unknown"},
    )

    assert device_info["manufacturer"] == "Hoymiles"
    assert device_info["model"] == "HM-300/350/400-1T"


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
