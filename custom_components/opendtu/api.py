"""
Asynchronous OpenDTU REST API client.

This module contains the small HTTP client used by the Home Assistant
integration. It reads OpenDTU's unauthenticated, read-only API endpoints and
normalizes optional endpoint payloads into the common coordinator data model.
"""

from __future__ import annotations

import asyncio
import socket
from typing import Any
from urllib.parse import quote

import aiohttp
import async_timeout

DTU_STATUS_ENDPOINTS = {
    "mqtt": "/api/mqtt/status",
    "network": "/api/network/status",
    "ntp": "/api/ntp/status",
    "power": "/api/power/status",
    "system": "/api/system/status",
}


class OpenDtuApiClientError(Exception):
    """Base exception for OpenDTU API failures."""


class OpenDtuApiClientCommunicationError(
    OpenDtuApiClientError,
):
    """Exception raised when OpenDTU cannot be reached or times out."""


class OpenDtuApiClientAuthenticationError(
    OpenDtuApiClientError,
):
    """Exception raised when OpenDTU requires or rejects authentication."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """
    Validate an OpenDTU HTTP response.

    Args:
        response: Response returned by the shared Home Assistant aiohttp
            session.

    Raises:
        OpenDtuApiClientAuthenticationError: The endpoint returned HTTP 401 or
            HTTP 403.
        aiohttp.ClientResponseError: The endpoint returned another unsuccessful
            HTTP status.

    """
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise OpenDtuApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()


class OpenDtuApiClient:
    """Client for OpenDTU's local REST API."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """
        Initialize the OpenDTU API client.

        Args:
            host: OpenDTU hostname, IP address, or URL configured by the user.
            session: Home Assistant managed aiohttp client session.

        """
        self._host = host.strip()
        self._session = session

    async def async_get_data(self, *, include_diagnostics: bool = True) -> Any:
        """
        Fetch and enrich OpenDTU data for one coordinator update.

        Args:
            include_diagnostics: Whether optional diagnostic endpoints should
                be fetched in addition to live production data.

        Returns:
            The decoded JSON response from `/api/livedata/status`, enriched
            with inverter details and, when requested, diagnostic payloads.

        Raises:
            OpenDtuApiClientAuthenticationError: Authentication is required or
                rejected by the required live-data endpoint.
            OpenDtuApiClientCommunicationError: The required live-data endpoint
                cannot be reached or times out.
            OpenDtuApiClientError: Any other required endpoint failure.

        """
        data = await self._api_wrapper(
            method="get",
            path="/api/livedata/status",
        )
        api_tasks = [self._add_inverter_details(data)]
        if include_diagnostics:
            api_tasks.extend(
                (
                    self._add_dtu_statuses(data),
                    self._add_limit_status(data),
                    self._add_eventlogs(data),
                )
            )
        await asyncio.gather(*api_tasks)
        return data

    async def _add_dtu_statuses(self, data: Any) -> None:
        """
        Add optional DTU status endpoint payloads to live data.

        Args:
            data: Mutable live-data response to enrich. Non-dict payloads are
                ignored.

        """
        if not isinstance(data, dict):
            return

        endpoint_results = await asyncio.gather(
            *(
                self._api_wrapper_optional(method="get", path=path)
                for path in DTU_STATUS_ENDPOINTS.values()
            ),
        )
        status_data = {
            endpoint: result
            for endpoint, result in zip(
                DTU_STATUS_ENDPOINTS,
                endpoint_results,
                strict=True,
            )
            if isinstance(result, dict)
        }
        if status_data:
            data["_status"] = status_data

    async def _add_inverter_details(self, data: Any) -> None:
        """
        Add detailed live measurements for each inverter.

        Args:
            data: Mutable live-data response containing an `inverters` list.

        """
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
        """
        Fetch detailed live data for one inverter.

        Args:
            inverter: Inverter summary object containing a `serial` value.

        Returns:
            The first inverter object from `/api/livedata/status?inv=<serial>`,
            or `None` when the optional endpoint is unavailable.

        """
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
        """
        Attach limit status payloads to matching inverter objects.

        Args:
            data: Mutable live-data response containing an `inverters` list.

        """
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
        """
        Attach event log payloads to matching inverter objects.

        Args:
            data: Mutable live-data response containing an `inverters` list.

        """
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
        """
        Fetch event log data for one inverter.

        Args:
            inverter: Inverter summary object containing a `serial` value.

        Returns:
            A tuple containing the inverter serial and its optional event log
            payload. The event log value is `None` when unavailable.

        """
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
        """
        Fetch a required OpenDTU endpoint.

        Args:
            method: HTTP method to use.
            path: API path relative to the normalized OpenDTU base URL.
            data: Optional JSON request body.
            headers: Optional request headers.

        Returns:
            The decoded JSON response.

        Raises:
            OpenDtuApiClientAuthenticationError: Authentication is required or
                rejected.
            OpenDtuApiClientCommunicationError: The endpoint cannot be reached
                or times out.
            OpenDtuApiClientError: Any other request or decoding failure.

        """
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
        """
        Fetch an optional OpenDTU endpoint.

        Args:
            method: HTTP method to use.
            path: API path relative to the normalized OpenDTU base URL.
            data: Optional JSON request body.
            headers: Optional request headers.

        Returns:
            The decoded JSON response, or `None` when the optional endpoint
            fails.

        """
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
        """
        Return the normalized base URL for the OpenDTU device.

        Returns:
            A URL including scheme and without trailing slash.

        """
        if self._host.startswith(("http://", "https://")):
            return self._host.rstrip("/")
        return f"http://{self._host}".rstrip("/")
