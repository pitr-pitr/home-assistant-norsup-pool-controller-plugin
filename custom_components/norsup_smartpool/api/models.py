"""Typed models for Smart Pool Connect API responses."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

_PH_RE = re.compile(r'"ph"\s*:\s*([\d.]+)', re.IGNORECASE)
_RX_RE = re.compile(r'"rx"\s*:\s*([\d.]+)', re.IGNORECASE)
_PH_LABEL_RE = re.compile(r"pH[:\s]+([\d.]+)", re.IGNORECASE)
_RX_LABEL_RE = re.compile(r"(?:Rx|ORP)[:\s]+([\d.]+)", re.IGNORECASE)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "on", "yes"):
            return True
        if lowered in ("false", "0", "off", "no"):
            return False
    return None


@dataclass(slots=True)
class NorsupPoolData:
    """Normalized pool snapshot for entity platforms."""

    pool_id: str
    online: bool | None = None
    water_temperature_c: float | None = None
    pump_running: bool | None = None
    pump_speed: str | None = None
    ph: float | None = None
    orp_mv: float | None = None
    live_status: dict[str, Any] = field(default_factory=dict)
    pool_status: dict[str, Any] = field(default_factory=dict)


def parse_live_status(pool_id: str, payload: dict[str, Any]) -> NorsupPoolData:
    """Map live-status JSON into normalized fields."""
    water_temp = _coerce_float(
        payload.get("water_temperature")
        or payload.get("water_temp")
        or payload.get("waterTemperature")
    )
    pump_running = _coerce_bool(
        payload.get("pump_status")
        or payload.get("pump_running")
        or payload.get("pumpRunning")
    )
    pump_speed = payload.get("pump_speed") or payload.get("pumpSpeed")
    if pump_speed is not None and not isinstance(pump_speed, str):
        pump_speed = str(pump_speed)

    online = _coerce_bool(payload.get("online"))
    if online is None and water_temp is not None:
        online = True

    return NorsupPoolData(
        pool_id=pool_id,
        online=online,
        water_temperature_c=water_temp,
        pump_running=pump_running,
        pump_speed=pump_speed,
        live_status=dict(payload),
    )


def parse_pool_status(data: NorsupPoolData, payload: dict[str, Any]) -> NorsupPoolData:
    """Merge supplemental pool-status JSON."""
    if not payload:
        return data
    water_temp = _coerce_float(
        payload.get("water_temperature")
        or payload.get("water_temp")
        or payload.get("waterTemperature")
    )
    if data.water_temperature_c is None and water_temp is not None:
        data.water_temperature_c = water_temp
    pump_running = _coerce_bool(
        payload.get("pump_status") or payload.get("pump_running")
    )
    if data.pump_running is None and pump_running is not None:
        data.pump_running = pump_running
    data.pool_status = dict(payload)
    return data


def parse_pool_data_readings(text: str, pool_id: str) -> tuple[float | None, float | None]:
    """Extract pH and Rx/ORP from /pool.data body (JSON fragment or text)."""
    ph: float | None = None
    rx: float | None = None

    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            pools = parsed.get("pools") or parsed.get("pool")
            if isinstance(pools, dict) and pool_id in pools:
                entry = pools[pool_id]
            elif isinstance(pools, list):
                entry = next(
                    (p for p in pools if isinstance(p, dict) and p.get("id") == pool_id),
                    parsed,
                )
            else:
                entry = parsed
            if isinstance(entry, dict):
                ph = _coerce_float(entry.get("ph"))
                rx = _coerce_float(
                    entry.get("rx") or entry.get("orp") or entry.get("ORP")
                )

    if ph is None:
        match = _PH_RE.search(text) or _PH_LABEL_RE.search(text)
        if match:
            ph = _coerce_float(match.group(1))
    if rx is None:
        match = _RX_RE.search(text) or _RX_LABEL_RE.search(text)
        if match:
            rx = _coerce_float(match.group(1))

    return ph, rx


def merge_readings(data: NorsupPoolData, ph: float | None, rx: float | None) -> NorsupPoolData:
    """Apply chemistry readings when present."""
    if ph is not None:
        data.ph = ph
    if rx is not None:
        data.orp_mv = rx
    return data
