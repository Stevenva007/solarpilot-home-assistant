"""Bounded, read-only research of witnessed SG requests and their stop reasons.

The research journal cannot start, renew, release or rearm an SG request. It
keeps observed request timing separate from compressor operation and from
causal extra power. A restored ON never becomes a witnessed session start.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
import math
import re
import time

from .const import VERSION

MAX_SESSIONS = 12
MAX_GAP_S = 30.0
INTERRUPTIONS = frozenset({"restart", "source_loss", "source_gap", "invalid_time", "shutdown", "binding_changed"})
TRANSPORT_OPERATIONS = frozenset({"read", "on", "renew", "off"})
TRANSPORT_PHASES = frozenset({"pending", "confirmed", "failed", "not_sent", "send_uncertain", "accepted_readback_unconfirmed"})
TRANSPORT_CATEGORIES = frozenset({"none", "timeout", "cancelled", "write_uncertain", "unavailable", "invalid_response",
    "contact_unconfirmed", "lease_unconfirmed", "mapping_or_setup_changed", "policy_changed", "unknown"})
POLICY_KEYS = ("import_threshold_w", "stop_delay_s", "min_session_s", "max_session_s",
               "expected_power_w", "threshold_w", "start_delay_s", "rest_s", "lease_s",
               "renew_s", "stale_s", "ack_timeout_s")
_NET_STOP = re.compile(r"^Netgrens overschreden: ([0-9]+(?:\.[0-9]+)?) W afname > ([0-9]+(?:\.[0-9]+)?) W$")
_RELEASE = re.compile(r"^\d+\.\d+\.\d+(?:-beta\.\d+)?$")
_IDENTITY = re.compile(r"^[0-9a-f]{32,64}$")
_MAX_REPORT_WALL = 4102444800.0
# Fixed diagnostic vocabulary. A rejected boundary does not grant permission
# and is not classified from a generic 'voorwaarden gewijzigd' message.
DISPATCH_REJECTION_REASONS = {
    "actuator_conflict": ("De SG-uitgang heeft een conflicterende toewijzing", "manual_or_configuration"),
    "cooling_context": ("De actuele koelcontext geeft geen SG-vrijgave", "unknown"),
    "runtime_closed": ("De regeling is afgesloten", "manual_or_configuration"),
    "runtime_mode": ("De actuele regelmodus geeft geen SG-vrijgave", "manual_or_configuration"),
    "removal_requested": ("Verwijdering van de regeling is aangevraagd", "manual_or_configuration"),
    "restart_blocking": ("Een opdrachtuitkomst na herstart is nog onzeker", "unknown"),
    "runtime_fault": ("Een actuele regelingsfout blokkeert SG", "unknown"),
    "pending_command": ("Een andere opdracht wacht op bevestiging", "unknown"),
    "handover": ("Een vermogensoverdracht is nog bezig", "unknown"),
    "battery_busy": ("De batterijregeling heeft een lopende opdracht", "unknown"),
    "site_source": ("De actuele zonne- en netmetingen zijn niet bruikbaar", "source_or_contact_fault"),
    "battery_discharge": ("De actuele batterijontlading overschrijdt de grens", "electrical_limit"),
    "priority": ("De actuele toestelvoorrang geeft geen SG-vrijgave", "unknown"),
    "wallbox_priority": ("De actuele Wallbox-voorrang vraagt vrijgave", "unknown"),
    "solar_threshold": ("Het actuele zonnebudget ligt onder de startdrempel", "unknown"),
    "settle": ("De actuele meet- of bezinktijd is nog niet vrijgegeven", "unknown"),
    "wallbox_headroom": ("De beschikbare ruimte naast de Wallbox is te klein", "electrical_limit"),
    "net_limit": ("De berekende netafname overschrijdt de vaste netgrens", "electrical_limit"),
    "soft_import_policy": ("De actuele zachte netafnamecontrole geeft geen SG-vrijgave", "unknown"),
    "phase_source": ("De actuele fasemetingen zijn niet bruikbaar", "source_or_contact_fault"),
    "phase_limit": ("De actuele fasegrens geeft geen SG-vrijgave", "electrical_limit"),
    "capacity_source": ("De actuele kwartiermeting is niet bruikbaar", "source_or_contact_fault"),
    "capacity_limit": ("De berekende netafname overschrijdt het kwartierbudget", "electrical_limit"),
    "permission_changed": ("De actuele SG-toestemming of configuratie is ingetrokken", "unknown"),
    "lease_unconfirmed": ("De bestaande SG-toestemming is niet actueel bevestigd", "source_or_contact_fault"),
    "dispatch_callback_error": ("De finale SG-controle kon niet worden afgerond", "unknown"),
    "dispatch_unexplained": ("De finale SG-controle wees af zonder specifieke oorzaak", "unknown"),
    "session_deadline": ("De begrensde SG-sessietijd laat geen nieuwe lokale termijn toe", "session_limit"),
    "manual_deadline": ("De tijdelijke handmatige SG-keuze laat geen nieuwe lokale termijn toe", "manual_or_configuration"),
}
DISPATCH_READING_KEYS = frozenset({"grid_w", "pv_w", "discharge_w", "reserve_w", "available_w", "eligible_w",
    "budget_oldest_reported_at", "residual_oldest_reported_at", "extra_w", "envelope_w", "projected_grid_w",
    "fixed_import_limit_w", "wallbox_headroom_w", "phase_headroom_w", "quarter_limit_w"})
DISPATCH_SOURCE_KEYS = ("site_grid", "site_pv", "hp_power", "soft_import", "phase_1", "phase_2", "phase_3", "quarter_average", "quarter_peak")


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


def clean_dispatch_rejection(value):
    """Bounded source-time evidence, never reconstructed from present sources."""
    value = _map(value)
    code = value.get("code")
    stamp = _number(value.get("evaluated_at"))
    if (type(value.get("schema")) is not int or value.get("schema") != 1
            or not isinstance(code, str) or code not in DISPATCH_REJECTION_REASONS
            or stamp is None or not 0 < stamp <= _MAX_REPORT_WALL or type(value.get("renewal")) is not bool):
        return None
    readings = _map(value.get("readings"))
    sources = _map(value.get("source_reports"))
    def source_stamp(raw):
        stamp = _number(raw)
        return stamp if stamp is not None and 0 < stamp <= _MAX_REPORT_WALL else None
    return {"schema": 1, "code": code, "reason": DISPATCH_REJECTION_REASONS[code][0],
        "evaluated_at": stamp, "renewal": value["renewal"],
        "readings": {key: source_stamp(readings[key]) if key.endswith("_reported_at") else _number(readings[key])
            for key in DISPATCH_READING_KEYS if key in readings},
        "source_reports": {key: {"watts": _number(_map(sources[key]).get("watts")),
            "reported_at": source_stamp(_map(sources[key]).get("reported_at"))}
            for key in DISPATCH_SOURCE_KEYS if key in sources}}


def effective_session_policy(config, effective_minimum_s, fixed_import_limit_w=None):
    """Capture policy at the command boundary; never reconstruct old policy."""
    policy = _current_policy({"effective_min_session_s": effective_minimum_s}, _map(config))
    policy["fixed_import_limit_w"] = _number(fixed_import_limit_w)
    return policy


def session_policy_hash(policy):
    """Hash exactly the exported policy, without mutable presentation options."""
    try:
        return hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(",", ":"),
            allow_nan=False).encode()).hexdigest()
    except (TypeError, ValueError):
        return None


def _original_reports(reports, labels):
    reports = _map(reports)
    cleaned_reports = {}
    for label in labels:
        report = _map(reports.get(label))
        cleaned = {}
        for key in ("watts", "temperature_c", "stamp", "until", "reported_at", "lease_remaining_s",
                    "timer_started_at", "timer_duration", "expires_at", "timer_expires_at"):
            if key in report:
                cleaned[key] = _number(report.get(key))
        for key in ("entity_id", "context", "signature", "source_signature", "binding_identity"):
            if isinstance(report.get(key), str):
                cleaned[key] = _text(report[key], 240)
        source = report.get("source")
        if isinstance(source, str):
            cleaned["source"] = _text(source)
        elif isinstance(source, (list, tuple)):
            cleaned["source"] = [_text(part) if isinstance(part, str) else None for part in source[:8]]
        for key in ("output", "confirmed", "state"):
            if type(report.get(key)) is bool:
                cleaned[key] = report[key]
        cleaned_reports[label] = cleaned if cleaned else None
    return cleaned_reports


def clean_session_provenance(value):
    """Historical evidence only. Invalid/absent legacy fields remain unknown."""
    value = _map(value)
    policy = _map(value.get("policy"))
    identity = value.get("command_identity")
    started = _number(value.get("started_at"))
    if (type(value.get("schema")) is not int or value.get("schema") != 1
            or _release(value.get("release")) is None or not _valid_policy(policy)
            or not isinstance(identity, str) or not _IDENTITY.fullmatch(identity)
            or value.get("owner") != "solarpilot" or started is None or started <= 0):
        return None
    frozen = effective_session_policy(policy, policy.get("effective_min_session_s"),
        policy.get("fixed_import_limit_w"))
    if value.get("policy_hash") != session_policy_hash(frozen):
        return None
    # These are the original reports, including their source timestamps. No
    # restore/export time is substituted for a missing historical source.
    cleaned_reports = _original_reports(value.get("source_reports"), ("grid", "solar", "tank", "native", "contact"))
    return {"schema": 1, "release": value["release"], "policy": frozen,
        "policy_hash": value["policy_hash"], "command_identity": identity,
        "owner": "solarpilot", "started_at": started,
        "command_issued_at": _number(value.get("command_issued_at")),
        "request_mode": value.get("request_mode") if value.get("request_mode") in ("automatic", "manual_on") else None,
        "binding_identity": _text(value.get("binding_identity"), 64) or None,
        "source_reports": cleaned_reports}


def _transport(value):
    """Only explicit transport telemetry, never derive a stage from UI text."""
    value = _map(value)
    stamp = _number(value.get("observed_at"))
    if (not all(isinstance(value.get(key), str) for key in ("operation", "phase", "category"))
            or value.get("operation") not in TRANSPORT_OPERATIONS or value.get("phase") not in TRANSPORT_PHASES
            or value.get("category") not in TRANSPORT_CATEGORIES or stamp is None or stamp <= 0):
        return None
    return {"operation": value["operation"], "phase": value["phase"], "category": value["category"],
            "observed_at": stamp, **{key: value.get(key) if type(value.get(key)) is bool else None
                for key in ("command_attempted", "command_applied")}}


def _contact(sg, now):
    stamp = _number(sg.get("relay_observed_at"))
    valid = (sg.get("relay_confirmed") is True and _fresh(stamp, now, sg.get("relay_stale_s"))
             and type(sg.get("relay_on")) is bool)
    return {"state": sg.get("relay_on") if valid else None, "reported_at": stamp if valid else None}


def _controller_stop(record, last, now=None):
    """A controller end is separate from contact confirmation or transport."""
    last = _map(last)
    original = clean_session_provenance(record.get("session_provenance"))
    if original is not None:
        ended_provenance = clean_session_provenance(last.get("session_provenance"))
        identity = (ended_provenance["command_identity"] if ended_provenance is not None
                    else last.get("command_identity"))
        if original["command_identity"] != identity:
            return None
    ended, duration, started = (_number(value) for value in
        (last.get("ended_at"), last.get("duration_s"), record.get("started_at")))
    lower = _number(record.get("start_lower_at"))
    if (record.get("known_start") is not True or lower is None or lower <= 0
            or ended is None or duration is None or started is None or ended < started
            or not 0 <= duration <= 86400 or ended - duration > started + 5
            or (lower is not None and ended - duration < lower - 30)
            or (now is not None and ended > now + 5)):
        return None
    evidence = clean_dispatch_rejection(last.get("stop_evidence"))
    if evidence is not None and not lower-30 <= evidence["evaluated_at"] <= ended+5:
        evidence = None
    result = {"ended_at": ended, "duration_s": duration, "reason": _text(last.get("reason")),
              "category": _category(last.get("reason"), evidence)}
    if evidence is not None:
        result["stop_evidence"] = evidence
    if original is not None:
        result["command_identity"] = original["command_identity"]
    return result


def _category(reason, stop_evidence=None):
    """Classify recorded controller reasons, without inferring unknown causes."""
    evidence = clean_dispatch_rejection(stop_evidence)
    if evidence is not None:
        return DISPATCH_REJECTION_REASONS[evidence["code"]][1]
    reason = _text(reason)
    if _NET_STOP.fullmatch(reason):
        return "hard_net_limit"
    if reason.startswith(("Kwartierbudget overschreden", "Elektrische grens", "Actuele fasebewaking", "Batterij ontlaadt")):
        return "electrical_limit"
    if reason == "Aanhoudende netafname; extra SG-aanvraag vrijgegeven":
        return "soft_cloud_import"
    if any(word in reason.casefold() for word in ("netmeting niet actueel", "betrouwbare actuele", "kwartierpiekmeting", "uitgangstatus", "niet bevestigd", "sg-uitgang niet bereikbaar")):
        return "source_or_contact_fault"
    if reason == "Bevestigde boost voltooid of geen extra opname":
        return "native_completion"
    if reason == "Begrensde SG-sessieduur bereikt":
        return "session_limit"
    if reason.startswith("SG-voorwaarden gewijzigd;"):
        # This legacy message also represented source/electrical/priority
        # rejection. Its actual historical gate cannot be reconstructed.
        return "unknown"
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
    policy = {key: _number(_map(policy).get(key)) for key in (
        "import_threshold_w", "stop_delay_s", "effective_min_session_s", "max_session_s", "stale_s")}
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
        # This is historical evidence, not a restorable active cursor. Even a
        # crash during an ON can only restore an interrupted, unknown ending.
        return {"schema": 1, "sessions": deepcopy(self.sessions[-MAX_SESSIONS:]),
                "checkpoint": self._interrupted_record("restart") if self.active is not None else None}

    def _interrupted_record(self, reason, *, now=None, sg=None):
        if self.active is None:
            return None
        record = deepcopy(self.active)
        observed = _number(record.get("last_observed_at"))
        started = _number(record.get("started_at"))
        record.update(interrupted=True, interruption=reason, source_complete=False, end_matched=False,
                      comparable=False, consistency="unknown", ended_at=None,
                      duration_s=max(0.0, observed-started) if observed is not None and started is not None else 0.0,
                      reason="", stop_category="unknown", contact_end={"state": None, "reported_at": None})
        if sg is not None and _number(now) is not None:
            record["controller_stop"] = _controller_stop(record, sg.get("last_session"), now)
            record["contact_end"] = _contact(sg, now)
            # A later successful status read must not replace the failed OFF.
            last_transport = (_transport(_map(sg.get("last_session")).get("transport"))
                              if record["controller_stop"] is not None else None)
            current_transport = _transport(sg.get("transport_evidence"))
            record["transport"] = next((value for value in (last_transport, current_transport)
                if value is not None and started is not None and started-5 <= value["observed_at"] <= now+5), None)
        return record

    def interrupt(self, reason, *, now=None, sg=None):
        """End evidence continuity without claiming the physical request ended."""
        if not isinstance(reason, str) or reason not in INTERRUPTIONS:
            reason = "source_loss"
        record = self._interrupted_record(reason, now=now, sg=sg)
        if record is not None:
            self.sessions.append(record)
            self.sessions = self.sessions[-MAX_SESSIONS:]
        self.active = self.previous = None
        self.latest = {}

    def restore(self, value):
        self.sessions, self.active, self.previous, self.latest = [], None, None, {}
        value = _map(value)
        records = value.get("sessions")
        if value.get("schema") != 1 or isinstance(value.get("schema"), bool) or not isinstance(records, list):
            return
        checkpoint = value.get("checkpoint")
        restore_now = _number(time.time())
        entries = [(record, False) for record in records[-MAX_SESSIONS:]]
        if isinstance(checkpoint, Mapping):
            entries.append((checkpoint, True))
        for record, checkpoint_record in entries:
            record = _map(record)
            ended, duration = _number(record.get("ended_at")), _number(record.get("duration_s"))
            interrupted = checkpoint_record or record.get("interrupted") is True
            observed, started = _number(record.get("last_observed_at")), _number(record.get("started_at"))
            if (duration is None or not 0 <= duration <= 86400
                    or (not interrupted and (ended is None or ended <= 0))
                    or (interrupted and (started is None or observed is None or not 0 < started <= observed
                                         or observed-started > 86400 or restore_now is None or observed > restore_now+5))):
                continue
            # Rebuild a bounded whitelist, never restore an active cursor/lease.
            cleaned = {key: deepcopy(record.get(key)) for key in (
                "release", "policy", "binding", "started_at", "start_lower_at", "ended_at", "duration_s",
                "reason", "stop_category", "known_start", "source_complete", "policy_unchanged",
                "end_matched", "grid_reports", "pv_reports", "contact_reports", "continuous_import_s",
                "max_grid_import_w", "native_context", "consistency", "gaps", "last_observed_at")}
            cleaned.update(ended_at=ended, duration_s=duration, reason=_text(record.get("reason")),
                           release=_release(record.get("release")), binding=_text(record.get("binding"), 64))
            cleaned["policy"] = _current_policy(_map(record.get("policy")), _map(record.get("policy")))
            cleaned["policy"]["fixed_import_limit_w"] = _number(_map(record.get("policy")).get("fixed_import_limit_w"))
            frozen_hash = record.get("policy_hash")
            cleaned["policy_hash"] = (frozen_hash if isinstance(frozen_hash, str)
                and frozen_hash == session_policy_hash(cleaned["policy"]) else None)
            cleaned["session_provenance"] = clean_session_provenance(record.get("session_provenance"))
            # Older research records stay useful history, but do not acquire a
            # newly invented command identity, original report or policy hash.
            original = _map(record.get("source_reports"))
            cleaned["source_reports"] = _original_reports(original, ("grid", "pv", "contact")) if original else None
            for key in ("known_start", "source_complete", "policy_unchanged", "end_matched"):
                cleaned[key] = record.get(key) is True
            for key in ("started_at", "start_lower_at", "continuous_import_s", "max_grid_import_w"):
                cleaned[key] = _number(record.get(key))
            for key in ("grid_reports", "pv_reports", "contact_reports", "gaps"):
                number = _number(record.get(key))
                cleaned[key] = min(1000000, max(0, int(number))) if number is not None else 0
            cleaned["stop_evidence"] = clean_dispatch_rejection(record.get("stop_evidence"))
            if (cleaned["stop_evidence"] is not None and (started is None or ended is None
                    or not started-30 <= cleaned["stop_evidence"]["evaluated_at"] <= ended+5)):
                cleaned["stop_evidence"] = None
            cleaned["stop_category"] = _category(cleaned["reason"], cleaned["stop_evidence"])
            cleaned["last_observed_at"] = observed
            cleaned["interrupted"] = interrupted
            cleaned["interruption"] = ("restart" if checkpoint_record else record.get("interruption")) if interrupted else None
            if not isinstance(cleaned["interruption"], str) or cleaned["interruption"] not in INTERRUPTIONS:
                cleaned["interruption"] = "source_loss" if interrupted else None
            cleaned["controller_stop"] = (_controller_stop(cleaned, record.get("controller_stop"), restore_now)
                                           if restore_now is not None else None)
            contact = _map(record.get("contact_end"))
            contact_stamp = _number(contact.get("reported_at"))
            contact_valid = (type(contact.get("state")) is bool and contact_stamp is not None
                             and started is not None and contact_stamp >= started
                             and restore_now is not None and contact_stamp <= restore_now+5)
            cleaned["contact_end"] = {"state": contact.get("state") if contact_valid else None,
                                      "reported_at": contact_stamp if contact_valid else None}
            cleaned["transport"] = _transport(record.get("transport"))
            if (cleaned["transport"] is not None and (restore_now is None or started is None
                    or not started-5 <= cleaned["transport"]["observed_at"] <= restore_now+5)):
                cleaned["transport"] = None
            if interrupted:
                cleaned.update(ended_at=None, reason="", stop_category="unknown", source_complete=False, end_matched=False)
                cleaned["duration_s"] = observed-started
            cleaned["native_context"] = record.get("native_context") if record.get("native_context") in (
                "space_heating", "space_cooling", "tapwater_heating", "sterilization") else None
            cleaned["consistency"] = self._consistency(cleaned)
            cleaned["comparable"] = cleaned["consistency"] in ("consistent_observation", "review_timing")
            self.sessions.append(cleaned)
        self.sessions = self.sessions[-MAX_SESSIONS:]

    @staticmethod
    def _consistency(record):
        if record.get("interrupted") is True:
            return "unknown"
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
                and record.get("policy_hash") == session_policy_hash(record.get("policy"))
                and bool(_map(record.get("source_reports")))
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
            self.interrupt("invalid_time")
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
        interrupted_now = False
        if self.active is not None:
            loss = (state is None or grid_value is None or pv_value is None)
            gap = (previous is None or not contiguous)
            rebound = (current["binding"] != self.active["binding"] or current["release"] != self.active["release"])
            if loss or gap or rebound:
                self.interrupt("binding_changed" if rebound else "source_loss" if loss else "source_gap", now=now, sg=sg)
                interrupted_now = True
        # Only newly witnessed OFF evidence may enrich an interrupted record.
        # It cannot close the source gap, restore continuity or change timing.
        for record in reversed(self.sessions):
            if record.get("interrupted") is not True or record.get("binding") != current["binding"]:
                continue
            stop = _controller_stop(record, sg.get("last_session"), now)
            if stop is None or stop["ended_at"] > now + 5:
                continue
            record["controller_stop"] = stop
            contact = _contact(sg, now)
            if (contact["state"] is False and contact["reported_at"] >= stop["ended_at"]
                    and _map(record.get("contact_end")).get("state") is not False):
                record["contact_end"] = contact
            transport = _transport(_map(sg.get("last_session")).get("transport"))
            if transport is not None:
                record["transport"] = transport
            break
        if state is True and self.active is None and not interrupted_now:
            known_start = bool(contiguous and previous["state"] is False
                               and current["relay_stamp"] is not None
                               and current["relay_stamp"] > previous["relay_stamp"]
                               and previous["now"] - 5 <= current["relay_stamp"] <= now + 5)
            task = _map(native.get("native_task"))
            provenance = clean_session_provenance(sg.get("active_session_provenance"))
            self.active = {"release": current["release"], "policy": deepcopy(policy),
                "policy_hash": session_policy_hash(policy), "session_provenance": provenance,
                "source_reports": {"grid": deepcopy(grid_value), "pv": deepcopy(pv_value),
                    "contact": _contact(sg, now)},
                "binding": current["binding"], "started_at": now, "start_lower_at": previous["now"] if known_start else None,
                "known_start": known_start, "source_complete": bool(grid_value and pv_value and _valid_policy(policy)),
                "policy_unchanged": True, "end_matched": False, "grid_reports": 0,
                "pv_reports": 0, "contact_reports": 0, "continuous_import_s": 0.0,
                "max_grid_import_w": 0.0, "gaps": 0,
                "last_observed_at": now, "interrupted": False, "interruption": None,
                "controller_stop": None, "contact_end": {"state": None, "reported_at": None},
                "transport": None,
                "native_context": task.get("function") if task.get("function") in ("space_heating", "space_cooling", "tapwater_heating", "sterilization") else None}
        active = self.active
        if active is not None:
            active["last_observed_at"] = now
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
                              stop_category=_category(last.get("reason"), last.get("stop_evidence")))
                stop = _controller_stop(active, last, now)
                if active.get("session_provenance") is not None and stop is None:
                    active.update(reason="", stop_category="unknown", end_matched=False)
                active.update(controller_stop=stop, contact_end=_contact(sg, now),
                    stop_evidence=stop.get("stop_evidence") if stop is not None else None,
                    transport=_transport(last.get("transport")) if stop is not None else None)
                active["consistency"] = self._consistency(active)
                active["comparable"] = active["consistency"] in ("consistent_observation", "review_timing")
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
    category = _category(last.get("reason"), last.get("stop_evidence"))
    release = _release(observed_last.get("release")) if observed_last is not None else _release(last.get("release"))
    last_metrics = {"release": release, "duration_s": _number(last.get("duration_s")),
                    "ended_at": _number(last.get("ended_at")), "stop_category": category,
                    "historical": release != VERSION if release is not None else None,
                    "session_provenance": clean_session_provenance(last.get("session_provenance")),
                    "policy_hash": last.get("policy_hash") if isinstance(last.get("policy_hash"), str) else None,
                    "command_identity": last.get("command_identity") if isinstance(last.get("command_identity"), str) else None,
                    "transport": _transport(last.get("transport")), "reason": _text(last.get("reason"))}
    last_metrics["stop_evidence"] = clean_dispatch_rejection(last.get("stop_evidence"))
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
    interrupted = [record for record in records if record.get("interrupted") is True]
    item["metrics"].update(completed_sessions=len(records)-len(interrupted), interrupted_sessions=len(interrupted),
                           comparable_sessions=len(comparable), timing_review_sessions=len(reviews))
    if interrupted:
        item["evidence"].append(f"{len(interrupted)} onderzoeksperiode(n) onderbroken; einde en meetcontinuïteit blijven onbekend en valideren de timers niet.")
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
