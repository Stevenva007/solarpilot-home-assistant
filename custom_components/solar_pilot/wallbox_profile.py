"""Read-only charging envelope from existing HA Wallbox entities, with provenance.

The main fuse/ICP setting is intentionally never a charging-current source.
No network requests or Wallbox services are made by this module.
"""
from __future__ import annotations
import math
import time
from homeassistant.helpers import entity_registry as er

PROFILE_DEFAULTS = {
    "profile_auto": True, "max_current_entity": "", "phases_entity": "",
    "charging_phases": 1, "max_current_a": 25.0, "voltage_v": 230.0,
    "minimum_current_a": 6.0, "minimum_from_profile": False,
}
PROFILE_READ_KEYS = ("max_current_entity", "phases_entity")


def numeric(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


class WallboxProfile:
    def __init__(self, hass, settings):
        self.hass, self.settings = hass, settings
        self.sources = {}
        self.next_discovery = 0.0
        self.cached = {}

    def discover(self, now):
        if now < self.next_discovery:
            return
        self.next_discovery = now+600
        self.sources = {}
        reg = er.async_get(self.hass)
        get = getattr(reg, "async_get", lambda _: None)
        reference = next((get(self.settings.get(k)) for k in ("power_entity", "status_entity", "mode_entity")
                          if self.settings.get(k) and get(self.settings[k]) is not None), None)
        device = getattr(reference, "device_id", None)
        if not device:
            return
        rows = getattr(reg, "entities", {})
        rows = list(rows.values()) if hasattr(rows, "values") else []
        candidates = [x for x in rows if getattr(x, "device_id", None) == device
                      and getattr(x, "platform", None) == "wallbox"
                      and not getattr(x, "disabled_by", None)]
        for dest, keys in (("max_current_entity", ("max_charging_current",)),
                           ("phases_entity", ("charging_phases", "phase_count", "phases"))):
            hits = [x for x in candidates if getattr(x, "translation_key", None) in keys
                    and str(x.entity_id).split(".")[0] in ("number", "sensor")]
            # Prefer the configured number over its sensor mirror. No arbitrary
            # selection when several candidates remain for the same charger.
            number = [x for x in hits if x.entity_id.startswith("number.")]
            hits = number or hits
            if len(hits) == 1:
                self.sources[dest] = hits[0].entity_id

    def _read(self, entity_id, wall):
        obj = self.hass.states.get(entity_id) if entity_id else None
        if obj is None or obj.state in ("unknown", "unavailable", ""):
            return None, "bron ontbreekt"
        if obj.attributes.get("restored"):
            return None, "bron nog niet opnieuw bevestigd"
        stamp = getattr(obj, "last_reported", None) or getattr(obj, "last_updated", None)
        try:
            age = wall - stamp.timestamp()
        except (AttributeError, TypeError, ValueError, OverflowError):
            return None, "bron verouderd"
        if not math.isfinite(age) or not -5 <= age <= self.settings.get("stale_s", 300):
            return None, "bron verouderd"
        return obj, ""

    def update(self, *, wall=None, monotonic=None):
        wall = time.time() if wall is None else wall
        monotonic = time.monotonic() if monotonic is None else monotonic
        c = {**PROFILE_DEFAULTS, **self.settings}
        if c["profile_auto"]:
            self.discover(monotonic)
        sources = {k: c.get(k) or (self.sources.get(k) if c["profile_auto"] else "") for k in PROFILE_READ_KEYS}
        phases, amps = int(c["charging_phases"]), float(c["max_current_a"])
        current_source, phase_source = "handmatig bevestigd profiel", "handmatig bevestigd profiel"
        warning = []
        if c["profile_auto"] and sources["max_current_entity"]:
            entity = sources["max_current_entity"]
            obj, issue = self._read(entity, wall)
            value = numeric(obj.state) if obj else None
            unit = obj.attributes.get("unit_of_measurement") if obj else None
            # Older Wallbox number entities omit the A unit. Only accept a known
            # max-current number binding in that case, never an ICP value.
            identity = str(entity).casefold()
            if "icp" in identity:
                warning.append("ICP/hoofdzekering is geen laadlimiet; handmatig profiel gebruikt")
            elif value is not None and 0 <= value <= 80 and (unit == "A" or entity.startswith("number.") and not unit):
                upper = numeric(obj.attributes.get("max"))
                amps = min(value, upper) if upper is not None and 0 <= upper <= 80 else value
                current_source = "Wallbox-integratie"
            else:
                warning.append(f"Laadstroom {issue or 'ongeldig'}; handmatige terugval {amps:g} A (niet live bevestigd)")
        elif c["profile_auto"]:
            warning.append("Geen eenduidige laadstroombron gevonden; handmatige terugval gebruikt")
        if c["profile_auto"] and sources["phases_entity"]:
            obj, issue = self._read(sources["phases_entity"], wall)
            value = numeric(obj.state) if obj else None
            if value in (1, 3):
                phases, phase_source = int(value), "expliciete Wallbox-bron"
            else:
                warning.append("Fasebron ontbreekt/ongeldig; handmatig bevestigd faseprofiel gebruikt")
        volts, minimum = float(c["voltage_v"]), float(c["minimum_current_a"])
        self.cached = {
            "phases": phases, "max_current_a": round(amps, 2), "voltage_v": volts,
            "maximum_power_w": round(phases*volts*amps, 1),
            "minimum_power_w": round(phases*volts*minimum, 1),
            "current_source": current_source, "phase_source": phase_source,
            "current_entity": sources["max_current_entity"] or None,
            "phases_entity": sources["phases_entity"] or None,
            "warning": "; ".join(warning), "read_only": True,
            "note": "Profiel is planning, geen fysieke stroombegrenzer. ICP/hoofdzekering wordt niet als laadlimiet gebruikt.",
        }
        return self.cached


def validate_profile(c):
    c = {**PROFILE_DEFAULTS, **c}
    errors = {}
    if numeric(c["charging_phases"]) not in (1, 3):
        errors["charging_phases"] = "invalid_number"
    for key, low, high in (("max_current_a", 6, 80), ("voltage_v", 207, 253), ("minimum_current_a", 6, 16)):
        value = numeric(c[key])
        if value is None or not low <= value <= high:
            errors[key] = "invalid_number"
    if not errors and float(c["minimum_current_a"]) > float(c["max_current_a"]):
        errors["minimum_current_a"] = "invalid_number"
    if "icp" in str(c.get("max_current_entity", "")).casefold():
        errors["max_current_entity"] = "invalid_current_source"
    return errors
