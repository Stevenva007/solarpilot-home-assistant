"""AEG/Electrolux start-only adapter. Never switches power or interrupts a cycle.

All entity names and accepted states are explicit configuration. A one-shot user
preparation ticket plus live device interlocks are required for every START.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
import math
import re
import time
from .dishwasher_priority import PRIORITY_DEFAULTS

UNKNOWN = {"", "unknown", "unavailable", "none", "null", "disconnected"}
DISHWASHER_DEFAULTS = {
    **PRIORITY_DEFAULTS,
    "dishwasher_stale_s": 300,
    "dishwasher_ready_states": "Ready To Start;Ready;Idle",
    "dishwasher_running_states": "Running;Washing;Prewash;Pre wash;Main wash;Rinsing;Drying;Ado Drying;Paused",
    "dishwasher_finished_states": "End Of Cycle;Finished;End;Completed;Cycle finished",
    "dishwasher_connected_states": "Connected",
    "dishwasher_remote_states": "Enabled;Remote Control Enabled",
    "dishwasher_closed_states": "off;Closed",
    "dishwasher_safe_states": "off;No alerts;No alarms;OK;0",
    "dishwasher_mapping_confirmed": False,
    "dishwasher_ticket_hours": 24,
    "dishwasher_delay_entity": "",
    "dishwasher_phase_entity": "", "dishwasher_alert_mode": "state",
    "dishwasher_arming_mode": "manual", "dishwasher_start_deadline": "13:00:00",
    "dishwasher_after_deadline": "next_day", "dishwasher_deadline_grid_allowed": True,
    "dishwasher_deadline_grace_min": 120,
    "dishwasher_alert_entity": "",
}
REFERENCE_KEYS = ("start_button", "dishwasher_state_entity", "dishwasher_connection_entity",
                  "dishwasher_remote_entity", "dishwasher_door_entity", "cycle_program_entity",
                  "dishwasher_alert_entity", "dishwasher_delay_entity", "dishwasher_phase_entity")


def norm(value):
    return re.sub(r"[\s_\-]+", "", str(value or "").casefold())


def accepted(value):
    return {norm(x) for x in str(value or "").split(";") if x.strip()}


def settings(cfg):
    return {**DISHWASHER_DEFAULTS, **cfg}


def normalize_config(cfg):
    if cfg.get("kind") != "dishwasher":
        return cfg
    # These are invariants, not optional UI hints. Never inherit switch actuators.
    out = {**DISHWASHER_DEFAULTS, **cfg, "non_interruptible": True,
           "allow_wallbox_reclaim": False, "manual_hold_s": max(60, cfg.get("manual_hold_s", 60))}
    for key in ("control_entity", "number_entity", "start_script", "stop_script", "active_entity"):
        out.pop(key, None)
    return out


def config_errors(hass, cfg):
    c = settings(cfg)
    errors = {}
    for key in PRIORITY_DEFAULTS:
        if not isinstance(c.get(key), bool):
            errors[key] = "invalid_selection"
    required = REFERENCE_KEYS[:6]
    for key in required:
        eid = c.get(key, "")
        obj = hass.states.get(eid) if eid else None
        domains = ("button",) if key == "start_button" else (("select", "sensor", "input_select") if key == "cycle_program_entity" else ("sensor", "binary_sensor"))
        if not eid or obj is None or eid.split(".")[0] not in domains:
            errors[key] = "entity_missing"
        elif key == "start_button" and obj.attributes.get("restored"):
            errors[key] = "dishwasher_restored"
    for key in REFERENCE_KEYS[6:]:
        if c.get(key) and hass.states.get(c[key]) is None:
            errors[key] = "entity_missing"
    maps = [accepted(c[k]) for k in ("dishwasher_ready_states", "dishwasher_running_states", "dishwasher_finished_states")]
    if any(not v for v in maps) or any(maps[i] & maps[j] for i in range(3) for j in range(i+1, 3)):
        errors["dishwasher_ready_states"] = "dishwasher_state_overlap"
    for key in ("dishwasher_ready_states", "dishwasher_running_states", "dishwasher_finished_states",
                "dishwasher_connected_states", "dishwasher_remote_states", "dishwasher_closed_states"):
        if accepted(c[key]) & {norm(v) for v in UNKNOWN}:
            errors[key] = "dishwasher_unknown_state"
    if cfg.get("dishwasher_mapping_confirmed"):
        try:
            from homeassistant.helpers import entity_registry as er
            reg = er.async_get(hass)
            rows = [reg.async_get(c.get(k)) for k in required]
            ids = {getattr(row, "device_id", None) for row in rows}
            if None in ids or len(ids) != 1:
                errors["base"] = "dishwasher_same_device"
        except AttributeError:
            errors["base"] = "dishwasher_same_device"
    from datetime import time as clock_time
    try:
        clock_time.fromisoformat(str(c["dishwasher_start_deadline"]))
    except ValueError:
        errors["dishwasher_start_deadline"] = "time"
    for key, allowed in (("dishwasher_arming_mode", ("manual", "app")),
                         ("dishwasher_after_deadline", ("next_day", "same_day")),
                         ("dishwasher_alert_mode", ("state", "aeg_attributes"))):
        if c[key] not in allowed:
            errors[key] = "invalid_selection"
    if c["dishwasher_arming_mode"] == "app" and str(c["dishwasher_remote_states"]) != "Enabled":
        errors["dishwasher_remote_states"] = "dishwasher_exact_remote"
    return errors


def fresh(hass, eid, age, wall):
    obj = hass.states.get(eid) if eid else None
    if obj is None or norm(obj.state) in {norm(x) for x in UNKNOWN} or obj.attributes.get("restored"):
        return None
    try:
        stamp = getattr(obj, "last_reported", obj.last_updated).timestamp()
    except (AttributeError, ValueError, TypeError):
        return None
    return obj if -5 <= wall - stamp <= age else None


@dataclass
class Reading:
    active: bool | None = None
    ready: bool = False
    finished: bool = False
    reason: str = "Afwasmachinestatus onbekend"
    raw: str = ""
    stamp: float = 0.0
    program: str = ""
    phase: str = ""


def read(hass, cfg, wall=None):
    c, wall = settings(cfg), time.time() if wall is None else wall
    age = c["dishwasher_stale_s"]
    obj = fresh(hass, c.get("dishwasher_state_entity"), age, wall)
    link = fresh(hass, c.get("dishwasher_connection_entity"), age, wall)
    r = Reading(raw=str(getattr(obj, "state", "")))
    if link is None or norm(link.state) not in accepted(c["dishwasher_connected_states"]):
        r.reason = "Afwasmachine offline of terugmelding te oud"
        return r
    if obj is None:
        return r
    r.stamp = getattr(obj, "last_reported", obj.last_updated).timestamp()
    r.phase = str(obj.state)[:80]
    val = norm(obj.state)
    if val in accepted(c["dishwasher_running_states"]):
        r.active, r.reason = True, "Beschermd afwasprogramma actief; niet onderbreken"
    elif val in accepted(c["dishwasher_finished_states"]):
        r.active, r.finished, r.reason = False, True, "Afwasprogramma voltooid"
    elif val in accepted(c["dishwasher_ready_states"]):
        r.active, r.reason = False, "Afwasmachine gereed"
    elif val == "off":
        r.active, r.reason = False, "Toestel uit; einde niet bevestigd"
        return r
    else:
        r.reason = "Afwasmachinestatus niet herkend: " + str(obj.state)[:80]
        return r
    prog = fresh(hass, c.get("cycle_program_entity"), age, wall)
    r.program = str(prog.state)[:80] if prog else ""
    if c.get("dishwasher_phase_entity"):
        phase = fresh(hass, c["dishwasher_phase_entity"], age, wall)
        r.phase = str(phase.state)[:80] if phase else "onbekend"
    if r.active or r.finished:
        return r
    if not c.get("dishwasher_mapping_confirmed"):
        r.reason = "AEG-startknop en statuskoppelingen nog niet bevestigd"
        return r
    for key, values, label in (
        ("dishwasher_remote_entity", "dishwasher_remote_states", "Start op afstand niet bevestigd"),
        ("dishwasher_door_entity", "dishwasher_closed_states", "Deur niet aantoonbaar gesloten"),
    ):
        value = fresh(hass, c.get(key), age, wall)
        exact_remote = key == "dishwasher_remote_entity" and c.get("dishwasher_arming_mode") == "app"
        if value is None or (str(value.state) != "Enabled" if exact_remote else norm(value.state) not in accepted(c[values])):
            r.reason = label
            return r
    if not prog:
        r.reason = "Programmakeuze ontbreekt of is verouderd"
        return r
    if c.get("dishwasher_delay_entity"):
        obj_delay = fresh(hass, c["dishwasher_delay_entity"], age, wall)
        try:
            delay = float(obj_delay.state) if obj_delay else math.nan
        except (TypeError, ValueError):
            delay = math.nan
        if not math.isfinite(delay) or delay != 0:
            r.reason = "Eigen uitgestelde start van afwasmachine actief of onbekend"
            return r
    if c.get("dishwasher_alert_entity"):
        alert = fresh(hass, c["dishwasher_alert_entity"], age, wall)
        safe = alert is not None and norm(alert.state) in accepted(c["dishwasher_safe_states"])
        if c.get("dishwasher_alert_mode") == "aeg_attributes":
            # The aggregate includes consumable warnings. Never whitelist a numeric
            # count such as 2: inspect explicit alarm flags from the AEG API instead.
            flags = {k: v for k, v in getattr(alert, "attributes", {}).items()
                     if k.startswith("DISH_ALARM_") and k not in
                     ("DISH_ALARM_RINSE_AID_LOW", "DISH_ALARM_SALT_MISSING")}
            safe = bool(alert and flags) and all(str(v) == "OFF" for v in flags.values())
        if not safe:
            r.reason = "Afwasmachine meldt een alarm of onbekende alarmstatus"
            return r
    button = hass.states.get(c.get("start_button", ""))
    # A never-pressed HA button legitimately reports 'unknown'. Other guards
    # provide live connectivity; button timestamps are not telemetry timestamps.
    if button is None or str(button.state).lower() == "unavailable" or button.attributes.get("restored"):
        r.reason = "AEG START-knop ontbreekt of is onbeschikbaar"
        return r
    r.ready = True
    return r


class DishwasherControl:
    """Durable one-cycle preparation tickets and explicit START outcome tracking."""
    def __init__(self):
        self.tickets = {}
        self.readings = {}
        self.profiles = {}
        self.live = {}
        self.previous = {}

    def snapshot(self):
        return {"tickets": deepcopy(self.tickets), "profiles": deepcopy(self.profiles)}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        self.tickets = {str(k): dict(v) for k, v in list(data.get("tickets", {}).items())[:100] if isinstance(v, dict)}
        self.profiles = {str(k): v[-12:] for k, v in list(data.get("profiles", {}).items())[:100] if isinstance(v, list)}
        # No reconstructed phase consumption across an offline interval.
        self.live = {}
        self.previous = {}

    def arm(self, cfg, reading, wall):
        if reading.active is not False or not reading.ready:
            raise ValueError(reading.reason)
        old = self.tickets.get(cfg["id"], {})
        if old.get("attempted"):
            raise ValueError("Vorige START-uitkomst eerst controleren; geen automatische herhaalopdracht")
        self.tickets[cfg["id"]] = {"armed": True, "program": reading.program, "created": wall,
                                    "expires": wall + settings(cfg)["dishwasher_ticket_hours"] * 3600,
                                    "attempted": False, "confirmed": False}

    def permitted(self, cfg, r, wall):
        ticket = self.tickets.get(cfg["id"], {})
        if not r.ready:
            return False, r.reason
        if ticket.get("attempted"):
            return False, "START al verzonden; geen tweede poging zonder controle"
        if not ticket.get("armed"):
            return False, "Klaarzetten voor één automatische afwasbeurt"
        if wall < float(ticket.get("not_before", 0)):
            return False, "Klaargezet na deadline; wacht op volgende dag " + str(ticket.get("planned_day", ""))
        if wall >= float(ticket.get("expires", 0)):
            return False, "Starttoestemming verlopen; opnieuw klaarzetten"
        if ticket.get("program") != r.program:
            return False, "Programma gewijzigd; opnieuw klaarzetten"
        return True, "Klaargezet; wacht op zon en planning"

    def sent(self, cfg, wall):
        t = self.tickets[cfg["id"]]
        t.update(armed=False, attempted=True, confirmed=False, sent_at=wall)

    def confirmed(self, device_id):
        self.tickets.setdefault(device_id, {}).update(armed=False, attempted=False, confirmed=True)

    def cancel(self, device_id):
        self.tickets.setdefault(device_id, {})["armed"] = False

    def review(self, device_id):
        self.tickets[device_id] = {"armed": False, "attempted": False, "confirmed": False}

    def observe(self, cfg, r, power, wall, max_gap=30):
        """Stage profile from a dedicated power meter, never inferred as zero."""
        i = cfg["id"]
        if power is not None and (not isinstance(power, (int, float)) or not math.isfinite(power) or power < 0):
            power = None
        old = self.previous.get(i)
        self.previous[i] = r
        self.readings[i] = r
        ticket = self.tickets.get(i, {})
        if ticket.get("armed") and ((r.program and r.program != ticket.get("program")) or r.reason == "Deur niet aantoonbaar gesloten"):
            self.cancel(i)
        if r.active:
            self.cancel(i)  # Manual starts also consume any preparation ticket.
        if r.active and old is not None and old.active is False:
            self.live[i] = {"start": wall, "last": wall, "program": r.program or "onbekend",
                            "phase": r.phase, "power": power, "stages": {}, "covered_s": 0,
                            "energy_kwh": 0, "gap": False}
        session = self.live.get(i)
        if not session:
            return
        if r.active is None or (r.active and (not r.program or r.program != session["program"])):
            session["gap"] = True
        dt = wall - session["last"]
        prior_w = session["power"]
        if 0 < dt <= max_gap and prior_w is not None:
            stage = session["stages"].setdefault(session["phase"], {"seconds": 0., "kwh": 0., "peak_w": 0., "samples": 0})
            stage["seconds"] += dt
            stage["kwh"] += prior_w * dt / 3_600_000
            stage["peak_w"] = max(stage["peak_w"], prior_w)
            stage["samples"] += 1
            session["covered_s"] += dt
            session["energy_kwh"] += prior_w * dt / 3_600_000
        elif dt > max_gap or r.active is None or prior_w is None:
            session["gap"] = True
        session.update(last=wall, phase=r.phase, power=power)
        result = None
        if r.active is False:
            duration = max(0, wall - session["start"])
            coverage = min(1., session["covered_s"] / max(1., duration))
            if r.finished and duration >= 60 and coverage >= .95 and not session["gap"]:
                result = {"program": session["program"], "start": session["start"], "end": wall,
                          "duration_s": duration, "energy_kwh": session["energy_kwh"],
                          "coverage": coverage, "stages": session["stages"], "source": "exclusive_power_meter"}
                self.profiles.setdefault(i, []).append(result)
                self.profiles[i] = self.profiles[i][-12:]
            self.live.pop(i, None)
        return result

    def overview(self, cfg, wall=None):
        wall = time.time() if wall is None else wall
        i = cfg["id"]
        r = self.readings.get(i, Reading())
        allowed, reason = self.permitted(cfg, r, wall)
        ticket = self.tickets.get(i, {})
        profiles = self.profiles.get(i, [])
        return {"ready": r.ready, "prepared": allowed, "ticket_armed": bool(ticket.get("armed")),
                "attempted": bool(ticket.get("attempted")), "gate_reason": reason,
                "phase": r.phase, "program": r.program, "source_age_s": round(max(0, wall-r.stamp), 1) if r.stamp else None,
                "profile_count": len(profiles), "last_measured_profile": profiles[-1] if profiles else None,
                "profile_note": "Exclusief gemeten cyclusprofielen" if profiles else "Nog geen volledig gemeten cyclus; fasen zijn onbekend, niet 0 W",
                "power_source": "Shelly/toestelmeter" if cfg.get("power_entity") else "Handmatige vermogensschatting; geen meting",
                "non_interruptible": True, "actuator": "button.press only"}
