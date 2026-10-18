"""Unit tests for the Norsup API client (no live network)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aioresponses import aioresponses
from custom_components.norsup_smartpool.api import (
    NorsupApiClient,
    NorsupAuthError,
    NorsupConnectionError,
    NorsupTransientError,
    async_list_pools_for_api_key,
    async_validate_api_key,
    async_validate_portal_credentials,
)
from custom_components.norsup_smartpool.api.models import (
    coerce_pump_speed_code,
    filter_module_from_pool_data,
    format_pump_speed,
    merge_filter_payload,
    merge_v3_analog_data,
    parse_live_status,
    parse_pool_data_readings,
    parse_rest_pool,
)
from custom_components.norsup_smartpool.const import (
    AUTH_TYPE_PORTAL,
    DEFAULT_API_BASE_URL,
)

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


def _filter_data_url() -> str:
    return f"{BASE}/pool/{POOL_ID}/filter.data"


def _v3_analog_url() -> str:
    return f"{DEFAULT_API_BASE_URL}/pool/{POOL_ID}/v3/analoge_data"


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


def test_parse_rest_pool_rx_metric_field() -> None:
    payload = json.loads((FIXTURES / "rest_pool_rx_metric.json").read_text())
    data = parse_rest_pool(POOL_ID, payload)
    assert data.orp_mv == 712.0
    assert data.free_chlorine_ppm == 1.2
    assert data.pump_speed == "medium"
    assert data.pump_running is True
    assert data.ambient_temperature_c == 18.5
    assert data.ph_target == 7.2
    assert data.orp_target == 700.0


def test_parse_rest_pool_clm_target_and_pump_fallback() -> None:
    """V3 pools expose ORP target under cl.config.clm and hide speed in config."""
    payload = {
        "pid": POOL_ID,
        "status": "online",
        "cl": {
            "config": {"clm": {"target": 675.0}},
            "metrics": {"clm": 681.5},
        },
        "filter": {
            "config": {
                "pump_speed": "high",
                "schedule_1": {
                    "enabled": True,
                    "pump_speed": "medium",
                    "start_time": "08:00",
                    "stop_time": "20:00",
                },
            },
            "metrics": {"pump_speed": 0, "error_code": 0},
            "status": {"pump_speed": 0, "pump_status": 2, "status": 4},
        },
        "aux_1": {
            "config": {
                "name": "flow",
                "always_on": False,
                "schedule": {"enabled": False, "start_time": "00:00", "stop_time": "00:00"},
            },
            "status": {"status": 1},
        },
    }
    data = parse_rest_pool(POOL_ID, payload)
    assert data.orp_mv == 681.5
    assert data.orp_target == 675.0
    assert data.free_chlorine_ppm is None
    assert data.pump_speed == "high"
    assert data.pump_running is True
    assert data.filter_status_code == 4
    assert len(data.aux_channels) == 1
    assert data.aux_channels[0].name == "flow"
    assert data.aux_channels[0].active is True


def test_merge_v3_analog_ambient_and_salt() -> None:
    data = parse_live_status(POOL_ID, {"online": True})
    data = merge_v3_analog_data(
        data,
        {
            "data": {
                "ambient_t": 108.74,
                "ambient_temp_input_error": 0,
                "tds_salt": 3350.6,
            }
        },
    )
    assert data.ambient_temperature_c == pytest.approx(10.874)
    assert data.tds_salt_ppm == pytest.approx(3350.6)


def test_format_pump_speed_codes() -> None:
    assert format_pump_speed(2) == "medium"
    assert format_pump_speed(-1) == "disabled"
    assert format_pump_speed("high") == "high"


def test_coerce_pump_speed_code() -> None:
    assert coerce_pump_speed_code(2) == 2
    assert coerce_pump_speed_code("medium") == 2
    assert coerce_pump_speed_code("high") == 3


def test_filter_module_from_pool_data() -> None:
    data = parse_live_status(
        POOL_ID,
        {
            "filter": {
                "config": {"always_active": True, "pump_speed": "high"},
                "status": {"pump_speed": 2},
            }
        },
    )
    filter_mod = filter_module_from_pool_data(data)
    assert filter_mod["config"]["always_active"] is True
    assert filter_mod["status"]["pump_speed"] == 2


def test_merge_v3_analog_fills_orp() -> None:
    data = parse_live_status(POOL_ID, {"online": True})
    data = merge_v3_analog_data(
        data,
        {"data": {"rx": 680, "ph": 7.1, "water_t": 25.0}},
    )
    assert data.orp_mv == 680.0
    assert data.ph == 7.1
    assert data.water_temperature_c == 25.0


def test_merge_filter_payload_for_portal() -> None:
    data = parse_live_status(POOL_ID, {"pump_status": 1})
    data = merge_filter_payload(
        data,
        {"metrics": {"pump_speed": 3}, "status": {"pump_status": 8}},
    )
    assert data.pump_speed == "high"
    assert data.pump_running is True


def test_live_status_numeric_pump_speed() -> None:
    data = parse_live_status(POOL_ID, {"pump_speed": 2, "pump_status": 10})
    assert data.pump_speed == "medium"
    assert data.pump_running is True


@pytest.mark.asyncio
async def test_async_get_pool_data_v3_analog_fallback() -> None:
    """REST /pool gaps are filled from V3 analoge_data."""
    sparse_pool = {
        "pid": POOL_ID,
        "status": "online",
        "filter": {"metrics": {"pump_speed": 2}, "status": {"pump_status": 10}},
    }
    analog = {"data": {"rx": 701, "ph": 7.0, "water_t": 22.0}}

    with aioresponses() as m:
        m.get(_rest_pool_url(), payload=sparse_pool)
        m.get(_v3_analog_url(), payload=analog)
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(session, POOL_ID, GOOD_KEY, BASE)
            data = await client.async_get_pool_data()

    assert data.orp_mv == 701.0
    assert data.ph == 7.0
    assert data.water_temperature_c == 22.0
    assert data.pump_speed == "medium"


@pytest.mark.asyncio
async def test_async_get_pool_data_portal_merges_endpoints() -> None:
    """Portal login path batches live-status, pool.data, and filter.data."""
    live = json.loads((FIXTURES / "live_status.json").read_text())
    pool_data = json.dumps(json.loads((FIXTURES / "pool_data.json").read_text()))
    filter_payload = {
        "metrics": {"pump_speed": 3, "pump_current": 1.1},
        "status": {"pump_status": 8},
    }

    with aioresponses() as m:
        m.get(_live_url(), payload=live)
        m.get(_pool_status_url(), payload={})
        m.get(_pool_data_url(), body=pool_data)
        m.get(_filter_data_url(), payload=filter_payload)
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(
                session,
                POOL_ID,
                api_key=None,
                base_url=BASE,
                username="owner@example.com",
                password="secret",
                auth_type=AUTH_TYPE_PORTAL,
            )
            client._ensure_portal_session = AsyncMock()  # noqa: SLF001
            client._portal_logged_in = True  # noqa: SLF001
            data = await client.async_get_pool_data()

    assert data.water_temperature_c == 24.5
    assert data.ph == 7.2
    assert data.orp_mv == 650.0
    assert data.pump_speed == "high"
    assert data.pump_current_a == 1.1
    assert data.pump_running is True


@pytest.mark.asyncio
async def test_async_validate_api_key_pool_not_in_list() -> None:
    pool_list = {"items": [{"pid": "00000000-0000-0000-0000-000000000001", "name": "Other"}]}
    with aioresponses() as m:
        m.get(_rest_pools_url(), payload=pool_list)
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(session, POOL_ID, GOOD_KEY, BASE)
            with pytest.raises(NorsupAuthError, match="pool_not_found"):
                await client.async_validate_api_key()


@pytest.mark.asyncio
async def test_async_list_pools_for_api_key() -> None:
    pool_list = json.loads((FIXTURES / "rest_pool_list.json").read_text())
    with aioresponses() as m:
        m.get(_rest_pools_url(), payload=pool_list)
        async with aiohttp.ClientSession() as session:
            pools = await async_list_pools_for_api_key(session, GOOD_KEY)
    assert pools
    assert pools[0][0]


@pytest.mark.asyncio
async def test_legacy_www_auth_retries_headers() -> None:
    """Non-REST clients probe X-API-Key then Bearer on the portal host."""
    live = json.loads((FIXTURES / "live_status.json").read_text())

    with aioresponses() as m:
        m.get(_live_url(), status=401)
        m.get(_live_url(), status=401)
        m.get(_live_url(), payload=live)
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(session, POOL_ID, GOOD_KEY, BASE)
            client._rest_api = False  # noqa: SLF001
            payload = await client.async_get_live_status()
    assert payload["online"] is True


@pytest.mark.asyncio
async def test_optional_endpoint_404_returns_empty() -> None:
    with aioresponses() as m:
        m.get(_pool_status_url(), status=404)
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(session, POOL_ID, GOOD_KEY, BASE)
            client._rest_api = False  # noqa: SLF001
            client._auth_headers = {"X-API-Key": GOOD_KEY}  # noqa: SLF001
            payload = await client.async_get_pool_status()
    assert payload == {}


@pytest.mark.asyncio
async def test_optional_non_json_response() -> None:
    with aioresponses() as m:
        m.get(_pool_status_url(), status=200, body="not-json")
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(session, POOL_ID, GOOD_KEY, BASE)
            client._rest_api = False  # noqa: SLF001
            client._auth_headers = {"X-API-Key": GOOD_KEY}  # noqa: SLF001
            payload = await client.async_get_pool_status()
    assert payload == {}


@pytest.mark.asyncio
async def test_rest_get_json_invalid_response() -> None:
    with aioresponses() as m:
        m.get(_rest_pool_url(), status=200, body="[]")
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(session, POOL_ID, GOOD_KEY, BASE)
            with pytest.raises(NorsupAuthError, match="invalid_response"):
                await client.async_get_pool_data()


@pytest.mark.asyncio
async def test_rest_get_json_requires_api_key() -> None:
    async with aiohttp.ClientSession() as session:
        client = NorsupApiClient(session, POOL_ID, "", BASE)
        with pytest.raises(NorsupAuthError, match="invalid_credentials"):
            await client._async_rest_get_json("/pool")  # noqa: SLF001


@pytest.mark.asyncio
async def test_rest_connection_error() -> None:
    with aioresponses() as m:
        m.get(_rest_pool_url(), exception=aiohttp.ClientError("offline"))
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(session, POOL_ID, GOOD_KEY, BASE)
            with pytest.raises(NorsupConnectionError):
                await client.async_get_pool_data()


@pytest.mark.asyncio
async def test_live_status_pool_not_found() -> None:
    with aioresponses() as m:
        m.get(_live_url(), status=404)
        async with aiohttp.ClientSession() as session:
            client = NorsupApiClient(session, POOL_ID, GOOD_KEY, BASE)
            client._rest_api = False  # noqa: SLF001
            client._auth_headers = {"X-API-Key": GOOD_KEY}  # noqa: SLF001
            with pytest.raises(NorsupAuthError, match="pool_not_found"):
                await client.async_get_live_status()


@pytest.mark.asyncio
async def test_async_validate_portal_credentials() -> None:
    live = json.loads((FIXTURES / "live_status.json").read_text())
    with aioresponses() as m:
        m.get(_live_url(), payload=live)
        async with aiohttp.ClientSession() as session:
            with patch(
                "custom_components.norsup_smartpool.api.client.async_portal_login",
                new_callable=AsyncMock,
            ):
                payload = await async_validate_portal_credentials(
                    session,
                    POOL_ID,
                    "owner@example.com",
                    "secret",
                    base_url=BASE,
                )
    assert payload["online"] is True
