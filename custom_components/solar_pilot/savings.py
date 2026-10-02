"""Qualified, forward-only value accounting; never a control decision.

Solar energy used by an automatically controlled consumer has an opportunity
value relative to buying that energy and exporting the solar energy instead.
That comparison is not a measured counterfactual without SolarPilot. In
particular, native EV charging, warm-water control and climate control are not
included in this consumer ledger, and their savings must not be invented.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import math


def _finite(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _day(value):
    try:
        parsed = date.fromisoformat(value) if isinstance(value, str) else None
        return value if parsed is not None and parsed.isoformat() == value else None
    except (ValueError, TypeError):
        return None


def _nonnegative(value):
    number = _finite(value)
    return max(0.0, number) if number is not None else None


def _managed_record(stats, economy_enabled=None, power_estimated=None):
    if not isinstance(stats, dict) or not _day(stats.get("date")):
        return None
    return {
        "date": stats["date"],
        "solar_kwh": _nonnegative(stats.get("managed_solar_kwh")),
        "managed_kwh": _nonnegative(stats.get("managed_kwh")),
        "estimated_value_eur": _finite(stats.get("estimated_value_eur")),
        "coverage_s": _nonnegative(stats.get("samples_s")) or 0.0,
        # Legacy daily accounting did not record tariff/meter quality per
        # interval. Current quality must not be presented as historical proof.
        "economy_enabled_at_capture": economy_enabled if isinstance(economy_enabled, bool) else None,
        "power_estimated_at_capture": power_estimated if isinstance(power_estimated, bool) else None,
        "automatic_only": False,
    }


_AUTO_COUNTERS = (
    "managed_kwh", "solar_kwh", "grid_kwh", "battery_kwh", "unattributed_kwh",
    "estimated_value_eur", "coverage_s", "solar_coverage_s", "priced_s",
    "estimated_power_s", "unknown_power_s",
)


class SavingsHistory:
    """Retain at most 90 real daily records, with no historical backfill.

``capture`` archives existing daily EMS totals without changing/repricing
them. ``record_automatic_interval`` is a separate, forward-only subset. Its
caller must supply only genuinely automatically controlled, owned and active
consumer watts, excluding manual/boost operation. The methods have no access
to Home Assistant, services, devices, tariffs, clocks or network resources.
    """

    def __init__(self, retention_days=90):
        self.retention_days = max(1, min(90, int(retention_days)))
        self.records = {}

    def _prune(self):
        for day in sorted(self.records)[:-self.retention_days]:
            del self.records[day]

    def capture(self, stats, *, economy_enabled=None, power_estimated=None):
        managed = _managed_record(stats, economy_enabled, power_estimated)
        if managed is None:
            return False
        record = self.records.setdefault(managed["date"], {"date": managed["date"]})
        record["managed_reference"] = managed
        self._prune()
        return True

    def record_automatic_interval(self, *, day, dt_s, grid_w, pv_w, automatic_w,
                                  battery_discharge_w=0.0, import_price_eur_kwh=None,
                                  export_price_eur_kwh=None, power_estimated=None,
                                  timestamp=None, max_gap_s=120):
        day, dt, grid, managed = _day(day), _finite(dt_s), _finite(grid_w), _nonnegative(automatic_w)
        stamp = _finite(timestamp)
        gap = _finite(max_gap_s)
        if day is None or dt is None or gap is None or not 0 < dt <= min(120, gap) or grid is None or managed is None:
            return False
        record = self.records.setdefault(day, {"date": day})
        previous = record.get("automatic")
        if (previous and stamp is not None and previous.get("last_sample") is not None
                and stamp <= previous["last_sample"]):
            return False
        automatic = record.setdefault("automatic", {**{key: 0.0 for key in _AUTO_COUNTERS},
                                                    "first_sample": None, "last_sample": None})
        factor = dt / 3_600_000.0
        import_w, export_w = max(0.0, grid), max(0.0, -grid)
        grid_part = min(managed, import_w)
        automatic["managed_kwh"] += managed * factor
        automatic["grid_kwh"] += grid_part * factor
        automatic["coverage_s"] += dt
        if managed > 0:
            if power_estimated is True:
                automatic["estimated_power_s"] += dt
            elif power_estimated is not False:
                automatic["unknown_power_s"] += dt
        pv, battery = _finite(pv_w), _finite(battery_discharge_w)
        if pv is not None and pv >= 0 and battery is not None and battery >= 0:
            battery_part = min(max(0.0, managed - grid_part), battery)
            # Never call estimated consumer watts solar if actual production
            # cannot supply them. Export and battery discharge are not savings.
            solar = min(max(0.0, managed - grid_part - battery_part), max(0.0, pv - export_w))
            automatic["battery_kwh"] += battery_part * factor
            automatic["solar_kwh"] += solar * factor
            automatic["unattributed_kwh"] += max(0.0, managed - grid_part - battery_part - solar) * factor
            automatic["solar_coverage_s"] += dt
            buy, sell = _finite(import_price_eur_kwh), _finite(export_price_eur_kwh)
            if buy is not None and sell is not None:
                # Preserve the actual interval spread, including negative
                # tariffs. Never revalue past energy at a current tariff.
                automatic["estimated_value_eur"] += solar * factor * (buy - sell)
                automatic["priced_s"] += dt
        else:
            automatic["unattributed_kwh"] += max(0.0, managed - grid_part) * factor
        if stamp is not None:
            if automatic["first_sample"] is None:
                automatic["first_sample"] = stamp - dt
            automatic["last_sample"] = stamp
        self._prune()
        return True

    def snapshot(self):
        return {"version": 1, "records": deepcopy([self.records[day] for day in sorted(self.records)])}

    def restore(self, payload):
        self.records = {}
        rows = payload.get("records") if isinstance(payload, dict) and payload.get("version") == 1 else None
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict) or not _day(row.get("date")):
                continue
            day = row["date"]
            clean = {"date": day}
            managed = row.get("managed_reference")
            if isinstance(managed, dict):
                clean["managed_reference"] = {
                    "date": day, "solar_kwh": _nonnegative(managed.get("solar_kwh")),
                    "managed_kwh": _nonnegative(managed.get("managed_kwh")),
                    "estimated_value_eur": _finite(managed.get("estimated_value_eur")),
                    "coverage_s": _nonnegative(managed.get("coverage_s")) or 0.0,
                    "economy_enabled_at_capture": managed.get("economy_enabled_at_capture") if isinstance(managed.get("economy_enabled_at_capture"), bool) else None,
                    "power_estimated_at_capture": managed.get("power_estimated_at_capture") if isinstance(managed.get("power_estimated_at_capture"), bool) else None,
                    "automatic_only": False,
                }
            automatic = row.get("automatic")
            if isinstance(automatic, dict):
                clean["automatic"] = {key: (_finite(automatic.get(key)) or 0.0) if key == "estimated_value_eur"
                                      else (_nonnegative(automatic.get(key)) or 0.0) for key in _AUTO_COUNTERS}
                for key in ("first_sample", "last_sample"):
                    clean["automatic"][key] = _finite(automatic.get(key))
                auto = clean["automatic"]
                auto["solar_coverage_s"] = min(auto["solar_coverage_s"], auto["coverage_s"])
                auto["priced_s"] = min(auto["priced_s"], auto["solar_coverage_s"])
                auto["solar_kwh"] = min(auto["solar_kwh"], auto["managed_kwh"])
                if _finite(automatic.get("estimated_value_eur")) is None:
                    auto["priced_s"] = 0.0
            if len(clean) > 1:
                self.records[day] = clean  # Duplicate dates replace, never double-count.
        self._prune()

    def report(self, stats=None, **kwargs):
        return build_savings_report(stats, history=self, **kwargs)


def _summary(rows, key):
    selected = [(row["date"], row[key]) for row in rows if isinstance(row.get(key), dict)]
    has_samples = [(day, value) for day, value in selected if (_finite(value.get("coverage_s")) or 0) > 0]
    solar = sum(_nonnegative(value.get("solar_kwh")) or 0.0 for _, value in has_samples)
    coverage = sum(_nonnegative(value.get("coverage_s")) or 0.0 for _, value in has_samples)
    if key == "automatic":
        priced = sum(_nonnegative(value.get("priced_s")) or 0.0 for _, value in has_samples)
        solar_coverage = sum(_nonnegative(value.get("solar_coverage_s")) or 0.0 for _, value in has_samples)
        known = [(day, value) for day, value in has_samples if (_finite(value.get("priced_s")) or 0) > 0]
        value_partial = solar_coverage > priced + .01 or coverage > solar_coverage + .01
        power_estimated = any((_finite(value.get("estimated_power_s")) or 0) > 0 for _, value in has_samples)
        power_unknown = any((_finite(value.get("unknown_power_s")) or 0) > 0 for _, value in has_samples)
        solar_known = solar_coverage > 0
    else:
        # Captured legacy counters are retained as a distinct broad reference;
        # missing/disabled prices are never displayed as free energy.
        known = [(day, value) for day, value in has_samples
                 if value.get("economy_enabled_at_capture") is not False
                 and _finite(value.get("estimated_value_eur")) is not None]
        priced, solar_coverage, value_partial = None, None, True
        power_estimated, power_unknown = None, True
        solar_known = any(_finite(value.get("solar_kwh")) is not None for _, value in has_samples)
    total = sum(_finite(value.get("estimated_value_eur")) or 0.0 for _, value in known)
    return {
        "available": bool(known), "estimated_benefit_eur": round(total, 6) if known else None,
        "solar_kwh": round(solar, 6) if solar_known else None,
        "start_date": min((day for day, _ in has_samples), default=None),
        "end_date": max((day for day, _ in has_samples), default=None),
        "recorded_days": len(has_samples), "priced_days": len(known),
        "coverage_s": round(coverage, 1), "priced_s": round(priced, 1) if priced is not None else None,
        "solar_coverage_s": round(solar_coverage, 1) if solar_coverage is not None else None,
        "partial": True, "value_partial": value_partial,
        "power_estimated": power_estimated, "power_quality_unknown": power_unknown,
        "status": "estimated" if known else "not_recorded",
        "automatic_only": key == "automatic",
        "note": ("Alleen bijgehouden meetperioden; ontbrekende perioden zijn niet aangevuld."
                 if key == "automatic" else
                 "Ruimere bestaande telling, ook met handmatige regeling; geen apart bewijs voor automatische besparing."),
    }


def build_savings_report(stats=None, *, history=None, economy_enabled=None,
                         power_estimated=None, current_date=None):
    """Return an immutable presentation of recorded estimates, not real savings.

No price or energy is reconstructed. Existing day counters remain a separate
managed-load reference, never migrated into the new automatic-only subtotal.
    """
    rows = deepcopy(list(history.records.values())) if isinstance(history, SavingsHistory) else []
    managed = _managed_record(stats, economy_enabled, power_estimated)
    today = _day(current_date) or (managed["date"] if managed else None)
    if managed is not None:
        current = next((row for row in rows if row["date"] == managed["date"]), None)
        if current is None:
            current = {"date": managed["date"]}
            rows.append(current)
        current["managed_reference"] = managed
    if today:
        rows = [row for row in rows if row["date"] <= today]
    today_rows = [row for row in rows if row["date"] == today]
    return {
        "title": "Geschat voordeel van automatisch gestuurd zonverbruik",
        "today": {"date": today, **_summary(today_rows, "automatic")},
        "available_period": _summary(rows, "automatic"),
        "managed_reference": {
            "title": "Geschatte waarde van geregeld zonverbruik",
            "today": {"date": today, **_summary(today_rows, "managed_reference")},
            "available_period": _summary(rows, "managed_reference"),
        },
        "proven_savings_eur": None, "baseline_available": False,
        "method": "solar_vs_grid_opportunity_value",
        "formula": "Bijgehouden zonnestroom × (afnameprijs − injectievergoeding), per meetinterval.",
        "comparison": "Vergeleken met dezelfde energie van het net afnemen en de zonnestroom terugleveren.",
        "not_proven": "Geen gemeten vergelijking met een woning zonder SolarPilot; extra besparing is niet bewezen.",
        "included": "Alleen verbruikers die SolarPilot in Auto zelf heeft ingeschakeld; geen handmatige start of boost.",
        "excluded": ["Autonoom Wallbox-laden", "Boilerregeling", "Verwarming en koeling",
                     "Vaste elektriciteitskosten", "Capaciteitstarief"],
        "cost_note": "Dit voordeel is al verwerkt in lagere netafname; niet nogmaals van de elektriciteitskost aftrekken.",
        "history_note": "Alleen bewaarde dagen, maximaal 90; geen reconstructie vóór de start van deze telling.",
    }
