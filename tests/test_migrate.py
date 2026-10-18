"""Config-entry migration tests."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.norsup_smartpool.const import CONF_POOL_ID, DOMAIN
from custom_components.norsup_smartpool.entity import norsup_unique_id
from custom_components.norsup_smartpool.migrate import async_enable_integration_disabled_entities

POOL_ID = "11111111-2222-3333-4444-555555555555"


def test_migration_reenables_integration_disabled_entities(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_POOL_ID: POOL_ID},
        unique_id=POOL_ID,
    )
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    ph_uid = norsup_unique_id(POOL_ID, "ph_target")
    diag_uid = norsup_unique_id(POOL_ID, "diagnostics")
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        ph_uid,
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        diag_uid,
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )

    async_enable_integration_disabled_entities(hass, entry)

    ph_entity_id = registry.async_get_entity_id("sensor", DOMAIN, ph_uid)
    diag_entity_id = registry.async_get_entity_id("sensor", DOMAIN, diag_uid)
    assert ph_entity_id is not None
    assert diag_entity_id is not None
    assert registry.async_get(ph_entity_id).disabled_by is None
    assert (
        registry.async_get(diag_entity_id).disabled_by
        == er.RegistryEntryDisabler.INTEGRATION
    )
