"""Independent, read-only dishwasher activity and cumulative-energy evidence.

Meter activity never grants START permission, confirms a command, consumes a
preparation ticket, or proves native programme completion. No HA services here.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import math

METER_DEFAULTS = {
    "dishwasher_meter_start_w": 10.0,
    "dishwasher_meter_idle_w": 5.0,
    "dishwasher_meter_start_s": 60.0,
    "dishwasher_meter_end_s": 900.0,
    "dishwasher_meter_stale_s": 120.0,
}


def finite(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) else None


@dataclass(frozen=True)
class Sample:
    value: float | None = None
    stamp: float | None = None
    reason: str = "not_configured"

    @property
    def valid(self):
        return self.value is not None and self.stamp is not None


def read_sample(hass, entity_id, units, wall, stale_s):
    """Validate original reports, never refresh a cached or restored reading."""
    if not entity_id:
        return Sample()
    obj = hass.states.get(entity_id)
    if obj is None:
        return Sample(reason="missing")
    attrs = getattr(obj, "attributes", {}) or {}
    if any(attrs.get(key) for key in ("restored", "estimated", "is_estimated")):
        return Sample(reason="restored_or_estimated")
    unit = attrs.get("unit_of_measurement")
    if unit not in units:
        return Sample(reason="unit")
    number = finite(getattr(obj, "state", None))
    if number is None or number < 0:
        return Sample(reason="value")
    reported = getattr(obj, "last_reported", None) or getattr(obj, "last_updated", None)
    try:
        stamp = finite(reported.timestamp())
    except (AttributeError, TypeError, ValueError, OverflowError, OSError):
        stamp = None
    if stamp is None or stamp < 0 or not -5 <= wall - stamp <= stale_s:
        return Sample(reason="time")
    value = number * units[unit]
    return Sample(value, stamp, "current") if math.isfinite(value) else Sample(reason="value")


def config_errors(cfg):
    values = {key: finite(cfg.get(key, default)) for key, default in METER_DEFAULTS.items()}
    if (any(v is None for v in values.values())
            or not 0 <= values["dishwasher_meter_idle_w"] < values["dishwasher_meter_start_w"] <= 5000
            or not 1 <= values["dishwasher_meter_start_s"] <= 600
            or not 60 <= values["dishwasher_meter_end_s"] <= 3600
            or not 30 <= values["dishwasher_meter_stale_s"] <= 1800):
        return {"base": "invalid_selection"}
    return {}


class DishwasherMeter:
    """One meter binding; bounded persisted daily energy, ephemeral activity.

    Activity hysteresis deliberately survives short low-power phases but never
    a missing-source interval or restart. Low consumption is not cycle end.
    Counter deltas span only consecutive reports on the same local date; gaps,
    resets and midnight crossings are flagged, never interpolated or invented.
    """
    def __init__(self, cfg):
        self.binding = (cfg.get("power_entity", ""), cfg.get("energy_entity", ""))
        self.settings_key = tuple(cfg.get(key, default) for key, default in METER_DEFAULTS.items())
        self.invalid_config = bool(config_errors(cfg))
        self.config = {**cfg, **{key: (finite(cfg.get(key, default))
            if finite(cfg.get(key, default)) is not None else default)
            for key, default in METER_DEFAULTS.items()}}
        self.active = None
        self.above_since = self.below_since = None
        self.last_power_stamp = None
        self.last_energy = None
        self.days = {}
        self.latest = {}
        self.last_wall = None

    def sample(self, hass, when, native_active=None, native_finished=False, *, dedicated=True):
        wall = when.timestamp()
        invalid_config = self.invalid_config
        stale = finite(self.config["dishwasher_meter_stale_s"]) or METER_DEFAULTS["dishwasher_meter_stale_s"]
        day = when.date().isoformat()
        power = read_sample(hass, self.binding[0], {"W": 1., "kW": 1000.}, wall, stale)
        energy = read_sample(hass, self.binding[1], {"Wh": .001, "kWh": 1.}, wall, stale)
        # A fresh-but-delayed report can still belong to yesterday. Never
        # assign that counter interval to today's capture date.
        if energy.valid and datetime.fromtimestamp(energy.stamp, tz=when.tzinfo).date() != when.date():
            energy = Sample(reason="date_boundary")
        energy_obj = hass.states.get(self.binding[1]) if self.binding[1] else None
        if energy.valid and (getattr(energy_obj, "attributes", {}).get("state_class") not in ("total", "total_increasing")
                or getattr(energy_obj, "attributes", {}).get("device_class") not in (None, "energy")):
            energy = Sample(reason="counter_type")
        if not dedicated or invalid_config:
            power = Sample(reason="binding")
            energy = Sample(reason="binding")
        # A delayed callback or a backwards clock cannot create elapsed evidence.
        if self.last_wall is not None and wall < self.last_wall:
            self.active = None
            self.above_since = self.below_since = self.last_power_stamp = self.last_energy = None
        self.last_wall = wall
        previous = self.active
        new_report = power.valid and (self.last_power_stamp is None or power.stamp > self.last_power_stamp)
        if not power.valid or (self.last_power_stamp is not None and power.stamp < self.last_power_stamp):
            self.active = None
            self.above_since = self.below_since = self.last_power_stamp = None
        elif new_report:
            if self.last_power_stamp is not None and power.stamp - self.last_power_stamp > stale:
                self.active = None
                self.above_since = self.below_since = None
            self.last_power_stamp = power.stamp
            if power.value >= self.config["dishwasher_meter_start_w"]:
                self.below_since = None
                if self.above_since is None:
                    self.above_since = power.stamp
                if power.stamp - self.above_since >= self.config["dishwasher_meter_start_s"]:
                    self.active = True
            elif power.value <= self.config["dishwasher_meter_idle_w"]:
                self.above_since = None
                if self.below_since is None:
                    self.below_since = power.stamp
                if self.active is not True or power.stamp - self.below_since >= self.config["dishwasher_meter_end_s"]:
                    self.active = False
            else:
                self.above_since = self.below_since = None
        # Native running/paused is stronger than a quiet electrical phase. A
        # trusted completion closes history; a meter alone NEVER declares it.
        source = "meter"
        if native_active is True:
            observed, source = True, "native"
            if power.valid:
                self.active = True
        elif native_finished and native_active is False:
            observed, source = False, "native"
            self.active = False
            self.above_since = self.below_since = None
        elif self.active is not None:
            observed = self.active
        else:
            observed, source = native_active, "native" if native_active is not None else "unknown"
        delta = self._energy(day, energy, stale)
        row = self.days.get(day, {})
        if not power.valid and source == "meter":
            observed, source = None, "unknown"
        self.latest = {
            "power_w": power.value, "power_reported_at": power.stamp,
            "power_valid": power.valid, "power_reason": power.reason,
            "energy_total_kwh": energy.value, "energy_reported_at": energy.stamp,
            "energy_valid": energy.valid, "energy_reason": energy.reason,
            "active": observed, "source": source, "native_active": native_active,
            "programme_finished": native_finished is True,
            "observed_at": wall, "stale_s": stale,
            "energy_today_kwh": row.get("kwh") if row.get("pairs", 0) else None, "energy_partial": row.get("partial", True),
            "energy_delta_kwh": delta,
            "activity_changed": observed != previous,
            "note": "Activiteit afgeleid uit eigen meter; geen bewijs van programma-einde of toestemming voor bediening.",
        }
        return dict(self.latest)

    def _energy(self, day, energy, stale):
        if not self.binding[1]:
            return None
        row = self.days.setdefault(day, {"kwh": 0., "partial": True, "samples": 0, "pairs": 0, "resets": 0})
        self.days = dict(sorted(self.days.items())[-30:])
        if not energy.valid:
            row["partial"] = True
            self.last_energy = None
            return None
        previous = self.last_energy
        if previous is not None and energy.stamp == previous[1]:
            # Re-rendering never adds the same counter increment twice.
            if energy.value != previous[0]:
                row["partial"] = True
                self.last_energy = None
            return None
        self.last_energy = (energy.value, energy.stamp, day)
        row["samples"] += 1
        if previous is None:
            return None
        dt, delta = energy.stamp - previous[1], energy.value - previous[0]
        if delta < 0:
            row["resets"] += 1
            row["partial"] = True
            return None
        # A cumulative meter does not locate consumption within a gap/midnight.
        if previous[2] != day or not 0 < dt <= stale or delta > 10000 * dt / 3600000 + .002:
            row["partial"] = True
            return None
        row["pairs"] += 1
        row["kwh"] += delta
        return delta

    def snapshot(self):
        return {"version": 1, "binding": list(self.binding), "days": deepcopy(self.days)}

    def restore(self, data):
        if data is None:
            return True
        if (not isinstance(data, dict) or data.get("version") != 1
                or not isinstance(data.get("days"), dict)):
            return False
        if data.get("binding") != list(self.binding):
            # Old meter totals remain in the history file but are not relabelled.
            return False
        days = {}
        try:
            for day, row in data["days"].items():
                if datetime.fromisoformat(day).date().isoformat() != day:
                    return False
                value = finite(row.get("kwh"))
                if value is None or value < 0 or type(row.get("partial")) is not bool:
                    return False
                days[day] = {"kwh": value, "partial": True,
                    "samples": max(0, int(row.get("samples", 0))), "pairs": max(0, int(row.get("pairs", 0))), "resets": max(0, int(row.get("resets", 0)))}
        except (ValueError, TypeError, AttributeError, OverflowError):
            return False
        self.days = dict(sorted(days.items())[-30:])
        # Never restore elapsed activity, baselines, or any command authority.
        return True
