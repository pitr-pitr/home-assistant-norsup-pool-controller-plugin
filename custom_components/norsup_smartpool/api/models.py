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


def _module_metrics(module: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(module, dict):
        return {}
    metrics = module.get("metrics")
    return metrics if isinstance(metrics, dict) else {}


def _module_status(module: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(module, dict):
        return {}
    status = module.get("status")
    return status if isinstance(status, dict) else {}


_PUMP_SPEED_NAMES = ("off", "low", "medium", "high", "maximum")


def parse_rest_pool_list(payload: dict[str, Any] | list[Any]) -> list[tuple[str, str]]:
    """Return (pool_id, name) pairs from GET /pool on the REST API host."""
    items: Any = payload
    if isinstance(payload, dict):
        items = payload.get("items", payload)
    if not isinstance(items, list):
        return []
    pools: list[tuple[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pool_id = item.get("pid") or item.get("id")
        if not pool_id:
            continue
        name = item.get("name") or f"Pool {str(pool_id)[:8]}"
        pools.append((str(pool_id), str(name)))
    return pools


def parse_rest_pool(pool_id: str, payload: dict[str, Any]) -> NorsupPoolData:
    """Map GET /pool/{pid} REST JSON into normalized fields."""
    resolved_id = str(payload.get("pid") or payload.get("id") or pool_id)
    online = payload.get("status", "online") == "online"

    ph_mod = payload.get("ph") if isinstance(payload.get("ph"), dict) else {}
    cl_mod = payload.get("cl") if isinstance(payload.get("cl"), dict) else {}
    temp_mod = (
        payload.get("temperature")
        if isinstance(payload.get("temperature"), dict)
        else {}
    )
    filter_mod = payload.get("filter") if isinstance(payload.get("filter"), dict) else {}

    ph = _coerce_float(_module_metrics(ph_mod).get("actual"))
    orp = _coerce_float(_module_metrics(cl_mod).get("actual"))
    water_temp = _coerce_float(_module_metrics(temp_mod).get("water_temp"))

    filter_status = _module_status(filter_mod)
    filter_metrics = _module_metrics(filter_mod)
    pump_status = _coerce_float(filter_status.get("pump_status"))
    pump_speed_raw = _coerce_float(filter_metrics.get("pump_speed"))
    pump_running = pump_status is not None and pump_status > 0
    pump_speed: str | None = None
    if pump_speed_raw is not None:
        idx = int(pump_speed_raw)
        if 0 <= idx < len(_PUMP_SPEED_NAMES):
            pump_speed = _PUMP_SPEED_NAMES[idx]
        else:
            pump_speed = str(int(pump_speed_raw))

    return NorsupPoolData(
        pool_id=resolved_id,
        online=online,
        water_temperature_c=water_temp,
        pump_running=pump_running,
        pump_speed=pump_speed,
        ph=ph,
        orp_mv=orp,
        live_status=dict(payload),
    )
