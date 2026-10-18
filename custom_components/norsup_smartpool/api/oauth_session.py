"""OAuth owner login and pool discovery for Smart Pool Connect."""

from __future__ import annotations

import base64
import logging
import re
import secrets
from dataclasses import dataclass
from urllib.parse import urljoin

import aiohttp

from ..const import DEFAULT_BASE_URL, DEFAULT_OAUTH_BASE_URL

_LOGGER = logging.getLogger(__name__)

POOL_ENTRY_RE = re.compile(
    r'"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})","([^"]*)"'
)

_AUTH_REDIRECT_PATTERNS = (
    r"https://www\.smartpoolconnect\.eu/auth\?[^\"'<>\s]+",
    r"https:\\/\\/www\.smartpoolconnect\.eu\\/auth\?[^\"'<>\s]+",
    r"/auth\?code=[^\"'<>\s]+",
    r'"redirect"\s*:\s*"([^"]+)"',
    r'"location"\s*:\s*"([^"]+)"',
)


class NorsupPortalLoginError(Exception):
    """Portal email/password login failed."""


@dataclass(frozen=True, slots=True)
class DiscoveredPool:
    """Pool listed in the owner portal."""

    pool_id: str
    name: str


def parse_pools_from_pool_data(text: str) -> list[DiscoveredPool]:
    """Extract pool UUIDs and display names from ``/pool.data``."""
    seen: set[str] = set()
    pools: list[DiscoveredPool] = []
    for match in POOL_ENTRY_RE.finditer(text):
        pool_id, name = match.group(1), match.group(2).strip()
        if pool_id in seen:
            continue
        seen.add(pool_id)
        pools.append(DiscoveredPool(pool_id=pool_id, name=name or pool_id[:8]))
    return pools


def _extract_auth_redirect(text: str) -> str | None:
    if not text:
        return None
    for pattern in _AUTH_REDIRECT_PATTERNS:
        found = re.search(pattern, text)
        if not found:
            continue
        result = found.group(1) if found.lastindex else found.group(0)
        return result.replace("\\/", "/")
    return None


def _to_login_data_url(login_page_url: str) -> str:
    if "/oauth/login?" not in login_page_url:
        raise NorsupPortalLoginError(f"Unexpected OAuth login URL: {login_page_url}")
    return login_page_url.replace("/oauth/login?", "/oauth/login.data?")


async def _get_login_page_url(
    session: aiohttp.ClientSession, base_url: str
) -> str:
    current_url = f"{base_url.rstrip('/')}/"
    for _ in range(8):
        async with session.get(current_url, allow_redirects=False) as resp:
            await resp.text()
            location = resp.headers.get("Location")
            if resp.status == 200 and "/oauth/login" in current_url:
                return current_url
            if not location:
                if "/oauth/login" in current_url:
                    return current_url
                raise NorsupPortalLoginError(
                    "Could not discover OAuth login URL: no redirect location"
                )
            if location.startswith("/"):
                location = urljoin(current_url, location)
            current_url = location
            if "/oauth/login" in current_url:
                return current_url
    raise NorsupPortalLoginError("Could not discover OAuth login URL after redirects")


async def _follow_auth_redirect(
    session: aiohttp.ClientSession, oauth_base_url: str, redirect_to: str
) -> None:
    current_url = redirect_to
    for _step in range(10):
        async with session.get(current_url, allow_redirects=False) as resp:
            body = await resp.text()
            next_url = (
                resp.headers.get("Location")
                or resp.headers.get("X-Remix-Redirect")
                or _extract_auth_redirect(body)
            )
            if "www.smartpoolconnect.eu/auth" in current_url and resp.status in (
                200,
                202,
                204,
                301,
                302,
                303,
            ):
                return
            if not next_url:
                if resp.status in (200, 202, 204):
                    if "oauth.smartpoolconnect.eu" in current_url:
                        raise NorsupPortalLoginError(
                            "OAuth flow ended on oauth domain without www callback"
                        )
                    return
                raise NorsupPortalLoginError(f"OAuth redirect failed: HTTP {resp.status}")
            if next_url.startswith("/"):
                next_url = urljoin(current_url, next_url)
            current_url = next_url
    raise NorsupPortalLoginError("Too many OAuth redirect steps")


async def async_portal_login(
    session: aiohttp.ClientSession,
    email: str,
    password: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    oauth_base_url: str = DEFAULT_OAUTH_BASE_URL,
) -> None:
    """Perform owner OAuth login; session cookie jar receives portal cookies."""
    oauth_base_url = oauth_base_url.rstrip("/")
    login_page_url = await _get_login_page_url(session, base_url)
    async with session.get(login_page_url) as resp:
        await resp.text()
        if resp.status >= 400:
            raise NorsupPortalLoginError(f"OAuth login page failed: HTTP {resp.status}")

    login_data_url = _to_login_data_url(login_page_url)
    device = base64.b64encode(str(secrets.randbelow(10_000_000_000)).encode()).decode()
    async with session.post(
        login_data_url,
        data={"email": email, "password": password, "device": device},
        headers={
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": oauth_base_url,
            "Referer": login_page_url,
        },
        allow_redirects=False,
    ) as resp:
        login_text = await resp.text()
        login_location = resp.headers.get("Location")
        login_remix_redirect = resp.headers.get("X-Remix-Redirect")
        if resp.status not in (200, 202, 204, 301, 302, 303):
            raise NorsupPortalLoginError(f"OAuth login.data failed: HTTP {resp.status}")
        next_url = (
            login_location
            or login_remix_redirect
            or _extract_auth_redirect(login_text)
            or login_page_url.replace("/oauth/login?", "/oauth/auth.data?")
        )
        if next_url.startswith("/"):
            next_url = urljoin(oauth_base_url, next_url)
        await _follow_auth_redirect(session, oauth_base_url, next_url)


async def async_fetch_pool_data_text(
    session: aiohttp.ClientSession,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    """GET ``/pool.data`` using cookies already on the session."""
    url = f"{base_url.rstrip('/')}/pool.data"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=25)) as resp:
        text = await resp.text()
        if resp.status in (401, 403):
            raise NorsupPortalLoginError("session not authorized for /pool.data")
        if resp.status >= 400:
            raise NorsupPortalLoginError(f"/pool.data failed: HTTP {resp.status}")
        return text


async def async_discover_pools(
    session: aiohttp.ClientSession,
    base_url: str = DEFAULT_BASE_URL,
) -> list[DiscoveredPool]:
    """Return pools visible to the logged-in portal session."""
    text = await async_fetch_pool_data_text(session, base_url)
    return parse_pools_from_pool_data(text)
