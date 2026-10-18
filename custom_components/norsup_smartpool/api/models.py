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

_PUMP_SPEED_BY_CODE: dict[int, str] = {
    -1: "disabled",
    0: "off",
    1: "low",
    2: "medium",
    3: "high",
    4: "max",
}


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


def format_pump_speed(value: Any) -> str | None:
    """Map Smart Pool Connect pump_speed codes to readable labels."""
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _PUMP_SPEED_BY_CODE.values():
            return normalized
        if normalized in ("maximum", "max"):
            return "max"
        try:
            value = int(normalized)
        except ValueError:
            return value.strip()
    if isinstance(value, (int, float)):
        code = int(value)
        return _PUMP_SPEED_BY_CODE.get(code, str(code))
    return str(value)


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


def _module_config(module: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(module, dict):
        return {}
    config = module.get("config")
    return config if isinstance(config, dict) else {}


def _pool_module(payload: dict[str, Any], *names: str) -> dict[str, Any]:
    for name in names:
        module = payload.get(name)
        if isinstance(module, dict):
            return module
    return {}


def _metric_first(metrics: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _coerce_float(metrics.get(key))
        if value is not None:
            return value
    return None


def _normalize_ambient_temperature_c(
    raw: float | None, *, input_error: int | None = None
) -> float | None:
    """Reject or scale implausible ambient readings from analog payloads."""
    if raw is None:
        return None
    if input_error not in (None, 0):
        return None
    if -40.0 <= raw <= 60.0:
        return raw
    scaled = raw / 10.0
    if -40.0 <= scaled <= 60.0:
        return scaled
    return None


def _orp_from_module(module: dict[str, Any]) -> float | None:
    metrics = _module_metrics(module)
    orp = _metric_first(metrics, "actual", "rx", "orp", "ORP", "value")
    if orp is not None:
        return orp
    clm = _metric_first(metrics, "clm")
    if clm is not None and clm > 50:
        return clm
    return None


def _orp_target_from_cl_config(config: dict[str, Any]) -> float | None:
    target = _coerce_float(config.get("target") or config.get("rx_target"))
    if target is not None:
        return target
    clm_cfg = config.get("clm")
    if isinstance(clm_cfg, dict):
        return _coerce_float(clm_cfg.get("target"))
    return None


def _free_chlorine_from_cl_metrics(
    metrics: dict[str, Any], orp_mv: float | None
) -> float | None:
    """CLM is ORP mV on many V3 pools; only treat low values as ppm."""
    explicit = _metric_first(metrics, "free_chlorine", "chlorine", "ppm")
    if explicit is not None:
        return explicit
    clm = _metric_first(metrics, "clm")
    if clm is None:
        return None
    if clm <= 20 and (orp_mv is None or abs(clm - orp_mv) > 5):
        return clm
    return None


def _resolve_filter_pump_speed(filter_mod: dict[str, Any]) -> str | None:
    """Prefer live speed codes; fall back to config when the pump is running."""
    filter_metrics = _module_metrics(filter_mod)
    filter_status = _module_status(filter_mod)
    filter_config = _module_config(filter_mod)

    def _non_off_speed(raw: Any) -> str | None:
        if raw is None:
            return None
        label = format_pump_speed(raw)
        if label and label not in ("off", "0"):
            return label
        return None

    for raw in (
        filter_metrics.get("pump_speed"),
        filter_status.get("pump_speed"),
    ):
        speed = _non_off_speed(raw)
        if speed:
            return speed

    pump_status = _coerce_float(filter_status.get("pump_status"))
    if pump_status is not None and pump_status > 0:
        cfg_speed = _non_off_speed(filter_config.get("pump_speed"))
        if cfg_speed:
            return cfg_speed
        for sched_key in ("schedule_1", "schedule_2", "schedule_3"):
            sched = filter_config.get(sched_key)
            if not isinstance(sched, dict) or not sched.get("enabled"):
                continue
            sched_speed = _non_off_speed(sched.get("pump_speed"))
            if sched_speed:
                return sched_speed

    if filter_metrics.get("pump_speed") is not None:
        return format_pump_speed(filter_metrics.get("pump_speed"))
    if filter_status.get("pump_speed") is not None:
        return format_pump_speed(filter_status.get("pump_speed"))
    return None


@dataclass(slots=True)
class NorsupAuxChannel:
    """One auxiliary output (flow, disinfection, …) from the REST pool tree."""

    key: str
    name: str
    active: bool | None = None
    always_on: bool | None = None
    flow: bool | None = None
    cover_closed: bool | None = None
    schedule_enabled: bool | None = None
    schedule_start: str | None = None
    schedule_stop: str | None = None


@dataclass(slots=True)
class NorsupPoolData:
    """Normalized pool snapshot for entity platforms."""

    pool_id: str
    online: bool | None = None
    water_temperature_c: float | None = None
    ambient_temperature_c: float | None = None
    pump_running: bool | None = None
    pump_speed: str | None = None
    pump_current_a: float | None = None
    filter_pump_status: int | None = None
    filter_status_code: int | None = None
    filter_error_code: int | None = None
    ph: float | None = None
    orp_mv: float | None = None
    free_chlorine_ppm: float | None = None
    tds_salt_ppm: float | None = None
    ph_target: float | None = None
    orp_target: float | None = None
    ph_dosing_status: int | None = None
    cl_dosing_status: int | None = None
    ph_calibration: int | None = None
    cl_calibration: int | None = None
    aux_channels: list[NorsupAuxChannel] = field(default_factory=list)
    pool_name: str | None = None
    live_status: dict[str, Any] = field(default_factory=dict)
    pool_status: dict[str, Any] = field(default_factory=dict)


def _apply_filter_module(data: NorsupPoolData, filter_mod: dict[str, Any]) -> None:
    filter_status = _module_status(filter_mod)
    filter_metrics = _module_metrics(filter_mod)
    pump_status_raw = _coerce_float(filter_status.get("pump_status"))
    if pump_status_raw is not None:
        data.filter_pump_status = int(pump_status_raw)
        if data.pump_running is None:
            data.pump_running = pump_status_raw > 0
    resolved_speed = _resolve_filter_pump_speed(filter_mod)
    if resolved_speed is not None:
        data.pump_speed = resolved_speed
    pump_current = _coerce_float(filter_metrics.get("pump_current"))
    if pump_current is not None:
        data.pump_current_a = pump_current
    err_code = _coerce_float(filter_metrics.get("error_code"))
    if err_code is not None:
        data.filter_error_code = int(err_code)
    filter_status_code = _coerce_float(filter_status.get("status"))
    if filter_status_code is not None:
        data.filter_status_code = int(filter_status_code)


def _apply_aux_modules(data: NorsupPoolData, payload: dict[str, Any]) -> None:
    channels: list[NorsupAuxChannel] = []
    for index in range(1, 5):
        key = f"aux_{index}"
        module = payload.get(key)
        if not isinstance(module, dict):
            continue
        cfg = _module_config(module)
        st = _module_status(module)
        name_raw = cfg.get("name")
        name = str(name_raw).strip() if isinstance(name_raw, str) and name_raw.strip() else key
        status_val = _coerce_float(st.get("status"))
        schedule = cfg.get("schedule") if isinstance(cfg.get("schedule"), dict) else {}
        channels.append(
            NorsupAuxChannel(
                key=key,
                name=name,
                active=status_val == 1 if status_val is not None else None,
                always_on=_coerce_bool(cfg.get("always_on")),
                flow=_coerce_bool(cfg.get("flow")),
                cover_closed=_coerce_bool(cfg.get("cover_closed")),
                schedule_enabled=_coerce_bool(schedule.get("enabled")),
                schedule_start=str(schedule.get("start_time"))
                if schedule.get("start_time")
                else None,
                schedule_stop=str(schedule.get("stop_time"))
                if schedule.get("stop_time")
                else None,
            )
        )
    if channels:
        data.aux_channels = channels


def _apply_chemistry_modules(data: NorsupPoolData, payload: dict[str, Any]) -> None:
    ph_mod = _pool_module(payload, "ph")
    cl_mod = _pool_module(payload, "cl", "chlorine")

    ph = _metric_first(_module_metrics(ph_mod), "actual", "ph", "value")
    if ph is not None:
        data.ph = ph
    orp = _orp_from_module(cl_mod)
    if orp is not None:
        data.orp_mv = orp
    cl_metrics = _module_metrics(cl_mod)
    chlorine = _free_chlorine_from_cl_metrics(cl_metrics, data.orp_mv)
    if chlorine is not None:
        data.free_chlorine_ppm = chlorine

    ph_target = _coerce_float(_module_config(ph_mod).get("target"))
    if ph_target is not None:
        data.ph_target = ph_target
    orp_target = _orp_target_from_cl_config(_module_config(cl_mod))
    if orp_target is not None:
        data.orp_target = orp_target

    ph_status_mod = _module_status(ph_mod)
    ph_status = _coerce_float(ph_status_mod.get("status"))
    if ph_status is not None:
        data.ph_dosing_status = int(ph_status)
    ph_cal = _coerce_float(ph_status_mod.get("calibration"))
    if ph_cal is not None:
        data.ph_calibration = int(ph_cal)
    cl_status_mod = _module_status(cl_mod)
    cl_status = _coerce_float(cl_status_mod.get("status"))
    if cl_status is not None:
        data.cl_dosing_status = int(cl_status)
    cl_cal = _coerce_float(cl_status_mod.get("calibration"))
    if cl_cal is not None:
        data.cl_calibration = int(cl_cal)


def _apply_temperature_module(data: NorsupPoolData, payload: dict[str, Any]) -> None:
    temp_mod = _pool_module(payload, "temperature", "temp")
    metrics = _module_metrics(temp_mod)
    water_temp = _metric_first(metrics, "water_temp", "water_temperature", "actual")
    if water_temp is not None and data.water_temperature_c is None:
        data.water_temperature_c = water_temp
    ambient = _normalize_ambient_temperature_c(
        _metric_first(metrics, "ambient_temp", "ambient_temperature")
    )
    if ambient is not None:
        data.ambient_temperature_c = ambient


def parse_live_status(pool_id: str, payload: dict[str, Any]) -> NorsupPoolData:
    """Map live-status JSON into normalized fields."""
    water_temp = _coerce_float(
        payload.get("water_temperature")
        or payload.get("water_temp")
        or payload.get("waterTemperature")
    )
    pump_status_raw = payload.get("pump_status")
    pump_running = _coerce_bool(
        pump_status_raw
        or payload.get("pump_running")
        or payload.get("pumpRunning")
    )
    if pump_running is None:
        pump_status_num = _coerce_float(pump_status_raw)
        if pump_status_num is not None:
            pump_running = pump_status_num > 0

    pump_speed = format_pump_speed(
        payload.get("pump_speed") or payload.get("pumpSpeed")
    )

    online = _coerce_bool(payload.get("online"))
    if online is None and water_temp is not None:
        online = True

    data = NorsupPoolData(
        pool_id=pool_id,
        online=online,
        water_temperature_c=water_temp,
        pump_running=pump_running,
        pump_speed=pump_speed,
        live_status=dict(payload),
    )
    _apply_chemistry_modules(data, payload)
    _apply_temperature_module(data, payload)
    filter_mod = _pool_module(payload, "filter")
    if filter_mod:
        _apply_filter_module(data, filter_mod)
    _apply_aux_modules(data, payload)
    return data


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
    _apply_chemistry_modules(data, payload)
    _apply_temperature_module(data, payload)
    filter_mod = _pool_module(payload, "filter")
    if filter_mod:
        _apply_filter_module(data, filter_mod)
    _apply_aux_modules(data, payload)
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
                    entry.get("rx")
                    or entry.get("orp")
                    or entry.get("ORP")
                    or entry.get("actual")
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


def merge_v3_analog_data(data: NorsupPoolData, payload: dict[str, Any]) -> NorsupPoolData:
    """Fill gaps from GET /pool/{pid}/v3/analoge_data (V3 pools)."""
    if not payload:
        return data
    inner = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(inner, dict):
        return data
    if data.ph is None:
        data.ph = _coerce_float(inner.get("ph"))
    if data.orp_mv is None:
        data.orp_mv = _coerce_float(inner.get("rx") or inner.get("orp"))
    if data.water_temperature_c is None:
        data.water_temperature_c = _coerce_float(
            inner.get("water_t") or inner.get("water_temp")
        )
    if data.ambient_temperature_c is None:
        err = _coerce_float(inner.get("ambient_temp_input_error"))
        err_int = int(err) if err is not None else None
        data.ambient_temperature_c = _normalize_ambient_temperature_c(
            _coerce_float(inner.get("ambient_t") or inner.get("ambient_temp")),
            input_error=err_int,
        )
    if data.tds_salt_ppm is None:
        salt = _coerce_float(inner.get("tds_salt"))
        if salt is not None:
            data.tds_salt_ppm = salt
    return data


def merge_filter_payload(data: NorsupPoolData, payload: dict[str, Any]) -> NorsupPoolData:
    """Merge portal filter.data or REST /filter module JSON."""
    if not payload:
        return data
    if "metrics" in payload or "status" in payload:
        _apply_filter_module(data, payload)
    else:
        filter_mod = _pool_module(payload, "filter")
        if filter_mod:
            _apply_filter_module(data, filter_mod)
    return data


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
    pool_name = payload.get("name")
    pool_name = (
        pool_name.strip()
        if isinstance(pool_name, str) and pool_name.strip()
        else None
    )

    data = NorsupPoolData(
        pool_id=resolved_id,
        online=online,
        pool_name=pool_name,
        live_status=dict(payload),
        pool_status={"name": pool_name} if pool_name else {},
    )
    _apply_chemistry_modules(data, payload)
    _apply_temperature_module(data, payload)
    filter_mod = _pool_module(payload, "filter")
    if filter_mod:
        _apply_filter_module(data, filter_mod)
    _apply_aux_modules(data, payload)
    return data
