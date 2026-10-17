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
    "dishwasher_monday_start_deadline": "",
    "dishwasher_after_deadline": "next_day",
    "dishwasher_deadline_grid_allowed": True,
    "dishwasher_deadline_grace_min": 120,
    "dishwasher_phase_entity": "",
    "dishwasher_alert_mode": "state",
}


def _finite_time(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        if not math.isfinite(value):
            return False
        # A finite scalar can still lie outside usable datetime/platform range.
        # Restored completion epochs are used by the runtime before formatting.
        datetime.fromtimestamp(value, timezone.utc)
        return True
    except (ValueError, OverflowError, OSError):
        return False


def deadline_time(cfg, day):
    """Return the configured deadline for one local calendar day."""
    value = (cfg.get("dishwasher_monday_start_deadline")
             if day.weekday() == 0 else None)
    return clock_time.fromisoformat(str(value or cfg.get("dishwasher_start_deadline", "13:00:00")))


def request_window(wall, cfg, zone="Europe/Brussels"):
    """Bind a request ONCE. Tomorrow means next calendar day, not next fair day."""
    tz = ZoneInfo(zone)
    now = datetime.fromtimestamp(wall, tz)
    deadline = datetime.combine(now.date(), deadline_time(cfg, now.date()), tz)
    tomorrow = now >= deadline and cfg.get("dishwasher_after_deadline", "next_day") == "next_day"
    day = now.date() + timedelta(days=1) if tomorrow else now.date()
    if tomorrow:
        deadline = datetime.combine(day, deadline_time(cfg, day), tz)
    # Same-day alternative: a late request is due now, not expired at noon.
    if not tomorrow and now >= deadline:
        deadline = now
    begin = datetime.combine(day, clock_time(0), tz) if tomorrow else now
    expiry = deadline.timestamp() + max(1, int(cfg.get("dishwasher_deadline_grace_min", 120))) * 60
    return {"not_before": begin.timestamp(), "deadline": deadline.timestamp(),
            "expires": expiry, "planned_day": day.isoformat(), "zone": zone,
            # A fixed APP start deadline is a grid fallback. Existing stored
            # flags remain readable, but cannot turn that deadline into a second
            # solar-only waiting window. Appliance and electrical guards remain
            # the serialized runtime's responsibility.
            "grid_allowed": True}


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
            report = d.get("running_report")
            if report is not None and (not _finite_time(report) or report > time.time()):
                d["quarantined_running_report"] = deepcopy(report)
                d.pop("running_report", None)
            q = d.get("request")
            if q and (not isinstance(q, dict) or any(not _finite_time(q.get(k))
                    for k in ("created", "not_before", "deadline", "expires"))):
                d["quarantined_request"] = deepcopy(q)
                d.pop("request", None)
                d["message"] = "Opgeslagen aanvraag ongeldig; APP opnieuw vrijgeven"
            for key in ("completion", "end_pending"):
                e = d.get(key)
                if e and (not isinstance(e, dict) or not _finite_time(e.get("ended_at"))):
                    d["quarantined_"+key] = deepcopy(e)
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

    def _ready_again(self, cfg, value):
        """A new READY ends the old active latch without inventing completion.

        It does not restore a consumed request or clear an uncertain START. Only
        a later, explicit APP edge may create permission for the new loading.
        """
        d = self._entry(cfg["id"])
        cycle = d.get("cycle", {})
        if norm(value) not in accepted(settings(cfg)["dishwasher_ready_states"]) or cycle.get("status") != "running":
            return False
        d["cycle"] = {**cycle, "status": "end_unconfirmed"}
        if self.r.dishwasher.tickets.get(cfg["id"], {}).get("attempted"):
            d["message"] = "Toestel opnieuw gereed; START-uitkomst eerst controleren, geen automatische herhaalopdracht"
        else:
            d["message"] = "Toestel opnieuw gereed; einde vorige cyclus niet bevestigd; APP opnieuw vrijgeven"
        return True

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

    def event(self, cfg, eid, value, wall, *, observed_only=False):
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
                    if self.r.dishwasher.storage_blocked:
                        d["message"] = "Opgeslagen START-toestemming onleesbaar; nieuwe APP-aanvraag is geblokkeerd"
                        self._dirty()
                        return
                    raw_obj = self.r.hass.states.get(cfg.get("dishwasher_state_entity", ""))
                    raw = str(getattr(raw_obj, "state", ""))
                    ticket = self.r.dishwasher.tickets.get(i, {})
                    # A retained old Running may outlive a lost End/Off event.
                    # Resolve it only from a usable live reading of READY; a
                    # stale/restored/offline source cannot release this latch.
                    reading = read(self.r.hass, cfg, wall)
                    if reading.active is False:
                        self._ready_again(cfg, reading.raw)
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
                    elif ticket.get("attempted"):
                        d["message"] = "START-uitkomst eerst controleren; geen tweede APP-aanvraag zonder controle"
                    elif active:
                        d["message"] = "Vorige cyclus nog actief of niet opnieuw gereed; geen nieuwe APP-aanvraag"
                    else:
                        d["message"] = "AEG-startknop en statuskoppelingen nog niet bevestigd; APP-aanvraag niet opgeslagen"
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
                    context = self._cycle_request(cfg, d, cycle)
                    d["cycle"] = {"status": "running", "started_at": wall if not observed_only and n == "running" and norm(d.get("last_state", "")) in accepted(c["dishwasher_ready_states"]) else None, "observed_at": wall,
                                  "program": str(getattr(prog, "state", ""))[:80], "context_checked": True}
                    if context:
                        d["cycle"]["request"] = context
                        d["cycle"]["request_created"] = context["created"]
                if n == "running":
                    if not d["cycle"].get("context_checked"):
                        context = self._legacy_cycle_request(cfg, d, d["cycle"])
                        if context:
                            d["cycle"]["request"] = context
                            d["cycle"]["request_created"] = context["created"]
                        d["cycle"]["context_checked"] = True
                    d["running_report"] = wall
                    d["cycle"].setdefault("start_confirmed_at", wall)
                self.cancel(cfg, "Programma loopt; APP-aanvraag verbruikt")
            elif n == "off" and d.get("cycle", {}).get("status") == "running":
                d["cycle"]["status"] = "end_unconfirmed"
                d["message"] = "Toestel uit; einde niet bevestigd"
                self.cancel(cfg, d["message"])
            elif n in accepted(c["dishwasher_ready_states"]):
                self._ready_again(cfg, value)
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

    def _valid_request(self, cfg, request):
        """Only a bound, finite frozen request can carry deadline context."""
        if not isinstance(request, dict) or request.get("source_signature") != self.signature(cfg):
            return False
        keys = ("created", "not_before", "deadline", "expires")
        if any(not _finite_time(request.get(k)) for k in keys):
            return False
        return (request["created"] <= request["not_before"] <= request["deadline"]
                < request["expires"])

    def _cycle_request(self, cfg, data, cycle):
        """Keep consumed context; never turn an old request into new permission.

        AEG may revoke Remote before reporting Running. A matching durable START
        ticket links that earlier request to this cycle. A completed previous
        cycle or an unrelated manual start cannot inherit its old deadline.
        """
        current = data.get("request")
        if self._valid_request(cfg, current):
            return deepcopy(current)
        ticket = self.r.dishwasher.tickets.get(cfg["id"], {})
        previous = data.get("last_request")
        sent = ticket.get("sent_at")
        pending = (cycle.get("status") in (None, "waiting") and
                   (ticket.get("attempted") or ticket.get("confirmed")))
        if (pending and ticket.get("source") == "app" and self._valid_request(cfg, previous)
                and ticket.get("created") == previous["created"]
                and _finite_time(sent)
                and sent >= previous["created"]):
            return deepcopy(previous)
        return None

    def _legacy_cycle_request(self, cfg, data, cycle):
        """Reconcile old running context only from the same completed START proof.

        Legacy beta.77 did not copy the request into its running cycle. Matching
        durable intent plus a prompt first cycle report can recover that context;
        a later independent cycle, a later completed cycle, and an uncertain old
        START cannot supply ownership. No actual start time is reconstructed.
        """
        current = data.get("request")
        if self._valid_request(cfg, current):
            return deepcopy(current)
        ticket = self.r.dishwasher.tickets.get(cfg["id"], {})
        previous = data.get("last_request")
        sent, observed = ticket.get("sent_at"), cycle.get("observed_at")
        if (ticket.get("source") != "app" or not (ticket.get("attempted") or ticket.get("confirmed"))
                or not self._valid_request(cfg, previous) or ticket.get("created") != previous["created"]
                or previous.get("outcome") not in ("Programma loopt; APP-aanvraag verbruikt",
                    "Herstart: APP-aanvraag verbruikt door bevestigde cyclus")
                or any(not _finite_time(value) for value in (sent, observed))):
            return None
        try:
            confirmation_window = max(60.0, float(cfg.get("ack_timeout_s", 60)) + float(self.r.settings.get("interval_s", 5)))
        except (ValueError, TypeError, OverflowError):
            return None
        if not math.isfinite(confirmation_window) or not previous["created"] <= sent <= observed <= sent + confirmation_window:
            return None
        completion = data.get("completion", {})
        if not isinstance(completion, dict):
            return None
        ended = completion.get("ended_at")
        if (completion and completion.get("confirmed") is True and _finite_time(ended) and ended >= sent):
            return None
        if previous.get("program") and cycle.get("program") != previous["program"]:
            return None
        return deepcopy(previous)

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
        if self.r.dishwasher.storage_blocked:
            return
        self.seed(cfg)
        d = self._entry(cfg["id"])
        if reading.active is False and self._ready_again(cfg, reading.raw):
            self._dirty()
        q = d.get("request")
        if reading.active is True and d.get("cycle", {}).get("status") != "running":
            # Polling fallback for long-lived Running, never for brief End events.
            self.event(cfg, cfg["dishwasher_state_entity"], reading.raw, wall, observed_only=True)
            return
        if not q:
            return
        if q.get("source_signature") != self.signature(cfg):
            self.cancel(cfg, "AEG-bronkoppelingen gewijzigd; APP opnieuw vrijgeven")
            self._dirty()
            return
        if not self._valid_request(cfg, q):
            self.cancel(cfg, "Opgeslagen aanvraag ongeldig; APP opnieuw vrijgeven")
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
        return bool(self._valid_request(cfg, q) and q["not_before"] <= wall
                    and q["deadline"] <= wall < q["expires"])

    def overlay(self, cfg, reading):
        d = self._entry(cfg["id"])
        if d.get("end_pending"):
            e = d["end_pending"]
            return Reading(active=False, finished=True, raw=e["state"], phase="End Of Cycle",
                           stamp=e["ended_at"], program=e.get("program", ""), reason="Afwasprogramma bevestigd voltooid")
        # A retained completion explains a currently confirmed OFF; it cannot
        # replace an unknown read after the appliance heartbeat was lost. The
        # one-shot end_pending event above still closes history at its original
        # event time, independently of later connectivity.
        if (reading.active is False and reading.gates.get("connection") is True
                and norm(reading.raw) == "off" and d.get("completion")
                and d.get("cycle", {}).get("status") == "completed"):
            return replace(reading, active=False, finished=True, reason="Afwasprogramma voltooid; toestel uit")
        return reading

    def overview(self, cfg, wall):
        d = self._entry(cfg["id"])
        q = d.get("request", {})
        cycle = d.get("cycle", {})
        context = q if self._valid_request(cfg, q) else None
        if context is None and self._valid_request(cfg, cycle.get("request")):
            context = cycle["request"]
        if context is None:
            context = self._cycle_request(cfg, d, cycle)
        context = context or {}
        ticket = self.r.dishwasher.tickets.get(cfg["id"], {})
        request_status = ("completed" if context and cycle.get("status") == "completed" else
                          "running" if context and cycle.get("status") == "running" else
                          "start_requested" if context and ticket.get("attempted") else
                          "waiting" if q else "consumed" if context else "none")
        e = d.get("completion")
        def iso(value):
            if not _finite_time(value) or value <= 0:
                return None
            try:
                return datetime.fromtimestamp(value, ZoneInfo(self.zone)).isoformat()
            except (ValueError, OverflowError, OSError):
                return None
        return {"arming_mode": cfg.get("dishwasher_arming_mode", "manual"),
                "app_request": bool(q), "request_context": bool(context), "request_status": request_status,
                "planned_day": context.get("planned_day"),
                "start_deadline": iso(context.get("deadline")), "not_before": iso(context.get("not_before")),
                "start_requested_at": iso(ticket.get("sent_at")) if context and ticket.get("created") == context.get("created") else None,
                "started_at": iso(cycle.get("started_at")),
                "start_confirmed_at": iso(cycle.get("start_confirmed_at")),
                "start_observed_at": iso(cycle.get("observed_at")),
                "deadline_due": self.due(cfg, wall), "after_deadline": cfg.get("dishwasher_after_deadline", "next_day"),
                "app_message": d.get("message", "Druk op Delay Start / APP op de afwasmachine"),
                "completion": {**e, "ended_at_local": iso(e["ended_at"])} if e else None,
                "cycle_status": cycle.get("status"),
                "airdry": norm(d.get("phase", "")) == "adodrying" and cycle.get("status") == "running"}
