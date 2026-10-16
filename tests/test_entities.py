"""Entity helper tests."""

from __future__ import annotations

from custom_components.norsup_smartpool.entity import norsup_unique_id

POOL_ID = "11111111-2222-3333-4444-555555555555"


def test_unique_id_stable() -> None:
    assert norsup_unique_id(POOL_ID, "ph") == f"{POOL_ID}_ph"
    assert norsup_unique_id(POOL_ID, "water_temperature") == (
        f"{POOL_ID}_water_temperature"
    )
