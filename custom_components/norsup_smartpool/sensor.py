"""Sensor platform for Norsup Smartpool."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.coverage import v3_adc_diagnostic_attributes, v3_misc_diagnostic_attributes
from .api.models import (
    _module_config,
    _module_status,
    coerce_pump_speed_code,
    filter_module_from_pool_data,
    format_pump_speed,
)
from .const import CONF_ENABLE_DIAGNOSTICS, DOMAIN
from .coordinator import NorsupDataUpdateCoordinator
from .entity import NorsupSmartpoolEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Norsup Smartpool sensors."""
    coordinator: NorsupDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    entities: list[SensorEntity] = [
        NorsupWaterTemperatureSensor(coordinator),
        NorsupAmbientTemperatureSensor(coordinator),
        NorsupPhSensor(coordinator),
        NorsupOrpSensor(coordinator),
        NorsupFreeChlorineSensor(coordinator),
        NorsupTdsSaltSensor(coordinator),
        NorsupPumpSpeedSensor(coordinator),
        NorsupPumpCurrentSensor(coordinator),
        NorsupPhTargetSensor(coordinator),
        NorsupOrpTargetSensor(coordinator),
        NorsupPhDosingStatusSensor(coordinator),
        NorsupClDosingStatusSensor(coordinator),
        NorsupFilterErrorSensor(coordinator),
        NorsupFilterStatusSensor(coordinator),
        NorsupFilterConfigPumpSpeedSensor(coordinator),
        NorsupFilterStatusPumpSpeedCodeSensor(coordinator),
    ]
    for schedule_index in range(1, 4):
        entities.extend(
            [
                NorsupFilterScheduleStartTimeSensor(coordinator, schedule_index),
                NorsupFilterScheduleStopTimeSensor(coordinator, schedule_index),
                NorsupFilterSchedulePumpSpeedSensor(coordinator, schedule_index),
                NorsupFilterScheduleDaysSensor(coordinator, schedule_index),
            ]
        )

    if entry.options.get(CONF_ENABLE_DIAGNOSTICS):
        entities.append(NorsupDiagnosticsSensor(coordinator))

    async_add_entities(entities)


class NorsupWaterTemperatureSensor(NorsupSmartpoolEntity, SensorEntity):
    """Pool water temperature from live status."""

    _attr_translation_key = "water_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "water_temperature")

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.water_temperature_c


class NorsupAmbientTemperatureSensor(NorsupSmartpoolEntity, SensorEntity):
    """Ambient air temperature when reported by the controller."""

    _attr_translation_key = "ambient_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "ambient_temperature")

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.ambient_temperature_c


class NorsupPhSensor(NorsupSmartpoolEntity, SensorEntity):
    """Pool pH from /pool.data."""

    _attr_translation_key = "ph"
    _attr_native_unit_of_measurement = "pH"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "ph")

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.ph


class NorsupOrpSensor(NorsupSmartpoolEntity, SensorEntity):
    """Pool ORP / Rx from /pool.data."""

    _attr_translation_key = "orp"
    _attr_native_unit_of_measurement = UnitOfElectricPotential.MILLIVOLT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "orp")

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.orp_mv


class NorsupFreeChlorineSensor(NorsupSmartpoolEntity, SensorEntity):
    """Free chlorine (CLM probe) when reported."""

    _attr_translation_key = "free_chlorine"
    _attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "free_chlorine")

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.free_chlorine_ppm


class NorsupTdsSaltSensor(NorsupSmartpoolEntity, SensorEntity):
    """TDS salt estimate from V3 analog data when available."""

    _attr_translation_key = "tds_salt"
    _attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "tds_salt")

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.tds_salt_ppm


class NorsupPumpSpeedSensor(NorsupSmartpoolEntity, SensorEntity):
    """Reported filter pump speed (read-only)."""

    _attr_translation_key = "pump_speed"
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "pump_speed")

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.pump_speed

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        if self.coordinator.data is None:
            return {}
        data = self.coordinator.data
        attrs: dict[str, object] = {}
        if data.filter_pump_status is not None:
            attrs["filter_pump_status_code"] = data.filter_pump_status
        if data.filter_status_code is not None:
            attrs["filter_status_code"] = data.filter_status_code
        if data.filter_error_code is not None:
            attrs["filter_error_code"] = data.filter_error_code
        filter_mod = data.live_status.get("filter")
        if isinstance(filter_mod, dict):
            config = filter_mod.get("config")
            if isinstance(config, dict):
                attrs["filter_config"] = config
        return attrs


class NorsupPumpCurrentSensor(NorsupSmartpoolEntity, SensorEntity):
    """Filter pump motor current."""

    _attr_translation_key = "pump_current"
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "pump_current")

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.pump_current_a


class NorsupPhTargetSensor(NorsupSmartpoolEntity, SensorEntity):
    """Configured pH dosing target."""

    _attr_translation_key = "ph_target"
    _attr_native_unit_of_measurement = "pH"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "ph_target")

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.ph_target


class NorsupOrpTargetSensor(NorsupSmartpoolEntity, SensorEntity):
    """Configured ORP / Rx dosing target."""

    _attr_translation_key = "orp_target"
    _attr_native_unit_of_measurement = UnitOfElectricPotential.MILLIVOLT

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "orp_target")

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.orp_target


class NorsupPhDosingStatusSensor(NorsupSmartpoolEntity, SensorEntity):
    """pH dosing controller status code from the REST pool tree."""

    _attr_translation_key = "ph_dosing_status"
    _attr_icon = "mdi:flask"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "ph_dosing_status")

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.ph_dosing_status

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        if self.coordinator.data is None or self.coordinator.data.ph_calibration is None:
            return {}
        return {"calibration": self.coordinator.data.ph_calibration}


class NorsupClDosingStatusSensor(NorsupSmartpoolEntity, SensorEntity):
    """Chlorine / ORP dosing controller status code."""

    _attr_translation_key = "cl_dosing_status"
    _attr_icon = "mdi:water-opacity"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "cl_dosing_status")

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.cl_dosing_status

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        if self.coordinator.data is None or self.coordinator.data.cl_calibration is None:
            return {}
        return {"calibration": self.coordinator.data.cl_calibration}


class NorsupFilterErrorSensor(NorsupSmartpoolEntity, SensorEntity):
    """Filter pump error code from filter.metrics."""

    _attr_translation_key = "filter_error"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "filter_error")

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.filter_error_code


class NorsupFilterStatusSensor(NorsupSmartpoolEntity, SensorEntity):
    """Filter module status code from filter.status."""

    _attr_translation_key = "filter_status"
    _attr_icon = "mdi:filter"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "filter_status")

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.filter_status_code


class NorsupFilterConfigPumpSpeedSensor(NorsupSmartpoolEntity, SensorEntity):
    """Configured default pump speed from filter.config (not live status)."""

    _attr_translation_key = "filter_config_pump_speed"
    _attr_icon = "mdi:fan-chevron-down"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "filter_config_pump_speed")

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        config = _module_config(filter_module_from_pool_data(self.coordinator.data))
        raw = config.get("pump_speed")
        return format_pump_speed(raw) if raw is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        if self.coordinator.data is None:
            return {}
        live = self.coordinator.data.pump_speed
        if live is None:
            return {}
        return {"live_pump_speed": live}


class NorsupFilterStatusPumpSpeedCodeSensor(NorsupSmartpoolEntity, SensorEntity):
    """Raw filter.status.pump_speed code alongside the human-readable pump speed."""

    _attr_translation_key = "filter_status_pump_speed_code"
    _attr_icon = "mdi:numeric"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "filter_status_pump_speed_code")

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        status = _module_status(filter_module_from_pool_data(self.coordinator.data))
        return coerce_pump_speed_code(status.get("pump_speed"))

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        if self.coordinator.data is None:
            return {}
        attrs: dict[str, object] = {}
        if self.coordinator.data.pump_speed is not None:
            attrs["pump_speed_label"] = self.coordinator.data.pump_speed
        code = self.native_value
        if code is not None:
            attrs["pump_speed_code"] = code
        return attrs


class _NorsupFilterScheduleSensorBase(NorsupSmartpoolEntity, SensorEntity):
    """Shared helpers for filter.config schedule_* slots."""

    def __init__(
        self,
        coordinator: NorsupDataUpdateCoordinator,
        schedule_index: int,
        key_suffix: str,
        translation_key: str,
    ) -> None:
        self._schedule_index = schedule_index
        super().__init__(coordinator, f"filter_schedule_{schedule_index}_{key_suffix}")
        self._attr_translation_key = translation_key
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


class NorsupFilterScheduleStartTimeSensor(_NorsupFilterScheduleSensorBase):
    """Start time for a filter schedule slot."""

    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator, schedule_index: int) -> None:
        super().__init__(
            coordinator,
            schedule_index,
            "start_time",
            "filter_schedule_start_time",
        )

    @property
    def native_value(self) -> str | None:
        sched = self._schedule_config()
        if sched is None:
            return None
        start = sched.get("start_time")
        return str(start) if start else None


class NorsupFilterScheduleStopTimeSensor(_NorsupFilterScheduleSensorBase):
    """Stop time for a filter schedule slot."""

    _attr_icon = "mdi:clock-end"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator, schedule_index: int) -> None:
        super().__init__(
            coordinator,
            schedule_index,
            "stop_time",
            "filter_schedule_stop_time",
        )

    @property
    def native_value(self) -> str | None:
        sched = self._schedule_config()
        if sched is None:
            return None
        stop = sched.get("stop_time")
        return str(stop) if stop else None


class NorsupFilterSchedulePumpSpeedSensor(_NorsupFilterScheduleSensorBase):
    """Configured pump speed for a filter schedule slot."""

    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator, schedule_index: int) -> None:
        super().__init__(
            coordinator,
            schedule_index,
            "pump_speed",
            "filter_schedule_pump_speed",
        )

    @property
    def native_value(self) -> str | None:
        sched = self._schedule_config()
        if sched is None:
            return None
        raw = sched.get("pump_speed")
        return format_pump_speed(raw) if raw is not None else None


class NorsupFilterScheduleDaysSensor(_NorsupFilterScheduleSensorBase):
    """Active weekdays for a filter schedule slot."""

    _attr_icon = "mdi:calendar-week"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator, schedule_index: int) -> None:
        super().__init__(
            coordinator,
            schedule_index,
            "days",
            "filter_schedule_days",
        )

    @property
    def native_value(self) -> str | None:
        sched = self._schedule_config()
        if sched is None:
            return None
        days = sched.get("days")
        if not isinstance(days, list) or not days:
            return "—"
        return ", ".join(str(day) for day in days)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        sched = self._schedule_config()
        if sched is None:
            return {}
        days = sched.get("days")
        if isinstance(days, list):
            return {"days": days}
        return {}


class NorsupDiagnosticsSensor(NorsupSmartpoolEntity, SensorEntity):
    """Raw API fragments for troubleshooting (opt-in via integration options)."""

    _attr_translation_key = "diagnostics"
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:bug"

    def __init__(self, coordinator: NorsupDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "diagnostics")

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return "ok" if self.coordinator.data.online else "offline"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        if self.coordinator.data is None:
            return {}
        data = self.coordinator.data
        attrs: dict[str, object] = {
            "live_status": data.live_status,
            "pool_status": data.pool_status,
            "ph_dosing_status": data.ph_dosing_status,
            "cl_dosing_status": data.cl_dosing_status,
            "filter_pump_status": data.filter_pump_status,
            "pool_id": data.pool_id,
            "mac_address": data.live_status.get("mac_address"),
            "api_version": data.live_status.get("api_version"),
            "pool_activity_at": data.live_status.get("activity_at"),
            "pool_created_at": data.live_status.get("created_at"),
        }
        v3 = data.v3_analog_data
        if v3:
            attrs.update(v3_adc_diagnostic_attributes(v3))
            attrs.update(v3_misc_diagnostic_attributes(v3))
        return attrs
