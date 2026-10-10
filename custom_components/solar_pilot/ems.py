"""EMS-wide planning, accounting and protection policies.

Pure calculations only: no Home Assistant service calls.  The runtime decides
when these advisory/protection results may influence deterministic control.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import math

CAPACITY_DEFAULTS = {
    "enabled": False,
    "average_demand_entity": "",
    "monthly_peak_entity": "",
    "target_peak_w": 3500.0,
    "adaptive_to_month_peak": True,
    # In Flanders the billed capacity has a 2.5 kW floor.  Keeping this explicit
    # avoids pointless peak shaving below the tariff floor unless the user has
    # another technical reason and disables this guard.
    "respect_billing_floor": True,
    "billing_floor_w": 2500.0,
    "margin_w": 100.0,
    "minimum_elapsed_s": 60,
    "stale_s": 120,
}

ECONOMY_DEFAULTS = {
    "enabled": False,
    "import_price_entity": "",
    "export_price_entity": "",
    "fixed_import_eur_kwh": 0.30,
    "fixed_export_eur_kwh": 0.03,
}

FORECAST_DEFAULTS = {
    "enabled": False,
    "current_hour_entity": "",
    "next_hour_entity": "",
    "remaining_today_entity": "",
    "tomorrow_entity": "",
    "stale_s": 7200,
}

PLANNER_DEFAULTS = {
    "enabled": True,
    "forecast_deferral_enabled": True,
    "forecast_gain_kwh": 0.50,
    "forecast_sufficiency_factor": 1.25,
    "max_deferral_s": 3600,
    "deadline_guard_s": 600,
    "early_grid_enabled": False,
    "cheap_grid_limit_eur_kwh": 0.15,
    "early_grid_requires_forecast_shortfall": True,
    # Learning may only make a configured on/off load *more conservative* by
    # raising its planning estimate to an observed P90.  It never lowers it.
    "adaptive_power_guard": True,
    "adaptive_power_min_samples": 10,
    "adaptive_power_max_multiplier": 2.0,
}

PHASE_DEFAULTS = {
    "enabled": False,
    "phase_1_entity": "",
    "phase_2_entity": "",
    "phase_3_entity": "",
    "limit_w": 7000.0,
    "margin_w": 300.0,
    "start_headroom_w": 500.0,
    "stale_s": 120,
    # Advisory by default.  Users must explicitly enable control because SolarPilot
    # does not know a load's phase distribution yet.
    "control_starts": False,
    "shed_on_overlimit": False,
    "learning_enabled": True,
    "learning_min_delta_w": 250.0,
    "learning_settle_s": 15.0,
    "learning_max_window_s": 60.0,
    "learning_min_samples": 5,
    "learning_min_confidence": 0.75,
    "use_learned_device_map": False,
    "monitor_power_entities": [],
}

# A SolarPilot automatic run is unsafe while another known controller still has
# authority over the same actuators. Missing entities are ignored, so uninstalling
# the legacy integration is enough to clear the guard.
KNOWN_LEGACY_CONFLICTS = {
    "switch.pv_excess_control_control_enabled": "PV Excess Control hoofdregeling",
}


def finite(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def quarter_elapsed_s(local_now: datetime) -> int:
    """Elapsed wall-clock seconds in the current 15-minute tariff interval."""
    return (local_now.minute % 15) * 60 + local_now.second


@dataclass(frozen=True)
class CapacityDecision:
    enabled: bool = False
    valid: bool = True
    current_average_w: float | None = None
    monthly_peak_w: float | None = None
    configured_target_w: float = 0.0
    effective_target_w: float = 0.0
    allowed_grid_w: float | None = None
    optional_headroom_w: float | None = None
    elapsed_s: int = 0
    remaining_s: int = 900
    reason: str = "Capaciteitsbewaking uitgeschakeld"


def capacity_decision(local_now: datetime, current_average_w, monthly_peak_w,
                      current_grid_w, settings=None) -> CapacityDecision:
    """Calculate a grid ceiling aimed at avoiding a new 15-minute peak.

    `current_average_w` is expected to be the smart-meter average of the running
    quarter-hour.  The result cannot undo energy already consumed and is never an
    electrical protection device.
    """
    c = {**CAPACITY_DEFAULTS, **(settings or {})}
    if not c["enabled"]:
        return CapacityDecision()
    avg = finite(current_average_w)
    monthly = finite(monthly_peak_w)
    grid = finite(current_grid_w)
    elapsed = quarter_elapsed_s(local_now)
    remaining = max(1, 900 - elapsed)
    configured = max(0.0, float(c["target_peak_w"]))
    target = configured
    if c.get("respect_billing_floor", True):
        target = max(target, max(0.0, float(c.get("billing_floor_w", 2500.0))))
    if c["adaptive_to_month_peak"] and monthly is not None:
        # Once a higher month peak already exists, chasing a much lower ceiling for
        # the remainder of that same month cannot lower that month's maximum.
        target = max(target, monthly)
    guarded_target = max(0.0, target - max(0.0, float(c["margin_w"])))
    if avg is None or grid is None:
        return CapacityDecision(True, False, avg, monthly, configured, target,
                                None, 0.0, elapsed, remaining,
                                "Kwartierpiekmeting ontbreekt of is ongeldig; optionele netlast blokkeren")
    if elapsed < int(c["minimum_elapsed_s"]):
        optional = max(0.0, guarded_target - max(0.0, grid))
        return CapacityDecision(True, True, avg, monthly, configured, target,
                                None, optional, elapsed, remaining,
                                "Begin van kwartier: nog geen dynamische piekgrens; alleen conservatieve headroom")
    consumed_equivalent = max(0.0, avg) * elapsed
    allowed = (guarded_target * 900 - consumed_equivalent) / remaining
    allowed = max(0.0, allowed)
    optional = max(0.0, allowed - max(0.0, grid))
    reason = (f"Kwartierpiekdoel {target:.0f} W; resterende importgrens {allowed:.0f} W"
              if allowed > 0 else
              f"Kwartierpiekdoel {target:.0f} W is voor dit kwartier opgebruikt; flexibele netlast afbouwen")
    return CapacityDecision(True, True, avg, monthly, configured, target,
                            allowed, optional, elapsed, remaining, reason)


@dataclass(frozen=True)
class PhaseDecision:
    enabled: bool = False
    valid: bool = True
    phase_w: tuple[float | None, float | None, float | None] = (None, None, None)
    limit_w: float = 0.0
    guarded_limit_w: float = 0.0
    max_import_w: float | None = None
    headroom_w: float | None = None
    block_increase: bool = False
    release_flexible: bool = False
    reason: str = "Fasebewaking uitgeschakeld"


def phase_decision(values, settings=None) -> PhaseDecision:
    """Conservative three-phase advisory/guard.

    Positive values mean import.  Because device phase allocation is not yet known,
    start control uses the *least* remaining phase headroom and is opt-in.
    """
    c = {**PHASE_DEFAULTS, **(settings or {})}
    if not c["enabled"]:
        return PhaseDecision()
    vals = tuple(finite(v) for v in values)
    if len(vals) != 3 or any(v is None for v in vals):
        return PhaseDecision(True, False, vals if len(vals) == 3 else (None, None, None),
                             float(c["limit_w"]), 0.0, None, 0.0,
                             bool(c.get("control_starts")), False,
                             "Fasevermogens ontbreken of zijn ongeldig; nieuwe flexibele starts blokkeren indien fasecontrole actief is")
    limit = max(0.0, float(c["limit_w"]))
    guarded = max(0.0, limit - max(0.0, float(c["margin_w"])))
    imports = tuple(max(0.0, v) for v in vals)
    maximum = max(imports)
    headroom = min(max(0.0, guarded - v) for v in imports)
    over = maximum > limit
    block = bool(c.get("control_starts")) and headroom < max(0.0, float(c["start_headroom_w"]))
    release = bool(c.get("shed_on_overlimit")) and over
    reason = (f"Fasegrens overschreden: hoogste fase {maximum:.0f} W > {limit:.0f} W" if over else
              f"Fasebewaking: kleinste vrije faseruimte {headroom:.0f} W")
    return PhaseDecision(True, True, vals, limit, guarded, maximum, headroom, block, release, reason)


@dataclass(frozen=True)
class PlannerDecision:
    hold_start: bool = False
    allow_early_grid: bool = False
    reason: str = "Geen plannerbeperking"
    forecast_gain_kwh: float | None = None
    required_energy_kwh: float = 0.0
    forecast_shortfall: bool = False


def planner_decision(*, settings=None, deferrable=False, cheap_grid_allowed=False,
                     already_on=False, urgent=False, boost=False, hold_elapsed_s=0.0,
                     deadline_s=None, current_hour_kwh=None, next_hour_kwh=None,
                     remaining_today_kwh=None, required_energy_kwh=0.0,
                     import_price_eur_kwh=None) -> PlannerDecision:
    """Decide whether an optional new start should wait for a better solar hour.

    This never interrupts a running device and never delays an urgent daily minimum.
    Early grid is optional and only a permission; the normal import/capacity limits
    still apply in the deterministic engine.
    """
    c = {**PLANNER_DEFAULTS, **(settings or {})}
    required = max(0.0, finite(required_energy_kwh) or 0.0)
    cur = finite(current_hour_kwh)
    nxt = finite(next_hour_kwh)
    rem = finite(remaining_today_kwh)
    price = finite(import_price_eur_kwh)
    gain = None if cur is None or nxt is None else nxt - cur
    shortfall = rem is not None and required > 0 and rem < required * max(1.0, float(c["forecast_sufficiency_factor"]))

    early_grid = False
    if (c["enabled"] and c.get("early_grid_enabled") and cheap_grid_allowed and required > 0
            and price is not None and price <= float(c["cheap_grid_limit_eur_kwh"])):
        if not c.get("early_grid_requires_forecast_shortfall") or shortfall:
            early_grid = True

    if (not c["enabled"] or not c.get("forecast_deferral_enabled") or not deferrable
            or already_on or urgent or boost):
        return PlannerDecision(False, early_grid, "Planner laat start toe", gain, required, shortfall)
    if cur is None or nxt is None:
        return PlannerDecision(False, early_grid, "Geen bruikbare uurvoorspelling; niet uitstellen", gain, required, shortfall)
    if shortfall:
        return PlannerDecision(False, early_grid, "Resterende zonnevoorspelling is krap voor dagminimum; niet uitstellen", gain, required, True)
    max_deferral = max(0.0, float(c["max_deferral_s"]))
    if hold_elapsed_s >= max_deferral > 0:
        return PlannerDecision(False, early_grid, "Maximale voorspelling-uitstelduur bereikt", gain, required, shortfall)
    if deadline_s is not None and deadline_s <= max_deferral + max(0.0, float(c["deadline_guard_s"])):
        return PlannerDecision(False, early_grid, "Deadline te dichtbij om nog voor betere zon uit te stellen", gain, required, shortfall)
    if gain is not None and gain >= float(c["forecast_gain_kwh"]):
        return PlannerDecision(True, early_grid,
                               f"Volgend uur circa {gain:.2f} kWh meer PV voorspeld; optionele start uitgesteld",
                               gain, required, shortfall)
    return PlannerDecision(False, early_grid, "Geen duidelijk beter zonne-uur voorspeld", gain, required, shortfall)


def fresh_daily_stats(day=""):
    return {
        "date": day,
        "site_import_kwh": 0.0,
        "site_export_kwh": 0.0,
        "pv_kwh": 0.0,
        "pv_self_used_kwh": 0.0,
        "managed_kwh": 0.0,
        "managed_solar_kwh": 0.0,
        "managed_grid_kwh": 0.0,
        "managed_battery_kwh": 0.0,
        "estimated_value_eur": 0.0,
        "samples_s": 0.0,
    }


def accounting_step(stats, *, day, dt_s, grid_w, pv_w, managed_w,
                    battery_discharge_w=0.0, import_price_eur_kwh=0.0,
                    export_price_eur_kwh=0.0):
    """Integrate transparent daily EMS KPIs from instantaneous measurements.

    Attribution of managed-load energy is intentionally conservative and labelled
    approximate: simultaneous unmanaged loads make exact electron attribution
    impossible without dedicated meters for every circuit.
    """
    out = fresh_daily_stats(day) if not isinstance(stats, dict) or stats.get("date") != day else dict(stats)
    dt = finite(dt_s)
    grid = finite(grid_w)
    managed = finite(managed_w)
    if dt is None or not 0 < dt <= 120 or grid is None or managed is None:
        return out
    hours = dt / 3_600_000.0  # W*s -> kWh multiplier
    imp_w, exp_w = max(0.0, grid), max(0.0, -grid)
    pv = max(0.0, finite(pv_w) or 0.0)
    batt = max(0.0, finite(battery_discharge_w) or 0.0)
    managed = max(0.0, managed)
    out["site_import_kwh"] += imp_w * hours
    out["site_export_kwh"] += exp_w * hours
    out["pv_kwh"] += pv * hours
    out["pv_self_used_kwh"] += min(pv, max(0.0, pv - exp_w)) * hours
    out["managed_kwh"] += managed * hours
    # Conservatively assign visible import and battery discharge to managed load
    # before claiming the rest as PV-supported.
    managed_grid_w = min(managed, imp_w)
    remaining = max(0.0, managed - managed_grid_w)
    managed_batt_w = min(remaining, batt)
    managed_solar_w = max(0.0, remaining - managed_batt_w)
    out["managed_grid_kwh"] += managed_grid_w * hours
    out["managed_battery_kwh"] += managed_batt_w * hours
    out["managed_solar_kwh"] += managed_solar_w * hours
    spread = (finite(import_price_eur_kwh) or 0.0) - (finite(export_price_eur_kwh) or 0.0)
    out["estimated_value_eur"] += managed_solar_w * hours * spread
    out["samples_s"] += dt
    return out
