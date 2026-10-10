"""Read verified Aquarea programme snapshots without fetching or changing them.

The native climate entity collapses AUTO_HEAT/AUTO_COOL to AUTO and hides the
programme while its zone is OFF. The supported Aquarea coordinator exposes the
actual programme in ``device.mode``. It replaces that device on each successful
cloud poll, so an observed successful listener update can prove freshness. A
cached snapshot at setup or an optimistic entity write cannot do so.
"""
from __future__ import annotations

from enum import Enum
import hashlib
import json
import math
import time


_PROGRAMMES = {
    "OFF": (0, "off"),
    "HEAT": (1, "heating"),
    "COOL": (2, "cooling"),
    "AUTO_HEAT": (3, "heating"),
    "AUTO_COOL": (4, "cooling"),
}
_ACTIONS = {"OFF": (0, "off"), "IDLE": (1, "idle"),
            "HEATING": (2, "space_heating"), "COOLING": (3, "space_cooling"),
            "HEATING_WATER": (4, "tapwater_heating")}


def _native_mode(device):
    """Accept the library's specific enum, never its other operation enums."""
    mode = getattr(device, "mode", None)
    kind = type(mode)
    if (not isinstance(mode, Enum) or kind.__name__ != "ExtendedOperationMode"
            or not kind.__module__.startswith("aioaquarea.")):
        return None
    expected = _PROGRAMMES.get(mode.name)
    if (expected is None or isinstance(mode.value, bool)
            or not isinstance(mode.value, int) or mode.value != expected[0]):
        return None
    return mode.name, expected[1]


def _native_action(device):
    """Specific library action enum; this is display context, not control proof."""
    try:
        action = getattr(device, "current_action", None)
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
        return None
    kind = type(action)
    if (not isinstance(action, Enum) or kind.__name__ != "DeviceAction"
            or not kind.__module__.startswith("aioaquarea.")):
        return None
    expected = _ACTIONS.get(action.name)
    if (expected is None or isinstance(action.value, bool)
            or not isinstance(action.value, int) or action.value != expected[0]):
        return None
    return action.name, expected[1]


def _action_inputs(device):
    """Freeze mutable inputs so optimistic valve/mode changes lose poll proof."""
    def frozen(value):
        if isinstance(value, Enum):
            return type(value).__module__, type(value).__name__, value.name, value.value
        return value if value is None or isinstance(value, (str, int, float, bool)) else (type(value).__name__, id(value))
    try:
        tank = getattr(device, "tank", None)
        return tuple(frozen(value) for value in (
            getattr(device, "current_direction", None), getattr(device, "mode", None),
            getattr(device, "operation_status", None), getattr(device, "has_tank", None),
            getattr(device, "device_mode_status", None), getattr(device, "mode_status", None),
            getattr(tank, "operation_status", None)))
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
        return None


class NativeClimateProgram:
    """Small read-only adapter for the registered Aquarea climate provider."""

    def __init__(self, runtime):
        self.runtime = runtime
        self._watches = {}
        # Legacy Aquarea stores coordinators in hass.data, unlike the programme
        # adapter's supported runtime_data binding. Its display-only watcher
        # must not change or revive any programme/control evidence.
        self._tank_watches = {}

    def close(self):
        """Unsubscribe without retaining programme evidence across reloads."""
        watches = {**self._watches, **{("tank", key): value for key, value in self._tank_watches.items()}}
        self._watches, self._tank_watches = {}, {}
        for watch in watches.values():
            self._unsubscribe(watch)

    def _display_identity(self, row):
        """Exact native registry identity, independent of control bindings."""
        from homeassistant.helpers import device_registry as dr
        hass = self.runtime.hass
        if row is None or getattr(row, "platform", None) != "aquarea" or getattr(row, "disabled_by", None) is not None:
            return None
        entry_id, uid = getattr(row, "config_entry_id", None), getattr(row, "unique_id", None)
        entry = hass.config_entries.async_get_entry(entry_id) if isinstance(entry_id, str) else None
        device = dr.async_get(hass).async_get(getattr(row, "device_id", None))
        missing = object()
        owner = getattr(device, "config_entry_id", missing)
        same_entry = (owner == entry_id if owner is not missing else
                      entry_id in getattr(device, "config_entries", ()))
        if (entry is None or getattr(entry, "domain", None) != "aquarea" or device is None
                or not same_entry or not isinstance(uid, str)):
            return None
        matches = [native_id for domain, native_id in getattr(device, "identifiers", ())
                   if domain == "aquarea" and isinstance(native_id, str) and native_id]
        if len(matches) != 1:
            return None
        return entry_id, getattr(row, "device_id", None), matches[0], uid

    def display_sources(self, anchors=()):
        """Find read-only siblings on one exact registered Aquarea device.

        Never persist these sources, rebind SG or choose between installations
        by their entity names. A configured native source anchors the device;
        without one, discovery requires one unambiguous native device group.
        """
        result = {"tank_entity": "", "zone_entities": [], "direction_entity": "",
                  "defrost_entity": "", "automatic": True, "reason": ""}
        try:
            from homeassistant.helpers import entity_registry as er
            registry = er.async_get(self.runtime.hass)
            entities = getattr(registry, "entities", {})
            rows = list(entities.values()) if hasattr(entities, "values") else []
            groups = {}
            for row in rows:
                identity = self._display_identity(row)
                if identity is None:
                    continue
                entry_id, device_id, native_id, uid = identity
                eid = getattr(row, "entity_id", "")
                role = ("tank_entity" if eid.startswith("water_heater.") and uid == f"{native_id}_tank" else
                        "direction_entity" if eid.startswith("sensor.") and uid == f"{native_id}_direction" else
                        "defrost_entity" if eid.startswith("binary_sensor.") and uid == f"{native_id}_defrost" else
                        "zone_entities" if eid.startswith("climate.") and uid.startswith(f"{native_id}_climate_")
                        and uid[len(f"{native_id}_climate_"):].isdigit() else None)
                if role:
                    group = groups.setdefault((entry_id, device_id), {})
                    group.setdefault(role, []).append(eid)
            selected = set()
            for eid in anchors:
                identity = self._display_identity(registry.async_get(eid)) if isinstance(eid, str) else None
                if identity is not None:
                    selected.add(identity[:2])
            if len(selected) > 1 or not selected and len(groups) != 1:
                return {**result, "reason": "Geen eenduidig gekoppeld Panasonic-apparaat voor automatische uitlezing."}
            key = next(iter(selected or groups), None)
            group = groups.get(key, {})
            for role, eids in group.items():
                if role == "zone_entities":
                    result[role] = sorted(eids)
                elif len(eids) == 1:
                    result[role] = eids[0]
            return result
        except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            return result

    def _display_object(self, entity_id):
        obj = self.runtime.hass.states.get(entity_id)
        attrs = getattr(obj, "attributes", {}) or {}
        if (obj is None or str(obj.state).strip().casefold() in ("unknown", "unavailable", "")
                or any(attrs.get(key) for key in ("restored", "estimated", "is_estimated"))):
            return None, None
        stamp = getattr(obj, "last_reported", None) or getattr(obj, "last_updated", None)
        try:
            stamp = stamp.timestamp()
            if isinstance(stamp, bool) or not math.isfinite(stamp) or not -5 <= time.time() - stamp <= self._stale_s():
                return None, None
        except (AttributeError, TypeError, ValueError, OverflowError, OSError):
            return None, None
        return obj, stamp

    def read_tank_context(self, entity_id):
        """Aquarea's WATER/tank report is routing context, never native action.

        Verified Aquarea water_heater implementations report heating from the
        WATER route/current water action. Turning the tank on reports idle.
        This narrow provider context is intentionally not a generic WH mode.
        """
        result = {"function": None, "label": "", "note": "", "source": "none",
                  "kind": "none", "observed_at": None, "stale_s": self._stale_s()}
        try:
            from homeassistant.helpers import entity_registry as er
            if not isinstance(entity_id, str) or not entity_id.startswith("water_heater."):
                return result
            identity = self._display_identity(er.async_get(self.runtime.hass).async_get(entity_id))
            if identity is None or identity[3] != f"{identity[2]}_tank":
                return result
            obj, stamp = self._display_object(entity_id)
            if (obj is None or str(obj.state).strip().casefold() not in ("heating", "heat_pump")
                    or str(obj.attributes.get("operation_mode", "")).strip().casefold() != "heating"):
                return result
            return {**result, "function": "tapwater_heating", "label": "Panasonic meldt tankroute",
                    "note": "Tankroute gemeld; actuele warmteproductie niet afzonderlijk gemeten.",
                    "source": "aquarea_entity", "kind": "tank_route", "observed_at": stamp}
        except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            return result

    def is_display_zone(self, entity_id):
        """Keep a registered space zone from becoming tank display evidence."""
        try:
            from homeassistant.helpers import entity_registry as er
            if not isinstance(entity_id, str) or not entity_id.startswith("climate."):
                return False
            identity = self._display_identity(er.async_get(self.runtime.hass).async_get(entity_id))
            if identity is None:
                return False
            prefix = f"{identity[2]}_climate_"
            return identity[3].startswith(prefix) and identity[3][len(prefix):].isdigit()
        except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            return False

    @staticmethod
    def _unsubscribe(watch):
        unsubscribe = watch.get("unsubscribe")
        if callable(unsubscribe):
            try:
                unsubscribe()
            except (AttributeError, KeyError, ValueError):
                # The native entry may already have removed its listeners.
                pass

    def _prune_entry(self, entry_id, current=(), *, watches=None):
        """Drop replaced coordinators when the native provider reloads."""
        watches = self._watches if watches is None else watches
        current_ids = {id(coordinator) for coordinator in current}
        for key, watch in tuple(watches.items()):
            if watch["entry_id"] == entry_id and key not in current_ids:
                watches.pop(key)
                self._unsubscribe(watch)

    def _resolve(self, entity_id):
        """Match exact registry identity, entry and coordinator device/zone."""
        if not isinstance(entity_id, str) or not entity_id.startswith("climate."):
            return None
        try:
            from homeassistant.helpers import entity_registry as er
            hass = self.runtime.hass
            row = er.async_get(hass).async_get(entity_id)
            if row is None or getattr(row, "platform", None) != "aquarea":
                return None
            entry_id = getattr(row, "config_entry_id", None)
            unique_id = getattr(row, "unique_id", None)
            if not isinstance(entry_id, str) or not isinstance(unique_id, str):
                return None
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is None or getattr(entry, "domain", None) != "aquarea":
                self._prune_entry(entry_id)
                return None
            coordinators = getattr(entry, "runtime_data", None)
            if not isinstance(coordinators, dict):
                self._prune_entry(entry_id)
                return None
            self._prune_entry(entry_id, coordinators.values())
            matches = []
            for device_id, coordinator in coordinators.items():
                if not isinstance(device_id, str) or not device_id:
                    continue
                info = getattr(coordinator, "device_info", None)
                if getattr(info, "device_id", None) != device_id:
                    continue
                device = getattr(coordinator, "device", None)
                if getattr(device, "device_id", None) != device_id:
                    continue
                zones = getattr(device, "zones", None)
                if not isinstance(zones, dict):
                    continue
                if any(unique_id == f"{device_id}_climate_{zone_id}"
                       for zone_id in zones):
                    matches.append(coordinator)
            if len(matches) != 1:
                return None
            # A durable ownership journal can compare this opaque identity
            # across real polls without exporting device or entry identifiers.
            binding_key = hashlib.sha256(json.dumps(
                ["aquarea", entry_id, unique_id], separators=(",", ":")
            ).encode()).hexdigest()
            return matches[0], binding_key, entry_id
        except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            return None

    def _resolve_tank(self, entity_id):
        """Exact native tank registry/device identity for display-only action."""
        if not isinstance(entity_id, str) or not entity_id.startswith("water_heater."):
            return None
        return self._resolve_action(entity_id)

    def _resolve_action(self, entity_id):
        """Display-only device action through an exact tank or zone binding."""
        if not isinstance(entity_id, str) or not entity_id.startswith(("water_heater.", "climate.")):
            return None
        try:
            from homeassistant.helpers import entity_registry as er
            hass = self.runtime.hass
            row = er.async_get(hass).async_get(entity_id)
            if (row is None or getattr(row, "platform", None) != "aquarea"
                    or getattr(row, "disabled_by", None) is not None):
                return None
            obj = hass.states.get(entity_id)
            attrs = getattr(obj, "attributes", {}) or {}
            if (obj is None or str(obj.state).strip().casefold() in ("unknown", "unavailable", "")
                    or any(attrs.get(key) for key in ("restored", "estimated", "is_estimated"))):
                return None
            entry_id, unique_id = getattr(row, "config_entry_id", None), getattr(row, "unique_id", None)
            if not isinstance(entry_id, str) or not isinstance(unique_id, str):
                return None
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is None or getattr(entry, "domain", None) != "aquarea":
                self._prune_entry(entry_id, watches=self._tank_watches)
                return None
            coordinators = getattr(entry, "runtime_data", None)
            if not isinstance(coordinators, dict):
                # Verified cjaliaga Aquarea layout; never inspect unrelated
                # entries, discover devices by name or call a cloud endpoint.
                data = getattr(hass, "data", {})
                provider = data.get("aquarea", {}) if isinstance(data, dict) else {}
                native_entry = provider.get(entry_id, {}) if isinstance(provider, dict) else {}
                coordinators = native_entry.get("devices") if isinstance(native_entry, dict) else None
            if not isinstance(coordinators, dict):
                self._prune_entry(entry_id, watches=self._tank_watches)
                return None
            self._prune_entry(entry_id, coordinators.values(), watches=self._tank_watches)
            matches = []
            for device_id, coordinator in coordinators.items():
                device = getattr(coordinator, "device", None)
                tank_binding = (entity_id.startswith("water_heater.") and unique_id == f"{device_id}_tank"
                                and getattr(device, "has_tank", None) is True
                                and getattr(device, "tank", None) is not None)
                zones = getattr(device, "zones", None)
                zone_binding = (entity_id.startswith("climate.") and isinstance(zones, dict)
                                and any(unique_id == f"{device_id}_climate_{zone_id}" for zone_id in zones))
                if (isinstance(device_id, str) and device_id and (tank_binding or zone_binding)
                        and getattr(getattr(coordinator, "device_info", None), "device_id", None) == device_id
                        and getattr(device, "device_id", None) == device_id):
                    matches.append(coordinator)
            if len(matches) != 1:
                return None
            binding_key = hashlib.sha256(json.dumps(
                ["aquarea_tank", entry_id, unique_id], separators=(",", ":")
            ).encode()).hexdigest()
            return matches[0], binding_key, entry_id
        except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            return None

    def _watch(self, coordinator, entry_id, *, watches=None):
        watches = self._watches if watches is None else watches
        key = id(coordinator)
        if key in watches:
            return watches[key]
        add_listener = getattr(coordinator, "async_add_listener", None)
        if not callable(add_listener):
            return None
        watch = {"coordinator": coordinator, "entry_id": entry_id,
                 "baseline": getattr(coordinator, "device", None),
                 "snapshot": None, "mode": None, "observed": None,
                 "observed_at": None, "unsubscribe": None,
                 "action_snapshot": None, "action": None, "action_inputs": None,
                 "action_observed": None, "action_observed_at": None}

        def updated():
            # Aquarea's supported coordinator replaces Device on each successful
            # poll. A notification of the same mutable object is not poll proof.
            device = getattr(coordinator, "device", None)
            if getattr(coordinator, "last_update_success", None) is not True:
                watch.update(snapshot=None, mode=None, observed=None, observed_at=None)
                watch.update(action_snapshot=None, action=None, action_inputs=None,
                             action_observed=None, action_observed_at=None)
                return
            if device is None or device is watch["baseline"]:
                return
            watch["baseline"] = device
            mode = _native_mode(device)
            watch.update(snapshot=device if mode else None, mode=mode,
                         observed=time.monotonic() if mode else None,
                         observed_at=time.time() if mode else None)
            inputs = _action_inputs(device)
            action = _native_action(device) if inputs is not None else None
            watch.update(action_snapshot=device if action else None, action=action,
                         action_inputs=inputs if action else None,
                         action_observed=time.monotonic() if action else None,
                         action_observed_at=time.time() if action else None)

        try:
            watch["unsubscribe"] = add_listener(updated)
        except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            return None
        watches[key] = watch
        return watch

    def read_tank_action(self, entity_id):
        """Fresh successful provider action used only for task presentation."""
        return self._read_action(entity_id, self._resolve_tank)

    def read_device_action(self, entity_id):
        """The whole device's action can be read through a registered zone.

        An OFF zone does not hide the other zone or a tank task. This uses the
        display watcher, never the programme/controller's source namespace.
        """
        return self._read_action(entity_id, self._resolve_action)

    def _read_action(self, entity_id, resolve):
        result = {"action": "unknown", "raw_action": None, "source": "",
                  "entity_id": entity_id, "fresh": False, "binding_key": None,
                  "observed_at": None}
        resolved = resolve(entity_id)
        if resolved is None:
            return result
        coordinator, result["binding_key"], entry_id = resolved
        result["source"] = "aquarea_poll"
        watch = self._watch(coordinator, entry_id, watches=self._tank_watches)
        if watch is None:
            return result
        if getattr(coordinator, "last_update_success", None) is not True:
            watch.update(action_snapshot=None, action=None, action_inputs=None,
                         action_observed=None, action_observed_at=None)
            return result
        if watch["action_observed"] is None:
            return result
        device = getattr(coordinator, "device", None)
        if (device is not watch["action_snapshot"] or _native_action(device) != watch["action"]
                or _action_inputs(device) != watch["action_inputs"]):
            watch.update(action_snapshot=None, action=None, action_inputs=None,
                         action_observed=None, action_observed_at=None)
            return result
        age = time.monotonic() - watch["action_observed"]
        if not math.isfinite(age) or age < 0 or age > self._stale_s():
            return result
        result.update(action=watch["action"][1], raw_action=watch["action"][0], fresh=True,
                      observed_at=watch["action_observed_at"])
        mode = _native_mode(device)
        if mode is not None and mode == watch["mode"]:
            result.update(program=mode[1], raw_mode=mode[0])
        status = getattr(device, "device_mode_status", None)
        if (isinstance(status, Enum) and type(status).__name__ == "DeviceModeStatus"
                and type(status).__module__.startswith("aioaquarea.")
                and status.name == "DEFROST" and not isinstance(status.value, bool) and status.value == 1):
            result["defrost_active"] = True
        return result

    def _stale_s(self):
        settings = getattr(getattr(self.runtime, "panasonic", None), "settings", {})
        value = settings.get("stale_s", 300) if isinstance(settings, dict) else 300
        if isinstance(value, bool):
            return 300.0
        try:
            seconds = float(value)
        except (TypeError, ValueError, OverflowError):
            return 300.0
        return min(300.0, seconds) if math.isfinite(seconds) and seconds > 0 else 300.0

    def read(self, entity_id):
        """Return only fresh programme evidence from the exact native binding."""
        result = {"program": "unknown", "raw_mode": None, "source": "",
                  "entity_id": entity_id, "fresh": False,
                  "binding_key": None,
                  "reason": "Het gekozen warmtepompprogramma is nog niet betrouwbaar bekend"}
        resolved = self._resolve(entity_id)
        if resolved is None:
            return result
        coordinator, result["binding_key"], entry_id = resolved
        result["source"] = "aquarea_poll"
        watch = self._watch(coordinator, entry_id)
        if watch is None:
            result["reason"] = "De gekozen warmtepomp levert geen controleerbare programmaterugmelding"
            return result
        if getattr(coordinator, "last_update_success", None) is not True:
            watch.update(snapshot=None, mode=None, observed=None, observed_at=None)
            result["reason"] = "De programmaterugmelding van de warmtepomp is tijdelijk niet beschikbaar"
            return result
        if watch["observed"] is None:
            result["reason"] = "Wacht op een nieuwe terugmelding van het gekozen warmtepompprogramma"
            return result
        device = getattr(coordinator, "device", None)
        mode = _native_mode(device)
        if device is not watch["snapshot"] or mode != watch["mode"]:
            watch.update(snapshot=None, mode=None, observed=None, observed_at=None)
            result["reason"] = "Het warmtepompprogramma is gewijzigd; wacht op bevestigde terugmelding"
            return result
        age = time.monotonic() - watch["observed"]
        result["age_s"] = round(age, 3)
        result["observed_at"] = watch["observed_at"]
        if not math.isfinite(age) or age < 0 or age > self._stale_s():
            result["reason"] = "De terugmelding van het gekozen warmtepompprogramma is te oud"
            return result
        result.update(program=mode[1], raw_mode=mode[0], fresh=True, reason="")
        return result
