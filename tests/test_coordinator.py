"""Coordinator behavior tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from custom_components.norsup_smartpool.api import (
    NorsupAuthError,
    NorsupPoolData,
    NorsupTransientError,
)
from custom_components.norsup_smartpool.coordinator import NorsupDataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

POOL_ID = "11111111-2222-3333-4444-555555555555"


def _make_coordinator(hass) -> NorsupDataUpdateCoordinator:
    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test-entry"
    entry.data = {"pool_id": POOL_ID, "api_key": "secret", "base_url": "http://test"}
    client = MagicMock()
    client.pool_id = POOL_ID
    client.async_get_pool_data = AsyncMock(
        return_value=NorsupPoolData(pool_id=POOL_ID, online=True)
    )
    return NorsupDataUpdateCoordinator(hass, entry, client)


@pytest.mark.asyncio
async def test_coordinator_update_success(hass) -> None:
    coordinator = _make_coordinator(hass)
    data = await coordinator._async_update_data()
    assert data.online is True
    assert coordinator._consecutive_failures == 0


@pytest.mark.asyncio
async def test_coordinator_auth_failure(hass, caplog: pytest.LogCaptureFixture) -> None:
    coordinator = _make_coordinator(hass)
    coordinator._client.async_get_pool_data = AsyncMock(side_effect=NorsupAuthError("x"))

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert "secret" not in caplog.text
    assert "api_key" not in caplog.text.lower()


@pytest.mark.asyncio
async def test_coordinator_repeated_failure_single_warning(
    hass,
    caplog: pytest.LogCaptureFixture,
) -> None:
    coordinator = _make_coordinator(hass)
    coordinator._client.async_get_pool_data = AsyncMock(
        side_effect=NorsupTransientError("server_error_503")
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    with caplog.at_level("WARNING"), pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert POOL_ID in message
    assert "secret" not in message
