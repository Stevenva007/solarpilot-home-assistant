"""One explicit SG relay configuration; Panasonic bindings are read-only.

This module performs validation only. Commissioning flags never arise from
inferred device names, imported profiles or a successful service call.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import math
import re

SG_DEFAULTS = {
    "entity_id": "", "enabled": False,
    "commissioning_confirmed": False, "watchdog_confirmed": False,
    "threshold_w": 3000.0, "expected_power_w": 3200.0,
    "start_delay_s": 120, "stop_delay_s": 60, "rest_s": 900,
    "max_session_s": 3600, "lease_s": 300, "renew_s": 60,
    "hysteresis_w": 300.0, "ack_timeout_s": 20, "stale_s": 120,
    "tank_temperature_entity": "", "tank_target_entity": "",
    "power_entity": "", "power_scope": "unconfirmed",
    "power_supply1_entity": "", "power_supply2_entity": "",
    "split_power_confirmed": False,
    "compressor_frequency_entity": "", "sg_status_entity": "",
    "profile": "dhw_only", "profile_confirmed": False,
    "cooling_protection_confirmed": False,
    "activity_entity": "", "zone_entities": [],
}
READ_ENTITY_KEYS = frozenset({"tank_temperature_entity", "tank_target_entity",
                              "power_entity", "activity_entity", "power_supply1_entity",
                              "power_supply2_entity", "compressor_frequency_entity", "sg_status_entity"})
POWER_ENTITY_KEYS = ("power_entity", "power_supply1_entity", "power_supply2_entity")
PROFILES = frozenset({"dhw_only", "general"})
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
    raw = raw if isinstance(raw, Mapping) else {}
    def detached(value):
        if isinstance(value, Mapping):
            return {key: detached(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [detached(item) for item in value]
        return deepcopy(value)
    return {key: detached(raw.get(key, default)) for key, default in SG_DEFAULTS.items()}


def validate_config(raw):
    c = normalize_config(raw)
    errors = {}
    for key, (low, high) in NUMBER_LIMITS.items():
        value = finite(c[key])
        if value is None or not low <= value <= high:
            errors[key] = "range"
    for key in ("enabled", "commissioning_confirmed", "watchdog_confirmed", "profile_confirmed",
                "cooling_protection_confirmed", "split_power_confirmed"):
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
    if not isinstance(c["profile"], str) or c["profile"] not in PROFILES:
        errors["profile"] = "range"
    split = any(isinstance(c[key], str) and c[key] for key in POWER_ENTITY_KEYS[1:])
    if split:
        for key in POWER_ENTITY_KEYS[1:]:
            if not c[key]:
                errors[key] = "required"
        if c["power_entity"]:
            errors["power_entity"] = "sg_meter_overlap"
        if c["power_supply1_entity"] == c["power_supply2_entity"]:
            errors["power_supply2_entity"] = "sg_meter_overlap"
    if finite(c["hysteresis_w"]) is not None and finite(c["threshold_w"]) is not None and finite(c["hysteresis_w"]) >= finite(c["threshold_w"]):
        errors["hysteresis_w"] = "range"
    if all(finite(c[k]) is not None for k in ("renew_s", "lease_s", "ack_timeout_s")):
        if finite(c["renew_s"]) + finite(c["ack_timeout_s"]) >= finite(c["lease_s"]):
            errors["renew_s"] = "timing"
    if c["enabled"] is True:
        if c["profile"] == "general" and c["profile_confirmed"] is not True:
            errors["profile_confirmed"] = "sg_profile_confirmation"
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


_ENTITY_REF = re.compile(r"\b(?:sensor|binary_sensor|input_number|input_boolean|switch|climate|water_heater|number)\.[a-z0-9_]+\b")


def _template_references(hass, entity_id):
    """Read bounded inspectable dependencies without rendering a template.

    HA's loaded template entity can expose its original config/templates; state
    source attributes are accepted as extra declared dependencies. Dynamic or
    hidden physical overlap remains part of explicit local coverage confirmation.
    """
    refs = set()
    obj = hass.states.get(entity_id)
    attrs = getattr(obj, "attributes", {}) or {}
    for key in ("entity_id", "source_entity", "source_entities"):
        value = attrs.get(key)
        values = value if isinstance(value, (list, tuple, set, frozenset)) else [value]
        refs.update(item for item in values if isinstance(item, str) and _ENTITY_REF.fullmatch(item))
    data = getattr(hass, "data", {})
    component = data.get(entity_id.split(".", 1)[0]) if isinstance(data, Mapping) else None
    lookup = getattr(component, "get_entity", None)
    try:
        entity = lookup(entity_id) if callable(lookup) else None
    except (AttributeError, KeyError, TypeError, ValueError):
        entity = None

    def inspect(value, depth=0):
        if depth > 5:
            return
        if isinstance(value, Mapping):
            for item in tuple(value.values())[:64]:
                inspect(item, depth + 1)
        elif isinstance(value, (list, tuple)):
            for item in value[:64]:
                inspect(item, depth + 1)
        else:
            template = value if isinstance(value, str) else getattr(value, "template", None)
            if isinstance(template, str):
                refs.update(_ENTITY_REF.findall(template[:65536]))
    for key in ("_config", "_template", "_state_template", "_value_template"):
        inspect(getattr(entity, key, None))
    return refs


def meter_source_entities(hass, entity_id):
    """Known dependency closure, bounded to avoid cyclic template graphs."""
    found, pending = {entity_id}, [entity_id]
    while pending and len(found) < 64:
        current = pending.pop()
        for source in _template_references(hass, current):
            if source not in found:
                found.add(source)
                pending.append(source)
                if len(found) >= 64:
                    break
    return found


def meter_sources_overlap(hass, first, second):
    return bool(first and second and meter_source_entities(hass, first) & meter_source_entities(hass, second))


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
    reserved = {str(site.get(k) or "") for k in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity")}
    reserved.update(str(d.get("power_entity") or "") for d in devices if isinstance(d, dict))
    reserved.add(str(wallbox.get("power_entity") or ""))
    reserved.update(str(b.get("power_entity") or "") for b in batteries if isinstance(b, dict))
    meters = [c[key] for key in POWER_ENTITY_KEYS if isinstance(c[key], str) and c[key]]
    for key in POWER_ENTITY_KEYS:
        eid = c[key]
        if not isinstance(eid, str) or not eid:
            continue
        obj = hass.states.get(eid)
        if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
            errors[key] = "power_unit"
        if eid in reserved or any(meter_sources_overlap(hass, eid, other) for other in reserved if other):
            errors[key] = "dedicated_meter"
        if any(meter_sources_overlap(hass, eid, other) for other in meters if other != eid):
            errors[key] = "sg_meter_overlap"
    frequency = c.get("compressor_frequency_entity")
    if isinstance(frequency, str) and frequency:
        obj = hass.states.get(frequency)
        if not frequency.startswith("sensor.") or obj is None or obj.attributes.get("unit_of_measurement") != "Hz":
            errors["compressor_frequency_entity"] = "sg_frequency_unit"
    status = c.get("sg_status_entity")
    if isinstance(status, str) and status and (status == c["entity_id"] or not status.startswith(("sensor.", "binary_sensor."))
            or meter_sources_overlap(hass, status, c["entity_id"])):
        errors["sg_status_entity"] = "sg_status_source"
    if c.get("enabled") is True and not (site or {}).get("pv_entity"):
        errors["base"] = "sg_pv_required"
    return errors


# Stable public aliases for one shared runtime/options schema.
normalized_settings = normalize_config
normalized_config = normalize_config
