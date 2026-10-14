"""Calculated DHW SG target from locally confirmed display metadata only.

This is a temperature comparison, never a Panasonic command, native SG receipt,
applied target, completion signal or thermal/control-model input. A normal
target's original report time is not replaced with the render or capture time.
"""
from __future__ import annotations

import math
import hashlib
import json
import re


REASONS = frozenset({"profile_unconfirmed", "profile_invalid", "profile_confirmation_invalid",
                     "profile_source_unbound", "normal_target_unavailable", "calculated_target_out_of_range", "calculated"})


def resolved_goal_binding(hass, entity_id):
    """Opaque exact registry identity; a reused entity name is not old proof."""
    if not isinstance(entity_id, str) or not entity_id.startswith(("water_heater.", "climate.")):
        return None
    try:
        from homeassistant.helpers import entity_registry
        entry = entity_registry.async_get(hass).async_get(entity_id)
    except (AttributeError, KeyError, TypeError, ValueError, ImportError):
        return None
    keys = ("entity_id", "platform", "unique_id", "device_id", "config_entry_id")
    parts = [getattr(entry, key, None) for key in keys]
    if any(not isinstance(value, str) or not value for value in parts):
        return None
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def binding(value):
    return value if isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) else None


def number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def timestamp(value):
    value = number(value)
    return value if value is not None and 0 < value <= 4102444800 else None


def fresh(original, now, stale):
    original, now, stale = timestamp(original), timestamp(now), number(stale)
    return (original is not None and now is not None and stale is not None
            and 0 < stale <= 600 and -5 <= now-original <= stale)


def calculate_sg_tank_goal(config, tank, now, *, stale_s=120, source_binding=None):
    """Return a detached comparison; unknown input stays unknown.

    The confirmation time bounds new history: no observation captured before
    that time can acquire today's percentage. Native ordinary min/max values
    are not assumed to be effective SG limits and are never silently applied.
    """
    config = config if isinstance(config, dict) else {}
    tank = tank if isinstance(tank, dict) else {}
    target, original = number(tank.get("target_c")), timestamp(tank.get("target_stamp"))
    stale = number(stale_s)
    valid_normal = (target is not None and 0 <= target <= 100 and fresh(original, now, stale))
    row = {"normal_target_c": target if valid_normal else None,
           "normal_target_reported_at": original,
           "calculated_c": None, "profile_percent": None, "profile_confirmed_at": None,
           "valid_until": None, "stale_s": stale, "source": "none", "read_only": True,
           "source_binding": None,
           "reason": "profile_unconfirmed"}
    if config.get("sg_dhw_capacity_confirmed") is not True:
        return row
    explicit = config.get("sg_dhw_capacity_target_entity")
    confirmed_binding = binding(config.get("sg_dhw_capacity_binding"))
    if (not isinstance(explicit, str) or not explicit.startswith(("water_heater.", "climate."))
            or tank.get("entity_id") != explicit or confirmed_binding is None
            or binding(source_binding) != confirmed_binding):
        row["reason"] = "profile_source_unbound"
        return row
    percent = number(config.get("sg_dhw_capacity_percent"))
    if percent is None or not 100 <= percent <= 200:
        row["reason"] = "profile_invalid"
        return row
    confirmed = timestamp(config.get("sg_dhw_capacity_confirmed_at"))
    now = timestamp(now)
    if confirmed is None or now is None or confirmed > now:
        row["reason"] = "profile_confirmation_invalid"
        return row
    row.update(profile_percent=percent, profile_confirmed_at=confirmed, source="local_confirmed_profile",
               source_binding=confirmed_binding)
    if not valid_normal:
        row["reason"] = "normal_target_unavailable"
        return row
    calculated = round(target*percent/100, 2)
    if not 0 <= calculated <= 100:
        row["reason"] = "calculated_target_out_of_range"
        return row
    row.update(calculated_c=calculated, valid_until=original+stale, reason="calculated")
    return row


def contact_observation(sg, now):
    """Only the actually confirmed relay report supplies contact state."""
    sg = sg if isinstance(sg, dict) else {}
    original, stale = timestamp(sg.get("relay_observed_at")), number(sg.get("relay_stale_s", 120))
    current = (sg.get("configured") is True and sg.get("relay_confirmed") is True and type(sg.get("relay_on")) is bool
               and fresh(original, now, stale))
    deadline = timestamp(sg.get("relay_valid_until"))
    expiry = original+stale if current else None
    if current and sg["relay_on"] is True and deadline is not None:
        expiry = min(expiry, deadline)
        current = now <= expiry
    return {"contact_state": ("on" if sg["relay_on"] else "off") if current else "unknown",
            "contact_reported_at": original, "contact_valid_until": expiry if current else None,
            "contact_stale_s": stale}


def retained_sg_goal(raw, *, captured_at, stale_s, normal_target_c, normal_target_reported_at):
    """Validate the closed stored evidence shape without adding current facts.

    Missing pre-feature rows stay missing. Corrupt math, forged source times,
    future profile confirmation and contact requests cannot become history.
    """
    if raw is None:
        return None
    if (not isinstance(raw, dict) or raw.get("read_only") is not True
            or not isinstance(raw.get("reason"), str) or raw["reason"] not in REASONS):
        raise ValueError("Warmtepomphistoriek bevat ongeldig berekend SG-doel")
    for key in ("normal_target_c", "normal_target_reported_at", "calculated_c", "profile_percent",
                "profile_confirmed_at", "valid_until", "stale_s", "contact_reported_at",
                "contact_valid_until", "contact_stale_s"):
        value = raw.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value)):
            raise ValueError("Warmtepomphistoriek bevat ongeldige SG-doelwaarden")
    source = raw.get("source")
    if source not in ("none", "local_confirmed_profile"):
        raise ValueError("Warmtepomphistoriek bevat ongeldige SG-doelbron")
    source_binding = binding(raw.get("source_binding"))
    if (source == "local_confirmed_profile" and source_binding is None
            or source == "none" and raw.get("source_binding") is not None):
        raise ValueError("Warmtepomphistoriek bevat ongeldige SG-doelkoppeling")
    expected = calculate_sg_tank_goal({
        "sg_dhw_capacity_target_entity": "water_heater.retained_source", "sg_dhw_capacity_binding": source_binding,
        "sg_dhw_capacity_confirmed": source == "local_confirmed_profile",
        "sg_dhw_capacity_percent": raw.get("profile_percent"),
        "sg_dhw_capacity_confirmed_at": raw.get("profile_confirmed_at")},
        {"entity_id": "water_heater.retained_source", "target_c": normal_target_c, "target_stamp": normal_target_reported_at},
        captured_at, stale_s=stale_s, source_binding=source_binding)
    # Invalid/unconfirmed metadata may retain only an unknown comparison. The
    # numerical fields must still match the real ordinary target and timestamp.
    for key in ("normal_target_c", "normal_target_reported_at", "calculated_c", "profile_percent",
                "profile_confirmed_at", "valid_until", "stale_s", "source", "read_only", "source_binding"):
        if raw.get(key) != expected[key]:
            raise ValueError("Warmtepomphistoriek bevat tegenstrijdig berekend SG-doel")
    if source == "local_confirmed_profile" and raw["reason"] != expected["reason"]:
        raise ValueError("Warmtepomphistoriek bevat tegenstrijdige SG-doelstatus")
    if source == "none" and raw["reason"] not in ("profile_unconfirmed", "profile_invalid", "profile_confirmation_invalid", "profile_source_unbound"):
        raise ValueError("Warmtepomphistoriek bevat tegenstrijdige SG-doelstatus")
    state = raw.get("contact_state")
    original, deadline, contact_stale = (timestamp(raw.get("contact_reported_at")),
        timestamp(raw.get("contact_valid_until")), number(raw.get("contact_stale_s")))
    if state not in ("on", "off", "unknown"):
        raise ValueError("Warmtepomphistoriek bevat ongeldige SG-contactstatus")
    if (state != "unknown" and (not fresh(original, captured_at, contact_stale)
            or deadline is None or not captured_at <= deadline <= original+contact_stale)
            or state == "unknown" and raw.get("contact_valid_until") is not None
            or raw.get("contact_reported_at") is not None and original is None
            or contact_stale is None or not 0 < contact_stale <= 600):
        raise ValueError("Warmtepomphistoriek bevat tegenstrijdige SG-contactactualiteit")
    return {**expected, "reason": raw["reason"], "contact_state": state,
            "contact_reported_at": original, "contact_valid_until": deadline, "contact_stale_s": contact_stale}
