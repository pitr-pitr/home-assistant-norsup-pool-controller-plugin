"""Data update coordinator for Norsup Smartpool."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    NorsupApiClient,
    NorsupAuthError,
    NorsupConnectionError,
    NorsupPoolData,
    NorsupTransientError,
)
from .const import (
    AUTH_TYPE_PORTAL,
    CONF_API_BASE_URL,
    CONF_API_KEY,
    CONF_AUTH_TYPE,
    CONF_BASE_URL,
    CONF_OAUTH_BASE_URL,
    CONF_PASSWORD,
    CONF_POOL_ID,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_API_BASE_URL,
    DEFAULT_BASE_URL,
    DEFAULT_OAUTH_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class NorsupDataUpdateCoordinator(DataUpdateCoordinator[NorsupPoolData]):
    """Fetch and normalize Smart Pool Connect data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: NorsupApiClient,
    ) -> None:
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self._client = client
        self._consecutive_failures = 0
        self._failure_warning_logged = False

        super().__init__(
            hass,
            _LOGGER,
            name="norsup_smartpool",
            update_interval=timedelta(seconds=int(scan_interval)),
            config_entry=entry,
        )

    @property
    def pool_id(self) -> str:
        return self._client.pool_id

    async def _async_update_data(self) -> NorsupPoolData:
        try:
            data = await self._client.async_get_pool_data()
        except NorsupAuthError as err:
            self._register_failure()
            raise UpdateFailed(
                "Authentication failed; check portal password or API key in integration options"
            ) from err
        except (NorsupTransientError, NorsupConnectionError) as err:
            self._register_failure()
            raise UpdateFailed("Smart Pool Connect is temporarily unavailable") from err
        except Exception as err:
            self._register_failure()
            _LOGGER.debug("Unexpected coordinator error", exc_info=True)
            raise UpdateFailed("Failed to update pool data") from err

        self._consecutive_failures = 0
        self._failure_warning_logged = False
        return data

    def _register_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= 2 and not self._failure_warning_logged:
            _LOGGER.warning(
                "Repeated failures updating Norsup Smartpool data for pool %s; "
                "check connectivity and credentials in integration options",
                self.pool_id,
            )
            self._failure_warning_logged = True


def build_client(hass: HomeAssistant, entry: ConfigEntry) -> NorsupApiClient:
    """Create an API client from config entry data."""
    import aiohttp
    from homeassistant.helpers import aiohttp_client

    portal = entry.data.get(CONF_AUTH_TYPE) == AUTH_TYPE_PORTAL
    if portal:
        session = aiohttp_client.async_create_clientsession(
            hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
    else:
        session = aiohttp_client.async_get_clientsession(hass)

    return NorsupApiClient(
        session,
        entry.data[CONF_POOL_ID],
        entry.data.get(CONF_API_KEY),
        entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        api_base_url=entry.data.get(CONF_API_BASE_URL, DEFAULT_API_BASE_URL),
        username=entry.data.get(CONF_USERNAME) if portal else None,
        password=entry.data.get(CONF_PASSWORD) if portal else None,
        oauth_base_url=entry.data.get(CONF_OAUTH_BASE_URL, DEFAULT_OAUTH_BASE_URL),
        auth_type=entry.data.get(CONF_AUTH_TYPE),
    )
