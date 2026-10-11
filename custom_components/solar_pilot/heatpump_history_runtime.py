"""Optional read-only heat-pump history in its own bounded HA Store."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import re
import time

from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .heatpump_history import HeatpumpHistory
from .sg_config import READ_ENTITY_KEYS

_LOGGER = logging.getLogger(__name__)
_ENTITY = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
_STORE_VERSION = 1
_MAX_ACCESS_SOURCES = 2048
CHECKPOINT_S = 60
SAVE_DELAY_S = 5


def heatpump_history_storage_key(entry_id):
    return f"{DOMAIN}.{entry_id}.heatpump_history"


def configured_history_sources(runtime):
    """Current configured read sources, never a new actuator permission."""
    result = set()
    for owner in (getattr(runtime, "panasonic", None), getattr(runtime, "sg_boost", None)):
        config = getattr(owner, "settings", {})
        if not isinstance(config, Mapping):
            continue
        for key in ("entity_id", *READ_ENTITY_KEYS):
            entity = config.get(key)
            if isinstance(entity, str) and _ENTITY.fullmatch(entity):
                result.add(entity)
        for entity in config.get("zone_entities", ()) if isinstance(config.get("zone_entities"), (list, tuple)) else ():
            if isinstance(entity, str) and _ENTITY.fullmatch(entity):
                result.add(entity)
    return result


def _snapshot_sources(value, depth=0):
    """Also protect automatically used native siblings in private history."""
    if depth > 16:
        return set()
    if isinstance(value, str):
        return {value} if _ENTITY.fullmatch(value) else set()
    result = set()
    if isinstance(value, Mapping):
        children = value.values()
    elif isinstance(value, (list, tuple)):
        children = value
    else:
        return result
    for child in children:
        result.update(_snapshot_sources(child, depth+1))
    return result


def history_binding(runtime, panasonic, sg=None):
    """Opaque identity changes break continuity without publishing bindings."""
    keys = (
        "entity_id", *sorted(READ_ENTITY_KEYS), "zone_entities", "power_scope", "split_power_confirmed",
        "power_supply_profile", "power_supply1_role", "power_supply2_role", "power_activity_threshold_w")
    identity = {name: {key: getattr(getattr(runtime, name, None), "settings", {}).get(key) for key in keys}
                for name in ("panasonic", "sg_boost")}
    sources = configured_history_sources(runtime) | _snapshot_sources(panasonic) | _snapshot_sources(sg)
    try:
        from homeassistant.helpers import entity_registry as er
        lookup = getattr(er.async_get(runtime.hass), "async_get", lambda _entity: None)
        identity["registry"] = {entity: [getattr(lookup(entity), key, None) for key in (
            "config_entry_id", "device_id", "unique_id")] for entity in sorted(sources)}
    except Exception:
        identity["registry"] = {}
    # Registry identifiers remain local inputs to an opaque digest, not API data.
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":"),
                                     default=lambda _value: None).encode("utf-8")).hexdigest()


class HeatpumpHistoryRecorder:
    def __init__(self, hass, entry, interval_s=5):
        self._zone = getattr(getattr(hass, "config", None), "time_zone", "Europe/Brussels")
        self.model = HeatpumpHistory(self._zone)
        self.store = Store(hass, 1, heatpump_history_storage_key(entry.entry_id))
        self.interval_s = float(interval_s)
        self.loaded = False
        self.error = ""
        self._closed = False
        self._writable = False
        self._save_scheduled = False
        self._dirty = False
        self._saved_revision = -1
        self._last_checkpoint = time.monotonic()
        self.access_sources = set()
        self.access_sources_complete = True

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    async def start(self):
        if self.loaded or self._closed:
            return
        try:
            data = await self.store.async_load()
            if data is None or data == {}:
                history, sources = {}, []
            elif (isinstance(data, Mapping) and type(data.get("version")) is int and data.get("version") == _STORE_VERSION
                    and isinstance(data.get("history"), Mapping)
                    and isinstance(data.get("access_sources"), list)
                    and all(isinstance(entity, str) and _ENTITY.fullmatch(entity) for entity in data["access_sources"])
                    and type(data.get("access_sources_complete", True)) is bool):
                history, sources = data["history"], data["access_sources"]
                self.access_sources_complete = data.get("access_sources_complete", True)
            else:
                raise ValueError("Unsupported heat-pump history storage")
            if self.model.restore(history, self.now()) is False:
                raise ValueError("Unsupported heat-pump history model")
            self.access_sources = set(sources[:_MAX_ACCESS_SOURCES])
            self.access_sources_complete = self.access_sources_complete and len(sources) <= _MAX_ACCESS_SOURCES
            evidence = bool(history.get("energy_days")) or any(
                row.get("days") or row.get("sessions") or row.get("events")
                for field in ("lanes", "tasks") for row in history.get(field, {}).get("devices", {}).values())
            if evidence and not self.access_sources:
                # Existing observations without their retained source ACL
                # cannot borrow read permission from a replacement binding.
                self.access_sources_complete = False
            self._writable = True
            self._last_checkpoint = time.monotonic()-CHECKPOINT_S
        except Exception:
            # Never replace an unreadable/future Store with a new empty model.
            # New observations may remain in memory, explicitly without durability.
            _LOGGER.exception("SolarPilot warmtepomphistoriek kon niet geladen worden")
            self.model = HeatpumpHistory(self._zone)
            self.access_sources_complete = False
            self.error = "Bestaande warmtepomphistoriek niet geladen; opslag blijft behouden en nieuwe registratie is alleen tijdelijk"
        self.loaded = True

    def _checkpoint(self):
        self._save_scheduled = False
        try:
            data = {"version": _STORE_VERSION, "history": self.model.snapshot(),
                    "access_sources": sorted(self.access_sources),
                    "access_sources_complete": self.access_sources_complete}
        except Exception:
            self.error = "Warmtepomphistoriek niet opgeslagen; het eerdere checkpoint blijft behouden"
            raise
        self._saved_revision = getattr(self.model, "revision", 0)
        self._dirty = False
        self._last_checkpoint = time.monotonic()
        return data

    def _maybe_save(self):
        if (not self.loaded or not self._writable or self._closed or self._save_scheduled
                or time.monotonic()-self._last_checkpoint < CHECKPOINT_S):
            return
        if not self._dirty:
            return
        self._save_scheduled = True
        try:
            self.store.async_delay_save(self._checkpoint, SAVE_DELAY_S)
        except Exception:
            self._save_scheduled = False
            raise

    def observe(self, panasonic, sg, when, *, binding="", sources=()):
        if not self.loaded or self._closed:
            return
        try:
            actual_sources = set(sources) | _snapshot_sources(panasonic) | _snapshot_sources(sg)
            actual_sources = {entity for entity in actual_sources if isinstance(entity, str) and _ENTITY.fullmatch(entity)}
            combined = self.access_sources | actual_sources
            if len(combined) > _MAX_ACCESS_SOURCES:
                self.access_sources_complete = False
            self.access_sources = set(sorted(combined)[:_MAX_ACCESS_SOURCES])
            self.model.observe(panasonic, sg, when, binding=binding)
            self._dirty = True
            self._maybe_save()
        except Exception:
            if not self.error:
                _LOGGER.exception("SolarPilot warmtepomphistoriek kon niet worden bijgewerkt")
            self.error = "Warmtepomphistoriek onvolledig; bestaande regeling en opslag blijven behouden"
            # The next usable sample must not bridge a failed telemetry interval.
            try:
                self.model.pause_recording()
            except Exception:
                pass

    def brief(self):
        try:
            raw = self.model.brief(self.now())
            # Live HA status permissions are not the historical source ACL.
            # Only opaque recorder metadata belongs in public state attributes.
            result = {key: raw[key] for key in ("date", "recording", "ongoing", "revision") if key in raw}
        except Exception:
            result = {"recording": False, "ongoing": False, "revision": getattr(self.model, "revision", 0)}
        result["recording_error"] = self.error
        result["storage_available"] = self._writable
        return result

    def detail(self, day=None):
        result = deepcopy(self.model.detail(day, when=self.now()))
        result["recording_error"] = self.error
        result["storage_available"] = self._writable
        result["time_resolution_s"] = self.interval_s
        return result

    def export(self, hours=168, *, when=None):
        """Full local-day evidence overlapping the requested UTC interval."""
        if type(hours) is not int or hours not in (1, 24, 168):
            raise ValueError("History export hours must be 1, 24 or 168")
        when = self.now() if when is None else when
        if not isinstance(when, datetime) or when.tzinfo is None:
            raise ValueError("History export timestamps must be timezone-aware")
        wall = when.timestamp()
        cutoff = wall-hours*3600
        zone = self.model.lanes.zone
        day = datetime.fromtimestamp(cutoff, zone).date()
        last_day = datetime.fromtimestamp(wall, zone).date()
        days = []
        partial_boundary_dates = []
        while day <= last_day:
            key = day.isoformat()
            start, end = self.model.lanes._bounds(key)
            day += timedelta(days=1)
            # Half-open UTC overlap excludes an empty day at an exact midnight
            # endpoint. Local midnight boundaries preserve 23/25-hour DST days.
            if end <= start or start >= wall or end <= cutoff:
                continue
            boundary_partial = cutoff > start or wall < end
            if boundary_partial:
                partial_boundary_dates.append(key)
            row = deepcopy(self.model.detail(key, when=when))
            row.update(aggregate_scope="full_local_calendar_day",
                       window_boundary_partial=boundary_partial,
                       window_overlap_s=min(end, wall)-max(start, cutoff))
            # Each selected day already has totals and clipped sessions; avoid
            # repetitions of the full 30-day overview and other lanes. Retained
            # day aggregates cannot be exactly clipped to a partial boundary;
            # export their real totals without proportional energy estimates.
            row.pop("days", None)
            for lane in row.get("sg", {}).values():
                lane.pop("days", None)
            days.append(row)
        return {"days": days, "retention_days": self.model.lanes.retention_days,
                "requested_hours": hours, "exported_days": len(days),
                "window_start": datetime.fromtimestamp(cutoff, timezone.utc).isoformat(),
                "window_end": datetime.fromtimestamp(wall, timezone.utc).isoformat(),
                "timezone": self.model.timezone_name,
                "aggregate_scope": "full_local_calendar_day",
                "partial_boundary_dates": partial_boundary_dates,
                "note": "Dagtotalen, taken en SG-lagen omvatten de volledige lokale kalenderdag voor zover werkelijk geregistreerd. Grensdagen kunnen waarnemingen buiten het gevraagde tijdvenster bevatten; energie wordt niet naar rato geknipt.",
                "recording_error": self.error,
                "storage_available": self._writable, "time_resolution_s": self.interval_s}

    def _cancel_pending_writes(self):
        for name in ("_async_cleanup_delay_listener", "_async_cleanup_final_write_listener"):
            cleanup = getattr(self.store, name, None)
            if callable(cleanup):
                try:
                    cleanup()
                except Exception:
                    _LOGGER.debug("SolarPilot warmtepomphistoriek-listener kon niet sluiten", exc_info=True)
        self._save_scheduled = False

    async def close(self, *, persist=True):
        if self._closed:
            return
        self._closed = True
        self._cancel_pending_writes()
        try:
            self.model.pause_recording()
            if self.loaded and self._writable and persist:
                await self.store.async_save(self._checkpoint())
        except Exception:
            _LOGGER.exception("SolarPilot warmtepomphistoriek kon niet worden opgeslagen bij afsluiten")
            self.error = "Laatste warmtepomphistorie niet opgeslagen; eerder checkpoint blijft behouden"
