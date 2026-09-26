"""Setpoint-only boiler controller, serialized by SolarRuntime's existing lock.

No on/off calls, no powerful/boost mode, no Wallbox calls. Independent factory
thermostat, hygiene functions and hot-water safety remain prerequisites.
"""
from __future__ import annotations
import asyncio
from datetime import datetime
import time
from zoneinfo import ZoneInfo
from homeassistant.exceptions import HomeAssistantError
from .dhw import (DHW_DEFAULTS, DHW_NUMBERS, DHWPolicy, DHWReading,
                  cooling_state, finite, validate_settings, effective_base_target,
                  hygiene_schedule_active)
from .wallbox import protected_entity


class DHWManager:
    def __init__(self, runtime):
        self.runtime = runtime
        self.config = {**DHW_DEFAULTS, **runtime.entry.options.get("dhw", {})}
        self.settings = dict(self.config)
        self.policy = DHWPolicy(self.settings)
        self.auto_enabled = bool(self.config["enabled"])
        self.tunables = {}
        self.pending = None
        self.owned_target = None
        self.needs_review = False
        self.manual_hold = False
        self.fault = ""
        self.status = "Niet geconfigureerd"
        self.reading = DHWReading()
        self.last_command_wall = 0.0
        self._release = False
        self._last_low = False
        self.last_success = None

    @property
    def configured(self):
        return bool(self.config.get("target_entity"))

    @property
    def busy(self):
        return self.pending is not None or self.owned_target is not None

    @property
    def blocks_increase(self):
        return self.pending is not None or self.needs_review or bool(self.fault)

    def snapshot(self):
        return {"config_revision": self.config["config_revision"],
                "target_entity": self.config["target_entity"],
                "enabled": self.auto_enabled, "tunables": self.tunables,
                "pending": self.pending, "owned_target": self.owned_target,
                "needs_review": self.needs_review, "manual_hold": self.manual_hold,
                "fault": self.fault, "last_success": self.last_success}

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
        self.manual_hold = bool(data.get("manual_hold")) if same_binding else False
        self.fault = str(data.get("fault", ""))
        self.needs_review = bool(data.get("needs_review") or data.get("pending") or data.get("owned_target") is not None)
        # Do not replay a target or a pending physical call after a restart.
        self.owned_target = None
        self.pending = None
        if self.needs_review:
            self.status = "Boilercontrole na herstart vereist; huidige instelling blijft onaangeroerd"

    def _state(self, entity_id, freshness=True):
        obj = self.runtime.hass.states.get(entity_id) if entity_id else None
        if obj is None or obj.state in ("unknown", "unavailable", ""):
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
        obj = self._state(self.config["target_entity"], freshness=False)
        if obj is None or self._unit(obj) != "°C":
            return None, obj
        domain = self.config["target_entity"].split(".")[0]
        raw = obj.state if domain in ("number", "input_number") else obj.attributes.get("temperature")
        return finite(raw), obj

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
        if not ids:
            return None
        results = []
        for entity_id in ids:
            # Climate cloud reports must be fresh; binary helpers can legitimately
            # be unchanged. Their source template must propagate availability.
            obj = self._state(entity_id, freshness=entity_id.startswith("climate."))
            results.append(cooling_state(obj.state if obj else None, obj.attributes if obj else {}, self.settings["cooling_detection"]))
        return True if True in results else None if None in results else False

    def read(self, grid, grid_valid, discharge, local_now=None):
        target, obj = self._target()
        pv = self.runtime.pv_w
        pv = pv if pv is not None and pv >= 0 else None
        export = min(pv, max(0, -grid - discharge)) if grid_valid and pv is not None else None
        power, _ = self.runtime._power(self.config.get("power_entity"), self.settings["stale_s"])
        own_power = power if power is not None and power >= 0 and self.exclusive_meter() else None
        before = (min(pv, max(0, -grid + own_power - discharge))
                  if grid_valid and pv is not None and own_power is not None else None)
        capacity = getattr(self.runtime, "capacity", None)
        optional_headroom = (capacity.optional_headroom_w if capacity and capacity.enabled
                             and self.runtime.capacity_settings.get("respect_optional_dhw", True)
                             else None)
        self.reading = DHWReading(self._temperature(), target, pv, export, before,
                                  grid if grid_valid else None, self._cooling(),
                                  bool(reason := self._protected(obj, local_now)), reason,
                                  optional_headroom)
        return self.reading

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

    async def tick(self, now, grid, valid, discharge, allow_command=True, local_now=None):
        if not self.configured:
            return False
        if local_now is None:
            zone = getattr(getattr(self.runtime.hass, "config", None), "time_zone", "Europe/Brussels")
            local_now = datetime.now(ZoneInfo(zone))
        r = self.read(grid, valid, discharge, local_now)
        self.policy.settings = {**self.settings, "sample_gap_s": max(30, self.runtime.settings["interval_s"] * 2)}
        holding = self.owned_target == self.settings["surplus_c"] and not self.pending
        decision = self.policy.update(now, local_now, r, holding)
        if r.temperature_c is not None and r.temperature_c < self.settings["minimum_c"] and not self._last_low:
            self.runtime.note("Boiler onder ingestelde minimumtemperatuur; minimumregime krijgt voorrang op optimalisatie.")
        self._last_low = decision.low_temperature
        if self.pending:
            p = self.pending
            obj = self._state(self.config["target_entity"])
            stamp = getattr(obj, "last_reported", obj.last_updated).timestamp() if obj else 0
            if r.actual_target_c is not None and abs(r.actual_target_c - p["target"]) < 0.05 and stamp >= p["issued_wall"]:
                self.pending = None
                self.owned_target = None if p["release"] else p["target"]
                self.last_success = {"target_c": p["target"], "time": datetime.now().astimezone().isoformat()}
                self.runtime.note(f"Boiler: doel {p['target']:g} °C bevestigd (niet hetzelfde als opgewarmd).")
                await self._save()
            elif now - p["issued"] >= self.settings["ack_timeout_s"]:
                await self._mark_fault("Boileropdracht niet bevestigd; handmatige controle vereist")
            else:
                self.status = "Wacht op terugmelding boilerdoel"
                return False
        if self.needs_review or self.fault or self.manual_hold:
            self.status = self.fault or ("Boilercontrole na herstart vereist" if self.needs_review else "Handmatig overgenomen; hervat pas na boilercontrole")
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
            self.status = "Doel extern gewijzigd: boiler met rust gelaten"
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
            if releasing:
                self.owned_target = None
            else:
                self.owned_target = desired
            self.status = "Basisdoel vrijgegeven; boiler niet uitgeschakeld" if releasing else decision.reason
            self.runtime.store.async_delay_save(self.runtime._snapshot, 1)
            return False
        if not allow_command:
            self.status = decision.reason + "; wacht op andere regelopdracht"
            return False
        return await self._send(now, desired, releasing, decision.reason)

    async def _send(self, now, desired, release, reason):
        rt = self.runtime
        self.owned_target = desired
        self.pending = {"target": desired, "issued": now, "issued_wall": time.time(), "release": release}
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
            self.policy.reset_stability()
            await self._save()
        await self.runtime.tick()

    async def set_number(self, key, value):
        if key not in DHW_NUMBERS:
            raise HomeAssistantError("Onbekende boilerinstelling")
        async with self.runtime._lock:
            candidate = {**self.settings, key: float(value)}
            if validate_settings(candidate):
                raise HomeAssistantError("Ongeldige boilerinstelling: controleer minimum + differentie + buffer ≤ zon ≤ overschot, koellimiet en bereiken")
            targets = []
            if key in ("minimum_c", "tank_differential_c", "minimum_buffer_c"):
                targets.append(effective_base_target(candidate))
            elif key in ("solar_c", "surplus_c", "cooling_cap_c"):
                targets.append(float(value))
            for target in targets:
                if error := self.check_target(target):
                    raise HomeAssistantError(error)
            self.settings = candidate
            self.tunables[key] = float(value)
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
            self.fault = ""
            await self._save()
            self.runtime.note("Boiler handmatig overgenomen: GEEN temperatuur- of uitschakelopdracht.")
        await self.runtime.tick()

    def overview(self):
        d, r = self.policy.result, self.reading
        return {"configured": self.configured, "enabled": self.auto_enabled,
                "status": self.status, "reason": d.reason, "stage": d.stage,
                "temperature_c": r.temperature_c, "actual_target_c": r.actual_target_c,
                "proposed_target_c": d.target_c, "base_target_c": d.base_target_c,
                "minimum_c": self.settings["minimum_c"],
                "tank_differential_c": self.settings["tank_differential_c"],
                "minimum_buffer_c": self.settings["minimum_buffer_c"],
                "expected_restart_c": effective_base_target(self.settings) + self.settings["tank_differential_c"],
                "night": d.night, "cooling": r.cooling, "cooling_block": d.cooling_block,
                "capacity_block": d.capacity_block,
                "optional_import_headroom_w": r.optional_import_headroom_w,
                "low_temperature": d.low_temperature, "pending": bool(self.pending),
                "owned": self.owned_target is not None, "needs_review": self.needs_review,
                "manual_hold": self.manual_hold, "fault": self.fault,
                "pv_w": r.pv_w, "measured_solar_export_w": r.export_w,
                "before_boiler_w": r.before_boiler_w,
                "own_meter_available": self.exclusive_meter(),
                "remaining_s": d.remaining_s, "last_success": self.last_success,
                "hygiene_schedule": {"enabled": self.settings["hygiene_schedule_enabled"],
                    "weekdays": self.settings["hygiene_weekdays"], "start": self.settings["hygiene_start"],
                    "target_c": self.settings["hygiene_target_c"],
                    "guard_before_s": self.settings["hygiene_guard_before_s"],
                    "guard_after_s": self.settings["hygiene_guard_after_s"]},
                "switch_entity": self.runtime.entity_id("switch", "dhw_enabled"),
                "review_entity": self.runtime.entity_id("button", "dhw_review"),
                "takeover_entity": self.runtime.entity_id("button", "dhw_takeover"),
                "number_entities": {k: self.runtime.entity_id("number", "dhw_" + k) for k in DHW_NUMBERS},
                "settings": {k: self.settings[k] for k in (*DHW_NUMBERS, "night_enabled", "night_start", "night_end",
                    "rise_delay_s", "fall_delay_s", "cooling_clear_s", "cooling_detection",
                    "hygiene_schedule_enabled", "hygiene_weekdays", "hygiene_start", "hygiene_target_c",
                    "hygiene_guard_before_s", "hygiene_guard_after_s")}}
