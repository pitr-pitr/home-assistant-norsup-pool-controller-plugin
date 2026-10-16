"""Config flow for Norsup Smartpool."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.selector import (
    BooleanSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    NorsupAuthError,
    NorsupConnectionError,
    async_validate_api_key,
)
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_ENABLE_DIAGNOSTICS,
    CONF_POOL_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

POOL_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

def _user_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_API_KEY): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Required(CONF_POOL_ID): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)
            ),
        }
    )


def _options_schema(scan_interval: int, enable_diagnostics: bool) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_API_KEY): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=600)
            ),
            vol.Optional(
                CONF_ENABLE_DIAGNOSTICS, default=enable_diagnostics
            ): BooleanSelector(),
        }
    )


async def _async_validate(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, str]:
    """Validate API key against live-status."""
    pool_id = data[CONF_POOL_ID].strip()
    api_key = data[CONF_API_KEY].strip()
    base_url = data.get(CONF_BASE_URL, DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL

    if not POOL_ID_PATTERN.match(pool_id):
        return {"base": "invalid_auth"}

    session = aiohttp_client.async_get_clientsession(hass)
    try:
        await async_validate_api_key(session, pool_id, api_key, base_url)
    except NorsupAuthError:
        return {"base": "invalid_auth"}
    except NorsupConnectionError:
        return {"base": "cannot_connect"}
    except Exception:
        _LOGGER.exception("Unexpected error validating Norsup credentials")
        return {"base": "unknown"}

    return {}


class NorsupSmartpoolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Norsup Smartpool."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            pool_id = user_input[CONF_POOL_ID].strip()
            await self.async_set_unique_id(pool_id)
            self._abort_if_unique_id_configured()

            errors = await _async_validate(self.hass, user_input)
            if not errors:
                return self.async_create_entry(
                    title=f"Norsup Smartpool ({pool_id[:8]}…)",
                    data={
                        CONF_API_KEY: user_input[CONF_API_KEY].strip(),
                        CONF_POOL_ID: pool_id,
                        CONF_BASE_URL: (
                            user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL).strip()
                            or DEFAULT_BASE_URL
                        ),
                    },
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NorsupSmartpoolOptionsFlow:
        """Return the options flow handler."""
        return NorsupSmartpoolOptionsFlow(config_entry)


class NorsupSmartpoolOptionsFlow(config_entries.OptionsFlowWithConfigEntry):
    """Handle options for Norsup Smartpool."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage API key rotation and scan interval."""
        errors: dict[str, str] = {}

        if user_input is not None:
            validate_data = {
                CONF_API_KEY: user_input[CONF_API_KEY],
                CONF_POOL_ID: self.config_entry.data[CONF_POOL_ID],
                CONF_BASE_URL: self.config_entry.data.get(
                    CONF_BASE_URL, DEFAULT_BASE_URL
                ),
            }
            errors = await _async_validate(self.hass, validate_data)
            if not errors:
                new_data = dict(self.config_entry.data)
                new_data[CONF_API_KEY] = user_input[CONF_API_KEY].strip()
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                )
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.options.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        ),
                        CONF_ENABLE_DIAGNOSTICS: user_input.get(
                            CONF_ENABLE_DIAGNOSTICS,
                            self.config_entry.options.get(
                                CONF_ENABLE_DIAGNOSTICS, False
                            ),
                        ),
                    },
                )

        scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        enable_diagnostics = self.config_entry.options.get(
            CONF_ENABLE_DIAGNOSTICS, False
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(scan_interval, enable_diagnostics),
            errors=errors,
        )
