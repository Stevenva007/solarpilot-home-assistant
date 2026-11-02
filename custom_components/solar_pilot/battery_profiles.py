"""Explicit battery capabilities; product names never discover or bind sensors."""
from __future__ import annotations

from collections.abc import Mapping

MARSTEK_PROFILE = "marstek_venus_e3"
_ACTUATOR_KEYS = ("number_entity", "number_sign", "charge_script", "discharge_script", "idle_script")


def is_monitor_profile(config):
    return isinstance(config, Mapping) and config.get("profile") == MARSTEK_PROFILE


def normalize_battery_config(raw):
    """A Marstek profile cannot acquire write permission from saved generic flags."""
    from .battery_fleet import BATTERY_DEFAULTS

    raw = dict(raw) if isinstance(raw, Mapping) else {}
    result = {**BATTERY_DEFAULTS, **raw}
    if is_monitor_profile(result):
        result.update(control_kind="read_only", control_enabled=False,
                      exclusive_control_confirmed=False,
                      capacity_kwh=raw.get("capacity_kwh", 5.12),
                      power_sign=raw.get("power_sign", ""),
                      ac_power_confirmed=raw.get("ac_power_confirmed") is True)
        for key in _ACTUATOR_KEYS:
            result.pop(key, None)
    return result


def battery_source_error(configs, site):
    """Reject overlapping or unaccounted sources instead of guessing their scope.

    The legacy central meter may be the same explicitly selected fleet meter.
    A different central meter could be a total or another battery: neither
    adding it nor silently replacing it is justified by its entity name.
    """
    active = [config for config in configs if config.get("enabled", True) is True]
    if any(config.get("power_entity") is not None and not isinstance(config.get("power_entity"), str)
           for config in active):
        return "De batterijvermogensbron is ongeldig; kies een sensorentiteit"
    powers = [config.get("power_entity") for config in active if config.get("power_entity")]
    if len(powers) != len(set(powers)):
        return "Een batterijvermogensbron is meermaals gekoppeld; kies afzonderlijke metingen"
    if set(powers) & {site.get(key) for key in ("grid_entity", "export_entity", "pv_entity")}:
        return "Batterijvermogen mag niet dezelfde bron zijn als P1 of zonnepanelen"
    legacy = site.get("battery_power_entity")
    if active and legacy and legacy not in powers:
        return "Centrale batterijbron en batterijprofielen hebben onbekende overlap; controleer de bronkoppelingen"
    if legacy and any(config.get("power_entity") == legacy and
                      config.get("power_sign") != site.get("battery_sign", "discharge_positive")
                      for config in active):
        return "Dezelfde batterijbron heeft twee verschillende tekenrichtingen; controleer de bronkoppelingen"
    return ""
