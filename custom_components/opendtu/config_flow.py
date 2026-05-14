"""Adds config flow for OpenDTU."""

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
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
)


class OpenDtuFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for OpenDTU."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,  # noqa: ARG004 Unused argument
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OpenDtuOptionsFlowHandler()

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                host = user_input[CONF_HOST].strip()
                await self._test_credentials(
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
                    title=host,
                    data={CONF_HOST: host},
                )

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, (  # noqa: S101
            "Integration documentation URL is not set in manifest.json"
        )

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "documentation_url": integration.documentation,
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

    async def _test_credentials(self, host: str) -> None:
        """Validate the OpenDTU host."""
        client = OpenDtuApiClient(
            host=host,
            session=async_create_clientsession(self.hass),
        )
        await client.async_get_data()


class OpenDtuOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for OpenDTU."""

    async def async_step_init(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage OpenDTU options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
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
                },
            ),
        )
