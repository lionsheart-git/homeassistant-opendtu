"""Tests for the OpenDTU API client."""

from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.opendtu.api import (
    OpenDtuApiClient,
    OpenDtuApiClientAuthenticationError,
)

COMMON_STATUS = {
    "inverters": [
        {
            "serial": "123456789",
            "name": "Roof inverter",
            "order": 0,
            "data_age": 3,
            "poll_enabled": True,
            "reachable": True,
            "producing": True,
            "limit_relative": 100,
            "limit_absolute": 600,
        },
    ],
    "total": {
        "Power": {"v": 120.12, "u": "W", "d": 1},
        "YieldDay": {"v": 500, "u": "Wh", "d": 0},
        "YieldTotal": {"v": 12.345, "u": "kWh", "d": 3},
    },
    "hints": {
        "time_sync": False,
        "radio_problem": False,
        "default_password": False,
    },
}

DETAIL_STATUS = {
    "inverters": [
        {
            "serial": "123456789",
            "name": "Roof inverter",
            "AC": {
                "0": {
                    "Power": {"v": 120.12, "u": "W", "d": 1},
                    "Voltage": {"v": 230.1, "u": "V", "d": 1},
                },
            },
            "DC": {
                "0": {
                    "Current": {"v": 1.23, "u": "A", "d": 2},
                    "Power": {"v": 120.12, "u": "W", "d": 1},
                },
            },
            "INV": {
                "0": {
                    "Temperature": {"v": 42.2, "u": "°C", "d": 1},
                },
            },
            "events": 2,
        },
    ],
}


@pytest.mark.asyncio
async def test_async_get_data_enriches_inverters() -> None:
    """Test that common status is enriched with inverter detail endpoints."""
    with aioresponses() as mocked:
        mocked.get("http://opendtu.local/api/livedata/status", payload=COMMON_STATUS)
        mocked.get(
            "http://opendtu.local/api/livedata/status?inv=123456789",
            payload=DETAIL_STATUS,
        )
        mocked.get(
            "http://opendtu.local/api/limit/status",
            payload={
                "123456789": {
                    "limit_relative": 100,
                    "max_power": 600,
                    "limit_set_status": "Ok",
                },
            },
        )
        mocked.get(
            "http://opendtu.local/api/eventlog/status?inv=123456789",
            payload={
                "123456789": {
                    "count": 1,
                    "events": [
                        {
                            "message_id": 1,
                            "message": "Inverter start",
                            "start_time": 1,
                            "end_time": 1,
                        },
                    ],
                },
            },
        )

        async with aiohttp.ClientSession() as session:
            client = OpenDtuApiClient("opendtu.local", session)
            data = await client.async_get_data()

    inverter = data["inverters"][0]
    assert inverter["AC"]["0"]["Power"]["v"] == 120.12
    assert inverter["_limit_status"]["max_power"] == 600
    assert inverter["_eventlog"]["events"][0]["message"] == "Inverter start"


@pytest.mark.asyncio
async def test_optional_endpoints_do_not_fail_update() -> None:
    """Test that optional detail endpoints do not fail the main update."""
    with aioresponses() as mocked:
        mocked.get("http://opendtu.local/api/livedata/status", payload=COMMON_STATUS)
        mocked.get("http://opendtu.local/api/livedata/status?inv=123456789", status=404)
        mocked.get("http://opendtu.local/api/limit/status", status=404)
        mocked.get("http://opendtu.local/api/eventlog/status?inv=123456789", status=404)

        async with aiohttp.ClientSession() as session:
            client = OpenDtuApiClient("opendtu.local", session)
            data = await client.async_get_data()

    assert data["inverters"][0]["serial"] == "123456789"
    assert "_limit_status" not in data["inverters"][0]
    assert "_eventlog" not in data["inverters"][0]


@pytest.mark.asyncio
async def test_authentication_error_is_raised_for_common_status() -> None:
    """Test that authentication errors are raised for the required endpoint."""
    with aioresponses() as mocked:
        mocked.get("http://opendtu.local/api/livedata/status", status=401)

        async with aiohttp.ClientSession() as session:
            client = OpenDtuApiClient("opendtu.local", session)
            with pytest.raises(OpenDtuApiClientAuthenticationError):
                await client.async_get_data()
