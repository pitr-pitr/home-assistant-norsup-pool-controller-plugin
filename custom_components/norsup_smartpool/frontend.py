"""Serve Lovelace card assets from the integration package."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_WWW_URL_PATH = f"/{DOMAIN}"
_WWW_DIR = Path(__file__).parent / "www"
_FRONTEND_FLAG = f"{DOMAIN}_frontend_registered"
_CARD_FILE = _WWW_DIR / "pool-health-card.js"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register static paths for the Pool Health Lovelace card (once per HA instance)."""
    if hass.data.get(_FRONTEND_FLAG):
        return

    if not _CARD_FILE.is_file():
        _LOGGER.error(
            "Pool Health card asset missing at %s — Lovelace resource "
            "/norsup_smartpool/pool-health-card.js will return 404 until "
            "you reinstall the full integration (including www/ and frontend.py)",
            _CARD_FILE,
        )
        return

    if "http" not in hass.config.components:
        await async_setup_component(hass, "http", {})

    if hass.http is None:
        _LOGGER.warning(
            "HTTP server not ready; Pool Health card static path was not registered"
        )
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
    _LOGGER.debug(
        "Registered Lovelace static path %s -> %s", _WWW_URL_PATH, _WWW_DIR
    )
