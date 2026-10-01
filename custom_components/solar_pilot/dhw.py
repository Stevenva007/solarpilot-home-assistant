"""Domestic hot water policy.

SolarPilot only changes the tank temperature setpoint.  It never bypasses the
manufacturer thermostat, compressor protection, sterilisation programme or
scald protection.

The normal setpoint and monitored comfort floor are independent. A low tank or
a morning forecast never raises the normal target to defeat the manufacturer
deadband. A 50 °C target and -5 °C differential nominally allow a 45 °C restart;
the 46 °C comfort floor is therefore a warning threshold, NOT a hard guarantee.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import math
from .dhw_schedule import SCHEDULE_DEFAULTS, validate_schedule

DHW_DEFAULTS = {
    **SCHEDULE_DEFAULTS,
    "enabled": False, "safety_confirmed": False,
    "target_entity": "", "temperature_entity": "", "power_entity": "",
    "cooling_entities": [], "hygiene_entity": "", "manual_entity": "", "manual_entities": [],
    "manual_active_states": "on,on-30m,on-60m,on-90m",
    # User-facing thermal policy.
    "normal_c": 50.0, "minimum_c": 46.0,
    "tank_differential_c": -5.0,
    "minimum_buffer_c": 1.0,  # retained only for pre-beta.28 migration, not control
    "respect_space_climate": True, "optional_raise_interval_s": 1800,
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
    "rise_delay_s": 300, "fall_delay_s": 300,
    "pv_hysteresis_w": 100.0, "surplus_hysteresis_w": 300.0,
    "cooling_clear_s": 1800, "cooling_detection": "action",
    "stale_s": 300, "ack_timeout_s": 180,
    "max_surplus_import_w": 100.0, "compensate_own_power": True,
    "config_revision": "",
}

DHW_NUMBERS = {
    "normal_c": ("Normale boilerdoeltemperatuur", 40, 60, 0.5, "°C"),
    "minimum_c": ("Bewaakte comfortondergrens", 35, 55, 0.5, "°C"),
    "tank_differential_c": ("Tank schakeldifferentie", -12, -2, 1, "°C"),
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
    """Independent normal target; no deadband-compensating comfort boost."""
    return float(settings.get("normal_c", DHW_DEFAULTS["normal_c"]))


def normalized_settings(saved=None):
    """Migrate old normal targets once without silently resetting user choices.

    Old versions derived the base from minimum - differential + buffer. Preserve
    that historical base as an explicit normal target. After migration the floor,
    differential and deprecated buffer NEVER automatically change that target.
    Empty/new configurations use the new 50/46 defaults. No permissions enabled.
    """
    data = dict(saved or {})
    if data and "normal_c" not in data:
        minimum = finite(data.get("minimum_c", 43.0))
        differential = finite(data.get("tank_differential_c", -5.0))
        buffer = finite(data.get("minimum_buffer_c", 1.0))
        if None not in (minimum, differential, buffer):
            data["normal_c"] = minimum - differential + buffer
        else:
            data["normal_c"] = None  # validation must fail, not hide bad data
        data.setdefault("minimum_c", 43.0)
    return {**DHW_DEFAULTS, **data}


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
    c = {**DHW_DEFAULTS, **c}
    errors = validate_schedule(c)
    for key, (_, low, high, step, _) in DHW_NUMBERS.items():
        value = finite(c.get(key))
        if value is None or not low <= value <= high:
            errors[key] = "dhw_range"
        elif abs((value - low) / step - round((value - low) / step)) > 1e-5:
            errors[key] = "dhw_step"
    if not errors:
        base = effective_base_target(c)
        if not c["minimum_c"] <= base <= c["solar_c"] <= c["surplus_c"]:
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
            ("optional_raise_interval_s", 0, 21600),
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
    battery_discharge_w: float = 0.0
    standby_c: float | None = None
    comfort_target_c: float | None = None
    comfort_reason: str = ""
    comfort_stage: str = ""
    comfort_urgent: bool = False
    predicted_cooling: bool = False
    predicted_cooling_reason: str = ""
    luxury_allowed: bool = True
    luxury_reason: str = ""
    space_climate_busy: bool | None = False
    space_climate_reason: str = ""


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
        cooling_block = cooling_block or r.predicted_cooling
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
        # The wider hold band belongs only to a high target SolarPilot has
        # actually issued and received back.  A stale policy decision or an
        # externally selected 60 °C target must satisfy the full start rule.
        already_high = holding_owned_high and prev == c["surplus_c"]
        export = r.before_boiler_w if holding_owned_high and c["compensate_own_power"] and r.before_boiler_w is not None else r.export_w
        high = (r.export_w is not None and r.pv_w is not None and not cooling_block and r.luxury_allowed and
                ((export is not None and export >= c["surplus_threshold_w"] - c["surplus_hysteresis_w"]
                  and r.grid_w is not None and r.grid_w <= c["max_surplus_import_w"])
                 if already_high else r.export_w > c["surplus_threshold_w"]))

        desired, stage = base_target, "base"
        reason = f"Normaal doel {base_target:g} °C; Panasonic bepaalt zelf warmtevraag en verdeling"
        capacity_block = False
        if night:
            reason, stage = f"Nachtrust: normaal doel {base_target:g} °C blijft staan; geen zonnebuffer", "night"
        elif high:
            desired, stage = c["surplus_c"], "surplus"
            reason = "Voldoende werkelijk zonneoverschot; geen actieve of onzekere koeling"
        elif solar:
            # 50 °C is optional comfort/storage.  If the capacity guard says there
            # is too little quarter-hour headroom, keep only the minimum regime.
            headroom = r.optional_import_headroom_w
            if c["solar_c"] > base_target and headroom is not None and not low and headroom < c["estimated_heat_power_w"]:
                capacity_block = True
                reason = (f"Voldoende PV, maar kwartierpiekbewaking reserveert netruimte; "
                          f"minimumregime blijft actief")
            else:
                desired, stage = c["solar_c"], "solar"
                reason = "Voldoende zonneopbrengst; netstroom aanvullen is toegestaan"
        if r.standby_c is not None and stage in ("base", "night"):
            desired = min(base_target, r.standby_c)
            stage = "waiting_solar"
            reason = f"Nacht-/ochtendrust: normaal doel {base_target:g} °C; geen klokstart, Panasonic blijft regelen"
        if r.comfort_target_c is not None:
            if (not r.comfort_urgent and r.optional_import_headroom_w is not None
                    and r.optional_import_headroom_w < c["estimated_heat_power_w"]):
                capacity_block = True
                reason += "; avondvoorraad wacht op kwartierpiekruimte"
            elif (r.comfort_urgent and desired <= base_target) or r.comfort_target_c > desired:
                # Urgent diagnostics may restore normal comfort, never boost it.
                desired = min(base_target, r.comfort_target_c) if r.comfort_urgent else r.comfort_target_c
                stage = r.comfort_stage
                reason = r.comfort_reason
        if low and desired <= base_target:
            desired, stage = base_target, "minimum_monitor"
            reason = (f"Onder comfortgrens {c['minimum_c']:g} °C: normaal doel {base_target:g} °C; "
                      "geen temperatuurboost of Force DHW, Panasonic herverwarmt zelf")
        if (c.get("respect_space_climate", True) and r.space_climate_busy is not False
                and desired > base_target and desired > r.actual_target_c + .05):
            desired = base_target
            stage = "space_priority"
            reason = r.space_climate_reason or "Extra zonnebuffer wacht: ruimteklimaat actief of niet betrouwbaar bekend"
        if not r.luxury_allowed and stage not in ("morning", "minimum_recovery"):
            reason += "; " + (r.luxury_reason or "extra 60 °C wacht op Wallbox")
        if r.predicted_cooling:
            reason += "; " + r.predicted_cooling_reason
        if cooling_block and desired > c["cooling_cap_c"]:
            desired = c["cooling_cap_c"]
        if cooling_block and not night and solar:
            reason += "; extra verhoging begrensd door koeling/koelcontrole"
        if r.pv_w is None and not night and r.comfort_target_c is None and r.standby_c is None:
            reason = f"Zonnemeting ontbreekt: normaal doel {base_target:g} °C blijft beschikbaar"

        real_import_drop = (r.grid_w is not None and r.grid_w > c["max_surplus_import_w"]
                            and prev is not None and desired < prev)
        unowned_high_drop = (prev == c["surplus_c"] and desired < prev
                             and not holding_owned_high)
        if real_import_drop:
            reason += "; werkelijke netafname: extra doel valt zonder terugvalvertraging weg"
        elif unowned_high_drop:
            reason += "; onbevestigde extra-doelbeslissing vervalt zonder terugvalvertraging"
        immediate = ((r.comfort_urgent and desired <= base_target) or prev is None and desired <= base_target or night or
                     cooling_block and prev is not None and prev > c["cooling_cap_c"] or
                     real_import_drop or unowned_high_drop or r.pv_w is None or (low and desired <= base_target))
        if prev is None:
            prev = min(base_target, r.standby_c) if r.standby_c is not None else base_target
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
