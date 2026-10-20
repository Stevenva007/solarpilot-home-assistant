"""Optional water telemetry in a separate bounded Store; no service calls."""
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
from .water import WATER_DEFAULTS, WaterModel, normalize_config, source_reading
from .water_diagnostics import water_monitor_diagnostic

_LOGGER = logging.getLogger(__name__)
_ENTITY = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
MAX_ACCESS_SOURCES = 2048


def water_storage_key(entry_id):
    return f"{DOMAIN}.{entry_id}.water_history"


class WaterRecorder:
    def __init__(self, hass, entry, config=None, interval_s=5):
        self.hass, self.entry = hass, entry
        self.settings = normalize_config(config)
        zone = getattr(getattr(hass, "config", None), "time_zone", "Europe/Brussels")
        self.model = WaterModel(self.settings, zone)
        self.store = Store(hass, 1, water_storage_key(entry.entry_id))
        self.interval_s = interval_s
        self.loaded, self._closed, self._writable = False, False, False
        self.error = ""
        self.access_sources, self._context_sources = set(), set()
        self.access_sources_complete = True
        self._save_scheduled = False
        self._saved_revision = -1
        self._last_checkpoint = time.monotonic()

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    @property
    def configured(self):
        return any(self.settings[key] for key in ("volume_entity", "flow_entity", "leak_entity"))

    def configured_sources(self):
        return {self.settings[key] for key in ("volume_entity", "flow_entity", "leak_entity") if self.settings[key]} | self._context_sources

    async def start(self):
        if self.loaded or self._closed:
            return
        try:
            data = await self.store.async_load()
            if data in (None, {}):
                history, sources, complete = None, [], True
            elif (isinstance(data, Mapping) and type(data.get("version")) is int and data["version"] == 1
                    and isinstance(data.get("history"), Mapping) and isinstance(data.get("access_sources"), list)
                    and all(isinstance(entity, str) and _ENTITY.fullmatch(entity) for entity in data["access_sources"])
                    and type(data.get("access_sources_complete")) is bool):
                history, sources, complete = data["history"], data["access_sources"], data["access_sources_complete"]
            else:
                raise ValueError("Unsupported water history storage")
            if self.model.restore(history, self.now()) is False:
                raise ValueError("Unsupported water history model")
            self.access_sources = set(sources[:MAX_ACCESS_SOURCES])
            self.access_sources_complete = complete and len(sources) <= MAX_ACCESS_SOURCES
            if history and any(history.get(key) for key in ("points", "intervals", "events", "days")) and not self.access_sources:
                self.access_sources_complete = False
            self._writable = True
            self._last_checkpoint = time.monotonic()-60
        except Exception:
            _LOGGER.exception("SolarPilot waterhistoriek kon niet geladen worden")
            self.error = "Bestaande waterhistoriek niet geladen; opslag blijft behouden en nieuwe registratie is alleen tijdelijk"
            self.access_sources_complete = False
        self.loaded = True

    def update_config(self, config):
        self.settings = normalize_config(config)
        self.model.update_config(self.settings, self.now())

    def _binding(self, readings):
        identity = {key: self.settings[key] for key in WATER_DEFAULTS if key != "notifications"}
        registry = None
        try:
            from homeassistant.helpers import entity_registry as er
            registry = er.async_get(self.hass)
        except (ImportError, AttributeError, RuntimeError):
            pass
        sources = {}
        lookup = getattr(registry, "async_get", lambda _entity: None)
        for key, role in (("volume_entity", "volume"), ("flow_entity", "flow"), ("leak_entity", "native_leak")):
            entity = self.settings[key]
            row = lookup(entity) if entity else None
            sources[key] = [entity, readings[role].get("source_unit"), *[
                getattr(row, field, None) for field in ("config_entry_id", "device_id", "unique_id")]]
        identity["sources"] = sources
        return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def observe(self, when=None, *, context=None, context_sources=(), context_binding=None):
        if not self.loaded or self._closed:
            return
        when = self.now() if when is None else when
        try:
            stamp = when.timestamp() if isinstance(when, datetime) else float(when)
            readings = {}
            for key, role in (("volume_entity", "volume"), ("flow_entity", "flow"), ("leak_entity", "native_leak")):
                entity = self.settings[key]
                obj = self.hass.states.get(entity) if entity and self.settings["enabled"] else None
                readings[role] = source_reading(obj, role, stamp, self.settings["source_stale_s"], configured=bool(entity))
            current = {entity for entity in context_sources if isinstance(entity, str) and _ENTITY.fullmatch(entity)}
            if len(current) > MAX_ACCESS_SOURCES:
                self.access_sources_complete = False
            self._context_sources = set(sorted(current)[:MAX_ACCESS_SOURCES])
            if self.settings["enabled"]:
                combined = self.access_sources | self.configured_sources()
                if len(combined) > MAX_ACCESS_SOURCES:
                    self.access_sources_complete = False
                self.access_sources = set(sorted(combined)[:MAX_ACCESS_SOURCES])
            self.model.observe(readings, when, binding=self._binding(readings), context=context,
                               context_binding=context_binding)
            self._maybe_save()
        except Exception:
            if not self.error:
                _LOGGER.exception("SolarPilot watermeting overgeslagen")
            self.error = "Waterregistratie onvolledig; bestaande regeling blijft ongewijzigd"
            self.model.interrupt("observation_failed", when)

    def _checkpoint(self):
        self._save_scheduled = False
        result = {"version": 1, "history": self.model.snapshot(), "access_sources": sorted(self.access_sources),
                  "access_sources_complete": self.access_sources_complete}
        self._saved_revision, self._last_checkpoint = self.model.revision, time.monotonic()
        return result

    def _maybe_save(self):
        if (not self._writable or self._closed or self._save_scheduled
                or self.model.revision == self._saved_revision or time.monotonic()-self._last_checkpoint < 60):
            return
        self._save_scheduled = True
        self.store.async_delay_save(self._checkpoint, 5)

    def overview(self):
        result = self.model.overview(self.now())
        result["diagnostic"] = water_monitor_diagnostic(result, self.settings)
        result.update(recording=self.loaded and not self._closed and self.settings["enabled"],
                      storage_available=self._writable, recording_error=self.error)
        return result

    def detail(self, day=None):
        result = deepcopy(self.model.detail(day, when=self.now()))
        result.update(storage_available=self._writable, recording_error=self.error, time_resolution_s=self.interval_s)
        return result

    def export(self, hours=168, *, when=None):
        if type(hours) is not int or hours not in (1, 24, 168):
            raise ValueError("Water export hours must be 1, 24 or 168")
        when = self.now() if when is None else when
        if not isinstance(when, datetime) or when.tzinfo is None:
            raise ValueError("Water export requires a timezone-aware timestamp")
        wall, cutoff = when.timestamp(), when.timestamp()-hours*3600
        day = datetime.fromtimestamp(cutoff, self.model.zone).date()
        last = datetime.fromtimestamp(wall, self.model.zone).date()
        days, partial = [], []
        while day <= last:
            key = day.isoformat()
            start, end = self.model._bounds(key)
            day += timedelta(days=1)
            if start >= wall or end <= cutoff:
                continue
            boundary = cutoff > start or wall < end
            if boundary:
                partial.append(key)
            row = self.model.detail(key, when=when)
            row.pop("days", None)
            row.update(aggregate_scope="full_local_calendar_day", window_boundary_partial=boundary,
                       window_overlap_s=min(end, wall)-max(start, cutoff))
            days.append(row)
        return {"schema": 1, "read_only": True, "days": days, "requested_hours": hours,
                "window_start": datetime.fromtimestamp(cutoff, timezone.utc).isoformat(),
                "window_end": datetime.fromtimestamp(wall, timezone.utc).isoformat(),
                "timezone": self.model.timezone_name, "retention_days": 30,
                "aggregate_scope": "full_local_calendar_day", "partial_boundary_dates": partial,
                "recording_error": self.error, "storage_available": self._writable,
                "note": "Alleen geregistreerde gedeelde waterintervallen. Geen Recorder-aanvulling, geen verdeling over toestellen of ontbrekende tijd."}

    async def close(self, *, persist=True):
        if self._closed:
            return
        self._closed = True
        for name in ("_async_cleanup_delay_listener", "_async_cleanup_final_write_listener"):
            cleanup = getattr(self.store, name, None)
            if callable(cleanup):
                try:
                    cleanup()
                except Exception:
                    _LOGGER.debug("SolarPilot waterhistoriek-listener kon niet sluiten", exc_info=True)
        self._save_scheduled = False
        self.model.interrupt("shutdown", self.now())
        if self.loaded and self._writable and persist:
            try:
                await self.store.async_save(self._checkpoint())
            except Exception:
                _LOGGER.exception("SolarPilot waterhistoriek kon niet worden opgeslagen")
                self.error = "Laatste waterhistoriek niet opgeslagen; eerder checkpoint blijft behouden"
