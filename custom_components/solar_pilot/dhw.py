"""Domestic hot water policy.

SolarPilot only changes the tank temperature setpoint.  It never bypasses the
manufacturer thermostat, compressor protection, sterilisation programme or
scald protection.

The important distinction in current SolarPilot is between a *minimum desired measured tank
water temperature* and the Panasonic setpoint.  A tank with a -5 °C switching
differential needs a higher setpoint if 43 °C is intended as the practical lower
comfort bound.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import math

DHW_DEFAULTS = {
    "enabled": False, "safety_confirmed": False,
    "target_entity": "", "temperature_entity": "", "power_entity": "",
    "cooling_entities": [], "hygiene_entity": "", "manual_entity": "", "manual_entities": [],
    "manual_active_states": "on,on-30m,on-60m,on-90m",
    # User-facing thermal policy.
    "minimum_c": 43.0,
    "tank_differential_c": -5.0,
    "minimum_buffer_c": 1.0,
    "solar_c": 50.0, "surplus_c": 60.0, "cooling_cap_c": 50.0,
    "pv_threshold_w": 1000.0, "surplus_threshold_w": 3500.0,
    "estimated_heat_power_w": 3200.0,
    "night_enabled": True, "night_start": "23:00:00", "night_end": "06:00:00",
    # Manufacturer sterilisation guard.  This is a no-command window, not a
    # replacement for the actual Panasonic programme.
    "hygiene_schedule_enabled": True,
    "hygiene_weekdays": "0",  # Monday=0
    "hygiene_start": "12:00:00",
    "hygiene_target_c": 62.0,
    "hygiene_guard_before_s": 900,
    "hygiene_guard_after_s": 10800,
    "rise_delay_s": 60, "fall_delay_s": 120,
    "pv_hysteresis_w": 100.0, "surplus_hysteresis_w": 300.0,
    "cooling_clear_s": 600, "cooling_detection": "action",
    "stale_s": 300, "ack_timeout_s": 180,
    "max_surplus_import_w": 100.0, "compensate_own_power": True,
    "config_revision": "",
}

DHW_NUMBERS = {
    "minimum_c": ("Minimum gewenste watertemperatuur", 35, 55, 0.5, "°C"),
    "tank_differential_c": ("Tank schakeldifferentie", -12, -2, 1, "°C"),
    "minimum_buffer_c": ("Minimum veiligheidsbuffer", 0, 5, 0.5, "°C"),
    "solar_c": ("Boiler bij zonneopbrengst", 40, 65, 0.5, "°C"),
    "surplus_c": ("Boiler bij overschot", 45, 65, 0.5, "°C"),
    "cooling_cap_c": ("Boiler maximum bij koeling", 40, 65, 0.5, "°C"),
    "pv_threshold_w": ("Boiler drempel zonneopbrengst", 0, 50000, 50, "W"),
    "surplus_threshold_w": ("Boiler drempel overschot", 0, 50000, 50, "W"),
    "estimated_heat_power_w": ("Geschat elektrisch boilervermogen", 100, 20000, 50, "W"),
}


def finite(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def minute(value):
    parts = str(value).split(":")
    if len(parts) not in (2, 3):
        raise ValueError("Gebruik HH:MM of HH:MM:SS")
    h, m = int(parts[0]), int(parts[1])
    if not 0 <= h <= 23 or not 0 <= m <= 59 or (len(parts) == 3 and int(parts[2]) != 0):
        raise ValueError("Ongeldig tijdstip; seconden moeten 00 zijn")
    return h * 60 + m


def weekday_set(value) -> set[int]:
    try:
        days = {int(x.strip()) for x in str(value).split(",") if x.strip() != ""}
    except (TypeError, ValueError):
        return set()
    return days if days and all(0 <= x <= 6 for x in days) else set()


def effective_base_target(settings) -> float:
    """Setpoint needed to keep the practical lower bound near minimum_c.

    Example: minimum 43, Panasonic switching differential -5 and 1 degree
    buffer -> setpoint 49.  This is still only a control target, not a guarantee
    that a rapidly drawn tank can never dip below the minimum.
    """
    return float(settings["minimum_c"]) - float(settings["tank_differential_c"]) + float(settings["minimum_buffer_c"])


def night_active(c, local_now: datetime):
    if not c["night_enabled"]:
        return False
    start, end = minute(c["night_start"]), minute(c["night_end"])
    now = local_now.hour * 60 + local_now.minute
    return (start <= now < end) if start < end else (now >= start or now < end)


def hygiene_schedule_active(c, local_now: datetime):
    if not c.get("hygiene_schedule_enabled"):
        return False
    days = weekday_set(c.get("hygiene_weekdays", ""))
    if not days:
        return False
    try:
        start_minute = minute(c["hygiene_start"])
    except (ValueError, TypeError):
        return False
    week_s = 7 * 24 * 3600
    now_s = local_now.weekday() * 86400 + local_now.hour * 3600 + local_now.minute * 60 + local_now.second
    before = max(0, int(c.get("hygiene_guard_before_s", 0)))
    after = max(0, int(c.get("hygiene_guard_after_s", 0)))
    span = before + after
    for day in days:
        start_s = day * 86400 + start_minute * 60
        window_start = (start_s - before) % week_s
        distance = (now_s - window_start) % week_s
        if distance <= span:
            return True
    return False


def validate_settings(c):
    errors = {}
    for key, (_, low, high, step, _) in DHW_NUMBERS.items():
        value = finite(c.get(key))
        if value is None or not low <= value <= high:
            errors[key] = "dhw_range"
        elif abs((value - low) / step - round((value - low) / step)) > 1e-5:
            errors[key] = "dhw_step"
    if not errors:
        base = effective_base_target(c)
        if not base <= c["solar_c"] <= c["surplus_c"]:
            errors["base"] = "dhw_order"
        if not base <= c["cooling_cap_c"] <= c["surplus_c"]:
            errors["cooling_cap_c"] = "dhw_order"
        if c["hygiene_target_c"] < c["surplus_c"]:
            errors["hygiene_target_c"] = "dhw_order"
    try:
        if minute(c["night_start"]) == minute(c["night_end"]):
            errors["night_end"] = "dhw_night"
        minute(c["hygiene_start"])
    except (ValueError, TypeError):
        errors["night_start"] = "dhw_night"
    if not weekday_set(c.get("hygiene_weekdays", "")):
        errors["hygiene_weekdays"] = "dhw_range"
    for key, low, high in (
            ("rise_delay_s", 0, 1800), ("fall_delay_s", 0, 1800),
            ("cooling_clear_s", 0, 3600), ("stale_s", 30, 3600),
            ("ack_timeout_s", 15, 600), ("max_surplus_import_w", 0, 3000),
            ("pv_hysteresis_w", 0, 5000), ("surplus_hysteresis_w", 0, 5000),
            ("hygiene_guard_before_s", 0, 7200), ("hygiene_guard_after_s", 900, 21600),
            ("hygiene_target_c", 55, 65)):
        value = finite(c.get(key))
        if value is None or not low <= value <= high:
            errors[key] = "dhw_range"
    if finite(c.get("pv_hysteresis_w")) is not None and finite(c.get("pv_threshold_w")) is not None and c["pv_hysteresis_w"] > c["pv_threshold_w"]:
        errors["pv_hysteresis_w"] = "dhw_range"
    if finite(c.get("surplus_hysteresis_w")) is not None and finite(c.get("surplus_threshold_w")) is not None and c["surplus_hysteresis_w"] > c["surplus_threshold_w"]:
        errors["surplus_hysteresis_w"] = "dhw_range"
    if c["cooling_detection"] not in ("action", "mode"):
        errors["cooling_detection"] = "dhw_range"
    return errors


def cooling_state(state: str | None, attributes: dict, detection="action") -> bool | None:
    if state in (None, "unknown", "unavailable", ""):
        return None
    if state == "on":
        return True
    action = attributes.get("hvac_action")
    if action == "cooling":
        return True
    if state == "off":
        return False
    if detection == "mode" and state == "cool":
        return True
    if action in ("idle", "off", "heating", "preheating", "fan", "drying", "defrosting"):
        return False
    if state == "cool":
        return True
    if state in ("heat", "fan_only", "dry"):
        return False
    return None


@dataclass
class DHWReading:
    temperature_c: float | None = None
    actual_target_c: float | None = None
    pv_w: float | None = None
    export_w: float | None = None
    before_boiler_w: float | None = None
    grid_w: float | None = None
    cooling: bool | None = None
    protected: bool = False
    protection_reason: str = ""
    optional_import_headroom_w: float | None = None


@dataclass
class DHWDecision:
    target_c: float | None = None
    reason: str = "Nog niet geconfigureerd"
    stage: str = "disabled"
    night: bool = False
    cooling_block: bool = True
    low_temperature: bool = False
    remaining_s: int = 0
    base_target_c: float | None = None
    capacity_block: bool = False


class DHWPolicy:
    def __init__(self, settings):
        self.settings = {**DHW_DEFAULTS, **settings}
        self.current = None
        self.candidate = None
        self.candidate_since = None
        self.last_cooling = None
        self.last_sample = None
        self.result = DHWDecision()

    def reset_stability(self):
        self.current = self.candidate = self.candidate_since = None
        self.last_sample = None

    def update(self, now, local_now, r: DHWReading, holding_owned_high=False):
        c = self.settings
        base_target = effective_base_target(c)
        night = night_active(c, local_now)
        low = r.temperature_c is not None and r.temperature_c < c["minimum_c"]
        if r.cooling is not False:
            self.last_cooling = now
        cooling_block = (r.cooling is not False or
                         self.last_cooling is not None and now - self.last_cooling < c["cooling_clear_s"])
        if r.protected:
            self.reset_stability()
            self.result = DHWDecision(None, r.protection_reason, "protected", night, cooling_block,
                                      low, base_target_c=base_target)
            return self.result
        if r.temperature_c is None or r.actual_target_c is None:
            self.reset_stability()
            self.result = DHWDecision(None, "Boilertemperatuur of doelterugmelding ontbreekt; geen opdrachten",
                                      "unavailable", night, cooling_block, low,
                                      base_target_c=base_target)
            return self.result
        if self.last_sample is not None and now - self.last_sample > max(30, c.get("sample_gap_s", 30)):
            self.current = self.candidate = self.candidate_since = None
        self.last_sample = now
        prev = self.current
        pv_hold = prev is not None and prev >= c["solar_c"]
        pv_min = c["pv_threshold_w"] - (c["pv_hysteresis_w"] if pv_hold else 0)
        solar = r.pv_w is not None and r.pv_w >= pv_min
        already_high = prev == c["surplus_c"]
        export = r.before_boiler_w if holding_owned_high and c["compensate_own_power"] and r.before_boiler_w is not None else r.export_w
        high = (r.export_w is not None and r.pv_w is not None and not cooling_block and
                ((export is not None and export >= c["surplus_threshold_w"] - c["surplus_hysteresis_w"]
                  and r.grid_w is not None and r.grid_w <= c["max_surplus_import_w"])
                 if already_high else r.export_w > c["surplus_threshold_w"]))

        desired, stage = base_target, "base"
        reason = f"Minimumregime: doel {base_target:g} °C houdt rekening met tankdifferentie"
        capacity_block = False
        if night:
            reason, stage = "Nachtrust: alleen minimumregime behouden", "night"
        elif high:
            desired, stage = c["surplus_c"], "surplus"
            reason = "Voldoende werkelijk zonneoverschot; geen actieve of onzekere koeling"
        elif solar:
            # 50 °C is optional comfort/storage.  If the capacity guard says there
            # is too little quarter-hour headroom, keep only the minimum regime.
            headroom = r.optional_import_headroom_w
            if headroom is not None and not low and headroom < c["estimated_heat_power_w"]:
                capacity_block = True
                reason = (f"Voldoende PV, maar kwartierpiekbewaking reserveert netruimte; "
                          f"minimumregime blijft actief")
            else:
                desired, stage = c["solar_c"], "solar"
                reason = "Voldoende zonneopbrengst; netstroom aanvullen is toegestaan"
        if cooling_block and desired > c["cooling_cap_c"]:
            desired = c["cooling_cap_c"]
        if cooling_block and not night and solar:
            reason += "; extra verhoging begrensd door koeling/koelcontrole"
        if r.pv_w is None and not night:
            reason = "Zonnemeting ontbreekt: terug naar minimumregime"

        immediate = (prev is None and desired == base_target or night or
                     cooling_block and prev is not None and prev > c["cooling_cap_c"] or
                     r.pv_w is None or low)
        if prev is None:
            prev = base_target
            self.current = prev
        remaining = 0
        if desired != prev and not immediate:
            if self.candidate != desired:
                self.candidate, self.candidate_since = desired, now
            delay = c["rise_delay_s"] if desired > prev else c["fall_delay_s"]
            remaining = max(0, math.ceil(delay - (now - self.candidate_since)))
            if remaining:
                reason += f"; stabiliteitscontrole nog {remaining} s"
                desired = prev
            else:
                self.current = desired
                self.candidate = self.candidate_since = None
        else:
            self.current = desired
            self.candidate = self.candidate_since = None
        self.result = DHWDecision(desired, reason, stage, night, cooling_block, low,
                                  remaining, base_target, capacity_block)
        return self.result
