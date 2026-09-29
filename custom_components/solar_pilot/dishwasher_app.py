"""One APP request, one fixed local deadline, and event-latched cycle evidence.

This module never calls an appliance. Only the serialized runtime can send START.
It records brief HA events synchronously so End Of Cycle cannot disappear between
regular five-second ticks. Persistence is handled by the existing local Store.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone, time as clock_time
from zoneinfo import ZoneInfo
import time
import math

from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event

from .dishwasher import Reading, accepted, norm, fresh, read, settings

APP_DEFAULTS = {
    "dishwasher_arming_mode": "manual",
    "dishwasher_start_deadline": "13:00:00",
    "dishwasher_after_deadline": "next_day",
    "dishwasher_deadline_grid_allowed": True,
    "dishwasher_deadline_grace_min": 120,
    "dishwasher_phase_entity": "",
    "dishwasher_alert_mode": "state",
}


def request_window(wall, cfg, zone="Europe/Brussels"):
    """Bind a request ONCE. Tomorrow means next calendar day, not next fair day."""
    tz = ZoneInfo(zone)
    now = datetime.fromtimestamp(wall, tz)
    deadline_time = clock_time.fromisoformat(str(cfg.get("dishwasher_start_deadline", "13:00:00")))
    deadline = datetime.combine(now.date(), deadline_time, tz)
    tomorrow = now >= deadline and cfg.get("dishwasher_after_deadline", "next_day") == "next_day"
    day = now.date() + timedelta(days=1) if tomorrow else now.date()
    if tomorrow:
        deadline = datetime.combine(day, deadline_time, tz)
    # Same-day alternative: a late request is due now, not expired at noon.
    if not tomorrow and now >= deadline:
        deadline = now
    begin = datetime.combine(day, clock_time(0), tz) if tomorrow else now
    expiry = deadline.timestamp() + max(1, int(cfg.get("dishwasher_deadline_grace_min", 120))) * 60
    return {"not_before": begin.timestamp(), "deadline": deadline.timestamp(),
            "expires": expiry, "planned_day": day.isoformat(), "zone": zone,
            "grid_allowed": cfg.get("dishwasher_deadline_grid_allowed", True) is True}


class DishwasherApp:
    def __init__(self, runtime):
        self.r = runtime
        self.data = {}
        self._unsub = None
        self._seeded = set()
        self._need_remote_baseline = set()

    def snapshot(self):
        return deepcopy(self.data)

    def restore(self, data):
        if isinstance(data, dict):
            self.data = {i: deepcopy(v) for i, v in list(data.items())[:100]
                         if i in self.r.configs and isinstance(v, dict)}
        self._seeded.clear()
        self._need_remote_baseline.clear()
        for d in self.data.values():
            q = d.get("request")
            if q and (not isinstance(q, dict) or any(not isinstance(q.get(k), (int, float)) or
                    not math.isfinite(q[k]) for k in ("created", "not_before", "deadline", "expires"))):
                d.pop("request", None)
                d["message"] = "Opgeslagen aanvraag ongeldig; APP opnieuw vrijgeven"
            for key in ("completion", "end_pending"):
                e = d.get(key)
                if e and (not isinstance(e, dict) or not isinstance(e.get("ended_at"), (int, float)) or not math.isfinite(e["ended_at"])):
                    d.pop(key, None)

    @property
    def zone(self):
        return getattr(getattr(self.r.hass, "config", None), "time_zone", "Europe/Brussels")

    def enabled(self, cfg):
        return cfg.get("kind") == "dishwasher" and cfg.get("dishwasher_arming_mode", "manual") == "app"

    def _entry(self, i):
        return self.data.setdefault(i, {})

    def _dirty(self):
        self.r.store.async_delay_save(self.r._snapshot, 1)

    def _note(self, cfg, message):
        self.r.note(f'{cfg["name"]}: {message}')

    def start(self):
        ids = set()
        for i, cfg in self.r.configs.items():
            if cfg.get("kind") != "dishwasher":
                continue
            # Current Enabled at startup is not a newly observed physical press.
            self.seed(cfg)
            ids.update(cfg.get(k) for k in ("dishwasher_remote_entity", "dishwasher_state_entity",
                                           "dishwasher_phase_entity", "dishwasher_door_entity",
                                           "cycle_program_entity") if cfg.get(k))
        if ids:
            self._unsub = async_track_state_change_event(self.r.hass, sorted(ids), self.on_event)

    def close(self):
        if self._unsub:
            self._unsub()
            self._unsub = None

    def seed(self, cfg):
        i = cfg["id"]
        if i in self._seeded:
            return
        self._seeded.add(i)
        d = self._entry(i)
        obj = self.r.hass.states.get(cfg.get("dishwasher_remote_entity", ""))
        # Do NOT erase a known baseline when integrations have not loaded yet.
        if obj and norm(obj.state) not in ("", "unknown", "unavailable") and not obj.attributes.get("restored"):
            d["remote"] = str(obj.state)
        else:
            self._need_remote_baseline.add(i)
        state = self.r.hass.states.get(cfg.get("dishwasher_state_entity", ""))
        if state and norm(state.state) not in ("", "unknown", "unavailable"):
            d["last_state"] = str(state.state)
        if self.enabled(cfg) and d.get("remote") == "Enabled" and not d.get("request"):
            d.setdefault("message", "APP stond al aan; schakel APP eenmaal uit en aan voor een nieuwe belading")

    @callback
    def on_event(self, event):
        if self.r._closed:
            return
        new = event.data.get("new_state")
        if new is None or getattr(new, "attributes", {}).get("restored"):
            return
        wall = event.time_fired.timestamp() if getattr(event, "time_fired", None) else time.time()
        # Never reconstruct transitions by re-reading a newer state: use payload.
        for cfg in self.r.configs.values():
            if cfg.get("kind") != "dishwasher":
                continue
            self.event(cfg, event.data.get("entity_id"), str(new.state), wall)

    def event(self, cfg, eid, value, wall):
        """Public deterministic event entry point, also exercised in HA-double tests."""
        i = cfg["id"]
        d = self._entry(i)
        before = deepcopy(d)
        c = settings(cfg)
        if eid == cfg.get("dishwasher_remote_entity"):
            if norm(value) in ("", "unknown", "unavailable"):
                return  # A reconnect cannot become a new APP press.
            previous = d.get("remote")
            d["remote"] = value
            if i in self._need_remote_baseline:
                self._need_remote_baseline.discard(i)
                self._dirty()
                return
            if self.enabled(cfg):
                if value == "Enabled" and previous is not None and previous != "Enabled":
                    raw_obj = self.r.hass.states.get(cfg.get("dishwasher_state_entity", ""))
                    raw = str(getattr(raw_obj, "state", ""))
                    ticket = self.r.dishwasher.tickets.get(i, {})
                    active = d.get("cycle", {}).get("status") == "running" or norm(raw) in accepted(c["dishwasher_running_states"])
                    if not active and not ticket.get("attempted") and c.get("dishwasher_mapping_confirmed"):
                        prog = self.r.hass.states.get(cfg.get("cycle_program_entity", ""))
                        program = str(prog.state)[:80] if prog and norm(prog.state) not in ("unknown", "unavailable", "") else ""
                        d["request"] = {"created": wall, "program": program, "source_signature": self.signature(cfg),
                                        **request_window(wall, cfg, self.zone)}
                        d["cycle"] = {"status": "waiting"}
                        d["message"] = "Via APP klaargezet; wacht op geschikte zon en de vaste startdeadline"
                        d.pop("notified_deadline", None)
                        d.pop("end_pending", None)
                        self._note(cfg, "één APP-aanvraag opgeslagen; plandag " + d["request"]["planned_day"])
                elif value != "Enabled" and d.get("request"):
                    self.cancel(cfg, "APP-starttoestemming ingetrokken")
        elif eid == cfg.get("dishwasher_state_entity"):
            n = norm(value)
            if n in accepted(c["dishwasher_finished_states"]):
                cycle = d.get("cycle", {})
                # Dedupe repeated events/attribute refreshes; retain exact first end.
                if cycle.get("status") != "completed":
                    started = cycle.get("started_at")
                    completion = {"ended_at": wall, "state": value, "confirmed": True,
                                  "started_at": started, "program": cycle.get("program", ""),
                                  "duration_s": max(0, wall-started) if started else None}
                    d["completion"] = completion
                    d["cycle"] = {**cycle, "status": "completed"}
                    d["end_pending"] = dict(completion)
                    self.cancel(cfg, "Afwasprogramma bevestigd voltooid")
                    self._note(cfg, "End Of Cycle onmiddellijk vastgelegd; einde blijft bewaard na Off of verbindingsverlies")
            elif n in accepted(c["dishwasher_running_states"]):
                cycle = d.get("cycle", {})
                if cycle.get("status") != "running":
                    prog = self.r.hass.states.get(cfg.get("cycle_program_entity", ""))
                    d["cycle"] = {"status": "running", "started_at": wall if norm(d.get("last_state", "")) in accepted(c["dishwasher_ready_states"]) else None, "observed_at": wall,
                                  "program": str(getattr(prog, "state", ""))[:80]}
                if n == "running":
                    d["running_report"] = wall
                self.cancel(cfg, "Programma loopt; APP-aanvraag verbruikt")
            elif n == "off" and d.get("cycle", {}).get("status") == "running":
                d["cycle"]["status"] = "end_unconfirmed"
                d["message"] = "Toestel uit; einde niet bevestigd"
                self.cancel(cfg, d["message"])
            # Unknown/Disconnected never records a successful end.
            d["last_state"] = value
        elif eid == cfg.get("dishwasher_phase_entity"):
            d["phase"] = value
        elif eid == cfg.get("cycle_program_entity") and d.get("request"):
            q = d["request"]
            if norm(value) not in ("", "unknown", "unavailable"):
                if q.get("program") and q["program"] != value:
                    self.cancel(cfg, "Programma gewijzigd; APP opnieuw vrijgeven")
                else:
                    q["program"] = value[:80]
        elif eid == cfg.get("dishwasher_door_entity") and d.get("request"):
            q = d["request"]
            if norm(value) in accepted(c["dishwasher_closed_states"]):
                q["closed_seen"] = True
            elif q.get("closed_seen") and norm(value) not in ("", "unknown", "unavailable"):
                self.cancel(cfg, "Deur opnieuw geopend vóór start; APP opnieuw vrijgeven")
        else:
            return
        if d != before:
            self._dirty()

    @staticmethod
    def signature(cfg):
        return "|".join(str(cfg.get(k, "")) for k in ("start_button", "dishwasher_state_entity", "dishwasher_remote_entity", "dishwasher_door_entity", "dishwasher_connection_entity", "cycle_program_entity"))

    def cancel(self, cfg, reason="Wachtende APP-aanvraag geannuleerd"):
        d = self._entry(cfg["id"])
        previous = d.pop("request", None)
        if previous:
            d["last_request"] = {**previous, "outcome": reason}
        d["message"] = reason
        self.r.dishwasher.cancel(cfg["id"])

    def prepare(self, cfg, reading, wall):
        """Bind delayed entity updates to an already observed physical APP edge."""
        if not self.enabled(cfg):
            return
        self.seed(cfg)
        d = self._entry(cfg["id"])
        q = d.get("request")
        if reading.active is True and d.get("cycle", {}).get("status") != "running":
            # Polling fallback for long-lived Running, never for brief End events.
            self.event(cfg, cfg["dishwasher_state_entity"], reading.raw, wall)
            return
        if not q:
            return
        if q.get("source_signature") != self.signature(cfg):
            self.cancel(cfg, "AEG-bronkoppelingen gewijzigd; APP opnieuw vrijgeven")
            self._dirty()
            return
        if wall >= q["expires"]:
            self.cancel(cfg, "Startdeadline gemist en herstelvenster verlopen; APP opnieuw vrijgeven")
            self._dirty()
            return
        if reading.program and q.get("program") and reading.program != q["program"]:
            self.cancel(cfg, "Programma gewijzigd; APP opnieuw vrijgeven")
            self._dirty()
            return
        if not reading.ready:
            return
        q["closed_seen"] = True
        if not q.get("program"):
            q["program"] = reading.program
        ticket = self.r.dishwasher.tickets.get(cfg["id"], {})
        if not ticket.get("armed") and not ticket.get("attempted"):
            self.r.dishwasher.arm(cfg, reading, wall)
            self.r.dishwasher.tickets[cfg["id"]].update(q, source="app")
            self._dirty()

    def due(self, cfg, wall):
        if not self.enabled(cfg):
            return False
        q = self._entry(cfg["id"]).get("request", {})
        return bool(q and cfg.get("dishwasher_deadline_grid_allowed", True) and q.get("grid_allowed") and q["deadline"] <= wall < q["expires"])

    def overlay(self, cfg, reading):
        d = self._entry(cfg["id"])
        if d.get("end_pending"):
            e = d["end_pending"]
            return Reading(active=False, finished=True, raw=e["state"], phase="End Of Cycle",
                           stamp=e["ended_at"], program=e.get("program", ""), reason="Afwasprogramma bevestigd voltooid")
        if norm(reading.raw) == "off" and d.get("completion") and d.get("cycle", {}).get("status") == "completed":
            return replace(reading, active=False, finished=True, reason="Afwasprogramma voltooid; toestel uit")
        return reading

    def overview(self, cfg, wall):
        d = self._entry(cfg["id"])
        q = d.get("request", {})
        cycle = d.get("cycle", {})
        e = d.get("completion")
        def iso(value):
            return datetime.fromtimestamp(value, ZoneInfo(self.zone)).isoformat() if value else None
        return {"arming_mode": cfg.get("dishwasher_arming_mode", "manual"),
                "app_request": bool(q), "planned_day": q.get("planned_day"),
                "start_deadline": iso(q.get("deadline")), "not_before": iso(q.get("not_before")),
                "deadline_due": self.due(cfg, wall), "after_deadline": cfg.get("dishwasher_after_deadline", "next_day"),
                "app_message": d.get("message", "Druk op Delay Start / APP op de afwasmachine"),
                "completion": {**e, "ended_at_local": iso(e["ended_at"])} if e else None,
                "cycle_status": cycle.get("status"),
                "airdry": norm(d.get("phase", "")) == "adodrying" and cycle.get("status") == "running"}
