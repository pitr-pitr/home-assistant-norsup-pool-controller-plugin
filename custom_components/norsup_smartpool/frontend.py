"""Serve Lovelace card assets from the integration package."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_WWW_URL_PATH = f"/{DOMAIN}"
_WWW_DIR = Path(__file__).parent / "www"
_FRONTEND_FLAG = f"{DOMAIN}_frontend_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register static paths for the Pool Health Lovelace card (once per HA instance)."""
    if hass.data.get(_FRONTEND_FLAG):
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                _WWW_URL_PATH,
                str(_WWW_DIR),
                cache_headers=False,
            )
        ]
    )
    hass.data[_FRONTEND_FLAG] = True
