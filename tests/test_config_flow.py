"""Config flow and options flow tests (mocked API, no live network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aioresponses import aioresponses
from custom_components.norsup_smartpool.const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_POOL_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

FIXTURES = Path(__file__).parent / "fixtures"
POOL_ID = "11111111-2222-3333-4444-555555555555"
GOOD_KEY = "test_api_key_secret"
NEW_KEY = "rotated_api_key_secret"
BASE = "https://test.example"


def _live_url() -> str:
    return f"{BASE}/api/live-status/{POOL_ID}"


def _user_input(api_key: str = GOOD_KEY, pool_id: str = POOL_ID) -> dict[str, str]:
    return {
        CONF_API_KEY: api_key,
        CONF_POOL_ID: pool_id,
        CONF_BASE_URL: BASE,
    }


@pytest.mark.asyncio
async def test_config_flow_invalid_pool_id(hass: HomeAssistant) -> None:
    """Malformed pool UUID is rejected before calling the API."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        _user_input(pool_id="not-a-valid-uuid"),
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_config_flow_auth_failure(hass: HomeAssistant) -> None:
    """Invalid API key shows invalid_auth and does not create an entry."""
    with aioresponses() as m:
        m.get(_live_url(), status=401, repeat=True)
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            _user_input(api_key="wrong-key"),
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert not hass.config_entries.async_entries(DOMAIN)


@pytest.mark.asyncio
async def test_config_flow_success(hass: HomeAssistant) -> None:
    """Valid credentials create a single config entry with expected data."""
    live_status = json.loads((FIXTURES / "live_status.json").read_text())

    with aioresponses() as m:
        m.get(_live_url(), payload=live_status)
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            _user_input(),
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_POOL_ID] == POOL_ID
    assert result["data"][CONF_API_KEY] == GOOD_KEY
    assert result["data"][CONF_BASE_URL] == BASE
    assert result["options"][CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].unique_id == POOL_ID


@pytest.mark.asyncio
async def test_config_flow_aborts_duplicate_pool(hass: HomeAssistant) -> None:
    """Second setup for the same pool_id aborts as already configured."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=POOL_ID,
        data=_user_input(),
        options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        _user_input(),
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_options_flow_rotates_api_key(hass: HomeAssistant) -> None:
    """Options flow re-validates and persists a new API key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=POOL_ID,
        data=_user_input(),
        options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
    )
    entry.add_to_hass(hass)
    live_status = json.loads((FIXTURES / "live_status.json").read_text())

    with aioresponses() as m:
        m.get(_live_url(), payload=live_status)
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: NEW_KEY,
                CONF_SCAN_INTERVAL: 45,
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    updated = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated is not None
    assert updated.data[CONF_API_KEY] == NEW_KEY
    assert updated.options[CONF_SCAN_INTERVAL] == 45


@pytest.mark.asyncio
async def test_options_flow_invalid_key(hass: HomeAssistant) -> None:
    """Options flow rejects an invalid rotated key without changing stored data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=POOL_ID,
        data=_user_input(),
        options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
    )
    entry.add_to_hass(hass)

    with aioresponses() as m:
        m.get(_live_url(), status=403, repeat=True)
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "bad-rotation"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data[CONF_API_KEY] == GOOD_KEY
