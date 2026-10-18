"""Ensure every API dump leaf is mapped to an entity or diagnostics attribute."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.norsup_smartpool.api.coverage import (
    unmapped_rest_pool_leaves,
    unmapped_v3_analog_leaves,
)
from custom_components.norsup_smartpool.api.models import merge_v3_analog_data, parse_rest_pool

DUMP = Path(__file__).resolve().parents[1] / "norsup_api_dump.json"


def test_api_dump_leaves_are_documented() -> None:
    data = json.loads(DUMP.read_text())
    pool = data["endpoints"]["rest_pool"]
    analog = data["endpoints"]["rest_v3_analog"]["data"]
    assert unmapped_rest_pool_leaves(pool) == []
    assert unmapped_v3_analog_leaves(analog) == []


def test_dump_normalization_orp_target_pump_ambient() -> None:
    data = json.loads(DUMP.read_text())
    pool = data["endpoints"]["rest_pool"]
    analog = data["endpoints"]["rest_v3_analog"]
    snapshot = parse_rest_pool(pool["pid"], pool)
    snapshot = merge_v3_analog_data(snapshot, analog)
    assert snapshot.orp_target == 675.0
    assert snapshot.pump_running is True
    assert snapshot.pump_speed == "high"
    assert snapshot.ambient_temperature_c == pytest.approx(10.874046)
    assert snapshot.free_chlorine_ppm is None
    assert snapshot.orp_mv == pytest.approx(681.562, rel=1e-3)
