"""Config-entry migrations for Norsup Smartpool."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import CONF_POOL_ID

# Entities that stay integration-disabled (opt-in only).
_INTEGRATION_DISABLED_KEYS = frozenset({"diagnostics"})


@callback
def async_enable_integration_disabled_entities(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Turn on entities that were disabled by integration defaults in older releases."""
    pool_id = entry.data.get(CONF_POOL_ID)
    if not pool_id:
        return
    prefix = f"{pool_id}_"
    registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity_entry.disabled_by != er.RegistryEntryDisabler.INTEGRATION:
            continue
        unique_id = entity_entry.unique_id
        if not unique_id or not unique_id.startswith(prefix):
            continue
        key = unique_id[len(prefix) :]
        if key in _INTEGRATION_DISABLED_KEYS:
            continue
        registry.async_update_entity(entity_entry.entity_id, disabled_by=None)
