"""Actual solar budget; native Panasonic demand is never reclaimed or added back."""
from __future__ import annotations
import math
import time
from .sg_config import meter_sources_overlap


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def heatpump_shared(runtime):
    return bool(getattr(runtime, "panasonic", None) and runtime.panasonic.configured)


# Broad sensor plausibility ceiling, not a demand estimate or start threshold.
# Local electrical limits are still applied separately using actual net P1.
_POWER_PLAUSIBILITY_W = 100000.0


def _reserved_meters(runtime):
    reserved = {runtime.settings.get(k) for k in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity")}
    reserved.update(c.get("power_entity") for c in getattr(runtime, "configs", {}).values())
    reserved.add(getattr(runtime, "wallbox_settings", {}).get("power_entity"))
    reserved.update(c.get("power_entity") for c in getattr(getattr(runtime, "battery_fleet", None), "configs", {}).values())
    return {eid for eid in reserved if isinstance(eid, str) and eid}


def _meter_reading(runtime, config, meter, reserved, now):
    result = {"valid": False, "watts": None, "measured_wall": None,
              "entity_id": meter or None, "reason": "Geen actuele betrouwbare deelmeting"}
    if not isinstance(meter, str) or not meter:
        return result
    obj = runtime.hass.states.get(meter)
    attrs = getattr(obj, "attributes", {}) or {}
    if (meter in reserved or any(meter_sources_overlap(runtime.hass, meter, other) for other in reserved)
            or obj is None or any(attrs.get(k) for k in ("restored", "estimated", "is_estimated"))
            or any(word in str(attrs.get("friendly_name", "")).casefold() for word in ("geschat", "estimated"))):
        return result
    if attrs.get("unit_of_measurement") not in ("W", "kW"):
        return result
    watts, stamp = runtime._power(meter, config.get("stale_s", 120))
    watts, stamp = _number(watts), _number(stamp)
    if (watts is None or not 0 <= watts <= _POWER_PLAUSIBILITY_W or stamp is None
            or not -5 <= now-stamp <= config.get("stale_s", 120)):
        return result
    return {**result, "valid": True, "watts": watts, "measured_wall": stamp, "reason": ""}


def heatpump_power(runtime, *, now_wall=None):
    """One legacy source or two confirmed disjoint actual supply measurements.

    Invalid/stale split readings never become a partial total. A known part is
    retained separately, including a legitimate measured zero. Nothing here is
    SG-owned consumption or recoverable solar credit.
    """
    config = getattr(getattr(runtime, "panasonic", None), "settings", {})
    meter, scope = config.get("power_entity"), config.get("power_scope", "unconfirmed")
    first, second = config.get("power_supply1_entity"), config.get("power_supply2_entity")
    split = bool(first or second)
    result = {"valid": False, "complete": False, "watts": None, "measured_wall": None,
              "entity_id": meter or None, "shared": True, "meter_scope": "split" if split else scope,
              "split_confirmed": config.get("split_power_confirmed") is True,
              "reason": "Geen actuele betrouwbare warmtepompmeting", "supplies": {}}
    now = time.time() if now_wall is None else now_wall
    reserved = _reserved_meters(runtime)
    if not split:
        reading = _meter_reading(runtime, config, meter, reserved, now)
        return {**result, **reading, "complete": reading["valid"] and scope == "total"}
    one = _meter_reading(runtime, config, first, reserved, now)
    two = _meter_reading(runtime, config, second, reserved, now)
    result.update(entity_id=None, supplies={"supply1": one, "supply2": two})
    if meter or (first and second and meter_sources_overlap(runtime.hass, first, second)):
        result["reason"] = "Warmtepompmeters overlappen; geen bevestigd totaal"
        return result
    if config.get("split_power_confirmed") is not True:
        result["reason"] = "Dekking en niet-overlap van beide voedingen nog niet lokaal bevestigd"
        return result
    if not one["valid"] or not two["valid"]:
        result["reason"] = "Warmtepomptotaal onvolledig; een deelmeter ontbreekt of is niet actueel"
        return result
    total = one["watts"] + two["watts"]
    if total > _POWER_PLAUSIBILITY_W:
        result["reason"] = "Warmtepomptotaal buiten plausibel meetbereik"
        return result
    return {**result, "valid": True, "complete": True, "watts": total,
            "measured_wall": min(one["measured_wall"], two["measured_wall"]), "reason": ""}


def sg_solar_budget(runtime):
    grid, valid, discharge, ready, grid_stamp = runtime._site_data()
    pv, pv_stamp = runtime._power(runtime.settings.get("pv_entity"))
    values = [_number(x) for x in (grid, pv, discharge, grid_stamp, pv_stamp)]
    result = {"valid": False, "available_w": 0.0, "reason": "Wacht op betrouwbare actuele zonnemetingen"}
    if not valid or not ready or any(v is None for v in values):
        return result
    grid, pv, discharge, grid_stamp, pv_stamp = values
    now, stale = time.time(), runtime.sg_boost.settings["stale_s"]
    if pv < 0 or discharge < 0 or not all(-5 <= now-stamp <= stale for stamp in (grid_stamp, pv_stamp)):
        return result
    filtered = _number(runtime.filtered)
    if runtime.filtered is not None and filtered is None:
        return result
    reserve = max(0.0, runtime.settings["reserve_w"]) + max(0.0, runtime.isolated_reserve_w)
    reserve += max(0.0, getattr(runtime, "_dishwasher_comfort_reserve", 0))
    available = max(0.0, min(pv, -max(grid, filtered if filtered is not None else grid)-discharge)-reserve)
    return {"valid": True, "available_w": available, "grid_w": grid, "discharge_w": discharge,
            "pv_w": pv, "reserve_w": reserve, "stamp": min(grid_stamp, pv_stamp),
            "reason": "Werkelijk restoverschot na beschermde toestellen"}
