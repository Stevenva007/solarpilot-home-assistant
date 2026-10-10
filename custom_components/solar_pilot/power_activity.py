"""Read-only electrical activity and task interpretation, never control proof.

The caller supplies already validated meter coverage from ``heatpump_power``.
An interpretation threshold describes electrical uptake, not compressor motion,
thermal output, received SG or authority to change Panasonic operation.
"""
from __future__ import annotations

import time

from .sg_config import finite


POWER_NOTE = "Afgeleid uit gemeten verbruik; compressorbedrijf/warmteproductie niet afzonderlijk gemeten."
_HEATING = frozenset({"heating", "preheating"})
_TANK_HEATING = _HEATING | {"dhw", "hot_water"}
_COOLING = frozenset({"cooling", "precooling"})
_INACTIVE = frozenset({"idle", "off", "inactive", "none"})
_ROLES = frozenset({"unconfirmed", "main", "heater"})
_PROVIDER_TASKS = {"HEATING_WATER": "tapwater_heating", "HEATING": "space_heating", "COOLING": "space_cooling"}


def _text(value):
    return str(value or "").strip().casefold()


def _stamp(value, now, stale):
    value = finite(value)
    return value if value is not None and -5 <= now - value <= stale else None


def _state(watts, threshold):
    if watts is None:
        return "unknown"
    if watts == 0:
        return "off"
    if threshold is None:
        return "unknown"
    return "active" if watts >= threshold else "basis"


def _supply(number, reading, config, threshold, now, stale):
    role = config.get(f"power_supply{number}_role", "unconfirmed")
    role = role if role in _ROLES else "unconfirmed"
    stamp = _stamp(reading.get("measured_wall"), now, stale)
    watts = finite(reading.get("watts"))
    valid = reading.get("valid") is True and stamp is not None and watts is not None and watts >= 0
    watts, stamp = (watts, stamp) if valid else (None, None)
    if role == "heater":
        label = ("Elektrische ondersteuning onbekend" if watts is None else
                 "Elektrische ondersteuning uit (0 W)" if watts == 0 else
                 f"Elektrische ondersteuning verbruikt {watts:g} W")
    elif role == "main":
        label = ("Hoofdcircuit onbekend (inclusief regeling/pompen)" if watts is None else
                 f"Hoofdcircuit verbruikt {watts:g} W (inclusief regeling/pompen)")
    else:
        label = f"Voeding {number} onbekend" if watts is None else f"Voeding {number}: {watts:g} W"
    return {"number": number, "role": role, "label": label, "watts": watts,
            "valid": valid, "state": _state(watts, threshold), "observed_at": stamp}


def _task(*, tank, tank_entity, tank_stamp, tank_action, zones, native_programs, context,
          context_reliable, context_stamp, conflict, now, stale):
    """Return bounded interpretive task evidence, independent of native proof."""
    attrs = getattr(tank, "attributes", {}) or {}
    tank_stamp = _stamp(tank_stamp, now, stale)
    native_tank = isinstance(tank_entity, str) and tank_entity.startswith(("water_heater.", "climate."))
    tank_valid = (native_tank and tank is not None and tank_stamp is not None
                  and _text(getattr(tank, "state", None)) not in ("unknown", "unavailable", "")
                  and not any(attrs.get(key) for key in ("restored", "estimated", "is_estimated")))
    reported_tank_action = _text(attrs.get("hvac_action")) if tank_valid else ""
    tank_mode = _text(attrs.get("operation_mode")) if tank_valid and tank_entity.startswith("water_heater.") else ""
    tank_state = _text(getattr(tank, "state", None)) if tank_valid and tank_entity.startswith("water_heater.") else ""
    provider_stamp = _stamp(tank_action.get("observed_at"), now, stale)
    provider_valid = (tank_valid and tank_entity.startswith("water_heater.")
        and tank_action.get("entity_id") == tank_entity
        and tank_action.get("source") == "aquarea_poll" and tank_action.get("fresh") is True
        and _PROVIDER_TASKS.get(tank_action.get("raw_action")) is not None
        and _PROVIDER_TASKS.get(tank_action.get("raw_action")) == tank_action.get("action")
        and provider_stamp is not None)
    provider_task = tank_action["action"] if provider_valid else None
    heating_stamps = ([tank_stamp] if tank_valid and reported_tank_action in _TANK_HEATING else [])
    if provider_task == "tapwater_heating":
        heating_stamps.extend((provider_stamp, tank_stamp))
    tank_heating = bool(heating_stamps)
    tank_heating_stamp = min(heating_stamps) if heating_stamps else None
    selected_tank_heating = tank_valid and (tank_mode == "heating" or tank_state == "heating")
    tank_idle = tank_valid and not tank_heating and any(
        value in _INACTIVE for value in (reported_tank_action, tank_mode, tank_state))
    tank_idle = tank_idle and not selected_tank_heating

    heat, cool = [], []
    for zone in zones:
        stamp = _stamp(zone.get("observed_at"), now, stale)
        if zone.get("available") is not True or zone.get("action_valid", True) is not True or stamp is None:
            continue
        action = _text(zone.get("action"))
        if action in _HEATING:
            heat.append(stamp)
        elif action in _COOLING:
            cool.append(stamp)
    if provider_task == "space_heating":
        heat.append(min(provider_stamp, tank_stamp))
    elif provider_task == "space_cooling":
        cool.append(min(provider_stamp, tank_stamp))
    programme_cool = [stamp for row in native_programs
                      if row.get("fresh") is True and row.get("program") == "cooling"
                      and (stamp := _stamp(row.get("observed_at"), now, stale)) is not None]
    programme_heat = [stamp for row in native_programs
                      if row.get("fresh") is True and row.get("program") == "heating"
                      and (stamp := _stamp(row.get("observed_at"), now, stale)) is not None]
    context_stamp = _stamp(context_stamp, now, stale) if context_reliable is True else None
    cooling_context = context_stamp is not None and context == "space_cooling"

    # Concurrent DHW and space actions are not two independently established
    # physical tasks on the shared heat pump. Preserve the measured uptake and
    # explicitly leave its function unresolved.
    if (conflict or heat and (cool or programme_cool or cooling_context)
            or cool and programme_heat
            or tank_heating and (heat or cool or programme_cool or cooling_context)):
        stamps = heat + cool + programme_cool + programme_heat
        if tank_heating:
            stamps.append(tank_heating_stamp)
        if context_stamp is not None:
            stamps.append(context_stamp)
        return None, "Panasonic meldt meerdere of tegenstrijdige taken; de functie is niet eenduidig.", min(stamps) if stamps else None
    if tank_heating:
        return "tapwater_heating", "Afgeleid uit gemeten verbruik en Panasonic-tankmelding.", tank_heating_stamp
    if heat:
        note = "Afgeleid uit gemeten verbruik en Panasonic-bedrijfsactie." if provider_task == "space_heating" else "Afgeleid uit gemeten verbruik en Panasonic-ruimteactie."
        return "space_heating", note, min(heat + ([tank_stamp] if tank_idle else []))
    if cool:
        note = "Afgeleid uit gemeten verbruik en Panasonic-bedrijfsactie." if provider_task == "space_cooling" else "Afgeleid uit gemeten verbruik en Panasonic-ruimteactie."
        return "space_cooling", note, min(cool + ([tank_stamp] if tank_idle else []))
    # A selected native programme is useful task context only alongside a
    # current explicit idle/off tank report and the caller's reliable context.
    if tank_idle and context_stamp is not None and context in ("space_heating", "space_cooling"):
        return context, "Afgeleid uit gemeten verbruik en Panasonic-programmacontext; tank meldt rust.", min(tank_stamp, context_stamp)
    if selected_tank_heating:
        return None, "Tank staat op verwarmen; actuele tapwateropwarming niet afzonderlijk bevestigd.", tank_stamp
    return None, "", None


def power_activity(power, config, *, tank=None, tank_entity="", tank_stamp=None, tank_action=None,
                   zones=(), native_programs=(), context=None, context_reliable=False,
                   context_stamp=None, conflict=False, now_wall=None):
    """Build presentation data without fetching sources or changing policy."""
    now = time.time() if now_wall is None else now_wall
    stale = finite(config.get("stale_s", 120))
    stale = stale if stale is not None and stale > 0 else 120.0
    threshold = finite(config.get("power_activity_threshold_w", 200))
    threshold = threshold if threshold is not None and threshold > 0 else None
    supplies = [_supply(number, reading, config, threshold, now, stale)
                for number in (1, 2)
                if (reading := power.get("supplies", {}).get(f"supply{number}")) is not None]
    if not supplies and power.get("meter_scope") in ("supply1", "supply2"):
        supplies = [_supply(int(power["meter_scope"][-1]), power, config, threshold, now, stale)]
    power_stamp = _stamp(power.get("measured_wall"), now, stale)
    watts = finite(power.get("watts"))
    known = power.get("valid") is True and watts is not None and watts >= 0 and power_stamp is not None
    complete = known and power.get("complete") is True
    result = {"state": "unknown", "active": False, "label": "Elektrisch verbruik onbekend",
              "note": power.get("reason") or "Wacht op actuele betrouwbare vermogensmetingen.",
              "evidence": "metered_power", "threshold_w": threshold,
              "observed_at": None, "stale_s": stale, "total_w": watts if complete else None,
              "complete": complete, "function": None, "context_observed_at": None,
              "supplies": supplies}
    if threshold is None:
        return {**result, "note": "Interpretatiedrempel ongeldig; gemeten waarden blijven afzonderlijk zichtbaar."}
    if not complete:
        valid = [row for row in supplies if row["valid"]]
        active = [row for row in valid if row["state"] == "active"]
        if valid:
            numbers = " en ".join(str(row["number"]) for row in active)
            return {**result, "state": "partial", "active": bool(active),
                    "label": f"Actief verbruik op voeding {numbers}" if active else "Deelmeting; totaal onbekend",
                    "note": result["note"] + (" " + POWER_NOTE if active else ""),
                    "observed_at": min(row["observed_at"] for row in active or valid)}
        # Preserve a legacy partial single meter without treating its coverage
        # label as a complete heat-pump measurement.
        if known:
            return {**result, "state": "partial", "active": watts >= threshold,
                    "label": "Actief verbruik op deelmeter" if watts >= threshold else "Deelmeting; totaal onbekend",
                    "observed_at": power_stamp}
        return result
    state = _state(watts, threshold)
    result.update(state=state, active=state == "active", observed_at=power_stamp,
                  label={"off": "Geen elektrisch verbruik", "basis": "Basisverbruik", "active": "Warmtepomp werkt"}[state],
                  note=POWER_NOTE)
    if state != "active":
        return result
    function, task_note, stamp = _task(tank=tank, tank_entity=tank_entity, tank_stamp=tank_stamp,
        tank_action=tank_action or {}, zones=zones, native_programs=native_programs, context=context,
        context_reliable=context_reliable, context_stamp=context_stamp,
        conflict=conflict, now=now, stale=stale)
    if task_note:
        result.update(note=task_note + " " + POWER_NOTE, context_observed_at=stamp,
                      evidence="metered_power_and_context" if stamp is not None else "metered_power")
        if stamp is not None:
            result["observed_at"] = min(power_stamp, stamp)
    if function:
        result.update(function=function, label={"tapwater_heating": "Sanitair water opwarmen",
            "space_heating": "Ruimte verwarmen", "space_cooling": "Ruimte koelen"}[function])
    return result
