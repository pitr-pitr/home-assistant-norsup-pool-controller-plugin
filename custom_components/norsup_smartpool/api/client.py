"""aiohttp client for Smart Pool Connect."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from ..const import (
    API_LIVE_STATUS,
    API_POOL_DATA,
    API_POOL_STATUS,
    API_REST_POOL,
    API_REST_POOLS,
    AUTH_TYPE_PORTAL,
    DEFAULT_API_BASE_URL,
    DEFAULT_BASE_URL,
    DEFAULT_OAUTH_BASE_URL,
)
from .oauth_session import NorsupPortalLoginError, async_portal_login
from .models import (
    NorsupPoolData,
    merge_readings,
    parse_live_status,
    parse_pool_data_readings,
    parse_pool_status,
    parse_rest_pool,
    parse_rest_pool_list,
)

_LOGGER = logging.getLogger(__name__)

AUTH_BEARER = "bearer"
AUTH_API_KEY_HEADER = "x_api_key"

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=25)


class NorsupAuthError(Exception):
    """Raised when the cloud API rejects credentials."""


class NorsupTransientError(Exception):
    """Raised when the cloud API is temporarily unavailable."""


class NorsupConnectionError(Exception):
    """Raised when the cloud API cannot be reached."""


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def _rest_api_key_headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key}


def _auth_header_variants(api_key: str) -> tuple[tuple[str, dict[str, str]], ...]:
    return (
        (AUTH_API_KEY_HEADER, _rest_api_key_headers(api_key)),
        (AUTH_BEARER, {"Authorization": f"Bearer {api_key}"}),
        (AUTH_API_KEY_HEADER, {"X-Api-Key": api_key}),
    )


class NorsupApiClient:
    """Async HTTP client for Norsup Smart Pool Connect."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        pool_id: str,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        *,
        api_base_url: str = DEFAULT_API_BASE_URL,
        username: str | None = None,
        password: str | None = None,
        oauth_base_url: str = DEFAULT_OAUTH_BASE_URL,
        auth_type: str | None = None,
    ) -> None:
        self._session = session
        self._pool_id = pool_id
        self._api_key = (api_key or "").strip()
        self._base_url = base_url.rstrip("/")
        self._api_base_url = api_base_url.rstrip("/")
        self._username = (username or "").strip() or None
        self._password = password or None
        self._oauth_base_url = oauth_base_url.rstrip("/")
        self._use_portal = auth_type == AUTH_TYPE_PORTAL or (
            auth_type is None and self._username and self._password
        )
        self._portal_logged_in = False
        self._rest_api = not self._use_portal and bool(self._api_key)
        self._auth_mode: str | None = None
        self._auth_headers: dict[str, str] | None = None

    @property
    def pool_id(self) -> str:
        return self._pool_id

    async def async_validate_api_key(self) -> dict[str, Any]:
        """Verify API key (REST /pool) or portal live-status; returns raw JSON."""
        if self._rest_api:
            payload = await self._async_rest_get_json(API_REST_POOLS, auth_probe=True)
            if self._pool_id:
                pools = parse_rest_pool_list(payload)
                if pools and not any(pid == self._pool_id for pid, _ in pools):
                    raise NorsupAuthError("pool_not_found")
            return payload
        return await self._async_get_json(
            API_LIVE_STATUS.format(pool_id=self._pool_id),
            auth_probe=True,
        )

    async def async_list_rest_pools(self) -> list[tuple[str, str]]:
        """List pools visible to the configured SPC API key."""
        payload = await self._async_rest_get_json(API_REST_POOLS)
        return parse_rest_pool_list(payload)

    async def async_get_live_status(self) -> dict[str, Any]:
        """Fetch live-status JSON."""
        return await self._async_get_json(
            API_LIVE_STATUS.format(pool_id=self._pool_id),
        )

    async def async_get_pool_status(self) -> dict[str, Any]:
        """Fetch supplemental pool-status JSON."""
        return await self._async_get_json(
            API_POOL_STATUS.format(pool_id=self._pool_id),
            optional=True,
        )

    async def async_get_pool_data_text(self) -> str:
        """Fetch /pool.data body for chemistry readings."""
        status, text = await self._async_get_text(API_POOL_DATA, optional=True)
        if status == 404:
            return ""
        if status >= 400:
            return ""
        return text

    async def async_get_pool_data(self) -> NorsupPoolData:
        """Batch P0 reads and return normalized pool data."""
        if self._rest_api:
            payload = await self._async_rest_get_json(
                API_REST_POOL.format(pool_id=self._pool_id)
            )
            return parse_rest_pool(self._pool_id, payload)

        live_task = asyncio.create_task(self.async_get_live_status())
        status_task = asyncio.create_task(self.async_get_pool_status())
        pool_data_task = asyncio.create_task(self.async_get_pool_data_text())

        live_payload = await live_task
        status_payload, pool_data_text = await asyncio.gather(status_task, pool_data_task)

        data = parse_live_status(self._pool_id, live_payload)
        data = parse_pool_status(data, status_payload)
        ph, rx = parse_pool_data_readings(pool_data_text, self._pool_id)
        return merge_readings(data, ph, rx)

    async def _async_get_json(
        self,
        path: str,
        *,
        auth_probe: bool = False,
        optional: bool = False,
    ) -> dict[str, Any]:
        status, text = await self._async_get_text(
            path, auth_probe=auth_probe, optional=optional
        )
        if optional and status == 404:
            return {}
        if not text:
            return {}
        try:
            payload: Any = json.loads(text)
        except json.JSONDecodeError:
            if optional:
                _LOGGER.debug("Non-JSON optional response for %s", path)
                return {}
            raise NorsupAuthError("invalid_response") from None
        if not isinstance(payload, dict):
            if optional:
                return {}
            raise NorsupAuthError("invalid_response")
        return payload

    async def _async_rest_get_json(
        self,
        path: str,
        *,
        auth_probe: bool = False,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise NorsupAuthError("invalid_credentials")
        url = _url(self._api_base_url, path)
        headers = self._auth_headers or _rest_api_key_headers(self._api_key)
        try:
            status, text = await self._request_once(url, headers, optional=False)
        except aiohttp.ClientError as err:
            raise NorsupConnectionError(str(err)) from err

        if status in (401, 403):
            if auth_probe and self._auth_headers is None:
                raise NorsupAuthError("invalid_credentials")
            raise NorsupAuthError("invalid_credentials")
        if status >= 500:
            raise NorsupTransientError(f"server_error_{status}")
        if status >= 400:
            raise NorsupAuthError(f"http_{status}")

        self._auth_headers = headers
        self._auth_mode = AUTH_API_KEY_HEADER
        if not text:
            return {}
        try:
            payload: Any = json.loads(text)
        except json.JSONDecodeError:
            raise NorsupAuthError("invalid_response") from None
        if not isinstance(payload, dict):
            raise NorsupAuthError("invalid_response")
        return payload

    async def _async_get_text(
        self,
        path: str,
        *,
        auth_probe: bool = False,
        optional: bool = False,
    ) -> tuple[int, str]:
        url = _url(self._base_url, path)

        if self._use_portal:
            await self._ensure_portal_session()
            try:
                status, text = await self._request_once(
                    url, {}, optional=optional, reauth_on_401=True
                )
            except aiohttp.ClientError as err:
                raise NorsupConnectionError(str(err)) from err
            if status in (401, 403):
                raise NorsupAuthError("invalid_credentials")
            if status == 404 and optional:
                return status, ""
            self._apply_status(status, optional=optional)
            return status, text

        if self._auth_headers is not None:
            status, text = await self._request_once(
                url, self._auth_headers, optional=optional
            )
            if status in (401, 403):
                raise NorsupAuthError("invalid_credentials")
            if status == 404 and optional:
                return status, ""
            self._apply_status(status, optional=optional)
            return status, text

        last_status: int | None = None
        for mode, headers in _auth_header_variants(self._api_key or ""):
            try:
                status, text = await self._request_once(url, headers, optional=optional)
            except aiohttp.ClientError as err:
                raise NorsupConnectionError(str(err)) from err

            last_status = status
            if status in (401, 403):
                continue
            if status == 404 and optional:
                return status, ""
            self._apply_status(status, optional=optional)
            self._auth_mode = mode
            self._auth_headers = headers
            return status, text

        if last_status in (401, 403):
            raise NorsupAuthError("invalid_credentials")
        raise NorsupAuthError("invalid_credentials")

    async def _ensure_portal_session(self) -> None:
        if self._portal_logged_in:
            return
        if not self._username or not self._password:
            raise NorsupAuthError("invalid_credentials")
        try:
            await async_portal_login(
                self._session,
                self._username,
                self._password,
                base_url=self._base_url,
                oauth_base_url=self._oauth_base_url,
            )
        except NorsupPortalLoginError as err:
            raise NorsupAuthError("invalid_credentials") from err
        self._portal_logged_in = True

    async def _request_once(
        self,
        url: str,
        headers: dict[str, str],
        *,
        optional: bool,
        reauth_on_401: bool = False,
    ) -> tuple[int, str]:
        try:
            async with self._session.get(
                url, headers=headers, timeout=DEFAULT_TIMEOUT
            ) as response:
                text = await response.text()
                if response.status in (401, 403):
                    if (
                        reauth_on_401
                        and self._use_portal
                        and self._portal_logged_in
                    ):
                        self._portal_logged_in = False
                        await self._ensure_portal_session()
                        async with self._session.get(
                            url, headers=headers, timeout=DEFAULT_TIMEOUT
                        ) as retry:
                            retry_text = await retry.text()
                            return retry.status, retry_text
                    return response.status, text
                if response.status == 404:
                    return response.status, text
                self._apply_status(response.status, optional=optional)
                return response.status, text
        except aiohttp.ClientError as err:
            raise NorsupConnectionError(str(err)) from err

    def _apply_status(self, status: int, *, optional: bool) -> None:
        if status in (401, 403):
            raise NorsupAuthError("invalid_credentials")
        if status == 404 and not optional:
            raise NorsupAuthError("pool_not_found")
        if status >= 500:
            raise NorsupTransientError(f"server_error_{status}")
        if status >= 400 and not (optional and status == 404):
            raise NorsupAuthError(f"http_{status}")


async def async_validate_api_key(
    session: aiohttp.ClientSession,
    pool_id: str,
    api_key: str,
    base_url: str = DEFAULT_BASE_URL,
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> dict[str, Any]:
    """Verify SPC API key (REST) or legacy portal live-status; return JSON on success."""
    client = NorsupApiClient(
        session,
        pool_id,
        api_key,
        base_url,
        api_base_url=api_base_url,
    )
    return await client.async_validate_api_key()


async def async_list_pools_for_api_key(
    session: aiohttp.ClientSession,
    api_key: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> list[tuple[str, str]]:
    """Return pools accessible with an SPC API key (GET /pool on the REST host)."""
    client = NorsupApiClient(
        session,
        pool_id="",
        api_key=api_key,
        base_url=DEFAULT_BASE_URL,
        api_base_url=api_base_url,
    )
    return await client.async_list_rest_pools()


async def async_validate_portal_credentials(
    session: aiohttp.ClientSession,
    pool_id: str,
    username: str,
    password: str,
    base_url: str = DEFAULT_BASE_URL,
    oauth_base_url: str = DEFAULT_OAUTH_BASE_URL,
) -> dict[str, Any]:
    """Log in with portal email/password and verify live-status for ``pool_id``."""
    client = NorsupApiClient(
        session,
        pool_id,
        api_key=None,
        base_url=base_url,
        username=username,
        password=password,
        oauth_base_url=oauth_base_url,
        auth_type=AUTH_TYPE_PORTAL,
    )
    return await client.async_validate_api_key()
