"""Lovelace Pool Health card assets."""

from pathlib import Path

import pytest
from custom_components.norsup_smartpool import async_setup
from custom_components.norsup_smartpool.frontend import _FRONTEND_FLAG, _WWW_URL_PATH
from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

CARD_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "norsup_smartpool"
    / "www"
    / "pool-health-card.js"
)


def test_pool_health_card_bundled() -> None:
    """Card script ships with the integration for Lovelace."""
    assert CARD_PATH.is_file()
    text = CARD_PATH.read_text(encoding="utf-8")
    assert "norsup-pool-health-card" in text
    assert "window.customCards" in text


@pytest.mark.asyncio
async def test_pool_health_card_registers_static_path(hass: HomeAssistant) -> None:
    """async_setup registers /norsup_smartpool for the Lovelace resource URL."""
    assert await async_setup(hass, {})
    assert hass.data[_FRONTEND_FLAG] is True

    resource_paths = {
        getattr(resource, "canonical", "")
        for resource in hass.http.app.router.resources()
    }
    assert _WWW_URL_PATH in resource_paths
