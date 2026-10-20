"""Bounded water observations and advisory patterns, with no control actions.

HA report timestamps describe reports, not independently proven physical
measurement times. Counter deltas, instantaneous flow and leak sensor reports
remain separate evidence. Shared water is never attributed to a device.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime, time as dtime, timedelta, timezone
import hashlib
import math
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WATER_DEFAULTS = {"enabled": False, "volume_entity": "", "flow_entity": "", "leak_entity": "",
                  "source_stale_s": 300, "continuous_flow_l_min": 0.1,
                  "continuous_flow_minutes": 60, "notifications": True}
RETENTION_DAYS = 30
MAX_POINTS = 8192
MAX_INTERVALS = 8192
MAX_EVENTS = 512
MAX_TIME = 4102444800
_ENTITY = re.compile(r"^(sensor|binary_sensor)\.[a-z0-9_]+$")
_VOLUME = {"L": 1, "l": 1, "m³": 1000, "m3": 1000, "mL": .001}
_FLOW = {"L/min": 1, "l/min": 1, "L/h": 1/60, "L/s": 60,
         "m³/h": 1000/60, "m3/h": 1000/60, "m³/min": 1000,
         "m³/s": 60000, "mL/s": .06}
_SOURCE_KEYS = ("volume_entity", "flow_entity", "leak_entity")


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _stamp(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return None
        try:
            value = value.timestamp()
        except (ValueError, OSError, OverflowError):
            return None
    value = _number(value)
    return value if value is not None and 0 < value <= MAX_TIME else None


def normalize_config(config=None):
    raw = {**WATER_DEFAULTS, **(dict(config) if isinstance(config, Mapping) else {})}
    result = dict(WATER_DEFAULTS)
    for key in ("enabled", "notifications"):
        if type(raw.get(key)) is bool:
            result[key] = raw[key]
    for key in _SOURCE_KEYS:
        value = raw.get(key)
        if isinstance(value, str) and len(value) <= 256 and (not value or _ENTITY.fullmatch(value)):
            domain = "binary_sensor." if key == "leak_entity" else "sensor."
            if not value or value.startswith(domain):
                result[key] = value
    for key, low, high in (("source_stale_s", 15, 86400), ("continuous_flow_l_min", .01, 1000),
                            ("continuous_flow_minutes", 1, 1440)):
        value = _number(raw.get(key))
        if value is not None and low <= value <= high:
            result[key] = value
    return result


def _metadata_valid(role, attributes):
    attrs = attributes if isinstance(attributes, Mapping) else {}
    device_class = attrs.get("device_class")
    if role == "native_leak":
        return device_class == "moisture"
    if role == "flow":
        return attrs.get("unit_of_measurement") in _FLOW and device_class in (None, "volume_flow_rate")
    return (attrs.get("unit_of_measurement") in _VOLUME and device_class in (None, "water", "volume")
            and attrs.get("state_class") in (None, "total", "total_increasing"))


def source_errors(hass, config):
    """Validate selected roles/metadata, independently of current numeric state."""
    raw = {**WATER_DEFAULTS, **(dict(config) if isinstance(config, Mapping) else {})}
    clean, errors = normalize_config(raw), {}
    for key in WATER_DEFAULTS:
        if (key in ("enabled", "notifications") and type(raw.get(key)) is not bool
                or raw.get(key) != clean[key] or type(raw.get(key)) is bool and key not in ("enabled", "notifications")):
            errors[key] = "invalid_water_setting"
    if raw.get("enabled") is not True:
        return errors
    if not any(clean[key] for key in _SOURCE_KEYS):
        errors["base"] = "water_source_required"
    for key, role, code in (("volume_entity", "volume", "water_volume_source"),
                             ("flow_entity", "flow", "water_flow_source"),
                             ("leak_entity", "native_leak", "water_leak_source")):
        if not clean[key] or key in errors:
            continue
        obj = hass.states.get(clean[key])
        if obj is None or not _metadata_valid(role, getattr(obj, "attributes", {})):
            errors[key] = code
    return errors


def source_reading(obj, role, now, stale_s, *, configured=True):
    """Detach only the selected source's normalized value and original report."""
    result = {"value": None, "unit": "L/min" if role == "flow" else "L" if role == "volume" else None,
              "source_unit": None, "reported_at": None, "valid_until": None,
              "fresh": False, "reason": "not_configured" if not configured else "missing"}
    if not configured or obj is None:
        return result
    attrs = getattr(obj, "attributes", {})
    attrs = attrs if isinstance(attrs, Mapping) else {}
    unit = attrs.get("unit_of_measurement")
    result["source_unit"] = unit if isinstance(unit, str) and len(unit) <= 16 else None
    original = getattr(obj, "last_reported", None)
    if original is None:
        original = getattr(obj, "last_updated", None)
    reported = _stamp(original)
    result["reported_at"] = reported
    result["valid_until"] = reported+stale_s if reported is not None else None
    raw = getattr(obj, "state", None)
    if any(attrs.get(key) for key in ("restored", "estimated", "is_estimated")):
        result["reason"] = "restored_or_estimated"
    elif raw is None or str(raw).strip().casefold() in ("", "unknown", "unavailable", "none"):
        result["reason"] = "unavailable"
    elif reported is None:
        result["reason"] = "report_time_unknown"
    elif not -5 <= now-reported <= stale_s:
        result["reason"] = "stale" if now >= reported else "future_report"
    elif not _metadata_valid(role, attrs):
        result["reason"] = "invalid_source_metadata"
    else:
        value = (True if raw == "on" else False if raw == "off" else None) if role == "native_leak" else _number(raw)
        if role != "native_leak" and value is not None:
            value *= (_FLOW if role == "flow" else _VOLUME)[unit]
            if not math.isfinite(value) or not 0 <= value <= (1000000 if role == "flow" else 1e15):
                value = None
        if value is None:
            result["reason"] = "invalid_value"
        else:
            result.update(value=value, fresh=True, reason="current")
    return result


def _clean_context(context, now):
    context = context if isinstance(context, Mapping) else {}
    result = {"boiler": {}, "dishwasher": {"value": None, "reported_at": None, "valid_until": None}}
    boiler = context.get("boiler", {})
    for role in ("temperature", "target", "dishwasher"):
        raw = context.get(role, {}) if role == "dishwasher" else boiler.get(role, {}) if isinstance(boiler, Mapping) else {}
        raw = raw if isinstance(raw, Mapping) else {}
        stamp, until = _stamp(raw.get("reported_at")), _stamp(raw.get("valid_until"))
        fresh = stamp is not None and until is not None and stamp <= until <= stamp+86400 and -5 <= now-stamp and now <= until
        value = raw.get("value") if role == "dishwasher" else _number(raw.get("value"))
        valid = type(value) is bool if role == "dishwasher" else value is not None and 0 <= value <= 100
        row = {"value": value if fresh and valid else None, "reported_at": stamp, "valid_until": until}
        if role == "dishwasher":
            result[role] = row
        else:
            result["boiler"][role] = row
    return result


class WaterModel:
    """Observed counter intervals, sparse capture points and advisory episodes."""
    def __init__(self, config=None, timezone_name="Europe/Brussels"):
        self.settings = normalize_config(config)
        try:
            self.zone = ZoneInfo(timezone_name)
            self.timezone_name = timezone_name
        except (ZoneInfoNotFoundError, TypeError, ValueError):
            self.zone, self.timezone_name = timezone.utc, "UTC"
        self.points, self.intervals, self.events, self.days = [], [], [], {}
        self.dropped = {"points": 0, "intervals": 0, "events": 0}
        self.revision = 0
        self.alert = {"active": False, "cause": None, "episode_id": None, "started_at": None,
                      "last_evidence_at": None, "evidence_current": False, "binding": None}
        self._binding = None
        self._after = None
        self._volume = None
        self._volume_gap = False
        self._flow = None
        self._flow_since = None
        self._leak = None
        self._leak_rejected_at = None
        self._latest = {}
        self._suspicion = self._unknown_suspicion("collecting")
        self._last_point = None
        self._last_fingerprint = None
        self._context_quality = None

    def _unknown_suspicion(self, reason):
        return {"state": "unknown", "elapsed_s": 0, "required_s": self.settings["continuous_flow_minutes"]*60,
                "threshold_l_min": self.settings["continuous_flow_l_min"], "last_reported_at": None, "reason": reason}

    def _day(self, stamp):
        return datetime.fromtimestamp(stamp, self.zone).date().isoformat()

    def _bounds(self, day):
        local = date.fromisoformat(day)
        return (datetime.combine(local, dtime(), self.zone).timestamp(),
                datetime.combine(local+timedelta(days=1), dtime(), self.zone).timestamp())

    def _event(self, kind, now, **facts):
        self.events.append({"at": now, "kind": kind, **facts})
        if len(self.events) > MAX_EVENTS:
            self.dropped["events"] += len(self.events)-MAX_EVENTS
            self.events = self.events[-MAX_EVENTS:]
        self.revision += 1

    def interrupt(self, reason="restart", now=None):
        moment = _stamp(now)
        marker = {"restart": "restart", "configuration_changed": "binding_changed",
                  "observation_failed": "source_gap", "clock_reversal": "clock_reversal",
                  "disabled": "disabled"}.get(reason)
        if marker and moment is not None and self.points and (not self.events or self.events[-1]["kind"] != marker):
            self._event(marker, moment)
        self._volume = self._flow = self._flow_since = None
        self._leak = self._leak_rejected_at = None
        self._volume_gap = False
        self._after = _stamp(now)
        self._latest = {}
        self._suspicion = self._unknown_suspicion(reason)
        self.alert["evidence_current"] = False
        self._last_point = self._last_fingerprint = None
        self._context_quality = None

    def update_config(self, config, now=None):
        clean = normalize_config(config)
        if any(clean[key] != self.settings[key] for key in WATER_DEFAULTS if key != "notifications"):
            self.settings = clean
            self._binding = None
            self.interrupt("configuration_changed", now)
        else:
            self.settings = clean

    def _prune(self, now):
        cutoff_day = datetime.fromtimestamp(now, self.zone).date()-timedelta(days=RETENTION_DAYS-1)
        cutoff = self._bounds(cutoff_day.isoformat())[0]
        self.days = {day: row for day, row in self.days.items() if day >= cutoff_day.isoformat()}
        for name, maximum, stamp_key in (("points", MAX_POINTS, "captured_at"),
                                          ("intervals", MAX_INTERVALS, "end"), ("events", MAX_EVENTS, "at")):
            values = [row for row in getattr(self, name) if row[stamp_key] >= cutoff]
            if len(values) > maximum:
                self.dropped[name] += len(values)-maximum
            setattr(self, name, values[-maximum:])

    def _observe_volume(self, reading, now):
        if not reading.get("fresh") or reading.get("value") is None:
            if self._volume is not None and not self._volume_gap:
                self._event("source_gap", now, source_role="volume")
            self._volume_gap = self._volume is not None
            return
        stamp, value = reading["reported_at"], reading["value"]
        if stamp < self._after:
            return
        previous = self._volume
        if previous is not None and stamp <= previous[0]:
            # A mutable value under the same original report cannot replace
            # the prior counter baseline or create another delta.
            if value != previous[1] or stamp < previous[0]:
                self._volume = None
                self._after = now
                reading.update(value=None, fresh=False, reason="report_not_advanced")
            return
        self._volume = stamp, value
        if previous is None:
            self._volume_gap = False
            return
        elapsed, delta = stamp-previous[0], value-previous[1]
        if delta < 0:
            self._event("counter_reset", now)
            self._volume_gap = False
            return
        if self._volume_gap or elapsed > self.settings["source_stale_s"]:
            self._event("counter_gap", now)
            self.intervals.append({"start": previous[0], "end": stamp, "volume_l": delta,
                                   "day": None, "reason": "counter_gap"})
            self._volume_gap = False
            return
        day = self._day(stamp)
        allocated = day if self._day(previous[0]) == day else None
        self.intervals.append({"start": previous[0], "end": stamp, "volume_l": delta, "day": allocated,
                               "reason": "counter_delta" if allocated else "cross_local_day"})
        if allocated:
            row = self.days.setdefault(day, {"volume_l": 0., "volume_covered_s": 0., "volume_intervals": 0})
            row["volume_l"] += delta
            row["volume_covered_s"] += elapsed
            row["volume_intervals"] += 1
        self.revision += 1

    def _observe_flow(self, reading, now):
        if not reading.get("fresh") or reading.get("value") is None:
            if self._flow is not None:
                self._event("source_gap", now, source_role="flow")
            self._flow = self._flow_since = None
            self._suspicion = self._unknown_suspicion(reading.get("reason", "unknown"))
            return
        stamp, value = reading["reported_at"], reading["value"]
        previous = self._flow
        if previous is not None and (stamp < previous[0] or stamp == previous[0] and value != previous[1]):
            self._flow = self._flow_since = None
            self._after = now
            self._suspicion = self._unknown_suspicion("report_not_advanced")
            reading.update(value=None, fresh=False, reason="report_not_advanced")
            return
        if stamp < self._after:
            self._flow = self._flow_since = None
            self._suspicion = self._unknown_suspicion("awaiting_new_report")
            return
        if previous is not None and stamp == previous[0]:
            return
        active = value >= self.settings["continuous_flow_l_min"]
        if not active:
            self._flow_since = None
        elif previous is None or previous[1] < self.settings["continuous_flow_l_min"] or stamp-previous[0] > min(300, self.settings["source_stale_s"]):
            self._flow_since = stamp
        self._flow = stamp, value
        elapsed = max(0, stamp-self._flow_since) if active and self._flow_since is not None else 0
        required = self.settings["continuous_flow_minutes"]*60
        self._suspicion = {"state": "suspected" if active and elapsed >= required else "pending" if active else "clear",
                           "elapsed_s": elapsed, "required_s": required,
                           "threshold_l_min": self.settings["continuous_flow_l_min"],
                           "last_reported_at": stamp, "reason": "reported_continuous_flow" if active else "flow_below_threshold"}

    def _observe_alert(self, readings, now):
        leak = readings["native_leak"]
        native = leak.get("fresh") is True and leak.get("value") is True
        suspect = self._suspicion["state"] == "suspected"
        if native or suspect:
            cause = "both" if native and suspect else "native_leak" if native else "continuous_flow"
            evidence = max(leak.get("reported_at") or 0 if native else 0,
                           self._suspicion.get("last_reported_at") or 0 if suspect else 0)
            if not self.alert["active"] or self.alert.get("binding") != self._binding:
                episode = hashlib.sha256(f"{self._binding}:{now}:{self.revision}".encode()).hexdigest()[:24]
                self.alert = {"active": True, "cause": cause, "episode_id": episode, "started_at": now,
                              "last_evidence_at": evidence, "evidence_current": True, "binding": self._binding}
                self._event("advisory_started", now, cause=cause, episode_id=episode)
            else:
                self.alert.update(cause=cause, last_evidence_at=max(evidence, self.alert["last_evidence_at"] or 0), evidence_current=True)
        elif self.alert["active"]:
            if self.alert.get("binding") != self._binding:
                self.alert["evidence_current"] = False
                return
            previous_evidence = self.alert["last_evidence_at"] or 0
            leak_clear = (not self.settings["leak_entity"] or leak.get("fresh") is True
                          and leak.get("value") is False and leak["reported_at"] > previous_evidence)
            flow_clear = (not self.settings["flow_entity"] or self._suspicion["state"] == "clear"
                          and self._suspicion["last_reported_at"] > previous_evidence)
            if leak_clear and flow_clear:
                self._event("advisory_resolved", now, episode_id=self.alert["episode_id"])
                reports = [readings[role].get("reported_at") for role, key in (
                    ("native_leak", "leak_entity"), ("flow", "flow_entity")) if self.settings[key]]
                self.alert.update(active=False, evidence_current=True, last_evidence_at=min(reports) if reports else now)
            else:
                self.alert["evidence_current"] = False

    def _observe_leak_report(self, reading):
        """An old or in-place changed report cannot clear/rearm an episode."""
        if reading.get("fresh") is not True:
            return
        stamp, value = reading["reported_at"], reading["value"]
        previous = self._leak
        rejected = self._leak_rejected_at
        invalid = rejected is not None and stamp <= rejected
        if previous is not None and (stamp < previous[0] or stamp == previous[0] and value is not previous[1]):
            self._leak_rejected_at = max(previous[0], rejected or 0)
            invalid = True
        # A retained resolution is a rejection fence, never a new live proof.
        if (not self.alert["active"] and self.alert["episode_id"] is not None
                and self.alert.get("binding") == self._binding and value is True
                and stamp <= (self.alert["last_evidence_at"] or 0)):
            invalid = True
        if invalid:
            reading.update(value=None, fresh=False, reason="report_not_advanced")
            return
        if rejected is not None and stamp > rejected:
            self._leak_rejected_at = None
        self._leak = stamp, value

    def observe(self, readings, when, *, binding="", context=None, context_binding=None):
        now = _stamp(when)
        if now is None:
            raise ValueError("Water observations require a valid UTC instant")
        if not self.settings["enabled"]:
            self.interrupt("disabled", now)
            return
        if not isinstance(binding, str):
            raise ValueError("Water binding must be an opaque identity")
        if not re.fullmatch(r"[a-f0-9]{64}", binding):
            binding = hashlib.sha256(binding.encode()).hexdigest()
        if self._binding != binding:
            if self._binding is not None:
                self._event("binding_changed", now)
            self.interrupt("collecting", now)
            self._binding = binding
        if self._after is None:
            self._after = now
        if self._last_point is not None and now < self._last_point:
            self.interrupt("clock_reversal", now)
            return
        readings = deepcopy(readings)
        self._observe_leak_report(readings["native_leak"])
        self._observe_volume(readings["volume"], now)
        previous_suspicion = self._suspicion["state"]
        self._observe_flow(readings["flow"], now)
        if self._suspicion["state"] != previous_suspicion:
            self._event("flow_state", now, state=self._suspicion["state"])
        self._observe_alert(readings, now)
        self._latest = deepcopy(readings)
        clean_context = _clean_context(context, now)
        context_identity = context_binding if isinstance(context_binding, str) and re.fullmatch(r"[a-f0-9]{64}", context_binding) else None
        context_quality = (context_identity, clean_context["boiler"]["temperature"]["value"] is not None,
                           clean_context["boiler"]["target"]["value"] is not None,
                           clean_context["dishwasher"]["value"])
        if (self._context_quality is not None and self._context_quality[1]
                and (not context_quality[1] or self._context_quality[0] != context_identity)):
            self._event("source_gap", now, source_role="boiler_temperature")
        self._context_quality = context_quality
        fingerprint = (readings["volume"]["fresh"], readings["flow"]["fresh"],
                       readings["native_leak"]["fresh"], readings["native_leak"]["value"], self._suspicion["state"], context_quality)
        important = fingerprint != self._last_fingerprint
        elapsed = now-self._last_point if self._last_point is not None else math.inf
        changed_value = bool(self.points and any(readings[key]["value"] != self.points[-1][key]["value"]
                                               for key in ("volume", "flow")))
        if important or elapsed >= 300 or changed_value and elapsed >= 60:
            self.points.append({"captured_at": now, **deepcopy(readings), "context": clean_context,
                                "context_binding": context_identity,
                                "suspicion": deepcopy(self._suspicion)})
            self._last_point, self._last_fingerprint = now, fingerprint
            self.revision += 1
        self._prune(now)

    def overview(self, when):
        now = _stamp(when)
        if now is None:
            raise ValueError("Water overview requires a valid UTC instant")
        values = {}
        for role, key in (("volume", "volume_entity"), ("flow", "flow_entity"), ("native_leak", "leak_entity")):
            row = deepcopy(self._latest.get(role) or source_reading(None, role, now, self.settings["source_stale_s"], configured=bool(self.settings[key])))
            if row.get("fresh") and (row.get("valid_until") is None or now > row["valid_until"] or now < row["reported_at"]-5):
                row.update(value=None, fresh=False, reason="stale")
            values[role] = row
        suspicion = deepcopy(self._suspicion) if values["flow"]["fresh"] else self._unknown_suspicion(values["flow"]["reason"])
        day = self._day(now)
        daily = self.days.get(day)
        today = {"date": day, "volume_l": daily["volume_l"] if daily else None,
                 "volume_covered_s": daily["volume_covered_s"] if daily else 0,
                 "volume_intervals": daily["volume_intervals"] if daily else 0, "complete": False}
        alert = deepcopy(self.alert)
        if alert["active"]:
            native_current = values["native_leak"]["fresh"] and values["native_leak"]["value"] is True
            flow_current = values["flow"]["fresh"] and suspicion["state"] == "suspected"
            alert["evidence_current"] = bool(native_current if alert["cause"] == "native_leak" else
                                             flow_current if alert["cause"] == "continuous_flow" else native_current and flow_current)
            if alert.get("binding") != self._binding:
                alert["evidence_current"] = False
        elif alert["episode_id"] is not None:
            leak_clear = not self.settings["leak_entity"] or values["native_leak"]["fresh"] and values["native_leak"]["value"] is False
            flow_clear = not self.settings["flow_entity"] or values["flow"]["fresh"] and suspicion["state"] == "clear"
            alert["evidence_current"] = bool(leak_clear and flow_clear and alert.get("binding") == self._binding)
        return {"schema": 1, "read_only": True, "enabled": self.settings["enabled"],
                "configured": any(self.settings[key] for key in _SOURCE_KEYS), "observed_at": now,
                **values, "suspicion": suspicion, "alert": alert, "today": today, "revision": self.revision,
                "note": "Geregistreerde gedeelde watermeting; rapporttijd is geen bewezen fysiek meettijdstip. Langdurige stroming is een vermoeden, geen vastgesteld lek of toestelverbruik."}

    def detail(self, day=None, *, when):
        now = _stamp(when)
        if now is None:
            raise ValueError("Water history requires a valid UTC instant")
        day = self._day(now) if day is None else day
        start, end = self._bounds(day)
        minimum = (datetime.fromtimestamp(now, self.zone).date()-timedelta(days=RETENTION_DAYS-1)).isoformat()
        if not minimum <= day <= self._day(now):
            raise ValueError("Water history date outside retention")
        result = {"schema": 1, "read_only": True, "date": day, "day_start": start, "day_end": end,
                "timezone": self.timezone_name, "retention_days": RETENTION_DAYS, "revision": self.revision,
                "generated_at": now, "today": self._day(now), "min_date": minimum,
                "has_data": any(start <= row["captured_at"] < end for row in self.points)
                    or any(row["start"] < end and row["end"] > start for row in self.intervals),
                "days": [{"date": key, **deepcopy(row), "complete": False} for key, row in sorted(self.days.items())],
                "volume_l": self.days.get(day, {}).get("volume_l"),
                "volume_covered_s": self.days.get(day, {}).get("volume_covered_s", 0), "complete": False,
                "points": deepcopy([row for row in self.points if start <= row["captured_at"] < end]),
                "intervals": deepcopy([row for row in self.intervals if row["start"] < end and row["end"] > start]),
                "events": deepcopy([row for row in self.events if start <= row["at"] < end]),
                "coverage": {"first_point": self.points[0]["captured_at"] if self.points else None,
                             "last_point": self.points[-1]["captured_at"] if self.points else None,
                             "first_interval": self.intervals[0]["start"] if self.intervals else None,
                             "last_interval": self.intervals[-1]["end"] if self.intervals else None,
                             "point_cap": MAX_POINTS, "interval_cap": MAX_INTERVALS, "event_cap": MAX_EVENTS,
                             "dropped": deepcopy(self.dropped),
                             "sample_min_interval_s": 60, "heartbeat_s": 300,
                             "note": "Werkelijke opnamepunten; geen interpolatie of aanvulling over ontbrekende perioden."}}
        from .water_correlations import correlate_water_history
        result["correlations"] = correlate_water_history(result)
        return result

    def snapshot(self):
        return {"schema": 1, "timezone": self.timezone_name, "points": deepcopy(self.points),
                "intervals": deepcopy(self.intervals), "events": deepcopy(self.events), "days": deepcopy(self.days),
                "dropped": deepcopy(self.dropped), "revision": self.revision, "alert": deepcopy(self.alert)}

    def restore(self, data, when):
        """Unsupported/corrupt checkpoints fail without authorizing a rewrite."""
        if data in (None, {}):
            self.interrupt("restart", when)
            return True
        if not isinstance(data, Mapping) or type(data.get("schema")) is not int or data["schema"] != 1:
            return False
        try:
            for name, cap, stamp_key in (("points", MAX_POINTS, "captured_at"), ("intervals", MAX_INTERVALS, "end"),
                                        ("events", MAX_EVENTS, "at")):
                rows = data.get(name)
                if not isinstance(rows, list) or len(rows) > cap:
                    return False
                if any(not isinstance(row, Mapping) or _stamp(row.get(stamp_key)) is None or row[stamp_key] > _stamp(when)+5 for row in rows):
                    return False
            points = []
            for raw in data["points"]:
                identity = raw.get("context_binding")
                if identity is not None and (not isinstance(identity, str) or not re.fullmatch(r"[a-f0-9]{64}", identity)):
                    return False
                point = {"captured_at": raw["captured_at"], "context": _clean_context(raw.get("context"), raw["captured_at"]),
                         "context_binding": identity}
                for role in ("volume", "flow", "native_leak"):
                    source = raw.get(role)
                    if not isinstance(source, Mapping) or type(source.get("fresh")) is not bool:
                        return False
                    stamp, until = _stamp(source.get("reported_at")), _stamp(source.get("valid_until"))
                    value = source.get("value")
                    if (source.get("reported_at") is not None and stamp is None
                            or source.get("valid_until") is not None and until is None
                            or (stamp is None) != (until is None)):
                        return False
                    if source["fresh"] and (stamp is None or until is None
                            or not stamp <= until <= stamp+86400 or not stamp-5 <= raw["captured_at"] <= until):
                        return False
                    if role == "native_leak" and value is not None and type(value) is not bool:
                        return False
                    if role != "native_leak" and value is not None and (_number(value) is None
                            or not 0 <= value <= (1e6 if role == "flow" else 1e15)):
                        return False
                    if source["fresh"] is True and value is None or source["fresh"] is False and value is not None:
                        return False
                    if source.get("unit") != ("L/min" if role == "flow" else "L" if role == "volume" else None):
                        return False
                    if any(source.get(key) is not None and (not isinstance(source[key], str) or len(source[key]) > limit)
                            for key, limit in (("source_unit", 16), ("reason", 80))):
                        return False
                    point[role] = {key: deepcopy(source.get(key)) for key in (
                        "value", "unit", "source_unit", "reported_at", "valid_until", "fresh", "reason")}
                suspicion = raw.get("suspicion", {})
                if (not isinstance(suspicion, Mapping) or suspicion.get("state") not in ("unknown", "clear", "pending", "suspected")
                        or any(_number(suspicion.get(key)) is None or not 0 <= suspicion[key] <= limit
                               for key, limit in (("elapsed_s", MAX_TIME), ("required_s", 86400), ("threshold_l_min", 1000)))
                        or suspicion.get("last_reported_at") is not None and _stamp(suspicion["last_reported_at"]) is None
                        or not isinstance(suspicion.get("reason"), str) or len(suspicion["reason"]) > 80):
                    return False
                point["suspicion"] = {key: deepcopy(suspicion.get(key)) for key in (
                    "state", "elapsed_s", "required_s", "threshold_l_min", "last_reported_at", "reason")}
                points.append(point)
            intervals = []
            for row in data["intervals"]:
                if (_stamp(row.get("start")) is None or row["start"] >= row["end"]
                        or _number(row.get("volume_l")) is None or not 0 <= row["volume_l"] <= 1e15):
                    return False
                assigned = row.get("day")
                if assigned is not None and (assigned != self._day(row["start"]) or assigned != self._day(row["end"])):
                    return False
                intervals.append({key: deepcopy(row.get(key)) for key in ("start", "end", "volume_l", "day", "reason")})
            days = data.get("days")
            if not isinstance(days, Mapping) or len(days) > RETENTION_DAYS+1:
                return False
            for day, row in days.items():
                self._bounds(day)
                if not isinstance(row, Mapping) or any(_number(row.get(key)) is None or row[key] < 0
                        for key in ("volume_l", "volume_covered_s", "volume_intervals")):
                    return False
            alert = data.get("alert", {})
            if (not isinstance(alert, Mapping) or type(alert.get("active")) is not bool
                    or alert.get("cause") not in (None, "native_leak", "continuous_flow", "both")
                    or alert.get("episode_id") is not None and (not isinstance(alert["episode_id"], str)
                    or not re.fullmatch(r"[a-f0-9]{24}", alert["episode_id"]))
                    or alert.get("binding") is not None and (not isinstance(alert["binding"], str)
                    or not re.fullmatch(r"[a-f0-9]{64}", alert["binding"]))
                    or type(alert.get("evidence_current")) is not bool):
                return False
            if alert["active"] and (not alert.get("episode_id") or _stamp(alert.get("started_at")) is None):
                return False
            for key in ("started_at", "last_evidence_at"):
                if alert.get(key) is not None and (_stamp(alert[key]) is None or alert[key] > _stamp(when)+5):
                    return False
            event_kinds = {"counter_reset", "counter_gap", "binding_changed", "flow_state", "advisory_started", "advisory_resolved",
                           "restart", "source_gap", "clock_reversal", "disabled"}
            for event in data["events"]:
                if (event.get("kind") not in event_kinds
                        or "source_role" in event and (event["kind"] != "source_gap"
                        or type(event["source_role"]) is not str
                        or event["source_role"] not in ("volume", "flow", "boiler_temperature"))
                        or event.get("state") is not None and event["state"] not in ("unknown", "clear", "pending", "suspected")
                        or event.get("cause") is not None and event["cause"] not in ("native_leak", "continuous_flow", "both")
                        or event.get("episode_id") is not None and (not isinstance(event["episode_id"], str)
                        or not re.fullmatch(r"[a-f0-9]{24}", event["episode_id"]))):
                    return False
            dropped = data.get("dropped", {})
            if not isinstance(dropped, Mapping) or any(type(dropped.get(key, 0)) is not int
                    or not 0 <= dropped.get(key, 0) <= 10**12 for key in self.dropped):
                return False
            revision = data.get("revision", 0)
            if type(revision) is not int or not 0 <= revision <= 10**12:
                return False
            self.points, self.intervals = points, intervals
            self.events = [{key: deepcopy(row.get(key)) for key in ("at", "kind", "state", "cause", "episode_id", "source_role") if key in row}
                           for row in data["events"]]
            self.days = {day: {key: row[key] for key in ("volume_l", "volume_covered_s", "volume_intervals")}
                         for day, row in days.items()}
            self.alert = {key: deepcopy(alert.get(key)) for key in (
                "active", "cause", "episode_id", "started_at", "last_evidence_at", "evidence_current", "binding")}
            self.dropped = {key: dropped.get(key, 0) for key in self.dropped}
            self.revision = revision
            self._prune(_stamp(when))
            self.interrupt("restart", when)
            return True
        except (TypeError, ValueError, KeyError, OverflowError, OSError):
            return False
