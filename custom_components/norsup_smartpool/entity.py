"""Shared entity helpers for Norsup Smartpool."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NorsupDataUpdateCoordinator


def norsup_unique_id(pool_id: str, key: str) -> str:
    """Stable unique_id across restarts (see ARCHITECTURE.md §6)."""
    return f"{pool_id}_{key}"


class NorsupSmartpoolEntity(CoordinatorEntity[NorsupDataUpdateCoordinator]):
    """Base class for Norsup pool entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NorsupDataUpdateCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = norsup_unique_id(coordinator.pool_id, key)

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data
        name = "Norsup Smartpool"
        if data:
            if data.pool_name and data.pool_name.strip():
                name = data.pool_name.strip()
            elif data.pool_status:
                portal_name = data.pool_status.get("name") or data.pool_status.get(
                    "pool_name"
                )
                if isinstance(portal_name, str) and portal_name.strip():
                    name = portal_name.strip()

        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.pool_id)},
            name=name,
            manufacturer="Norsup",
            model="Smart Pool Connect",
        )
