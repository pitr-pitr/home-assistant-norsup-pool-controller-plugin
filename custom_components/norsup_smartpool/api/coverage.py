"""Map every REST pool / V3 analog leaf to an entity or diagnostics attribute."""

from __future__ import annotations

import re
from typing import Any

# One-line documentation for each API leaf (entity id suffix or diagnostics attribute).
# Keys are dot-paths under rest_pool or rest_v3_analog.data; aux_N uses a pattern.
REST_POOL_LEAF_MAP: dict[str, str] = {
    "activity_at": "diagnostics:pool_activity_at",  # Last controller activity epoch ms
    "api_version": "diagnostics:api_version",  # Smart Pool Connect API major version
    "avatar": "diagnostics:avatar",  # Portal avatar URL when set
    "avatar_thumb": "diagnostics:avatar_thumb",  # Thumbnail avatar URL when set
    "created_at": "diagnostics:pool_created_at",  # Pool record creation epoch ms
    "location": "diagnostics:location",  # Geo/label from portal when present
    "mac_address": "diagnostics:mac_address",  # Controller MAC from REST pool
    "name": "entity:pool_name",  # Shown on device; mirrored in coordinator pool_name
    "pid": "diagnostics:pool_id",  # Pool UUID (same as config entry pool id)
    "status": "entity:cloud_online",  # online/offline → cloud_online binary + online flag
    "cl.config.clm.probe": "diagnostics:cl_probe_offset",  # CLM probe offset config
    "cl.config.clm.target": "entity:orp_target",  # ORP/Rx dosing target (mV)
    "cl.config.dosing_time": "diagnostics:cl_dosing_time_ms",  # Chlorine dose pulse length
    "cl.config.min_water_temp": "diagnostics:cl_min_water_temp_c",  # Min water temp for dosing
    "cl.config.overdose_alert": "diagnostics:cl_overdose_alert",  # Overdose alert threshold
    "cl.config.pausing_time": "diagnostics:cl_pausing_time_ms",  # Pause between doses
    "cl.metrics.clm": "entity:orp",  # Live ORP/Rx (mV); not ppm chlorine when > 50
    "cl.metrics.timestamp": "diagnostics:cl_metrics_timestamp",  # CL metrics sample time
    "cl.status.calibration": "entity:cl_dosing_status",  # Calibration flag on CL status
    "cl.status.status": "entity:cl_dosing_status",  # Chlorine dosing state code
    "cl.status.timestamp": "diagnostics:cl_status_timestamp",  # CL status sample time
    "filter.config.always_active": "entity:filter_always_active",  # 24/7 circulation flag
    "filter.config.pump_speed": "entity:filter_config_pump_speed",  # Default speed preset
    "filter.metrics.error_code": "entity:filter_error",  # Filter fault code
    "filter.metrics.pump_current": "entity:pump_current",  # Motor current (A)
    "filter.metrics.pump_speed": "entity:pump_speed",  # Live metrics pump speed code
    "filter.metrics.timestamp": "diagnostics:filter_metrics_timestamp",  # Filter metrics time
    "filter.status.pump_speed": "entity:filter_status_pump_speed_code",  # Status speed code
    "filter.status.pump_status": "entity:pump_running",  # Pump running when > 0
    "filter.status.status": "entity:filter_status",  # Filter module status code
    "filter.status.timestamp": "diagnostics:filter_status_timestamp",  # Filter status time
    "ph.config.dosing_time": "diagnostics:ph_dosing_time_ms",  # pH dose pulse length
    "ph.config.gain": "diagnostics:ph_gain",  # pH control gain
    "ph.config.hysteresis": "diagnostics:ph_hysteresis",  # pH dosing hysteresis
    "ph.config.min_water_temp": "diagnostics:ph_min_water_temp_c",  # Min water temp for pH dose
    "ph.config.offset": "diagnostics:ph_offset",  # pH offset calibration
    "ph.config.overdose_alert": "diagnostics:ph_overdose_alert",  # pH overdose alert
    "ph.config.pausing_time": "diagnostics:ph_pausing_time_ms",  # Pause between pH doses
    "ph.config.probe_offset": "diagnostics:ph_probe_offset",  # Probe offset
    "ph.config.target": "entity:ph_target",  # pH dosing target
    "ph.config.type": "diagnostics:ph_dosing_type",  # Acid dosing type (pos/neg)
    "ph.metrics.actual": "entity:ph",  # Live pH reading
    "ph.metrics.timestamp": "diagnostics:ph_metrics_timestamp",  # pH metrics sample time
    "ph.status.calibration": "entity:ph_dosing_status",  # pH calibration flag attribute
    "ph.status.status": "entity:ph_dosing_status",  # pH dosing state code
    "ph.status.timestamp": "diagnostics:ph_status_timestamp",  # pH status sample time
}

_REST_POOL_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"^aux_[1-4]\.config\.always_on$"),
        "entity:aux_*",
        "Aux output always-on config (per-channel binary sensor attrs)",
    ),
    (
        re.compile(r"^aux_[1-4]\.config\.cover_closed$"),
        "entity:aux_*",
        "Aux cover-closed config on auxiliary channel",
    ),
    (
        re.compile(r"^aux_[1-4]\.config\.flow$"),
        "entity:aux_*",
        "Aux flow flag on auxiliary channel",
    ),
    (
        re.compile(r"^aux_[1-4]\.config\.name$"),
        "entity:aux_*",
        "Aux channel label (binary sensor name)",
    ),
    (
        re.compile(r"^aux_[1-4]\.config\.schedule\.enabled$"),
        "entity:aux_*",
        "Aux schedule enabled flag (binary sensor attribute)",
    ),
    (
        re.compile(r"^aux_[1-4]\.config\.schedule\.start_time$"),
        "entity:aux_*",
        "Aux schedule start time attribute",
    ),
    (
        re.compile(r"^aux_[1-4]\.config\.schedule\.stop_time$"),
        "entity:aux_*",
        "Aux schedule stop time attribute",
    ),
    (
        re.compile(r"^aux_[1-4]\.status\.status$"),
        "entity:aux_*",
        "Aux output on/off (binary sensor state)",
    ),
    (
        re.compile(r"^aux_[1-4]\.status\.timestamp$"),
        "diagnostics:aux_status_timestamp",
        "Aux status sample epoch ms",
    ),
    (
        re.compile(r"^filter\.config\.schedule_[1-3]\.enabled$"),
        "entity:filter_schedule_*_enabled",
        "Filter schedule slot enabled flag",
    ),
    (
        re.compile(r"^filter\.config\.schedule_[1-3]\.start_time$"),
        "entity:filter_schedule_*_start_time",
        "Filter schedule slot start time",
    ),
    (
        re.compile(r"^filter\.config\.schedule_[1-3]\.stop_time$"),
        "entity:filter_schedule_*_stop_time",
        "Filter schedule slot stop time",
    ),
    (
        re.compile(r"^filter\.config\.schedule_[1-3]\.pump_speed$"),
        "entity:filter_schedule_*_pump_speed",
        "Filter schedule slot pump speed preset",
    ),
)

V3_ANALOG_LEAF_MAP: dict[str, str] = {
    "ph": "entity:ph",  # V3 analog pH when REST pool omits it
    "rx": "entity:orp",  # V3 analog ORP/Rx (mV)
    "water_t": "entity:water_temperature",  # V3 water temperature (°C)
    "ambient_t": "entity:ambient_temperature",  # V3 ambient (scaled ÷10 when needed)
    "tds_salt": "entity:tds_salt",  # TDS salt estimate (ppm)
    "a_input_error": "entity:sensor_faults",  # Generic analog input fault flag
    "ambient_temp_input_error": "entity:sensor_faults",  # Ambient probe fault flag
    "ntc_input_error": "entity:sensor_faults",  # NTC temperature input fault
    "ph_input_error": "entity:sensor_faults",  # pH probe input fault
    "rx_input_error": "entity:sensor_faults",  # ORP probe input fault
    "tds_input_error": "entity:sensor_faults",  # TDS input fault
    "tds_pollution_input_error": "entity:sensor_faults",  # TDS pollution sensor fault
    "tds_salt_input_error": "entity:sensor_faults",  # TDS salt channel fault
    "water_temp_input_error": "entity:sensor_faults",  # Water temperature input fault
    "calibration_ph_4": "entity:calibration_ph_4",  # pH 4-point calibration done
    "calibration_ph_7": "entity:calibration_ph_7",  # pH 7-point calibration done
    "calibration_ph_correct": "entity:calibration_ph_correct",  # pH calibration valid
    "calibration_rx_475": "entity:calibration_rx_475",  # ORP 475 mV cal done
    "calibration_rx_correct": "entity:calibration_rx_correct",  # ORP calibration valid
    "b_tds_null_measurement": "diagnostics:b_tds_null_measurement",  # TDS null measurement flag
    "calibration_gain": "diagnostics:calibration_gain",  # Factory calibration gain
    "calibration_offset": "diagnostics:calibration_offset",  # Factory calibration offset
    "ph_mv": "diagnostics:ph_mv",  # pH module millivolt reading
    "ph_mv_measure": "diagnostics:ph_mv_measure",  # Raw pH mV measurement
    "ph_raw": "diagnostics:ph_raw",  # Unfiltered pH
    "ph_sensor_status": "diagnostics:ph_sensor_status",  # pH sensor status code
    "ph_sensor_status_gain": "diagnostics:ph_sensor_status_gain",  # pH sensor gain status
    "ph_sensor_status_offset": "diagnostics:ph_sensor_status_offset",  # pH sensor offset status
    "rx_mv_measure": "diagnostics:rx_mv_measure",  # Raw ORP mV measurement
    "rx_raw": "diagnostics:rx_raw",  # Unfiltered ORP
    "rx_sensor_status": "diagnostics:rx_sensor_status",  # ORP sensor status code
    "tds_pollution": "diagnostics:tds_pollution",  # TDS pollution index
    "reserved": "diagnostics:reserved",  # Reserved analog field
}

V3_ADC_ATTRIBUTE_PREFIXES = ("adc_", "filter_")

INPUT_ERROR_KEYS: tuple[str, ...] = (
    "a_input_error",
    "ambient_temp_input_error",
    "ntc_input_error",
    "ph_input_error",
    "rx_input_error",
    "tds_input_error",
    "tds_pollution_input_error",
    "tds_salt_input_error",
    "water_temp_input_error",
)

CALIBRATION_FLAG_KEYS: tuple[str, ...] = (
    "calibration_ph_4",
    "calibration_ph_7",
    "calibration_ph_correct",
    "calibration_rx_475",
    "calibration_rx_correct",
)


def _iter_leaves(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    leaves: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(child, dict):
                leaves.extend(_iter_leaves(child, path))
            elif isinstance(child, list):
                if not child:
                    continue
                for index, item in enumerate(child):
                    leaves.extend(_iter_leaves(item, f"{path}[{index}]"))
            else:
                leaves.append((path, child))
    return leaves


def rest_pool_leaf_target(path: str) -> str | None:
    """Return mapping target for a rest_pool dot-path leaf."""
    if path in REST_POOL_LEAF_MAP:
        return REST_POOL_LEAF_MAP[path]
    for pattern, target, _comment in _REST_POOL_PATTERNS:
        if pattern.match(path):
            return target
    return None


def v3_analog_leaf_target(path: str) -> str | None:
    """Return mapping target for a rest_v3_analog.data dot-path leaf."""
    if path in V3_ANALOG_LEAF_MAP:
        return V3_ANALOG_LEAF_MAP[path]
    if path.startswith(V3_ADC_ATTRIBUTE_PREFIXES):
        return "diagnostics:adc"
    return None


def unmapped_rest_pool_leaves(payload: dict[str, Any]) -> list[str]:
    """Paths under rest_pool with no documented entity/diagnostics mapping."""
    missing: list[str] = []
    for path, _value in _iter_leaves(payload):
        if rest_pool_leaf_target(path) is None:
            missing.append(path)
    return missing


def unmapped_v3_analog_leaves(data: dict[str, Any]) -> list[str]:
    """Leaves under rest_v3_analog.data with no documented mapping."""
    missing: list[str] = []
    for path, _value in _iter_leaves(data):
        if v3_analog_leaf_target(path) is None:
            missing.append(path)
    return missing


def v3_adc_diagnostic_attributes(v3_data: dict[str, Any]) -> dict[str, Any]:
    """ADC and filter ADC fields for the diagnostics sensor (attributes only)."""
    attrs: dict[str, Any] = {}
    for key, value in v3_data.items():
        if key.startswith("adc_") or key.startswith("filter_"):
            attrs[key] = value
    return attrs


def v3_misc_diagnostic_attributes(v3_data: dict[str, Any]) -> dict[str, Any]:
    """Non-ADC V3 fields exposed only on the diagnostics sensor."""
    attrs: dict[str, Any] = {}
    for key in V3_ANALOG_LEAF_MAP:
        if key.startswith("calibration_") or key.endswith("_input_error"):
            continue
        if key in ("ph", "rx", "water_t", "ambient_t", "tds_salt"):
            continue
        if key in v3_data:
            attrs[key] = v3_data[key]
    return attrs
