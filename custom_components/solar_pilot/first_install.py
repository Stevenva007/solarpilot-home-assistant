"""Privacy-safe first-install suggestions for the public HACS build.

The public repository deliberately contains no household-specific Home Assistant
entity IDs.  Only universal/harmless values may be suggested here.  Actual grid,
PV, phase, forecast, heat-pump, tariff and Wallbox entities are selected by the
user in Home Assistant and are never enabled merely by being suggested.
"""
from __future__ import annotations
from copy import deepcopy

# Keep this mapping intentionally small. ``sun.sun`` is a Home Assistant core
# entity when the Sun integration is present; the Wallbox name is only a label.
PUBLIC_FIRST_INSTALL = {
    "local_pv": {"sun_entity": "sun.sun"},
    "wallbox": {"name": "Wallbox"},
}


def _exists(hass, entity_id: str) -> bool:
    return bool(entity_id and getattr(hass, "states", None) and hass.states.get(entity_id) is not None)


def apply_first_install_suggestions(hass, values: dict, group: str) -> dict:
    """Return a copy with only privacy-safe empty fields prefilled.

    Entity values are inserted only when the exact universal candidate exists.
    Boolean master switches are never changed.  A friendly name does not enable
    or control any physical device.
    """
    out = deepcopy(values or {})
    for key, candidate in PUBLIC_FIRST_INSTALL.get(group, {}).items():
        if out.get(key):
            continue
        if key == "name":
            out[key] = candidate
        elif _exists(hass, candidate):
            out[key] = candidate
    return out
