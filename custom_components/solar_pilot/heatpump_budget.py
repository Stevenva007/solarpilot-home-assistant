"""One physical electricity budget for space climate and domestic hot water.

The site meter already contains the heat pump's current draw. A physical heat
pump meter may therefore be added back once when judging ongoing availability,
but it is not evidence that either heating function is actually operating. This
module never writes a device, uses an inferred watt estimate as measured power,
or borrows Wallbox consumption for optional heat-pump availability.
"""
from __future__ import annotations

import math
import time


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _fresh(stamp, now, stale_s):
    value = _number(stamp)
    age = now - value if value is not None else None
    return value is not None and value > 0 and -5 <= age <= stale_s


def heatpump_shared(runtime):
    """Configured room zones share the DHW meter's physical heat pump.

    Disabling advice or control does not turn a shared physical meter into a
    dedicated tank meter. No household-specific entity-name inference is used.
    """
    dhw = getattr(runtime, "dhw", None)
    climate = getattr(runtime, "smart_climate", None)
    return bool(getattr(dhw, "configured", False)
                and getattr(climate, "settings", {}).get("zone_entities"))


def heatpump_power(runtime, *, now_wall=None):
    """Read one current physical HP meter; missing/duplicate/estimated is unknown."""
    now = time.time() if now_wall is None else now_wall
    dhw = getattr(runtime, "dhw", None)
    config = getattr(dhw, "config", {})
    meter = config.get("power_entity")
    scope = config.get("power_meter_scope", "heat_pump")
    result = {"valid": False, "watts": None, "measured_wall": None,
              "entity_id": meter or None, "shared": heatpump_shared(runtime),
              "meter_scope": scope}
    if not isinstance(meter, str) or not meter or not getattr(dhw, "configured", False):
        return result
    # A tank-only meter cannot tell room control how much the complete shared
    # heat pump currently consumes. Keep it out of the physical HP add-back.
    if scope not in ("heat_pump", "tank") or scope == "tank" and result["shared"]:
        return result
    settings = getattr(runtime, "settings", {})
    reserved = {settings.get(key) for key in (
        "grid_entity", "export_entity", "pv_entity", "battery_power_entity")}
    reserved.update(c.get("power_entity") for c in getattr(runtime, "configs", {}).values())
    reserved.add(getattr(runtime, "wallbox_settings", {}).get("power_entity"))
    fleet = getattr(runtime, "battery_fleet", None)
    reserved.update(c.get("power_entity") for c in getattr(fleet, "configs", {}).values())
    if meter in reserved:
        return result
    obj = runtime.hass.states.get(meter)
    attributes = getattr(obj, "attributes", {}) or {}
    if (obj is None or attributes.get("restored") or attributes.get("estimated") is True
            or attributes.get("is_estimated") is True
            or any(word in str(attributes.get("friendly_name", "")).casefold()
                   for word in ("geschat", "estimated"))):
        return result
    max_age = _number(getattr(dhw, "settings", {}).get("stale_s", 300))
    max_age = min(300.0, max_age) if max_age is not None and max_age >= 0 else 300.0
    watts, stamp = runtime._power(meter, max_age)
    watts = _number(watts)
    if watts is None or watts < 0 or not _fresh(stamp, now, max_age):
        return result
    return {**result, "valid": True, "watts": watts, "measured_wall": float(stamp)}


def shared_commitment(dhw_planned_w, climate_planned_w, heatpump_w=None):
    """Reserve a shared envelope once, minus its already measured current draw.

    Missing live metering reserves the full envelope. Both proposals describe
    the same appliance's total electrical envelope; they are never added. An
    invalid proposal is an input error, rather than permission to reserve zero.
    """
    dhw, climate = _number(dhw_planned_w), _number(climate_planned_w)
    if dhw is None or climate is None or dhw < 0 or climate < 0:
        raise ValueError("Heat-pump commitments must be finite non-negative watts")
    measured = _number(heatpump_w)
    measured = measured if measured is not None and measured >= 0 else 0.0
    return max(0.0, max(dhw, climate) - measured)


def climate_solar_budget(runtime, *, now_wall=None):
    """Fresh remaining solar watts plus one optional physical HP add-back.

    ``available_w`` and ``residual_w`` use actual net export after reserves.
    ``compensated_w`` also includes the same appliance's current measured draw;
    callers must restrict this to sustaining an already issued solar allowance.
    A new start cannot spend power merely because an OFF command was requested.
    Command serialization, settling, newer P1, phase and import ceilings remain
    mandatory dispatch guards in the runtime; this helper provides no exemption.
    """
    now = time.time() if now_wall is None else now_wall
    result = {"valid": False, "reason": "Wacht op betrouwbare actuele zonnemetingen",
              "available_w": 0.0, "residual_w": 0.0, "compensated_w": 0.0,
              "heatpump_w": None, "heatpump_meter_valid": False,
              "measured_wall": None, "solar_ceiling_w": 0.0}
    grid, valid, discharge, ready, grid_stamp = runtime._site_data()
    settings = runtime.settings
    pv, pv_stamp = runtime._power(settings.get("pv_entity"))
    raw_grid, pv, discharge = _number(grid), _number(pv), _number(discharge)
    stale = _number(settings.get("stale_s", 300))
    stale = stale if stale is not None and stale >= 0 else 300.0
    filtered = _number(getattr(runtime, "filtered", None))
    if getattr(runtime, "filtered", None) is not None and filtered is None:
        return result
    if (not valid or not ready or raw_grid is None or pv is None or pv < 0
            or discharge is None or discharge < 0
            or not _fresh(grid_stamp, now, stale) or not _fresh(pv_stamp, now, stale)):
        return result
    filtered = raw_grid if filtered is None else filtered
    reserve = _number(settings.get("reserve_w", 0))
    isolated = _number(getattr(runtime, "isolated_reserve_w", 0))
    protected_total = _number(getattr(runtime, "_dishwasher_comfort_reserve", 0))
    shared_reserve = _number(getattr(runtime, "_shared_heatpump_comfort_reserve_w", 0))
    if (any(value is None or value < 0 for value in (
            reserve, isolated, protected_total, shared_reserve))
            or shared_reserve > protected_total):
        return result
    # The dishwasher allocator reserves imminent normal HP demand against
    # *other* devices. Climate availability belongs to that same HP envelope,
    # so that part cannot be deducted again from its own solar threshold. The
    # unmetered dishwasher reserve and other protected appliances still count.
    protected = protected_total - shared_reserve
    all_reserves = reserve + isolated + protected
    # Battery power is subtracted from export, not from PV itself: PV remains an
    # independent physical ceiling, so its watts cannot be subtracted twice.
    net_solar = -max(raw_grid, filtered) - discharge
    actual = max(0.0, min(pv, net_solar) - all_reserves)
    hp = heatpump_power(runtime, now_wall=now)
    measured = hp["watts"] if hp["valid"] else 0.0
    compensated = max(0.0, min(pv, net_solar + measured) - all_reserves)
    return {**result, "valid": True, "reason": "Actueel zonneoverschot na huis- en toestelreserves",
            "available_w": actual, "residual_w": actual, "compensated_w": compensated,
            "heatpump_w": hp["watts"], "heatpump_meter_valid": hp["valid"],
            "heatpump_measured_wall": hp["measured_wall"],
            "measured_wall": min(float(grid_stamp), float(pv_stamp)),
            "solar_ceiling_w": max(0.0, pv - all_reserves),
            "reserve_w": reserve, "isolated_reserve_w": isolated,
            "protected_reserve_w": protected,
            "shared_heatpump_reserve_w": shared_reserve,
            "raw_grid_w": raw_grid, "filtered_grid_w": filtered,
            "battery_discharge_w": discharge}
