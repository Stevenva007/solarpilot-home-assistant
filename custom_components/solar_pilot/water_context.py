"""Current read-only appliance context for household water observations.

These are simultaneous HA reports, not attribution of water or proof of a
physical cause. Never call a controller or replace a missing source timestamp.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import math
import re
import time

from .dishwasher import accepted, norm, settings as dishwasher_settings

_ENTITY = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        value = float(value)
    except (ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _entity(value):
    return value if isinstance(value, str) and _ENTITY.fullmatch(value) else None


def _reading(value, stamp, stale, now):
    value, stamp = _number(value), _number(stamp)
    if value is None or stamp is None or not 0 <= value <= 100 or not 0 < stamp <= now:
        return None
    if now - stamp > stale:
        return None
    return {"value": value, "reported_at": stamp, "valid_until": stamp + stale}


def _state_stamp(obj, stale, now):
    if obj is None:
        return None
    attrs = getattr(obj, "attributes", {})
    if (not isinstance(attrs, Mapping) or any(attrs.get(key) for key in
            ("restored", "estimated", "is_estimated"))
            or str(getattr(obj, "state", "")).casefold() in
            ("", "unknown", "unavailable", "none", "null")):
        return None
    stamp = getattr(obj, "last_reported", None) or getattr(obj, "last_updated", None)
    try:
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            return None
        wall = stamp.timestamp()
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(wall) or not 0 < wall <= now or now - wall > stale:
        return None
    return wall


def capture_water_context(runtime, panasonic=None, *, now=None):
    """Return validated context, private source ACLs and an opaque binding."""
    now = time.time() if now is None else now
    if _number(now) is None or now <= 0:
        return {}, set(), None
    p = panasonic if isinstance(panasonic, Mapping) else {}
    sources, context, roles = set(), {}, {}
    stale = _number(p.get("source_stale_s"))
    stale = stale if stale is not None and 5 <= stale <= 86400 else 120
    tank = p.get("display_tank")
    tank = tank if isinstance(tank, Mapping) else {}
    boiler = {}
    for role, key, stamp_key, entity_key in (
        ("temperature", "temperature_c", "temperature_stamp", "temperature_entity"),
        ("target", "target_c", "target_stamp", "target_entity"),
    ):
        source, reading = None, None
        if tank.get("available") is True and _entity(tank.get("entity_id")):
            reading = _reading(tank.get(key), tank.get(stamp_key), stale, now)
            if reading is not None:
                source = tank["entity_id"]
        if reading is None and _entity(p.get(entity_key)):
            reading = _reading(p.get(key), p.get(stamp_key), stale, now)
            if reading is not None:
                source = p[entity_key]
        if reading is not None:
            boiler[role] = reading
            sources.add(source)
            roles["boiler_" + role] = source
    if boiler:
        context["boiler"] = boiler

    readings = []
    configs = getattr(runtime, "configs", {})
    configs = configs.values() if isinstance(configs, Mapping) else ()
    for index, cfg in enumerate(configs):
        if not isinstance(cfg, Mapping) or cfg.get("kind") != "dishwasher":
            continue
        c = dishwasher_settings(cfg)
        state_id, link_id = (_entity(c.get("dishwasher_state_entity")),
                             _entity(c.get("dishwasher_connection_entity")))
        sources.update(value for value in (state_id, link_id) if value)
        subject = str(cfg.get("id", index))
        roles["dishwasher:" + subject] = [state_id, link_id]
        max_age = _number(c.get("dishwasher_stale_s"))
        max_age = max_age if max_age is not None and 5 <= max_age <= 86400 else 300
        obj = runtime.hass.states.get(state_id) if state_id else None
        link = runtime.hass.states.get(link_id) if link_id else None
        stamp, link_stamp = _state_stamp(obj, max_age, now), _state_stamp(link, max_age, now)
        if (stamp is None or link_stamp is None or
                norm(link.state) not in accepted(c["dishwasher_connected_states"])):
            readings.append(None)
            continue
        value = norm(obj.state)
        if value in accepted(c["dishwasher_running_states"]):
            active = True
        elif value in accepted(c["dishwasher_ready_states"]) | accepted(c["dishwasher_finished_states"]) | {"off"}:
            active = False
        else:
            readings.append(None)
            continue
        oldest = min(stamp, link_stamp)
        readings.append({"value": active, "reported_at": oldest, "valid_until": oldest + max_age})
    known_active = [row for row in readings if row is not None and row["value"] is True]
    usable = known_active or ([row for row in readings if row is not None]
                             if readings and all(row is not None for row in readings) else [])
    if usable:
        context["dishwasher"] = {"value": bool(known_active),
                                 "reported_at": min(row["reported_at"] for row in usable),
                                 "valid_until": min(row["valid_until"] for row in usable)}

    try:
        from homeassistant.helpers import entity_registry as er
        lookup = er.async_get(runtime.hass).async_get
        identity = {"roles": roles, "registry": {
            entity: [getattr(lookup(entity), key, None) for key in
                     ("config_entry_id", "device_id", "unique_id")] for entity in sorted(sources)}}
        binding = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":"),
                                            default=lambda _v: None).encode()).hexdigest()
    except Exception:
        # Values can still be displayed independently; no cross-point pairing
        # may borrow provenance from an unavailable registry.
        binding = None
    return context, sources, binding
