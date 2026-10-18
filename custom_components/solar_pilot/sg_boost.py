"""One leased SG contact; Panasonic remains the sole heat-pump controller.

The manager owns no temperature target, climate command, heater permission or
cloud retry. A local Shelly deadline is required for each ON and renewal. A
confirmed journal may continue the same live lease after fresh current checks;
it never replays an old ON or restores a timer without current evidence.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import inspect
import hashlib
import json
import math
import time
import uuid

from homeassistant.exceptions import HomeAssistantError

from .sg_config import DISPLAY_ONLY_KEYS, actuator_conflicts, finite, normalize_config, validate_config
from .const import VERSION
from .sg_investigation import (clean_dispatch_rejection, clean_session_provenance,
    effective_session_policy, session_policy_hash)

# Anti-repeat evidence thresholds, not Panasonic targets or comfort settings.
NEW_STORAGE_DROP_C = 2.0
NEW_STORAGE_CONFIRM_S = 300.0
NEW_CONTEXT_CONFIRM_S = 300.0
RELEVANT_NATIVE_CONTEXTS = frozenset({"space_heating", "space_cooling", "tapwater_heating"})
_UNSET_RESIDUAL = object()


class SGBoostManager:
    def __init__(self, runtime, adapter=None, clock=None):
        self.runtime = runtime
        self.settings = normalize_config(runtime.entry.options.get("sg_boost", {}))
        self.config = self.settings
        self._adapter = adapter
        self._injected_adapter = adapter is not None
        self._clock = clock or time.monotonic
        self._wall_clock = clock or time.time
        self._lock = asyncio.Lock()
        self._generation = 0
        self._session = 0
        self._started = False
        self._closed = False
        self._in_flight = False
        self._restart_release = False
        self._restored_expiry = None
        self._restart_resume = None
        self._manual_control = None
        self._manual_deadline = None
        self._manual_session_started = None
        self._lease_duration = None
        self._binding_identity = None
        self._off_attempted = False
        self._possibly_owned = False
        self.owned = False
        self.desired_on = False
        self.relay_on = None
        self.relay_confirmed = False
        self._relay_observed_at = None
        self._relay_valid_until = None
        self._relay_binding_identity = None
        self._request_rest_off_current = False
        self.panasonic_confirmed = None
        self.manual_hold = False
        self.completion_hold = False
        self.fault = ""
        self.fault_code = ""
        self.state = "normal"
        self.status = "Panasonic regelt zelfstandig"
        self.reason = "Automatische zonneboost staat uit"
        self._stable_since = None
        self._start_soft_since = None
        self._start_soft_kind = None
        self._start_source_identity = None
        self._start_source_stamp = None
        self._start_last_evaluated = None
        self._import_since = None
        self._import_observation = None
        self._import_policy = None
        self._session_started = None
        self._minimum_started = None
        self._session_finishing = False
        self._rest_until = 0.0
        self._rest_until_wall = None
        self._request_rest_policy = None
        self._suppress_saves = False
        self._last_renewed = None
        self._lease_expiry = None
        self._lease_deadline = None
        self._next_read = 0.0
        self._read_failures = 0
        self._blocked_reasons = []
        self._physical = {}
        self._tank_observation = None
        self._need_reference = None
        self._need_candidate = None
        self._tank_source_changed = False
        self._last_rearm = None
        self._last_session = None
        self._session_provenance = None
        self._hold_origin = None
        self._transport_evidence = None
        self._dispatch_rejection = None
        self._native_observation = {}
        self._solar_observation = None
        self._general_reference = None
        self._session_reference = None
        self._general_candidate = None
        self._general_reset_candidate = None
        self._hold_provenance = None
        self._hold_reason = ""
        self._profile_change_release = False
        self._low_uptake_noted = False
        self._low_uptake_since = None
        self._low_uptake_stamp = None
        self._commissioned_fingerprint = None
        self._observed_fingerprint = None
        self.sent_this_tick = False
        self.renewed_this_tick = False

    @property
    def configured(self):
        return bool(self.settings.get("entity_id"))

    @property
    def busy(self):
        # A lease ending does not fabricate an OFF observation. It does bound
        # the lifetime of our authority, even if the transport is unreachable.
        valid_lease = self._lease_deadline is None or self._clock() < self._lease_deadline
        return self._in_flight or self._restart_release or ((self.owned or self._possibly_owned) and valid_lease)

    @property
    def action_required(self):
        """Ordinary solar/rest waits never create a control notification."""
        return bool(self.fault)

    @property
    def auto_enabled(self):
        return self.settings.get("enabled") is True

    def _control_identity(self, settings=None):
        source = self.settings if settings is None else settings
        value = {key: value for key, value in source.items() if key not in DISPLAY_ONLY_KEYS}
        try:
            return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                             allow_nan=False).encode()).hexdigest()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _historical_provenance(value):
        """Preserve an optional original identity; never fill an older record."""
        cleaned = clean_session_provenance(value)
        if cleaned is None:
            return None
        binding = value.get("binding_identity") if isinstance(value, dict) else None
        if binding is not None and (not isinstance(binding, str) or len(binding) != 64
                or any(char not in "0123456789abcdef" for char in binding)):
            return None
        if isinstance(value, dict) and "control_identity" in value:
            identity = value["control_identity"]
            if (not isinstance(identity, str) or len(identity) != 64
                    or any(char not in "0123456789abcdef" for char in identity)):
                return None
            cleaned["control_identity"] = identity
        return cleaned

    @property
    def manual_mode(self):
        value = self._manual_control
        if (not isinstance(value, dict) or self._manual_deadline is None
                or self._clock() >= self._manual_deadline
                or self._wall_clock() >= value["expires_at"]):
            return "auto"
        return value["mode"]

    def _manual_overview(self):
        mode = self.manual_mode
        value = self._manual_control if mode != "auto" else {}
        remaining = (max(0.0, min(self._manual_deadline-self._clock(),
                                 value["expires_at"]-self._wall_clock())) if value else 0)
        return {"mode": mode, "duration_s": value.get("duration_s"),
                "expires_at": value.get("expires_at"), "remaining_s": math.ceil(remaining),
                "active": mode != "auto", "returns_to": "auto"}

    def _session_checkpoint(self):
        if self._restart_resume is not None:
            return deepcopy(self._restart_resume)
        if (not self.owned or not self.desired_on or self._session_started is None
                or self._minimum_started is None or self._last_renewed is None
                or not self._commissioned_fingerprint or self._lease_duration is None):
            return None
        now, wall = self._clock(), self._wall_clock()
        return {"schema": 1, "control_identity": self._control_identity(),
                "fingerprint": deepcopy(self._commissioned_fingerprint),
                "binding_identity": self._binding_identity,
                "started_at": wall-(now-self._session_started),
                "minimum_started_at": wall-(now-self._minimum_started),
                "renewed_at": wall-(now-self._last_renewed),
                "lease_duration_s": self._lease_duration,
                "import_started_at": wall-(now-self._import_since) if self._import_since is not None else None,
                "import_observation": deepcopy(self._import_observation),
                "import_policy": list(self._import_policy) if self._import_policy is not None else None,
                "session_provenance": deepcopy(self._session_provenance)}

    def update_config(self, value):
        """Apply effective options; a changed binding is never an old lease."""
        updated = normalize_config(value)
        old_entity = self.settings.get("entity_id")
        old_tank_entity = self.settings.get("tank_temperature_entity")
        old_profile = self.settings.get("profile", "dhw_only")
        old_profile_confirmed = self.settings.get("profile_confirmed") is True
        native_sources_changed = any(updated.get(key) != self.settings.get(key) for key in (
            "activity_entity", "zone_entities", "tank_target_entity"))
        new_confirmation = (self.settings.get("watchdog_confirmed") is not True
                            and updated.get("watchdog_confirmed") is True
                            and updated.get("commissioning_confirmed") is True)
        # Meter interpretation is presentation metadata. Editing it must not
        # revoke an in-flight dispatch or restart the stable-solar window.
        control_changed = any(updated.get(key) != self.settings.get(key)
                              for key in updated if key not in DISPLAY_ONLY_KEYS)
        if control_changed:
            self._generation += 1
            self._stable_since = None
            self._manual_control = self._manual_deadline = None
            self._restart_resume = None
            if updated.get("enabled") is not True:
                self.desired_on = False
            if updated.get("entity_id") != old_entity:
                if self.busy or self.relay_on is True:
                    raise HomeAssistantError("Geef de huidige SG-aanvraag eerst vrij voordat de uitgang verandert.")
                self._adapter = None if not self._injected_adapter else self._adapter
                self._started = False
                self.manual_hold = False
                self.completion_hold = False
                self.relay_on = None
                self.relay_confirmed = False
                self._relay_observed_at = None
                self._relay_valid_until = None
                self._relay_binding_identity = None
                self._request_rest_off_current = False
                self._lease_expiry = self._lease_deadline = None
                self._commissioned_fingerprint = self._observed_fingerprint = None
        if (updated.get("tank_temperature_entity") != old_tank_entity
                and (self.completion_hold or self.owned or self._need_reference)):
            self._tank_source_changed = True
            self._need_candidate = None
        self.settings = updated
        scope_changed = updated.get("profile", "dhw_only") != old_profile
        scope_confirmed = (updated.get("profile") == "general"
                           and updated.get("profile_confirmed") is True
                           and (scope_changed or not old_profile_confirmed))
        if scope_changed:
            self.desired_on = False
            self._profile_change_release = self.owned or self._possibly_owned
            self._general_reference = None
            self._general_candidate = self._general_reset_candidate = None
        if scope_confirmed and self.completion_hold:
            self._convert_legacy_hold()
        elif native_sources_changed and self._general_reference is not None:
            # Selecting another reader is not evidence of new native demand.
            self._general_reference.update(signature=None, native_stamp=None,
                native_reset_stamp=None, profile_transition=False,
                native_rebase=True, native_after=self._wall_clock())
            self._general_candidate = self._general_reset_candidate = None
        if new_confirmation and self.fault_code == "firmware_changed":
            if not self._injected_adapter:
                self._adapter = None
            self._commissioned_fingerprint = deepcopy(self._observed_fingerprint)
            self.fault_code = self.fault = ""
        self.config = self.settings

    def snapshot(self):
        """Store evidence only; configuration remains the enable authority."""
        return {"schema": 1, "relay_entity": self.settings.get("entity_id", ""),
                "owned": bool(self.owned or self._possibly_owned or self._restart_release),
                "lease_expiry": self._lease_expiry,
                "session_checkpoint": self._session_checkpoint(),
                "manual_control": deepcopy(self._manual_control),
                "manual_hold": self.manual_hold, "completion_hold": self.completion_hold,
                "session_finishing": self._session_finishing,
                "rest_until_wall": self._rest_until_wall,
                "request_rest_policy": self._request_rest_policy,
                "fault_code": self.fault_code, "last_session": deepcopy(self._last_session),
                "commissioned_fingerprint": deepcopy(self._commissioned_fingerprint),
                "need_reference": deepcopy(self._need_reference),
                "tank_source_changed": self._tank_source_changed,
                "last_rearm": deepcopy(self._last_rearm),
                "profile": self.settings.get("profile", "dhw_only"),
                "hold_reason": self._hold_reason,
                "general_reference": deepcopy(self._general_reference),
                "session_reference": deepcopy(self._session_reference),
                "session_provenance": deepcopy(self._session_provenance),
                "hold_origin": deepcopy(self._hold_origin),
                "hold_provenance": deepcopy(self._hold_provenance)}

    def restore(self, stored):
        """Restore bounded evidence; no command or ownership comes from bytes."""
        if not isinstance(stored, dict) or stored.get("schema") != 1:
            return
        if stored.get("relay_entity") != self.settings.get("entity_id"):
            return
        self.manual_hold = stored.get("manual_hold") is True
        self.completion_hold = stored.get("completion_hold") is True or stored.get("session_finishing") is True
        self._restart_release = stored.get("owned") is True and not self.manual_hold
        self._restored_expiry = finite(stored.get("lease_expiry"))
        self._lease_expiry = self._restored_expiry
        manual = stored.get("manual_control")
        if (isinstance(manual, dict) and manual.get("schema") == 1
                and manual.get("mode") in ("on", "off")
                and type(manual.get("duration_s")) is int and manual["duration_s"] in (1800, 3600)
                and self._control_identity() is not None and manual.get("control_identity") == self._control_identity()
                and finite(manual.get("created_at")) is not None and finite(manual.get("expires_at")) is not None
                and 0 <= self._wall_clock()-manual["created_at"]
                and manual["expires_at"]-manual["created_at"] == manual["duration_s"]
                and 0 < manual["expires_at"]-self._wall_clock() <= manual["duration_s"]):
            self._manual_control = deepcopy(manual)
            self._manual_deadline = self._clock()+manual["expires_at"]-self._wall_clock()
            origin = finite(manual.get("session_started_at"))
            if origin is not None and (origin > self._wall_clock() or origin < manual["created_at"]-float(self.settings["max_session_s"])):
                self._manual_control = self._manual_deadline = None
            elif origin is not None:
                self._manual_session_started = self._clock()-(self._wall_clock()-origin)
        checkpoint = stored.get("session_checkpoint")
        anchors = [finite(checkpoint.get(key)) for key in ("started_at", "minimum_started_at", "renewed_at")] if isinstance(checkpoint, dict) else []
        duration = finite(checkpoint.get("lease_duration_s")) if isinstance(checkpoint, dict) else None
        if (self._restart_release and isinstance(checkpoint, dict) and checkpoint.get("schema") == 1
                and self._control_identity() is not None and checkpoint.get("control_identity") == self._control_identity()
                and isinstance(checkpoint.get("fingerprint"), dict) and checkpoint["fingerprint"]
                and all(value is not None for value in anchors)
                and 0 <= self._wall_clock()-anchors[0] < float(self.settings["max_session_s"])
                and anchors[0] <= anchors[1] <= anchors[2] <= self._wall_clock()
                and duration is not None and 60 <= duration <= float(self.settings["lease_s"])
                and self._restored_expiry is not None):
            self._restart_resume = deepcopy(checkpoint)
            if self._manual_control is not None and self._manual_control.get("mode") == "on":
                origin = finite(self._manual_control.get("session_started_at"))
                origin = min(checkpoint["started_at"], origin) if origin is not None else checkpoint["started_at"]
                self._manual_control["session_started_at"] = origin
                self._manual_session_started = self._clock()-(self._wall_clock()-origin)
            if stored.get("completion_hold") is not True:
                self.completion_hold = False
            self._session_finishing = stored.get("session_finishing") is True
            imported = checkpoint.get("import_observation")
            policy = checkpoint.get("import_policy")
            since = finite(checkpoint.get("import_started_at"))
            if (isinstance(imported, dict) and finite(imported.get("watts")) is not None
                    and finite(imported.get("stamp")) is not None and since is not None
                    and checkpoint["started_at"] <= since <= self._wall_clock()
                    and isinstance(policy, list) and len(policy) == 2
                    and all(finite(value) is not None for value in policy)
                    and tuple(policy) == self._import_policy_current()):
                self._import_since = self._clock()-(self._wall_clock()-since)
                self._import_observation = deepcopy(imported)
                self._import_policy = tuple(policy)
        self._tank_source_changed = stored.get("tank_source_changed") is True
        reference = stored.get("need_reference")
        if (isinstance(reference, dict) and reference.get("schema") == 1
                and isinstance(reference.get("entity_id"), str)
                and finite(reference.get("temperature_c")) is not None
                and 0 <= finite(reference.get("temperature_c")) <= 100
                and finite(reference.get("stamp")) is not None
                and finite(reference.get("ended_at")) is not None):
            self._need_reference = {"schema": 1, "entity_id": reference["entity_id"],
                **{key: finite(reference[key]) for key in ("temperature_c", "stamp", "ended_at")}}
            if reference["entity_id"] != self.settings.get("tank_temperature_entity"):
                self._tank_source_changed = True
        self._need_candidate = None  # New real reports are required after reload.
        last_rearm = stored.get("last_rearm")
        self._last_rearm = deepcopy(last_rearm) if isinstance(last_rearm, dict) else None
        rest = finite(stored.get("rest_until_wall"))
        if rest is not None:
            remaining = max(0.0, min(float(self.settings["rest_s"]), rest - self._wall_clock()))
            self._rest_until = self._clock() + remaining
            self._rest_until_wall = rest
        rest_policy = stored.get("request_rest_policy")
        self._request_rest_policy = rest_policy if rest_policy in ("request", "protected") else None
        last = stored.get("last_session")
        self._last_session = deepcopy(last) if isinstance(last, dict) else None
        # Evidence never grants ownership or supplies restart permission. In
        # particular, a pre-provenance journal stays historically unknown.
        self._session_provenance = self._historical_provenance(stored.get("session_provenance"))
        if self._restart_resume is not None:
            self._session_provenance = self._historical_provenance(self._restart_resume.get("session_provenance"))
        origin = stored.get("hold_origin")
        self._hold_origin = ({"hold_reason": origin.get("hold_reason") if isinstance(origin.get("hold_reason"), str) else None,
            "stop_reason": origin.get("stop_reason")[:240] if isinstance(origin.get("stop_reason"), str) else None,
            "ended_at": finite(origin.get("ended_at")),
            "session_provenance": self._historical_provenance(origin.get("session_provenance"))}
            if isinstance(origin, dict) else None)
        fingerprint = stored.get("commissioned_fingerprint")
        self._commissioned_fingerprint = deepcopy(fingerprint) if isinstance(fingerprint, dict) else None
        reason = stored.get("hold_reason")
        self._hold_reason = (reason if reason in {"session_limit", "native_completed", "no_uptake", "profile_changed", "response_unknown"}
                             else "session_limit" if self.completion_hold else "")
        reference = stored.get("general_reference")
        if (isinstance(reference, dict) and reference.get("schema") == 1
                and finite(reference.get("ended_at")) is not None):
            self._general_reference = {"schema": 1, "ended_at": finite(reference["ended_at"]),
                "signature": reference.get("signature") if isinstance(reference.get("signature"), str) else None,
                **{key: finite(reference.get(key)) for key in (
                    "native_stamp", "solar_stamp", "solar_reset_stamp", "native_reset_stamp")},
                "profile_transition": reference.get("profile_transition") is True,
                "native_rebase": reference.get("native_rebase") is True,
                "native_after": finite(reference.get("native_after"))}
        provenance = stored.get("hold_provenance")
        self._hold_provenance = deepcopy(provenance) if isinstance(provenance, dict) else None
        session = stored.get("session_reference")
        if isinstance(session, dict) and session.get("schema") == 1:
            self._session_reference = {"schema": 1,
                "signature": session.get("signature") if isinstance(session.get("signature"), str) else None,
                "native_stamp": finite(session.get("native_stamp")),
                "solar_stamp": finite(session.get("solar_stamp"))}
        if (stored.get("owned") is True and self._restart_resume is None and not self.completion_hold
                and self.settings.get("profile") == "general"):
            self.completion_hold = True
            self._hold_reason = "response_unknown"
            self._general_reference = {"schema": 1, "ended_at": self._wall_clock(),
                "signature": (self._session_reference or {}).get("signature"),
                "native_stamp": (self._session_reference or {}).get("native_stamp"),
                "solar_stamp": (self._session_reference or {}).get("solar_stamp"),
                "solar_reset_stamp": None, "native_reset_stamp": None,
                "profile_transition": False, "native_rebase": False, "native_after": None}
        if (self.completion_hold and self.settings.get("profile") == "general"
                and self.settings.get("profile_confirmed") is True
                and self._general_reference is None):
            self._convert_legacy_hold()
        # Reload preserves completed evidence, never a partly observed window.
        self._general_candidate = self._general_reset_candidate = None
        code = stored.get("fault_code")
        if code in {"on_failed", "lease_invalid", "lease_failed", "firmware_changed"}:
            self._fault(code, "SG-zonneboost vraagt controle van de lokale terugval; overige toestellen blijven werken")
        self.desired_on = False
        self.owned = False
        self._possibly_owned = False
        self._stable_since = None
        self._minimum_started = None
        if self._restart_resume is None:
            self._import_since = self._import_observation = self._import_policy = None

    def _capture_session_provenance(self, *, identity, settings, issued_at, source_reports,
                                    fixed_import_limit_w, request_mode):
        """Freeze the actual command's observations, separate from ON authority."""
        try:
            configured_minimum = finite(settings.get("min_session_s"))
            maximum = finite(settings.get("max_session_s"))
            # Manual reissue can retain an older hard-session origin. Record
            # that actual minimum/max relationship, separately from this ON.
            delay = (max(0.0, self._minimum_started-self._session_started)
                if self._minimum_started is not None and self._session_started is not None else 0.0)
            effective_minimum = (max(0.0, min(configured_minimum, maximum-delay))
                if configured_minimum is not None and maximum is not None else None)
            policy = effective_session_policy(settings, effective_minimum,
                fixed_import_limit_w)
            value = {"schema": 1, "release": VERSION, "policy": policy,
                "policy_hash": session_policy_hash(policy), "command_identity": identity,
                "owner": "solarpilot", "started_at": self._wall_clock()-(self._clock()-self._session_started),
                "command_issued_at": self._wall_clock()-(self._clock()-issued_at),
                "request_mode": request_mode,
                "binding_identity": self._binding_identity,
                "control_identity": self._control_identity(settings),
                "source_reports": source_reports}
            self._session_provenance = self._historical_provenance(value)
        except (Exception, asyncio.CancelledError):
            # Failure to collect optional evidence cannot change native safety.
            self._session_provenance = None

    def _record_session_end(self, reason, *, transport=None, ended_at=None, stop_evidence=None):
        if self._session_started is None:
            return
        ended = self._wall_clock() if ended_at is None else ended_at
        provenance = deepcopy(self._session_provenance)
        self._last_session = {"ended_at": ended, "reason": reason,
            "duration_s": max(0, self._clock()-self._session_started),
            "transport": deepcopy(transport), "session_provenance": provenance,
            "release": provenance.get("release") if provenance else None,
            "policy_hash": provenance.get("policy_hash") if provenance else None,
            "command_identity": provenance.get("command_identity") if provenance else None,
            "provenance_status": "recorded_at_start" if provenance else "unknown_legacy",
            "stop_evidence": clean_dispatch_rejection(stop_evidence)}
        if self.completion_hold and isinstance(self._hold_origin, dict):
            # Match by the captured command, never attach an unrelated old end
            # to a restored completion hold merely because it was the latest.
            origin = self._hold_origin.get("session_provenance")
            if provenance and isinstance(origin, dict) and origin.get("command_identity") == provenance["command_identity"]:
                self._hold_origin.update(stop_reason=reason, ended_at=ended)
        self._session_provenance = None

    def _rearm_wait(self):
        if not self.completion_hold:
            return None
        origin = self._hold_origin if isinstance(self._hold_origin, dict) else {}
        provenance = origin.get("session_provenance")
        if self.settings.get("profile") == "general":
            condition = ("Vijf minuten werkelijk restoverschot en actuele UIT bevestigen; daarna gewone startvertraging"
                if self._hold_reason == "response_unknown" and self._request_rest_proven() else
                "Na rust vijf minuten werkelijk restoverschot of nieuwe betrouwbare toestelcontext bevestigen"
                if self._hold_reason == "response_unknown" else
                "Na rust een nieuwe zonneperiode of betrouwbare gewijzigde toestelcontext bevestigen")
        else:
            condition = ("Na rust aantoonbare afkoeling van de tank bevestigen"
                if self._need_reference is not None and not self._tank_source_changed else self._completion_reason())
        return {"original_stop_reason": origin.get("stop_reason"),
            "original_hold_reason": origin.get("hold_reason"),
            "original_ended_at": origin.get("ended_at"),
            "command_identity": provenance.get("command_identity") if isinstance(provenance, dict) else None,
            "provenance_status": "recorded_at_start" if isinstance(provenance, dict) else "unknown_legacy",
            "request_rest_remaining_s": math.ceil(max(0.0, self._rest_until-self._clock())),
            "request_rest_replaceable": self._clock() < self._rest_until and self._request_rest_proven(),
            "current_condition": condition}

    def _effective_minimum_s(self):
        configured = finite(self.settings.get("min_session_s"))
        maximum = finite(self.settings.get("max_session_s"))
        if configured is None or maximum is None:
            return 0.0
        # The minimum starts at confirmed ON; the hard ceiling conservatively
        # remains anchored before the asynchronous write/readback.
        confirmation_delay = (max(0.0, self._minimum_started - self._session_started)
                              if self._minimum_started is not None and self._session_started is not None else 0.0)
        return max(0.0, min(configured, maximum - confirmation_delay))

    def _confirmed_request_current(self):
        stamp = finite(self._relay_observed_at)
        relay_deadline = finite(self._relay_valid_until)
        return (self.owned and self.desired_on and self.relay_confirmed and self.relay_on is True
                and self._session_started is not None and self._lease_deadline is not None
                and self._clock() < self._lease_deadline and stamp is not None
                and relay_deadline is not None and self._wall_clock() < relay_deadline
                and -5 <= self._wall_clock() - stamp <= float(self.settings["stale_s"]))

    @property
    def minimum_hold_active(self):
        """Only a live confirmed request can postpone the soft import stop."""
        return bool(self._minimum_started is not None and self._confirmed_request_current()
                    and self._on_permission_current(self._generation)
                    and self._clock() - self._minimum_started < self._effective_minimum_s())

    def _import_policy_current(self):
        threshold, delay = finite(self.settings.get("import_threshold_w")), finite(self.settings.get("stop_delay_s"))
        return (threshold, delay) if threshold is not None and delay is not None else None

    def _import_source_current(self):
        observation = self._import_observation or {}
        stamp = finite(observation.get("stamp"))
        return (stamp is not None and finite(observation.get("watts")) is not None
                and -5 <= self._wall_clock() - stamp < float(self.settings["stale_s"]))

    @property
    def cloud_hold_active(self):
        """Fresh continuous soft-import evidence can retain only an owned ON."""
        policy = self._import_policy_current()
        return bool(self._confirmed_request_current() and self._on_permission_current(self._generation)
                    and policy is not None
                    and self._import_source_current() and self._import_since is not None
                    and self._import_policy == policy
                    and self._import_observation["watts"] > policy[0]
                    and self._clock() - self._import_since < policy[1])

    def soft_import_renewal_allowed(self, *, grid_import_w, grid_import_stamp, grid_import_source=None):
        """Recheck the same soft policy against a fresh real P1 after awaits.

        This method never starts or refreshes a candidate. A new live import
        reading cannot revive expired evidence or invent a completed grace.
        """
        imported, stamp = finite(grid_import_w), finite(grid_import_stamp)
        policy = self._import_policy_current()
        if (not self._confirmed_request_current() or not self._on_permission_current(self._generation)
                or policy is None
                or imported is None or imported < 0 or stamp is None
                or not -5 <= self._wall_clock() - stamp < float(self.settings["stale_s"])):
            return False
        if imported <= policy[0]:
            return True
        if self.minimum_hold_active:
            return True
        observation = self._import_observation or {}
        return bool(self.cloud_hold_active and stamp >= observation["stamp"]
                    and grid_import_source == observation.get("source"))

    def _observe_import(self, imported, stamp, source, now):
        policy = self._import_policy_current()
        if policy is None:
            self._import_since = self._import_observation = self._import_policy = None
            return True  # Validation supplies the direct configuration gate.
        previous = self._import_observation
        continuous = (self._import_source_current() and previous.get("source") == source
                      and stamp is not None and stamp >= previous["stamp"]
                      and self._import_policy == self._import_policy_current())
        current = (stamp is not None
                   and -5 <= self._wall_clock() - stamp < float(self.settings["stale_s"]))
        if self._restart_resume is not None and imported > policy[0] and not continuous:
            # Downtime is not a new observed cloud episode. Fresh current P1
            # may still retain an original live minimum, but buys no new grace.
            self._import_since = None
            self._import_observation = {"watts": imported, "stamp": stamp, "source": source} if current else None
            self._import_policy = policy if current else None
            return True
        if (self.owned and self.desired_on and self._import_since is not None
                and imported > policy[0] and not continuous):
            # A backdated/rebound/expired report is not measured recovery.
            # Missing continuity must never purchase a fresh five-minute hold.
            return False
        self._import_observation = {"watts": imported, "stamp": stamp, "source": source} if current else None
        if imported <= policy[0] or not current:
            self._import_since = None
        elif self._import_since is None or not continuous:
            self._import_since = now
        self._import_policy = policy if current else None
        return True

    def _transport(self):
        if self._adapter is None:
            from .sg_transport import ShellyLeaseAdapter
            self._adapter = ShellyLeaseAdapter(self.runtime.hass, self.settings["entity_id"])
        return self._adapter

    def _fault(self, code, reason):
        self.fault_code, self.fault = code, reason
        self.state, self.status, self.reason = "blocked", "Zonneboost geblokkeerd", reason
        self._stable_since = None

    def _record_transport(self, operation, *, error=None, attempted=None):
        """Diagnostic-only phase/flags; never used by dispatch or recovery."""
        try:
            self._capture_transport_evidence(operation, error=error, attempted=attempted)
        except (Exception, asyncio.CancelledError):
            # Optional diagnostics must not affect any native command/result.
            self._transport_evidence = None

    def _capture_transport_evidence(self, operation, *, error=None, attempted=None):
        category, phase, applied = "none", "pending", None
        if error is not None:
            code = getattr(error, "code", None)
            code = code if isinstance(code, str) else None
            category = {
                "write_uncertain": "write_uncertain", "unavailable": "unavailable",
                "unsupported_runtime": "unavailable", "invalid_response": "invalid_response",
                "status_unknown": "contact_unconfirmed", "off_unconfirmed": "contact_unconfirmed",
                "off_timer_active": "contact_unconfirmed", "lease_unconfirmed": "lease_unconfirmed",
                "lease_not_renewed": "lease_unconfirmed", "clock_unknown": "lease_unconfirmed",
                "binding_changed": "mapping_or_setup_changed", "configuration_invalid": "mapping_or_setup_changed",
                "unverified_mapping": "mapping_or_setup_changed", "unsupported_device": "mapping_or_setup_changed",
                "unsupported_source": "mapping_or_setup_changed", "entity_disabled": "mapping_or_setup_changed",
                "wrong_channel": "mapping_or_setup_changed", "wrong_role": "mapping_or_setup_changed",
                "firmware_unknown": "mapping_or_setup_changed", "dispatch_changed": "policy_changed",
            }.get(code, "unknown")
            if isinstance(error, asyncio.TimeoutError):
                category = "timeout"
            elif isinstance(error, asyncio.CancelledError):
                category = "cancelled"
            elif isinstance(error, ValueError) and error.args and isinstance(error.args[0], str):
                # Only fixed internal markers are interpreted; raw exception
                # strings, hosts, device identities and payloads never escape.
                category = {"off_not_confirmed": "contact_unconfirmed", "lease_not_confirmed": "lease_unconfirmed",
                            "commissioning_changed": "mapping_or_setup_changed"}.get(error.args[0], "unknown")
            explicit_attempted = getattr(error, "command_attempted", None)
            if type(explicit_attempted) is bool:
                attempted = explicit_attempted
            explicit_applied = getattr(error, "command_applied", None)
            if explicit_applied is True:
                applied = True
            phase = ("accepted_readback_unconfirmed" if applied is True else "send_uncertain" if attempted is True
                     else "not_sent" if attempted is False else "failed")
        stamp = finite(self._wall_clock())
        self._transport_evidence = {"operation": operation, "phase": phase, "category": category,
            "observed_at": stamp, "command_attempted": attempted, "command_applied": applied}

    def _transport_confirmed(self, operation):
        self._record_transport(operation, attempted=operation != "read")
        if self._transport_evidence is not None:
            self._transport_evidence.update(phase="confirmed", command_applied=True if operation != "read" else None)

    def _set_state(self, state, reason):
        self.state = state
        self.status = {"normal": "Panasonic regelt zelfstandig", "waiting_surplus": "Wachten op zon",
                       "boost_requested": "SG-zonneboost aangevraagd", "rest": "Rusttijd",
                       "blocked": "Zonneboost geblokkeerd"}[state]
        self.reason = reason

    async def _save(self):
        if self._suppress_saves:
            return
        store = getattr(self.runtime, "store", None)
        snapshot = getattr(self.runtime, "_snapshot", None)
        if store is not None and callable(snapshot):
            await store.async_save(snapshot())

    def _note(self, text):
        note = getattr(self.runtime, "note", None)
        if callable(note):
            note(text)

    def _begin_rest(self, *, request_reassessment=False):
        now = self._clock()
        seconds = float(self.settings["rest_s"])
        deadline = now + seconds
        if not request_reassessment:
            # An explicit/manual or uncertain later rest cannot borrow the
            # previous automatic request's early-reassessment evidence.
            self._request_rest_policy = "protected"
        if deadline > self._rest_until:
            self._rest_until = deadline
            self._rest_until_wall = self._wall_clock() + seconds
            self._request_rest_policy = "request" if request_reassessment else "protected"

    def _command_clock(self):
        self.runtime.last_issued = self._clock()
        self.runtime.last_issued_wall = self._wall_clock()
        self.sent_this_tick = True

    def _status(self, raw):
        if not isinstance(raw, dict) or type(raw.get("output")) is not bool:
            raise ValueError("missing_output")
        if type(self.relay_on) is bool and self.relay_on != raw["output"]:
            self._note("SG-uitgang meldt " + ("AAN" if raw["output"] else "UIT"))
        self.relay_on = raw["output"]
        self.relay_confirmed = True
        # A live readback is source evidence. Rendering the overview must never
        # refresh this timestamp or turn an expired cached contact into proof.
        self._relay_observed_at = self._wall_clock()
        self._relay_binding_identity = raw.get("binding_identity")
        remaining = finite(raw.get("lease_remaining_s"))
        self._relay_valid_until = (self._relay_observed_at + remaining
                                  if raw["output"] and remaining is not None and 0 < remaining <= 600 else None)
        return raw

    @staticmethod
    def _expiry(raw):
        return finite(raw.get("expires_at", raw.get("timer_expires_at")))

    def _persist_settings(self):
        """Persist revoked commissioning authority; no physical settings write."""
        entries = getattr(getattr(self.runtime, "hass", None), "config_entries", None)
        options = {**self.runtime.entry.options, "sg_boost": deepcopy(self.settings)}
        if entries is not None:
            self.runtime._skip_options_reload_once = True
            entries.async_update_entry(self.runtime.entry, options=options)
        else:
            self.runtime.entry.options = options
        monitor = getattr(self.runtime, "panasonic", None)
        if monitor is not None and callable(getattr(monitor, "update_config", None)):
            monitor.update_config(self.settings)
        live = getattr(self.runtime, "live_options", None)
        if live is not None and isinstance(getattr(live, "applied", None), dict):
            live.applied["sg_boost"] = deepcopy(self.settings)

    def _fingerprint_check(self, raw):
        fingerprint = raw.get("fingerprint")
        if not isinstance(fingerprint, dict) or not fingerprint:
            return
        self._observed_fingerprint = deepcopy(fingerprint)
        if self._commissioned_fingerprint is None:
            if self.settings.get("commissioning_confirmed") is True and self.settings.get("watchdog_confirmed") is True:
                self._commissioned_fingerprint = deepcopy(fingerprint)
            return
        if fingerprint != self._commissioned_fingerprint:
            self.settings["commissioning_confirmed"] = False
            self.settings["watchdog_confirmed"] = False
            self._persist_settings()
            self._fault("firmware_changed", "SG-toestel of firmware gewijzigd; bevestig de koppeling en test de lokale aflooptimer opnieuw")

    def _timer_proof(self, raw, *, renewal=False, lease_s=None):
        start = finite(raw.get("timer_started_at"))
        duration = finite(raw.get("timer_duration"))
        expiry = self._expiry(raw)
        if expiry is None and start is not None and duration is not None:
            expiry = finite(start + duration)
        remaining = finite(raw.get("lease_remaining_s"))
        # Production transport obtains remaining validity from the device clock.
        # A small fake/legacy adapter may supply no device clock: this cannot
        # establish safe authority and is deliberately rejected.
        lease = float(self.settings["lease_s"] if lease_s is None else lease_s)
        valid = (raw.get("output") is True and start is not None and duration is not None
                 and abs(duration - lease) <= 1 and expiry is not None
                 and remaining is not None and 0 < remaining <= lease + 1)
        if renewal and self._lease_expiry is not None:
            valid = valid and expiry > self._lease_expiry
        if not valid:
            raise ValueError("lease_not_confirmed")
        self._lease_expiry = expiry
        self._lease_deadline = self._clock() + remaining
        self._lease_duration = duration
        self._binding_identity = raw.get("binding_identity")

    async def _read(self, *, force=False):
        now = self._clock()
        if not force and now < self._next_read:
            return None
        self._record_transport("read", attempted=False)
        try:
            raw = self._status(await asyncio.wait_for(self._transport().get_status(),
                                                    float(self.settings["ack_timeout_s"])))
        except Exception as err:
            self._record_transport("read", error=err, attempted=False)
            self.relay_on = None
            self.relay_confirmed = False
            self._read_failures += 1
            self._next_read = now + min(300.0, 15.0 * 2 ** min(self._read_failures, 4))
            if self.fault_code not in {"on_failed", "lease_invalid", "lease_failed", "firmware_changed"}:
                self._fault("unavailable_read", "SG-uitgang niet bereikbaar; status onbekend, de lokale toestemming wordt niet vernieuwd")
            return None
        self._transport_confirmed("read")
        self._read_failures = 0
        self._next_read = now
        if self.fault_code == "unavailable_read":
            self.fault_code = self.fault = ""
        self._fingerprint_check(raw)
        manual = self._manual_control
        if (manual is not None and (raw.get("fingerprint") != manual.get("fingerprint")
                or raw.get("binding_identity") != manual.get("binding_identity"))):
            self._generation += 1
            self._manual_control = self._manual_deadline = None
            self._stable_since = self._start_soft_since = None
            self._start_soft_kind = None
            self._fault("binding_changed", "Tijdelijke SG-keuze vervallen: actuele uitgangskoppeling gewijzigd")
        if (raw.get("setup_valid") is False or raw.get("configuration_error")) and self.fault_code not in {"on_failed", "lease_invalid", "lease_failed", "firmware_changed"}:
            self._fault("setup_invalid", "Controleer de SG-koppeling en lokale Shelly-terugval; automatische boost blijft uit")
        elif self.fault_code == "setup_invalid":
            self.fault_code = self.fault = ""
        return raw

    async def start(self):
        async with self._lock:
            if self._started or self._closed:
                return
            self._started = True
            if not self.configured:
                return
            raw = await self._read(force=True)
            if raw is None:
                return
            if self._restart_resume is not None:
                # The next complete runtime round supplies current sources and
                # hard gates. A cached journal alone cannot renew this lease.
                self._set_state("blocked", "Herstart: bestaande SG-toestemming wacht op actuele voorwaarden")
                checkpoint = self._restart_resume
                expiry = self._expiry(raw)
                if (raw["output"] and (raw.get("fingerprint") != checkpoint["fingerprint"]
                        or raw.get("binding_identity") != checkpoint.get("binding_identity")
                        or expiry is not None and abs(expiry-self._restored_expiry) > 2
                        or raw.get("timer_cancelled") is True or finite(raw.get("timer_duration")) == 0)):
                    self._restart_resume = None
                    self._restart_release = False
                    self.manual_hold = True
                    self._set_state("blocked", "SG-contact tijdens herstart gewijzigd; handmatige stand blijft behouden")
            elif self._restart_release:
                await self._reconcile_restart(raw)
            elif raw["output"]:
                self.manual_hold = True
                self._set_state("blocked", "SG-contact staat buiten SolarPilot aan; handmatige stand blijft behouden")
            await self._save()

    async def _reconcile_restart(self, raw, *, current_gates=None, source_gap=False):
        """Finish an unread startup journal when a real later report arrives.

        A new confirmed checkpoint can continue only the exact current ON lease,
        without any ON command. Old journals retain their one possible OFF.
        """
        if not self._restart_release or raw is None:
            return
        expiry = self._expiry(raw)
        checkpoint = self._restart_resume
        if checkpoint is not None and current_gates is None:
            return
        if (checkpoint is not None and raw["output"] is True
                and (raw.get("fingerprint") != checkpoint["fingerprint"]
                     or raw.get("binding_identity") != checkpoint.get("binding_identity"))):
            self._restart_release = False
            self._restart_resume = None
            self.manual_hold = True
            self._set_state("blocked", "SG-koppeling na herstart gewijzigd; huidige contactstand blijft vrij")
            await self._save()
            return
        different = (self._restored_expiry is not None
                     and (expiry is not None and abs(expiry-self._restored_expiry) > 2
                          or raw.get("timer_cancelled") is True
                          or finite(raw.get("timer_duration")) == 0))
        self._restart_release = False
        self._restart_resume = None
        if raw["output"] and different:
            self.manual_hold = True
            self._set_state("blocked", "SG-uitgang is handmatig gewijzigd; hervat de automatisering wanneer gewenst")
        elif raw["output"]:
            self._possibly_owned = True
            # A failed safe OFF still has only this observed local lease. Its
            # remaining timer bounds busy/recovery without replaying old ON.
            remaining = finite(raw.get("lease_remaining_s"))
            if expiry is not None and remaining is not None and 0 < remaining <= 600:
                self._lease_expiry = expiry
                self._lease_deadline = self._clock()+remaining
            duration = finite(raw.get("timer_duration"))
            start = finite(raw.get("timer_started_at"))
            matching = (checkpoint is not None and raw.get("setup_valid") is True
                and not raw.get("configuration_error") and not different
                and self._lease_deadline is not None and self._clock() < self._lease_deadline
                and duration is not None and abs(duration-checkpoint["lease_duration_s"]) <= 1
                and start is not None and expiry is not None and abs(start+duration-expiry) <= 1
                and expiry == self._restored_expiry
                and self._clock()+float(self.settings["ack_timeout_s"]) < self._lease_deadline)
            if matching:
                if source_gap is True and not self._gates(data_fresh=True, phase_allowed=True,
                        priority_allowed=True, hard_limit=False):
                    # Missing new HA reports are not failed physical limits.
                    # Keep only the proven old local deadline, without adopting
                    # ownership or renewing it while evidence is unavailable.
                    self._restart_release = True
                    self._restart_resume = checkpoint
                    self._possibly_owned = False
                    self.owned = self.desired_on = False
                    self._set_state("blocked", "Herstart: bestaande lokale SG-toestemming wacht op actuele metingen")
                    await self._save()
                    return
                wall, now = self._wall_clock(), self._clock()
                self._session_started = now-(wall-checkpoint["started_at"])
                self._minimum_started = now-(wall-checkpoint["minimum_started_at"])
                self._last_renewed = now-(wall-checkpoint["renewed_at"])
                self._lease_duration = duration
                self._binding_identity = raw.get("binding_identity")
                self.owned = self.desired_on = True
                self._possibly_owned = False
                self._off_attempted = False
                if (not current_gates and self.manual_mode != "off"
                        and self._on_authorized(self._generation, True)):
                    self._set_state("boost_requested", "Herstart gecontroleerd; bestaande SG-aanvraag blijft actief")
                    self._note("Bestaande SG-aanvraag na herstart bevestigd zonder relaiscyclus")
                    await self._save()
                    return
                self.desired_on = False
            await self._release("Eerdere SG-aanvraag na herstart vrijgegeven", rest=True)
        else:
            if (checkpoint is not None and self._restored_expiry is not None
                    and self._restored_expiry > self._wall_clock()+1):
                self.manual_hold = True
                self._set_state("blocked", "SG-contact tijdens herstart handmatig uitgeschakeld; handmatige stand blijft behouden")
            else:
                self._begin_rest()
        await self._save()

    def _on_permission_current(self, generation):
        return (generation == self._generation and not self._closed and self.auto_enabled
                and not getattr(self.runtime, "_closed", False)
                and (not hasattr(self.runtime.entry, "runtime_data")
                     or self.runtime.entry.runtime_data is self.runtime)
                and getattr(self.runtime, "mode", "observe") == "solar"
                and self.settings.get("commissioning_confirmed") is True
                and self.settings.get("watchdog_confirmed") is True
                and not validate_config(self.settings)
                and (self.settings.get("profile", "dhw_only") != "general"
                     or self.settings.get("profile_confirmed") is True)
                and not self.cooling_block_reason(live=True)
                and not self._profile_change_release
                and self.manual_mode != "off" and not self.manual_hold
                and (not self.completion_hold or self.manual_mode == "on") and not self.fault)

    def _manual_session_origin(self):
        return self._manual_session_started if self.manual_mode == "on" else None

    def _on_authorized(self, generation, renewal):
        """Recheck authority after async work and at the transport boundary."""
        if not self._on_permission_current(generation):
            self._capture_dispatch_rejection("permission_changed", renewal)
            return False
        if renewal and not self._confirmed_request_current():
            self._capture_dispatch_rejection("lease_unconfirmed", renewal)
            return False
        gate = getattr(self.runtime, "sg_dispatch_allowed", None)
        if not callable(gate):
            # Small isolated tests have no runtime. Production SolarRuntime
            # provides a final live electrical/priority gate.
            return self._injected_adapter
        owner = getattr(gate, "__self__", self.runtime)
        previous_evidence = getattr(owner, "_sg_dispatch_rejection", None)
        try:
            approved = gate(renewal=renewal)
        except Exception:
            self._capture_dispatch_rejection("dispatch_callback_error", renewal)
            return False
        if isinstance(approved, tuple):
            approved = approved[0] if approved else False
        if approved is not True:
            evidence = getattr(owner, "_sg_dispatch_rejection", None)
            self._capture_dispatch_rejection("dispatch_unexplained", renewal,
                evidence=evidence if evidence is not previous_evidence else None)
        return approved is True

    def _capture_dispatch_rejection(self, code, renewal, *, evidence=None):
        """Attach the exact rejected check; never reread it during safe OFF."""
        try:
            cleaned = clean_dispatch_rejection(evidence)
            if cleaned is None or cleaned["renewal"] != (renewal is True):
                cleaned = clean_dispatch_rejection({"schema": 1, "code": code,
                    "evaluated_at": self._wall_clock(), "renewal": renewal is True})
            self._dispatch_rejection = cleaned
        except Exception:
            self._dispatch_rejection = None

    def _automatic_continuation_allowed(self, generation):
        """Only current automatic permission may bridge a manual deadline."""
        if (self.completion_hold or not self._on_permission_current(generation)
                or not self._confirmed_request_current()):
            return False
        observation = self._import_observation or {}
        if not self.soft_import_renewal_allowed(grid_import_w=observation.get("watts"),
                grid_import_stamp=observation.get("stamp"), grid_import_source=observation.get("source")):
            return False
        gate = getattr(self.runtime, "sg_dispatch_allowed", None)
        if not callable(gate):
            return self._injected_adapter
        try:
            return gate(renewal=True, automatic=True) is True
        except Exception:
            return False

    async def _issue_on(self, *, renewal=False):
        if renewal and not self._confirmed_request_current():
            return False
        self._dispatch_rejection = None
        # A physical write may arrive late within the bounded ACK interval.
        # Reserve that delivery time on the initial lease as well as renewals,
        # so the local fallback never extends a short hard session ceiling.
        lease_s = min(float(self.settings["lease_s"]),
                      float(self.settings["max_session_s"]) - float(self.settings["ack_timeout_s"]))
        manual_origin = self._manual_session_origin()
        automatic_bridge = renewal and self.manual_mode == "on" and self._automatic_continuation_allowed(self._generation)
        manual_limit = self._manual_deadline if self.manual_mode == "on" and not automatic_bridge else None
        manual_wall_limit = self._manual_control["expires_at"] if manual_limit is not None else None
        if not renewal and manual_origin is not None:
            lease_s = min(lease_s, manual_origin+float(self.settings["max_session_s"])
                          -self._clock()-float(self.settings["ack_timeout_s"]))
        if manual_limit is not None:
            lease_s = min(lease_s, self._manual_deadline-self._clock()-float(self.settings["ack_timeout_s"]),
                          self._manual_control["expires_at"]-self._wall_clock()-float(self.settings["ack_timeout_s"]))
        if lease_s < 60:
            return False
        if renewal:
            elapsed = self._clock() - self._session_started if self._session_started is not None else float(self.settings["max_session_s"])
            remaining = float(self.settings["max_session_s"]) - elapsed - float(self.settings["ack_timeout_s"])
            lease_s = min(lease_s, remaining)
            if (lease_s < 60 or self._lease_deadline is not None
                    and self._lease_deadline >= self._clock() + lease_s):
                # The existing device timer already covers the final window.
                # Leave it intact: a shorter ON would fail the renewal proof,
                # while a full new lease could outlive the maximum session.
                self._session_finishing = True
                await self._save()
                return False
        lease_s = int(lease_s)
        generation = self._generation
        self._in_flight = True
        self._possibly_owned = True
        self.desired_on = True
        if not renewal:
            self._session += 1
            self._off_attempted = False
        write_started = False
        issued_at = None
        adapter = None
        callback = None
        supports_callback = False
        status_callback = None
        supports_status_callback = False
        write_guard_deadline = None
        command_identity = uuid.uuid4().hex if not renewal else None
        command_settings = None
        source_reports = None
        command_fixed_import_limit_w = None
        command_request_mode = None
        before_contact = {"output": self.relay_on, "confirmed": self.relay_confirmed,
            "stamp": self._relay_observed_at}

        def before_on_status(raw):
            nonlocal before_contact
            # The native transport reads the contact after awaited preflight.
            # Changes there must not be overwritten with our earlier cached
            # lease. The existing no-arg callback still checks live electrical
            # permission at Switch.Set; no new ON authority comes from a read.
            self._status(raw)
            before_contact = {**deepcopy(raw), "confirmed": True, "stamp": self._relay_observed_at}
            if not renewal and raw["output"] is True:
                self.owned = self._possibly_owned = self.desired_on = False
                self.manual_hold = True
                self._set_state("blocked", "SG-contact staat buiten SolarPilot aan; handmatige stand blijft behouden")
                return False
            if renewal:
                self._observe_contact(raw)
            return self._on_authorized(generation, renewal)

        def before_on():
            nonlocal issued_at, command_settings, source_reports, command_fixed_import_limit_w, command_request_mode
            if not self._on_authorized(generation, renewal):
                return False
            if automatic_bridge and not self._automatic_continuation_allowed(generation):
                self._capture_dispatch_rejection("permission_changed", renewal)
                return False
            final_now = self._clock()
            remaining_ack = max(0.0, write_guard_deadline - final_now)
            hard_deadline = ((self._session_started if renewal else manual_origin if manual_origin is not None else final_now)
                             + float(self.settings["max_session_s"]))
            if (final_now >= write_guard_deadline
                    or final_now + lease_s + remaining_ack > hard_deadline):
                self._capture_dispatch_rejection("session_deadline", renewal)
                return False
            if manual_limit is not None and (
                    self.manual_mode != "on" or self._manual_deadline != manual_limit
                    or final_now+lease_s+remaining_ack > manual_limit
                    or self._wall_clock()+lease_s+remaining_ack > manual_wall_limit):
                self._capture_dispatch_rejection("manual_deadline", renewal)
                return False
            issued_at = final_now
            if not renewal:
                command_settings = deepcopy(self.settings)
                runtime_settings = getattr(self.runtime, "settings", {})
                command_fixed_import_limit_w = (runtime_settings.get("max_import_w")
                    if isinstance(runtime_settings, dict) else None)
                command_request_mode = "manual_on" if self.manual_mode == "on" else "automatic"
                source_reports = {"grid": deepcopy(self._import_observation),
                    "solar": deepcopy(self._solar_observation), "tank": deepcopy(self._tank_observation),
                    "native": self._valid_native_observation(self._native_observation),
                    "contact": deepcopy(before_contact)}
                self._command_clock()
            return True

        # Persist ownership intent before a possible successful physical write.
        try:
            await self._save()
            if not self._on_authorized(generation, renewal):
                self._possibly_owned = False
                self.desired_on = False
                if self.owned:
                    await self._release("SG-voorwaarden gewijzigd; eigen aanvraag vrijgegeven",
                        preserve_fault=bool(self.fault), stop_evidence=self._dispatch_rejection)
                else:
                    self._dispatch_start_wait(generation)
                    self._set_state("blocked", "SG-voorwaarden gewijzigd; verse zonnebeoordeling volgt")
                    await self._save()
                return False
            adapter = self._transport()
            # Ownership storage is outside the bounded transport ACK timeout.
            # Recompute after it, then retain an absolute check in before_on
            # so neither slow storage nor transport preflight extends the cap.
            write_guard_deadline = self._clock() + float(self.settings["ack_timeout_s"])
            if manual_limit is not None:
                lease_s = int(min(lease_s, self._manual_deadline-write_guard_deadline,
                                  self._manual_control["expires_at"]-self._wall_clock()-float(self.settings["ack_timeout_s"])))
                if lease_s < 60:
                    self._possibly_owned = False
                    self.desired_on = self.owned
                    return False
            if renewal:
                lease_s = int(min(lease_s, self._session_started + float(self.settings["max_session_s"])
                                 - write_guard_deadline))
                if (lease_s < 60 or self._lease_deadline is not None
                        and self._lease_deadline >= self._clock() + lease_s):
                    self._possibly_owned = False
                    self._session_finishing = True
                    await self._save()
                    return False
            supports_callback = hasattr(adapter, "before_on")
            callback = before_on
            adapter.before_on = callback
            supports_status_callback = hasattr(adapter, "before_on_status")
            if supports_status_callback:
                status_callback = before_on_status
                adapter.before_on_status = status_callback
            if not supports_callback:
                # Injected deterministic doubles can omit the callback protocol.
                # The production adapter always invokes it after async preflight.
                if not before_on():
                    self._possibly_owned = False
                    self.desired_on = False
                    return False
            write_started = True
            self._record_transport("renew" if renewal else "on")
            raw = await asyncio.wait_for(adapter.set_on(lease_s=lease_s),
                                         float(self.settings["ack_timeout_s"]))
            self._status(raw)
            if issued_at is None:
                raise ValueError("dispatch_not_observed")
            self._fingerprint_check(raw)
            if self.fault_code == "firmware_changed":
                raise ValueError("commissioning_changed")
            self._timer_proof(raw, renewal=renewal, lease_s=lease_s)
            self._transport_confirmed("renew" if renewal else "on")
            if not renewal:
                self._session_started = manual_origin if manual_origin is not None else issued_at
                self._minimum_started = self._clock()
                self._capture_session_provenance(identity=command_identity, settings=command_settings,
                    issued_at=issued_at, source_reports=source_reports,
                    fixed_import_limit_w=command_fixed_import_limit_w, request_mode=command_request_mode)
        except (Exception, asyncio.CancelledError) as err:
            self._record_transport("renew" if renewal else "on", error=err,
                                   attempted=False if not write_started else None)
            # No replay or retry. A missing readback is not a confirmed OFF.
            attempted = write_started and getattr(err, "command_attempted", True)
            if not attempted:
                self._possibly_owned = False
            self.desired_on = False
            policy_rejected = getattr(err, "code", "") == "dispatch_changed"
            if policy_rejected:
                # This was a new live policy decision before Switch.Set, rather
                # than an actuator fault or an unconfirmed physical operation.
                self._dispatch_start_wait(generation)
                reason = "SG-voorwaarden gewijzigd; verse zonnebeoordeling volgt"
                if self.owned:
                    await self._release(reason, preserve_fault=bool(self.fault),
                        stop_evidence=self._dispatch_rejection)
                else:
                    self._set_state("blocked", reason)
            else:
                if attempted:
                    self.relay_on = None
                    self.relay_confirmed = False
                    # An unacknowledged renewal may itself have changed the
                    # device timer. Its difference from the last confirmed
                    # expiry is no proof of manual takeover during safe OFF.
                    self._lease_expiry = None
                    if write_guard_deadline is not None:
                        self._lease_deadline = max(self._lease_deadline or 0.0,
                                                   write_guard_deadline+lease_s)
                if self.fault_code != "firmware_changed":
                    self._fault("on_failed", "SG-aanvraag of lokale aflooptimer niet bevestigd; controle nodig voordat opnieuw wordt gestart")
                if self.owned or self._possibly_owned:
                    await self._release(self.fault, rest=True, preserve_fault=True)
            await self._save()
            if isinstance(err, asyncio.CancelledError):
                raise
            return False
        finally:
            self._in_flight = False
            if (adapter is not None and callback is not None
                    and getattr(adapter, "before_on", None) is callback):
                if supports_callback:
                    adapter.before_on = None
                else:
                    del adapter.before_on
            if (adapter is not None and supports_status_callback
                    and getattr(adapter, "before_on_status", None) is status_callback):
                adapter.before_on_status = None
        if not self._on_permission_current(generation):
            self.desired_on = False
            self._capture_dispatch_rejection("permission_changed", renewal)
            await self._release("Verouderde SG-aanvraag vrijgegeven", rest=True,
                stop_evidence=self._dispatch_rejection)
            return False
        self.owned = True
        self._possibly_owned = False
        self._last_renewed = self._clock()
        if not renewal:
            self._need_reference = self._need_candidate = None
            self._general_reference = self._general_candidate = self._general_reset_candidate = None
            self._hold_reason = ""
            self._hold_origin = None
            self._low_uptake_noted = False
            self._low_uptake_since = self._low_uptake_stamp = None
            native = self._valid_native_observation(self._native_observation)
            self._session_reference = ({"schema": 1, "signature": native["signature"],
                "native_stamp": native["stamp"], "solar_stamp": (self._solar_observation or {}).get("stamp")}
                if native is not None else None)
            self._tank_source_changed = False
            if self.manual_mode == "on" and self._manual_control.get("session_started_at") is None:
                self._manual_control["session_started_at"] = self._wall_clock()-(self._clock()-self._session_started)
                self._manual_session_started = self._session_started
            self._session_finishing = (self._lease_deadline is not None and
                self._lease_deadline >= issued_at + float(self.settings["max_session_s"]) - float(self.settings["ack_timeout_s"]))
            self._stable_since = self._import_since = None
            self._note("SG-zonneboost aangevraagd; alleen het bestaande SG-contact wordt bediend" + self._observation_summary())
        else:
            self.renewed_this_tick = True
            self._note("Lokale SG-toestemming bevestigd vernieuwd zonder relaiscyclus" + self._observation_summary())
        self._set_state("boost_requested", self._active_reason())
        await self._save()
        return True

    def _active_reason(self):
        if self.manual_mode == "on":
            return f"SG-boost tijdelijk handmatig aan; automatisch over {self._manual_overview()['remaining_s']} s"
        if self._import_since is not None and self.minimum_hold_active:
            remaining = math.ceil(max(0.0, self._effective_minimum_s() - (self._clock() - self._minimum_started)))
            return f"Minimumduur SG-aanvraag nog {remaining} s; tijdelijke netafname binnen veiligheidsgrenzen"
        if self.panasonic_confirmed is True:
            return "SG-contact actief; Panasonic meldt de extra SG-aanvraag"
        return "SG-contact actief; Panasonic-reactie niet afzonderlijk bevestigd"

    def _observation_summary(self):
        value = self._native_observation
        parts = []
        context = value.get("context")
        if context in RELEVANT_NATIVE_CONTEXTS | {"normal", "heatpump_unknown"}:
            parts.append("native " + context)
        power = finite(value.get("power_w"))
        if power is not None and value.get("power_kind") == "measured":
            parts.append(f"gemeten {power:g} W")
        for key, label in (("power_supply1_w", "voeding 1"), ("power_supply2_w", "voeding 2")):
            watts = finite(value.get(key))
            if watts is not None:
                parts.append(f"{label} {watts:g} W")
        hz = finite(value.get("compressor_frequency_hz"))
        if hz is not None:
            parts.append(f"compressor {hz:g} Hz")
        return "; " + " · ".join(parts) if parts else ""

    def _observe_low_uptake(self):
        value = self._native_observation
        power, stamp = finite(value.get("power_w")), finite(value.get("power_stamp"))
        valid = (power is not None and 0 <= power <= 100
                 and value.get("power_kind") == "measured" and stamp is not None
                 and -5 <= self._wall_clock() - stamp <= float(self.settings["stale_s"])
                 and value.get("compressor_running") is not True)
        if not valid:
            self._low_uptake_since = self._low_uptake_stamp = None
            return
        now = self._clock()
        if self._low_uptake_since is None:
            self._low_uptake_since, self._low_uptake_stamp = now, stamp
            return
        new_report = stamp > self._low_uptake_stamp
        if new_report:
            self._low_uptake_stamp = stamp
        if not self._low_uptake_noted and new_report and now - self._low_uptake_since >= 1200:
            self._low_uptake_noted = True
            self._note("SG-contact actief; extra warmteopname nog niet aangetoond")

    async def _release(self, reason, *, rest=True, preserve_fault=False, policy_hold=True, stop_evidence=None):
        cancelled = None
        frozen_stop = clean_dispatch_rejection(stop_evidence)
        if frozen_stop is not None:
            reason = reason + "; " + frozen_stop["reason"]
        self.desired_on = False
        self._stable_since = self._import_since = None
        self._import_observation = self._import_policy = None
        had_authority = self.owned or self._possibly_owned
        release_confirmed = False
        if (policy_hold and self.settings.get("profile") == "general"
                and self._session_started is not None and not self.completion_hold):
            self.completion_hold = True
            self._hold_reason = "response_unknown"
            self._capture_need_reference()
        if had_authority and not self._off_attempted:
            self._off_attempted = True
            self._in_flight = True
            adapter = None
            off_callback = None
            supports_off_callback = False

            def before_off_status(raw):
                # Only a provable current timer change can transfer ownership.
                # Missing timer/clock fields are uncertainty, not manual proof,
                # and must not block a known-owned emergency or closing OFF.
                if raw is None:
                    self._note("SG-status vóór vrijgave niet leesbaar; bestaande eigen aanvraag wordt veilig vrijgegeven")
                    self._command_clock()
                    return True
                self._status(raw)
                expiry = self._expiry(raw)
                changed = (self._lease_expiry is not None and (
                    expiry is not None and abs(expiry-self._lease_expiry) > 2
                    or raw.get("timer_cancelled") is True))
                if raw["output"] is False or changed:
                    self.owned = self._possibly_owned = self.desired_on = False
                    self._minimum_started = None
                    self._lease_expiry = self._lease_deadline = None
                    if changed and raw["output"] is True:
                        self.manual_hold = True
                        self._set_state("blocked", "SG-contact buiten SolarPilot gewijzigd; handmatige stand blijft behouden")
                    return False
                self._command_clock()
                return True

            try:
                self._record_transport("off")
                adapter = self._transport()
                supports_off_callback = hasattr(adapter, "before_off_status")
                if supports_off_callback:
                    off_callback = before_off_status
                    adapter.before_off_status = off_callback
                else:
                    self._command_clock()
                raw = self._status(await asyncio.wait_for(adapter.set_off(),
                                                        float(self.settings["ack_timeout_s"])))
                if raw["output"] is not False:
                    raise ValueError("off_not_confirmed")
                release_confirmed = True
                self._transport_confirmed("off")
                self.owned = self._possibly_owned = False
                self._lease_expiry = self._lease_deadline = None
                if self.fault_code == "off_failed":
                    self.fault_code = self.fault = ""
            except (Exception, asyncio.CancelledError) as err:
                self._record_transport("off", error=err)
                cancelled = err if isinstance(err, asyncio.CancelledError) else None
                ownership_withdrawn = (getattr(err, "code", "") == "dispatch_changed"
                    and getattr(err, "command_attempted", False) is False
                    and not self.owned and not self._possibly_owned)
                if not ownership_withdrawn:
                    self.relay_on = None
                    self.relay_confirmed = False
                    if not preserve_fault:
                        self._fault("off_failed", "Vrijgave van het SG-contact nog niet bevestigd; de lokale toestemming wordt niet vernieuwd")
            finally:
                self._in_flight = False
                if (adapter is not None and supports_off_callback
                        and getattr(adapter, "before_off_status", None) is off_callback):
                    adapter.before_off_status = None
        if rest:
            self._begin_rest(request_reassessment=bool(policy_hold and release_confirmed
                and self.settings.get("profile") == "general" and self._hold_reason == "response_unknown"
                and self._session_started is not None and self.manual_mode == "auto"
                and not self.manual_hold and self.auto_enabled
                and getattr(self.runtime, "mode", "observe") == "solar"))
        if self._session_started is not None:
            self._record_session_end(reason, transport=(self._transport_evidence
                if isinstance(self._transport_evidence, dict)
                and self._transport_evidence.get("operation") == "off" else None), stop_evidence=frozen_stop)
            self._note("SG-aanvraag beëindigd: " + reason + self._observation_summary())
        self._session_started = None
        self._minimum_started = None
        self._session_finishing = False
        self._last_renewed = None
        if not self.fault and not self.manual_hold:
            self._set_state("rest" if rest else "normal", reason)
        await self._save()
        if cancelled is not None:
            raise cancelled

    def _observe_contact(self, raw):
        """Distinguish our expiry/late echo from an external contact change."""
        if raw is None:
            return
        now = self._clock()
        ours = self.owned or self._possibly_owned
        if ours and raw["output"] is False:
            ending_session = self._session_started is not None
            expired = self._lease_deadline is not None and now >= self._lease_deadline - 1
            limit_reached = (self._session_started is not None and
                now-self._session_started >= float(self.settings["max_session_s"]))
            if (expired and (self._session_finishing or limit_reached)
                    or self.settings.get("profile") == "general" and not self.completion_hold):
                self.completion_hold = True
                self._hold_reason = "session_limit" if self._session_finishing or limit_reached else "response_unknown"
                self._capture_need_reference()
            releasing = self._off_attempted or not self.desired_on
            self._record_session_end("Begrensde SG-sessieduur bereikt" if limit_reached or self._session_finishing
                else "Lokale SG-toestemming afgelopen" if expired else
                "Eigen SG-aanvraag vrijgegeven" if releasing else "SG-contact handmatig uitgeschakeld")
            self._session_finishing = False
            self.owned = self._possibly_owned = False
            self.desired_on = False
            self._lease_expiry = self._lease_deadline = None
            self._session_started = self._last_renewed = None
            self._minimum_started = None
            self._begin_rest(request_reassessment=bool(ending_session and (expired or releasing)
                and self.settings.get("profile") == "general" and self._hold_reason == "response_unknown"
                and self.manual_mode == "auto" and not self.manual_hold and self.auto_enabled
                and getattr(self.runtime, "mode", "observe") == "solar"))
            self._stable_since = self._import_since = None
            if expired or releasing:
                if self.fault_code in {"off_failed", "unavailable_read"}:
                    self.fault_code = self.fault = ""
                self._set_state("rest", "Lokale SG-toestemming afgelopen of eigen aanvraag vrijgegeven; opnieuw beoordelen na rusttijd")
            else:
                self.manual_hold = True
                self._set_state("blocked", "SG-contact handmatig uitgeschakeld; hervat de automatisering wanneer gewenst")
        elif ours and raw["output"] is True:
            expiry = self._expiry(raw)
            if (self._lease_expiry is not None
                    and (expiry is not None and abs(expiry - self._lease_expiry) > 2
                         or raw.get("timer_cancelled") is True
                         or finite(raw.get("timer_duration")) == 0)):
                self.owned = self._possibly_owned = self.desired_on = False
                self._record_session_end("SG-contact buiten SolarPilot gewijzigd; eigenaarschap vrijgegeven")
                self._session_started = self._last_renewed = None
                self._minimum_started = None
                self.manual_hold = True
                self._set_state("blocked", "SG-contact buiten SolarPilot gewijzigd; handmatige stand blijft behouden")
            elif expiry is None:
                # Missing/invalid timer fields cannot prove who changed it.
                # Retain only prior OFF/recovery authority, never renew ON.
                self.desired_on = False
                self._fault("lease_invalid", "Lokale SG-aflooptimer niet betrouwbaar bevestigd; bestaande eigen aanvraag wordt vrijgegeven")
            elif self._lease_deadline is not None and now > self._lease_deadline + 2:
                self.desired_on = False
                self._fault("lease_failed", "SG-contact bleef na de lokale aflooptijd aan; controleer de Shelly-terugval")
        elif raw["output"] and not self.manual_hold:
            self.manual_hold = True
            self._set_state("blocked", "SG-contact staat buiten SolarPilot aan; handmatige stand blijft behouden")

    def _valid_tank_observation(self, raw):
        """Accept only the live monitor's validated Celsius tank observation."""
        if not isinstance(raw, dict) or not self.settings.get("tank_temperature_entity"):
            return None
        temperature, stamp = finite(raw.get("temperature_c")), finite(raw.get("stamp"))
        if (raw.get("entity_id") != self.settings["tank_temperature_entity"]
                or temperature is None or not 0 <= temperature <= 100 or stamp is None
                or not -5 <= self._wall_clock() - stamp <= float(self.settings["stale_s"])):
            return None
        return {"entity_id": raw["entity_id"], "temperature_c": temperature, "stamp": stamp}

    def _capture_need_reference(self):
        # Capture the actual end observation once. Missing end evidence may not
        # be invented later from an unrelated/changed temperature context.
        observation = self._valid_tank_observation(self._tank_observation)
        self._need_reference = ({"schema": 1, **observation, "ended_at": self._wall_clock()}
                                if observation is not None and not self._tank_source_changed else None)
        self._need_candidate = None
        self._hold_origin = {"hold_reason": self._hold_reason or None, "stop_reason": None,
            "ended_at": self._wall_clock(), "session_provenance": deepcopy(self._session_provenance)}
        if self.settings.get("profile") == "general":
            native = self._valid_native_observation(self._native_observation)
            self._general_reference = {
                "schema": 1, "ended_at": self._wall_clock(),
                "signature": native["signature"] if native else None,
                "native_stamp": native["stamp"] if native else None,
                "solar_stamp": (self._solar_observation or {}).get("stamp"),
                "solar_reset_stamp": None, "native_reset_stamp": None,
                "profile_transition": False, "native_rebase": False, "native_after": None}
            self._general_candidate = self._general_reset_candidate = None

    def _read_native(self):
        monitor = getattr(self.runtime, "panasonic", None)
        try:
            value = monitor.overview() if monitor is not None else None
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    def _valid_native_observation(self, value):
        if not isinstance(value, dict) or value.get("context_reliable") is not True:
            return None
        stamp = finite(value.get("context_stamp"))
        signature = value.get("context_signature")
        context = value.get("context")
        if (stamp is None or not isinstance(signature, str) or not signature
                or context not in RELEVANT_NATIVE_CONTEXTS | {"normal"}
                or not -5 <= self._wall_clock() - stamp <= float(self.settings["stale_s"])):
            return None
        return {"stamp": stamp, "signature": signature, "context": context}

    def cooling_block_reason(self, *, live=False):
        """A scope choice never certifies protection from condensation."""
        if self.settings.get("profile", "dhw_only") != "general":
            return ""
        if self.settings.get("cooling_protection_confirmed") is True:
            return ""
        value = self._read_native() if live else self._native_observation
        native = self._valid_native_observation(value)
        if native is not None and value.get("cooling_possible") is False:
            return ""
        value = value if isinstance(value, dict) else {}
        diagnostic = value.get("cooling_context_diagnostic")
        diagnostic = diagnostic if isinstance(diagnostic, dict) and diagnostic.get("schema") == 1 else {}
        code = diagnostic.get("code")
        stamp = finite(value.get("context_stamp"))
        if stamp is not None and not -5 <= self._wall_clock() - stamp <= float(self.settings["stale_s"]):
            return "SG wacht op actuele Panasonic-koelcontext: context verouderd; condensbeveiliging niet bevestigd"
        reasons = {
            "no_configured_zones": "SG wacht op gekoppelde Panasonic-ruimtes; condensbeveiliging niet bevestigd",
            "zone_source_missing": "SG wacht op een ontbrekende Panasonic-ruimtebron; condensbeveiliging niet bevestigd",
            "zone_source_unavailable": "SG wacht op een beschikbare Panasonic-ruimtebron; condensbeveiliging niet bevestigd",
            "zone_source_stale": "SG wacht op actuele Panasonic-ruimtemeldingen; condensbeveiliging niet bevestigd",
            "native_context_conflict": "SG wacht op eenduidige Panasonic-koelcontext: bronnen spreken elkaar tegen; condensbeveiliging niet bevestigd",
            "auto_program_unknown": "SG wacht op het werkelijke Panasonic-programma achter AUTO; condensbeveiliging niet bevestigd",
            "cooling_present": "Extra SG-koeling niet vrijgegeven: condens-/dauwpuntbeveiliging niet bevestigd",
        }
        if isinstance(code, str) and code in reasons:
            return reasons[code]
        if native is not None and native["context"] == "space_cooling":
            return reasons["cooling_present"]
        return "SG wacht op bekende Panasonic-koelcontext; condensbeveiliging niet bevestigd"

    def _convert_legacy_hold(self):
        """Convert only the old tank policy, keeping its rollback provenance."""
        if self._general_reference is not None:
            return
        self._hold_provenance = {
            "profile": "dhw_only", "completion_hold": self.completion_hold,
            "need_reference": deepcopy(self._need_reference),
            "tank_source_changed": self._tank_source_changed,
            "converted_at": self._wall_clock()}
        self._general_reference = {
            "schema": 1, "ended_at": self._wall_clock(), "signature": None,
            "native_stamp": None, "solar_stamp": None,
            "solar_reset_stamp": None, "native_reset_stamp": None,
            "profile_transition": True, "native_rebase": False, "native_after": None}
        self._hold_reason = "profile_changed"
        self._general_candidate = self._general_reset_candidate = None
        self._need_candidate = None
        self._note("Bevestigde algemene SG-keuze: oude tankwachtstand wordt met verse native context of een nieuwe zonneperiode herbeoordeeld")

    @staticmethod
    def _confirmed_reports(candidate, kind, signature, stamp, now):
        """A real new final report is required, not elapsed wall time alone."""
        if candidate is None or candidate["kind"] != kind or candidate["signature"] != signature:
            return {"kind": kind, "signature": signature, "first_seen": now,
                    "last_stamp": stamp, "reports": 1}, False
        new_report = stamp > candidate["last_stamp"]
        if new_report:
            candidate["last_stamp"] = stamp
            candidate["reports"] += 1
        return candidate, (new_report and candidate["reports"] >= 2
                           and now - candidate["first_seen"] >= NEW_CONTEXT_CONFIRM_S)

    def _residual_reassessment_threshold(self):
        values = [finite(self.settings.get(key)) for key in ("threshold_w", "expected_power_w")]
        return max(values) if all(value is not None and value >= 0 for value in values) else None

    def _residual_source_signature(self, source_identity, grid_source):
        control = self._control_identity()
        if control is None:
            return None
        try:
            return hashlib.sha256(json.dumps([control, source_identity, grid_source],
                sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        except (TypeError, ValueError):
            return None

    def _request_rest_proven(self):
        """Only a known ended automatic request can replace request-only rest.

        This never infers a compressor start/non-start. Panasonic still owns
        compressor protection; the evidence only bounds another SG request.
        """
        if (self.settings.get("profile") != "general" or not self.completion_hold
                or self._hold_reason != "response_unknown" or self._request_rest_policy != "request"
                or self._closed or getattr(self.runtime, "_closed", False)
                or (hasattr(self.runtime.entry, "runtime_data") and self.runtime.entry.runtime_data is not self.runtime)
                or not self._request_rest_off_current or not self.relay_confirmed or self.relay_on is not False
                or self.owned or self._possibly_owned or self.desired_on or self._in_flight
                or self._restart_release or self._restart_resume is not None
                or self.manual_hold or self.manual_mode != "auto" or self.fault
                or getattr(self.runtime, "pending", None) or getattr(self.runtime, "handover", None)
                or getattr(self.runtime, "removal_requested", False)
                or getattr(self.runtime, "restart_blocking", False)):
            return False
        origin = self._hold_origin if isinstance(self._hold_origin, dict) else {}
        last = self._last_session if isinstance(self._last_session, dict) else {}
        old = self._historical_provenance(origin.get("session_provenance"))
        ended = self._historical_provenance(last.get("session_provenance"))
        wall = self._wall_clock()
        end_stamp, origin_stamp = finite(last.get("ended_at")), finite(origin.get("ended_at"))
        contact_stamp, rest_stamp = finite(self._relay_observed_at), finite(self._rest_until_wall)
        if (old is None or ended is None or old != ended or old.get("request_mode") != "automatic"
                or last.get("provenance_status") != "recorded_at_start"
                or origin.get("hold_reason") != "response_unknown"
                or not isinstance(last.get("reason"), str) or last["reason"] != origin.get("stop_reason")
                or type(last.get("ended_at")) not in (int, float)
                or type(origin.get("ended_at")) not in (int, float)
                or end_stamp is None or origin_stamp != end_stamp or not 0 < end_stamp <= wall
                or old.get("command_issued_at") is None
                or not 0 < old["started_at"] <= old["command_issued_at"] <= end_stamp
                or contact_stamp is None or not end_stamp < contact_stamp <= wall
                or wall-contact_stamp > float(self.settings["stale_s"])
                or rest_stamp is None or abs(rest_stamp-end_stamp-float(self.settings["rest_s"])) > 5):
            return False
        binding = old.get("binding_identity")
        if (not isinstance(binding, str) or len(binding) != 64
                or binding != self._relay_binding_identity):
            return False
        identity = old.get("control_identity")
        if identity is None or identity != self._control_identity():
            return False
        # Older sessions without a full original control hash keep the normal
        # rest fallback. No historical identity is inferred from current options.
        runtime_settings = getattr(self.runtime, "settings", {})
        current = effective_session_policy(self.settings, old["policy"]["effective_min_session_s"],
            runtime_settings.get("max_import_w") if isinstance(runtime_settings, dict) else None)
        return session_policy_hash(current) == old["policy_hash"]

    def _request_rest_live_allowed(self):
        """Read the existing automatic boundary without creating stop evidence."""
        gate = getattr(self.runtime, "sg_dispatch_allowed", None)
        if not callable(gate):
            return self._injected_adapter
        owner = getattr(gate, "__self__", self.runtime)
        existed = hasattr(owner, "_sg_dispatch_rejection")
        previous = getattr(owner, "_sg_dispatch_rejection", None)
        try:
            return gate(renewal=False, automatic=True) is True
        except Exception:
            return False
        finally:
            if existed:
                owner._sg_dispatch_rejection = previous
            elif hasattr(owner, "_sg_dispatch_rejection"):
                del owner._sg_dispatch_rejection

    def _general_reassessment(self, *, residual_allowed=False):
        if (self.settings.get("profile") != "general" or not self.completion_hold
                or self.settings.get("profile_confirmed") is not True):
            return False
        reference = self._general_reference
        if reference is None:
            return False
        now = self._clock()
        native = self._valid_native_observation(self._native_observation)
        ended = reference["ended_at"]
        native_new = (native is not None and native["stamp"] > max(
            ended, finite(reference.get("native_stamp")) or ended,
            finite(reference.get("native_after")) or ended))
        if reference.get("native_rebase") is True and native_new:
            # First fresh report of a newly selected reader establishes a
            # baseline only. A later actual context change must still be proven.
            reference.update(signature=native["signature"], native_stamp=native["stamp"], native_rebase=False)
            native_new = False
        solar = self._solar_observation
        solar_new = (solar is not None and solar["stamp"] > max(
            ended, finite(reference.get("solar_stamp")) or ended))
        # Observe a real inactive interval after the session. Temporary missing
        # sources do not reset an episode and cannot supply new demand evidence.
        reset_kind = None
        if solar_new and solar["watts"] <= float(self.settings["hysteresis_w"]):
            reset_kind, signature, stamp = "solar", "near_zero", solar["stamp"]
        elif native_new and native["context"] == "normal":
            reset_kind, signature, stamp = "native", native["signature"], native["stamp"]
        if reset_kind:
            self._general_reset_candidate, confirmed = self._confirmed_reports(
                self._general_reset_candidate, reset_kind, signature, stamp, now)
            if confirmed:
                reference[reset_kind + "_reset_stamp"] = stamp
                self._general_reset_candidate = None
        else:
            self._general_reset_candidate = None
        residual_ready = (self._hold_reason == "response_unknown" and residual_allowed is True
            and solar_new and self._residual_reassessment_threshold() is not None
            and solar["watts"] >= self._residual_reassessment_threshold()
            and isinstance(solar.get("source_signature"), str))
        early_residual = (now < self._rest_until and residual_ready and self._request_rest_proven()
            and solar["stamp"] > self._hold_origin["ended_at"] and self._request_rest_live_allowed())
        if now < self._rest_until and not early_residual:
            self._general_candidate = None
            return False
        kind = None
        if early_residual:
            kind, signature, stamp = "fresh_residual_surplus", solar["source_signature"], solar["stamp"]
        elif (native_new and native["context"] in RELEVANT_NATIVE_CONTEXTS
                and (reference.get("profile_transition") is True
                     or (reference.get("signature") is not None
                         and native["signature"] != reference["signature"])
                     or (finite(reference.get("native_reset_stamp")) is not None
                         and native["stamp"] > reference["native_reset_stamp"]))):
            kind, signature, stamp = "fresh_native_context", native["signature"], native["stamp"]
        elif (solar_new and solar["watts"] >= float(self.settings["threshold_w"])
                and finite(reference.get("solar_reset_stamp")) is not None
                and solar["stamp"] > reference["solar_reset_stamp"]):
            kind, signature, stamp = "new_solar_period", "qualified_surplus", solar["stamp"]
        elif residual_ready:
            kind, signature, stamp = "fresh_residual_surplus", solar["source_signature"], solar["stamp"]
        if kind is None:
            self._general_candidate = None
            return False
        if kind == "fresh_residual_surplus" and isinstance(self._general_candidate, dict):
            previous = self._general_candidate
            if (previous.get("kind") == kind and (stamp < previous["last_stamp"]
                    or self._wall_clock()-previous["last_stamp"] > float(self.settings["stale_s"]))):
                # Unobserved expired P1/PV evidence is not five minutes of
                # verified residual solar. A returned meter starts new proof.
                self._general_candidate = None
                if stamp < previous["last_stamp"]:
                    return False
        self._general_candidate, confirmed = self._confirmed_reports(
            self._general_candidate, kind, signature, stamp, now)
        if not confirmed:
            return False
        self._last_rearm = {"kind": kind, "at": self._wall_clock()}
        if early_residual:
            self._last_rearm["request_rest_replaced_s"] = max(0.0, self._rest_until-now)
            self._rest_until = now
            self._rest_until_wall = self._wall_clock()
            self._request_rest_policy = None
        self.completion_hold = False
        self._hold_reason = ""
        self._hold_origin = None
        self._general_reference = self._general_candidate = self._general_reset_candidate = None
        self._need_reference = self._need_candidate = None
        self._tank_source_changed = False
        self._stable_since = None
        self._note("Werkelijk restoverschot opnieuw bevestigd; warmtepomprespons blijft onbekend; verse veiligheidsbeoordeling volgt"
            if kind == "fresh_residual_surplus" else
            "Nieuwe betrouwbare SG-aanleiding vastgesteld; verse zonne- en veiligheidsbeoordeling volgt")
        return True

    def _new_storage_available(self):
        """A sustained measured decline permits another solar evaluation.

        This proves additional tank storage space, not comfort demand, previous
        SG ownership, a successful Panasonic boost or an effective SG setpoint.
        """
        if (self.settings.get("profile", "dhw_only") == "general" or not self.completion_hold
                or self._tank_source_changed or self._need_reference is None):
            return False
        reference = self._need_reference
        observation = self._valid_tank_observation(self._tank_observation)
        now = self._clock()
        if (now < self._rest_until or observation is None
                or observation["entity_id"] != reference["entity_id"]
                or observation["stamp"] <= max(reference["stamp"], reference["ended_at"])
                or reference["temperature_c"] - observation["temperature_c"] < NEW_STORAGE_DROP_C):
            self._need_candidate = None
            return False
        candidate = self._need_candidate
        if candidate is None:
            self._need_candidate = {"first_seen": now, "last_stamp": observation["stamp"], "reports": 1}
            return False
        new_report = observation["stamp"] > candidate["last_stamp"]
        if new_report:
            candidate["last_stamp"] = observation["stamp"]
            candidate["reports"] += 1
        if not new_report or candidate["reports"] < 2 or now - candidate["first_seen"] < NEW_STORAGE_CONFIRM_S:
            return False
        self._last_rearm = {"kind": "fresh_tank_decline", "at": self._wall_clock(),
                           "drop_c": round(reference["temperature_c"] - observation["temperature_c"], 2)}
        self.completion_hold = False
        self._hold_reason = ""
        self._hold_origin = None
        self._need_reference = self._need_candidate = None
        self._stable_since = None
        self._note("Tank na vorige SG-sessie aantoonbaar afgekoeld; nieuw zonneoverschot wordt beoordeeld")
        return True

    def _completion_reason(self):
        if self.settings.get("profile") == "general":
            if self._hold_reason == "response_unknown" and self._request_rest_proven():
                return "Vorige SG-aanvraag beëindigd; bevestig vijf minuten werkelijk restoverschot en actuele UIT; daarna gewone startvertraging"
            prefix = {"native_completed": "Native voltooiing bevestigd",
                      "no_uptake": "Geen extra opname bevestigd",
                      "response_unknown": "Vorige SG-aanvraag beëindigd; wacht na rust op vijf minuten werkelijk restoverschot of nieuwe toestelcontext",
                      "profile_changed": "Algemene SG-keuze bevestigd"}.get(
                          self._hold_reason, "Begrensde sessieduur bereikt; SG-effect onbekend")
            return prefix if self._hold_reason == "response_unknown" else prefix + "; wacht op een nieuwe zonneperiode of betrouwbare gewijzigde native context"
        if self._tank_source_changed:
            return "Tankbron gewijzigd; hervat de automatisering na controle van de nieuwe bron"
        if self._need_reference is None:
            return "Sessielimiet bereikt; geen betrouwbare tankmeting bij het einde. Gebruik Hervatten voor een nieuwe beoordeling"
        return "Vorige SG-sessie afgerond; nieuwe boost wacht op aantoonbare afkoeling van de tank"

    def _actuator_conflicts(self, settings):
        profiles = getattr(self.runtime, "configs", {})
        batteries = getattr(getattr(self.runtime, "battery_fleet", None), "configs", {})
        profiles = list(profiles.values()) if isinstance(profiles, dict) else profiles if isinstance(profiles, list) else []
        batteries = list(batteries.values()) if isinstance(batteries, dict) else batteries if isinstance(batteries, list) else []
        return actuator_conflicts(settings, profiles + batteries)

    def _gates(self, *, data_fresh, phase_allowed, priority_allowed, hard_limit,
               electrical_reason=None, include_completion_hold=True):
        reasons = []
        if self._closed:
            reasons.append("SolarPilot wordt afgesloten")
        if not self.configured:
            reasons.append("Koppel eerst de bestaande SG-uitgang")
        if self._actuator_conflicts(self.settings):
            reasons.append("De SG-uitgang is ook aan een ander toestel gekoppeld; één uitgang mag maar één eigenaar hebben")
        if not self.auto_enabled:
            reasons.append("Automatische zonneboost staat uit")
        if getattr(self.runtime, "mode", "observe") != "solar":
            reasons.append("Automatisch regelen staat niet aan")
        if self.settings.get("commissioning_confirmed") is not True:
            reasons.append("Bevestig eerst de SG-mapping en Panasonic-instellingen")
        if self.settings.get("watchdog_confirmed") is not True:
            reasons.append("Test en bevestig eerst de lokale Shelly-aflooptimer")
        if (self.settings.get("profile") == "general"
                and self.settings.get("profile_confirmed") is not True):
            reasons.append("Bevestig eerst lokaal het toepassingsbereik van de algemene SG-zonneboost")
        cooling_reason = self.cooling_block_reason()
        if cooling_reason:
            reasons.append(cooling_reason)
        if validate_config(self.settings):
            reasons.append("SG-instellingen vragen controle")
        if data_fresh is not True:
            reasons.append("Wachten op betrouwbare actuele net- en zonnemetingen")
        if phase_allowed is not True or hard_limit:
            reasons.append(electrical_reason if isinstance(electrical_reason, str) and electrical_reason.strip()
                           else "Elektrische grens of fasebewaking laat geen extra SG-aanvraag toe")
        if priority_allowed is not True:
            reasons.append("Hoger geplaatste of beschermde verbruikers krijgen voorrang")
        if self.manual_hold:
            reasons.append("Handmatige SG-stand blijft behouden; hervat de automatisering wanneer gewenst")
        if self.manual_mode == "off":
            reasons.append("SG-boost tijdelijk handmatig uit; daarna automatisch")
        origin = self._manual_session_origin()
        if origin is not None and self._clock()-origin >= float(self.settings["max_session_s"]):
            reasons.append("Begrensde SG-sessieduur bereikt; tijdelijke keuze verlengt de sessielimiet niet")
        if include_completion_hold and self.completion_hold and self.manual_mode != "on":
            reasons.append(self._completion_reason())
        if self.fault:
            reasons.append(self.fault)
        return reasons

    async def tick(self, *, surplus_w, data_fresh, phase_allowed, priority_allowed=True,
                   grid_import_w=0, physical_evidence=None, tank_observation=None,
                   native_observation=None, solar_stamp=None, hard_limit=False,
                   real_surplus_w=_UNSET_RESIDUAL, electrical_reason=None, grid_import_stamp=None,
                   grid_import_source=None, start_wait_source_gap=False,
                   start_source_identity=None, **_context):
        if not self._started:
            await self.start()
        async with self._lock:
            self.sent_this_tick = self.renewed_this_tick = False
            self._request_rest_off_current = False
            now = self._clock()
            if (self._stable_since is not None and self._start_last_evaluated is not None
                    and now-self._start_last_evaluated > 300):
                self._reset_start_window()
            if self._stable_since is not None:
                self._start_last_evaluated = now
            if self._manual_control is not None and self.manual_mode == "auto":
                self._generation += 1
                self._manual_control = self._manual_deadline = None
                self._stable_since = None
                self._note("Tijdelijke SG-keuze afgelopen; automatische regeling hervat")
                await self._save()
            self._tank_observation = self._valid_tank_observation(tank_observation)
            self._native_observation = (dict(native_observation) if isinstance(native_observation, dict)
                                        else self._read_native())
            surplus, imported, stamp = finite(surplus_w), finite(grid_import_w), finite(solar_stamp)
            if (self._stable_since is not None and
                    (self._start_source_identity is not None and start_source_identity != self._start_source_identity
                     or stamp is not None and self._start_source_stamp is not None and stamp < self._start_source_stamp)):
                self._reset_start_window()
            self._start_source_identity = deepcopy(start_source_identity)
            if stamp is not None:
                self._start_source_stamp = stamp
            residual = surplus if real_surplus_w is _UNSET_RESIDUAL else finite(real_surplus_w)
            data_fresh = (data_fresh is True and surplus is not None and imported is not None
                          and residual is not None and surplus >= 0 and imported >= 0 and residual >= 0)
            import_stamp = finite(grid_import_stamp)
            import_policy = self._import_policy_current()
            if (data_fresh and import_policy is not None and imported > import_policy[0]
                    and (import_stamp is None or not -5 <= self._wall_clock() - import_stamp < float(self.settings["stale_s"]))):
                data_fresh = False
            if data_fresh:
                data_fresh = self._observe_import(imported, import_stamp, grid_import_source, now)
            else:
                self._observe_import(0, None, None, now)
            # Already solar-fed native consumption qualifies only the start
            # threshold. A new solar episode still needs fresh residual export;
            # continuing native draw cannot create a completion-hold reset loop.
            self._solar_observation = ({"watts": residual, "stamp": stamp,
                "source_signature": self._residual_source_signature(start_source_identity, grid_import_source)}
                if data_fresh and stamp is not None
                and -5 <= self._wall_clock() - stamp <= float(self.settings["stale_s"]) else None)
            native = self._valid_native_observation(self._native_observation)
            if native is not None and (self.owned or self._in_flight):
                self._session_reference = {"schema": 1, "signature": native["signature"],
                    "native_stamp": native["stamp"],
                    "solar_stamp": (self._solar_observation or {}).get("stamp")}
            self._physical = dict(physical_evidence) if isinstance(physical_evidence, dict) else {}
            physical = self._physical
            self.panasonic_confirmed = (physical.get("sg_active") if physical.get("verified") is True
                                        and type(physical.get("sg_active")) is bool else None)
            if self._native_observation.get("sg_status_confirmed") is True:
                status = self._native_observation.get("sg_status")
                self.panasonic_confirmed = True if status == "active" else False if status == "inactive" else None
            if (self.settings.get("profile", "dhw_only") != "general" and self.completion_hold
                    and physical.get("verified") is True and physical.get("restart_ready") is True):
                self.completion_hold = False
                self._hold_reason = ""
                self._need_reference = self._need_candidate = None
                self._stable_since = None
            if self._new_storage_available():
                await self._save()
            raw = await self._read() if self.configured and not self._closed else None
            if self._restart_release and self._restart_resume is None and raw is not None:
                await self._reconcile_restart(raw)
                # Reconciliation may have written OFF. Its fresh readback or
                # unknown result supersedes the earlier ON snapshot.
                raw = None
            observed = (self.owned, self._possibly_owned, self.manual_hold, self.completion_hold,
                        self._session_started, self.fault_code)
            if self._restart_resume is None:
                self._observe_contact(raw)
            self._request_rest_off_current = bool(raw is not None and raw.get("output") is False
                and self.relay_confirmed and self.relay_on is False)
            if observed != (self.owned, self._possibly_owned, self.manual_hold, self.completion_hold,
                            self._session_started, self.fault_code):
                await self._save()
            if self._profile_change_release:
                self._profile_change_release = False
                if self.owned or self._possibly_owned:
                    await self._release("SG-toepassingsbereik gewijzigd; vorige aanvraag veilig vrijgegeven")
                self._stable_since = None
                await self._save()
            now = self._clock()
            if import_stamp is not None and not -5 <= self._wall_clock() - import_stamp < float(self.settings["stale_s"]):
                data_fresh = False
            if stamp is not None and not -5 <= self._wall_clock()-stamp <= float(self.settings["stale_s"]):
                data_fresh = False
                self._solar_observation = None
            previous_reference = deepcopy(self._general_reference)
            residual_allowed = not self._gates(data_fresh=data_fresh, phase_allowed=phase_allowed,
                priority_allowed=priority_allowed, hard_limit=hard_limit,
                electrical_reason=electrical_reason, include_completion_hold=False)
            rearmed = self._general_reassessment(residual_allowed=residual_allowed)
            if rearmed or previous_reference != self._general_reference:
                await self._save()
            gates = self._gates(data_fresh=data_fresh, phase_allowed=phase_allowed,
                                 priority_allowed=priority_allowed, hard_limit=hard_limit,
                                 electrical_reason=electrical_reason)
            self._blocked_reasons = gates
            if self._restart_resume is not None and raw is not None:
                await self._reconcile_restart(raw, current_gates=gates,
                    source_gap=start_wait_source_gap is True or not data_fresh and phase_allowed is True and not hard_limit)
                if self.sent_this_tick:
                    return True
            if gates:
                waiting_gap = (not self.owned and self._stable_since is not None
                    and self.manual_mode == "auto" and not self._gates(data_fresh=True,
                        phase_allowed=True, priority_allowed=True if start_wait_source_gap is True else priority_allowed, hard_limit=False)
                    and (start_wait_source_gap is True or not data_fresh and phase_allowed is True and not hard_limit))
                if waiting_gap:
                    self._keep_start_window("measurement_gap", now)
                else:
                    self._reset_start_window()
                if self.owned or self._possibly_owned:
                    self._generation += 1
                    await self._release(gates[0], preserve_fault=bool(self.fault))
                self._set_state("blocked" if self.auto_enabled or self.fault or self.manual_hold else "normal", gates[0])
                return self.sent_this_tick
            if self._restart_release or raw is None or not self.relay_confirmed:
                self._reset_start_window()
                self._set_state("blocked", "Wachten op betrouwbare SG-uitgangstatus")
                return self.sent_this_tick
            if self.owned and self.desired_on:
                elapsed = now - self._session_started if self._session_started is not None else 0
                complete = self.manual_mode != "on" and physical.get("verified") is True and (physical.get("completed") is True or physical.get("no_uptake") is True)
                if complete or elapsed >= float(self.settings["max_session_s"]):
                    self.completion_hold = True
                    self._hold_reason = ("no_uptake" if complete and physical.get("no_uptake") is True
                                         else "native_completed" if complete else "session_limit")
                    self._capture_need_reference()
                    self._generation += 1
                    reason = "Bevestigde boost voltooid of geen extra opname" if complete else "Begrensde SG-sessieduur bereikt"
                    await self._release(reason)
                    return self.sent_this_tick
                # One read-only diagnostic per session; neither absence of proof
                # nor low power permits a pulse, fault or a Panasonic command.
                self._observe_low_uptake()
                # Residual export need not retain the original start threshold:
                # consuming the admitted solar energy is the intended effect.
                if self.manual_mode == "on":
                    self._set_state("boost_requested", self._active_reason())
                elif imported > float(self.settings["import_threshold_w"]):
                    # Missing original P1 evidence cannot buy a cloud buffer.
                    if self._import_since is None and not self.minimum_hold_active:
                        self._generation += 1
                        await self._release("Netmeting niet actueel; extra SG-aanvraag vrijgegeven")
                        return self.sent_this_tick
                    if (self._import_since is not None and now - self._import_since >= float(self.settings["stop_delay_s"])
                            and not self.minimum_hold_active):
                        self._generation += 1
                        await self._release("Aanhoudende netafname; extra SG-aanvraag vrijgegeven")
                        return self.sent_this_tick
                    self._set_state("boost_requested", self._active_reason() if self.minimum_hold_active
                                    else "Tijdelijke netafname; wolkenbuffer voorkomt vroeg vrijgeven")
                else:
                    self._import_since = None
                    self._set_state("boost_requested", self._active_reason())
                if self._last_renewed is not None and now - self._last_renewed >= float(self.settings["renew_s"]):
                    # Minimum and cloud grace overlap; renewing the same short
                    # local lease never restarts either timer or the hard max.
                    if self.manual_mode == "on" or imported <= float(self.settings["import_threshold_w"]) or self.minimum_hold_active or self.cloud_hold_active:
                        await self._issue_on(renewal=True)
                return self.sent_this_tick
            if self.manual_mode == "on":
                await self._issue_on()
                return self.sent_this_tick
            if now < self._rest_until:
                self._reset_start_window()
                self._set_state("rest", "SG-contact vrijgegeven; rusttijd voorkomt herhaald schakelen")
                return self.sent_this_tick
            if surplus < float(self.settings["threshold_w"]):
                self._keep_start_window("cloud", now)
                self._set_state("waiting_surplus", f"Wachten op minstens {float(self.settings['threshold_w']):g} W bruikbaar zonnevermogen")
                return self.sent_this_tick
            if self._stable_since is None:
                self._stable_since = now
            elif self._start_soft_since is not None and now-self._start_soft_since > 300:
                self._stable_since = now
            self._start_soft_since = self._start_soft_kind = None
            self._start_last_evaluated = now
            remaining = max(0.0, float(self.settings["start_delay_s"]) - (now - self._stable_since))
            if remaining > 0:
                self._set_state("waiting_surplus", f"Voldoende zonnevermogen; stabiliteitscontrole nog {int(remaining + .999)} s")
                return self.sent_this_tick
            await self._issue_on()
            return self.sent_this_tick

    def _reset_start_window(self):
        self._stable_since = self._start_soft_since = None
        self._start_soft_kind = None
        self._start_last_evaluated = None

    def _dispatch_start_wait(self, generation):
        if generation != self._generation or self.manual_mode != "auto" or self._stable_since is None:
            self._reset_start_window()
            return False
        classify = getattr(self.runtime, "sg_start_wait_kind", None)
        try:
            kind = classify() if callable(classify) else None
        except Exception:
            kind = None
        if kind not in ("cloud", "measurement_gap"):
            self._reset_start_window()
            return False
        self._keep_start_window(kind, self._clock())
        return self._stable_since is not None

    def _keep_start_window(self, kind, now):
        if self._stable_since is None:
            self._start_soft_since = self._start_soft_kind = None
            return
        if self._start_soft_since is None:
            self._start_soft_since = now
        self._start_soft_kind = kind
        if now-self._start_soft_since > 300:
            self._reset_start_window()

    async def set_manual_control(self, mode, duration_s=None):
        """Persist one bounded deliberate request; never extend it on reload."""
        if (type(mode) is not str or mode not in ("auto", "on", "off")
                or mode == "auto" and duration_s is not None
                or mode != "auto" and (type(duration_s) is not int or duration_s not in (1800, 3600))):
            raise HomeAssistantError("Kies Automatisch, of tijdelijk Aan/Uit voor 30 of 60 minuten.")
        # Withdrawal wins even when an older ON is waiting on storage/transport.
        self._generation += 1
        generation = self._generation
        if mode != "on":
            self.desired_on = False if mode == "off" else self.desired_on
        async with self._lock:
            if (self._closed or getattr(self.runtime, "_closed", False)
                    or hasattr(self.runtime.entry, "runtime_data") and self.runtime.entry.runtime_data is not self.runtime):
                raise HomeAssistantError("Deze SolarPilot-regeling is afgesloten.")
            previous, previous_deadline = self._manual_control, self._manual_deadline
            previous_origin = self._manual_session_started
            raw = await self._read(force=True) if mode != "auto" and self.configured else None
            if generation != self._generation:
                raise HomeAssistantError("De SG-keuze is intussen vervangen.")
            if mode == "on" and (raw is None or raw.get("setup_valid") is not True
                    or not isinstance(raw.get("fingerprint"), dict) or not raw["fingerprint"]):
                raise HomeAssistantError("Controleer eerst de actuele SG-uitgang en lokale terugval.")
            wall, now = self._wall_clock(), self._clock()
            self._manual_control = (None if mode == "auto" else {"schema": 1, "mode": mode,
                "duration_s": duration_s, "created_at": wall, "expires_at": wall+duration_s,
                "control_identity": self._control_identity(),
                "fingerprint": deepcopy(raw.get("fingerprint")) if raw is not None else deepcopy(self._commissioned_fingerprint),
                "binding_identity": raw.get("binding_identity") if raw is not None else self._binding_identity,
                "session_started_at": wall-(now-self._session_started) if self._session_started is not None else None})
            self._manual_deadline = None if mode == "auto" else now+duration_s
            self._manual_session_started = self._session_started if mode == "on" else None
            if mode == "on" and (not self._on_permission_current(generation)
                    or self._actuator_conflicts(self.settings)):
                self._manual_control, self._manual_deadline = previous, previous_deadline
                self._manual_session_started = previous_origin
                if self.manual_hold:
                    raise HomeAssistantError("Het SG-contact is buiten SolarPilot gewijzigd; kies eerst Hervatten voordat je tijdelijk Aan kiest.")
                raise HomeAssistantError("Handmatige SG-boost vereist actieve regeling, een bevestigde koppeling en geldige veiligheidsvoorwaarden.")
            self._stable_since = None
            try:
                await self._save()
            except BaseException:
                if mode == "on":
                    self._manual_control, self._manual_deadline = previous, previous_deadline
                    self._manual_session_started = previous_origin
                else:
                    # Failed persistence cannot keep the old live ON choice.
                    self._manual_control = self._manual_deadline = None
                    self.desired_on = False
                    await self._release("Tijdelijke SG-keuze kon niet worden opgeslagen; eigen aanvraag vrijgegeven")
                raise
            if mode == "off":
                if (raw is not None and raw.get("output") is True and raw.get("setup_valid") is True
                        and not self.fault and not validate_config(self.settings)):
                    # This explicit user action names the current contact. A
                    # later external timer change still vetoes its OFF callback.
                    self._possibly_owned = True
                    self._lease_expiry = self._expiry(raw)
                    self._off_attempted = False
                    self.manual_hold = False
                await self._release("SG-boost tijdelijk handmatig uit", policy_hold=False)
            self._note("SG-bediening: " + ("automatisch" if mode == "auto" else
                       f"tijdelijk {mode} voor {duration_s//60} minuten"))
            await self._save()

    async def set_enabled(self, enabled):
        if type(enabled) is not bool:
            raise HomeAssistantError("Kies aan of uit voor automatische zonneboost.")
        if not enabled:
            self._generation += 1
            self.desired_on = False
        async with self._lock:
            updated = {**self.settings, "enabled": enabled}
            if enabled and validate_config(updated):
                raise HomeAssistantError("Bevestig eerst de juiste SG-koppeling en de geteste lokale Shelly-terugval.")
            if enabled and self._actuator_conflicts(updated):
                raise HomeAssistantError("De SG-uitgang is ook aan een ander toestel gekoppeld; één uitgang mag maar één eigenaar hebben.")
            previous = deepcopy(self.settings)
            self.settings = normalize_config(updated)
            self.config = self.settings
            self._stable_since = None
            if not enabled:
                await self._release("Automatische zonneboost uitgeschakeld", rest=True)
            try:
                persist = getattr(self.runtime, "set_sg_enabled", None)
                if callable(persist):
                    result = persist(enabled)
                    if inspect.isawaitable(result):
                        await result
                else:
                    self._persist_settings()
            except BaseException:
                # A rejected enable grants no live authority. A withdrawal
                # remains effective even if saving its preference fails.
                if enabled:
                    self.settings = previous
                    self.config = self.settings
                raise
            await self._save()

    async def resume_automation(self):
        self._generation += 1
        async with self._lock:
            raw = await self._read(force=True) if self.configured else None
            if raw is None:
                raise HomeAssistantError("De SG-uitgang is nog niet betrouwbaar bereikbaar.")
            if self.fault_code == "firmware_changed":
                raise HomeAssistantError("Bevestig de gewijzigde SG-koppeling en test de lokale aflooptimer opnieuw in de instellingen.")
            self.manual_hold = False
            self._manual_control = self._manual_deadline = None
            self.completion_hold = False
            self._need_reference = self._need_candidate = None
            self._general_reference = self._general_candidate = self._general_reset_candidate = None
            self._hold_reason = ""
            self._tank_source_changed = False
            self.fault_code = self.fault = ""
            self._off_attempted = False
            # Explicit resume grants authority to reconcile this contact, not
            # authority to continue an unleased/manual ON or to control Panasonic.
            if raw["output"]:
                # The deliberate resume names the current request, while a
                # later timer change during its OFF preflight stays protected.
                self._lease_expiry = self._expiry(raw)
                self._possibly_owned = True
                await self._release("Handmatige SG-stand vrijgegeven; verse zonnebeoordeling volgt", policy_hold=False)
            self._stable_since = None
            self._started = True
            self._set_state("rest" if self._clock() < self._rest_until else "waiting_surplus",
                            "Automatisering hervat; verse zonnebeoordeling volgt")
            await self._save()

    async def prepare_for_removal(self):
        self._generation += 1
        self.desired_on = False
        async with self._lock:
            await self._release("Eigen SG-aanvraag vrijgegeven voor afsluiten", rest=False)

    async def close(self, *, persist=True):
        if not persist:
            self._suppress_saves = True
        self._closed = True
        await self.prepare_for_removal()

    def _wait_progress(self, now):
        """Describe current evidence waits without granting or changing authority.

        Zero is only elapsed confirmation time. Reassessment still requires a
        genuinely new final source report through the existing control path.
        Stale observations cannot keep a visible confirmation countdown alive.
        """
        progress = {"reassessment_state": None, "reassessment_kind": None,
                    "reassessment_remaining_s": None, "reassessment_required_s": None,
                    "reassessment_valid_until": None,
                    "reassessment_reports": 0, "reassessment_source_current": False,
                    "reassessment_final_report_required": False, "start_remaining_s": None,
                    "start_valid_until": None, "start_required_s": math.ceil(float(self.settings["start_delay_s"])),
                    "start_cloud_active": False, "start_cloud_paused": False,
                    "start_cloud_kind": None, "start_cloud_remaining_s": None,
                    "start_cloud_valid_until": None, "start_accrued_s": None}
        if self._stable_since is not None and self._start_soft_since is not None:
            remaining = max(0.0, 300-(now-self._start_soft_since))
            progress.update(start_cloud_active=now-self._start_soft_since <= 300,
                start_cloud_kind=self._start_soft_kind, start_cloud_remaining_s=math.ceil(remaining),
                start_cloud_valid_until=self._wall_clock()+remaining,
                start_remaining_s=math.ceil(max(0.0, float(self.settings["start_delay_s"])-(now-self._stable_since))),
                start_accrued_s=max(0.0, now-self._stable_since))
        solar = self._solar_observation
        solar_stamp = finite(solar.get("stamp")) if isinstance(solar, dict) else None
        solar_watts = finite(solar.get("watts")) if isinstance(solar, dict) else None
        solar_current = (solar_stamp is not None and solar_watts is not None
                         and -5 <= self._wall_clock() - solar_stamp <= float(self.settings["stale_s"]))
        native = self._valid_native_observation(self._native_observation)
        reference = self._general_reference
        general_hold = (self.settings.get("profile") == "general" and self.completion_hold
                        and self.settings.get("profile_confirmed") is True)
        if general_hold:
            progress.update(reassessment_state="waiting_new_evidence",
                            reassessment_required_s=math.ceil(NEW_CONTEXT_CONFIRM_S),
                            reassessment_source_current=bool(solar_current or native is not None))
            if isinstance(reference, dict):
                ended = reference["ended_at"]
                solar_new = solar_current and solar_stamp > max(
                    ended, finite(reference.get("solar_stamp")) or ended)
                native_new = (native is not None and reference.get("native_rebase") is not True
                              and native["stamp"] > max(ended, finite(reference.get("native_stamp")) or ended,
                                                         finite(reference.get("native_after")) or ended))
                solar_reset = finite(reference.get("solar_reset_stamp"))
                native_reset = finite(reference.get("native_reset_stamp"))
                low_solar = solar_new and solar_watts <= float(self.settings["hysteresis_w"])
                checks = {
                    "fresh_residual_surplus": (self._hold_reason == "response_unknown" and solar_new
                        and self._residual_reassessment_threshold() is not None
                        and solar_watts >= self._residual_reassessment_threshold()
                        and isinstance(solar.get("source_signature"), str)),
                    "new_solar_period": (solar_new and solar_watts >= float(self.settings["threshold_w"])
                                         and solar_reset is not None and solar_stamp > solar_reset),
                    "fresh_native_context": (native_new and native["context"] in RELEVANT_NATIVE_CONTEXTS
                                             and (reference.get("profile_transition") is True
                                                  or reference.get("signature") is not None
                                                  and native["signature"] != reference["signature"]
                                                  or native_reset is not None and native["stamp"] > native_reset)),
                    "solar": low_solar,
                    "native": (not low_solar and native_new and native["context"] == "normal"),
                }
                for candidate, reset in ((self._general_candidate, False), (self._general_reset_candidate, True)):
                    if not isinstance(candidate, dict):
                        continue
                    kind = candidate.get("kind")
                    # A completed reset is already retained as evidence. The
                    # controller keeps its rolling report checks unchanged;
                    # their bookkeeping is not another user waiting period.
                    if reset and kind in {"solar", "native"} and finite(reference.get(kind + "_reset_stamp")) is not None:
                        continue
                    if (not checks.get(kind) or not reset and now < self._rest_until
                            and not (kind == "fresh_residual_surplus" and self._request_rest_proven())):
                        continue
                    observation = solar if kind in {"fresh_residual_surplus", "new_solar_period", "solar"} else native
                    signature = (solar["source_signature"] if kind == "fresh_residual_surplus"
                                 else "qualified_surplus" if kind == "new_solar_period" else "near_zero"
                                 if kind == "solar" else native["signature"])
                    if (candidate.get("signature") != signature
                            or observation["stamp"] < candidate["last_stamp"]):
                        continue
                    remaining = math.ceil(max(0.0, NEW_CONTEXT_CONFIRM_S - (now - candidate["first_seen"])))
                    display_kind = kind + "_reset" if reset else kind
                    progress.update(reassessment_state="confirming_" + display_kind,
                                    reassessment_kind=display_kind, reassessment_remaining_s=remaining,
                                    reassessment_reports=candidate["reports"], reassessment_source_current=True,
                                    reassessment_valid_until=observation["stamp"] + float(self.settings["stale_s"]),
                                    reassessment_final_report_required=remaining == 0)
                    break
        if (self.state == "waiting_surplus" and self._stable_since is not None and solar_current
                and not self._blocked_reasons and not self.completion_hold and not self.manual_hold
                and not self.fault and not self._closed and self.auto_enabled
                and getattr(self.runtime, "mode", "observe") == "solar" and not self.cooling_block_reason()):
            progress["start_remaining_s"] = math.ceil(max(
                0.0, float(self.settings["start_delay_s"]) - (now - self._stable_since)))
            progress["start_valid_until"] = solar_stamp + float(self.settings["stale_s"])
            if (self.settings.get("profile") == "general"
                    and self.settings.get("cooling_protection_confirmed") is not True and native is not None):
                progress["start_valid_until"] = min(progress["start_valid_until"],
                                                     native["stamp"] + float(self.settings["stale_s"]))
        return progress

    def overview(self):
        now = self._clock()
        wall = self._wall_clock()
        monitor = getattr(self.runtime, "panasonic", None)
        source = monitor.overview() if monitor is not None and callable(getattr(monitor, "overview", None)) else {}
        source = source if isinstance(source, dict) else {}
        entity_id = getattr(self.runtime, "entity_id", None)
        enabled_entity = entity_id("switch", "sg_boost_enabled") if callable(entity_id) else ""
        resume_entity = entity_id("button", "sg_boost_resume") if callable(entity_id) else ""
        session_remaining = (max(0.0, float(self.settings["max_session_s"]) - (now - self._session_started))
                             if self._session_started is not None else 0.0)
        minimum_current = (self._minimum_started is not None and self._confirmed_request_current()
                           and self._on_permission_current(self._generation))
        configured_minimum = finite(self.settings.get("min_session_s"))
        effective_minimum = self._effective_minimum_s()
        minimum_remaining = (math.ceil(max(0.0, effective_minimum - (now - self._minimum_started)))
                             if minimum_current else None)
        minimum_valid_until = (min(self._relay_observed_at + float(self.settings["stale_s"]),
                                   self._relay_valid_until,
                                   wall + max(0.0, self._lease_deadline - now), wall + session_remaining)
                               if minimum_current else None)
        cloud_current = (self._confirmed_request_current() and self._on_permission_current(self._generation)
                         and self._import_source_current())
        import_policy = self._import_policy_current()
        cloud_active = (cloud_current and self._import_since is not None
                        and self._import_policy == import_policy
                        and self._import_observation["watts"] > import_policy[0])
        cloud_remaining = (math.ceil(max(0.0, float(self.settings["stop_delay_s"]) - (now - self._import_since)))
                           if cloud_active else None)
        cloud_valid_until = (min(self._import_observation["stamp"] + float(self.settings["stale_s"]),
                                 self._relay_observed_at + float(self.settings["stale_s"]),
                                 self._relay_valid_until, wall + max(0.0, self._lease_deadline - now),
                                 wall + session_remaining) if cloud_current else None)
        return {**self._wait_progress(now), "configured": self.configured, "enabled": self.auto_enabled,
                "real_residual_surplus_w": (self._solar_observation["watts"]
                    if isinstance(self._solar_observation, dict)
                    and -5 <= wall-self._solar_observation["stamp"] <= float(self.settings["stale_s"]) else None),
                "residual_reassessment_threshold_w": self._residual_reassessment_threshold(),
                "residual_reassessment_available": bool(self.settings.get("profile") == "general"
                    and self.settings.get("profile_confirmed") is True and self.completion_hold
                    and self._hold_reason == "response_unknown" and self._general_reference is not None),
                "manual_control": self._manual_overview(),
                "observed_at": wall,
                "commissioning_confirmed": self.settings.get("commissioning_confirmed") is True,
                "watchdog_confirmed": self.settings.get("watchdog_confirmed") is True,
                "profile": self.settings.get("profile", "dhw_only"),
                "profile_confirmed": self.settings.get("profile_confirmed") is True,
                "cooling_protection_confirmed": self.settings.get("cooling_protection_confirmed") is True,
                "cooling_block_reason": self.cooling_block_reason(),
                "cooling_diagnostic": deepcopy(source.get("cooling_context_diagnostic", {})),
                "policy_hold_reason": self._hold_reason,
                "rearm_wait": self._rearm_wait(),
                "active_session_provenance": deepcopy(self._session_provenance)
                    if self._session_started is not None or self._restart_resume is not None else None,
                "owner": ("manual" if self.manual_hold else "solarpilot" if self.owned or self._possibly_owned
                          else "unknown" if self.relay_on is None else "none"),
                "lease_confirmed": bool(self.owned and self.relay_confirmed and self.relay_on is True
                    and self._lease_deadline is not None and now < self._lease_deadline),
                "state": self.state, "status": self.status, "reason": self.reason,
                "desired_on": self.desired_on, "relay_on": self.relay_on,
                "relay_confirmed": self.relay_confirmed, "panasonic_confirmed": self.panasonic_confirmed,
                "relay_observed_at": self._relay_observed_at if self.relay_confirmed else None,
                "relay_valid_until": self._relay_valid_until if self.relay_confirmed else None,
                "relay_stale_s": self.settings["stale_s"],
                "remaining_s": int(session_remaining), "rest_remaining_s": int(max(0.0, self._rest_until - now)),
                "lease_remaining_s": int(max(0.0, (self._lease_deadline or now) - now)),
                "min_session_s": configured_minimum, "effective_min_session_s": effective_minimum,
                "minimum_limited_by_max": configured_minimum is not None and effective_minimum < configured_minimum,
                "minimum_remaining_s": minimum_remaining, "minimum_active": self.minimum_hold_active,
                "minimum_import_hold": self._import_since is not None and self.minimum_hold_active,
                "minimum_valid_until": minimum_valid_until,
                "import_threshold_w": self.settings["import_threshold_w"], "stop_delay_s": self.settings["stop_delay_s"],
                "cloud_remaining_s": cloud_remaining, "cloud_active": bool(cloud_active),
                "cloud_import_hold": bool(cloud_active and (self.minimum_hold_active or self.cloud_hold_active)),
                "cloud_valid_until": cloud_valid_until,
                "manual_hold": self.manual_hold, "completion_hold": self.completion_hold,
                "fault": self.fault, "fault_code": self.fault_code, "action_required": self.action_required,
                "transport_evidence": deepcopy(self._transport_evidence),
                "dispatch_rejection": deepcopy(self._dispatch_rejection),
                "blocked_reasons": list(self._blocked_reasons), "last_session": deepcopy(self._last_session),
                "automatic_rearm_available": ((self._general_reference is not None) if self.settings.get("profile") == "general"
                    else self._need_reference is not None and not self._tank_source_changed),
                "last_rearm": deepcopy(self._last_rearm),
                "start_threshold_w": self.settings["threshold_w"], "estimated_power_w": self.settings["expected_power_w"],
                "switch_entity": self.settings.get("entity_id", ""), "enabled_entity": enabled_entity,
                "resume_entity": resume_entity, "power_w": source.get("power_w"),
                "power_kind": source.get("power_kind", "unknown"), "power_scope": source.get("power_scope", self.settings["power_scope"]),
                "temperature_c": source.get("temperature_c"), "target_c": source.get("target_c"),
                "uptake_diagnostic": "SG-contact actief; extra warmteopname nog niet aangetoond" if self._low_uptake_noted else ""}
