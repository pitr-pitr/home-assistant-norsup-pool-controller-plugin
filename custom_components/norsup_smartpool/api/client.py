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
    DEFAULT_BASE_URL,
)
from .models import (
    NorsupPoolData,
    merge_readings,
    parse_live_status,
    parse_pool_data_readings,
    parse_pool_status,
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


def _auth_header_variants(api_key: str) -> tuple[tuple[str, dict[str, str]], ...]:
    return (
        (AUTH_BEARER, {"Authorization": f"Bearer {api_key}"}),
        (AUTH_API_KEY_HEADER, {"X-Api-Key": api_key}),
    )


class NorsupApiClient:
    """Async HTTP client for Norsup Smart Pool Connect."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        pool_id: str,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self._session = session
        self._pool_id = pool_id
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._auth_mode: str | None = None
        self._auth_headers: dict[str, str] | None = None

    @property
    def pool_id(self) -> str:
        return self._pool_id

    async def async_validate_api_key(self) -> dict[str, Any]:
        """Verify credentials via live-status; returns raw JSON."""
        return await self._async_get_json(
            API_LIVE_STATUS.format(pool_id=self._pool_id),
            auth_probe=True,
        )

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

    async def _async_get_text(
        self,
        path: str,
        *,
        auth_probe: bool = False,
        optional: bool = False,
    ) -> tuple[int, str]:
        url = _url(self._base_url, path)

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
        for mode, headers in _auth_header_variants(self._api_key):
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

    async def _request_once(
        self,
        url: str,
        headers: dict[str, str],
        *,
        optional: bool,
    ) -> tuple[int, str]:
        try:
            async with self._session.get(
                url, headers=headers, timeout=DEFAULT_TIMEOUT
            ) as response:
                text = await response.text()
                if response.status in (401, 403):
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
) -> dict[str, Any]:
    """Call live-status to verify credentials; return parsed JSON on success."""
    client = NorsupApiClient(session, pool_id, api_key, base_url)
    return await client.async_validate_api_key()
