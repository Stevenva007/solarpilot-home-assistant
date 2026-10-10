"""One explicit SG relay configuration; Panasonic bindings are read-only.

This module performs validation only. Commissioning flags never arise from
inferred device names, imported profiles or a successful service call.
"""
from __future__ import annotations

from copy import deepcopy
import math

SG_DEFAULTS = {
    "entity_id": "", "enabled": False,
    "commissioning_confirmed": False, "watchdog_confirmed": False,
    "threshold_w": 3000.0, "expected_power_w": 3200.0,
    "start_delay_s": 120, "stop_delay_s": 60, "rest_s": 900,
    "max_session_s": 3600, "lease_s": 300, "renew_s": 60,
    "hysteresis_w": 300.0, "ack_timeout_s": 20, "stale_s": 120,
    "tank_temperature_entity": "", "tank_target_entity": "",
    "power_entity": "", "power_scope": "unconfirmed",
    "activity_entity": "", "zone_entities": [],
}
READ_ENTITY_KEYS = frozenset({"tank_temperature_entity", "tank_target_entity",
                              "power_entity", "activity_entity"})
REFERENCE_KEYS = frozenset({"entity_id", *READ_ENTITY_KEYS, "zone_entities"})
POWER_SCOPES = frozenset({"unconfirmed", "total", "supply1", "supply2"})
NUMBER_LIMITS = {
    "threshold_w": (500, 20000), "expected_power_w": (100, 30000),
    "hysteresis_w": (0, 5000), "start_delay_s": (30, 1800),
    "stop_delay_s": (5, 600), "rest_s": (60, 7200),
    "max_session_s": (300, 14400), "lease_s": (60, 600),
    "renew_s": (10, 120), "ack_timeout_s": (5, 60),
    "stale_s": (15, 600),
}


def finite(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def normalize_config(raw=None):
    """Copy only the current schema; retain bad values for visible validation."""
    raw = raw if isinstance(raw, dict) else {}
    return {key: deepcopy(raw.get(key, default)) for key, default in SG_DEFAULTS.items()}


def validate_config(raw):
    c = normalize_config(raw)
    errors = {}
    for key, (low, high) in NUMBER_LIMITS.items():
        value = finite(c[key])
        if value is None or not low <= value <= high:
            errors[key] = "range"
    for key in ("enabled", "commissioning_confirmed", "watchdog_confirmed"):
        if type(c[key]) is not bool:
            errors[key] = "range"
    for key in {"entity_id", *READ_ENTITY_KEYS}:
        if not isinstance(c[key], str):
            errors[key] = "entity_missing"
    relay = c["entity_id"]
    if relay and (not isinstance(relay, str) or not relay.startswith("switch.")):
        errors["entity_id"] = "sg_switch_required"
    zones = c["zone_entities"]
    if (not isinstance(zones, list) or any(not isinstance(x, str) or not x.startswith("climate.") for x in zones)
            or isinstance(zones, list) and all(isinstance(x, str) for x in zones) and len(zones) != len(set(zones))):
        errors["zone_entities"] = "range"
    if not isinstance(c["power_scope"], str) or c["power_scope"] not in POWER_SCOPES:
        errors["power_scope"] = "range"
    if finite(c["hysteresis_w"]) is not None and finite(c["threshold_w"]) is not None and finite(c["hysteresis_w"]) >= finite(c["threshold_w"]):
        errors["hysteresis_w"] = "range"
    if all(finite(c[k]) is not None for k in ("renew_s", "lease_s", "ack_timeout_s")):
        if finite(c["renew_s"]) + finite(c["ack_timeout_s"]) >= finite(c["lease_s"]):
            errors["renew_s"] = "timing"
    if c["enabled"] is True:
        if not relay:
            errors["entity_id"] = "required"
        if c["commissioning_confirmed"] is not True:
            errors["commissioning_confirmed"] = "sg_commissioning"
        if c["watchdog_confirmed"] is not True:
            errors["watchdog_confirmed"] = "sg_watchdog"
    return errors


def actuator_conflicts(config, devices):
    """Reject a shared relay even when the other profile is currently disabled."""
    relay = config.get("entity_id") if isinstance(config, dict) else None
    if not isinstance(relay, str) or not relay:
        return []
    rows = devices if isinstance(devices, (list, tuple)) else []
    return [str(d.get("id", "")) for d in rows if isinstance(d, dict)
            and any(d.get(k) == relay for k in ("control_entity", "active_entity", "number_entity",
                                               "start_script", "stop_script", "start_button",
                                               "charge_script", "discharge_script", "idle_script"))]


def source_errors(hass, config, *, site=None, devices=(), wallbox=None, batteries=()):
    """Inspect links without contacting a device or making any physical call."""
    c = normalize_config(config)
    site = site if isinstance(site, dict) else {}
    wallbox = wallbox if isinstance(wallbox, dict) else {}
    devices = devices if isinstance(devices, (list, tuple)) else []
    batteries = batteries if isinstance(batteries, (list, tuple)) else []
    errors = validate_config(c)
    if actuator_conflicts(c, devices) or actuator_conflicts(c, batteries):
        errors["entity_id"] = "sg_duplicate"
    for key in ("entity_id", *READ_ENTITY_KEYS):
        eid = c.get(key)
        if isinstance(eid, str) and eid and hass.states.get(eid) is None:
            errors[key] = "entity_missing"
    for eid in c.get("zone_entities", []) if isinstance(c.get("zone_entities"), list) else []:
        if isinstance(eid, str) and hass.states.get(eid) is None:
            errors["zone_entities"] = "entity_missing"
    if isinstance(c.get("power_entity"), str) and c["power_entity"]:
        obj = hass.states.get(c["power_entity"])
        if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
            errors["power_entity"] = "power_unit"
        reserved = {str((site or {}).get(k) or "") for k in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity")}
        reserved.update(str(d.get("power_entity") or "") for d in devices if isinstance(d, dict))
        reserved.add(str((wallbox or {}).get("power_entity") or ""))
        reserved.update(str(b.get("power_entity") or "") for b in batteries if isinstance(b, dict))
        if c["power_entity"] in reserved:
            errors["power_entity"] = "dedicated_meter"
    if c.get("enabled") is True and not (site or {}).get("pv_entity"):
        errors["base"] = "sg_pv_required"
    return errors


# Stable public aliases for one shared runtime/options schema.
normalized_settings = normalize_config
normalized_config = normalize_config
