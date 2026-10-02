"""Bounded, local tank learning and comfort deadlines (no I/O or actuator calls).

A deadline is a control objective, not a guarantee after an unobserved water draw.
Only the existing DHW manager may write a manufacturer-supported setpoint.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import math
from statistics import median

SCHEDULE_DEFAULTS = {
    # Opt-in on upgrade: existing installations retain their chosen thermal policy.
    "night_policy": "base",
    "morning_enabled": False, "morning_time": "09:00:00", "morning_c": 46.0,
    "morning_margin_c": 1.0, "morning_max_lead_min": 180,
    "morning_extra_lead_min": 30, "morning_hold_min": 30,
    "morning_cap_c": 55.0,
    "tank_loss_fallback_c_h": 0.25, "tank_heat_fallback_c_h": 6.0,
    "evening_enabled": False, "evening_cap_c": 55.0,
    "evening_lookahead_h": 3.0, "evening_fallback_start": "14:00:00",
    "evening_draw_buffer_c": 2.0, "evening_margin_w": 150.0,
    "predictive_cooling_enabled": False, "predictive_cooling_horizon_h": 2.0,
}


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


def quantile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered)-1, max(0, math.ceil(len(ordered)*fraction)-1))]


def clock_minutes(value):
    parts = str(value).split(":")
    if len(parts) not in (2, 3):
        raise ValueError("Gebruik HH:MM")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59) or len(parts) == 3 and int(parts[2]) != 0:
        raise ValueError("Ongeldig tijdstip")
    return h*60+m


def local_clock(now, value, day_offset=0):
    day = now.date() + timedelta(days=day_offset)
    minutes = clock_minutes(value)
    return datetime(day.year, day.month, day.day, minutes//60, minutes%60, tzinfo=now.tzinfo)


def elapsed_hours(later, earlier):
    # Timestamp arithmetic also handles the 23/25-hour DST days correctly.
    return (later.timestamp()-earlier.timestamp())/3600


class TankLearning:
    """Small robust temperature-rate model. No guessed history is generated."""
    def __init__(self):
        self.losses = []
        self.heating = []
        self.last = None
        self.anchor = None
        self.heating_now = False
        self.heating_anchor = None

    def observe(self, stamp, temperature, *, day, protected=False, heating=False):
        temp = finite(temperature)
        if temp is None or protected:
            self.last = self.anchor = self.heating_anchor = None
            self.heating_now = False
            return
        if self.last and stamp <= self.last[0]:
            return
        if self.last and stamp-self.last[0] < 300:
            return
        previous = self.last
        self.last = (stamp, temp)
        self.heating_now = bool(heating)
        if not previous or stamp-previous[0] > 900:
            self.anchor = (stamp, temp)
            self.heating_anchor = None
            return
        delta = temp-previous[1]
        if delta >= .3 or heating:
            self.heating_now = True
            if self.heating_anchor is None:
                self.heating_anchor = previous
            self.anchor = None
        elif delta < -1.5:
            # Large drops over <=15 min suggest draw/stratification, not loss.
            # A single -1 degree sensor step is allowed in a longer window:
            # Panasonic often reports whole degrees even during slow cooling.
            self.anchor = self.heating_anchor = None
        elif self.heating_anchor is not None and delta < 0:
            self.heating_anchor = None
            self.anchor = previous
        if self.heating_anchor is not None:
            span = stamp-self.heating_anchor[0]
            rise = temp-self.heating_anchor[1]
            if span >= 900 and rise >= .5:
                rate = rise*3600/span
                if 2 <= rate <= 60:
                    self.heating.append([stamp, day, rate])
                self.heating_anchor = (stamp, temp)
            elif span >= 1800 and rise < .5 and not heating:
                self.heating_anchor = None
                self.anchor = (stamp, temp)
            self.heating_now = self.heating_anchor is not None
        elif not heating and delta >= -1.5:
            if self.anchor is None:
                self.anchor = previous
            span = stamp-self.anchor[0]
            drop = self.anchor[1]-temp
            if span >= 1800 and drop >= .15:
                rate = drop*3600/span
                if 0 < rate <= 1.5:
                    self.losses.append([stamp, day, rate])
                self.anchor = (stamp, temp)
            elif span >= 7200:
                self.anchor = (stamp, temp)
        cutoff = stamp-30*86400
        self.losses = [x for x in self.losses if x[0] >= cutoff][-240:]
        self.heating = [x for x in self.heating if x[0] >= cutoff][-240:]

    def rates(self, c, stamp):
        self.losses = [x for x in self.losses if stamp-30*86400 <= x[0] <= stamp]
        self.heating = [x for x in self.heating if stamp-30*86400 <= x[0] <= stamp]
        loss_ok = len(self.losses) >= 6 and len({x[1] for x in self.losses}) >= 3
        heat_ok = len(self.heating) >= 6 and len({x[1] for x in self.heating}) >= 3
        loss = quantile([x[2] for x in self.losses], .9) if loss_ok else c["tank_loss_fallback_c_h"]
        heat = quantile([x[2] for x in self.heating], .2) if heat_ok else c["tank_heat_fallback_c_h"]
        return {"loss_c_h": round(float(loss), 4), "heat_c_h": round(float(heat), 4),
                "loss_source": "geleerd" if loss_ok else "ingestelde terugvalwaarde",
                "heat_source": "geleerd" if heat_ok else "ingestelde terugvalwaarde",
                "loss_samples": len(self.losses), "heat_samples": len(self.heating),
                "loss_days": len({x[1] for x in self.losses}), "heat_days": len({x[1] for x in self.heating})}

    def snapshot(self):
        return {"losses": self.losses[-240:], "heating": self.heating[-240:]}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        for key, low, high in (("losses", 0, 1.5), ("heating", 2, 60)):
            rows = data.get(key, [])
            clean = []
            if isinstance(rows, list):
                for row in rows[-240:]:
                    if not isinstance(row, list) or len(row) != 3:
                        continue
                    stamp, rate = finite(row[0]), finite(row[2])
                    if stamp is not None and rate is not None and low <= rate <= high and isinstance(row[1], str):
                        clean.append([stamp, row[1], rate])
            setattr(self, key, clean)


@dataclass
class ComfortPlan:
    target_c: float | None = None
    standby_target_c: float | None = None
    stage: str = ""
    reason: str = ""
    urgent: bool = False
    deadline: str = ""
    projected_c: float | None = None
    required_lead_min: float = 0
    evening_target_c: float | None = None
    last_useful_solar: str = ""
    forecast_source: str = "niet beschikbaar"
    warning: str = ""
    waiting_for_solar: bool = False
    comfort_floor_c: float | None = None
    native_restart_c: float | None = None
    below_floor: bool = False
    limit_note: str = ""
    evening_completed: bool = False

    def as_dict(self):
        return asdict(self)


class DHWComfortSchedule:
    def __init__(self):
        self.model = TankLearning()
        self.waiting = False
        self.solar_day = ""
        self.solar_since = None
        self.last_stamp = None
        self.emergency = False
        self.morning_day = ""
        self.morning_target = None
        self.evening_day = ""
        self.evening_target = None
        self.evening_done_day = ""
        self.result = ComfortPlan()
        self.rates = {}

    def snapshot(self):
        return {"model": self.model.snapshot(), "waiting": self.waiting, "solar_day": self.solar_day,
                "emergency": self.emergency, "morning_day": self.morning_day,
                "morning_target": self.morning_target, "evening_day": self.evening_day,
                "evening_target": self.evening_target, "evening_done_day": self.evening_done_day}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        self.model.restore(data.get("model", {}))
        self.waiting = bool(data.get("waiting"))
        self.emergency = bool(data.get("emergency"))
        for key in ("solar_day", "morning_day", "evening_day", "evening_done_day"):
            value = data.get(key, "")
            setattr(self, key, value if isinstance(value, str) and len(value) <= 10 else "")
        for key in ("morning_target", "evening_target"):
            value = finite(data.get(key))
            setattr(self, key, value if value is not None and 35 <= value < 60 else None)

    def plan(self, *, c, now, temperature, pv_w, grid_w, before_ev_w, night,
             protected=False, heating=False, forecast_slots=None, forecast_available=False,
             holding_evening=False):
        """Observe losses and offer a solar reserve; never defeat tank hysteresis.

        Minimum/morning recovery restores only the normal setpoint, even when
        that cannot meet a requested deadline. Manufacturer priority is intact.
        """
        c = {**SCHEDULE_DEFAULTS, **c}
        stamp, day = now.timestamp(), now.date().isoformat()
        base = float(c.get("normal_c", 50.0))
        floor = float(c["minimum_c"])
        if self.last_stamp is not None and (stamp-self.last_stamp > 900 or stamp < self.last_stamp):
            self.solar_since = None
        self.last_stamp = stamp
        self.model.observe(stamp, temperature, day=day, protected=protected, heating=heating)
        self.rates = self.model.rates(c, stamp)
        p = ComfortPlan(comfort_floor_c=floor,
                        native_restart_c=base+float(c["tank_differential_c"]))
        self.result = p
        self.emergency = False  # never restore an old compensation/boost latch
        self.morning_target = None
        if p.native_restart_c < floor:
            p.limit_note = (f"Normaal doel {base:g} °C en differentie {c['tank_differential_c']:g} °C "
                            f"geven een nominale herstart rond {p.native_restart_c:g} °C. "
                            f"{floor:g} °C is een bewaakte comfortgrens, geen gegarandeerd minimum; "
                            "SolarPilot verhoogt het doel niet om die differentie te omzeilen.")
        if protected or finite(temperature) is None:
            self.solar_since = None
            return p
        temp = float(temperature)
        pv = finite(pv_w)
        p.below_floor = temp < floor
        warnings = []
        if p.below_floor:
            warnings.append(f"Tank {temp:g} °C onder comfortgrens {floor:g} °C; "
                            f"normaal doel blijft {base:g} °C, Panasonic bepaalt de herverwarming")
        today_deadline = local_clock(now, c["morning_time"])
        morning_window_end = today_deadline + timedelta(minutes=c["morning_hold_min"])
        deadline = today_deadline if now <= morning_window_end else local_clock(now, c["morning_time"], 1)
        p.deadline = deadline.isoformat()
        hours = max(0.0, elapsed_hours(deadline, now))
        p.projected_c = round(temp-self.rates["loss_c_h"]*hours, 2)
        morning_goal = max(floor, float(c["morning_c"]))

        if c["night_policy"] == "minimum_until_solar":
            if night or (now < today_deadline and self.solar_day != day):
                self.waiting = True
            if not night and pv is not None and pv >= c["pv_threshold_w"]:
                if self.solar_since is None:
                    self.solar_since = stamp
                if stamp-self.solar_since >= c["rise_delay_s"]:
                    self.waiting = False
                    self.solar_day = day
            else:
                self.solar_since = None
            if self.waiting:
                # No overnight setback and no compensation increase. Native
                # thermostat cycles at the same normal setpoint all night.
                p.standby_target_c = base
                p.waiting_for_solar = True
                p.reason = (f"Nacht-/ochtendrust: normaal doel {base:g} °C blijft staan; "
                            "geen klokstart, Panasonic mag zelf herverwarmen")
        else:
            self.waiting = False

        if p.below_floor:
            p.target_c, p.stage, p.urgent = base, "minimum_monitor", True
            p.reason = (f"Comfortgrens onderschreden: alleen normaal doel {base:g} °C; "
                        "geen boost, Panasonic verdeelt zelf tussen ruimteklimaat en tapwater")

        if c["morning_enabled"] and now <= morning_window_end:
            need = morning_goal+float(c["morning_margin_c"])
            heat_min = max(0.0, base-temp)/max(.1, self.rates["heat_c_h"])*60
            lead = heat_min+float(c["morning_extra_lead_min"])
            p.required_lead_min = round(lead, 1)
            due = hours*60 <= min(float(c["morning_max_lead_min"]), lead)
            shortfall = p.projected_c < need
            if lead > c["morning_max_lead_min"] and shortfall:
                warnings.append("Berekende opwarmtijd overschrijdt voorlooptijd; ochtenddoel mogelijk niet haalbaar")
            if due and shortfall and not p.below_floor:
                self.morning_day, self.morning_target = day, base
                p.target_c, p.stage, p.urgent = base, "morning", True
                p.reason = (f"Ochtenddoel {morning_goal:g} °C om {str(c['morning_time'])[:5]}: "
                            f"normaal doel {base:g} °C beschikbaar; geen extra setpointverhoging, "
                            "Panasonic bepaalt de start; normaal comfort vóór Wallbox")
                if temp > p.native_restart_c:
                    warnings.append("Ochtendvoorspelling vraagt aandacht, maar de native herstartdrempel is nog niet bereikt; geen geforceerde warmtevraag")
            if now >= today_deadline and temp < morning_goal:
                warnings.append(f"Ochtenddoel nog niet gehaald: gemeten {temp:g} °C, gewenst {morning_goal:g} °C")
        if p.projected_c < floor and not p.below_floor:
            warnings.append(f"Zonder bijverwarming wordt circa {p.projected_c:g} °C voorspeld om "
                            f"{str(c['morning_time'])[:5]}; dit is een schatting zonder toekomstige waterafname")

        # A single bounded solar reserve for this day. It is not raised merely
        # to cross the thermostat's reheat differential. This may mean that the
        # manufacturer waits despite a higher setpoint; expose it, never force.
        if c["evening_enabled"] and now > morning_window_end and not night:
            remaining_h = max(0.0, elapsed_hours(local_clock(now, c["morning_time"], 1), now))
            reserve = morning_goal + self.rates["loss_c_h"]*remaining_h + float(c["evening_draw_buffer_c"]) + float(c["morning_margin_c"])
            target = min(float(c["evening_cap_c"]), max(base, float(c["solar_c"]), float(math.ceil(reserve))))
            p.evening_target_c = target
            if reserve > c["evening_cap_c"]:
                warnings.append("Avondlimiet mogelijk onvoldoende voor ochtendvoorraad; geen verhoging boven de limiet, normaal doel blijft beschikbaar")
            watts = float(c["estimated_heat_power_w"])+float(c["evening_margin_w"])
            valid_slots = []
            for item in forecast_slots or []:
                if not isinstance(item, (tuple, list)) or len(item) != 2:
                    continue
                when, available = item
                power = finite(available)
                if isinstance(when, datetime) and when.date() == now.date() and when >= now and power is not None and power >= watts:
                    valid_slots.append(when)
            if forecast_available:
                last = max(valid_slots) if valid_slots else now
                p.forecast_source = "lokaal gecorrigeerde zonneverwachting minus geschatte basislast"
                p.last_useful_solar = last.isoformat()
                in_window = elapsed_hours(last, now) <= c["evening_lookahead_h"]
            else:
                in_window = now.hour*60+now.minute >= clock_minutes(c["evening_fallback_start"])
                p.forecast_source = "ingesteld terugvalvenster; geen bruikbare zonnehorizon"
            enough = (finite(before_ev_w) is not None and before_ev_w >= watts
                      and pv is not None and pv >= c["pv_threshold_w"])
            if self.evening_day != day:
                self.evening_target = None
            if self.evening_day == day and self.evening_target is not None:
                # Clip restored settings before use; never replay a former high
                # goal after the user has selected a lower evening ceiling.
                self.evening_target = min(self.evening_target, float(c["evening_cap_c"]))
                if temp >= self.evening_target-.5:
                    self.evening_done_day = day
                    self.evening_target = None
            if (self.evening_done_day != day and self.evening_target is None and in_window
                    and enough and temp < target-.5 and target > c["solar_c"]):
                self.evening_day, self.evening_target = day, target
            p.evening_completed = self.evening_done_day == day
            holding = self.evening_day == day and self.evening_target is not None
            can_hold = (holding and holding_evening and finite(grid_w) is not None
                        and grid_w <= c["max_surplus_import_w"] and pv is not None
                        and pv >= c["pv_threshold_w"])
            if holding:
                p.evening_target_c = self.evening_target
                if temp > self.evening_target+float(c["tank_differential_c"]) and not heating:
                    warnings.append("Avonddoel ligt boven de tanktemperatuur, maar de Panasonic-herstartdrempel is nog niet bereikt; geen verhoging om een start af te dwingen")
            if ((in_window and enough or can_hold) and self.evening_target is not None
                    and not p.urgent):
                p.target_c, p.stage = self.evening_target, "evening"
                p.reason = (f"Avondvoorraad voor {str(c['morning_time'])[:5]}: laatste bruikbare zon; "
                            "begrensde warmwatervoorraad vóór Wallbox. Bij bevestigd zonneladen mag de auto "
                            "minder laden; Panasonic bepaalt zelf wanneer het water opwarmt")
        elif night:
            self.evening_target = None
        p.warning = "; ".join(dict.fromkeys(warnings))
        return p


def validate_schedule(c):
    c = {**SCHEDULE_DEFAULTS, **c}
    errors = {}
    if c["night_policy"] not in ("base", "minimum_until_solar"):
        errors["night_policy"] = "dhw_range"
    for key in ("morning_time", "evening_fallback_start"):
        try:
            clock_minutes(c[key])
        except (ValueError, TypeError):
            errors[key] = "dhw_night"
    ranges = {
        "morning_c": (40, 50), "morning_margin_c": (0, 3),
        "morning_max_lead_min": (30, 360), "morning_extra_lead_min": (0, 120),
        "morning_hold_min": (0, 120),
        "tank_loss_fallback_c_h": (.05, 1.5), "tank_heat_fallback_c_h": (1, 30),
        "evening_cap_c": (50, 59), "evening_lookahead_h": (.5, 6),
        "evening_draw_buffer_c": (0, 10), "evening_margin_w": (0, 1000),
        "predictive_cooling_horizon_h": (.5, 6),
    }
    for key, (lo, hi) in ranges.items():
        value = finite(c[key])
        if value is None or not lo <= value <= hi:
            errors[key] = "dhw_range"
    if not errors:
        if c["evening_enabled"] and c["evening_cap_c"] < c["solar_c"]:
            errors["evening_cap_c"] = "dhw_order"
        if c["evening_enabled"] and c["evening_cap_c"] > c["surplus_c"]:
            errors["evening_cap_c"] = "dhw_order"
    return errors
