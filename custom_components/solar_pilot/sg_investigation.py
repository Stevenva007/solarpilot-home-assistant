"""Bounded, read-only research of witnessed SG requests and their stop reasons.

The research journal cannot start, renew, release or rearm an SG request. It
keeps observed request timing separate from compressor operation and from
causal extra power. A restored ON never becomes a witnessed session start.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import math
import re

from .const import VERSION

MAX_SESSIONS = 12
MAX_GAP_S = 30.0
POLICY_KEYS = ("import_threshold_w", "stop_delay_s", "min_session_s", "max_session_s",
               "expected_power_w", "threshold_w", "start_delay_s", "rest_s", "lease_s",
               "renew_s", "stale_s", "ack_timeout_s")
_NET_STOP = re.compile(r"^Netgrens overschreden: ([0-9]+(?:\.[0-9]+)?) W afname > ([0-9]+(?:\.[0-9]+)?) W$")
_RELEASE = re.compile(r"^\d+\.\d+\.\d+(?:-beta\.\d+)?$")


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return float(value) if math.isfinite(value) else None
    except (OverflowError, ValueError):
        return None


def _map(value):
    return value if isinstance(value, Mapping) else {}


def _fresh(stamp, now, stale):
    stamp, stale = _number(stamp), _number(stale)
    return (stamp is not None and stamp > 0 and stale is not None and 0 < stale <= 600
            and -5 <= now - stamp < stale)


def _text(value, limit=240):
    return value[:limit] if isinstance(value, str) else ""


def _release(value):
    return value if isinstance(value, str) and len(value) <= 40 and _RELEASE.fullmatch(value) else None


def _category(reason):
    """Classify recorded controller reasons, without inferring unknown causes."""
    reason = _text(reason)
    if _NET_STOP.fullmatch(reason):
        return "hard_net_limit"
    if reason.startswith(("Kwartierbudget overschreden", "Elektrische grens", "Actuele fasebewaking", "Batterij ontlaadt")):
        return "electrical_limit"
    if reason == "Aanhoudende netafname; extra SG-aanvraag vrijgegeven":
        return "soft_cloud_import"
    if any(word in reason.casefold() for word in ("netmeting niet actueel", "betrouwbare actuele", "kwartierpiekmeting", "uitgangstatus", "niet bevestigd")):
        return "source_or_contact_fault"
    if reason == "Bevestigde boost voltooid of geen extra opname":
        return "native_completion"
    if reason == "Begrensde SG-sessieduur bereikt":
        return "session_limit"
    if any(word in reason.casefold() for word in ("handmatig", "uitgeschakeld", "afsluiten", "herstart", "gewijzigd")):
        return "manual_or_configuration"
    return "unknown"


def _current_policy(sg, config):
    values = {key: _number(config.get(key)) for key in POLICY_KEYS}
    # The overview is the effective current view, not an uploaded recommendation.
    for key in ("import_threshold_w", "stop_delay_s", "min_session_s"):
        if key in sg:
            values[key] = _number(sg.get(key))
    values["effective_min_session_s"] = _number(sg.get("effective_min_session_s"))
    values["profile"] = config.get("profile") if config.get("profile") in ("dhw_only", "general") else None
    return values


def _valid_policy(policy):
    return (policy.get("import_threshold_w") is not None and 0 <= policy["import_threshold_w"] <= 20000
            and policy.get("stop_delay_s") is not None and 5 <= policy["stop_delay_s"] <= 600
            and policy.get("effective_min_session_s") is not None and 0 <= policy["effective_min_session_s"] <= 14400
            and policy.get("max_session_s") is not None and 300 <= policy["max_session_s"] <= 14400
            and policy["effective_min_session_s"] <= policy["max_session_s"]
            and policy.get("stale_s") is not None and 15 <= policy["stale_s"] <= 600)


def _request_state(sg, now):
    stale = sg.get("relay_stale_s")
    if (sg.get("configured") is not True or not _fresh(sg.get("observed_at"), now, stale)
            or sg.get("relay_confirmed") is not True
            or not _fresh(sg.get("relay_observed_at"), now, stale)):
        return None, None
    source_until = _number(sg.get("relay_observed_at")) + _number(stale)
    if sg.get("relay_on") is False and sg.get("desired_on") is False:
        return False, source_until
    deadline = _number(sg.get("relay_valid_until"))
    lease = _number(sg.get("lease_remaining_s"))
    if (sg.get("relay_on") is True and sg.get("desired_on") is True
            and sg.get("owner") == "solarpilot" and sg.get("lease_confirmed") is True
            and deadline is not None and deadline > now and lease is not None and lease > 0):
        return True, min(source_until, deadline, now + lease)
    return None, None


def _reading(value, now, stale):
    """Import-only P1 from _sg_import_observation, or nonnegative PV watts."""
    value = _map(value)
    watts, stamp = _number(value.get("watts")), _number(value.get("stamp"))
    source = value.get("source")
    if (watts is None or not 0 <= watts <= 100000 or not _fresh(stamp, now, stale)
            or value.get("restored") is True or value.get("estimated") is True
            or not isinstance(source, (str, tuple, list)) or not source):
        return None
    # Bindings remain an opaque identity; there is no new discovery permission.
    return {"watts": watts, "stamp": stamp, "until": stamp + stale,
            "source": _text(source) if isinstance(source, str) else tuple(_text(part) for part in source)}


class SGSessionResearch:
    """At most twelve completed records; no replay or continuity after restore."""

    def __init__(self):
        self.sessions = []
        self.active = None
        self.previous = None
        self.latest = {}

    def snapshot(self):
        return {"schema": 1, "sessions": deepcopy(self.sessions[-MAX_SESSIONS:])}

    def restore(self, value):
        self.sessions, self.active, self.previous, self.latest = [], None, None, {}
        value = _map(value)
        records = value.get("sessions")
        if value.get("schema") != 1 or isinstance(value.get("schema"), bool) or not isinstance(records, list):
            return
        for record in records[-MAX_SESSIONS:]:
            record = _map(record)
            ended, duration = _number(record.get("ended_at")), _number(record.get("duration_s"))
            if ended is None or ended <= 0 or duration is None or not 0 <= duration <= 86400:
                continue
            # Rebuild a bounded whitelist, never restore an active cursor/lease.
            cleaned = {key: deepcopy(record.get(key)) for key in (
                "release", "policy", "binding", "started_at", "start_lower_at", "ended_at", "duration_s",
                "reason", "stop_category", "known_start", "source_complete", "policy_unchanged",
                "end_matched", "grid_reports", "pv_reports", "contact_reports", "continuous_import_s",
                "max_grid_import_w", "native_context", "consistency", "gaps")}
            cleaned.update(ended_at=ended, duration_s=duration, reason=_text(record.get("reason")),
                           release=_release(record.get("release")), binding=_text(record.get("binding"), 64))
            cleaned["policy"] = _current_policy(_map(record.get("policy")), _map(record.get("policy")))
            cleaned["policy"]["fixed_import_limit_w"] = _number(_map(record.get("policy")).get("fixed_import_limit_w"))
            for key in ("known_start", "source_complete", "policy_unchanged", "end_matched"):
                cleaned[key] = record.get(key) is True
            for key in ("started_at", "start_lower_at", "continuous_import_s", "max_grid_import_w"):
                cleaned[key] = _number(record.get(key))
            for key in ("grid_reports", "pv_reports", "contact_reports", "gaps"):
                number = _number(record.get(key))
                cleaned[key] = min(1000000, max(0, int(number))) if number is not None else 0
            cleaned["stop_category"] = _category(cleaned["reason"])
            cleaned["native_context"] = record.get("native_context") if record.get("native_context") in (
                "space_heating", "space_cooling", "tapwater_heating", "sterilization") else None
            cleaned["consistency"] = self._consistency(cleaned)
            self.sessions.append(cleaned)

    @staticmethod
    def _consistency(record):
        lower, started, ended, duration = (_number(record.get(key)) for key in (
            "start_lower_at", "started_at", "ended_at", "duration_s"))
        chronology = (lower is not None and started is not None and ended is not None
            and duration is not None and 0 < lower <= started <= ended and 0 <= duration <= 86400
            and 0 <= started-lower <= MAX_GAP_S
            and lower-30 <= ended-duration <= started+5)
        reports = all(_number(record.get(key)) is not None and _number(record[key]) >= 2
                      for key in ("grid_reports", "pv_reports", "contact_reports"))
        if not (record.get("known_start") is True and record.get("source_complete") is True
                and record.get("policy_unchanged") is True and record.get("end_matched") is True
                and _valid_policy(_map(record.get("policy"))) and _release(record.get("release"))
                and chronology and reports and _number(record.get("gaps")) == 0):
            return "unknown"
        if record.get("stop_category") != "soft_cloud_import":
            return "separate_stop_reason"
        policy = record["policy"]
        duration, above = _number(record.get("duration_s")), _number(record.get("continuous_import_s"))
        if duration is None or above is None:
            return "unknown"
        if duration + MAX_GAP_S < policy["effective_min_session_s"] or above + 2 * MAX_GAP_S < policy["stop_delay_s"]:
            return "review_timing"
        return "consistent_observation"

    def observe(self, now, sg, native, *, grid=None, context=None):
        now, sg, native, context = _number(now), _map(sg), _map(native), _map(context)
        if now is None or now <= 0:
            self.previous = None
            if self.active is not None:
                self.active["source_complete"] = False
                self.active["gaps"] += 1
            return
        policy = _current_policy(sg, _map(context.get("policy")))
        policy["fixed_import_limit_w"] = _number(context.get("fixed_import_limit_w"))
        state, deadline = _request_state(sg, now)
        grid_value = _reading(grid, now, policy.get("stale_s")) if policy.get("stale_s") is not None else None
        pv_value = _reading(context.get("pv"), now, policy.get("stale_s")) if policy.get("stale_s") is not None else None
        current = {"now": now, "state": state, "until": deadline, "grid": grid_value,
                   "pv": pv_value, "relay_stamp": _number(sg.get("relay_observed_at")),
                   "release": _release(context.get("release")), "policy": policy,
                   "binding": _text(context.get("binding"), 64)}
        self.latest = deepcopy(current)
        previous = self.previous
        contiguous = (previous is not None and 0 < now - previous["now"] <= MAX_GAP_S
                      and previous["until"] is not None and previous["until"] >= now)
        if state is True and self.active is None:
            known_start = bool(contiguous and previous["state"] is False
                               and current["relay_stamp"] is not None
                               and current["relay_stamp"] > previous["relay_stamp"]
                               and previous["now"] - 5 <= current["relay_stamp"] <= now + 5)
            task = _map(native.get("native_task"))
            self.active = {"release": current["release"], "policy": deepcopy(policy),
                "binding": current["binding"], "started_at": now, "start_lower_at": previous["now"] if known_start else None,
                "known_start": known_start, "source_complete": bool(grid_value and pv_value and _valid_policy(policy)),
                "policy_unchanged": True, "end_matched": False, "grid_reports": 0,
                "pv_reports": 0, "contact_reports": 0, "continuous_import_s": 0.0,
                "max_grid_import_w": 0.0, "gaps": 0,
                "native_context": task.get("function") if task.get("function") in ("space_heating", "space_cooling", "tapwater_heating", "sterilization") else None}
        active = self.active
        if active is not None:
            active["policy_unchanged"] = (active["policy_unchanged"] and policy == active["policy"]
                and current["release"] == active["release"] and current["binding"] == active["binding"])
            paired = bool(contiguous and previous["state"] is True and state in (True, False)
                and grid_value and pv_value and previous["grid"] and previous["pv"]
                and previous["grid"]["until"] >= now and previous["pv"]["until"] >= now
                and grid_value["source"] == previous["grid"]["source"]
                and pv_value["source"] == previous["pv"]["source"]
                and grid_value["stamp"] >= previous["grid"]["stamp"]
                and pv_value["stamp"] >= previous["pv"]["stamp"]
                and current["relay_stamp"] >= previous["relay_stamp"])
            paired = paired and _valid_policy(policy)
            if previous is not None and previous["state"] is True and not paired:
                active["source_complete"] = False
                active["gaps"] += 1
                active["continuous_import_s"] = 0.0
            if paired:
                if grid_value["watts"] > policy["import_threshold_w"] and previous["grid"]["watts"] > policy["import_threshold_w"]:
                    active["continuous_import_s"] += now - previous["now"]
                else:
                    active["continuous_import_s"] = 0.0
            for label, reading in (("grid", grid_value), ("pv", pv_value)):
                if reading is not None and (previous is None or previous[label] is None or reading["stamp"] > previous[label]["stamp"]):
                    active[label + "_reports"] += 1
            if current["relay_stamp"] is not None and (previous is None or previous["relay_stamp"] is None or current["relay_stamp"] > previous["relay_stamp"]):
                active["contact_reports"] += 1
            if grid_value is not None:
                active["max_grid_import_w"] = max(active["max_grid_import_w"], grid_value["watts"])
            if state is False:
                last = _map(sg.get("last_session"))
                ended, duration = _number(last.get("ended_at")), _number(last.get("duration_s"))
                start_lower = _number(active.get("start_lower_at"))
                matched = bool(previous is not None and ended is not None and duration is not None and 0 <= duration <= 86400
                    and previous["now"] - 5 <= ended <= now + 5 and start_lower is not None
                    and start_lower - 30 <= ended - duration <= active["started_at"] + 5)
                active.update(ended_at=ended if ended is not None else now, duration_s=duration if duration is not None else max(0.0, now-active["started_at"]),
                              reason=_text(last.get("reason")), end_matched=matched,
                              stop_category=_category(last.get("reason")))
                active["consistency"] = self._consistency(active)
                self.sessions.append(deepcopy(active))
                self.sessions = self.sessions[-MAX_SESSIONS:]
                self.active = None
        self.previous = current


def assessment(runtime, now, sg=None, research=None):
    """Current observations and bounded suggestions; never a control decision."""
    manager = getattr(runtime, "sg_boost", None)
    if sg is None:
        overview = getattr(manager, "overview", None)
        sg = overview() if callable(overview) else {}
    sg = _map(sg)
    policy = _current_policy(sg, _map(getattr(manager, "settings", None)))
    policy["fixed_import_limit_w"] = _number(_map(getattr(runtime, "settings", None)).get("max_import_w"))
    last = _map(sg.get("last_session"))
    records = research.sessions if isinstance(research, SGSessionResearch) else []
    observed_last = next((record for record in reversed(records)
        if _number(last.get("ended_at")) is not None and record.get("ended_at") == last.get("ended_at")
        and record.get("duration_s") == last.get("duration_s") and record.get("reason") == last.get("reason")), None)
    category = _category(last.get("reason"))
    release = _release(observed_last.get("release")) if observed_last is not None else _release(last.get("release"))
    last_metrics = {"release": release, "duration_s": _number(last.get("duration_s")),
                    "ended_at": _number(last.get("ended_at")), "stop_category": category,
                    "historical": release != VERSION if release is not None else None}
    item = {"id": "sg_policy", "title": "SG-duur en stopredenen", "status": "collecting",
        "summary": "Nieuwe SG-sessies worden onderzocht; de huidige timers zijn nog niet met een complete sessie beoordeeld.",
        "next_action": "Volg een nieuwe, normaal toegelaten SG-sessie met actuele net-, zonne- en contactmetingen.",
        "evidence": [], "hypotheses": [], "proposals": [],
        "metrics": {"current_release": VERSION, "effective_policy": policy, "last_session": last_metrics,
                    "completed_sessions": 0, "comparable_sessions": 0, "timing_review_sessions": 0,
                    "current_request_active": None}}
    if sg.get("configured") is False:
        item.update(status="not_configured", summary="Er is geen SG-uitgang gekoppeld.",
                    next_action="Onderzoek van SG-sessies begint pas bij een bestaande, bevestigde SG-koppeling.")
        return item
    if not sg:
        item["evidence"].append("Actuele SG-brongegevens ontbreken; er wordt geen sessie of instelling aangenomen.")
        return item
    valid_now = _number(now)
    if valid_now is not None:
        item["metrics"]["current_request_active"] = _request_state(sg, valid_now)[0]
    if _valid_policy(policy):
        item["evidence"].append(f"Huidige zachte grens: {policy['import_threshold_w']:g} W gedurende {policy['stop_delay_s']:g} s; effectieve minimumduur {policy['effective_min_session_s']:g} s.")
    else:
        item.update(status="check_needed", summary="De effectieve SG-instellingen zijn niet volledig betrouwbaar beschikbaar.")
    if last:
        if release is None:
            item["evidence"].append("De oudere laatste-sessieregistratie bevat geen softwareversie, bevroren beleid of volledige brondekking; zij valideert de huidige timers niet.")
        elif release != VERSION:
            item["evidence"].append(f"De laatste sessie komt uit {release}; deze historische sessie valideert de timers van {VERSION} niet.")
        else:
            item["evidence"].append("Een sessieversie alleen bewijst geen ononderbroken brondekking of gelijk gebleven instellingen.")
    if category in ("hard_net_limit", "electrical_limit"):
        item["hypotheses"].append("Een elektrische grens kan de SG-aanvraag vóór twintig minuten vrijgeven; de wolkenbuffer verlengt deze grens niet.")
        item["proposals"].append({"id": "sg_electrical_context", "kind": "investigation",
            "text": "Vergelijk een nieuwe elektrische grensstop met de gelijktijdige overige lasten. Behoud de vaste net- en fasegrenzen en de raming voor bijkomende SG-opname."})
    elif category == "source_or_contact_fault":
        item["hypotheses"].append("Een weggevallen meting of contactbevestiging kan vroeg vrijgeven verklaren, los van de zachte importtimer.")
    elif category == "native_completion":
        item["evidence"].append("De geregistreerde stop meldt native voltooiing of geen opname; deze stop hoort niet bij de zachte wolkenbuffer.")
    elif category == "manual_or_configuration":
        item["evidence"].append("De geregistreerde stop betreft bediening, herstart of configuratie; dit is geen test van de zachte importtimer.")
    elif category == "soft_cloud_import":
        item["hypotheses"].append("Beoordeel een zachte netafnamestop alleen tegen het beleid dat tijdens die volledige sessie gold.")
    comparable = [record for record in records if record.get("release") == VERSION and record.get("policy") == policy
                  and record.get("consistency") in ("consistent_observation", "review_timing")
                  and valid_now is not None and _number(record.get("ended_at")) is not None
                  and record["ended_at"] <= valid_now + 5]
    reviews = [record for record in comparable if record["consistency"] == "review_timing"]
    item["metrics"].update(completed_sessions=len(records), comparable_sessions=len(comparable), timing_review_sessions=len(reviews))
    if isinstance(research, SGSessionResearch):
        item["metrics"]["active_session_start_known"] = research.active.get("known_start") if research.active else None
        item["metrics"]["recent_sessions"] = deepcopy(records[-MAX_SESSIONS:])
        latest = research.latest
        grid = _map(latest.get("grid"))
        cap = _number(_map(getattr(runtime, "settings", None)).get("max_import_w"))
        expected = policy.get("expected_power_w")
        if (valid_now is not None and _fresh(grid.get("stamp"), valid_now, policy.get("stale_s"))
                and _number(grid.get("watts")) is not None and grid["watts"] > 0
                and latest.get("policy") == policy and cap is not None and cap >= 0):
            room = max(0.0, cap - grid["watts"])
            item["metrics"].update(fixed_import_limit_w=cap, current_grid_import_w=grid["watts"], fixed_import_room_w=room,
                                   fixed_limit_extra_deficit_w=max(0.0, expected-room) if expected is not None else None)
            if expected is not None and expected > room:
                item["evidence"].append(f"Bij de vaste netgrens ontbreekt {expected-room:g} W voor de geraamde bijkomende SG-opname. Afzonderlijke fase-, kwartier- en voorrangsvoorwaarden blijven gelden.")
    if comparable and not reviews:
        item.update(status="observed_ok", summary=f"{len(comparable)} complete sessie(s) met het huidige beleid tonen een zachte vrijgave die past bij de waargenomen timing.",
                    next_action="Blijf stopredenen en brondekking volgen; één type sessie bewijst geen algemene warmtepompreactie.")
    if reviews:
        item.update(status="check_needed", summary="Een complete sessie vraagt controle van de zachte vrijgavetiming.",
                    next_action="Vergelijk de contacttijdlijn en oorspronkelijke netrapporten met de geregistreerde stop; pas geen grenzen automatisch aan.")
        item["proposals"].append({"id": "sg_timing_trace", "kind": "investigation",
            "text": "Controleer de nieuwe sessietijdlijn op een vroege zachte stop. Herhaal bij gelijk beleid en complete bronnen voordat een wijziging aan de regeling wordt voorgesteld."})
    if _text(sg.get("fault")):
        item.update(status="check_needed", summary="De actuele SG-bron of contactbevestiging vraagt controle.")
    if not comparable:
        item["proposals"].append({"id": "sg_complete_session", "kind": "investigation",
            "text": "Registreer een complete nieuwe SG-sessie met versie, effectief beleid, originele bronrapporten en stopreden. Beoordeel 600 W/vijf minuten en de vrijgave rond minuut twintig; behoud instellingen en veiligheidsgrenzen."})
    return item
