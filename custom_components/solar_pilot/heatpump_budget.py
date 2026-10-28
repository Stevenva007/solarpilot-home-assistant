"""Actual residual solar and separately measured HP solar for SG eligibility."""
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


def _source_evidence(obj, now):
    """Retain source facts without granting an unusable report freshness.

    An absent last_reported may use HA's last_updated for older integrations.
    A malformed last_reported must not fall back to another, newer timestamp.
    A newer last_updated/last_changed never overrides an existing last_reported.
    Reads and controller cycles never create or refresh a source timestamp.
    The usable measured_wall remains separate and is set only after validation.
    """
    attrs = getattr(obj, "attributes", {}) or {}
    raw_value = getattr(obj, "state", None)
    unit = attrs.get("unit_of_measurement")
    source_value = str(raw_value)[:128] if raw_value is not None else None
    source_unit = str(unit)[:32] if unit is not None else None
    stamp = getattr(obj, "last_reported", None)
    kind = "last_reported" if stamp is not None else None
    if stamp is None:
        stamp = getattr(obj, "last_updated", None)
        kind = "last_updated" if stamp is not None else None
    try:
        raw_reported = stamp.timestamp()
        reported = (_number(raw_reported) if isinstance(raw_reported, (int, float))
                    and not isinstance(raw_reported, bool) else None)
        if reported is not None and reported < 0:
            reported = None
    except (AttributeError, TypeError, ValueError, OSError, OverflowError):
        reported = None
    value = _number(raw_value)
    watts = value * (1000 if unit == "kW" else 1) if value is not None and unit in ("W", "kW") else None
    if watts is not None and not math.isfinite(watts):
        watts = None
    return {"source_reported_wall": reported, "source_timestamp_kind": kind,
            "source_unit": source_unit, "source_value": source_value,
            "source_watts": watts, "source_age_s": now-reported if reported is not None else None}


def _meter_reading(runtime, config, meter, reserved, now):
    result = {"valid": False, "watts": None, "measured_wall": None,
              "entity_id": meter or None, "reason": "Geen vermogensbron ingesteld",
              "rejection_reason": "not_configured", "normalized": False,
              "normalization_reason": None, **_source_evidence(None, now)}

    def rejected(code, reason):
        return {**result, "rejection_reason": code, "reason": reason}

    if not isinstance(meter, str) or not meter:
        return result
    obj = runtime.hass.states.get(meter)
    attrs = getattr(obj, "attributes", {}) or {}
    result.update(_source_evidence(obj, now))
    if obj is None:
        return rejected("missing", "Vermogensbron ontbreekt")
    if meter in reserved or any(meter_sources_overlap(runtime.hass, meter, other) for other in reserved):
        return rejected("overlap", "Vermogensbron overlapt met een andere gebruikte meter")
    if attrs.get("restored"):
        return rejected("restored", "Herstelde toestand is geen nieuwe vermogensmeting")
    if (any(attrs.get(k) for k in ("estimated", "is_estimated"))
            or any(word in str(attrs.get("friendly_name", "")).casefold() for word in ("geschat", "estimated"))):
        return rejected("estimated", "Geschat vermogen is geen werkelijke vermogensmeting")
    if attrs.get("unit_of_measurement") not in ("W", "kW"):
        return rejected("unsupported_unit", "Vermogenseenheid ontbreekt of is geen W/kW")
    if result["source_watts"] is None:
        return rejected("invalid_value", "Vermogenswaarde ontbreekt of is niet eindig numeriek")
    if abs(result["source_watts"]) > _POWER_PLAUSIBILITY_W:
        return rejected("out_of_range", "Vermogenswaarde buiten plausibel meetbereik")
    if result["source_reported_wall"] is None:
        return rejected("invalid_timestamp", "Echte rapportagetijd ontbreekt of is ongeldig")
    if result["source_age_s"] < -5:
        return rejected("future_timestamp", "Rapportagetijd ligt in de toekomst")
    if result["source_age_s"] > config.get("stale_s", 120):
        return rejected("stale", "Vermogensrapport is te oud")
    validation_flags = tuple(bool(attrs.get(key)) for key in ("restored", "estimated", "is_estimated"))
    source_name = str(attrs.get("friendly_name", ""))
    watts, stamp = runtime._power(meter, config.get("stale_s", 120))
    watts, stamp = _number(watts), _number(stamp)
    if (watts is None or abs(watts) > _POWER_PLAUSIBILITY_W or stamp is None
            or not -5 <= now-stamp <= config.get("stale_s", 120)):
        return rejected("unusable_report", "Vermogensrapport is niet bruikbaar volgens de actuele broncontrole")
    current = runtime.hass.states.get(meter)
    current_attrs = getattr(current, "attributes", {}) or {}
    if (current is not obj or _source_evidence(current, now) != {
            key: result[key] for key in _source_evidence(None, now)}
            or tuple(bool(current_attrs.get(key)) for key in ("restored", "estimated", "is_estimated")) != validation_flags
            or str(current_attrs.get("friendly_name", "")) != source_name
            or _reserved_meters(runtime) != reserved
            or watts != result["source_watts"] or stamp != result["source_reported_wall"]):
        return rejected("source_changed", "Vermogensbron veranderde tijdens de broncontrole; wacht op een samenhangend nieuw rapport")
    if any(meter_sources_overlap(runtime.hass, meter, other) for other in reserved):
        return rejected("overlap", "Vermogensbron overlapt met een andere gebruikte meter")
    normalized = watts < 0
    # Explicit HP-consumption policy only. Raw signed reports and timestamps
    # stay available; site/P1/PV/battery/fase measurements are never modified.
    watts = max(0.0, watts)
    return {**result, "valid": True, "watts": watts, "measured_wall": stamp,
            "normalized": normalized, "normalization_reason": "negative_as_zero" if normalized else None,
            "rejection_reason": None, "reason": ""}


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
              "reason": "Geen actuele betrouwbare warmtepompmeting", "rejection_reason": "incomplete", "supplies": {}}
    now = time.time() if now_wall is None else now_wall
    reserved = _reserved_meters(runtime)
    if not split:
        reading = _meter_reading(runtime, config, meter, reserved, now)
        return {**result, **reading, "complete": reading["valid"] and scope == "total"}
    one = _meter_reading(runtime, config, first, reserved, now)
    two = _meter_reading(runtime, config, second, reserved, now)
    result.update(entity_id=None, supplies={"supply1": one, "supply2": two})
    if meter or (first and second and meter_sources_overlap(runtime.hass, first, second)):
        result["rejection_reason"] = "overlap"
        result["reason"] = "Warmtepompmeters overlappen; geen bevestigd totaal"
        return result
    if config.get("split_power_confirmed") is not True:
        result["rejection_reason"] = "split_unconfirmed"
        result["reason"] = "Dekking en niet-overlap van beide voedingen nog niet lokaal bevestigd"
        return result
    if not one["valid"] or not two["valid"]:
        failures = [f"voeding {index}: {reading['reason']}" for index, reading in ((1, one), (2, two)) if not reading["valid"]]
        result["reason"] = "Warmtepomptotaal onvolledig; " + "; ".join(failures)
        return result
    total = one["watts"] + two["watts"]
    if total > _POWER_PLAUSIBILITY_W:
        result["rejection_reason"] = "out_of_range"
        result["reason"] = "Warmtepomptotaal buiten plausibel meetbereik"
        return result
    return {**result, "valid": True, "complete": True, "watts": total,
            "measured_wall": min(one["measured_wall"], two["measured_wall"]), "rejection_reason": None, "reason": ""}


def sg_expected_increment(runtime, budget=None):
    """Expected total HP draw minus its proven current complete measurement.

    Other appliances already appear in P1. Their nominal watts or a possible
    later heating peak are not an extra commitment. Unknown HP draw receives
    no subtraction; malformed settings fail closed at electrical gates.
    """
    total = _number(runtime.sg_boost.settings.get("expected_power_w"))
    if total is None or total < 0:
        return math.inf
    budget = sg_solar_budget(runtime) if budget is None else budget
    current = _number(budget.get("hp_power_w"))
    stamp = _number(budget.get("hp_power_reported_at"))
    stale = _number(runtime.sg_boost.settings.get("stale_s"))
    site = [_number(budget.get(key)) for key in ("pv_w", "grid_w", "discharge_w")]
    coherent = (all(value is not None for value in site) and site[0] >= 0 and site[2] >= 0
                and current is not None and current <= max(0.0, sum(site))+250.0)
    complete = (budget.get("valid") is True and budget.get("hp_power_complete") is True
                and current is not None and 0 <= current <= _POWER_PLAUSIBILITY_W
                and stamp is not None and stale is not None and coherent
                and -5 <= time.time()-stamp <= stale)
    return max(0.0, total-(current if complete else 0.0))


def sg_solar_budget(runtime):
    """Keep physical export separate from the solar already used by the HP.

    Only a complete, fresh dedicated actual HP measurement can credit the SG
    start threshold. The combined measured balance discounts site import and
    battery discharge, and measured PV caps the total. Its incremental credit
    is an attribution, not a separate measured PV-to-HP share. This deliberately
    conservative budget is not headroom, SG-owned watts or forecast power.
    Confirmed autonomous solar charging can be allocated to SG only when SG
    precedes the Wallbox in the central order. It remains conditional EV power,
    never measured export; the dispatch guard checks stability and hard limits.
    """
    grid, valid, discharge, ready, grid_stamp = runtime._site_data()
    pv, pv_stamp = runtime._power(runtime.settings.get("pv_entity"))
    values = [_number(x) for x in (grid, pv, discharge, grid_stamp, pv_stamp)]
    result = {"valid": False, "available_w": 0.0, "eligible_w": 0.0, "hp_solar_w": 0.0,
              "hp_power_w": None, "hp_credit_reason": "Wacht op betrouwbare actuele zonnemetingen",
              "reason": "Wacht op betrouwbare actuele zonnemetingen"}
    actual_entities = {runtime.settings.get(key) for key in ("grid_entity", "pv_entity")}
    if runtime.settings.get("grid_sign") == "separate":
        actual_entities.add(runtime.settings.get("export_entity"))
    fleet = getattr(runtime, "battery_fleet", None)
    if getattr(fleet, "settings", {}).get("enabled") and getattr(fleet, "configured", False):
        actual_entities.update(config.get("power_entity") for config in getattr(fleet, "configs", {}).values())
    else:
        actual_entities.add(runtime.settings.get("battery_power_entity"))
    for entity in actual_entities:
        attrs = (getattr(runtime.hass.states.get(entity), "attributes", {}) or {}) if entity else {}
        if any(attrs.get(key) for key in ("estimated", "is_estimated", "restored")):
            return {**result, "reason": "Geschatte of herstelde bron is geen actuele werkelijke zonnemeting"}
    if not valid or not ready or any(v is None for v in values):
        return result
    grid, pv, discharge, grid_stamp, pv_stamp = values
    now, stale = time.time(), float(runtime.sg_boost.settings["stale_s"])
    if pv < 0 or discharge < 0 or not all(-5 <= now-stamp <= stale for stamp in (grid_stamp, pv_stamp)):
        return result
    filtered = _number(runtime.filtered)
    if runtime.filtered is not None and filtered is None:
        return result
    # Actual whole-site P1 already contains appliances' current consumption.
    # A possible future programme peak must not spend today's export twice.
    reserves = [_number(value) for value in (runtime.settings["reserve_w"], runtime.isolated_reserve_w)]
    if any(value is None for value in reserves):
        return result
    reserve = sum(max(0.0, value) for value in reserves)
    conservative_grid = max(grid, filtered if filtered is not None else grid)
    available = max(0.0, min(pv, -conservative_grid-discharge)-reserve)
    residual_stamp = min(grid_stamp, pv_stamp)
    power = heatpump_power(runtime, now_wall=now)
    hp, hp_stamp = _number(power.get("watts")), _number(power.get("measured_wall"))
    complete = (power.get("valid") is True and power.get("complete") is True
                and hp is not None and 0 <= hp <= _POWER_PLAUSIBILITY_W
                and hp_stamp is not None and -5 <= now-hp_stamp <= stale)
    # A fresh but delayed cloud value must still fit the current whole-site
    # balance. Otherwise it cannot provide HP solar credit or lower the new
    # electrical increase. Independent actual export remains usable.
    site_load = max(0.0, pv + grid + discharge)
    hp_incoherent = bool(complete and hp > site_load+250.0)
    if hp_incoherent:
        complete = False
    total = _number(runtime.sg_boost.settings.get("expected_power_w"))
    hp_deducted = bool(complete and hp > 0 and total is not None and total > 0)
    ev = 0.0
    ev_stamp = None
    ev_credit_reason = "Wallbox-monitor staat uit; geen laadvermogen als zonnebijdrage"
    if runtime.wallbox_settings.get("enabled"):
        from .wallbox import state_set
        reading = runtime._wallbox_reading()
        watts, reported = _number(reading.power_w), _number(reading.stamp)
        if not reading.valid or watts is None or watts < 0:
            ev_credit_reason = "Wallbox-bronnen ontbreken of zijn onbruikbaar; geen laadvermogen als zonnebijdrage"
        elif reported is None or not -5 <= now-reported <= min(stale, runtime.wallbox_settings["reclaim_max_age_s"]):
            ev_credit_reason = "Wallbox-rapport te oud of niet actueel; geen laadvermogen als zonnebijdrage"
        elif not isinstance(reading.mode, str) or reading.mode.casefold() not in state_set(runtime.wallbox_settings["full_solar_states"]):
            ev_credit_reason = ("Handmatige Wallbox-laadsessie; geen autonome zonnebijdrage"
                                if reading.mode == "manual" else
                                "Autonome Wallbox-zonnelaadsessie niet bevestigd; geen laadvermogen als zonnebijdrage")
        elif reading.demand is False or watts == 0:
            ev_credit_reason = "Geen actueel autonoom zonnelaadvermogen om over te nemen"
        else:
            # A cloud-polled EV report can still be within its age limit after
            # the charger has already reduced power. It must fit inside the
            # contemporaneous whole-site load before it supplies solar credit.
            # P1/PV also arrive separately: inconsistency removes conditional
            # credit only, never measured export or a live SG permission.
            if watts + (hp if complete else 0.0) > site_load + 250.0:
                ev_credit_reason = "Wallbox-rapport past niet bij de actuele P1/PV-balans; alleen werkelijk zonneoverschot telt"
            else:
                # The complete coherent solar pool is calculated before site
                # import/reserve are deducted. Capping EV watts at the HP
                # estimate here would deduct import from that estimate twice.
                # The actual bounded transfer allowance is a separate runtime
                # check, bounded by the SG total estimate and takeover watts.
                ev = watts
                ev_stamp = reported
                ev_credit_reason = None
    hp_eligible = max(0.0, min(pv, (hp if complete else 0.0)-conservative_grid-discharge)-reserve)
    eligible = max(0.0, min(pv, (hp if complete else 0.0)+ev-conservative_grid-discharge)-reserve)
    credit = max(0.0, hp_eligible-available)
    credit_reason = ("Warmtepomp-rapport past niet bij de actuele P1/PV-balans; geen aftrek of extra zonnebijdrage"
                     if hp_incoherent else "Actueel volledig warmtepompverbruik telt mee in het afgeleide SG-zonnebudget"
                     if credit > 0 else "Geen extra zonnebijdrage uit de warmtepompmeting"
                     if complete else power.get("reason") or "Warmtepomptotaal niet volledig of actueel")
    return {"valid": True, "available_w": available, "eligible_w": eligible, "hp_solar_w": credit,
            "ev_solar_w": ev, "ev_reported_at": ev_stamp, "ev_credit_reason": ev_credit_reason,
            "hp_power_w": hp if complete else None, "hp_power_complete": complete,
            "hp_power_reported_at": hp_stamp, "hp_credit_reason": credit_reason,
            "grid_w": grid, "conservative_grid_w": conservative_grid,
            "discharge_w": discharge, "pv_w": pv, "reserve_w": reserve,
            "grid_reported_at": grid_stamp, "pv_reported_at": pv_stamp,
            "stamp": min([residual_stamp] + ([hp_stamp] if complete and (credit > 0 or hp_deducted) else [])
                         + ([ev_stamp] if ev > 0 else [])),
            "residual_stamp": residual_stamp,
            "reason": "Actueel gemeten restoverschot; geen reservering voor toekomstige toestelpieken"}
