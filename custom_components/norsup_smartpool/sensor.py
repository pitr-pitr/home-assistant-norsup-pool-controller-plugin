"""Sensor platform for Norsup Smartpool."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricPotential, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
        NorsupPhSensor(coordinator),
        NorsupOrpSensor(coordinator),
        NorsupPumpSpeedSensor(coordinator),
    ]

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
        return {
            "live_status": data.live_status,
            "pool_status": data.pool_status,
        }
