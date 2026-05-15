"""
Config and options flows for OpenDTU.

The config flow validates a local OpenDTU host by fetching the REST API. The
options flow exposes live and diagnostic polling intervals.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import (
    OpenDtuApiClient,
    OpenDtuApiClientAuthenticationError,
    OpenDtuApiClientCommunicationError,
    OpenDtuApiClientError,
)
from .const import (
    CONF_DIAGNOSTIC_SCAN_INTERVAL,
    DEFAULT_DIAGNOSTIC_SCAN_INTERVAL_SECONDS,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    LOGGER,
    MAX_DIAGNOSTIC_SCAN_INTERVAL_SECONDS,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_DIAGNOSTIC_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
)
from .entity import get_dtu_hostname


class OpenDtuFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the OpenDTU user setup flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,  # noqa: ARG004 Unused argument
    ) -> config_entries.OptionsFlow:
        """
        Create the options flow.

        Args:
            config_entry: Existing OpenDTU config entry.

        Returns:
            Options flow handler for polling intervals.

        """
        return OpenDtuOptionsFlowHandler()

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle a user-initiated config flow step.

        Args:
            user_input: Form data containing the configured OpenDTU host, or
                `None` when the form should be shown.

        Returns:
            Home Assistant config flow result.

        """
        _errors = {}
        if user_input is not None:
            try:
                host = user_input[CONF_HOST].strip()
                data = await self._test_credentials(
                    host=host,
                )
            except OpenDtuApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except OpenDtuApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except OpenDtuApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(host.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=get_dtu_hostname(data) or host,
                    data={CONF_HOST: host},
                )

        integration = async_get_loaded_integration(self.hass, DOMAIN)

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "documentation_url": integration.documentation or "",
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=(user_input or {}).get(CONF_HOST, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    async def _test_credentials(self, host: str) -> object:
        """
        Validate that a host responds like an OpenDTU device.

        Args:
            host: Host, IP address, or URL submitted by the user.

        Returns:
            Initial OpenDTU API payload used to derive the config entry title.

        Raises:
            OpenDtuApiClientAuthenticationError: OpenDTU requires or rejects
                authentication.
            OpenDtuApiClientCommunicationError: OpenDTU cannot be reached.
            OpenDtuApiClientError: Any other API client failure.

        """
        client = OpenDtuApiClient(
            host=host,
            session=async_create_clientsession(self.hass),
        )
        return await client.async_get_data()


class OpenDtuOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle editable OpenDTU integration options."""

    async def async_step_init(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Show or save OpenDTU options.

        Args:
            user_input: Submitted option values, or `None` to show the form.

        Returns:
            Home Assistant options flow result.

        """
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_DIAGNOSTIC_SCAN_INTERVAL: int(
                        user_input[CONF_DIAGNOSTIC_SCAN_INTERVAL],
                    ),
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            DEFAULT_SCAN_INTERVAL_SECONDS,
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL_SECONDS,
                            max=MAX_SCAN_INTERVAL_SECONDS,
                            step=1,
                            unit_of_measurement=UnitOfTime.SECONDS,
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    ),
                    vol.Required(
                        CONF_DIAGNOSTIC_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_DIAGNOSTIC_SCAN_INTERVAL,
                            DEFAULT_DIAGNOSTIC_SCAN_INTERVAL_SECONDS,
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_DIAGNOSTIC_SCAN_INTERVAL_SECONDS,
                            max=MAX_DIAGNOSTIC_SCAN_INTERVAL_SECONDS,
                            step=1,
                            unit_of_measurement=UnitOfTime.SECONDS,
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    ),
                },
            ),
        )
