"""Observe native Wallbox activity, without commanding or blaming anything.

Exact native status names follow Home Assistant's Wallbox ChargerStatus enum
and the integration's documented green-energy status. A configured solar mode
alone is never evidence of a waiting reason, a full battery or a stop cause.
"""
from __future__ import annotations

from copy import deepcopy
import math


def _finite(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _text(value):
    return str(value).strip()[:160] if value is not None else ""


def _positive_time(value):
    stamp = _finite(value)
    return stamp if stamp is not None and stamp > 0 else None


def _get(reading, key, default=None):
    return reading.get(key, default) if isinstance(reading, dict) else getattr(reading, key, default)


# Exact matches only, not substrings and never an inference from Full Solar.
_STATUS = {
    "waiting in queue by eco-smart": ("waiting", "solar", "Wallbox wacht op zonnestroom", True),
    "waiting for green energy": ("waiting", "solar", "Wallbox wacht op zonnestroom", True),
    "paused": ("idle", "paused", "Laden gepauzeerd volgens Wallbox; wie of wat pauzeerde is niet gemeld", True),
    "scheduled": ("waiting", "schedule", "Wallbox wacht op zijn eigen laadschema", True),
    "waiting for car demand": ("waiting", "car", "Wallbox wacht tot de auto om laden vraagt", True),
    "waiting in queue by power boost": ("waiting", "power_boost", "Wallbox wacht op ruimte volgens Power Boost", True),
    "waiting in queue by power sharing": ("waiting", "power_sharing", "Wallbox wacht op zijn vermogensverdeling", True),
    "waiting mid failed": ("waiting", "meter", "Wallbox meldt een probleem met zijn MID-meter", True),
    "waiting mid safety margin exceeded": ("waiting", "meter_safety", "Wallbox meldt dat de MID-veiligheidsmarge is overschreden", True),
    "disconnected": ("idle", "connection", "Wallbox meldt een verbroken verbinding; verdere stopoorzaak niet gemeld", True),
    "locked": ("idle", "locked", "Wallbox meldt dat hij vergrendeld is", True),
    "locked, car connected": ("idle", "locked", "Wallbox meldt vergrendeld, met auto aangesloten", True),
    "error": ("idle", "error", "Wallbox meldt een fout; bekijk de fabrikantmelding", True),
    "updating": ("waiting", "update", "Wallbox meldt dat hij wordt bijgewerkt", True),
    "ready": ("idle", "unknown", "Wallbox is gereed maar laadt niet; exacte stopoorzaak niet gemeld", False),
    "waiting": ("waiting", "unknown", "Wallbox wacht; de fabrikant meldt niet waarop", False),
    "charging": ("waiting", "unknown", "Geen laadvermogen gemeten; Wallbox meldt nog Charging, stopoorzaak niet bevestigd", False),
}


_EVENT_TEXT = ("stop_reason", "native_status", "native_mode", "session_value", "end_state")
_EVENT_NUMBERS = ("observed_start_at", "last_charging_report_at", "observed_stop_at", "stop_report_at",
                  "status_report_at", "unavailable_observed_at", "previous_power_w", "power_w")
_EVENT_FLAGS = ("start_confirmed", "stop_confirmed", "cause_reported", "telemetry_gap")
_UNKNOWN_STOP_REASON = "Laadstop waargenomen; exacte stopoorzaak niet gelijktijdig door de Wallbox bevestigd"


def classify_native_status(status, demand=None):
    """Describe a current native status without granting any control right."""
    return _STATUS.get(_text(status).casefold(), (
        "waiting" if demand is True else "idle", "unknown",
        "Wallbox laadt niet; exacte wacht- of stopoorzaak is niet gemeld", False))


class WallboxActivityHistory:
    """Keep up to 30 observed charging endings, not inferred physical causes."""

    def __init__(self, *, stale_s=300, charging_threshold_w=50, max_records=30):
        self.stale_s = max(1.0, _finite(stale_s) or 300.0)
        self.charging_threshold_w = max(1.0, _finite(charging_threshold_w) or 50.0)
        count = _finite(max_records)
        self.max_records = max(1, min(30, int(count) if count is not None else 30))
        self.events = []
        self.ongoing = None
        self.current = self._unknown("Nog geen actuele Wallbox-meting")
        self._last_known_active = None
        self._last_stamp = None
        self._restored_gap = False
        self._restore_needs_time_check = False

    @staticmethod
    def _unknown(reason, *, status="", mode="", session="", age=None,
                 status_stamp=None, status_age=None):
        return {"known": False, "active": False, "state": "unknown", "label": "Laadstatus onbekend",
                "reason": reason, "waiting_for": "unknown", "cause_reported": False,
                "native_status": status, "native_mode": mode, "session_value": session,
                "power_w": None, "report_timestamp": None, "age_s": age,
                "status_report_timestamp": status_stamp, "status_age_s": status_age,
                "solar_pilot_cause_proven": False}

    def _end_gap(self, now, reason):
        if self.ongoing is None:
            return
        event = {**self.ongoing, "observed_stop_at": None, "stop_report_at": None,
                 "status_report_at": None,
                 "unavailable_observed_at": now, "stop_confirmed": False,
                 "cause_reported": False, "telemetry_gap": True, "end_state": "unconfirmed",
                 "stop_reason": reason, "power_w": None, "native_status": "",
                 "native_mode": "", "session_value": "", "solar_pilot_cause_proven": False}
        self.events.append(event)
        self.events = self.events[-self.max_records:]
        self.ongoing = None

    def update(self, reading, now_wall, *, grid_w=None, pv_w=None, free_w=None, enabled=True):
        now = _finite(now_wall)
        if now is None:
            return self.overview()
        if self._restore_needs_time_check:
            self._restore_needs_time_check = False
            if self._last_stamp is not None and self._last_stamp > now + 5:
                self._last_stamp = None
            if self.ongoing is not None and (
                    self.ongoing["observed_start_at"] > now + 5
                    or self.ongoing["last_charging_report_at"] > now + 5):
                # A corrupt/future restored session is not evidence of either a
                # start or a telemetry-gap stop in the current wall-clock era.
                self.ongoing = None
                self._restored_gap = False
        status = _text(_get(reading, "status"))
        mode = _text(_get(reading, "raw_mode"))
        session = _text(_get(reading, "session_value"))
        power = _finite(_get(reading, "power_w"))
        stamp = _finite(_get(reading, "stamp"))
        status_stamp = _positive_time(_get(reading, "status_stamp"))
        reported_age = _finite(_get(reading, "age_s"))
        actual_age = now - stamp if stamp is not None else None
        status_age = now - status_stamp if status_stamp is not None else None
        status_fresh = bool(status_age is not None and -5 <= status_age <= self.stale_s)
        fresh = bool(enabled and _get(reading, "valid") is True and power is not None and power >= 0
                     and stamp is not None and stamp > 0 and actual_age is not None
                     and -5 <= actual_age <= self.stale_s
                     and reported_age is not None and -5 <= reported_age <= self.stale_s)
        if self._restored_gap:
            self._end_gap(now, "Laadperiode liep vóór de herstart; einde tijdens de onderbreking niet bevestigd")
            self._restored_gap = False
        if not fresh:
            reason = ("Wallbox-monitor uitgeschakeld; actuele laadstatus niet gecontroleerd" if not enabled else
                      _text(_get(reading, "issue")) or "Wallbox-metingen ontbreken, zijn ongeldig of te oud")
            self._end_gap(now, "Wallbox-meting onderbroken; laadstop en exacte oorzaak niet bevestigd")
            self._last_known_active = None
            self.current = self._unknown(reason, status=status, mode=mode, session=session,
                                         age=actual_age if actual_age is not None else reported_age,
                                         status_stamp=status_stamp, status_age=status_age)
            return self.overview()

        if self._last_stamp is not None and stamp - self._last_stamp > self.stale_s:
            # A hung/stopped observer might see no invalid intermediate tick.
            # A fresh current sample does not bridge that missing history.
            self._end_gap(now, "Te lange onderbreking tussen Wallbox-rapporten; laadstop en oorzaak niet bevestigd")
            self._last_known_active = None

        active = power >= self.charging_threshold_w
        if active:
            state, waiting, reason, cause = "charging", "none", "Actueel laadvermogen gemeten; de Wallbox regelt het laden zelf", False
            label = "Auto laadt"
        else:
            state, waiting, reason, cause = classify_native_status(
                status if status_fresh else "", _get(reading, "demand"))
            label = "Wacht op zonnestroom" if waiting == "solar" else "Laden gepauzeerd" if waiting == "paused" else "Auto wacht" if state == "waiting" else "Auto laadt niet"
        self.current = {
            "known": True, "active": active, "state": state, "label": label, "reason": reason,
            "waiting_for": waiting, "cause_reported": cause, "native_status": status,
            "native_mode": mode, "session_value": session, "power_w": power,
            "report_timestamp": stamp, "age_s": max(actual_age, reported_age),
            "status_report_timestamp": status_stamp, "status_age_s": status_age,
            "solar_pilot_cause_proven": False,
            "site_context": {"grid_w": _finite(grid_w), "pv_w": _finite(pv_w), "free_w": _finite(free_w),
                             "proves_stop_cause": False},
        }
        # Repeated cloud snapshots may remain fresh; they are not new evidence
        # of a start or stop and must not create duplicate history entries.
        if self._last_stamp is not None and stamp <= self._last_stamp:
            return self.overview()
        if active:
            if self.ongoing is None:
                self.ongoing = {"observed_start_at": now, "start_confirmed": self._last_known_active is False,
                                "last_charging_report_at": stamp, "previous_power_w": power}
            else:
                self.ongoing["last_charging_report_at"] = stamp
                self.ongoing["previous_power_w"] = power
        elif self.ongoing is not None:
            cause_correlated = bool(cause and status_stamp is not None
                                    and self.ongoing.get("last_charging_report_at") is not None
                                    and status_stamp > self.ongoing["last_charging_report_at"]
                                    and abs(status_stamp - stamp) <= 5)
            self.events.append({**self.ongoing, "observed_stop_at": now, "stop_report_at": stamp,
                                "status_report_at": status_stamp,
                                "unavailable_observed_at": None, "stop_confirmed": True,
                                "cause_reported": cause_correlated, "telemetry_gap": False, "end_state": "stopped",
                                "stop_reason": reason if not cause or cause_correlated else _UNKNOWN_STOP_REASON,
                                "power_w": power, "native_status": status,
                                "native_mode": mode, "session_value": session, "solar_pilot_cause_proven": False})
            self.events = self.events[-self.max_records:]
            self.ongoing = None
        self._last_known_active = active
        self._last_stamp = stamp
        return self.overview()

    def snapshot(self):
        return {"version": 1, "events": deepcopy(self.events[-self.max_records:]),
                "ongoing": deepcopy(self.ongoing), "last_report_stamp": self._last_stamp}

    def restore(self, payload):
        self.events, self.ongoing = [], None
        self.current = self._unknown("Wacht op een nieuwe actuele Wallbox-meting na herstart")
        self._last_known_active, self._last_stamp, self._restored_gap = None, None, False
        self._restore_needs_time_check = False
        if not isinstance(payload, dict) or payload.get("version") != 1:
            return
        rows = payload.get("events")
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict) or _positive_time(row.get("observed_start_at")) is None:
                    continue
                clean = {key: _text(row.get(key)) for key in _EVENT_TEXT}
                clean.update({key: _finite(row.get(key)) for key in _EVENT_NUMBERS})
                for key in ("observed_start_at", "last_charging_report_at", "observed_stop_at",
                            "stop_report_at", "status_report_at", "unavailable_observed_at"):
                    clean[key] = _positive_time(row.get(key))
                clean.update({key: row.get(key) is True for key in _EVENT_FLAGS})
                clean["solar_pilot_cause_proven"] = False
                start, last_charge = clean["observed_start_at"], clean["last_charging_report_at"]
                stop, report = clean["observed_stop_at"], clean["stop_report_at"]
                sane_end = (stop is not None and report is not None and last_charge is not None
                            and stop >= start and report > last_charge and report <= stop + 5)
                if not sane_end:
                    clean["stop_confirmed"] = False
                    clean["observed_stop_at"] = None
                    clean["stop_report_at"] = None
                native = _STATUS.get(clean["native_status"].casefold())
                native_cause = native[3] if native else False
                status_report = clean["status_report_at"]
                correlated = bool(status_report is not None and last_charge is not None and report is not None
                                  and status_report > last_charge and abs(status_report-report) <= 5)
                clean["cause_reported"] = bool(clean["cause_reported"] and native_cause and correlated)
                if clean["stop_confirmed"]:
                    clean["stop_reason"] = (native[2] if native and (not native_cause or correlated)
                                            else _UNKNOWN_STOP_REASON)
                if not clean["stop_confirmed"]:
                    clean["cause_reported"] = False
                    clean["end_state"] = "unconfirmed"
                self.events.append(clean)
            self.events = self.events[-self.max_records:]
        ongoing = payload.get("ongoing")
        if isinstance(ongoing, dict):
            start = _positive_time(ongoing.get("observed_start_at"))
            last_charge = _positive_time(ongoing.get("last_charging_report_at"))
            previous_power = _finite(ongoing.get("previous_power_w"))
            structurally_valid = bool(start is not None and last_charge is not None
                                      and last_charge >= start-self.stale_s
                                      and previous_power is not None
                                      and previous_power >= self.charging_threshold_w)
            if structurally_valid:
                self.ongoing = {"observed_start_at": start,
                                "start_confirmed": ongoing.get("start_confirmed") is True,
                                "last_charging_report_at": last_charge,
                                "previous_power_w": previous_power}
                self._restored_gap = True
        self._last_stamp = _positive_time(payload.get("last_report_stamp"))
        self._restore_needs_time_check = True

    def overview(self):
        return {"current": deepcopy(self.current), "last_stop": deepcopy(self.events[-1]) if self.events else None,
                "history": deepcopy(list(reversed(self.events))), "retained_events": len(self.events),
                "ongoing": deepcopy(self.ongoing), "read_only": True,
                "note": "Tijdstippen zijn waarnemingen van Home Assistant, niet het exacte fysieke meetmoment. "
                        "Een fabrikantstatus kan een wachtreden melden; SolarPilot bewijst daarmee niet de oorzaak van een laadstop."}
