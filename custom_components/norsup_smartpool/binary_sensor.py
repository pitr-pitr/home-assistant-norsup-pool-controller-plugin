"""Binary sensor platform for Norsup Smartpool."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NorsupDataUpdateCoordinator
from .entity import NorsupSmartpoolEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Norsup Smartpool binary sensors."""
    coordinator: NorsupDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    async_add_entities(
        [
            NorsupPumpRunningBinarySensor(coordinator),
            NorsupCloudOnlineBinarySensor(coordinator),
        ]
    )


class NorsupPumpRunningBinarySensor(NorsupSmartpoolEntity, BinarySensorEntity):
    """Whether the circulation pump is running."""

    _attr_translation_key = "pump_running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "pump_running")

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.pump_running


class NorsupCloudOnlineBinarySensor(NorsupSmartpoolEntity, BinarySensorEntity):
    """Whether Smart Pool Connect returned a healthy live-status snapshot."""

    _attr_translation_key = "cloud_online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "cloud_online")

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.online
