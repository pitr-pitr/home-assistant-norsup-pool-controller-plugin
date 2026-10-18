"""Binary sensor platform for Norsup Smartpool."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.coverage import CALIBRATION_FLAG_KEYS
from .api.models import (
    NorsupAuxChannel,
    _coerce_bool,
    _module_config,
    filter_module_from_pool_data,
)
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
        NorsupFilterAlwaysActiveBinarySensor(coordinator),
    ]
    for index in range(1, 5):
        entities.append(NorsupAuxChannelBinarySensor(coordinator, f"aux_{index}"))
    for schedule_index in range(1, 4):
        entities.append(
            NorsupFilterScheduleEnabledBinarySensor(coordinator, schedule_index)
        )
    entities.append(NorsupSensorFaultsBinarySensor(coordinator))
    for flag_key in CALIBRATION_FLAG_KEYS:
        entities.append(NorsupCalibrationFlagBinarySensor(coordinator, flag_key))

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


class NorsupFilterAlwaysActiveBinarySensor(NorsupSmartpoolEntity, BinarySensorEntity):
    """Whether filter.config.always_active is enabled on the controller."""

    _attr_translation_key = "filter_always_active"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "filter_always_active")

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        config = _module_config(filter_module_from_pool_data(self.coordinator.data))
        if not config:
            return None
        return _coerce_bool(config.get("always_active"))


class NorsupFilterScheduleEnabledBinarySensor(NorsupSmartpoolEntity, BinarySensorEntity):
    """Whether a filter schedule slot is enabled in filter.config."""

    def __init__(
        self, coordinator: NorsupDataUpdateCoordinator, schedule_index: int
    ) -> None:
        self._schedule_index = schedule_index
        super().__init__(coordinator, f"filter_schedule_{schedule_index}_enabled")
        self._attr_translation_key = "filter_schedule_enabled"
        self._attr_translation_placeholders = {"schedule": str(schedule_index)}

    def _schedule_config(self) -> dict[str, object] | None:
        if self.coordinator.data is None:
            return None
        config = _module_config(filter_module_from_pool_data(self.coordinator.data))
        sched = config.get(f"schedule_{self._schedule_index}")
        return sched if isinstance(sched, dict) else None

    @property
    def available(self) -> bool:
        return self._schedule_config() is not None

    @property
    def is_on(self) -> bool | None:
        sched = self._schedule_config()
        if sched is None:
            return None
        return _coerce_bool(sched.get("enabled"))


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


class NorsupSensorFaultsBinarySensor(NorsupSmartpoolEntity, BinarySensorEntity):
    """Any V3 analog *_input_error flag is non-zero."""

    _attr_translation_key = "sensor_faults"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "sensor_faults")

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        errors = self.coordinator.data.input_errors
        if not errors:
            return False
        return any(value != 0 for value in errors.values())

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        if self.coordinator.data is None:
            return {}
        return dict(self.coordinator.data.input_errors)


class NorsupCalibrationFlagBinarySensor(NorsupSmartpoolEntity, BinarySensorEntity):
    """One V3 calibration_* flag from analoge_data."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self, coordinator: NorsupDataUpdateCoordinator, flag_key: str
    ) -> None:
        self._flag_key = flag_key
        super().__init__(coordinator, flag_key)
        self._attr_translation_key = flag_key

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        flags = self.coordinator.data.calibration_flags
        if self._flag_key not in flags:
            return None
        return flags[self._flag_key]
