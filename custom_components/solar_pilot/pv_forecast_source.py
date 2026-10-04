"""Read Forecast.Solar's already-fetched HA data. No HTTP, refresh or write calls.

The optional coordinator adapter is guarded: HA internals can change. Explicit
entity selectors remain supported and missing horizons remain None, never zero.
"""
from __future__ import annotations
from bisect import bisect_right
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import math

PV_FORECAST_DEFAULTS = {
    "enabled": True, "auto_discover": True, "forecast_entry_id": "",
    "calibration_enabled": True, "shadow_enabled": True, "learning_preset": "normal",
    "show_raw": True, "inverter_limit_w": 10000.0, "panel_peak_wp": 13800.0,
    "tilt_deg": 25.0, "azimuth_deg": 180.0, "stale_s": 7200,
    "minimum_days": 5, "history_days": 30,
}
ENTITY_ROLES = {
    "now_entity": ("power_production_now", "power"),
    "next_hour_power_entity": ("power_production_next_hour", "power"),
    "remaining_entity": ("energy_production_today_remaining", "energy"),
    "today_entity": ("energy_production_today", "energy"),
    "tomorrow_entity": ("energy_production_tomorrow", "energy"),
    "current_hour_entity": ("energy_current_hour", "energy"),
    "next_hour_entity": ("energy_next_hour", "energy"),
}

def finite(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError, OverflowError):
        return None


def stamp(value):
    try:
        dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.timestamp() if dt.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError, OSError):
        return None


class PowerSeries:
    """Bounded piecewise-linear power, integrated in actual elapsed seconds."""
    def __init__(self, points=None):
        clean = {}
        for t, v in (points or [])[:2048]:
            t, v = finite(t), finite(v)
            if t is not None and v is not None and 0 <= v <= 1000000:
                clean[t] = v
        self.points = sorted(clean.items())
        self.times = [x[0] for x in self.points]

    def at(self, ts):
        if not self.points or ts < self.times[0] or ts > self.times[-1]:
            return None
        i = bisect_right(self.times, ts) - 1
        a, va = self.points[i]
        if ts == a:
            return va
        b, vb = self.points[i+1]
        # Long zero-to-zero night intervals are legitimate; long data gaps aren't.
        if b-a > 10800 and (va != 0 or vb != 0):
            return None
        return va+(vb-va)*(ts-a)/(b-a)

    def energy(self, start, end, transform=None):
        if end <= start:
            return 0.0
        # Fifteen-minute maximum quadrature spacing for position-dependent factors.
        cuts = sorted(set([start, end, *[t for t in self.times if start < t < end],
                           *[start+i*900 for i in range(1, int((end-start)/900)+1) if start+i*900 < end]]))
        vals = []
        for t in cuts:
            w = self.at(t)
            if w is None:
                return None
            vals.append(transform(t, w) if transform else w)
        return sum((b-a)*(va+vb)/2 for a,b,va,vb in zip(cuts,cuts[1:],vals,vals[1:]))/3600000


class ForecastSolarSource:
    def __init__(self, hass, settings):
        self.hass, self.settings = hass, settings
        self.refs = {}; self.entry_id = None; self.candidates = []
        self.series = PowerSeries(); self.scalars = {}; self.status = "Nog geen gegevens"
        self.metadata = {}; self.last_scan = None; self.last_refresh = None
        self.coordinator_signature = None; self.coordinator_seen = None
        self.source_stamp = None; self.valid = False; self.warning = ""; self.discovery_warning = ""

    def _discover(self, now):
        if self.last_scan is not None and 0 <= now-self.last_scan < 300:
            return
        self.last_scan = now
        self.refs = {k:self.settings[k] for k in ENTITY_ROLES if self.settings.get(k)}
        self.entry_id = None; self.candidates = []; self.metadata = {}; self.discovery_warning = ""
        try:
            manager = getattr(self.hass, "config_entries", None)
            entries = list(manager.async_entries("forecast_solar")) if manager else []
            entries = [e for e in entries if not getattr(e, "disabled_by", None)]
            self.candidates = [{"id": e.entry_id, "name": str(getattr(e,"title","Forecast.Solar"))[:100]} for e in entries]
            requested = self.settings.get("forecast_entry_id")
            selected = next((e for e in entries if e.entry_id == requested), None) if requested else (entries[0] if self.settings.get("auto_discover") and len(entries)==1 else None)
            if selected is None:
                if len(entries)>1 and not requested:
                    self.discovery_warning = "Meerdere Forecast.Solar-installaties: kies één bron; niet dubbel optellen"
                return
            self.entry_id = selected.entry_id
            options = dict(getattr(selected,"options",{})); data = dict(getattr(selected,"data",{}))
            planes = []
            for sub in getattr(selected,"subentries",{}).values():
                sd = getattr(sub,"data",{})
                if "modules_power" in sd:
                    planes.append(sd)
            if not planes and "modules_power" in data:
                planes = [data]
            # Whitelist only. No API key, coordinates, URLs or auth material.
            self.metadata = {k: finite(options.get(k, data.get(k))) for k in ("inverter_size","damping_morning","damping_evening")}
            self.metadata["planes"] = [{k:finite(p.get(k)) for k in ("modules_power","declination","azimuth")} for p in planes]
            from homeassistant.helpers import entity_registry as er
            registry = er.async_get(self.hass)
            for ent in getattr(registry,"entities",{}).values():
                if getattr(ent,"config_entry_id",None) != self.entry_id or getattr(ent,"disabled_by",None):
                    continue
                for role, (key, _) in ENTITY_ROLES.items():
                    if role not in self.refs and (getattr(ent,"unique_id",None)==f"{self.entry_id}_{key}" or getattr(ent,"translation_key",None)==key):
                        self.refs[role] = ent.entity_id
        except (AttributeError, TypeError, ValueError, KeyError):
            self.discovery_warning = "Automatische bronadapter niet beschikbaar; expliciete sensorkoppelingen blijven bruikbaar"

    def _entity_value(self, entity_id, kind, now):
        obj = self.hass.states.get(entity_id) if entity_id else None
        if obj is None or obj.attributes.get("restored"):
            return None, None
        value = finite(obj.state)
        ts = stamp(getattr(obj,"last_reported",None) or getattr(obj,"last_updated",None))
        if value is None or value < 0 or ts is None or not -5 <= now-ts <= self.settings["stale_s"]:
            return None, ts
        unit = obj.attributes.get("unit_of_measurement")
        multiplier = ({"W":1, "kW":1000} if kind == "power" else {"Wh":.001, "kWh":1}).get(unit)
        return (value*multiplier if multiplier is not None else None), ts

    def refresh(self, now):
        if self.last_refresh is not None and 0 <= now-self.last_refresh < 60:
            return
        self.last_refresh = now; self.warning = ""; self.valid = False
        if not self.settings.get("enabled"):
            self.series = PowerSeries(); self.scalars = {}; self.status = "Forecast.Solar-laag uitgeschakeld"
            return
        self._discover(now)
        self.warning = self.discovery_warning
        self.scalars = {}; stamps=[]
        for role, (_, kind) in ENTITY_ROLES.items():
            value, ts = self._entity_value(self.refs.get(role), kind, now)
            self.scalars[role] = value
            if value is not None and ts is not None:
                stamps.append(ts)
        self.series = PowerSeries()
        try:
            entry = self.hass.config_entries.async_get_entry(self.entry_id) if self.entry_id else None
            coord = getattr(entry,"runtime_data",None)
            if coord is None and entry is not None:
                coord = getattr(self.hass,"data",{}).get("forecast_solar",{}).get(self.entry_id)
            estimate = getattr(coord,"data",None)
            watts = getattr(estimate,"watts",None)
            if getattr(coord,"last_update_success",False) and isinstance(watts, Mapping):
                # Track data object identity plus numerical content. A replaced equal
                # estimate is a real update; scanning an unchanged object is not.
                signature = (id(estimate), tuple((str(k),str(v)) for k,v in list(watts.items())[:2048]))
                if signature != self.coordinator_signature:
                    self.coordinator_signature = signature; self.coordinator_seen = now
                if self.coordinator_seen is not None and now-self.coordinator_seen <= self.settings["stale_s"]:
                    points=[(stamp(t),v) for t,v in list(watts.items())[:2048]]
                    self.series=PowerSeries(points)
                    # At startup, sensor freshness is required; don't 'refresh'
                    # an old retained coordinator value with our own start time.
                    if not stamps:
                        self.series=PowerSeries()
                else:
                    self.warning="Forecast.Solar-cache te oud; geen tijdreeks gebruikt"
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError):
            self.warning="Tijdreeksadapter niet beschikbaar; alleen gekoppelde forecastsensoren"
        self.valid = bool(stamps)
        self.source_stamp = min(stamps) if stamps else None
        self.status = ("Forecast.Solar tijdreeks + sensoren" if self.series.points else "Alleen forecastsensoren; beperkte horizon") if self.valid else "Forecast ontbreekt of te oud; actuele regeling blijft actief"
        if not self.valid:
            self.series=PowerSeries()

    def raw_at(self, ts, now):
        if not self.valid:
            return None
        value = self.series.at(ts)
        if value is not None:
            return value
        if abs(ts-now)<1:
            return self.scalars.get("now_entity")
        if abs(ts-now-3600)<1:
            return self.scalars.get("next_hour_power_entity")
        return None
