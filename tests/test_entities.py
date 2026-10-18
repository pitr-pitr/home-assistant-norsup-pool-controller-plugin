"""Entity helper tests."""

from __future__ import annotations

import inspect

from custom_components.norsup_smartpool import binary_sensor, sensor
from custom_components.norsup_smartpool.entity import norsup_unique_id

POOL_ID = "11111111-2222-3333-4444-555555555555"


def test_unique_id_stable() -> None:
    assert norsup_unique_id(POOL_ID, "ph") == f"{POOL_ID}_ph"
    assert norsup_unique_id(POOL_ID, "water_temperature") == (
        f"{POOL_ID}_water_temperature"
    )


def test_only_diagnostics_sensor_declares_disabled_by_default() -> None:
    sensor_path = inspect.getfile(sensor)
    text = open(sensor_path, encoding="utf-8").read()
    assert text.count("_attr_entity_registry_enabled_default = False") == 1
    assert "NorsupDiagnosticsSensor" in text


def test_aux_binary_sensors_enabled_by_default() -> None:
    enabled_default = getattr(
        binary_sensor.NorsupAuxChannelBinarySensor,
        "_attr_entity_registry_enabled_default",
        True,
    )
    assert enabled_default is not False
