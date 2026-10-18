"""Binary sensor platform for Norsup Smartpool."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.models import NorsupAuxChannel
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

    entities: list[BinarySensorEntity] = [
        NorsupPumpRunningBinarySensor(coordinator),
        NorsupCloudOnlineBinarySensor(coordinator),
    ]
    for index in range(1, 5):
        entities.append(NorsupAuxChannelBinarySensor(coordinator, f"aux_{index}"))

    async_add_entities(entities)


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


class NorsupAuxChannelBinarySensor(NorsupSmartpoolEntity, BinarySensorEntity):
    """Auxiliary output (flow, disinfection, …) from the REST pool payload."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: NorsupDataUpdateCoordinator, aux_key: str) -> None:
        super().__init__(coordinator, aux_key)
        self._aux_key = aux_key

    def _channel_state(self) -> NorsupAuxChannel | None:
        if self.coordinator.data is None:
            return None
        for item in self.coordinator.data.aux_channels:
            if item.key == self._aux_key:
                return item
        return None

    @property
    def available(self) -> bool:
        return self._channel_state() is not None

    @property
    def name(self) -> str:
        channel = self._channel_state()
        if channel is None:
            return self._aux_key.replace("_", " ").title()
        label = channel.name.replace("_", " ").strip().title() or channel.key
        return label

    @property
    def is_on(self) -> bool | None:
        channel = self._channel_state()
        if channel is None:
            return None
        return channel.active

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        channel = self._channel_state()
        if channel is None:
            return {}
        attrs: dict[str, object] = {"aux_name": channel.name}
        if channel.always_on is not None:
            attrs["always_on"] = channel.always_on
        if channel.flow is not None:
            attrs["flow"] = channel.flow
        if channel.cover_closed is not None:
            attrs["cover_closed"] = channel.cover_closed
        if channel.schedule_enabled is not None:
            attrs["schedule_enabled"] = channel.schedule_enabled
        if channel.schedule_start:
            attrs["schedule_start"] = channel.schedule_start
        if channel.schedule_stop:
            attrs["schedule_stop"] = channel.schedule_stop
        return attrs
