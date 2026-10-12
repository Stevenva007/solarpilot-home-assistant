"""Chronologically feasible battery what-if advice, with no device control.

Powers are AC-side watts. Stored energy is kWh inside the battery; each leg
uses the square root of round-trip efficiency. This is a chronological
self-consumption/median-price heuristic, not a global economic optimum.
"""
from __future__ import annotations

from collections.abc import Mapping
import math
import statistics


def _finite(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def plan_battery(slots, settings, slot_h, battery):
    """Set only ``slot.battery_w`` and return auditable advisory metadata.

``available_kwh`` is the legacy *capacity* field, not energy available to
discharge. Explicit separate power limits take precedence over ``power_w``.
Unknown PV hours stay idle. Initial SOC outside the configured operating
envelope is preserved, provided it remains within physical capacity.
"""
    slots = list(slots or [])
    settings = settings if isinstance(settings, Mapping) else {}
    for slot in slots:
        slot.battery_w = 0.0
    result = {
        "enabled": bool(settings.get("battery_advisory", True)),
        "advisory_only": True,
        "strategy": "chronological_self_consumption_median_price",
        "globally_optimal": False,
        "status": "unavailable",
        "warnings": [],
        "soc_trajectory": [],
        "charge_ac_kwh": 0.0,
        "discharge_ac_kwh": 0.0,
        "loss_kwh": 0.0,
        "note": "Batterijadvies; geen fysieke setpoints. SOC is een voorspeld scenario, geen meting.",
    }
    if not result["enabled"]:
        result["status"] = "disabled"
        return result
    if not slots:
        result["status"] = "no_slots"
        return result
    if not isinstance(battery, Mapping) or not battery:
        return result

    def invalid(message):
        result["status"] = "invalid_input"
        result["warnings"].append(message)
        return result

    duration = _finite(slot_h)
    capacity = _finite(battery.get("capacity_kwh", battery.get("available_kwh")))
    soc_pct = _finite(battery.get("soc_pct"))
    min_pct = _finite(battery.get("min_soc_pct", 20))
    max_pct = _finite(battery.get("max_soc_pct", 95))
    charge_power = _finite(battery.get("charge_power_w", battery.get("power_w")))
    discharge_power = _finite(battery.get("discharge_power_w", battery.get("power_w")))
    efficiency = _finite(battery.get("round_trip_efficiency", 0.9))
    reserve = _finite(settings.get("pv_reserve_w", 150))
    if duration is None or duration <= 0:
        return invalid("Batterijadvies ontbreekt: ongeldige slotduur.")
    if capacity is None or capacity <= 0:
        return invalid("Batterijadvies ontbreekt: bruikbare batterijcapaciteit ontbreekt.")
    if soc_pct is None or not 0 <= soc_pct <= 100:
        return invalid("Batterijadvies ontbreekt: geldige gemeten begin-SOC ontbreekt.")
    if min_pct is None or max_pct is None or not 0 <= min_pct <= max_pct <= 100:
        return invalid("Batterijadvies ontbreekt: ongeldige SOC-grenzen.")
    if charge_power is None or discharge_power is None or charge_power < 0 or discharge_power < 0:
        return invalid("Batterijadvies ontbreekt: geldige laad-/ontlaadlimieten ontbreken.")
    if efficiency is None or not 0 < efficiency <= 1:
        return invalid("Batterijadvies ontbreekt: ongeldige rondrendementwaarde.")
    if reserve is None or reserve < 0:
        return invalid("Batterijadvies ontbreekt: ongeldige PV-reserve.")

    # Validate the complete horizon before planning, so malformed data never
    # leaves a partially populated, apparently valid battery plan behind.
    price_on = bool(settings.get("price_optimisation", True))
    rows = []
    previous_start = None
    for slot in slots:
        base = _finite(getattr(slot, "base_w", None))
        load = _finite(getattr(slot, "planned_load_w", 0))
        known = bool(getattr(slot, "pv_available", True))
        pv = _finite(getattr(slot, "pv_w", None)) if known else 0.0
        price = _finite(getattr(slot, "import_price", None))
        if base is None or load is None or base < 0 or load < 0 or pv is None or pv < 0:
            return invalid("Batterijadvies ontbreekt: ongeldige PV- of lastgegevens.")
        if price_on and price is None:
            return invalid("Batterijadvies ontbreekt: ongeldige importprijs.")
        start = getattr(slot, "start", None)
        try:
            timestamp = start.timestamp()
            start_text = start.isoformat()
        except (AttributeError, ValueError, OverflowError, OSError):
            return invalid("Batterijadvies ontbreekt: ongeldige slottijd.")
        if not math.isfinite(timestamp) or (previous_start is not None and
                timestamp - previous_start < duration * 3600 - 1e-6):
            return invalid("Batterijadvies ontbreekt: slots overlappen of staan niet in chronologische volgorde.")
        net = base + load - pv
        if not math.isfinite(net):
            return invalid("Batterijadvies ontbreekt: ongeldige netto-last.")
        previous_start = timestamp
        rows.append((slot, net, known, price, start_text))

    leg_efficiency = math.sqrt(efficiency)
    energy = capacity * (soc_pct / 100)
    minimum = capacity * (min_pct / 100)
    maximum = capacity * (max_pct / 100)
    prices = [row[3] for row in rows if row[2] and row[3] is not None]
    threshold = statistics.median(prices) if price_on and prices else None
    result.update({
        "status": "planned",
        "capacity_kwh": capacity,
        "initial_soc_kwh": energy,
        "initial_soc_pct": soc_pct,
        "min_soc_kwh": minimum,
        "max_soc_kwh": maximum,
        "charge_power_w": charge_power,
        "discharge_power_w": discharge_power,
        "round_trip_efficiency": efficiency,
        "charge_efficiency": leg_efficiency,
        "discharge_efficiency": leg_efficiency,
        "discharge_price_threshold": threshold,
        "missing_pv_slots": sum(not row[2] for row in rows),
    })
    if not min_pct <= soc_pct <= max_pct:
        result["warnings"].append("Begin-SOC ligt buiten de ingestelde grenzen; gemeten energie blijft behouden.")
    if battery.get("aggregate_count", 1) > 1:
        result["warnings"].append("Batterijadvies gebruikt een geaggregeerd scenario; individuele batterijverdeling is niet gesimuleerd.")
    if result["missing_pv_slots"]:
        result["warnings"].append("Batterijadvies blijft stil in slots zonder PV-voorspelling; de SOC daarna is voorwaardelijk.")

    # One forward pass is essential: charging in a later slot cannot fund a
    # discharge in an earlier one. Charge/discharge are exclusive branches.
    for index, (slot, net, known, price, start_text) in enumerate(rows):
        start_energy = energy
        charge_ac = discharge_ac = loss = 0.0
        reason = "idle"
        if not known:
            reason = "missing_pv_forecast"
        elif net < -reserve and energy < maximum:
            charge_w = min(charge_power, -net - reserve,
                           (maximum - energy) / leg_efficiency / duration * 1000)
            charge_ac = charge_w * duration / 1000
            energy += charge_ac * leg_efficiency
            loss = charge_ac * (1 - leg_efficiency)
            slot.battery_w = charge_w
            reason = "pv_charge" if charge_w > 0 else "charge_limit"
        elif net > 0 and energy > minimum:
            if not price_on or (threshold is not None and price >= threshold):
                discharge_w = min(discharge_power, net,
                                  (energy - minimum) * leg_efficiency / duration * 1000)
                discharge_ac = discharge_w * duration / 1000
                energy -= discharge_ac / leg_efficiency
                loss = discharge_ac * (1 / leg_efficiency - 1)
                slot.battery_w = -discharge_w
                reason = "deficit_discharge" if discharge_w > 0 else "discharge_limit"
            else:
                reason = "price_below_threshold"
        result["charge_ac_kwh"] += charge_ac
        result["discharge_ac_kwh"] += discharge_ac
        result["loss_kwh"] += loss
        result["soc_trajectory"].append({
            "slot_index": index,
            "start": start_text,
            "pv_available": known,
            "battery_w": slot.battery_w,
            "soc_start_kwh": start_energy,
            "soc_end_kwh": energy,
            "soc_end_pct": energy / capacity * 100,
            "charge_ac_kwh": charge_ac,
            "discharge_ac_kwh": discharge_ac,
            "loss_kwh": loss,
            "reason": reason,
        })
    result["final_soc_kwh"] = energy
    result["final_soc_pct"] = energy / capacity * 100
    return result
