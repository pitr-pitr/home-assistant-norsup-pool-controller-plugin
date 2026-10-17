"""Config flow for Norsup Smartpool."""

from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    NorsupAuthError,
    NorsupConnectionError,
    NorsupPortalLoginError,
    async_discover_pools,
    async_list_pools_for_api_key,
    async_portal_login,
    async_validate_api_key,
    async_validate_portal_credentials,
)
from .const import (
    AUTH_TYPE_API_KEY,
    AUTH_TYPE_PORTAL,
    CONF_API_BASE_URL,
    CONF_API_KEY,
    CONF_AUTH_TYPE,
    CONF_BASE_URL,
    CONF_ENABLE_DIAGNOSTICS,
    CONF_OAUTH_BASE_URL,
    CONF_PASSWORD,
    CONF_POOL_ID,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_API_BASE_URL,
    DEFAULT_BASE_URL,
    DEFAULT_OAUTH_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

POOL_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

AUTH_MENU_API_KEY = "api_key"
AUTH_MENU_PORTAL = "portal"


def _user_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_API_KEY): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_POOL_ID, default=""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)
            ),
        }
    )


def _portal_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL)
            ),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_POOL_ID, default=""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)
            ),
        }
    )


def _options_schema(
    scan_interval: int,
    enable_diagnostics: bool,
    *,
    portal: bool,
) -> vol.Schema:
    secret_key = CONF_PASSWORD if portal else CONF_API_KEY
    secret_label = (
        TextSelectorConfig(type=TextSelectorType.PASSWORD)
    )
    return vol.Schema(
        {
            vol.Required(secret_key): TextSelector(secret_label),
            vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=600)
            ),
            vol.Optional(
                CONF_ENABLE_DIAGNOSTICS, default=enable_diagnostics
            ): BooleanSelector(),
        }
    )


async def _async_validate_api_key_flow(
    hass: HomeAssistant, data: dict[str, Any], pool_id: str
) -> dict[str, str]:
    """Validate SPC API key (REST) for the chosen pool."""
    api_key = data[CONF_API_KEY].strip()
    base_url = data.get(CONF_BASE_URL, DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    api_base_url = (
        data.get(CONF_API_BASE_URL, DEFAULT_API_BASE_URL).strip()
        or DEFAULT_API_BASE_URL
    )

    if not POOL_ID_PATTERN.match(pool_id):
        return {"base": "invalid_pool_id"}

    session = aiohttp_client.async_get_clientsession(hass)
    try:
        await async_validate_api_key(
            session, pool_id, api_key, base_url, api_base_url=api_base_url
        )
    except NorsupAuthError:
        return {"base": "invalid_auth"}
    except NorsupConnectionError:
        return {"base": "cannot_connect"}
    except Exception:
        _LOGGER.exception("Unexpected error validating Norsup API key")
        return {"base": "unknown"}

    return {}


async def _async_validate_portal_flow(
    hass: HomeAssistant,
    data: dict[str, Any],
    pool_id: str,
) -> dict[str, str]:
    """Validate portal login and live-status for the chosen pool."""
    username = data[CONF_USERNAME].strip()
    password = data[CONF_PASSWORD]
    base_url = data.get(CONF_BASE_URL, DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL

    if not POOL_ID_PATTERN.match(pool_id):
        return {"base": "invalid_pool_id"}

    session = aiohttp_client.async_create_clientsession(
        hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
    )
    try:
        await async_validate_portal_credentials(
            session,
            pool_id,
            username,
            password,
            base_url,
            DEFAULT_OAUTH_BASE_URL,
        )
    except NorsupAuthError:
        return {"base": "invalid_auth"}
    except NorsupConnectionError:
        return {"base": "cannot_connect"}
    except Exception:
        _LOGGER.exception("Unexpected error validating Norsup portal login")
        return {"base": "unknown"}
    finally:
        await session.close()

    return {}


class NorsupSmartpoolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Norsup Smartpool."""

    VERSION = 1

    def __init__(self) -> None:
        self._portal_input: dict[str, Any] | None = None
        self._api_key_input: dict[str, Any] | None = None
        self._discovered_pools: list[tuple[str, str]] = []
        self._choose_pool_for_api_key = False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose API key or portal account."""
        if user_input is not None:
            if user_input["auth_method"] == AUTH_MENU_PORTAL:
                return await self.async_step_portal()
            return await self.async_step_api_key()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("auth_method"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=AUTH_MENU_PORTAL,
                                    label="Smart Pool Connect account (email & password)",
                                ),
                                SelectOptionDict(
                                    value=AUTH_MENU_API_KEY,
                                    label="SPC API key (spc_…)",
                                ),
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_api_key(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure with bearer token and pool UUID."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key_input = user_input
            pool_id = user_input.get(CONF_POOL_ID, "").strip()
            api_key = user_input[CONF_API_KEY].strip()
            base_url = (
                user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL).strip()
                or DEFAULT_BASE_URL
            )
            api_base_url = DEFAULT_API_BASE_URL

            if pool_id and not POOL_ID_PATTERN.match(pool_id):
                errors = {"base": "invalid_pool_id"}
            elif pool_id:
                await self.async_set_unique_id(pool_id)
                self._abort_if_unique_id_configured()
                errors = await _async_validate_api_key_flow(
                    self.hass, user_input, pool_id
                )
                if not errors:
                    return self._async_create_api_key_entry(
                        user_input, pool_id, base_url, api_base_url
                    )
            else:
                session = aiohttp_client.async_get_clientsession(self.hass)
                try:
                    pools = await async_list_pools_for_api_key(
                        session, api_key, api_base_url=api_base_url
                    )
                except NorsupAuthError:
                    errors = {"base": "invalid_auth"}
                except NorsupConnectionError:
                    errors = {"base": "cannot_connect"}
                except Exception:
                    _LOGGER.exception("Unexpected error listing pools for API key")
                    errors = {"base": "unknown"}
                else:
                    if not pools:
                        errors = {"base": "no_pools"}
                    elif len(pools) == 1:
                        only_id, _ = pools[0]
                        await self.async_set_unique_id(only_id)
                        self._abort_if_unique_id_configured()
                        errors = await _async_validate_api_key_flow(
                            self.hass, user_input, only_id
                        )
                        if not errors:
                            return self._async_create_api_key_entry(
                                user_input, only_id, base_url, api_base_url
                            )
                    else:
                        self._discovered_pools = pools
                        self._choose_pool_for_api_key = True
                        return await self.async_step_choose_pool()

        return self.async_show_form(
            step_id="api_key",
            data_schema=_user_schema(),
            errors=errors,
        )

    async def async_step_portal(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure with owner portal login; pool ID optional (auto-discovered)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._portal_input = user_input
            pool_id = user_input.get(CONF_POOL_ID, "").strip()
            base_url = (
                user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL).strip()
                or DEFAULT_BASE_URL
            )
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]

            if pool_id and not POOL_ID_PATTERN.match(pool_id):
                errors = {"base": "invalid_pool_id"}
            elif pool_id:
                errors = await _async_validate_portal_flow(
                    self.hass, user_input, pool_id
                )
                if not errors:
                    return await self._async_create_portal_entry(
                        user_input, pool_id, username, password, base_url
                    )
            else:
                session = aiohttp_client.async_create_clientsession(
                    self.hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
                )
                try:
                    await async_portal_login(
                        session,
                        username,
                        password,
                        base_url=base_url,
                        oauth_base_url=DEFAULT_OAUTH_BASE_URL,
                    )
                    pools = await async_discover_pools(session, base_url)
                except NorsupPortalLoginError:
                    errors = {"base": "invalid_auth"}
                except NorsupConnectionError:
                    errors = {"base": "cannot_connect"}
                except Exception:
                    _LOGGER.exception("Unexpected error during pool discovery")
                    errors = {"base": "unknown"}
                finally:
                    await session.close()

                if not errors:
                    if not pools:
                        errors = {"base": "no_pools"}
                    elif len(pools) == 1:
                        only = pools[0]
                        errors = await _async_validate_portal_flow(
                            self.hass, user_input, only.pool_id
                        )
                        if not errors:
                            return await self._async_create_portal_entry(
                                user_input,
                                only.pool_id,
                                username,
                                password,
                                base_url,
                            )
                    else:
                        self._discovered_pools = [
                            (p.pool_id, p.name) for p in pools
                        ]
                        return await self.async_step_choose_pool()

        return self.async_show_form(
            step_id="portal",
            data_schema=_portal_schema(),
            errors=errors,
        )

    def _async_create_api_key_entry(
        self,
        user_input: dict[str, Any],
        pool_id: str,
        base_url: str,
        api_base_url: str,
    ) -> FlowResult:
        return self.async_create_entry(
            title=f"Norsup Smartpool ({pool_id[:8]}…)",
            data={
                CONF_AUTH_TYPE: AUTH_TYPE_API_KEY,
                CONF_API_KEY: user_input[CONF_API_KEY].strip(),
                CONF_POOL_ID: pool_id,
                CONF_BASE_URL: base_url,
                CONF_API_BASE_URL: api_base_url,
            },
            options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
        )

    async def async_step_choose_pool(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick a pool when the account has more than one."""
        if self._portal_input is None and not self._choose_pool_for_api_key:
            return await self.async_step_portal()
        if self._choose_pool_for_api_key and self._api_key_input is None:
            return await self.async_step_api_key()

        errors: dict[str, str] = {}
        options = [
            SelectOptionDict(value=pool_id, label=f"{name} ({pool_id[:8]}…)")
            for pool_id, name in self._discovered_pools
        ]

        if user_input is not None:
            pool_id = user_input[CONF_POOL_ID]
            if self._choose_pool_for_api_key and self._api_key_input is not None:
                await self.async_set_unique_id(pool_id)
                self._abort_if_unique_id_configured()
                errors = await _async_validate_api_key_flow(
                    self.hass, self._api_key_input, pool_id
                )
                if not errors:
                    base_url = (
                        self._api_key_input.get(CONF_BASE_URL, DEFAULT_BASE_URL).strip()
                        or DEFAULT_BASE_URL
                    )
                    return self._async_create_api_key_entry(
                        self._api_key_input,
                        pool_id,
                        base_url,
                        DEFAULT_API_BASE_URL,
                    )
            elif self._portal_input is not None:
                base_url = (
                    self._portal_input.get(CONF_BASE_URL, DEFAULT_BASE_URL).strip()
                    or DEFAULT_BASE_URL
                )
                username = self._portal_input[CONF_USERNAME].strip()
                password = self._portal_input[CONF_PASSWORD]
                errors = await _async_validate_portal_flow(
                    self.hass, self._portal_input, pool_id
                )
                if not errors:
                    return await self._async_create_portal_entry(
                        self._portal_input,
                        pool_id,
                        username,
                        password,
                        base_url,
                    )

        return self.async_show_form(
            step_id="choose_pool",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_POOL_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def _async_create_portal_entry(
        self,
        user_input: dict[str, Any],
        pool_id: str,
        username: str,
        password: str,
        base_url: str,
    ) -> FlowResult:
        await self.async_set_unique_id(pool_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"Norsup Smartpool ({pool_id[:8]}…)",
            data={
                CONF_AUTH_TYPE: AUTH_TYPE_PORTAL,
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
                CONF_POOL_ID: pool_id,
                CONF_BASE_URL: base_url,
                CONF_OAUTH_BASE_URL: DEFAULT_OAUTH_BASE_URL,
                CONF_API_KEY: "",
            },
            options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
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
        """Manage credential rotation and scan interval."""
        errors: dict[str, str] = {}
        portal = self.config_entry.data.get(CONF_AUTH_TYPE) == AUTH_TYPE_PORTAL

        if user_input is not None:
            if portal:
                validate_data = {
                    CONF_USERNAME: self.config_entry.data[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_POOL_ID: self.config_entry.data[CONF_POOL_ID],
                    CONF_BASE_URL: self.config_entry.data.get(
                        CONF_BASE_URL, DEFAULT_BASE_URL
                    ),
                }
                errors = await _async_validate_portal_flow(
                    self.hass,
                    validate_data,
                    self.config_entry.data[CONF_POOL_ID],
                )
            else:
                validate_data = {
                    CONF_API_KEY: user_input[CONF_API_KEY],
                    CONF_POOL_ID: self.config_entry.data[CONF_POOL_ID],
                    CONF_BASE_URL: self.config_entry.data.get(
                        CONF_BASE_URL, DEFAULT_BASE_URL
                    ),
                }
                errors = await _async_validate_api_key_flow(
                    self.hass,
                    validate_data,
                    self.config_entry.data[CONF_POOL_ID],
                )

            if not errors:
                new_data = dict(self.config_entry.data)
                if portal:
                    new_data[CONF_PASSWORD] = user_input[CONF_PASSWORD]
                else:
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
            data_schema=_options_schema(
                scan_interval, enable_diagnostics, portal=portal
            ),
            errors=errors,
        )
