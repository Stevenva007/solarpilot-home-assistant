"""Durable, source-bound minimum OFF time; never a command or ON lease."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math

from .learning import fingerprint


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def rest_binding(runtime, device_id):
    """An unchanged label/ID cannot lend a prior actuator's rest evidence."""
    cfg = runtime.configs.get(device_id)
    if cfg is None:
        return None
    refs = {cfg.get(key) for key in ("control_entity", "number_entity", "active_entity", "power_entity", "start_script", "stop_script")}
    try:
        from homeassistant.helpers import entity_registry as er
        lookup = getattr(er.async_get(runtime.hass), "async_get", lambda _entity: None)
        registry = {}
        for entity in sorted(ref for ref in refs if isinstance(ref, str) and ref):
            row = lookup(entity)
            registry[entity] = [getattr(row, key, None) for key in ("platform", "config_entry_id", "device_id", "unique_id")]
        return hashlib.sha256(json.dumps({"config": fingerprint(cfg), "registry": registry}, sort_keys=True).encode()).hexdigest()
    except (ImportError, AttributeError, TypeError, ValueError, RuntimeError):
        return None


class MinimumRestJournal:
    def __init__(self, runtime):
        self.r = runtime
        self.records = {}
        self._anchors = {}
        self._needs_off = set()
        self._verified_at_wall = None

    def _verified(self, wall):
        # A controller observation advances this proof watermark. Merely
        # projecting/reading a checkpoint must leave its content unchanged.
        self._verified_at_wall = max(wall, self._verified_at_wall or wall)

    def discard(self, device_id):
        changed = device_id in self.records
        self.records.pop(device_id, None)
        self._anchors.pop(device_id, None)
        return changed

    def _unsafe(self, device_id):
        r, st = self.r, self.r.states.get(device_id)
        return (st is None or device_id in r.recovery
            or st.owned and st.target_w > 0
            or r.pending is not None and r.pending.get("id") == device_id
            or r.device_retry.command_waiting(device_id)
            or r.handover is not None and r.handover.device_id == device_id)

    def _off_report(self, device_id):
        r, cfg = self.r, self.r.configs[device_id]
        if r._restart_active(cfg) is not False:
            return False
        if cfg.get("kind") == "dishwasher":
            stamp = _number(getattr(r.dishwasher.readings.get(device_id), "stamp", None))
        else:
            key = "active_entity" if cfg.get("kind") == "script" else "control_entity"
            stamp = r._reported_wall(r.hass.states.get(cfg.get(key)))
        return stamp is not None and stamp > 0

    def note_off(self, device_id, now, wall):
        """Call only for actual OFF feedback/observation, never an OFF intent."""
        st = self.r.states[device_id]
        if _number(now) is None:
            return self.discard(device_id)
        st.last_off = now
        binding = rest_binding(self.r, device_id)
        off_report = self._off_report(device_id)
        if off_report:
            self._needs_off.discard(device_id)
        if binding is None or _number(wall) is None or wall <= 0 or not off_report:
            return self.discard(device_id)
        self.records[device_id] = {"binding": binding, "off_since_wall": float(wall)}
        self._anchors[device_id] = (id(st), now)
        self._verified(wall)
        return True

    def restore(self, data, now, wall, *, blocked=()):
        self.records, self._anchors, self._needs_off = {}, {}, set()
        self._verified_at_wall = None
        if (_number(wall) is None or not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1
                or not isinstance(data.get("devices"), dict)):
            return
        saved = _number(data.get("saved_at_wall"))
        if saved is None or not 0 < saved <= wall:
            return
        for device_id, item in data["devices"].items():
            if device_id not in self.r.states or device_id in blocked or not isinstance(item, dict):
                continue
            off = _number(item.get("off_since_wall"))
            binding = rest_binding(self.r, device_id)
            if (off is None or not 0 < off <= saved or binding is None or item.get("binding") != binding
                    or self._unsafe(device_id)):
                continue
            self.records[device_id] = {"binding": binding, "off_since_wall": off}
        if self.records:
            self._verified_at_wall = saved
        # Restored records have no live anchor. Only a usable original OFF
        # report may rebase them to this process's monotonic clock.

    def observe(self, device_id, active, now, wall):
        if active is True:
            changed = self.discard(device_id) or device_id not in self._needs_off
            self._needs_off.add(device_id)
            return changed
        if _number(now) is None or _number(wall) is None or wall <= 0:
            return False
        record = self.records.get(device_id)
        st = self.r.states[device_id]
        anchor = self._anchors.get(device_id)
        binding = rest_binding(self.r, device_id)
        if record is not None and record["binding"] != binding:
            self.discard(device_id)
            st.last_off = now
            self._needs_off.add(device_id)
            record, anchor = None, None
        if record is not None and anchor is not None and anchor != (id(st), st.last_off):
            self.discard(device_id)
            record, anchor = None, None
        if active is False and device_id in self._needs_off and self._off_report(device_id):
            return self.note_off(device_id, now, wall)
        if active is not False or self._unsafe(device_id) or not self._off_report(device_id):
            return False
        if record is not None:
            off = record["off_since_wall"]
            if off > wall:
                self.discard(device_id)
                return self.note_off(device_id, now, wall)
            if anchor is None:
                rebased = now-(wall-off)
                if not math.isfinite(rebased):
                    return False
                st.last_off = rebased
                self._anchors[device_id] = (id(st), st.last_off)
                self._verified(wall)
                return True
            self._verified(wall)
            return False
        # Preserve today's existing engine baseline, but do not promote it to
        # historical OFF proof. A first-ever usable OFF report may arrive long
        # after startup; only this actual observation can survive a restart.
        if binding is None or _number(st.last_off) is None:
            return False
        self.records[device_id] = {"binding": binding, "off_since_wall": float(wall)}
        self._anchors[device_id] = (id(st), st.last_off)
        self._verified(wall)
        return True

    def snapshot(self, now, wall):
        result = {}
        if _number(now) is None or _number(wall) is None or wall <= 0:
            return {"schema": 1, "saved_at_wall": None, "devices": {}}
        for device_id, record in list(self.records.items()):
            st = self.r.states.get(device_id)
            anchor = self._anchors.get(device_id)
            binding = rest_binding(self.r, device_id)
            if st is None:
                self.discard(device_id)
                continue
            if record["binding"] != binding:
                self.discard(device_id)
                st.last_off = now
                self._needs_off.add(device_id)
                continue
            if anchor is not None and anchor != (id(st), st.last_off):
                self.discard(device_id)
                continue
            if self.r._restart_active(self.r.configs[device_id]) is True:
                self.discard(device_id)
                self._needs_off.add(device_id)
                continue
            # An unsent intent is excluded from its durable checkpoint, but the
            # proven OFF record stays in memory for the existing unsent rollback.
            if self._unsafe(device_id) or not 0 < record["off_since_wall"] <= wall:
                continue
            result[device_id] = deepcopy(record)
        self._needs_off.intersection_update(self.r.states)
        return {"schema": 1, "saved_at_wall": self._verified_at_wall if result else None, "devices": result}
