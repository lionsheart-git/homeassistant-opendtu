"""OpenDTU API client."""

from __future__ import annotations

import asyncio
import socket
from typing import Any
from urllib.parse import quote

import aiohttp
import async_timeout


class OpenDtuApiClientError(Exception):
    """Exception to indicate a general API error."""


class OpenDtuApiClientCommunicationError(
    OpenDtuApiClientError,
):
    """Exception to indicate a communication error."""


class OpenDtuApiClientAuthenticationError(
    OpenDtuApiClientError,
):
    """Exception to indicate an authentication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise OpenDtuApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()


class OpenDtuApiClient:
    """OpenDTU API client."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the OpenDTU API client."""
        self._host = host.strip()
        self._session = session

    async def async_get_data(self) -> Any:
        """Get data from the API."""
        data = await self._api_wrapper(
            method="get",
            path="/api/livedata/status",
        )
        await asyncio.gather(
            self._add_inverter_details(data),
            self._add_limit_status(data),
            self._add_eventlogs(data),
        )
        return data

    async def _add_inverter_details(self, data: Any) -> None:
        """Add detailed inverter live data to the common status response."""
        if not isinstance(data, dict):
            return

        inverters = data.get("inverters")
        if not isinstance(inverters, list):
            return

        inverter_details = await asyncio.gather(
            *(
                self._async_get_inverter_detail(inverter)
                for inverter in inverters
                if isinstance(inverter, dict) and inverter.get("serial")
            ),
        )
        details_by_serial = {
            detail["serial"]: detail
            for detail in inverter_details
            if isinstance(detail, dict) and detail.get("serial")
        }

        for inverter in inverters:
            if not isinstance(inverter, dict):
                continue
            detail = details_by_serial.get(inverter.get("serial"))
            if detail is not None:
                inverter.update(detail)

    async def _async_get_inverter_detail(self, inverter: dict[str, Any]) -> Any:
        """Get detailed live data for a single inverter."""
        serial = str(inverter["serial"])
        data = await self._api_wrapper_optional(
            method="get",
            path=f"/api/livedata/status?inv={quote(serial)}",
        )
        if not isinstance(data, dict):
            return None

        inverters = data.get("inverters")
        if not isinstance(inverters, list) or not inverters:
            return None
        return inverters[0]

    async def _add_limit_status(self, data: Any) -> None:
        """Add limit status data to each inverter."""
        if not isinstance(data, dict):
            return

        inverters = data.get("inverters")
        if not isinstance(inverters, list):
            return

        limit_status = await self._api_wrapper_optional(
            method="get",
            path="/api/limit/status",
        )
        if not isinstance(limit_status, dict):
            return

        for inverter in inverters:
            if not isinstance(inverter, dict):
                continue
            serial = str(inverter.get("serial"))
            if serial in limit_status:
                inverter["_limit_status"] = limit_status[serial]

    async def _add_eventlogs(self, data: Any) -> None:
        """Add event log data to each inverter."""
        if not isinstance(data, dict):
            return

        inverters = data.get("inverters")
        if not isinstance(inverters, list):
            return

        eventlogs = await asyncio.gather(
            *(
                self._async_get_eventlog(inverter)
                for inverter in inverters
                if isinstance(inverter, dict) and inverter.get("serial")
            ),
        )
        eventlogs_by_serial = {
            serial: eventlog
            for serial, eventlog in eventlogs
            if serial is not None and eventlog is not None
        }

        for inverter in inverters:
            if not isinstance(inverter, dict):
                continue
            eventlog = eventlogs_by_serial.get(inverter.get("serial"))
            if eventlog is not None:
                inverter["_eventlog"] = eventlog

    async def _async_get_eventlog(
        self,
        inverter: dict[str, Any],
    ) -> tuple[str | None, Any]:
        """Get event log data for a single inverter."""
        serial = str(inverter["serial"])
        data = await self._api_wrapper_optional(
            method="get",
            path=f"/api/eventlog/status?inv={quote(serial)}",
        )
        if not isinstance(data, dict):
            return (serial, None)

        return (serial, data.get(serial))

    async def _api_wrapper(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        url = f"{self._base_url}{path}"
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise OpenDtuApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise OpenDtuApiClientCommunicationError(
                msg,
            ) from exception
        except OpenDtuApiClientError:
            raise
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise OpenDtuApiClientError(
                msg,
            ) from exception

    async def _api_wrapper_optional(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get optional information from the API."""
        try:
            return await self._api_wrapper(
                method=method,
                path=path,
                data=data,
                headers=headers,
            )
        except OpenDtuApiClientError:
            return None

    @property
    def _base_url(self) -> str:
        """Return the normalized base URL for the OpenDTU device."""
        if self._host.startswith(("http://", "https://")):
            return self._host.rstrip("/")
        return f"http://{self._host}".rstrip("/")
