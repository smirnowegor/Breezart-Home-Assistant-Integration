"""Config flow for Breezart integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_PORT, DOMAIN
from .coordinator import BreezartTCPClient

_LOGGER = logging.getLogger(__name__)

class BreezartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Breezart."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._password: str | None = None

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = int(user_input[CONF_PORT])
            self._password = user_input[CONF_PASSWORD]

            # Test connection
            try:
                client = BreezartTCPClient(
                    host=self._host,
                    port=self._port,
                    password=int(self._password),
                )
                await client.connect()
                await client.get_properties()
                await client.disconnect()
            except TimeoutError as err:
                _LOGGER.error("Connection timeout: %s", err)
                errors["base"] = "cannot_connect"
            except ConnectionError as err:
                _LOGGER.error("Connection error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error during connection test: %s", err)
                errors["base"] = "unknown"
            else:
                # Connection successful, create entry
                return self.async_create_entry(
                    title=f"Breezart ({self._host})",
                    data={
                        CONF_HOST: self._host,
                        CONF_PORT: self._port,
                        CONF_PASSWORD: self._password,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default="192.168.1.121"): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_PASSWORD, default="21579"): str,
                }
            ),
            errors=errors,
        )
