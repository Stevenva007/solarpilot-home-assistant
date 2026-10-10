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
_PROVIDER_ACTIONS = {**_PROVIDER_TASKS, "OFF": "off", "IDLE": "idle"}
_TASK_LABELS = {"tapwater_heating": "Sanitair water opwarmen", "space_heating": "Ruimte verwarmen",
                "space_cooling": "Ruimte koelen"}


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
    assumed = (config.get("power_supply_profile") == "panasonic_standard"
               and role == ("main" if number == 1 else "heater"))
    return {"number": number, "role": role, "role_assumed": assumed, "label": label, "watts": watts,
            "valid": valid, "state": _state(watts, threshold), "observed_at": stamp}


def task_observations(config, *, tank=None, tank_entity="", tank_stamp=None, tank_action=None,
                      device_actions=(), zones=(), native_programs=(), route_context=None,
                      defrost=None, now_wall=None):
    """Native task and selected/routing context, independent of meter coverage.

    These objects are presentation only. They never become the monitor's
    native programme/context, compressor evidence or an SG guard.
    """
    now = time.time() if now_wall is None else now_wall
    stale = finite(config.get("stale_s", 120)) or 120.0
    empty = {"function": None, "label": "Actuele Panasonic-taak niet bevestigd", "note": "",
             "source": "none", "observed_at": None, "stale_s": stale}
    actual = dict(empty)
    context = {**empty, "label": "", "kind": "none"}
    attrs = getattr(tank, "attributes", {}) or {}
    stamp = _stamp(tank_stamp, now, stale)
    native_tank = isinstance(tank_entity, str) and tank_entity.startswith(("water_heater.", "climate."))
    tank_valid = (native_tank and tank is not None and stamp is not None
                  and _text(getattr(tank, "state", None)) not in ("unknown", "unavailable", "")
                  and not any(attrs.get(key) for key in ("restored", "estimated", "is_estimated")))
    bound = {tank_entity: stamp} if tank_valid else {}
    tasks = []
    if tank_valid and _text(attrs.get("hvac_action")) in _TANK_HEATING:
        tasks.append(("tapwater_heating", stamp, "native_hvac_action"))
    for zone in zones:
        zone_stamp = _stamp(zone.get("observed_at"), now, stale)
        if zone.get("available") is not True or zone.get("action_valid", True) is not True or zone_stamp is None:
            continue
        bound[zone.get("entity_id")] = zone_stamp
        action = _text(zone.get("action"))
        if action in _HEATING | _COOLING:
            tasks.append(("space_heating" if action in _HEATING else "space_cooling", zone_stamp, "native_hvac_action"))
    inactive = []
    for proof in [tank_action or {}, *device_actions]:
        source_stamp = bound.get(proof.get("entity_id"))
        proof_stamp = _stamp(proof.get("observed_at"), now, stale)
        action = _PROVIDER_ACTIONS.get(proof.get("raw_action"))
        if (source_stamp is None or proof_stamp is None or proof.get("fresh") is not True
                or proof.get("source") != "aquarea_poll" or action is None or proof.get("action") != action):
            continue
        used_stamp = min(source_stamp, proof_stamp)
        if action in _TASK_LABELS:
            tasks.append((action, used_stamp, "aquarea_poll"))
        else:
            inactive.append(used_stamp)
    defrost = defrost or {}
    defrost_stamp = _stamp(defrost.get("observed_at"), now, stale)
    if defrost.get("state") == "active" and defrost_stamp is not None:
        actual.update(label="Panasonic meldt ontdooien", note="Ontdooimelding gaat vóór de afgeleide warmte- of koelrichting.",
                      source="aquarea_entity", observed_at=defrost_stamp, conflict=True)
    elif len({task for task, _stamp_, _source in tasks}) > 1 or tasks and inactive:
        actual.update(label="Panasonic-taak niet eenduidig", note="Panasonic meldt meerdere of tegenstrijdige taken; de functie is niet eenduidig.",
                      observed_at=min([row[1] for row in tasks] + inactive), conflict=True)
    elif tasks:
        function = tasks[0][0]
        source = "aquarea_poll" if any(row[2] == "aquarea_poll" for row in tasks) else "native_hvac_action"
        actual.update(function=function, label="Panasonic meldt " + _TASK_LABELS[function].casefold(),
                      note="Gemelde bedrijfsactie; compressorbedrijf en warmteproductie niet afzonderlijk gemeten.",
                      source=source, observed_at=min(row[1] for row in tasks))
    elif inactive:
        actual.update(label="Panasonic meldt rust", source="aquarea_poll", observed_at=min(inactive), inactive=True)

    route = route_context or {}
    route_stamp = _stamp(route.get("observed_at"), now, stale)
    if (tank_valid and route.get("source") == "aquarea_entity" and route.get("kind") == "tank_route"
            and route.get("function") == "tapwater_heating" and route_stamp is not None):
        context.update(function="tapwater_heating", label="Panasonic meldt tankroute",
                       note="Tankroute is context; dit bevestigt op zichzelf geen actuele warmteproductie.",
                       kind="tank_route", source="aquarea_entity", observed_at=min(stamp, route_stamp))
    else:
        programmes = [(row.get("program"), _stamp(row.get("observed_at"), now, stale), "native_program")
                      for row in native_programs if row.get("fresh") is True]
        # Filter selected HA modes independently: estimated zone actions must
        # not return through the controller's broader context fallback.
        programmes.extend(("heating" if _text(row.get("mode")) == "heat" else "cooling",
                           _stamp(row.get("observed_at"), now, stale), "native_mode")
                          for row in zones if row.get("available") is True and row.get("action_valid", True) is True
                          and _text(row.get("mode")) in ("heat", "cool"))
        programmes = [row for row in programmes if row[0] in ("heating", "cooling") and row[1] is not None]
        if programmes and len({row[0] for row in programmes}) == 1:
            function = "space_heating" if programmes[0][0] == "heating" else "space_cooling"
            context.update(function=function, label="Gekozen Panasonic-stand: " + ("verwarmen" if function == "space_heating" else "koelen"),
                           note="Gekozen stand; dit is geen bevestiging van de actuele taak.", kind="selected_program",
                           source=programmes[0][2], observed_at=min(row[1] for row in programmes))
    return actual, context


def _task(*, tank, tank_entity, tank_stamp, tank_action, zones, native_programs, context,
          context_reliable, context_stamp, conflict, now, stale, native_actual,
          display_context, supplies):
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

    actual_stamp = _stamp(native_actual.get("observed_at"), now, stale)
    if actual_stamp is not None and native_actual.get("conflict"):
        return None, native_actual.get("note", "Panasonic-taak niet eenduidig."), actual_stamp
    if actual_stamp is not None and native_actual.get("inactive"):
        return None, "Panasonic meldt rust; gemeten verbruik bevestigt geen afzonderlijke warmte- of koelactie.", actual_stamp
    actual_function = native_actual.get("function") if actual_stamp is not None else None
    programmes = {row.get("program") for row in native_programs if row.get("fresh") is True
                  and _stamp(row.get("observed_at"), now, stale) is not None}
    if actual_function in _TASK_LABELS:
        if conflict:
            return None, "Panasonic meldt meerdere of tegenstrijdige taken; de functie is niet eenduidig.", actual_stamp
        note = ("Afgeleid uit gemeten verbruik en Panasonic-tankmelding." if actual_function == "tapwater_heating" else
                "Afgeleid uit gemeten verbruik en Panasonic-bedrijfsactie." if native_actual.get("source") == "aquarea_poll" else
                "Afgeleid uit gemeten verbruik en Panasonic-ruimteactie.")
        return actual_function, note, min(actual_stamp, tank_stamp) if tank_idle else actual_stamp

    route_stamp = _stamp(display_context.get("observed_at"), now, stale)
    if (not conflict and display_context.get("kind") == "tank_route"
            and display_context.get("source") == "aquarea_entity" and route_stamp is not None
            and any(row["valid"] and row["role"] == "main" and row["state"] == "active" for row in supplies)):
        main_stamps = [row["observed_at"] for row in supplies
                       if row["valid"] and row["role"] == "main" and row["state"] == "active"]
        return "tapwater_heating", "Afgeleid uit gemeten verbruik op het hoofdcircuit en Panasonic-tankroute.", min(route_stamp, *main_stamps)

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
    selected_stamp = _stamp(display_context.get("observed_at"), now, stale)
    selected_valid = (not zones or display_context.get("kind") == "selected_program"
                      and display_context.get("function") == context and selected_stamp is not None)
    if tank_idle and selected_valid and context_stamp is not None and context in ("space_heating", "space_cooling"):
        return context, "Afgeleid uit gemeten verbruik en Panasonic-programmacontext; tank meldt rust.", min(tank_stamp, context_stamp)
    if selected_tank_heating:
        return None, "Tank staat op verwarmen; actuele tapwateropwarming niet afzonderlijk bevestigd.", tank_stamp
    return None, "", None


def power_activity(power, config, *, tank=None, tank_entity="", tank_stamp=None, tank_action=None,
                   zones=(), native_programs=(), context=None, context_reliable=False,
                   context_stamp=None, conflict=False, now_wall=None, device_actions=(),
                   native_actual=None, display_context=None, route_context=None, defrost=None):
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
              "function_source": "none", "function_kind": "none", "activity_kind": "unknown",
              "supply_profile": config.get("power_supply_profile", "unconfirmed"), "supplies": supplies}
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
    actual, selected = task_observations(config, tank=tank, tank_entity=tank_entity, tank_stamp=tank_stamp,
        tank_action=tank_action, device_actions=device_actions, zones=zones, native_programs=native_programs,
        route_context=route_context, defrost=defrost, now_wall=now)
    actual = native_actual if native_actual is not None else actual
    selected = display_context if display_context is not None else selected
    main_active = any(row["valid"] and row["role"] == "main" and row["state"] == "active" for row in supplies)
    heater_active = any(row["valid"] and row["role"] == "heater" and row["state"] == "active" for row in supplies)
    result["activity_kind"] = "mixed" if main_active and heater_active else "main" if main_active else "heater" if heater_active else "unknown"
    if heater_active and not main_active:
        # A separately assigned heater feed can be active while the main
        # circuit only powers controls/pumps. Do not call that compressor work.
        result.update(label="Elektrische bijverwarming actief", note="Gemeten verbruik op de voeding voor elektrische ondersteuning. " + POWER_NOTE)
        return result
    function, task_note, stamp = _task(tank=tank, tank_entity=tank_entity, tank_stamp=tank_stamp,
        tank_action=tank_action or {}, zones=zones, native_programs=native_programs, context=context,
        context_reliable=context_reliable, context_stamp=context_stamp,
        conflict=conflict, now=now, stale=stale, native_actual=actual, display_context=selected, supplies=supplies)
    if task_note:
        result.update(note=task_note + " " + POWER_NOTE, context_observed_at=stamp,
                      evidence="metered_power_and_context" if stamp is not None else "metered_power")
        if stamp is not None:
            result["observed_at"] = min(power_stamp, stamp)
    if function:
        source = actual.get("source") if actual.get("function") == function else selected.get("source")
        kind = "native_action" if actual.get("function") == function else selected.get("kind")
        result.update(function=function, label=_TASK_LABELS[function],
                      function_source=source or "native_hvac_action", function_kind=kind or "selected_program")
    return result
