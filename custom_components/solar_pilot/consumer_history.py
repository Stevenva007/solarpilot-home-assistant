"""Bounded, local consumer activity history; no device control and no HA imports.

Runtime is the observed ON/status interval, not proof of continuous compressor
operation. UTC instants are split at HA-local midnights (including 23/25h days).
Missing observations and restarts are gaps, never fabricated OFF events.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time as dtime, timedelta, timezone
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

RETENTION_DAYS = 30
MAX_SESSIONS = 2000
MAX_EVENTS = 300
SCHEMA_VERSION = 1


def _finite(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _text(value, limit=400):
    return str(value or "")[:limit]


def _iso(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec="seconds")


class ConsumerHistory:
    """One compact session per observed ON period plus small daily aggregates."""

    def __init__(self, timezone_name="Europe/Brussels", *, retention_days=RETENTION_DAYS):
        self.timezone_name = str(timezone_name)
        try:
            self.zone = ZoneInfo(self.timezone_name)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            self.timezone_name, self.zone = "UTC", timezone.utc
        self.retention_days = max(1, min(90, int(retention_days)))
        self.devices = {}
        self.revision = 0
        self._pending = {}

    def _stamp(self, when):
        if not isinstance(when, datetime) or when.tzinfo is None:
            raise ValueError("History timestamps must be timezone-aware")
        return when.timestamp()

    def _day(self, stamp):
        return datetime.fromtimestamp(stamp, self.zone).date().isoformat()

    def _bounds(self, day):
        d = date.fromisoformat(day)
        start = datetime.combine(d, dtime(), self.zone).timestamp()
        end = datetime.combine(d + timedelta(days=1), dtime(), self.zone).timestamp()
        return start, end

    def _split(self, start, end):
        while start < end:
            day = self._day(start)
            _, boundary = self._bounds(day)
            until = min(end, boundary)
            if until <= start:
                break
            yield day, until - start
            start = until

    @staticmethod
    def _binding(cfg):
        # Names and planner settings may change without discarding history.
        return "|".join(str(cfg.get(k, "")) for k in (
            "kind", "control_entity", "active_entity", "number_entity"))

    def ensure(self, device_id, cfg, when):
        stamp = self._stamp(when)
        binding = self._binding(cfg)
        if device_id not in self.devices:
            self.devices[device_id] = {
                "name": _text(cfg.get("name", device_id), 120), "binding": binding,
                "since": stamp, "last_seen": None, "active": None,
                "days": {}, "sessions": [], "events": [], "open_id": None,
                "next_id": 1, "trimmed_before": None, "revision": 0,
            }
            self._change(self.devices[device_id])
        row = self.devices[device_id]
        row["name"] = _text(cfg.get("name", device_id), 120)
        if row["binding"] != binding:
            self._interrupt(row, "Koppeling gewijzigd; eerdere fysieke toestand niet overgenomen")
            row["binding"] = binding
            self._pending.pop(device_id, None)
        return row

    def _change(self, row):
        self.revision += 1
        row["revision"] = int(row.get("revision", 0)) + 1

    def _aggregate(self, row, day):
        return row["days"].setdefault(day, {"on_s": 0.0, "known_s": 0.0, "starts": 0, "stops": 0})

    def command(self, device_id, cfg, watts, reason, when):
        row = self.ensure(device_id, cfg, when)
        self._pending[device_id] = {"on": watts > 0, "reason": _text(reason),
                                    "issued": self._stamp(when), "confirmed": False}
        # A request alone is deliberately not logged as a successful start/stop.
        return row

    def confirm(self, device_id):
        if device_id in self._pending:
            self._pending[device_id]["confirmed"] = True

    def failure(self, device_id, cfg, reason, when):
        row = self.ensure(device_id, cfg, when)
        requested = self._pending.pop(device_id, None)
        suffix = f" Gevraagde reden: {requested['reason']}." if requested else ""
        self.event(device_id, cfg, "Opdracht niet bevestigd. " + _text(reason) + suffix, when, "warning")

    def event(self, device_id, cfg, reason, when, kind="info"):
        row = self.ensure(device_id, cfg, when)
        row["events"].append({"at": self._stamp(when), "reason": _text(reason, 600), "kind": kind})
        row["events"] = row["events"][-MAX_EVENTS:]
        self._change(row)

    def _open(self, row):
        if row["open_id"] is None:
            return None
        return next((s for s in reversed(row["sessions"]) if s["id"] == row["open_id"]), None)

    def _finish(self, row, stamp, reason, source, *, confirmed):
        session = self._open(row)
        if session is None:
            return
        stamp = max(session["start"], stamp)
        session.update(end=stamp, observed_until=stamp, stop_reason=_text(reason),
                       stop_source=source, stop_confirmed=bool(confirmed))
        row["open_id"] = None
        if confirmed:
            self._aggregate(row, self._day(stamp))["stops"] += 1
        self._change(row)

    def _interrupt(self, row, reason):
        if row["last_seen"] is not None:
            self._finish(row, row["last_seen"], reason, "unknown", confirmed=False)
        row["last_seen"], row["active"] = None, None
        self._change(row)

    def pause_recording(self, reason="Registratie gestopt bij herladen/afsluiten; toestel niet uitgeschakeld"):
        for row in self.devices.values():
            self._interrupt(row, reason)
        self._pending.clear()

    def observe(self, device_id, cfg, active, when, *, max_gap_s=30):
        """Observe a verified control/status value; unknown must be passed as None.

        Interval precision is the runtime polling interval. Unavailable endpoints
        and gaps over max_gap_s are excluded. On→off is approximated at observation.
        """
        stamp = self._stamp(when)
        row = self.ensure(device_id, cfg, when)
        previous, last = row["active"], row["last_seen"]
        if active is not None and not isinstance(active, bool):
            raise ValueError("active must be bool or None")
        if last is not None and stamp < last:
            return  # Ignore clock reversal/out-of-order input; never count twice.
        if last is not None and stamp - last > max_gap_s:
            self._interrupt(row, "Meetonderbreking; werkelijke stoptijd en stopreden onbekend")
            previous, last = None, None
            self._pending.pop(device_id, None)
        if active is None:
            if last is not None:
                self._interrupt(row, "Toestelstatus onbeschikbaar; geen uitschakeling bevestigd")
            self._prune(row, stamp)
            return
        if previous is not None and last is not None:
            for day, seconds in self._split(last, stamp):
                agg = self._aggregate(row, day)
                agg["known_s"] += seconds
                if previous:
                    agg["on_s"] += seconds
            opened = self._open(row)
            if opened is not None:
                opened["observed_until"] = stamp
        self._aggregate(row, self._day(stamp))
        hint = self._pending.get(device_id)
        own_transition = bool(hint and hint["confirmed"] and hint["on"] == active
                              and 0 <= stamp - hint["issued"] <= max(300, float(cfg.get("ack_timeout_s", 60)) + max_gap_s))
        if active != previous:
            if active:
                known = previous is False
                source = "solarpilot" if own_transition else "external" if known else "unknown"
                reason = (hint["reason"] if own_transition else
                          "Ingeschakeld buiten een bevestigde SolarPilot-opdracht; handmatig, andere automatisering of toestel" if known else
                          "Al ingeschakeld bij begin/hervatten registratie; eerdere starttijd en reden onbekend")
                session = {"id": row["next_id"], "start": stamp, "end": None,
                           "observed_until": stamp, "start_reason": reason, "stop_reason": None,
                           "start_source": source, "stop_source": None,
                           "start_confirmed": bool(known or own_transition), "stop_confirmed": False}
                row["next_id"] += 1
                row["sessions"].append(session)
                row["open_id"] = session["id"]
                if session["start_confirmed"]:
                    self._aggregate(row, self._day(stamp))["starts"] += 1
                self._change(row)
            elif previous is True:
                reason = (hint["reason"] if own_transition else
                          "Uitgeschakeld buiten een bevestigde SolarPilot-opdracht; handmatige bediening, andere automatisering of taak voltooid")
                self._finish(row, stamp, reason, "solarpilot" if own_transition else "external", confirmed=True)
        if own_transition:
            self._pending.pop(device_id, None)
        row["active"], row["last_seen"] = active, stamp
        self._prune(row, stamp)

    def _prune(self, row, stamp):
        first = (datetime.fromtimestamp(stamp, self.zone).date() - timedelta(days=self.retention_days - 1)).isoformat()
        if (row.get("_pruned_day") == first and len(row["sessions"]) <= MAX_SESSIONS
                and len(row["events"]) <= MAX_EVENTS):
            return
        row["_pruned_day"] = first
        boundary = self._bounds(first)[0]
        row["days"] = {d: a for d, a in row["days"].items() if d >= first}
        row["events"] = [e for e in row["events"] if e["at"] >= boundary][-MAX_EVENTS:]
        sessions = [s for s in row["sessions"] if s.get("end") is None or s["end"] >= boundary]
        if len(sessions) > MAX_SESSIONS:
            removed = sessions[:-MAX_SESSIONS]
            row["trimmed_before"] = max(s.get("end") or s["observed_until"] for s in removed)
        row["sessions"] = sessions[-MAX_SESSIONS:]

    def brief(self, device_id, when):
        row = self.devices.get(device_id)
        day = self._day(self._stamp(when))
        if not row:
            return {"date": day, "on_s": None, "recording": False, "revision": 0}
        agg = row["days"].get(day)
        return {"date": day, "on_s": round(agg.get("on_s", 0), 1) if agg else None, "recording": agg is not None,
                "ongoing": row["active"] is True, "revision": row["revision"]}

    def detail(self, device_id, day, when):
        """30 tiny daily totals plus sessions/events for one explicitly requested day."""
        stamp = self._stamp(when)
        today = self._day(stamp)
        day = day or today
        parsed = date.fromisoformat(day)
        if parsed.isoformat() != day:
            raise ValueError("Gebruik een datum in de vorm JJJJ-MM-DD")
        first = date.fromisoformat(today) - timedelta(days=self.retention_days - 1)
        if not first <= parsed <= date.fromisoformat(today):
            raise ValueError("Datum valt buiten de bewaarde 30 dagen")
        row = self.devices.get(device_id)
        if not row:
            raise KeyError(device_id)
        self._prune(row, stamp)
        start, end = self._bounds(day)
        day_until = min(stamp, end)
        expected = max(0, day_until - start)
        agg = row["days"].get(day, {})
        known = min(expected, max(0.0, agg.get("known_s", 0)))
        items = []
        for s in row["sessions"]:
            until = s["end"] if s["end"] is not None else s["observed_until"]
            left, right = max(start, s["start"]), min(end, until)
            if right < left or (right == left and not start <= s["start"] < end):
                continue
            # A session ending exactly at midnight belongs to the previous day.
            if until == start and s["start"] < start:
                continue
            item = deepcopy(s)
            item.update(start=_iso(s["start"]), end=_iso(s["end"]) if s["end"] is not None else None,
                        observed_until=_iso(s["observed_until"]), segment_start=_iso(left), segment_end=_iso(right),
                        duration_s=round(max(0, right-left), 1), ongoing=s["end"] is None,
                        continued_from_previous_day=s["start"] < start,
                        continues_next_day=until > end or (s["end"] is None and stamp >= end),
                        left_pct=round(100*(left-start)/(end-start), 5),
                        width_pct=round(100*max(0,right-left)/(end-start), 5))
            items.append(item)
        summaries = []
        for n in range(self.retention_days):
            d = (first + timedelta(days=n)).isoformat()
            a = row["days"].get(d)
            summaries.append({"date": d, "on_s": round(a.get("on_s", 0), 1) if a else None,
                              "known_s": round(a.get("known_s", 0), 1) if a else 0,
                              "starts": a.get("starts", 0) if a else 0})
        events = [{**e, "at": _iso(e["at"])} for e in row["events"] if start <= e["at"] < end]
        truncated = row["trimmed_before"] is not None and row["trimmed_before"] >= start
        return {"schema": SCHEMA_VERSION, "device_id": device_id, "name": row["name"],
                "timezone": self.timezone_name, "date": day, "today": today, "first_date": first.isoformat(),
                "retention_days": self.retention_days, "generated_at": _iso(stamp),
                "recording_since": _iso(row["since"]), "last_observation": _iso(row["last_seen"]) if row["last_seen"] is not None else None,
                "day_seconds": end-start, "on_s": round(max(0, agg.get("on_s", 0)), 1),
                "known_s": round(known, 1), "unobserved_s": round(max(0,expected-known), 1),
                "partial": expected-known > 15, "has_data": day in row["days"],
                "starts": agg.get("starts", 0), "stops": agg.get("stops", 0),
                "sessions": items, "events": events, "days": summaries,
                "sessions_truncated": truncated,
                "note": "Draaitijd = waargenomen aan-/actiefstatus. Bij een slimme stekker is dit ingeschakelde tijd, niet noodzakelijk continue compressorwerking. Meetonderbrekingen tellen niet mee; tijdprecisie volgt het meetritme."}

    def snapshot(self):
        return {"version": SCHEMA_VERSION, "timezone": self.timezone_name, "devices": deepcopy(self.devices)}

    def restore(self, data, configs, when):
        """Restore known intervals, but never extend an ON session through downtime."""
        self.devices = {}
        if not isinstance(data, dict) or data.get("version") != SCHEMA_VERSION:
            return
        stamp = self._stamp(when)
        raw_devices = data.get("devices", {})
        if not isinstance(raw_devices, dict):
            return
        for device_id, cfg in configs.items():
            raw = raw_devices.get(device_id)
            if not isinstance(raw, dict):
                continue
            try:
                since = _finite(raw.get("since"))
                if since is None or since < 0 or since > stamp + 60:
                    continue
                row = {"name": _text(raw.get("name", device_id), 120), "binding": str(raw.get("binding", "")),
                       "since": since, "last_seen": _finite(raw.get("last_seen")),
                       "active": raw.get("active") if isinstance(raw.get("active"), bool) else None,
                       "days": {}, "sessions": [], "events": [], "open_id": None,
                       "next_id": 1, "trimmed_before": _finite(raw.get("trimmed_before")), "revision": 0}
                for d, a in raw.get("days", {}).items():
                    date.fromisoformat(d)
                    if not isinstance(a, dict):
                        continue
                    row["days"][d] = {"on_s": max(0, min(90000, _finite(a.get("on_s")) or 0)),
                                      "known_s": max(0, min(90000, _finite(a.get("known_s")) or 0)),
                                      "starts": max(0, int(a.get("starts", 0))), "stops": max(0, int(a.get("stops", 0)))}
                for raw_session in raw.get("sessions", [])[-MAX_SESSIONS:]:
                    s = deepcopy(raw_session)
                    left, right = _finite(s.get("start")), _finite(s.get("observed_until"))
                    if left is None or right is None or not 0 <= left <= right <= stamp + 60:
                        continue
                    s.update(id=int(s["id"]), start=left, observed_until=right)
                    stop = _finite(s.get("end"))
                    if stop is None:
                        s.update(end=right, stop_reason="Registratie onderbroken door herstart/herladen; geen uitschakeling bevestigd",
                                 stop_source="unknown", stop_confirmed=False)
                    elif not left <= stop <= right:
                        continue
                    else:
                        s["end"] = stop
                    s["start_confirmed"] = s.get("start_confirmed") is True
                    s["stop_confirmed"] = s.get("stop_confirmed") is True
                    s["start_reason"] = _text(s.get("start_reason"))
                    s["stop_reason"] = _text(s.get("stop_reason"))
                    row["sessions"].append(s)
                    row["next_id"] = max(row["next_id"], s["id"]+1)
                for e in raw.get("events", [])[-MAX_EVENTS:]:
                    at = _finite(e.get("at"))
                    if at is not None and 0 <= at <= stamp + 60:
                        row["events"].append({"at": at, "reason": _text(e.get("reason"), 600), "kind": _text(e.get("kind"), 20)})
                row["last_seen"], row["active"] = None, None
                self.devices[device_id] = row
                self._prune(row, stamp)
                self.ensure(device_id, cfg, when)
                self._change(row)
            except (ValueError, TypeError, KeyError, OverflowError, AttributeError):
                # Corrupt optional history must not disable the energy controller.
                self.devices.pop(device_id, None)
        self._pending.clear()
