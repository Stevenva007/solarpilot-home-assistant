"""Setpoint-only boiler controller, serialized by SolarRuntime's existing lock.

No on/off calls, no powerful/boost mode, no Wallbox calls. Independent factory
thermostat, hygiene functions and hot-water safety remain prerequisites.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
import time
from zoneinfo import ZoneInfo
from homeassistant.exceptions import HomeAssistantError
from .dhw import (DHW_DEFAULTS, DHW_NUMBERS, DHWPolicy, DHWReading,
                  cooling_state, finite, validate_settings, effective_base_target,
                  hygiene_schedule_active, night_active, normalized_settings,
                  state_values)
from .wallbox import protected_entity, state_set
from .dhw_schedule import DHWComfortSchedule


# Aquarea publishes a command-side target observation before its delayed refresh;
# panasonic_cc already used the same conservative delayed-ACK contract. An early
# HA state must not prove the command. Scope is limited to exact registry/config-
# entry domains; other water-heater integrations keep their existing contract.
PANASONIC_ACK_POLL_MIN_S = 10.0
PANASONIC_ADAPTER_DOMAINS = frozenset({"aquarea", "panasonic_cc"})


class DHWManager:
    def __init__(self, runtime):
        self.runtime = runtime
        self.config = normalized_settings(runtime.entry.options.get("dhw", {}))
        self.settings = dict(self.config)
        self.policy = DHWPolicy(self.settings)
        self.auto_enabled = bool(self.config["enabled"])
        self.tunables = {}
        self.pending = None
        self.owned_target = None
        self.needs_review = False
        self.restart_recovery = None
        self.manual_hold = False
        self.fault = ""
        self.status = "Niet geconfigureerd"
        self.reading = DHWReading()
        self.last_command_wall = 0.0
        self.optional_raise_remaining_s = 0
        self._release = False
        self._last_low = False
        self.last_success = None
        self.comfort = DHWComfortSchedule()
        self._comfort_forecast_stamp = None
        self._comfort_slots = []
        self._comfort_forecast_available = False
        self._cooling_wall = None
        self._prediction_check_wall = None
        self._prediction_cached = (False, "")
        self._prediction_forecast_key = None
        self._last_model_save_wall = 0.0

    @property
    def configured(self):
        return bool(self.config.get("target_entity"))

    @property
    def busy(self):
        # A deferred restart still carries an unresolved historical target or
        # command. Safe removal must wait for its read-only reconciliation,
        # even though unrelated consumers need not be globally blocked.
        return self.pending is not None or self.owned_target is not None or bool(self.restart_recovery)

    @property
    def blocks_increase(self):
        return self.pending is not None or self.needs_review or bool(self.fault)

    def snapshot(self):
        return {"config_revision": self.config["config_revision"],
                "target_entity": self.config["target_entity"],
                "enabled": self.auto_enabled, "tunables": self.tunables,
                "pending": self.pending, "owned_target": self.owned_target,
                "needs_review": self.needs_review, "manual_hold": self.manual_hold,
                "restart_recovery": self.restart_recovery,
                "fault": self.fault, "last_success": self.last_success,
                "comfort": self.comfort.snapshot(), "cooling_wall": self._cooling_wall,
                "last_command_wall": self.last_command_wall}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        same_binding = data.get("target_entity") == self.config["target_entity"]
        same_revision = same_binding and data.get("config_revision") == self.config["config_revision"]
        if same_revision:
            trial = {k: v for k, v in data.get("tunables", {}).items() if k in DHW_NUMBERS}
            merged = {**self.config, **trial}
            if not validate_settings(merged):
                self.tunables, self.settings = trial, merged
            self.auto_enabled = bool(data.get("enabled", self.auto_enabled))
        self.policy = DHWPolicy(self.settings)
        self.last_success = data.get("last_success")
        if same_binding:
            command_wall = finite(data.get("last_command_wall"))
            if command_wall is not None and 0 <= time.time()-command_wall:
                self.last_command_wall = command_wall
            self.comfort.restore(data.get("comfort", {}))
            saved = finite(data.get("cooling_wall"))
            if saved is not None and 0 <= time.time()-saved <= self.settings["cooling_clear_s"]:
                self._cooling_wall = saved
                self.policy.last_cooling = time.monotonic()-(time.time()-saved)
        self.manual_hold = bool(data.get("manual_hold")) if same_binding else False
        self.fault = str(data.get("fault", ""))
        restart = data.get("restart_recovery")
        has_restart = bool(data.get("needs_review") or data.get("pending")
                           or data.get("owned_target") is not None or restart)
        self.needs_review = has_restart
        self.restart_recovery = None
        if has_restart and same_binding and not self.fault and not self.manual_hold:
            # A normal restart is not a manual override. Keep only a read-only
            # reconciliation journal; never resurrect a pre-restart monotonic
            # deadline or replay a temperature command. Older releases dropped
            # ownership while retaining needs_review: those clean same-binding
            # states can also recover against the actual current target.
            saved = restart if isinstance(restart, dict) else data
            owned = finite(saved.get("owned_target"))
            pending = saved.get("pending")
            valid = ((restart is None or isinstance(restart, dict) and restart.get("schema") == 1)
                     and (saved.get("owned_target") is None or owned is not None))
            if pending is not None:
                valid = valid and isinstance(pending, dict)
                if valid:
                    target = finite(pending.get("target"))
                    issued_wall = finite(pending.get("issued_wall"))
                    valid = (target is not None and issued_wall is not None
                             and 0 < issued_wall <= time.time() + 5
                             and isinstance(pending.get("release", False), bool))
                    if valid:
                        pending = {"target": target, "issued_wall": issued_wall,
                                   "release": bool(pending.get("release")),
                                   "ack_poll_min_s": max(0.0, finite(pending.get("ack_poll_min_s")) or 0.0)}
            if valid:
                self.restart_recovery = {
                    "schema": 1, "owned_target": owned, "pending": pending,
                    "started_wall": time.time(),
                    "reason": "Boilerherstart: wacht op betrouwbare actuele temperatuur- en doelterugmelding",
                }
                self.needs_review = False
        # Do not replay a target or a pending physical call after a restart.
        self.owned_target = None
        self.pending = None
        if self.needs_review:
            self.status = "Boilercontrole na herstart vereist; huidige instelling blijft onaangeroerd"
        elif self.restart_recovery:
            self.status = self.restart_recovery["reason"]

    async def reconcile_restart(self, local_now=None):
        """Resolve only an ordinary restart, using current reports without writes.

        Real faults, explicit holds and changed bindings require their existing
        review. Missing sources merely defer this module; its journal does not
        turn unrelated consumers into a global restart lock.
        """
        recovery = self.restart_recovery
        if not recovery or self.needs_review or self.fault or self.manual_hold:
            return False
        if local_now is None:
            zone = getattr(getattr(self.runtime.hass, "config", None), "time_zone", "Europe/Brussels")
            local_now = datetime.now(ZoneInfo(zone))

        def wait(reason):
            recovery["reason"] = reason
            self.status = reason
            return False

        target_obj = self._state(self.config.get("target_entity"))
        temperature_id = self.config.get("temperature_entity") or self.config.get("target_entity")
        temperature_obj = self._state(temperature_id)
        target, _ = self._target()
        if (target_obj is None or temperature_obj is None
                or target_obj.attributes.get("restored") or temperature_obj.attributes.get("restored")
                or target is None or self._temperature() is None):
            return wait("Boilerherstart: wacht op betrouwbare actuele temperatuur- en doelterugmelding")
        guard_ids = [self.config.get("hygiene_entity"), self.config.get("manual_entity"),
                     *self.config.get("manual_entities", [])]
        for entity_id in filter(None, guard_ids):
            obj = self._state(entity_id, freshness=False)
            if obj is None or obj.attributes.get("restored"):
                return wait("Boilerherstart: wacht op betrouwbare hygiëne- en handmatige status")
        if error := self.check_target(target):
            return wait("Boilerherstart: " + error)

        if protected := self._protected(target_obj, local_now):
            # Factory sterilisation, Powerful and native OFF retain control.
            # Forget only SolarPilot's historical ownership, without lowering
            # the current factory/manual target or switching anything on.
            self.restart_recovery = None
            self.owned_target = None
            self.policy.reset_stability()
            self.status = protected
            await self._save()
            self.runtime.note("Boilerherstart automatisch gecontroleerd; fabrikant-/handmatige regeling blijft vrij zonder opdracht.")
            return True

        pending = recovery.get("pending")
        if pending:
            stamp = getattr(target_obj, "last_reported", target_obj.last_updated).timestamp()
            delay = max(self._ack_poll_min_s(), pending.get("ack_poll_min_s", 0.0))
            # The command-side echo from before the restart cannot become an
            # ACK by waiting. Require a genuinely later HA report in this run.
            if stamp <= recovery["started_wall"] or stamp < pending["issued_wall"] + delay:
                return wait("Boilerherstart: wacht op latere doelrapportage; oude opdracht wordt niet herhaald")
            expected = pending["target"]
        else:
            expected = recovery.get("owned_target")
        self.restart_recovery = None
        self.policy.reset_stability()
        if expected is not None and abs(target - expected) > .05:
            self.manual_hold = True
            self.owned_target = None
            self.status = "Boilerdoel gewijzigd tijdens herstart: bestaande bediening krijgt voorrang; geen opdracht herhaald"
            self.runtime.note(self.status)
        else:
            self.owned_target = (None if pending and pending.get("release")
                                 else target if expected is not None else None)
            if pending:
                self.last_success = {
                    "target_c": target, "time": datetime.now().astimezone().isoformat(),
                    "confirmation": "restart_delayed_ha_state" if delay else "restart_ha_state",
                }
            self.status = "Boilerherstart automatisch gecontroleerd; actuele toestand behouden zonder doelopdracht"
            self.runtime.note(self.status)
        await self._save()
        return True

    def _persist_canonical(self):
        """Persist the effective DHW state as the single config-entry truth."""
        options = dict(self.runtime.entry.options)
        canonical = {**self.config, **self.settings, "enabled": bool(self.auto_enabled)}
        canonical["config_revision"] = str(canonical.get("config_revision") or self.config.get("config_revision") or "")
        options["dhw"] = canonical
        updater = getattr(getattr(self.runtime.hass, "config_entries", None), "async_update_entry", None)
        if updater is not None:
            updater(self.runtime.entry, options=options)
        else:
            self.runtime.entry.options = options
        self.config = normalized_settings(canonical)
        self.settings = dict(self.config)
        self.policy.settings = dict(self.settings)
        self.tunables = {}

    async def migrate_beta36(self, stored):
        """Fold beta.35 runtime tunables/enabled state into config-entry options."""
        stored = stored if isinstance(stored, dict) else {}
        before = dict(self.runtime.entry.options.get("dhw", {}) or {})
        canonical = {**normalized_settings(before), **self.settings, "enabled": bool(self.auto_enabled)}
        legacy_confirmed_profile = (
            bool(stored.get("enabled")) and self.configured
            and abs(float(canonical.get("normal_c", 0)) - 50.0) < 0.01
            and abs(float(canonical.get("minimum_c", 0)) - 46.0) < 0.01
            and abs(float(canonical.get("tank_differential_c", 0)) + 5.0) < 0.01
            and abs(float(canonical.get("solar_c", 0)) - 50.0) < 0.01
            and abs(float(canonical.get("surplus_c", 0)) - 60.0) < 0.01
            and abs(float(canonical.get("cooling_cap_c", 0)) - 50.0) < 0.01
            and abs(float(canonical.get("hygiene_target_c", 0)) - 62.0) < 0.01
        )
        if not canonical.get("safety_confirmed") and legacy_confirmed_profile:
            canonical["safety_confirmed"] = True
            canonical["safety_confirmation_source"] = "beta35_enabled_50_46_profile"
        changed = any(before.get(k) != v for k, v in canonical.items())
        if changed:
            self.settings = dict(canonical)
            self.config = dict(canonical)
            self.auto_enabled = bool(canonical["enabled"])
            self._persist_canonical()
            self.runtime.note(
                "Beta.36-migratie: effectieve boilerinstellingen als enige configbron vastgelegd "
                f"({self.settings['normal_c']:g}/{self.settings['minimum_c']:g} °C)."
            )
        return changed

    def _state(self, entity_id, freshness=True):
        obj = self.runtime.hass.states.get(entity_id) if entity_id else None
        if (obj is None or obj.state in ("unknown", "unavailable", "")
                or obj.attributes.get("restored")):
            return None
        if freshness:
            stamp = getattr(obj, "last_reported", obj.last_updated).timestamp()
            if not -5 <= time.time() - stamp <= self.settings["stale_s"]:
                return None
        return obj

    def _unit(self, obj):
        unit = obj.attributes.get("unit_of_measurement") or obj.attributes.get("temperature_unit")
        if unit is None:
            units = getattr(getattr(self.runtime.hass, "config", None), "units", None)
            unit = getattr(units, "temperature_unit", None)
        return unit

    def _target(self):
        entity_id = self.config["target_entity"]
        # Native climate/boiler reports carry the operating mode as well as the
        # target. An old cached mode cannot establish that factory protection
        # has ended. Numeric helpers may legitimately remain unchanged.
        obj = self._state(entity_id, freshness=entity_id.startswith(("climate.", "water_heater.")))
        if obj is None or self._unit(obj) != "°C":
            return None, obj
        domain = entity_id.split(".")[0]
        raw = obj.state if domain in ("number", "input_number") else obj.attributes.get("temperature")
        return finite(raw), obj

    def _ack_poll_min_s(self):
        """Return an adapter-specific delay before an HA state may ACK a write."""
        entity_id = self.config.get("target_entity", "")
        if not isinstance(entity_id, str) or not entity_id.startswith("water_heater."):
            return 0.0
        return (PANASONIC_ACK_POLL_MIN_S
                if self._is_panasonic_adapter(entity_id) else 0.0)

    def _temperature(self):
        entity_id = self.config.get("temperature_entity") or self.config["target_entity"]
        obj = self._state(entity_id)
        if obj is None or self._unit(obj) != "°C":
            return None
        value = obj.attributes.get("current_temperature") if entity_id.startswith(("climate.", "water_heater.")) else obj.state
        number = finite(value)
        return number if number is not None and 0 <= number <= 100 else None

    def _protected(self, obj, local_now=None):
        # Explicit manufacturer hygiene state, when available.
        if self.config.get("hygiene_entity"):
            state = self._state(self.config["hygiene_entity"], freshness=False)
            if state is None or state.state not in ("on", "off"):
                return "Hygiëneprogramma: status onbekend, geen setpointopdrachten"
            if state.state == "on":
                return "Hygiëneprogramma actief: fabrieksregeling krijgt voorrang"

        # Panasonic does not expose the configured weekly sterilisation cycle via
        # our HA binding.  Protect a configurable time window around that factory
        # programme instead of trying to reproduce it.
        if local_now is not None and hygiene_schedule_active(self.settings, local_now):
            return (f"Geplande fabrikantsterilisatie rond {self.settings['hygiene_start']} "
                    f"({self.settings['hygiene_target_c']:g} °C): SolarPilot stuurt geen boilerdoel")

        manual_ids = []
        if self.config.get("manual_entity"):
            manual_ids.append(self.config["manual_entity"])
        manual_ids.extend(x for x in self.config.get("manual_entities", []) if x and x not in manual_ids)
        active = {x.strip().casefold() for x in str(self.settings.get("manual_active_states", "on")).split(",") if x.strip()}
        for entity_id in manual_ids:
            state = self._state(entity_id, freshness=False)
            if state is None:
                return f"Handmatige/krachtige modus {entity_id}: status onbekend, geen setpointopdrachten"
            if state.state.casefold() in active:
                return f"Handmatige/krachtige modus actief ({entity_id}): fabrieksregeling krijgt voorrang"

        if obj is not None:
            text = " ".join(str(x) for x in (obj.state, obj.attributes.get("operation_mode", ""), obj.attributes.get("preset_mode", ""))).casefold()
            if any(word in text for word in ("disinfect", "legionella", "hygiene", "steriliz", "sterilis", "boost", "powerful")):
                return "Hygiëne/krachtige bedrijfsmodus gemeld; geen setpointopdrachten"
            # If the manufacturer (or a person) asks for a target above SolarPilot's
            # normal maximum, never lower it.  This also protects a sterilisation
            # cycle that continues beyond the configured schedule guard.  Control
            # resumes automatically only after the manufacturer has restored a
            # normal target on its own.
            domain = self.config["target_entity"].split(".")[0]
            raw_target = obj.state if domain in ("number", "input_number") else obj.attributes.get("temperature")
            target = finite(raw_target)
            if target is not None and target > float(self.settings["surplus_c"]) + 0.05:
                return (f"Boilerdoel {target:g} °C ligt boven SolarPilot-maximum; "
                        "fabrieks-/handmatige regeling krijgt voorrang")
            if obj.state == "off" and self.config["target_entity"].startswith(("climate.", "water_heater.")):
                return "Boiler staat uit; SolarPilot schakelt hem niet zelfstandig in"
        return ""

    def _cooling(self):
        ids = self.config.get("cooling_entities", [])
        results = []
        for entity_id in ids:
            # Climate cloud reports must be fresh; binary helpers can legitimately
            # be unchanged. Their source template must propagate availability.
            obj = self._state(entity_id, freshness=entity_id.startswith("climate."))
            if obj is not None and obj.attributes.get("restored"):
                obj = None
            results.append(cooling_state(obj.state if obj else None, obj.attributes if obj else {}, self.settings["cooling_detection"]))
        if True in results:
            return True
        source = self._space_activity_source()
        # A reported task (PUMP/WATER) is not an HVAC action. In particular,
        # PUMP must not erase a fresh explicit heating/idle action from the
        # installed Aquarea adapter, or invent cooling from generic activity.
        if self._panasonic_auto_blindspot():
            if source["busy"] is not False:
                return None
        if source["configured"]:
            if source["busy"] is not False and not self._verified_space_actions():
                return None
            if not ids:
                return False if source["busy"] is False else None
        return None if not ids or None in results else False

    def _entity_integration_domains(self, entity_id):
        """Return exact registry/config-entry domains without name heuristics."""
        if not isinstance(entity_id, str) or not entity_id:
            return frozenset()
        try:
            from homeassistant.helpers import entity_registry as er
            registry = er.async_get(self.runtime.hass)
            row = registry.async_get(entity_id)
        except (AttributeError, KeyError, TypeError, ValueError):
            return frozenset()
        if row is None:
            return frozenset()
        domains = set()
        platform = str(getattr(row, "platform", "") or "").strip().casefold()
        if platform:
            domains.add(platform)
        entry_id = getattr(row, "config_entry_id", None)
        entries = getattr(self.runtime.hass, "config_entries", None)
        get_entry = getattr(entries, "async_get_entry", None)
        if entry_id and callable(get_entry):
            try:
                entry = get_entry(entry_id)
            except (AttributeError, KeyError, TypeError, ValueError):
                entry = None
            domain = str(getattr(entry, "domain", "") or "").strip().casefold()
            if domain:
                domains.add(domain)
        return frozenset(domains)

    def _is_panasonic_adapter(self, entity_id):
        """Match only confirmed Panasonic adapter integration domains."""
        return bool(PANASONIC_ADAPTER_DOMAINS
                    & self._entity_integration_domains(entity_id))

    def _space_activity_source(self):
        """Read a configured task-direction source; never infer HEAT/COOL or power."""
        entity_id = self.config.get("space_activity_entity", "")
        if not entity_id:
            return {"configured": False, "busy": None, "valid": False,
                    "state": None, "reason": ""}
        obj = self._state(entity_id)
        if obj is None or obj.attributes.get("restored"):
            return {"configured": True, "busy": None, "valid": False,
                    "state": None,
                    "reason": "Extra zonnebuffer wacht: gemelde warmtepomptaak ontbreekt, is te oud of is herstelde cache"}
        active = state_values(self.settings.get("space_activity_active_states", "PUMP"))
        inactive = state_values(self.settings.get("space_activity_inactive_states", "IDLE;WATER"))
        raw = str(obj.state).strip()
        value = raw.casefold()
        if not active or not inactive or active & inactive:
            return {"configured": True, "busy": None, "valid": False,
                    "state": raw,
                    "reason": "Extra zonnebuffer wacht: actieve en inactieve warmtepomptaken zijn niet eenduidig ingesteld"}
        if value in active:
            return {"configured": True, "busy": True, "valid": True,
                    "state": raw,
                    "reason": "Extra zonnebuffer wacht: gemelde warmtepomptaak wijst op ruimtebedrijf; dit bewijst geen HEAT/COOL of compressorvermogen"}
        if value in inactive:
            return {"configured": True, "busy": False, "valid": True,
                    "state": raw, "reason": ""}
        return {"configured": True, "busy": None, "valid": False,
                "state": raw,
                "reason": "Extra zonnebuffer wacht: gemelde warmtepomptaak heeft geen eenduidig ingestelde betekenis"}

    def _panasonic_auto_blindspot(self):
        """Detect the legacy panasonic_cc AUTO idle/off mapping only.

        The installed aquarea adapter reports its native current_action. Its
        fresh idle action is usable; sharing a manufacturer or ACK contract
        does not make it share another adapter's legacy action blindspot.
        """
        for entity_id in self.config.get("cooling_entities", []):
            if not entity_id.startswith("climate."):
                continue
            obj = self._state(entity_id)
            if obj is None or "panasonic_cc" not in self._entity_integration_domains(entity_id):
                continue
            mode = str(obj.state).strip().casefold()
            action = str(obj.attributes.get("hvac_action", "")).strip().casefold()
            if mode in ("auto", "heat_cool") and action in ("idle", "off"):
                return True
        return False

    def space_activity_status(self):
        """Return busy/reason/relevance for DHW and advisory heat-pump learning."""
        source = self._space_activity_source()
        ids = [x for x in self.config.get("cooling_entities", []) if x.startswith("climate.")]
        unknown = bool(source["configured"] and source["busy"] is None)
        active_action = False
        # Keep the existing conservative learning context independent of the
        # optional-temperature guard, including registered Aquarea AUTO idle.
        uncertain_panasonic_load = False
        for entity_id in ids:
            obj = self._state(entity_id)
            if obj is None:
                unknown = True
                continue
            action = str(obj.attributes.get("hvac_action", "")).strip().casefold()
            if action in ("heating", "preheating", "cooling", "defrosting"):
                active_action = True
                continue
            mode = str(obj.state).strip().casefold()
            if mode != "off" and action not in ("idle", "off", "fan", "drying"):
                unknown = True
            if (mode in ("auto", "heat_cool") and action in ("idle", "off")
                    and self._is_panasonic_adapter(entity_id)
                    and not source["configured"]):
                unknown = True
                uncertain_panasonic_load = True
        relevant = bool(source["configured"] or uncertain_panasonic_load)
        if active_action:
            if source["configured"] and source["busy"] is False:
                return None, "Extra zonnebuffer wacht: klimaat- en gemelde warmtepomptaak spreken elkaar tegen", relevant, source
            return True, "Extra zonnebuffer wacht: ruimteverwarming/koeling actief; Panasonic houdt de taakverdeling", relevant, source
        if source["busy"] is True:
            return True, source["reason"], True, source
        if not ids and not source["configured"]:
            return None, "Extra zonnebuffer wacht: geen betrouwbare ruimteklimaatactie gekoppeld", False, source
        if unknown:
            return None, source["reason"] or "Extra zonnebuffer wacht: ruimteklimaatactie niet betrouwbaar bekend", relevant, source
        return False, "", relevant, source

    def _space_activity(self):
        """Read explicit climate actions and a reported task direction, read-only."""
        busy, reason, _relevant, _source = self.space_activity_status()
        return busy, reason

    def _verified_space_actions(self):
        """Can the known native adapter disambiguate a generic task report?

        This exception is scoped to the verified aquarea current_action route.
        Do not weaken a task guard for another/unregistered adapter. Explicitly
        off zones require no manufacturer-specific action contract.
        """
        ids = [entity_id for entity_id in self.config.get("cooling_entities", [])
               if entity_id.startswith("climate.")]
        if not ids:
            return False
        for entity_id in ids:
            obj = self._state(entity_id)
            if obj is None or obj.attributes.get("restored"):
                return False
            mode = str(obj.state).strip().casefold()
            action = str(obj.attributes.get("hvac_action", "")).strip().casefold()
            if mode == "off" and action in ("", "idle", "off"):
                continue
            if ("aquarea" not in self._entity_integration_domains(entity_id)
                    or action not in ("heating", "preheating", "cooling", "defrosting",
                                      "idle", "off", "fan", "drying")):
                return False
        return True

    def _space_raise_guard(self):
        """Guard optional raises using actual climate actions, not task labels.

        Keep space_activity_status separate: PUMP remains useful unknown-load
        evidence for learning even when a fresh idle action permits DHW.
        """
        ids = [entity_id for entity_id in self.config.get("cooling_entities", [])
               if entity_id.startswith("climate.")]
        if not ids:
            return self._space_activity()
        source = self._space_activity_source()
        if source["configured"] and source["busy"] is not False and not self._verified_space_actions():
            return self._space_activity()
        unknown = False
        for entity_id in ids:
            obj = self._state(entity_id)
            if obj is None or obj.attributes.get("restored"):
                unknown = True
                continue
            action = str(obj.attributes.get("hvac_action", "")).strip().casefold()
            if action in ("heating", "preheating", "cooling", "defrosting"):
                return True, "Extra zonnebuffer wacht: actuele ruimteverwarming/koeling actief; Panasonic houdt de taakverdeling"
            mode = str(obj.state).strip().casefold()
            if mode != "off" and action not in ("idle", "off", "fan", "drying"):
                unknown = True
        if self._panasonic_auto_blindspot() and self._space_activity_source()["busy"] is not False:
            unknown = True
        if unknown:
            return None, "Extra zonnebuffer wacht: actuele ruimteklimaatactie ontbreekt of is niet betrouwbaar"
        return False, ""

    def read(self, grid, grid_valid, discharge, local_now=None):
        target, obj = self._target()
        pv = self.runtime.pv_w
        pv = pv if pv is not None and pv >= 0 else None
        # P1 contains current consumption already. Only the isolated device's
        # possible unconsumed commitment is reserved; it is never solar credit.
        isolated_reserve = max(0.0, finite(getattr(self.runtime, "isolated_reserve_w", 0)) or 0.0)
        export = max(0.0, min(pv, max(0, -grid - discharge)) - isolated_reserve) if grid_valid and pv is not None else None
        power, _ = self.runtime._power(self.config.get("power_entity"), self.settings["stale_s"])
        own_power = power if power is not None and power >= 0 and self.exclusive_meter() else None
        before = (max(0.0, min(pv, max(0, -grid + own_power - discharge)) - isolated_reserve)
                  if grid_valid and pv is not None and own_power is not None else None)
        capacity = getattr(self.runtime, "capacity", None)
        optional_headroom = (capacity.optional_headroom_w if capacity and capacity.enabled
                             and self.runtime.capacity_settings.get("respect_optional_dhw", True)
                             else None)
        if optional_headroom is not None:
            optional_headroom = max(0.0, optional_headroom - isolated_reserve)
        self.reading = DHWReading(self._temperature(), target, pv, export, before,
                                  grid if grid_valid else None, self._cooling(),
                                  bool(reason := self._protected(obj, local_now)), reason,
                                  optional_headroom)
        self.reading.battery_discharge_w = max(0.0, float(discharge or 0.0))
        self.reading.space_climate_busy, self.reading.space_climate_reason = self._space_raise_guard()
        return self.reading

    def _comfort_forecast(self, local_now):
        """Reuse existing forecasts; no extra API call and at most once per 5 min."""
        stamp = local_now.timestamp()
        if self._comfort_forecast_stamp is not None and 0 <= stamp-self._comfort_forecast_stamp < 300:
            return
        self._comfort_forecast_stamp = stamp
        self._comfort_slots, self._comfort_forecast_available = [], False
        if not self.settings.get("evening_enabled"):
            return
        values = self.runtime._forecast_values()
        if values.get("remaining_today_kwh") is None:
            return
        rows = self.runtime._planner_pv_hourly(local_now)
        if not rows or not any(finite(x) is not None and x > 0 for x in rows[:24]):
            return
        # Actual household power minus Wallbox (if reliable), kept nonnegative.
        # This is a planning estimate; actual P1 remains the start guard.
        wb = self.runtime._wallbox_reading()
        ev = max(0.0, wb.power_w or 0.0) if wb.valid else 0.0
        pv, grid = finite(self.runtime.pv_w), finite(self.runtime.grid_w)
        base = max(0.0, (pv or 0)+(grid or 0)-ev)
        own, _ = self.runtime._power(self.config.get("power_entity"), self.settings["stale_s"])
        if self.exclusive_meter() and own is not None:
            base = max(0.0, base-max(0.0, own))
        self._comfort_slots = [(local_now+timedelta(hours=i), max(0.0, float(power)-base))
                              for i, power in enumerate(rows[:24]) if finite(power) is not None]
        self._comfort_forecast_available = True

    def _predicted_cooling(self):
        """Passive forecast veto, including manually selected COOL with idle action.

        Does not change HEAT/COOL/AUTO. Reuses the existing learned profiles and
        weather cache, not the climate *actuator* decision (which may be HOLD).
        """
        if not self.settings.get("predictive_cooling_enabled"):
            return False, ""
        climate = self.runtime.smart_climate
        if not climate.settings.get("enabled") or not climate.configured:
            return False, ""
        zones = climate._zones()
        if not zones or len(zones) != len(climate.settings.get("zone_entities", [])) or climate.state.fault:
            return False, ""
        wall = time.time()
        # A cached cooling prediction must not outlive its weather evidence.
        # Current weather heartbeat and forecast payload have separate lifetimes.
        if not climate.forecast_cache_valid():
            self._prediction_check_wall = None
            self._prediction_cached = (False, "")
            self._prediction_forecast_key = None
            return self._prediction_cached
        forecast_key = (climate.settings.get("weather_entity"), climate.state.last_forecast_wall)
        if forecast_key != self._prediction_forecast_key:
            self._prediction_check_wall = None
            self._prediction_forecast_key = forecast_key
        if self._prediction_check_wall is not None and 0 <= wall-self._prediction_check_wall < 300:
            return self._prediction_cached
        self._prediction_check_wall = wall
        self._prediction_cached = (False, "")
        import math
        hours = max(1, math.ceil(self.settings["predictive_cooling_horizon_h"]))
        weather = climate._outside_hourly()[:hours]
        if len(weather) < hours:
            return self._prediction_cached
        for z in zones:
            profile = climate.state.profiles.get(z["entity_id"])
            if profile is None or profile.confidence(climate.settings) < climate.settings.get("model_confidence_min", .55):
                continue
            # A deliberately fixed HEAT zone is not an automatic COOL request.
            if str(z["mode"]).casefold() == "heat":
                continue
            forecast = profile.predict(z["current"], z["target"], weather, mode="off",
                solar_hourly_w=climate.last_solar_hourly[:hours], settings=climate.settings)
            upper = float(z["target"])+float(climate.settings.get("soft_band_c", .5))
            if any(v > upper for v in [float(z["current"]), *forecast]):
                self._prediction_cached = (True, f"Thermisch model verwacht binnen {hours} uur koelvraag; extra boileropwarming begrensd")
                break
        return self._prediction_cached

    def _prepare_comfort(self, local_now, r):
        self._comfort_forecast(local_now)
        wb = self.runtime._wallbox_reading()
        wc = self.runtime.wallbox_settings
        # Comfort before EV: reclaimed watts are for THIS comfort test only.
        # Neither physical site capacity nor the 60 °C surplus is inflated.
        # A configured Full Solar setting alone is not proof of an autonomous
        # session. Require the same fresh, confirmed session as other transfers;
        # no power is borrowed from manual, stale, unknown or idle charging.
        power = finite(wb.power_w)
        age = finite(getattr(wb, "age_s", None))
        stamp = finite(getattr(wb, "stamp", None))
        wall_age = time.time()-stamp if stamp is not None else None
        max_age = min(wc.get("stale_s", 300), wc.get("reclaim_max_age_s", 120))
        full = (wc.get("enabled") and wb.valid and getattr(wb, "session_confirmed", False)
                and (wb.mode or "").casefold() in state_set(wc.get("full_solar_states", "full_solar"))
                and wb.connected is True and wb.demand is True
                and power is not None and power >= wc.get("charging_threshold_w", 50)
                and age is not None and -5 <= age <= max_age
                and wall_age is not None and -5 <= wall_age <= max_age)
        ev_w = power if full else 0.0
        isolated_reserve = max(0.0, finite(getattr(self.runtime, "isolated_reserve_w", 0)) or 0.0)
        before_ev = (max(0.0, min(r.pv_w, max(0.0, -(r.grid_w or 0.0)-r.battery_discharge_w+ev_w)) - isolated_reserve)
                     if r.pv_w is not None and r.grid_w is not None else None)
        ev_idle = wb.valid and (wb.connected is False or wb.demand is False
            or (wb.status or "").casefold() in state_set(wc.get("idle_states", "")))
        if wc.get("enabled") and not ev_idle and wc.get("manual_suspend_extra_dhw", True) and wb.mode in ("manual", "unknown"):
            r.luxury_allowed = False
            r.luxury_reason = ("Manueel autoladen: extra 60 °C vervalt; normaal warmtepompcomfort blijft vrij"
                                if wb.mode == "manual" else "Laadsessie onbekend: geen extra 60 °C tot terugmelding duidelijk is")
        if wc.get("enabled"):
            charging = wb.valid and (wb.power_w or 0) >= wc.get("charging_threshold_w", 50)
            idle = wb.valid and (wb.connected is False or wb.demand is False
                                 or (wb.status or "").casefold() in state_set(wc.get("idle_states", "")))
            if not wb.valid or (not charging and not idle):
                r.luxury_allowed = False
                r.luxury_reason = "Extra 60 °C wacht op Wallbox-laadstart of betrouwbare laadstatus"
        preference = getattr(self.runtime, "dishwasher_priority", None)
        # A running preferred dishwasher is a load to reserve, not a blanket
        # veto on 60 °C. A ready cycle that demonstrably fits still receives
        # the first start opportunity. The allocation deliberately excludes any
        # Wallbox credit and does not reserve this DHW heater a second time.
        if (preference is not None and r.luxury_allowed
                and (preference.view.active_ids or preference.view.candidate_ids)):
            holding_high = (self.owned_target == self.settings["surplus_c"]
                            and not self.pending)
            fresh_target = self._state(self.config["target_entity"])
            action = (str(fresh_target.attributes.get("hvac_action", "")).casefold()
                      if fresh_target is not None else "")
            own_power, _ = self.runtime._power(
                self.config.get("power_entity"), self.settings["stale_s"])
            verified_heating = (action in ("heating", "preheating")
                                or (self.exclusive_meter() and own_power is not None
                                    and own_power > 100))
            restart_c = self.settings["surplus_c"] + self.settings["tank_differential_c"]
            restart_proof = (holding_high and
                             (r.temperature_c is None or r.temperature_c <= restart_c)
                             and not verified_heating)
            capacity = getattr(self.runtime, "capacity", None)
            capacity_guard = bool(capacity and getattr(capacity, "enabled", False)
                                  and self.runtime.capacity_settings.get(
                                      "respect_optional_dhw", True))
            allocation = preference.dhw_luxury_allocation(
                mode=self.runtime.mode,
                actual_grid=r.grid_w,
                filtered_grid=getattr(self.runtime, "filtered", None),
                pv_w=r.pv_w,
                discharge_w=r.battery_discharge_w,
                reserve_w=(self.runtime.settings.get("reserve_w", 0) + isolated_reserve),
                unmetered_aeg_reserve_w=getattr(
                    self.runtime, "_dishwasher_unmetered_reserve", None),
                surplus_threshold_w=self.settings["surplus_threshold_w"],
                holding_owned_high=holding_high,
                restart_proof_required=restart_proof,
                capacity_guard_enabled=capacity_guard,
                capacity_valid=(bool(getattr(capacity, "valid", False))
                                if capacity_guard else True),
                optional_import_headroom_w=r.optional_import_headroom_w,
                estimated_heat_power_w=self.settings["estimated_heat_power_w"],
                # Active preferred cycles keep their own stricter protection.
                # Other isolated loads are covered by the explicit reserve.
                states={i: s for i, s in self.runtime.states.items()
                        if i not in getattr(self.runtime, "source_isolated_devices", {})
                        or i in preference.view.active_ids | preference.view.candidate_ids})
            if not allocation.allowed:
                r.luxury_allowed = False
                r.luxury_reason = allocation.reason
        if hasattr(self.runtime, "priority_board"):
            self.runtime.priority_board.guard_extra(r, time.monotonic())
        target, obj = self._target()
        heating = bool(obj and (obj.state == "heating" or obj.attributes.get("hvac_action") == "heating"))
        if r.cooling is True:
            self._cooling_wall = time.time()
        # A known cooling period interrupted by DHW is not a cooling-clear event.
        elif (heating or self.comfort.model.heating_now) and self._cooling_wall is not None:
            if time.time()-self._cooling_wall < self.settings["cooling_clear_s"]:
                self._cooling_wall = time.time()
                self.policy.last_cooling = time.monotonic()
        predicted, why = self._predicted_cooling()
        r.predicted_cooling, r.predicted_cooling_reason = predicted, why
        plan = self.comfort.plan(c=self.settings, now=local_now, temperature=r.temperature_c,
            pv_w=r.pv_w, grid_w=r.grid_w, before_ev_w=before_ev,
            night=night_active(self.settings, local_now), protected=r.protected, heating=heating,
            forecast_slots=self._comfort_slots, forecast_available=self._comfort_forecast_available,
            holding_evening=(self.owned_target is not None and self.comfort.evening_target is not None
                and abs(self.owned_target-self.comfort.evening_target)<0.51 and not self.pending))
        r.standby_c = plan.standby_target_c
        r.comfort_target_c, r.comfort_reason = plan.target_c, plan.reason
        r.comfort_stage, r.comfort_urgent = plan.stage, plan.urgent
        # Respect the native step without ever rounding above the explicitly
        # chosen normal/evening ceiling. No hidden deadband-compensating boost.
        if obj is not None:
            domain = self.config["target_entity"].split(".")[0]
            native = domain in ("number", "input_number")
            step = finite(obj.attributes.get("step" if native else "target_temp_step", .5))
            lower = finite(obj.attributes.get("min" if native else "min_temp"))
            if step and step > 0 and lower is not None:
                import math
                for key in ("standby_c", "comfort_target_c"):
                    value = getattr(r, key)
                    if value is not None:
                        rounded = lower+math.ceil((value-lower)/step-1e-8)*step
                        limit = (float(self.settings["evening_cap_c"])
                                 if key == "comfort_target_c" and plan.stage == "evening"
                                 else effective_base_target(self.settings))
                        if rounded > limit + .05:
                            setattr(r, key, None)
                            plan.warning = "; ".join(filter(None, [plan.warning,
                                "Apparaatstap past niet binnen het gekozen doelplafond; geen afronding boven de limiet"]))
                        else:
                            setattr(r, key, rounded)

    def exclusive_meter(self):
        meter = self.config.get("power_entity")
        if not meter:
            return False
        r = self.runtime
        reserved = {r.settings.get(k) for k in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity")}
        reserved.update(c.get("power_entity") for c in r.configs.values())
        if r.wallbox_settings["enabled"]:
            reserved.add(r.wallbox_settings.get("power_entity"))
        return meter not in reserved

    def check_target(self, desired):
        entity_id = self.config["target_entity"]
        domain = entity_id.split(".")[0]
        if domain not in ("water_heater", "climate", "number", "input_number"):
            return "Ongeldig type boilerbediening"
        if protected_entity(self.runtime.hass, self.runtime.wallbox_settings, entity_id):
            return "Wallbox is alleen-lezen; geen boilerbediening toegestaan"
        for cfg in self.runtime.configs.values():
            if entity_id in {cfg.get(k) for k in ("control_entity", "active_entity", "number_entity", "start_script", "stop_script")}:
                return "Boilerbediening is dubbel gekoppeld als gewone verbruiker"
        actual, obj = self._target()
        if actual is None or obj is None:
            return "Doelterugmelding/eenheid ontbreekt (vereist °C)"
        native_number = domain in ("number", "input_number")
        low = finite(obj.attributes.get("min" if native_number else "min_temp"))
        high = finite(obj.attributes.get("max" if native_number else "max_temp"))
        step = finite(obj.attributes.get("step" if native_number else "target_temp_step", 0.5))
        if low is None or high is None or step is None or step <= 0:
            return "Toestelgrenzen of temperatuurstap ontbreken"
        if not low <= desired <= high:
            return f"Doel {desired:g} °C buiten toestelbereik {low:g}–{high:g} °C"
        if abs((desired - low) / step - round((desired - low) / step)) > 1e-5:
            return "Doeltemperatuur past niet bij de stapgrootte van het toestel"
        features = finite(obj.attributes.get("supported_features"))
        if not native_number and (features is None or not int(features) & 1):
            return "Toestel meldt geen ondersteuning voor één doeltemperatuur"
        return ""

    async def _save(self):
        await self.runtime.store.async_save(self.runtime._snapshot())

    async def _mark_fault(self, reason):
        self.fault = reason
        self.pending = None
        self.status = reason
        await self._save()
        self.runtime.note("Boiler: " + reason)
        await self.runtime.notify("Boiler: " + reason + ". Controleer de echte toestand. Geen automatische herhaalpogingen.")

    def _defer_optional_raise(self, now, desired, previous, reading):
        """Retain completed live stability without treating a proposal as issued."""
        current, candidate, since = previous
        base = effective_base_target(self.settings)
        owned_current = (not self.pending and current is not None and current > base + .05
                         and self.owned_target is not None and reading.actual_target_c is not None
                         and abs(current - self.owned_target) < .05
                         and abs(current - reading.actual_target_c) < .05)
        self.policy.current = current if owned_current else None
        self.policy.candidate = desired
        self.policy.candidate_since = (since if candidate == desired and since is not None
                                       else now - float(self.settings["rise_delay_s"]))
        # last_sample remains current: genuine gaps and source changes still
        # invalidate the candidate in the next ordinary policy update.

    async def tick(self, now, grid, valid, discharge, allow_command=True, local_now=None):
        self.optional_raise_remaining_s = 0
        if not self.configured:
            return False
        if local_now is None:
            zone = getattr(getattr(self.runtime.hass, "config", None), "time_zone", "Europe/Brussels")
            local_now = datetime.now(ZoneInfo(zone))
        await self.reconcile_restart(local_now)
        r = self.read(grid, valid, discharge, local_now)
        self._prepare_comfort(local_now, r)
        self.policy.settings = {**self.settings, "sample_gap_s": max(30, self.runtime.settings["interval_s"] * 2)}
        holding = self.owned_target == self.settings["surplus_c"] and not self.pending
        previous_policy = (self.policy.current, self.policy.candidate, self.policy.candidate_since)
        decision = self.policy.update(now, local_now, r, holding)
        issued_proposal = (self.pending is not None and self.pending.get("target") == decision.target_c
                           and self.owned_target == decision.target_c)
        if (not issued_proposal and decision.remaining_s == 0 and decision.target_c is not None
                and decision.target_c > effective_base_target(self.settings) + .05
                and r.actual_target_c is not None and decision.target_c > r.actual_target_c + .05):
            # A mature proposal may still be denied by observation, safety,
            # capability or serialization guards below. It never grants hold
            # hysteresis until the target is actually issued/acknowledged.
            self._defer_optional_raise(now, decision.target_c, previous_policy, r)
        if r.temperature_c is not None and r.temperature_c < self.settings["minimum_c"] and not self._last_low:
            self.runtime.note(f"Boiler onder bewaakte comfortgrens {self.settings['minimum_c']:g} °C; normaal doel {effective_base_target(self.settings):g} °C blijft staan. Geen temperatuurboost; Panasonic bepaalt de herverwarming.")
        self._last_low = decision.low_temperature
        if local_now.timestamp()-self._last_model_save_wall >= 300:
            self._last_model_save_wall = local_now.timestamp()
            self.runtime.store.async_delay_save(self.runtime._snapshot, 30)
        if self.pending:
            p = self.pending
            obj = self._state(self.config["target_entity"])
            stamp = getattr(obj, "last_reported", obj.last_updated).timestamp() if obj else 0
            ack_poll_min_s = max(0.0, finite(p.get("ack_poll_min_s")) or 0.0)
            delayed_report = (now - p["issued"] >= ack_poll_min_s
                              and stamp >= p["issued_wall"] + ack_poll_min_s)
            if (r.actual_target_c is not None
                    and abs(r.actual_target_c - p["target"]) < 0.05
                    and delayed_report):
                self.pending = None
                self.owned_target = None if p["release"] else p["target"]
                self.last_success = {
                    "target_c": p["target"],
                    "time": datetime.now().astimezone().isoformat(),
                    "confirmation": ("delayed_ha_state" if ack_poll_min_s else "ha_state"),
                }
                if ack_poll_min_s:
                    self.runtime.note(
                        f"Boiler: doel {p['target']:g} °C na wachttijd teruggelezen in Home Assistant "
                        "(geen rechtstreeks apparaat- of opwarmbewijs).")
                else:
                    self.runtime.note(f"Boiler: doel {p['target']:g} °C bevestigd (niet hetzelfde als opgewarmd).")
                await self._save()
            elif now - p["issued"] >= self.settings["ack_timeout_s"]:
                await self._mark_fault("Boileropdracht niet bevestigd; handmatige controle vereist")
            else:
                self.status = ("Wacht op latere Panasonic-doelwaarneming; onmiddellijke terugmelding "
                               "geldt niet als bevestiging" if ack_poll_min_s
                               else "Wacht op terugmelding boilerdoel")
                return False
        if self.restart_recovery:
            self.status = self.restart_recovery["reason"]
            return False
        if self.needs_review or self.fault or self.manual_hold:
            self.status = self.fault or ("Boilercontrole na herstart vereist" if self.needs_review
                                         else "Boilerregeling uit voorzorg gepauzeerd; hervat pas na boilercontrole")
            return False
        # Observe cannot write, not even minimum/fallback/hygiene-related commands.
        if self.runtime.mode == "observe":
            self.status = "Observatie: " + decision.reason
            return False
        if r.protected:
            self.status = r.protection_reason
            # Relinquish SolarPilot ownership without writing a fallback target.
            # The factory/manual controller is authoritative while protected.
            # Once the protected state has ended *and* the device itself reports a
            # normal target again, SolarPilot may resume automatically.  This avoids
            # a weekly manual acknowledgement after Panasonic sterilisation while
            # still never lowering a 62/65 °C hygiene request.
            if self.owned_target is not None:
                self.owned_target = None
                self.policy.reset_stability()
                await self._save()
            return False
        if self.owned_target is not None and r.actual_target_c is not None and abs(self.owned_target - r.actual_target_c) > 0.05:
            self.owned_target = None
            self.manual_hold = True
            self.status = "Boilerdoel wijkt af van laatste bevestiging: regeling uit voorzorg gepauzeerd"
            self.policy.reset_stability()
            await self._save()
            self.runtime.note(self.status)
            return False
        if not self.settings["safety_confirmed"]:
            self.status = "Nog niet vrijgegeven: controleer hygiëneprogramma, toestelgeschiktheid en verbrandingsbeveiliging"
            return False
        releasing = self.runtime.mode != "solar" or not self.auto_enabled
        if releasing and self.owned_target is None:
            self.status = "Boilerregeling gepauzeerd; fabrieksinstelling blijft staan"
            return False
        desired = effective_base_target(self.settings) if releasing else decision.target_c
        if desired is None:
            self.status = decision.reason
            return False
        # Initial unexpected high temperature requests (e.g. disinfection) are
        # NEVER reduced automatically. Bestaande gewone minimum/50/60-doelen kunnen worden overgenomen.
        if self.owned_target is None and r.actual_target_c is not None and r.actual_target_c > self.settings["surplus_c"]:
            self.manual_hold = True
            self.status = "Hoger bestaand boilerdoel: controleer handmatige/hygiënestand"
            await self._save()
            return False
        error = self.check_target(desired)
        if error:
            self.status = error
            return False
        if r.actual_target_c is not None and abs(r.actual_target_c - desired) < 0.05:
            new_owned = None if releasing else desired
            ownership_changed = self.owned_target != new_owned
            self.owned_target = new_owned
            self.status = "Basisdoel vrijgegeven; boiler niet uitgeschakeld" if releasing else decision.reason
            if ownership_changed:
                self.runtime.store.async_delay_save(self.runtime._snapshot, 1)
            return False
        # Optional increases are infrequent. Never delay falling back after real
        # import, pause, night or cooling, and never use the floor to bypass this.
        if (not releasing and desired > effective_base_target(self.settings) + .05
                and r.actual_target_c is not None and desired > r.actual_target_c + .05
                and self.last_command_wall > 0):
            import math
            remaining = max(0, math.ceil(float(self.settings["optional_raise_interval_s"])
                                        - max(0.0, time.time()-self.last_command_wall)))
            if remaining:
                self.optional_raise_remaining_s = remaining
                self.status = f"Extra zonnebuffer wacht nog {remaining} s tussen doelverhogingen; Panasonic blijft regelen"
                return False
        if not allow_command:
            self.status = decision.reason + "; wacht op andere regelopdracht"
            return False
        return await self._send(now, desired, releasing, decision.reason)

    async def _send(self, now, desired, release, reason):
        rt = self.runtime
        self.policy.current = desired
        self.policy.candidate = self.policy.candidate_since = None
        self.owned_target = desired
        self.pending = {"target": desired, "issued": now, "issued_wall": time.time(), "release": release,
                        "ack_poll_min_s": self._ack_poll_min_s()}
        self.last_command_wall = self.pending["issued_wall"]
        rt.last_issued = now
        rt.last_issued_wall = self.last_command_wall
        rt.wallbox_guard.note_action(now, self.last_command_wall, 0, 0)
        await self._save()  # Durable intent BEFORE the physical call.
        self.status = f"Doel {desired:g} °C aangevraagd"
        rt.note("Boiler: " + self.status + " — " + reason)
        try:
            entity_id = self.config["target_entity"]
            domain = entity_id.split(".")[0]
            async with asyncio.timeout(20):
                if domain in ("number", "input_number"):
                    await rt._call(entity_id, "set_value", {"value": desired})
                else:
                    await rt._call(entity_id, "set_temperature", {"temperature": desired})
        except (HomeAssistantError, TimeoutError, ValueError) as err:
            await self._mark_fault(f"Onzekere boileropdracht ({type(err).__name__}); controle vereist")
        return True

    async def set_enabled(self, enabled):
        async with self.runtime._lock:
            self.auto_enabled = bool(enabled)
            self.settings["enabled"] = self.auto_enabled
            self.config["enabled"] = self.auto_enabled
            self._persist_canonical()
            self.policy.reset_stability()
            await self._save()
        await self.runtime.tick()

    async def set_number(self, key, value):
        if key not in DHW_NUMBERS:
            raise HomeAssistantError("Onbekende boilerinstelling")
        value = finite(value)
        if value is None:
            raise HomeAssistantError("Ongeldige boilerinstelling: waarde moet een eindig getal zijn")
        async with self.runtime._lock:
            candidate = {**self.settings, key: value}
            if validate_settings(candidate):
                raise HomeAssistantError("Ongeldige boilerinstelling: controleer comfortgrens ≤ normaal doel ≤ zonnedoel ≤ overschotdoel, koellimiet en bereiken")
            targets = []
            if key == "normal_c":
                targets.append(effective_base_target(candidate))
            elif key in ("solar_c", "surplus_c", "cooling_cap_c"):
                targets.append(value)
            for target in targets:
                if error := self.check_target(target):
                    raise HomeAssistantError(error)
            self.settings = candidate
            self.config = dict(candidate)
            self.tunables[key] = value
            self._persist_canonical()
            self.policy.reset_stability()
            await self._save()
        await self.runtime.tick()

    async def review(self):
        async with self.runtime._lock:
            if self.runtime.mode == "solar" or self.pending:
                raise HomeAssistantError("Kies eerst Pauze of Observatie en wacht op een lopende boileropdracht")
            target, obj = self._target()
            zone = getattr(getattr(self.runtime.hass, "config", None), "time_zone", "Europe/Brussels")
            if target is None or self._temperature() is None or self._protected(obj, datetime.now(ZoneInfo(zone))):
                raise HomeAssistantError("Controleer actuele temperaturen en rond hygiëne/krachtige modus eerst af")
            self.owned_target = None
            self.needs_review = self.manual_hold = False
            self.restart_recovery = None
            self.fault = ""
            self.policy.reset_stability()
            await self._save()
            self.runtime.note("Boilercontrole bevestigd; geen fysieke opdracht verstuurd.")
        await self.runtime.tick()

    async def takeover(self):
        async with self.runtime._lock:
            if self.runtime.mode == "solar" or self.pending:
                raise HomeAssistantError("Kies eerst Pauze/Observatie en wacht op een lopende boileropdracht")
            self.auto_enabled = False
            self.manual_hold = True
            self.owned_target = None
            self.needs_review = False
            self.restart_recovery = None
            self.fault = ""
            await self._save()
            self.runtime.note("Boiler handmatig overgenomen: GEEN temperatuur- of uitschakelopdracht.")
        await self.runtime.tick()

    def overview(self):
        d, r = self.policy.result, self.reading
        activity = self._space_activity_source()
        target_entity = self.config.get("target_entity", "")
        target_adapter_domains = sorted(self._entity_integration_domains(target_entity))
        ack_poll_min_s = self._ack_poll_min_s()
        safety_confirmed = bool(self.settings.get("safety_confirmed"))
        control_allowed = bool(self.configured and self.auto_enabled and safety_confirmed
                               and not self.needs_review and not self.manual_hold and not self.fault
                               and not self.restart_recovery)
        panasonic_autonomous = bool(r.protected or not control_allowed or self.owned_target is None)
        return {"configured": self.configured, "enabled": self.auto_enabled,
                "safety_confirmed": safety_confirmed,
                "control_allowed": control_allowed,
                "solar_pilot_owns_target": self.owned_target is not None,
                "panasonic_autonomous": panasonic_autonomous,
                "manual_override_active": bool(self.manual_hold),
                "target_adapter_domains": target_adapter_domains,
                "ack_poll_min_s": ack_poll_min_s,
                "ack_poll_min_unit": "s",
                "ack_confirmation_contract": (
                    "later_ha_report_at_or_after_adapter_delay"
                    if ack_poll_min_s else "fresh_ha_report_after_command"),
                "status": self.status, "reason": d.reason, "stage": d.stage,
                "temperature_c": r.temperature_c, "actual_target_c": r.actual_target_c,
                "proposed_target_c": d.target_c, "base_target_c": d.base_target_c,
                "minimum_c": self.settings["minimum_c"],
                "tank_differential_c": self.settings["tank_differential_c"],
                "normal_target_c": effective_base_target(self.settings),
                "space_climate_busy": r.space_climate_busy,
                "space_climate_reason": r.space_climate_reason,
                "space_activity_source": {
                    "configured": activity["configured"],
                    "valid": activity["valid"],
                    "reported_state": activity["state"],
                    "space_busy": activity["busy"],
                    "evidence": "Gemelde takenstatus; geen bewijs van HEAT/COOL, compressoractiviteit of elektrisch vermogen",
                },
                "control_contract": "Normaal doel is onafhankelijk; geen boost op comfortgrens of ochtenddeadline",
                "expected_restart_c": effective_base_target(self.settings) + self.settings["tank_differential_c"],
                "night": d.night, "cooling": r.cooling, "cooling_block": d.cooling_block,
                "capacity_block": d.capacity_block,
                "optional_import_headroom_w": r.optional_import_headroom_w,
                "low_temperature": d.low_temperature, "pending": bool(self.pending),
                "owned": self.owned_target is not None, "needs_review": self.needs_review,
                "restart_recovery_pending": bool(self.restart_recovery),
                "restart_recovery_reason": (self.restart_recovery or {}).get("reason", ""),
                "manual_hold": self.manual_hold, "fault": self.fault,
                "pv_w": r.pv_w, "measured_solar_export_w": r.export_w,
                "before_boiler_w": r.before_boiler_w,
                "own_meter_available": self.exclusive_meter(),
                "comfort_plan": self.comfort.result.as_dict(), "tank_learning": dict(self.comfort.rates),
                "heat_pump_priority": "Warmtepompcomfort vóór Wallbox; extra 60 °C uitsluitend werkelijk restoverschot",
                "predicted_cooling": r.predicted_cooling, "luxury_allowed": r.luxury_allowed,
                "remaining_s": d.remaining_s,
                "optional_raise_remaining_s": self.optional_raise_remaining_s,
                "last_success": self.last_success,
                "hygiene_schedule": {"enabled": self.settings["hygiene_schedule_enabled"],
                    "weekdays": self.settings["hygiene_weekdays"], "start": self.settings["hygiene_start"],
                    "target_c": self.settings["hygiene_target_c"],
                    "guard_before_s": self.settings["hygiene_guard_before_s"],
                    "guard_after_s": self.settings["hygiene_guard_after_s"]},
                "switch_entity": self.runtime.entity_id("switch", "dhw_enabled"),
                "review_entity": self.runtime.entity_id("button", "dhw_review"),
                "takeover_entity": self.runtime.entity_id("button", "dhw_takeover"),
                "number_entities": {k: self.runtime.entity_id("number", "dhw_" + k) for k in DHW_NUMBERS},
                "configuration_source": "config_entry.options.dhw",
                "settings": {k: self.settings[k] for k in (*DHW_NUMBERS, "night_enabled", "night_start", "night_end",
                    "rise_delay_s", "fall_delay_s", "cooling_clear_s", "cooling_detection",
                    "respect_space_climate", "optional_raise_interval_s",
                    "hygiene_schedule_enabled", "hygiene_weekdays", "hygiene_start", "hygiene_target_c",
                    "hygiene_guard_before_s", "hygiene_guard_after_s", *self._schedule_keys())}}

    @staticmethod
    def _schedule_keys():
        from .dhw_schedule import SCHEDULE_DEFAULTS
        return tuple(SCHEDULE_DEFAULTS)
