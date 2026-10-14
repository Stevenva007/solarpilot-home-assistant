"""Source-bound heat-pump presentation, never control or learning authority.

Thermal direction and electrical support are different observations. A fresh
assigned feed may support a display inference without making a partial meter
complete or changing the conservative learning/SG classifier.
"""
from __future__ import annotations

import math
import time

from .heatpump_learning import ACTIVE_CONTEXTS

LABELS = {"space_heating": "Verwarmen", "space_cooling": "Koelen",
          "tapwater_heating": "Boiler opwarmen", "sterilization": "Sterilisatie",
          "defrost": "Ontdooien", "normal": "Niet actief",
          "heatpump_unknown": "Taak onbekend"}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def classify_display_operation(snapshot, *, now_wall=None):
    """Interpret one existing snapshot; keep every original expiry intact."""
    p = snapshot if isinstance(snapshot, dict) else {}
    now = time.time() if now_wall is None else now_wall
    stale = _number(p.get("source_stale_s", 120))
    stale = stale if stale is not None and stale > 0 else 120.0
    native = p.get("native_task") if isinstance(p.get("native_task"), dict) else {}
    power = p.get("power_activity") if isinstance(p.get("power_activity"), dict) else {}
    context = p.get("task_context") if isinstance(p.get("task_context"), dict) else {}
    tank = p.get("display_tank") if isinstance(p.get("display_tank"), dict) else {}
    defrost = p.get("defrost") if isinstance(p.get("defrost"), dict) else {}

    def current(stamp, limit=stale):
        stamp, limit = _number(stamp), _number(limit)
        return (stamp is not None and stamp > 0 and limit is not None and limit > 0
                and -5 <= now-stamp <= min(stale, limit))

    def deadline(stamp, limit=stale):
        return _number(stamp) + min(stale, _number(limit))

    threshold = _number(power.get("threshold_w"))
    threshold_valid = threshold is not None and threshold > 0
    raw_rows = power.get("supplies") if isinstance(power.get("supplies"), list) else []
    numbers = [row.get("number") for row in raw_rows if isinstance(row, dict)]
    def consistent(row):
        number = row.get("number")
        value, stamp, valid = (f"power_supply{number}_w", f"power_supply{number}_observed_at", f"power_supply{number}_valid")
        return ((value not in p or _number(p[value]) == _number(row.get("watts")))
                and (stamp not in p or _number(p[stamp]) == _number(row.get("observed_at")))
                and (valid not in p or p[valid] is True))
    rows = [row for row in raw_rows if isinstance(row, dict) and row.get("valid") is True
            and type(row.get("number")) is int and row["number"] in (1, 2) and numbers.count(row["number"]) == 1
            and consistent(row)
            and _number(row.get("watts")) is not None and 0 <= _number(row["watts"]) <= 100000
            and current(row.get("observed_at"), power.get("stale_s", stale))]
    active_rows = [row for row in rows if threshold_valid and _number(row["watts"]) >= threshold]
    main = [row for row in active_rows if row.get("role") == "main"]
    heater = [row for row in rows if row.get("role") == "heater"]
    assigned_heater = [row for row in raw_rows if isinstance(row, dict) and row.get("role") == "heater"]
    support_complete = bool(assigned_heater) and len(heater) == len(assigned_heater)
    heater_active = [row for row in heater if threshold_valid and _number(row["watts"]) >= threshold]
    support_rows = heater_active if heater_active else heater if support_complete else []
    support_pair = (max if heater_active else min)(
        ((deadline(row["observed_at"], power.get("stale_s", stale)), row["observed_at"]) for row in support_rows),
        default=(None, None))
    support = {"active": True if heater_active else False if support_complete and threshold_valid else None,
               "watts": sum(_number(row["watts"]) for row in heater) if support_complete else None,
               "observed_at": support_pair[1], "valid_until": support_pair[0],
               "watts_observed_at": min(row["observed_at"] for row in heater) if support_complete else None,
               "watts_valid_until": min(deadline(row["observed_at"], power.get("stale_s", stale)) for row in heater) if support_complete else None}
    power_stamp = p.get("power_observed_at", p.get("power_stamp"))
    watts = _number(p.get("power_w"))
    complete = (p.get("power_kind") == "measured" and p.get("power_complete") is True
                and p.get("power_scope") in ("total", "split") and watts is not None and 0 <= watts <= 100000
                and current(power_stamp) and len(rows) == len(raw_rows))
    if p.get("power_scope") == "split":
        complete = complete and len(rows) == 2 and {row.get("number") for row in rows} == {1, 2}
        complete = complete and abs(sum(_number(row["watts"]) for row in rows)-watts) <= max(.1, watts*.00001)
    complete_stamps = [power_stamp, *[row["observed_at"] for row in rows]] if complete else []
    complete_until = min([deadline(power_stamp), *[deadline(row["observed_at"], power.get("stale_s", stale)) for row in rows]]) if complete else None
    total_active = complete and threshold_valid and watts >= threshold
    legacy_partial = (p.get("power_kind") == "measured" and not complete and not raw_rows
                      and watts is not None and threshold_valid and threshold <= watts <= 100000 and current(power_stamp))
    activity_stamps = [row["observed_at"] for row in active_rows]
    activity_deadlines = [deadline(row["observed_at"], power.get("stale_s", stale)) for row in active_rows]
    if total_active:
        activity_stamps.append(min(complete_stamps))
        activity_deadlines.append(complete_until)
    elif legacy_partial:
        activity_stamps.append(power_stamp)
        activity_deadlines.append(deadline(power_stamp))
    frequency = _number(p.get("compressor_frequency_hz"))
    frequency_stamp = p.get("compressor_frequency_observed_at", p.get("compressor_stamp"))
    if (isinstance(p.get("compressor_entity"), str) and p["compressor_entity"].startswith("sensor.")
            and frequency is not None and 0 < frequency <= 200 and current(frequency_stamp)):
        activity_stamps.append(frequency_stamp)
        activity_deadlines.append(deadline(frequency_stamp))
    active = True if activity_stamps else False if complete and threshold_valid else None
    activity_pair = max(zip(activity_deadlines, activity_stamps), default=(None, None))
    result = {"context": "heatpump_unknown", "function": None, "tier": "unknown",
              "label": "Actief · taak onbekend" if active else "Taak onbekend",
              "source": "none", "kind": "none", "observed_at": None, "valid_until": None,
              "stale_s": stale, "active": active,
              "activity_observed_at": activity_pair[1],
              "activity_valid_until": activity_pair[0],
              "support": support, "reason": "Actuele taak niet eenduidig vastgesteld",
              "model_eligible": False, "read_only": True}

    def resolved(function, tier, source, kind, stamps, limits=None, reason=""):
        limits = limits or [stale] * len(stamps)
        original = min(stamps)
        until = min(deadline(stamp, limit) for stamp, limit in zip(stamps, limits))
        activity_until, activity_stamp = max((until, original), activity_pair if activity_pair[0] is not None else (until, original))
        return {**result, "context": function, "function": function, "tier": tier,
                "label": LABELS[function], "source": source, "kind": kind,
                "observed_at": original, "valid_until": until, "active": True,
                "activity_observed_at": activity_stamp, "activity_valid_until": activity_until,
                "reason": reason}

    if (defrost.get("state") == "active" and defrost.get("source") in ("aquarea_entity", "aquarea_poll")
            and current(defrost.get("observed_at"), defrost.get("stale_s", stale))):
        return resolved("defrost", "confirmed", defrost["source"], "native_action",
                        [defrost["observed_at"]], [defrost.get("stale_s", stale)], "Panasonic meldt ontdooien")
    native_fresh = current(native.get("observed_at"), native.get("stale_s", stale))
    if native_fresh and native.get("conflict") is True:
        return {**result, "reason": "Tegenstrijdige actuele Panasonic-taakmeldingen"}
    if (native_fresh and native.get("function") in ACTIVE_CONTEXTS
            and native.get("source") in ("aquarea_poll", "native_hvac_action")
            and native.get("inactive") is not True and native.get("verified_global_off") is not True):
        return resolved(native["function"], "confirmed", native["source"], "native_action",
                        [native["observed_at"]], [native.get("stale_s", stale)], "Verse Panasonic-bedrijfsactie")

    global_off = (native_fresh and native.get("source") == "aquarea_poll"
                  and native.get("verified_global_off") is True and native.get("inactive") is True
                  and native.get("inactive_action") == "off" and native.get("inactive_scope") == "global"
                  and native.get("function") is None and native.get("independent_tank_on", False) is False)
    if global_off:
        if active:
            return {**result, "reason": "Panasonic meldt uit; gemeten elektrische activiteit heeft geen bevestigde taak"}
        return {**result, "context": "normal", "tier": "inactive", "label": "Niet actief",
                "source": "aquarea_poll", "kind": "native_action", "active": False,
                "observed_at": native["observed_at"], "valid_until": deadline(native["observed_at"], native.get("stale_s", stale)),
                "activity_observed_at": native["observed_at"], "activity_valid_until": deadline(native["observed_at"], native.get("stale_s", stale)),
                "reason": "Verse geverifieerde globale UIT-melding"}

    scoped_tank = (native_fresh and native.get("source") == "aquarea_poll"
                   and native.get("inactive") is True and native.get("function") is None
                   and native.get("inactive_action") == "off" and native.get("inactive_scope") == "space_circuit"
                   and native.get("independent_tank_on") is True and native.get("verified_global_off") is not True)
    native_veto = (native_fresh and native.get("inactive") is True
                   and native.get("inactive_action") != "idle" and not scoped_tank)
    context_fresh = current(context.get("observed_at"), context.get("stale_s", stale))
    route = (context_fresh and context.get("kind") == "tank_route" and context.get("source") == "aquarea_entity"
             and context.get("function") == "tapwater_heating")
    if not native_veto and route and (main or heater_active):
        feeds = main or heater_active
        stamps = [context["observed_at"], *[row["observed_at"] for row in feeds]]
        limits = [context.get("stale_s", stale), *[power.get("stale_s", stale)] * len(feeds)]
        if scoped_tank:
            stamps.append(native["observed_at"])
            limits.append(native.get("stale_s", stale))
        return resolved("tapwater_heating", "derived", "aquarea_entity", "tank_route", stamps, limits,
                        "Afgeleid uit de actuele Panasonic-tankroute en de afzonderlijk gemeten actieve voeding")

    # A selected space programme does not exclude tank operation. Require
    # fresh explicit tank inactivity before assigning a display direction.
    tank_fresh = tank.get("available") is True and current(tank.get("observed_at"))
    tank_mode = str(tank.get("mode", "")).strip().casefold()
    tank_action = str(tank.get("action", "")).strip().casefold()
    tank_idle = tank_fresh and (tank_mode in ("idle", "off", "inactive") or tank_action in ("idle", "off", "inactive"))
    tank_idle = tank_idle and tank_mode not in ("heating", "heat_pump") and tank_action not in ("heating", "dhw", "hot_water")
    selected = (context_fresh and context.get("kind") == "selected_program"
                and context.get("source") in ("native_program", "native_mode")
                and context.get("function") in ("space_heating", "space_cooling"))
    if not native_veto and not scoped_tank and selected and main and tank_idle:
        return resolved(context["function"], "derived", context["source"], "selected_program",
                        [context["observed_at"], tank["observed_at"], *[row["observed_at"] for row in main]],
                        [context.get("stale_s", stale), stale, *[power.get("stale_s", stale)] * len(main)],
                        "Afgeleid uit actieve hoofdvoeding, gekozen Panasonic-stand en actuele tankrust")
    # Only the independently checked complete reading can establish electrical
    # inactivity here. A cached classifier cannot bypass invalid split feeds.
    if active is False:
        stamp = min(complete_stamps)
        return {**result, "context": "normal", "tier": "inactive", "label": "Basisverbruik" if complete and watts else "Niet actief",
                "active": False, "source": "metered_power",
                "kind": "electrical_activity", "observed_at": stamp,
                "valid_until": complete_until,
                "activity_observed_at": stamp, "activity_valid_until": complete_until}
    return result
