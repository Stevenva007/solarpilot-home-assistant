"""One leased SG contact; Panasonic remains the sole heat-pump controller.

The manager owns no temperature target, climate command, heater permission or
cloud retry. A local Shelly deadline is required for each ON and renewal. Its
journal permits release of an old request, never replay of that request.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import inspect
import time

from homeassistant.exceptions import HomeAssistantError

from .sg_config import actuator_conflicts, finite, normalize_config, validate_config

# Anti-repeat evidence thresholds, not Panasonic targets or comfort settings.
NEW_STORAGE_DROP_C = 2.0
NEW_STORAGE_CONFIRM_S = 300.0
NEW_CONTEXT_CONFIRM_S = 300.0
RELEVANT_NATIVE_CONTEXTS = frozenset({"space_heating", "space_cooling", "tapwater_heating"})


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
        self._off_attempted = False
        self._possibly_owned = False
        self.owned = False
        self.desired_on = False
        self.relay_on = None
        self.relay_confirmed = False
        self.panasonic_confirmed = None
        self.manual_hold = False
        self.completion_hold = False
        self.fault = ""
        self.fault_code = ""
        self.state = "normal"
        self.status = "Panasonic regelt zelfstandig"
        self.reason = "Automatische zonneboost staat uit"
        self._stable_since = None
        self._import_since = None
        self._session_started = None
        self._session_finishing = False
        self._rest_until = 0.0
        self._rest_until_wall = None
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
        if updated != self.settings:
            self._generation += 1
            self._stable_since = None
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
                "owned": bool(self.owned or self._possibly_owned),
                "lease_expiry": self._lease_expiry,
                "manual_hold": self.manual_hold, "completion_hold": self.completion_hold,
                "session_finishing": self._session_finishing,
                "rest_until_wall": self._rest_until_wall,
                "fault_code": self.fault_code, "last_session": deepcopy(self._last_session),
                "commissioned_fingerprint": deepcopy(self._commissioned_fingerprint),
                "need_reference": deepcopy(self._need_reference),
                "tank_source_changed": self._tank_source_changed,
                "last_rearm": deepcopy(self._last_rearm),
                "profile": self.settings.get("profile", "dhw_only"),
                "hold_reason": self._hold_reason,
                "general_reference": deepcopy(self._general_reference),
                "session_reference": deepcopy(self._session_reference),
                "hold_provenance": deepcopy(self._hold_provenance)}

    def restore(self, stored):
        """A stored ON can authorize reconciliation OFF, never a new ON."""
        if not isinstance(stored, dict) or stored.get("schema") != 1:
            return
        if stored.get("relay_entity") != self.settings.get("entity_id"):
            return
        self.manual_hold = stored.get("manual_hold") is True
        self.completion_hold = stored.get("completion_hold") is True or stored.get("session_finishing") is True
        self._restart_release = stored.get("owned") is True and not self.manual_hold
        self._restored_expiry = finite(stored.get("lease_expiry"))
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
        last = stored.get("last_session")
        self._last_session = deepcopy(last) if isinstance(last, dict) else None
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
        if (stored.get("owned") is True and not self.completion_hold
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

    def _transport(self):
        if self._adapter is None:
            from .sg_transport import ShellyLeaseAdapter
            self._adapter = ShellyLeaseAdapter(self.runtime.hass, self.settings["entity_id"])
        return self._adapter

    def _fault(self, code, reason):
        self.fault_code, self.fault = code, reason
        self.state, self.status, self.reason = "blocked", "Zonneboost geblokkeerd", reason
        self._stable_since = None

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

    def _begin_rest(self):
        now = self._clock()
        seconds = float(self.settings["rest_s"])
        deadline = now + seconds
        if deadline > self._rest_until:
            self._rest_until = deadline
            self._rest_until_wall = self._wall_clock() + seconds

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
            expiry = start + duration
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

    async def _read(self, *, force=False):
        now = self._clock()
        if not force and now < self._next_read:
            return None
        try:
            raw = self._status(await asyncio.wait_for(self._transport().get_status(),
                                                    float(self.settings["ack_timeout_s"])))
        except Exception:
            self.relay_on = None
            self.relay_confirmed = False
            self._read_failures += 1
            self._next_read = now + min(300.0, 15.0 * 2 ** min(self._read_failures, 4))
            if self.fault_code not in {"on_failed", "lease_invalid", "lease_failed", "firmware_changed"}:
                self._fault("unavailable_read", "SG-uitgang niet bereikbaar; status onbekend, de lokale toestemming wordt niet vernieuwd")
            return None
        self._read_failures = 0
        self._next_read = now
        if self.fault_code == "unavailable_read":
            self.fault_code = self.fault = ""
        self._fingerprint_check(raw)
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
            if self._restart_release:
                # A different live timer can be an intervening manual request.
                expiry = self._expiry(raw)
                different = (self._restored_expiry is not None and expiry is not None
                             and abs(expiry - self._restored_expiry) > 2)
                if raw["output"] and different:
                    self._restart_release = False
                    self.manual_hold = True
                    self._set_state("blocked", "SG-uitgang is handmatig gewijzigd; hervat de automatisering wanneer gewenst")
                elif raw["output"]:
                    self._possibly_owned = True
                    self._restart_release = False
                    await self._release("Eerdere SG-aanvraag na herstart vrijgegeven", rest=True)
                else:
                    self._restart_release = False
                    self._begin_rest()
            elif raw["output"]:
                self.manual_hold = True
                self._set_state("blocked", "SG-contact staat buiten SolarPilot aan; handmatige stand blijft behouden")
            await self._save()

    def _on_permission_current(self, generation):
        return (generation == self._generation and not self._closed and self.auto_enabled
                and getattr(self.runtime, "mode", "observe") == "solar"
                and self.settings.get("commissioning_confirmed") is True
                and self.settings.get("watchdog_confirmed") is True
                and (self.settings.get("profile", "dhw_only") != "general"
                     or self.settings.get("profile_confirmed") is True)
                and not self.cooling_block_reason(live=True)
                and not self._profile_change_release
                and not self.manual_hold and not self.completion_hold and not self.fault)

    def _on_authorized(self, generation, renewal):
        """Recheck authority after async work and at the transport boundary."""
        if not self._on_permission_current(generation):
            return False
        gate = getattr(self.runtime, "sg_dispatch_allowed", None)
        if not callable(gate):
            # Small isolated tests have no runtime. Production SolarRuntime
            # provides a final live electrical/priority gate.
            return self._injected_adapter
        try:
            approved = gate(renewal=renewal)
        except Exception:
            return False
        if isinstance(approved, tuple):
            approved = approved[0] if approved else False
        return approved is True

    async def _issue_on(self, *, renewal=False):
        # Renewal preflight can consume the entire bounded ACK interval. Leave
        # that time within the session limit so a crash never extends SG beyond
        # the admitted maximum, even with a short configured session.
        lease_s = min(float(self.settings["lease_s"]), float(self.settings["max_session_s"]))
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

        def before_on():
            nonlocal issued_at
            if not self._on_authorized(generation, renewal):
                return False
            issued_at = self._clock()
            if not renewal:
                self._command_clock()
            return True

        # Persist ownership intent before a possible successful physical write.
        try:
            await self._save()
            if not self._on_authorized(generation, renewal):
                self._possibly_owned = False
                self.desired_on = False
                if self.owned:
                    await self._release("SG-voorwaarden gewijzigd; eigen aanvraag vrijgegeven", preserve_fault=bool(self.fault))
                else:
                    self._stable_since = None
                    self._set_state("blocked", "SG-voorwaarden gewijzigd; verse zonnebeoordeling volgt")
                    await self._save()
                return False
            adapter = self._transport()
            supports_callback = hasattr(adapter, "before_on")
            callback = before_on
            adapter.before_on = callback
            if not supports_callback:
                # Injected deterministic doubles can omit the callback protocol.
                # The production adapter always invokes it after async preflight.
                if not before_on():
                    self._possibly_owned = False
                    self.desired_on = False
                    return False
            write_started = True
            raw = await asyncio.wait_for(adapter.set_on(lease_s=lease_s),
                                         float(self.settings["ack_timeout_s"]))
            self._status(raw)
            self._fingerprint_check(raw)
            if self.fault_code == "firmware_changed":
                raise ValueError("commissioning_changed")
            self._timer_proof(raw, renewal=renewal, lease_s=lease_s)
        except Exception as err:
            # No replay or retry. A missing readback is not a confirmed OFF.
            attempted = write_started and getattr(err, "command_attempted", True)
            if not attempted:
                self._possibly_owned = False
            self.desired_on = False
            policy_rejected = getattr(err, "code", "") == "dispatch_changed"
            if policy_rejected:
                # This was a new live policy decision before Switch.Set, rather
                # than an actuator fault or an unconfirmed physical operation.
                self._stable_since = None
                reason = "SG-voorwaarden gewijzigd; verse zonnebeoordeling volgt"
                if self.owned:
                    await self._release(reason, preserve_fault=bool(self.fault))
                else:
                    self._set_state("blocked", reason)
            else:
                if attempted:
                    self.relay_on = None
                    self.relay_confirmed = False
                if self.fault_code != "firmware_changed":
                    self._fault("on_failed", "SG-aanvraag of lokale aflooptimer niet bevestigd; controle nodig voordat opnieuw wordt gestart")
                if self.owned or self._possibly_owned:
                    await self._release(self.fault, rest=True, preserve_fault=True)
            await self._save()
            return False
        finally:
            self._in_flight = False
            if adapter is not None and getattr(adapter, "before_on", None) is callback:
                if supports_callback:
                    adapter.before_on = None
                else:
                    del adapter.before_on
        if not self._on_permission_current(generation):
            self.desired_on = False
            await self._release("Verouderde SG-aanvraag vrijgegeven", rest=True)
            return False
        self.owned = True
        self._possibly_owned = False
        self._last_renewed = self._clock()
        if not renewal:
            self._need_reference = self._need_candidate = None
            self._general_reference = self._general_candidate = self._general_reset_candidate = None
            self._hold_reason = ""
            self._low_uptake_noted = False
            self._low_uptake_since = self._low_uptake_stamp = None
            native = self._valid_native_observation(self._native_observation)
            self._session_reference = ({"schema": 1, "signature": native["signature"],
                "native_stamp": native["stamp"], "solar_stamp": (self._solar_observation or {}).get("stamp")}
                if native is not None else None)
            self._tank_source_changed = False
            self._session_started = issued_at
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

    async def _release(self, reason, *, rest=True, preserve_fault=False, policy_hold=True):
        self.desired_on = False
        self._stable_since = self._import_since = None
        had_authority = self.owned or self._possibly_owned
        if (policy_hold and self.settings.get("profile") == "general"
                and self._session_started is not None and not self.completion_hold):
            self.completion_hold = True
            self._hold_reason = "response_unknown"
            self._capture_need_reference()
        if had_authority and not self._off_attempted:
            self._off_attempted = True
            self._in_flight = True
            self._command_clock()
            try:
                raw = self._status(await asyncio.wait_for(self._transport().set_off(),
                                                        float(self.settings["ack_timeout_s"])))
                if raw["output"] is not False:
                    raise ValueError("off_not_confirmed")
                self.owned = self._possibly_owned = False
                self._lease_expiry = self._lease_deadline = None
                if self.fault_code == "off_failed":
                    self.fault_code = self.fault = ""
            except Exception:
                self.relay_on = None
                self.relay_confirmed = False
                if not preserve_fault:
                    self._fault("off_failed", "Vrijgave van het SG-contact nog niet bevestigd; de lokale toestemming wordt niet vernieuwd")
            finally:
                self._in_flight = False
        if rest:
            self._begin_rest()
        if self._session_started is not None:
            self._last_session = {"ended_at": self._wall_clock(), "reason": reason,
                                  "duration_s": max(0, self._clock() - self._session_started)}
            self._note("SG-aanvraag beëindigd: " + reason + self._observation_summary())
        self._session_started = None
        self._session_finishing = False
        self._last_renewed = None
        if not self.fault:
            self._set_state("rest" if rest else "normal", reason)
        await self._save()

    def _observe_contact(self, raw):
        """Distinguish our expiry/late echo from an external contact change."""
        if raw is None:
            return
        now = self._clock()
        ours = self.owned or self._possibly_owned
        if ours and raw["output"] is False:
            expired = self._lease_deadline is not None and now >= self._lease_deadline - 1
            limit_reached = (self._session_started is not None and
                now-self._session_started >= float(self.settings["max_session_s"]))
            if (expired and (self._session_finishing or limit_reached)
                    or self.settings.get("profile") == "general" and not self.completion_hold):
                self.completion_hold = True
                self._hold_reason = "session_limit" if self._session_finishing or limit_reached else "response_unknown"
                self._capture_need_reference()
            self._session_finishing = False
            releasing = self._off_attempted or not self.desired_on
            self.owned = self._possibly_owned = False
            self.desired_on = False
            self._lease_expiry = self._lease_deadline = None
            self._session_started = self._last_renewed = None
            self._begin_rest()
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
            if expiry is not None and self._lease_expiry is not None and expiry > self._lease_expiry + 2:
                self.owned = self._possibly_owned = self.desired_on = False
                self.manual_hold = True
                self._set_state("blocked", "SG-contact buiten SolarPilot gewijzigd; handmatige stand blijft behouden")
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
        return "Extra SG-koeling niet vrijgegeven: condens-/dauwpuntbeveiliging niet bevestigd of actieve context onbekend"

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

    def _general_reassessment(self):
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
        if now < self._rest_until:
            self._general_candidate = None
            return False
        kind = None
        if (native_new and native["context"] in RELEVANT_NATIVE_CONTEXTS
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
        if kind is None:
            self._general_candidate = None
            return False
        self._general_candidate, confirmed = self._confirmed_reports(
            self._general_candidate, kind, signature, stamp, now)
        if not confirmed:
            return False
        self._last_rearm = {"kind": kind, "at": self._wall_clock()}
        self.completion_hold = False
        self._hold_reason = ""
        self._general_reference = self._general_candidate = self._general_reset_candidate = None
        self._need_reference = self._need_candidate = None
        self._tank_source_changed = False
        self._stable_since = None
        self._note("Nieuwe betrouwbare SG-aanleiding vastgesteld; verse zonne- en veiligheidsbeoordeling volgt")
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
        self._need_reference = self._need_candidate = None
        self._stable_since = None
        self._note("Tank na vorige SG-sessie aantoonbaar afgekoeld; nieuw zonneoverschot wordt beoordeeld")
        return True

    def _completion_reason(self):
        if self.settings.get("profile") == "general":
            prefix = {"native_completed": "Native voltooiing bevestigd",
                      "no_uptake": "Geen extra opname bevestigd",
                      "response_unknown": "Vorige SG-aanvraag beëindigd; extra opname niet bewezen",
                      "profile_changed": "Algemene SG-keuze bevestigd"}.get(
                          self._hold_reason, "Begrensde sessieduur bereikt; SG-effect onbekend")
            return prefix + "; wacht op een nieuwe zonneperiode of betrouwbare gewijzigde native context"
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

    def _gates(self, *, data_fresh, phase_allowed, priority_allowed, hard_limit):
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
            reasons.append("Elektrische grens of fasebewaking laat geen extra SG-aanvraag toe")
        if priority_allowed is not True:
            reasons.append("Hoger geplaatste of beschermde verbruikers krijgen voorrang")
        if self.manual_hold:
            reasons.append("Handmatige SG-stand blijft behouden; hervat de automatisering wanneer gewenst")
        if self.completion_hold:
            reasons.append(self._completion_reason())
        if self.fault:
            reasons.append(self.fault)
        return reasons

    async def tick(self, *, surplus_w, data_fresh, phase_allowed, priority_allowed=True,
                   grid_import_w=0, physical_evidence=None, tank_observation=None,
                   native_observation=None, solar_stamp=None, hard_limit=False, **_context):
        if not self._started:
            await self.start()
        async with self._lock:
            self.sent_this_tick = self.renewed_this_tick = False
            now = self._clock()
            self._tank_observation = self._valid_tank_observation(tank_observation)
            self._native_observation = (dict(native_observation) if isinstance(native_observation, dict)
                                        else self._read_native())
            surplus, imported, stamp = finite(surplus_w), finite(grid_import_w), finite(solar_stamp)
            data_fresh = data_fresh is True and surplus is not None and imported is not None and surplus >= 0 and imported >= 0
            self._solar_observation = ({"watts": surplus, "stamp": stamp}
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
            previous_reference = deepcopy(self._general_reference)
            rearmed = self._general_reassessment()
            if rearmed or previous_reference != self._general_reference:
                await self._save()
            raw = await self._read() if self.configured and not self._closed else None
            observed = (self.owned, self._possibly_owned, self.manual_hold, self.completion_hold,
                        self._session_started, self.fault_code)
            self._observe_contact(raw)
            if observed != (self.owned, self._possibly_owned, self.manual_hold, self.completion_hold,
                            self._session_started, self.fault_code):
                await self._save()
            if self._profile_change_release:
                self._profile_change_release = False
                if self.owned or self._possibly_owned:
                    await self._release("SG-toepassingsbereik gewijzigd; vorige aanvraag veilig vrijgegeven")
                self._stable_since = None
                await self._save()
            gates = self._gates(data_fresh=data_fresh, phase_allowed=phase_allowed,
                                 priority_allowed=priority_allowed, hard_limit=hard_limit)
            self._blocked_reasons = gates
            if gates:
                self._stable_since = None
                if self.owned or self._possibly_owned:
                    self._generation += 1
                    await self._release(gates[0], preserve_fault=bool(self.fault))
                self._set_state("blocked" if self.auto_enabled or self.fault or self.manual_hold else "normal", gates[0])
                return self.sent_this_tick
            if self._restart_release or raw is None or not self.relay_confirmed:
                self._stable_since = None
                self._set_state("blocked", "Wachten op betrouwbare SG-uitgangstatus")
                return self.sent_this_tick
            if self.owned and self.desired_on:
                elapsed = now - self._session_started if self._session_started is not None else 0
                complete = physical.get("verified") is True and (physical.get("completed") is True or physical.get("no_uptake") is True)
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
                if imported > float(self.settings["hysteresis_w"]):
                    if self._import_since is None:
                        self._import_since = now
                    if now - self._import_since >= float(self.settings["stop_delay_s"]):
                        self._generation += 1
                        await self._release("Aanhoudende netafname; extra SG-aanvraag vrijgegeven")
                        return self.sent_this_tick
                    self._set_state("boost_requested", "Tijdelijke netafname; SG stopt als deze aanhoudt")
                else:
                    self._import_since = None
                    self._set_state("boost_requested", self._active_reason())
                if self._last_renewed is not None and now - self._last_renewed >= float(self.settings["renew_s"]):
                    # While import is waiting to stop, the current local lease
                    # remains sufficient; do not extend unwanted consumption.
                    if self._import_since is None:
                        await self._issue_on(renewal=True)
                return self.sent_this_tick
            if now < self._rest_until:
                self._stable_since = None
                self._set_state("rest", "SG-contact vrijgegeven; rusttijd voorkomt herhaald schakelen")
                return self.sent_this_tick
            if surplus < float(self.settings["threshold_w"]):
                self._stable_since = None
                self._set_state("waiting_surplus", f"Wachten op minstens {self.settings['threshold_w']:g} W bruikbaar zonneoverschot")
                return self.sent_this_tick
            if self._stable_since is None:
                self._stable_since = now
            remaining = max(0.0, float(self.settings["start_delay_s"]) - (now - self._stable_since))
            if remaining > 0:
                self._set_state("waiting_surplus", f"Voldoende zonneoverschot; stabiliteitscontrole nog {int(remaining + .999)} s")
                return self.sent_this_tick
            await self._issue_on()
            return self.sent_this_tick

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

    def overview(self):
        now = self._clock()
        monitor = getattr(self.runtime, "panasonic", None)
        source = monitor.overview() if monitor is not None and callable(getattr(monitor, "overview", None)) else {}
        source = source if isinstance(source, dict) else {}
        entity_id = getattr(self.runtime, "entity_id", None)
        enabled_entity = entity_id("switch", "sg_boost_enabled") if callable(entity_id) else ""
        resume_entity = entity_id("button", "sg_boost_resume") if callable(entity_id) else ""
        session_remaining = (max(0.0, float(self.settings["max_session_s"]) - (now - self._session_started))
                             if self._session_started is not None else 0.0)
        return {"configured": self.configured, "enabled": self.auto_enabled,
                "commissioning_confirmed": self.settings.get("commissioning_confirmed") is True,
                "watchdog_confirmed": self.settings.get("watchdog_confirmed") is True,
                "profile": self.settings.get("profile", "dhw_only"),
                "profile_confirmed": self.settings.get("profile_confirmed") is True,
                "cooling_protection_confirmed": self.settings.get("cooling_protection_confirmed") is True,
                "cooling_block_reason": self.cooling_block_reason(),
                "policy_hold_reason": self._hold_reason,
                "owner": ("manual" if self.manual_hold else "solarpilot" if self.owned or self._possibly_owned
                          else "unknown" if self.relay_on is None else "none"),
                "lease_confirmed": bool(self.owned and self.relay_confirmed and self.relay_on is True
                    and self._lease_deadline is not None and now < self._lease_deadline),
                "state": self.state, "status": self.status, "reason": self.reason,
                "desired_on": self.desired_on, "relay_on": self.relay_on,
                "relay_confirmed": self.relay_confirmed, "panasonic_confirmed": self.panasonic_confirmed,
                "remaining_s": int(session_remaining), "rest_remaining_s": int(max(0.0, self._rest_until - now)),
                "lease_remaining_s": int(max(0.0, (self._lease_deadline or now) - now)),
                "manual_hold": self.manual_hold, "completion_hold": self.completion_hold,
                "fault": self.fault, "fault_code": self.fault_code, "action_required": self.action_required,
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
