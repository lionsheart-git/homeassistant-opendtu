"""OpenDTU API client."""

from __future__ import annotations

import socket
from typing import Any

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
        return await self._api_wrapper(
            method="get",
            path="/api/livedata/status",
        )

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
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise OpenDtuApiClientError(
                msg,
            ) from exception

    @property
    def _base_url(self) -> str:
        """Return the normalized base URL for the OpenDTU device."""
        if self._host.startswith(("http://", "https://")):
            return self._host.rstrip("/")
        return f"http://{self._host}".rstrip("/")
