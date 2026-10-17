"""Unit tests for the Norsup API client (no live network)."""

from __future__ import annotations

import json
from pathlib import Path

import aiohttp
import pytest
from aioresponses import aioresponses
from custom_components.norsup_smartpool.api import (
    NorsupApiClient,
    NorsupAuthError,
    NorsupTransientError,
    async_validate_api_key,
)
from custom_components.norsup_smartpool.api.models import (
    parse_live_status,
    parse_pool_data_readings,
    parse_rest_pool,
)
from custom_components.norsup_smartpool.const import DEFAULT_API_BASE_URL

FIXTURES = Path(__file__).parent / "fixtures"
POOL_ID = "11111111-2222-3333-4444-555555555555"
GOOD_KEY = "spc_test_api_key_secret_value"
BASE = "https://test.example"


def _rest_pools_url() -> str:
    return f"{DEFAULT_API_BASE_URL}/pool"


def _rest_pool_url() -> str:
    return f"{DEFAULT_API_BASE_URL}/pool/{POOL_ID}"


def _live_url() -> str:
    return f"{BASE}/api/live-status/{POOL_ID}"


def _pool_status_url() -> str:
    return f"{BASE}/api/pool-status/{POOL_ID}"


def _pool_data_url() -> str:
    return f"{BASE}/pool.data"


@pytest.mark.asyncio
async def test_async_validate_api_key_success() -> None:
    pool_list = json.loads((FIXTURES / "rest_pool_list.json").read_text())
    with aioresponses() as m:
        m.get(_rest_pools_url(), payload=pool_list)
        async with aiohttp.ClientSession() as session:
            payload = await async_validate_api_key(session, POOL_ID, GOOD_KEY, BASE)
    assert "items" in payload


@pytest.mark.asyncio
async def test_async_validate_api_key_invalid() -> None:
    with aioresponses() as m:
        m.get(_rest_pools_url(), status=401, repeat=True)
        async with aiohttp.ClientSession() as session:
            with pytest.raises(NorsupAuthError):
                await async_validate_api_key(session, POOL_ID, "wrong-key", BASE)


@pytest.mark.asyncio
async def test_async_get_pool_data_parses_rest_endpoint() -> None:
    rest_pool = json.loads((FIXTURES / "rest_pool.json").read_text())

    with aioresponses() as m:
        m.get(_rest_pool_url(), payload=rest_pool)
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(session, POOL_ID, GOOD_KEY, BASE)
            data = await client.async_get_pool_data()

    assert data.pool_id == POOL_ID
    assert data.online is True
    assert data.water_temperature_c == 24.5
    assert data.pump_running is True
    assert data.pump_speed == "medium"
    assert data.ph == 7.2
    assert data.orp_mv == 650.0


@pytest.mark.asyncio
async def test_server_error_raises_transient() -> None:
    with aioresponses() as m:
        m.get(_rest_pool_url(), status=503, repeat=True)
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(session, POOL_ID, GOOD_KEY, BASE)
            with pytest.raises(NorsupTransientError):
                await client.async_get_pool_data()


def test_parse_pool_data_readings_from_text() -> None:
    ph, rx = parse_pool_data_readings('{"ph": 7.1, "rx": 700}', POOL_ID)
    assert ph == 7.1
    assert rx == 700.0


def test_parse_live_status_missing_fields() -> None:
    data = parse_live_status(POOL_ID, {})
    assert data.water_temperature_c is None
    assert data.ph is None


def test_parse_rest_pool_fixture() -> None:
    rest_pool = json.loads((FIXTURES / "rest_pool.json").read_text())
    data = parse_rest_pool(POOL_ID, rest_pool)
    assert data.ph == 7.2
