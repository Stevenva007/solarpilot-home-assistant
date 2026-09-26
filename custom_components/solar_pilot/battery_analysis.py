"""Continuous local what-if battery simulator.

This module never controls a battery. It replays the actually observed site
import/export through virtual batteries so the user can see how much energy a
battery could have shifted under simple self-consumption rules. Results are
technical what-if estimates, not a financial recommendation.
"""
from __future__ import annotations
import math

BATTERY_ANALYSIS_DEFAULTS = {
    "enabled": True,
    "seed_enabled": True,
    "roundtrip_efficiency": 0.90,
    "reserve_pct": 0.0,
    "capacities_kwh": [5.0, 10.0, 15.0, 20.0],
    "powers_kw": [3.0, 5.0, 10.0],
    "max_dt_s": 120.0,
}


def _finite(v):
    try:
        v = float(v)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _scenario_key(capacity_kwh, power_kw):
    return f"{float(capacity_kwh):g}kWh_{float(power_kw):g}kW"


class BatteryOpportunitySimulator:
    def __init__(self, settings=None, seed=None):
        self.settings = {**BATTERY_ANALYSIS_DEFAULTS, **(settings or {})}
        self.seed = seed or {}
        self.scenarios = {}
        self.live_seconds = 0.0
        self.live_import_kwh = 0.0
        self.live_export_kwh = 0.0
        self._build_scenarios()

    def _build_scenarios(self):
        old = self.scenarios
        self.scenarios = {}
        seed_rows = {}
        if self.settings.get("seed_enabled", True):
            for row in self.seed.get("battery_upper_bound", {}).get("scenarios", []):
                try:
                    seed_rows[_scenario_key(row["capacity_kwh"], row["power_kw"])] = row
                except (KeyError, TypeError, ValueError):
                    continue
        for capacity in self.settings.get("capacities_kwh", []) or []:
            for power in self.settings.get("powers_kw", []) or []:
                c = _finite(capacity)
                p = _finite(power)
                if c is None or p is None or c <= 0 or p <= 0:
                    continue
                key = _scenario_key(c, p)
                prior = old.get(key, {})
                seed = seed_rows.get(key, {})
                self.scenarios[key] = {
                    "capacity_kwh": c,
                    "power_kw": p,
                    "soc_kwh": min(c, max(0.0, float(prior.get("soc_kwh", 0) or 0))),
                    "live_avoided_import_kwh": max(0.0, float(prior.get("live_avoided_import_kwh", 0) or 0)),
                    "live_used_export_kwh": max(0.0, float(prior.get("live_used_export_kwh", 0) or 0)),
                    "historical_avoided_import_kwh": max(0.0, float(seed.get("avoided_import_kwh", 0) or 0)),
                    "historical_used_export_kwh": max(0.0, float(seed.get("used_export_kwh", 0) or 0)),
                }

    def update_settings(self, settings):
        self.settings = {**BATTERY_ANALYSIS_DEFAULTS, **(settings or {})}
        self._build_scenarios()

    def reset_live(self):
        for row in self.scenarios.values():
            row["soc_kwh"] = 0.0
            row["live_avoided_import_kwh"] = 0.0
            row["live_used_export_kwh"] = 0.0
        self.live_seconds = 0.0
        self.live_import_kwh = 0.0
        self.live_export_kwh = 0.0

    def snapshot(self):
        return {
            "scenarios": {key: {
                "soc_kwh": row["soc_kwh"],
                "live_avoided_import_kwh": row["live_avoided_import_kwh"],
                "live_used_export_kwh": row["live_used_export_kwh"],
            } for key, row in self.scenarios.items()},
            "live_seconds": self.live_seconds,
            "live_import_kwh": self.live_import_kwh,
            "live_export_kwh": self.live_export_kwh,
        }

    def restore(self, data):
        if not isinstance(data, dict):
            return
        for key, state in data.get("scenarios", {}).items():
            if key not in self.scenarios or not isinstance(state, dict):
                continue
            row = self.scenarios[key]
            row["soc_kwh"] = min(row["capacity_kwh"], max(0.0, float(state.get("soc_kwh", 0) or 0)))
            row["live_avoided_import_kwh"] = max(0.0, float(state.get("live_avoided_import_kwh", 0) or 0))
            row["live_used_export_kwh"] = max(0.0, float(state.get("live_used_export_kwh", 0) or 0))
        self.live_seconds = max(0.0, float(data.get("live_seconds", 0) or 0))
        self.live_import_kwh = max(0.0, float(data.get("live_import_kwh", 0) or 0))
        self.live_export_kwh = max(0.0, float(data.get("live_export_kwh", 0) or 0))

    def step(self, dt_s, grid_w):
        if not self.settings.get("enabled", True):
            return
        dt = _finite(dt_s); grid = _finite(grid_w)
        if dt is None or grid is None or not 0 < dt <= float(self.settings.get("max_dt_s", 120)):
            return
        hours = dt / 3600.0
        import_kwh = max(0.0, grid) / 1000 * hours
        export_kwh = max(0.0, -grid) / 1000 * hours
        self.live_seconds += dt
        self.live_import_kwh += import_kwh
        self.live_export_kwh += export_kwh
        rte = max(0.50, min(1.0, float(self.settings["roundtrip_efficiency"])))
        eta = math.sqrt(rte)
        reserve = max(0.0, min(0.9, float(self.settings.get("reserve_pct", 0)) / 100.0))
        for row in self.scenarios.values():
            cap = row["capacity_kwh"]
            p_limit_kwh = row["power_kw"] * hours
            minimum_soc = cap * reserve
            available_capacity_ac = max(0.0, (cap - row["soc_kwh"]) / eta)
            charge_ac = min(export_kwh, p_limit_kwh, available_capacity_ac)
            row["soc_kwh"] += charge_ac * eta
            row["live_used_export_kwh"] += charge_ac
            usable_soc = max(0.0, row["soc_kwh"] - minimum_soc)
            discharge_ac = min(import_kwh, p_limit_kwh, usable_soc * eta)
            row["soc_kwh"] -= discharge_ac / eta
            row["live_avoided_import_kwh"] += discharge_ac

    def overview(self, import_price=0.0, export_price=0.0, existing_battery=False):
        imp = _finite(import_price) or 0.0
        exp = _finite(export_price) or 0.0
        scenarios = []
        for key, row in sorted(self.scenarios.items(), key=lambda kv: (kv[1]["power_kw"], kv[1]["capacity_kwh"])):
            avoided = row["historical_avoided_import_kwh"] + row["live_avoided_import_kwh"]
            used_export = row["historical_used_export_kwh"] + row["live_used_export_kwh"]
            value = avoided * imp - used_export * exp
            scenarios.append({
                "id": key, "capacity_kwh": row["capacity_kwh"], "power_kw": row["power_kw"],
                "soc_kwh_virtual": round(row["soc_kwh"], 3),
                "avoided_import_kwh": round(avoided, 1), "used_export_kwh": round(used_export, 1),
                "historical_avoided_import_kwh": round(row["historical_avoided_import_kwh"], 1),
                "historical_used_export_kwh": round(row["historical_used_export_kwh"], 1),
                "live_avoided_import_kwh": round(row["live_avoided_import_kwh"], 3),
                "live_used_export_kwh": round(row["live_used_export_kwh"], 3),
                "indicative_energy_value_eur": round(value, 2),
            })
        ref = sorted((x for x in scenarios if abs(x["power_kw"] - 5.0) < 1e-6), key=lambda x: x["capacity_kwh"])
        increments, previous = [], None
        for row in ref:
            delta = row["avoided_import_kwh"] if previous is None else row["avoided_import_kwh"] - previous["avoided_import_kwh"]
            increments.append({"capacity_kwh": row["capacity_kwh"], "incremental_avoided_import_kwh": round(delta, 1)})
            previous = row
        source = self.seed.get("source", {})
        return {
            "enabled": bool(self.settings.get("enabled", True)), "advisory_only": True,
            "existing_battery_detected": bool(existing_battery),
            "roundtrip_efficiency": float(self.settings["roundtrip_efficiency"]),
            "reserve_pct": float(self.settings.get("reserve_pct", 0)),
            "seed_period": {"start": source.get("homewizard_start"), "end": source.get("homewizard_end"),
                            "days": self.seed.get("grid", {}).get("period_days"),
                            "note": "Vooral lente/zomer; geen volledig jaar en dus geen definitieve ROI-basis."},
            "live_days": round(self.live_seconds / 86400, 2),
            "live_import_kwh": round(self.live_import_kwh, 3), "live_export_kwh": round(self.live_export_kwh, 3),
            "scenarios": scenarios, "capacity_increment_5kw": increments,
            "note": ("Bestaande batterij gedetecteerd: de simulatie beschrijft alleen een extra batterij bovenop het actuele netprofiel."
                     if existing_battery else "What-if op werkelijk gemeten import/export. Geen batterijbediening, degradatie-, financierings- of wintergarantie."),
        }
