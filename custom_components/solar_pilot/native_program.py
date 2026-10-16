"""Read verified Aquarea programme snapshots without fetching or changing them.

The native climate entity collapses AUTO_HEAT/AUTO_COOL to AUTO and hides the
programme while its zone is OFF. The supported Aquarea coordinator exposes the
actual programme in ``device.mode``. The modern provider replaces the device;
the verified legacy provider replaces its typed ``DeviceStatus`` instead.
Only a new successful listener update of either supported snapshot proves
freshness. Cached setup data or an optimistic entity write cannot do so.
"""
from __future__ import annotations

from enum import Enum
from dataclasses import fields, is_dataclass
import hashlib
import json
import math
import time
import sys

from .operation_source_evidence import CONTRACT_ID, inspect_loaded_aquarea_semantics, loaded_semantic_identity, valid_semantic_contract


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
_DISPLAY_METADATA_REFRESH_S = 300
_DISPLAY_METADATA_REFRESH_GRACE_S = 30


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


def _native_enum_name(value, kind_name, allowed):
    """Display metadata only, with the same narrow enum contract as actions."""
    kind = type(value)
    if (not isinstance(value, Enum) or kind.__name__ != kind_name
            or not kind.__module__.startswith("aioaquarea.")
            or isinstance(value.value, bool) or not isinstance(value.value, int)
            or allowed.get(value.name) != value.value):
        return None
    return value.name


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


def _status_inputs(status):
    """Freeze the typed library snapshot, including mutable nested fields."""
    def frozen(value, depth=0):
        if depth > 6:
            raise ValueError("Unsupported nested native status")
        if isinstance(value, Enum):
            return type(value).__module__, type(value).__name__, value.name, value.value
        if is_dataclass(value) and not isinstance(value, type):
            return tuple((field.name, frozen(getattr(value, field.name), depth + 1))
                         for field in fields(value))
        if isinstance(value, (list, tuple)) and len(value) <= 100:
            return tuple(frozen(item, depth + 1) for item in value)
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        raise ValueError("Unsupported native status field")
    try:
        return frozen(status)
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
        return None


class NativeClimateProgram:
    """Small read-only adapter for the registered Aquarea climate provider."""

    def __init__(self, runtime):
        self.runtime = runtime
        self._watches = {}
        # Display watchers are deliberately separate: observing a tank task
        # cannot establish fresh programme/controller evidence.
        self._tank_watches = {}
        # The ng 1.3.1 provider refreshes DeviceStatus without rebuilding its
        # DeviceZone objects. This display-only journal observes the current
        # typed status, never the older zone object's status or control proof.
        self._display_contract_watches = {}
        self._display_metadata = {}
        self._display_metadata_module = None
        self._display_semantic_identity = loaded_semantic_identity()
        self._display_metadata_checked = None
        self._display_metadata_task = None
        self._display_closed = False

    async def async_prepare_display_metadata(self):
        """Read actual installed metadata off the event loop; no native fetch.

        This affects only the additional display contract. Entry.version is a
        configuration schema and is deliberately never treated as a release.
        """
        if self._display_closed:
            return
        try:
            from .analysis_export import installed_aquarea_metadata
            executor = getattr(self.runtime.hass, "async_add_executor_job", None)
            if callable(executor):
                loaded = sys.modules.get("custom_components.aquarea")
                semantic_identity = loaded_semantic_identity()
                def inspect_metadata():
                    return {**installed_aquarea_metadata(), **inspect_loaded_aquarea_semantics()}
                metadata = await executor(inspect_metadata)
                if self._display_closed:
                    return
                self._display_metadata = metadata
                self._display_metadata_module = loaded
                self._display_semantic_identity = semantic_identity
                if (loaded is not sys.modules.get("custom_components.aquarea")
                        or semantic_identity != loaded_semantic_identity()):
                    self._display_metadata = {}
            else:
                self._display_metadata = {}
        except (ImportError, OSError, AttributeError, TypeError, ValueError, RuntimeError):
            self._display_metadata = {}
        finally:
            self._display_metadata_checked = time.monotonic()
            self._display_metadata_task = None

    def _contract_metadata(self):
        if self._display_closed:
            return {}
        loaded = sys.modules.get("custom_components.aquarea")
        checked = self._display_metadata_checked
        age = time.monotonic()-checked if checked is not None else None
        same_implementation = (loaded is self._display_metadata_module
                               and self._display_semantic_identity == loaded_semantic_identity())
        current = (checked is not None and age is not None and 0 <= age <= _DISPLAY_METADATA_REFRESH_S
                   and same_implementation)
        if not current and self._display_metadata_task is None:
            create = getattr(self.runtime.hass, "async_create_task", None)
            if callable(create):
                self._display_metadata_task = create(self.async_prepare_display_metadata())
        # Metadata describes the loaded implementation, not a live pump report.
        # Its periodic background reinspection must not insert a false unknown
        # task every five minutes. Only an already verified identical loaded
        # implementation may bridge a bounded in-flight refresh; actual polls,
        # source ages and registry bindings still pass their independent checks.
        refreshing_verified = (same_implementation and self._display_metadata_task is not None
            and age is not None and 0 <= age <= _DISPLAY_METADATA_REFRESH_S+_DISPLAY_METADATA_REFRESH_GRACE_S
            and self._display_metadata.get("integration_loaded") is True
            and valid_semantic_contract(self._display_metadata.get("compatibility")))
        return self._display_metadata if current or refreshing_verified else {}

    def close(self):
        """Unsubscribe without retaining programme evidence across reloads."""
        watches = {**self._watches, **{("tank", key): value for key, value in self._tank_watches.items()},
                   **{("display_contract", key): value for key, value in self._display_contract_watches.items()}}
        self._watches, self._tank_watches = {}, {}
        self._display_contract_watches = {}
        self._display_closed = True
        if self._display_metadata_task is not None:
            self._display_metadata_task.cancel()
            self._display_metadata_task = None
        self._display_metadata = {}
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
                  "defrost_entity": "", "pump_status_entity": "", "automatic": True, "reason": ""}
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
                        "pump_status_entity" if eid.startswith("sensor.") and uid == f"{native_id}_pump_status" else
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

    def read_source_contract(self, sources):
        """Separate read-only evidence for the verified specialStatus mapping.

        The registered pump_status role and typed PumpDuty agree on the same
        native device. Its ON value is water-pump duty, never compressor proof.
        The original raw DeviceAction and existing control adapter stay intact.
        """
        metadata = self._contract_metadata()
        metadata = metadata if isinstance(metadata, dict) else {}
        provider = {key: metadata.get(key) for key in ("integration_domain", "integration_version", "library_distribution", "library_version")}
        known = (metadata.get("integration_loaded") is True and provider["integration_domain"] == "aquarea"
                 and valid_semantic_contract(metadata.get("compatibility")))
        result = {"schema": 1, "read_only": True, "status": "unknown", "provider": provider,
                  "contract_id": CONTRACT_ID if known else None,
                  "action_semantics": "special_status" if known else "unknown", "source": "aquarea_contract",
                  "provider_loaded": metadata.get("integration_loaded") is True, "native_device_registered": False,
                  "compatibility": dict(metadata["compatibility"]) if known else None,
                  "compatibility_state": "compatible" if known else metadata.get("compatibility_state", "unknown"),
                  "compatibility_detail": metadata.get("compatibility_detail"),
                  "reason_code": metadata.get("reason_code", "provider_semantics_unavailable") if not known else "known_special_status_action_mapping",
                  "stale_s": self._stale_s(),
                  "reason": ("De betekenis of opbouw van de geladen Aquarea-statusbron is gewijzigd."
                             if metadata.get("reason_code") == "provider_semantics_changed" else
                             "De betekenis van de geladen Aquarea-statusbron kon niet gecontroleerd worden.") if not known else "",
                  "action": ("Laat de gewijzigde bronmapping controleren; de bestaande taakgegevens blijven afzonderlijk bewaard."
                             if metadata.get("reason_code") == "provider_semantics_changed" else
                             "Controleer de broncompatibiliteit; een versienummer alleen is geen reden om de bron te blokkeren.") if not known else "",
                  "observed_at": None, "raw_device_action": None,
                  "pump": {"state": "unknown", "observed_at": None}, "direction": {"state": None, "observed_at": None},
                  "program": {"state": None, "observed_at": None}, "tank": {"enabled": None, "observed_at": None}, "zones": []}
        try:
            from homeassistant.helpers import entity_registry as er
            if not isinstance(sources, dict):
                return {**result, "reason_code": "native_source_mapping_unverified"}
            zones = list(sources["zone_entities"]) if isinstance(sources.get("zone_entities"), list) else []
            tank_id, pump_id, direction_id = (sources.get(key, "") for key in ("tank_entity", "pump_status_entity", "direction_entity"))
            anchor = tank_id or next(iter(zones), "")
            registry = er.async_get(self.runtime.hass)
            identity = self._display_identity(registry.async_get(anchor))
            if identity is None:
                return {**result, "reason_code": "native_source_mapping_unverified"}
            result["native_device_registered"] = True
            if not known:
                return result
            required_ids = [pump_id, direction_id, *zones, *([tank_id] if tank_id else [])]
            if (not pump_id or not direction_id or not zones
                    or any(self._display_identity(registry.async_get(eid)) is None
                           or self._display_identity(registry.async_get(eid))[:3] != identity[:3] for eid in required_ids)):
                return {**result, "reason_code": "native_source_mapping_unverified"}
            for eid, suffix in ((pump_id, "pump_status"), (direction_id, "direction")):
                if self._display_identity(registry.async_get(eid))[3] != f"{identity[2]}_{suffix}":
                    return {**result, "reason_code": "native_source_mapping_unverified"}
            original_bindings = {eid: self._display_identity(registry.async_get(eid)) for eid in required_ids}
            resolved = self._resolve_action(anchor)
            if resolved is None:
                return {**result, "reason_code": "native_source_mapping_unverified"}
            coordinator, _, entry_id = resolved
            entry = self.runtime.hass.config_entries.async_get_entry(entry_id)
            device = coordinator.device
            # A reloaded SDK can coexist briefly with a coordinator retaining
            # an older same-named class. Its old getters cannot borrow new proof.
            if metadata.get("_loaded_device_class") is not type(device):
                return {**result, "reason_code": "native_loaded_device_type_changed",
                        "reason": "De warmtepompbron gebruikt nog een eerdere geladen bronklasse.",
                        "action": "Wacht op een nieuwe passende providerpoll; oude objecten krijgen geen nieuw bronbewijs."}
            def exact_enum(value, name, values):
                return _native_enum_name(value, name, values) if type(value).__module__ == "aioaquarea.data" else None
            modern = isinstance(getattr(entry, "runtime_data", None), dict)
            if modern:
                # The upstream coordinator fetches status A in get_device(),
                # then refreshes to B. DeviceZone._status still references A.
                # Read only the exact device's current typed B generation;
                # do not relax the shared legacy/control programme adapter.
                coordinators = entry.runtime_data
                self._prune_entry(entry_id, coordinators.values(), watches=self._display_contract_watches)
                proof = self._read_display_snapshot(coordinator, entry, entry_id)
                if proof.get("fresh") is not True:
                    return {**result, "reason_code": proof["reason_code"],
                            "observed_at": proof.get("observed_at")}
                original = proof["observed_at"]
                snapshot = proof["values"]
                pump, direction, mode = snapshot["pump"], snapshot["direction"], snapshot["mode"]
                tank_enabled, enabled_zones = snapshot["tank_enabled"], dict(snapshot["zones"])
                raw_action = snapshot["raw_action"]
            else:
                status = self._legacy_status(coordinator, entry)
                if status is None:
                    return {**result, "reason_code": "native_typed_snapshot_unverified"}
                action = self._read_action(anchor, self._resolve_action)
                if action.get("fresh") is not True:
                    watch = self._tank_watches.get(id(coordinator), {})
                    return {**result, "reason_code": "native_poll_not_current",
                            "observed_at": watch.get("action_observed_at")}
                original = action["observed_at"]
                pump = exact_enum(getattr(device, "pump_duty", None), "PumpDuty", {"OFF": 0, "ON": 1})
                direction = exact_enum(getattr(device, "current_direction", None), "DeviceDirection", {"IDLE": 0, "PUMP": 1, "WATER": 2})
                mode = _native_mode(device) if type(getattr(device, "mode", None)).__module__ == "aioaquarea.data" else None
                tank_enabled = exact_enum(getattr(getattr(device, "tank", None), "operation_status", None),
                                          "OperationStatus", {"OFF": 0, "ON": 1, "UNKNOWN": 2}) if device.has_tank else None
                enabled_zones = {number: exact_enum(getattr(zone, "operation_status", None), "OperationStatus",
                                                    {"OFF": 0, "ON": 1, "UNKNOWN": 2})
                                 for number, zone in device.zones.items()}
                raw_action = action.get("raw_action")
            if pump is None or direction is None or mode is None:
                return {**result, "reason_code": "native_typed_value_unverified"}
            pump_obj, pump_time = self._display_object(pump_id)
            direction_obj, direction_time = self._display_object(direction_id)
            pump_state = str(pump_obj.state).strip().casefold() if pump_obj else None
            direction_state = str(direction_obj.state).strip().upper() if direction_obj else None
            if pump_obj is None or direction_obj is None:
                return {**result, "reason_code": "native_source_not_current",
                        "observed_at": original,
                        "pump": {"state": "unknown", "entity_id": pump_id, "observed_at": self._display_report_time(pump_id)},
                        "direction": {"state": None, "entity_id": direction_id, "observed_at": self._display_report_time(direction_id)}}
            if pump_state != pump.casefold() or direction_state != direction:
                return {**result, "reason_code": "native_source_value_conflict"}
            zone_rows = []
            bound_zones = set()
            for eid in zones:
                uid = self._display_identity(registry.async_get(eid))[3]
                prefix = f"{identity[2]}_climate_"
                zone_number = int(uid[len(prefix):]) if uid.startswith(prefix) and uid[len(prefix):].isdigit() else None
                enabled = enabled_zones.get(zone_number)
                obj, report_time = self._display_object(eid)
                bound_zones.add(zone_number)
                if modern:
                    if obj is None:
                        return {**result, "reason_code": "native_zone_source_not_current", "observed_at": original}
                    expected = ("off" if enabled == "OFF" or mode[0] == "OFF" else
                                {"HEAT": "heat", "COOL": "cool", "AUTO_HEAT": "auto", "AUTO_COOL": "auto"}.get(mode[0])
                                if enabled == "ON" else None)
                    if expected is None or str(obj.state).casefold() != expected:
                        return {**result, "reason_code": "native_zone_source_value_conflict", "observed_at": original}
                zone_rows.append({"entity_id": eid, "enabled": True if enabled == "ON" else False if enabled == "OFF" else None,
                                  "observed_at": report_time if report_time is not None else self._display_report_time(eid), "native_observed_at": original,
                                  "state": str(obj.state).casefold() if obj else None})
            if modern:
                if bound_zones != set(enabled_zones):
                    return {**result, "reason_code": "native_display_zone_binding_unverified", "observed_at": original}
                current_registry = er.async_get(self.runtime.hass)
                if (self.runtime.hass.config_entries.async_get_entry(entry_id) is not entry
                        or any(self._display_identity(current_registry.async_get(eid)) != binding
                               for eid, binding in original_bindings.items())):
                    watch = self._display_contract_watches.get(id(coordinator))
                    if watch is not None:
                        watch.update(snapshot=None, observed=None, observed_at=None)
                    return {**result, "reason_code": "native_display_binding_changed", "observed_at": original}
                latest_proof = self._read_display_snapshot(coordinator, entry, entry_id)
                if latest_proof.get("fresh") is not True or latest_proof.get("generation") != proof["generation"]:
                    return {**result, "reason_code": latest_proof.get("reason_code") or "native_display_snapshot_changed", "observed_at": original}
            return {**result, "status": "verified", "reason_code": "known_special_status_action_mapping",
                    "observed_at": original, "raw_device_action": raw_action,
                    "pump": {"state": pump_state, "entity_id": pump_id, "observed_at": pump_time, "native_observed_at": original},
                    "direction": {"state": direction, "entity_id": direction_id, "observed_at": direction_time, "native_observed_at": original},
                    "program": {"state": mode[1], "raw_mode": mode[0], "observed_at": original},
                    "tank": {"enabled": True if tank_enabled == "ON" else False if tank_enabled == "OFF" else None,
                             "entity_id": tank_id, "observed_at": original}, "zones": zone_rows,
                    "note": "Deze SDK leidt DeviceAction af via specialStatus; geen onafhankelijke hoofd-AAN/UIT-meting. PumpDuty is waterpompbedrijf."}
        except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            return {**result, "reason_code": "native_source_mapping_unverified"}

    def _display_snapshot(self, coordinator, entry):
        """Immutable current ng 1.3.1 status values for display only.

        Its coordinator refreshes the status twice and leaves zone objects
        referencing the first response. Their own info still proves device
        ownership; all displayed zone values come from the second response.
        The stricter legacy/control verifier deliberately stays unchanged.
        """
        kind = type(coordinator)
        if (kind.__module__ != "custom_components.aquarea.coordinator"
                or kind.__name__ != "AquareaDataUpdateCoordinator"
                or getattr(coordinator, "_entry", None) is not entry
                or getattr(coordinator, "hass", None) is not self.runtime.hass):
            return None, "native_display_binding_unverified"
        device = getattr(coordinator, "device", None)
        if type(device).__module__ != "aioaquarea.entities" or type(device).__name__ != "DeviceImpl":
            return None, "native_display_device_type_unverified"
        info, own = getattr(coordinator, "_device_info", None), getattr(device, "_info", None)
        status = getattr(device, "_status", None)
        if any(type(value).__module__ != "aioaquarea.data" or type(value).__name__ != name
               or not is_dataclass(value) or isinstance(value, type)
               for value, name in ((info, "DeviceInfo"), (own, "DeviceInfo"), (status, "DeviceStatus"))):
            return None, "native_display_status_type_unverified"
        expected_fields = {"long_id", "operation_status", "device_status", "temperature_outdoor", "operation_mode",
                           "fault_status", "direction", "pump_duty", "tank_status", "zones", "quiet_mode", "force_dhw",
                           "force_heater", "holiday_timer", "powerful_time", "special_status", "water_pressure"}
        frozen = _status_inputs(status)
        if {field.name for field in fields(status)} != expected_fields or frozen is None:
            return None, "native_display_status_shape_unverified"
        native_id, long_id = getattr(info, "device_id", None), getattr(info, "long_id", None)
        owners = getattr(entry, "runtime_data", None)
        if (not isinstance(native_id, str) or not native_id or not isinstance(long_id, str) or not long_id
                or not isinstance(owners, dict) or owners.get(native_id) is not coordinator
                or getattr(device, "device_id", None) != native_id or getattr(own, "device_id", None) != native_id
                or getattr(own, "long_id", None) != long_id or getattr(device, "long_id", None) != long_id
                or getattr(status, "long_id", None) != long_id):
            return None, "native_display_identity_unverified"
        zone_sets = []
        for owner, name in ((info, "DeviceZoneInfo"), (own, "DeviceZoneInfo"), (status, "DeviceZoneStatus")):
            rows = getattr(owner, "zones", None)
            if (not isinstance(rows, list) or not rows or len(rows) > 100
                    or any(type(row).__module__ != "aioaquarea.data" or type(row).__name__ != name
                           or not is_dataclass(row) or isinstance(row, type)
                           or isinstance(getattr(row, "zone_id", None), bool)
                           or not isinstance(getattr(row, "zone_id", None), int) or row.zone_id <= 0 for row in rows)
                    or len({row.zone_id for row in rows}) != len(rows)):
                return None, "native_display_zone_binding_unverified"
            zone_sets.append({row.zone_id for row in rows})
        objects = getattr(device, "zones", None)
        if (zone_sets[0] != zone_sets[1] or zone_sets[0] != zone_sets[2] or not isinstance(objects, dict)
                or any(isinstance(key, bool) or not isinstance(key, int) for key in objects)
                or set(objects) != zone_sets[0]):
            return None, "native_display_zone_binding_unverified"
        for number, zone in objects.items():
            owner_info = next(row for row in own.zones if row.zone_id == number)
            if (type(zone).__module__ != "aioaquarea.data" or type(zone).__name__ != "DeviceZone"
                    or getattr(zone, "zone_id", None) != number or getattr(zone, "_info", None) is not owner_info):
                # The old library uses a shared zone dictionary. A neighbor's
                # zone object cannot establish even a display device binding.
                return None, "native_display_zone_binding_unverified"
        has_tank = getattr(own, "has_tank", None)
        if not isinstance(has_tank, bool) or getattr(info, "has_tank", None) is not has_tank or device.has_tank is not has_tank:
            return None, "native_display_tank_binding_unverified"
        tank_rows, tank = getattr(status, "tank_status", None), getattr(device, "tank", None)
        if not isinstance(tank_rows, list):
            return None, "native_display_tank_binding_unverified"
        if has_tank:
            if (len(tank_rows) != 1 or type(tank).__module__ != "aioaquarea.entities" or type(tank).__name__ != "TankImpl"
                    or type(tank_rows[0]).__module__ != "aioaquarea.data" or type(tank_rows[0]).__name__ != "TankStatus"
                    or getattr(tank, "_device", None) is not device or getattr(tank, "_status", None) is not tank_rows[0]):
                return None, "native_display_tank_binding_unverified"
        elif tank_rows or tank is not None:
            return None, "native_display_tank_binding_unverified"
        def exact(value, name, allowed):
            return _native_enum_name(value, name, allowed) if type(value).__module__ == "aioaquarea.data" else None
        mode, action = _native_mode(device), _native_action(device)
        pump = exact(status.pump_duty, "PumpDuty", {"OFF": 0, "ON": 1})
        direction = exact(status.direction, "DeviceDirection", {"IDLE": 0, "PUMP": 1, "WATER": 2})
        tank_enabled = exact(tank_rows[0].operation_status, "OperationStatus", {"OFF": 0, "ON": 1, "UNKNOWN": 2}) if has_tank else None
        zones = tuple((row.zone_id, exact(row.operation_status, "OperationStatus", {"OFF": 0, "ON": 1, "UNKNOWN": 2}))
                      for row in status.zones)
        if (mode is None or action is None or type(device.mode).__module__ != "aioaquarea.data"
                or type(device.current_action).__module__ != "aioaquarea.data" or pump is None or direction is None
                or has_tank and tank_enabled is None or any(value is None for _number, value in zones)):
            return None, "native_display_values_unverified"
        values = {"pump": pump, "direction": direction, "mode": mode, "tank_enabled": tank_enabled,
                  "zones": zones, "raw_action": action[0]}
        generation = (id(device), id(status), id(info), id(own), native_id, long_id, frozen,
                      tuple((number, id(zone), id(zone._info)) for number, zone in sorted(objects.items())), id(tank))
        return {"generation": generation, "values": values}, ""

    def _read_display_snapshot(self, coordinator, entry, entry_id):
        """A successful new provider generation, separate from control watches."""
        key = id(coordinator)
        watch = self._display_contract_watches.get(key)
        device = getattr(coordinator, "device", None)
        identity = (id(device), id(getattr(device, "_status", None)))
        if self.runtime.hass.config_entries.async_get_entry(entry_id) is not entry:
            if watch is not None:
                watch.update(snapshot=None, observed=None, observed_at=None, baseline=None, baseline_ids=identity)
            return {"fresh": False, "reason_code": "native_display_binding_changed", "observed_at": None}
        try:
            snapshot, reason = self._display_snapshot(coordinator, entry)
        except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            snapshot, reason = None, "native_display_status_shape_unverified"
        if snapshot is None:
            if watch is not None:
                watch.update(snapshot=None, observed=None, observed_at=None, baseline=None, baseline_ids=identity)
            return {"fresh": False, "reason_code": reason, "observed_at": None}
        if watch is None:
            add_listener = getattr(coordinator, "async_add_listener", None)
            if not callable(add_listener):
                return {"fresh": False, "reason_code": "native_display_listener_unavailable", "observed_at": None}
            watch = {"coordinator": coordinator, "entry_id": entry_id, "baseline": snapshot["generation"], "baseline_ids": identity,
                     "snapshot": None, "observed": None, "observed_at": None, "unsubscribe": None}
            def updated():
                current_device = getattr(coordinator, "device", None)
                current_ids = (id(current_device), id(getattr(current_device, "_status", None)))
                try:
                    current, _reason = self._display_snapshot(coordinator, entry)
                except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
                    current = None
                if (self.runtime.hass.config_entries.async_get_entry(entry_id) is not entry
                        or getattr(coordinator, "last_update_success", None) is not True or current is None):
                    watch.update(snapshot=None, observed=None, observed_at=None,
                                 baseline=current["generation"] if current else None, baseline_ids=current_ids)
                    return
                # An unchanged listener event or in-place mutation is not a
                # new network response. The device or typed status must change.
                previous = watch["baseline"]
                generation = current["generation"]
                if current_ids == watch["baseline_ids"]:
                    if generation != previous:
                        watch.update(snapshot=None, observed=None, observed_at=None, baseline=generation, baseline_ids=current_ids)
                    return
                watch.update(baseline=generation, baseline_ids=current_ids, snapshot=current,
                             observed=time.monotonic(), observed_at=time.time())
            try:
                watch["unsubscribe"] = add_listener(updated)
            except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
                return {"fresh": False, "reason_code": "native_display_listener_unavailable", "observed_at": None}
            self._display_contract_watches[key] = watch
        if getattr(coordinator, "last_update_success", None) is not True:
            watch.update(snapshot=None, observed=None, observed_at=None, baseline=snapshot["generation"], baseline_ids=identity)
            return {"fresh": False, "reason_code": "native_poll_unavailable", "observed_at": None}
        accepted = watch["snapshot"]
        if accepted is not None and accepted["generation"] != snapshot["generation"]:
            watch.update(snapshot=None, observed=None, observed_at=None, baseline=snapshot["generation"], baseline_ids=identity)
            return {"fresh": False, "reason_code": "native_display_snapshot_changed", "observed_at": None}
        age = time.monotonic()-watch["observed"] if watch["observed"] is not None else None
        if accepted is None or age is None or not math.isfinite(age) or not 0 <= age <= self._stale_s():
            watch.update(snapshot=None, observed=None, baseline=snapshot["generation"], baseline_ids=identity)
            return {"fresh": False, "reason_code": "native_poll_not_current", "observed_at": watch["observed_at"]}
        return {"fresh": True, "reason_code": "", "observed_at": watch["observed_at"],
                "generation": accepted["generation"], "values": dict(accepted["values"])}

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

    def _display_report_time(self, entity_id):
        """Keep an original diagnostic timestamp even when its value is old."""
        obj = self.runtime.hass.states.get(entity_id)
        value = getattr(obj, "last_reported", None) or getattr(obj, "last_updated", None)
        try:
            stamp = value.timestamp()
            return stamp if not isinstance(stamp, bool) and math.isfinite(stamp) and stamp > 0 else None
        except (AttributeError, TypeError, ValueError, OverflowError, OSError):
            return None

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

    def _legacy_coordinators(self, entry_id):
        """Read only the verified legacy provider's exact entry namespace."""
        data = getattr(self.runtime.hass, "data", {})
        provider = data.get("aquarea", {}) if isinstance(data, dict) else {}
        native_entry = provider.get(entry_id, {}) if isinstance(provider, dict) else {}
        return native_entry.get("devices") if isinstance(native_entry, dict) else None

    def _legacy_status(self, coordinator, entry):
        """Narrow cjaliaga coordinator/library identity, without importing it.

        The pinned 0.7.2 library implements DeviceImpl in aioaquarea.core; the
        later verified library implements it in aioaquarea.entities. Both keep
        Device and replace DeviceStatus from refresh_data(). Unknown shapes
        never gain programme permission through this compatibility route.
        """
        kind = type(coordinator)
        if (kind.__module__ != "custom_components.aquarea.coordinator"
                or kind.__name__ != "AquareaDataUpdateCoordinator"
                or getattr(coordinator, "_entry", None) is not entry
                or getattr(coordinator, "hass", None) is not self.runtime.hass):
            return None
        device = getattr(coordinator, "device", None)
        kind = type(device)
        if (kind.__module__ not in ("aioaquarea.core", "aioaquarea.entities")
                or kind.__name__ != "DeviceImpl"):
            return None
        info, native_info = getattr(coordinator, "_device_info", None), getattr(device, "_info", None)
        status = getattr(device, "_status", None)
        if any(type(value).__module__ != "aioaquarea.data" or type(value).__name__ != name
               for value, name in ((info, "DeviceInfo"), (native_info, "DeviceInfo"),
                                   (status, "DeviceStatus"))):
            return None
        native_id, long_id = getattr(info, "device_id", None), getattr(info, "long_id", None)
        if (not isinstance(native_id, str) or not native_id or not isinstance(long_id, str) or not long_id
                or getattr(device, "device_id", None) != native_id
                or getattr(native_info, "device_id", None) != native_id
                or getattr(native_info, "long_id", None) != long_id
                or getattr(device, "long_id", None) != long_id
                or getattr(status, "long_id", None) != long_id
                or not is_dataclass(status) or _status_inputs(status) is None):
            return None
        zones = getattr(device, "zones", None)
        if not isinstance(zones, dict) or not zones:
            return None
        zone_ids = set(zones)
        if any(isinstance(zone_id, bool) or not isinstance(zone_id, int) or zone_id <= 0
               or type(zone).__module__ != "aioaquarea.data" or type(zone).__name__ != "DeviceZone"
               or getattr(zone, "zone_id", None) != zone_id for zone_id, zone in zones.items()):
            return None
        for owner, name in ((info, "DeviceZoneInfo"), (native_info, "DeviceZoneInfo"),
                            (status, "DeviceZoneStatus")):
            rows = getattr(owner, "zones", None)
            if (not isinstance(rows, list) or len(rows) != len(zone_ids)
                    or any(type(row).__module__ != "aioaquarea.data" or type(row).__name__ != name
                           or isinstance(getattr(row, "zone_id", None), bool)
                           or not isinstance(getattr(row, "zone_id", None), int) for row in rows)
                    or {row.zone_id for row in rows} != zone_ids):
                return None
        for zone_id, zone in zones.items():
            own_info = next(row for row in native_info.zones if row.zone_id == zone_id)
            own_status = next(row for row in status.zones if row.zone_id == zone_id)
            if (getattr(zone, "_info", None) is not own_info
                    or getattr(zone, "_status", None) is not own_status):
                # Older library versions share a class-level zone dictionary.
                # A neighboring device's zone must not establish this binding.
                return None
        has_tank = getattr(native_info, "has_tank", None)
        if (not isinstance(has_tank, bool) or getattr(info, "has_tank", None) is not has_tank
                or getattr(device, "has_tank", None) is not has_tank):
            return None
        if has_tank:
            tank, rows = getattr(device, "tank", None), getattr(status, "tank_status", None)
            if (type(tank).__module__ not in ("aioaquarea.core", "aioaquarea.entities")
                    or type(tank).__name__ != "TankImpl" or not isinstance(rows, list) or not rows
                    or type(rows[0]).__module__ != "aioaquarea.data" or type(rows[0]).__name__ != "TankStatus"
                    or getattr(tank, "_device", None) is not device
                    or getattr(tank, "_status", None) is not rows[0]):
                return None
        return status

    def _current_legacy_status(self, coordinator, entry_id):
        try:
            entry = self.runtime.hass.config_entries.async_get_entry(entry_id)
            return self._legacy_status(coordinator, entry) if entry is not None else None
        except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            return None

    def _resolve(self, entity_id):
        """Match exact registry identity, entry and coordinator device/zone."""
        if not isinstance(entity_id, str) or not entity_id.startswith("climate."):
            return None
        try:
            from homeassistant.helpers import entity_registry as er
            hass = self.runtime.hass
            row = er.async_get(hass).async_get(entity_id)
            if (row is None or getattr(row, "platform", None) != "aquarea"
                    or getattr(row, "disabled_by", None) is not None):
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
            legacy = not isinstance(coordinators, dict)
            if legacy:
                coordinators = self._legacy_coordinators(entry_id)
            if not isinstance(coordinators, dict):
                self._prune_entry(entry_id)
                return None
            self._prune_entry(entry_id, coordinators.values())
            matches = []
            for device_id, coordinator in coordinators.items():
                if not isinstance(device_id, str) or not device_id:
                    continue
                if legacy and self._legacy_status(coordinator, entry) is None:
                    continue
                info = getattr(coordinator, "_device_info" if legacy else "device_info", None)
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
                self._prune_entry(entry_id)
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
                coordinators = self._legacy_coordinators(entry_id)
            if not isinstance(coordinators, dict):
                self._prune_entry(entry_id, watches=self._tank_watches)
                return None
            self._prune_entry(entry_id, coordinators.values(), watches=self._tank_watches)
            matches = []
            for device_id, coordinator in coordinators.items():
                device = getattr(coordinator, "device", None)
                info = getattr(coordinator, "device_info", None)
                if info is None and self._legacy_status(coordinator, entry) is not None:
                    info = getattr(coordinator, "_device_info", None)
                tank_binding = (entity_id.startswith("water_heater.") and unique_id == f"{device_id}_tank"
                                and getattr(device, "has_tank", None) is True
                                and getattr(device, "tank", None) is not None)
                zones = getattr(device, "zones", None)
                zone_binding = (entity_id.startswith("climate.") and isinstance(zones, dict)
                                and any(unique_id == f"{device_id}_climate_{zone_id}" for zone_id in zones))
                if (isinstance(device_id, str) and device_id and (tank_binding or zone_binding)
                        and getattr(info, "device_id", None) == device_id
                        and getattr(device, "device_id", None) == device_id):
                    matches.append(coordinator)
            if len(matches) != 1:
                self._prune_entry(entry_id, watches=self._tank_watches)
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
                 "legacy": self._current_legacy_status(coordinator, entry_id) is not None,
                 "status_baseline": self._current_legacy_status(coordinator, entry_id),
                 "status_snapshot": None, "status_inputs": None,
                 "snapshot": None, "mode": None, "observed": None,
                 "observed_at": None, "unsubscribe": None,
                 "action_snapshot": None, "action": None, "action_inputs": None,
                 "action_observed": None, "action_observed_at": None}

        def updated():
            # Successful replacement is required. The legacy library replaces
            # its typed status; modern coordinators replace the whole Device.
            device = getattr(coordinator, "device", None)
            status = self._current_legacy_status(coordinator, entry_id) if watch["legacy"] else None
            if getattr(coordinator, "last_update_success", None) is not True:
                watch.update(baseline=device, status_baseline=status,
                             status_snapshot=None, status_inputs=None)
                watch.update(snapshot=None, mode=None, observed=None, observed_at=None)
                watch.update(action_snapshot=None, action=None, action_inputs=None,
                             action_observed=None, action_observed_at=None)
                return
            changed = (status is not None and status is not watch["status_baseline"]
                       if watch["legacy"] else device is not watch["baseline"])
            if device is None or not changed:
                return
            watch["baseline"] = device
            watch["status_baseline"] = status
            watch["status_snapshot"] = status
            watch["status_inputs"] = _status_inputs(status) if status is not None else None
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
            watch.update(baseline=getattr(coordinator, "device", None),
                         status_baseline=self._current_legacy_status(coordinator, entry_id))
            watch.update(action_snapshot=None, action=None, action_inputs=None,
                         action_observed=None, action_observed_at=None)
            return result
        if watch["action_observed"] is None:
            return result
        device = getattr(coordinator, "device", None)
        if (device is not watch["action_snapshot"] or _native_action(device) != watch["action"]
                or _action_inputs(device) != watch["action_inputs"]
                or watch["legacy"] and (self._current_legacy_status(coordinator, entry_id) is not watch["status_snapshot"]
                                        or _status_inputs(watch["status_snapshot"]) != watch["status_inputs"])):
            watch.update(baseline=device, status_baseline=self._current_legacy_status(coordinator, entry_id))
            watch.update(action_snapshot=None, action=None, action_inputs=None,
                         action_observed=None, action_observed_at=None)
            return result
        age = time.monotonic() - watch["action_observed"]
        if not math.isfinite(age) or age < 0 or age > self._stale_s():
            return result
        result.update(action=watch["action"][1], raw_action=watch["action"][0], fresh=True,
                      observed_at=watch["action_observed_at"])
        # The library checks main operation_status before WATER/tank status
        # when deriving DeviceAction.OFF. Preserve those independent native
        # fields; OFF alone does not establish that an enabled tank is OFF.
        # These use the display watcher and never amend programme/SG evidence.
        result["operation_status"] = _native_enum_name(getattr(device, "operation_status", None),
            "OperationStatus", {"OFF": 0, "ON": 1, "UNKNOWN": 2})
        result["direction"] = _native_enum_name(getattr(device, "current_direction", None),
            "DeviceDirection", {"IDLE": 0, "PUMP": 1, "WATER": 2})
        has_tank = getattr(device, "has_tank", None)
        result["has_tank"] = has_tank if isinstance(has_tank, bool) else None
        result["tank_operation_status"] = _native_enum_name(
            getattr(getattr(device, "tank", None), "operation_status", None),
            "OperationStatus", {"OFF": 0, "ON": 1, "UNKNOWN": 2}) if has_tank is True else None
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
                  "reason_code": "unsupported_binding", "stale_s": self._stale_s(),
                  "reason": "Het gekozen warmtepompprogramma is nog niet betrouwbaar bekend"}
        resolved = self._resolve(entity_id)
        if resolved is None:
            return result
        coordinator, result["binding_key"], entry_id = resolved
        result["source"] = "aquarea_poll"
        watch = self._watch(coordinator, entry_id)
        if watch is None:
            result["reason_code"] = "listener_unavailable"
            result["reason"] = "De gekozen warmtepomp levert geen controleerbare programmaterugmelding"
            return result
        if getattr(coordinator, "last_update_success", None) is not True:
            watch.update(baseline=getattr(coordinator, "device", None),
                         status_baseline=self._current_legacy_status(coordinator, entry_id))
            watch.update(snapshot=None, mode=None, observed=None, observed_at=None)
            result["reason"] = "De programmaterugmelding van de warmtepomp is tijdelijk niet beschikbaar"
            result["reason_code"] = "poll_unavailable"
            return result
        if watch["observed"] is None:
            result["reason"] = "Wacht op een nieuwe terugmelding van het gekozen warmtepompprogramma"
            result["reason_code"] = "awaiting_poll"
            return result
        device = getattr(coordinator, "device", None)
        mode = _native_mode(device)
        if (device is not watch["snapshot"] or mode != watch["mode"]
                or watch["legacy"] and (self._current_legacy_status(coordinator, entry_id) is not watch["status_snapshot"]
                                        or _status_inputs(watch["status_snapshot"]) != watch["status_inputs"])):
            watch.update(baseline=device, status_baseline=self._current_legacy_status(coordinator, entry_id))
            watch.update(snapshot=None, mode=None, observed=None, observed_at=None)
            result["reason"] = "Het warmtepompprogramma is gewijzigd; wacht op bevestigde terugmelding"
            result["reason_code"] = "unconfirmed_change"
            return result
        age = time.monotonic() - watch["observed"]
        result["age_s"] = round(age, 3)
        result["observed_at"] = watch["observed_at"]
        if not math.isfinite(age) or age < 0 or age > self._stale_s():
            result["reason"] = "De terugmelding van het gekozen warmtepompprogramma is te oud"
            result["reason_code"] = "stale_poll"
            return result
        result.update(program=mode[1], raw_mode=mode[0], fresh=True, reason="", reason_code="confirmed")
        return result
