"""Runtime adapter for generic multi-battery profiles.

Read-only by default.  Optional control is intentionally generic and must be
explicitly enabled both globally and per battery after the user confirms there is
no second controller writing the same setpoint.
"""
from __future__ import annotations
import asyncio
import math
import time
from homeassistant.exceptions import HomeAssistantError
from .battery_fleet import BATTERY_DEFAULTS, BATTERY_FLEET_DEFAULTS, BatteryReading, BatteryFleetState, aggregate, recommend, finite
from .wallbox import protected_entity
from .panasonic_authority import PanasonicCommandAuthority


class BatteryFleetManager:
    def __init__(self, runtime):
        self.runtime = runtime
        self.settings = {**BATTERY_FLEET_DEFAULTS, **runtime.entry.options.get("battery_fleet", {})}
        self.configs = {b["id"]: {**BATTERY_DEFAULTS, **b} for b in runtime.entry.options.get("batteries", [])}
        self.state = BatteryFleetState()
        self.last = []
        self.recommendation = None

    @property
    def configured(self):
        return bool(self.configs)

    @property
    def busy(self):
        return self.state.pending is not None

    def snapshot(self):
        return self.state.snapshot()

    def restore(self, data):
        self.state.restore(data)
        self.state.expected_numbers = {
            bid: expected for bid, expected in self.state.expected_numbers.items()
            if bid in self.configs and self.configs[bid].get("control_kind") == "signed_number"
            and self.configs[bid].get("number_entity") == expected["entity_id"]
        }

    def _source_number(self, entity_id, units, *, fresh=True):
        obj = self.runtime.hass.states.get(entity_id) if isinstance(entity_id, str) and entity_id else None
        stamp = self.runtime._reported_wall(obj)
        if obj is None or stamp is None or obj.attributes.get("unit_of_measurement") not in units:
            return None, 0.0
        if fresh and time.time() - stamp > self.runtime.settings.get("stale_s", 120):
            return None, stamp
        return finite(obj.state), stamp

    def _read_one(self, battery_id, cfg, *, include_faulted=False):
        soc_id = cfg.get("soc_entity", "")
        soc, _soc_stamp = self._source_number(soc_id, {"%"},
                                             fresh=not isinstance(soc_id, str) or not soc_id.startswith("input_number."))
        power_id = cfg.get("power_entity")
        power, stamp = self._source_number(power_id, {"W", "kW"})
        if power is not None:
            obj = self.runtime.hass.states.get(power_id)
            power = finite(power * (1000 if obj.attributes.get("unit_of_measurement") == "kW" else 1))
        if power is not None and cfg.get("power_sign") == "charge_positive":
            power = -power
        values = {key: finite(cfg.get(key)) for key in (
            "capacity_kwh", "min_soc_pct", "reserve_soc_pct", "max_soc_pct", "max_charge_w", "max_discharge_w")}
        limits_valid = (all(value is not None for value in values.values())
                        and values["capacity_kwh"] > 0
                        and 0 <= values["min_soc_pct"] <= values["reserve_soc_pct"] < values["max_soc_pct"] <= 100
                        and values["max_charge_w"] >= 0 and values["max_discharge_w"] >= 0)
        valid = bool(cfg.get("enabled", True) is True and soc is not None and 0 <= soc <= 100
                     and power is not None and limits_valid)
        controllable = bool(cfg.get("enabled", True) is True and cfg.get("control_enabled") is True
                            and cfg.get("exclusive_control_confirmed") is True
                            and cfg.get("control_kind") in ("signed_number", "scripts"))
        if not include_faulted:
            controllable = controllable and "restart" not in self.state.faults and battery_id not in self.state.faults
            if cfg.get("control_kind") == "signed_number":
                bounds = self._number_bounds(cfg)
                controllable = controllable and self._number_target(cfg) is not None and bounds is not None
                if controllable:
                    values["max_charge_w"] = min(values["max_charge_w"], max(0.0, -bounds[0])) if values["max_charge_w"] is not None else None
                    values["max_discharge_w"] = min(values["max_discharge_w"], max(0.0, bounds[1])) if values["max_discharge_w"] is not None else None
        return BatteryReading(
            id=battery_id, name=cfg.get("name", battery_id), valid=valid, soc_pct=soc,
            power_w=power, **values,
            controllable=controllable, phase_hint=cfg.get("phase_hint", "unknown"), power_stamp=stamp)

    def read(self):
        self.last = [self._read_one(i, c) for i, c in self.configs.items()]
        return self.last

    def _target_matches(self, reading, target):
        tol = finite(self.settings.get("target_tolerance_w", 250))
        return (tol is not None and tol >= 0 and reading.power_w is not None
                and abs(reading.power_w - target) <= tol)

    def _number_target(self, cfg):
        entity_id = cfg.get("number_entity")
        if not isinstance(entity_id, str) or not entity_id.startswith(("number.", "input_number.")):
            return None
        value, _stamp = self._source_number(entity_id, {"W", "kW"}, fresh=False)
        if value is None:
            return None
        obj = self.runtime.hass.states.get(entity_id)
        target = finite(value * (1000 if obj.attributes.get("unit_of_measurement") == "kW" else 1))
        return -target if target is not None and cfg.get("number_sign") == "charge_positive" else target

    def _number_bounds(self, cfg):
        obj = self.runtime.hass.states.get(cfg.get("number_entity"))
        if obj is None or self._number_target(cfg) is None:
            return None
        lo, hi, step = (finite(obj.attributes.get(key)) for key in ("min", "max", "step"))
        if (lo is None or hi is None or step is None or not lo <= 0 <= hi or step <= 0
                or finite(hi - lo) is None):
            return None
        zero_steps = finite(-lo / step)
        if zero_steps is None or abs(lo + round(zero_steps) * step) > 1e-9:
            return None
        factor = 1000 if obj.attributes.get("unit_of_measurement") == "kW" else 1
        lo, hi = finite(lo * factor), finite(hi * factor)
        if lo is None or hi is None:
            return None
        return (-hi, -lo) if cfg.get("number_sign") == "charge_positive" else (lo, hi)

    def _command_matches(self, cfg, reading, target):
        if not self._target_matches(reading, target):
            return False
        if cfg.get("control_kind") != "signed_number":
            return True
        native = self._number_target(cfg)
        if native is None:
            return False
        if abs(target) < 1e-6:
            return abs(native) < 1e-6
        obj = self.runtime.hass.states.get(cfg.get("number_entity"))
        step = finite(obj.attributes.get("step")) if obj else None
        if step is None or step <= 0:
            return False
        step *= 1000 if obj.attributes.get("unit_of_measurement") == "kW" else 1
        # A coarse actuator may round toward zero, never above the planned budget.
        return (native * target >= 0 and abs(native) <= abs(target) + 1e-6
                and abs(native - target) < step + 1e-6)

    async def _save(self):
        await self.runtime.store.async_save(self.runtime._snapshot())

    async def _fault(self, battery_id, reason):
        self.state.pending = None
        self.state.faults[battery_id] = reason
        self.runtime.note(f'{self.configs.get(battery_id, {}).get("name", battery_id)}: {reason}')
        await self._save()

    async def _manual_number_changes(self):
        changed = False
        for battery_id, expected in list(self.state.expected_numbers.items()):
            cfg = self.configs.get(battery_id)
            if not cfg or cfg.get("number_entity") != expected["entity_id"]:
                self.state.expected_numbers.pop(battery_id, None)
                continue
            target = self._number_target(cfg)
            if target is not None and abs(target - expected["target_w"]) > 1e-6:
                self.state.expected_numbers.pop(battery_id, None)
                self.state.faults[battery_id] = "Batterijsetpoint extern gewijzigd; bestaande bediening behouden, controle vereist"
                self.runtime.note(f'{cfg.get("name", battery_id)}: {self.state.faults[battery_id]}')
                changed = True
        if changed:
            await self._save()

    async def _send(self, battery_id, target_w):
        cfg = self.configs[battery_id]
        if (self.state.pending or "restart" in self.state.faults or battery_id in self.state.faults
                or self.settings.get("control_enabled") is not True or cfg.get("enabled", True) is not True
                or cfg.get("control_enabled") is not True or cfg.get("exclusive_control_confirmed") is not True):
            return False
        target_w = finite(target_w)
        if target_w is None:
            raise HomeAssistantError("Batterijdoel moet een eindig getal zijn")
        kind = cfg.get("control_kind", "read_only")
        binding_keys = ("enabled", "control_enabled", "exclusive_control_confirmed", "control_kind",
                        "number_entity", "number_sign", "charge_script", "discharge_script", "idle_script",
                        "power_sign", "soc_entity", "power_entity", "min_soc_pct", "reserve_soc_pct",
                        "max_soc_pct", "max_charge_w", "max_discharge_w")
        binding_snapshot = {key: cfg.get(key) for key in binding_keys}
        native_snapshot = None
        if kind == "read_only":
            return False
        if kind == "signed_number":
            entity_id = cfg.get("number_entity")
            if not isinstance(entity_id, str) or not entity_id.startswith(("number.", "input_number.")):
                raise HomeAssistantError("Batterij heeft geen vermogenssetpoint")
            if protected_entity(self.runtime.hass, self.runtime.wallbox_settings, entity_id):
                raise HomeAssistantError("Wallbox-entiteiten mogen niet als batterij-actuator worden gebruikt")
            value = target_w
            if cfg.get("number_sign") == "charge_positive":
                value = -value
            obj = self.runtime.hass.states.get(entity_id)
            if obj is None or self._number_target(cfg) is None:
                raise HomeAssistantError("Batterijsetpoint ontbreekt")
            unit = obj.attributes.get("unit_of_measurement")
            if unit == "kW": value /= 1000.0
            elif unit != "W": raise HomeAssistantError("Batterijsetpoint moet W of kW gebruiken")
            lo, hi, step = (finite(obj.attributes.get(key)) for key in ("min", "max", "step"))
            native_snapshot = (self._number_target(cfg), unit, lo, hi, step)
            if (lo is None or hi is None or step is None or lo > hi or step <= 0
                    or finite(hi - lo) is None):
                raise HomeAssistantError("Batterijsetpoint heeft geen geldige grenzen/stap")
            value = min(hi, max(lo, value))
            steps = (value - lo) / step
            if not math.isfinite(steps):
                raise HomeAssistantError("Batterijsetpoint heeft geen geldige grenzen/stap")
            # Quantize toward zero: never enlarge the planned charge/discharge
            # request merely because the actuator has a coarse step.
            count = (math.floor(steps + 1e-9) if value > 0 else
                     math.ceil(steps - 1e-9) if value < 0 else round(steps))
            value = lo + count * step
            value = min(hi, max(lo, value))
            actual_target = finite(value * (1000 if unit == "kW" else 1))
            if actual_target is None:
                raise HomeAssistantError("Batterijsetpoint is geen eindig vermogen")
            if cfg.get("number_sign") == "charge_positive":
                actual_target = -actual_target
            if target_w * actual_target < 0 or abs(actual_target) > abs(target_w) + 1e-6:
                raise HomeAssistantError("Batterijsetpoint kan de gevraagde richting/limiet niet veilig weergeven")
            if abs(target_w) < 1e-6 and abs(actual_target) > 1e-6:
                raise HomeAssistantError("Batterijsetpoint kan geen neutraal nuldoel weergeven")
            target_w = actual_target
            domain, action, data = entity_id.split(".")[0], "set_value", {"entity_id": entity_id, "value": value}
        elif kind == "scripts":
            if target_w > 1:
                script = cfg.get("discharge_script")
            elif target_w < -1:
                script = cfg.get("charge_script")
            else:
                script = cfg.get("idle_script")
            if not isinstance(script, str) or not script.startswith("script."):
                raise HomeAssistantError("Batterijscript ontbreekt voor gevraagde richting")
            if protected_entity(self.runtime.hass, self.runtime.wallbox_settings, script):
                raise HomeAssistantError("Wallbox-entiteiten mogen niet als batterij-actuator worden gebruikt")
            entity_id = script
            domain, action, data = "script", "turn_on", {
                "entity_id": script, "variables": {"power_w": abs(target_w),
                "power_kw": abs(target_w)/1000.0, "signed_power_w": target_w}}
        else:
            raise HomeAssistantError("Onbekend batterij-controltype")
        authority = PanasonicCommandAuthority(self.runtime)
        try:
            data = authority.assert_allowed(domain, action, entity_id,
                {key: value for key, value in data.items() if key != "entity_id"})
        except HomeAssistantError as err:
            await self._fault(battery_id, f"Batterijactuator niet toegestaan; niets verzonden: {err}")
            return False
        self.state.pending = {"id": battery_id, "target_w": target_w, "issued_wall": time.time(),
                              "entity_id": entity_id, "kind": kind}
        self.state.last_command_mono = time.monotonic()
        self.state.last_command_wall = self.state.pending["issued_wall"]
        self.runtime.last_issued = self.state.last_command_mono
        self.runtime.last_issued_wall = self.state.last_command_wall
        await self._save()  # Durable intent precedes the non-blocking physical call.
        # Native/manual events may arrive while persistence yields. Recheck the
        # selected binding and permission before dispatching the saved intent.
        current_cfg = self.configs.get(battery_id, {})
        unchanged = ({key: current_cfg.get(key) for key in binding_keys} == binding_snapshot
                     and self.settings.get("control_enabled") is True
                     and current_cfg.get("enabled", True) is True
                     and current_cfg.get("control_enabled") is True
                     and current_cfg.get("exclusive_control_confirmed") is True
                     and "restart" not in self.state.faults and battery_id not in self.state.faults
                     and not protected_entity(self.runtime.hass, self.runtime.wallbox_settings, entity_id))
        if kind == "signed_number":
            current_obj = self.runtime.hass.states.get(entity_id)
            current_attrs = current_obj.attributes if current_obj else {}
            current_snapshot = (self._number_target(current_cfg), current_attrs.get("unit_of_measurement"),
                                *(finite(current_attrs.get(key)) for key in ("min", "max", "step")))
            unchanged = unchanged and current_snapshot == native_snapshot
        if not unchanged:
            await self._fault(battery_id, "Batterijbediening veranderde tijdens opdrachtvoorbereiding; bestaande toestand behouden, geen write")
            return False
        self.runtime.note(f'{cfg.get("name",battery_id)}: batterijdoel {target_w:+.0f} W aangevraagd.')
        try:
            async with asyncio.timeout(20):
                # Persistence yielded: a script, registry scope or SG binding
                # may have changed. Revalidate the exact target at dispatch.
                data = authority.assert_allowed(domain, action, entity_id,
                    {key: value for key, value in data.items() if key != "entity_id"})
                await self.runtime.hass.services.async_call(domain, action, data, blocking=False)
        except (HomeAssistantError, TimeoutError, ValueError, TypeError) as err:
            await self._fault(battery_id, f"Onzekere batterijopdracht ({type(err).__name__}); controle vereist, geen herhaling")
        return True

    def removal_blocked(self):
        if self.state.pending:
            return True
        if self.settings.get("control_enabled") is not True:
            return False
        for bid, cfg in self.configs.items():
            reading = self._read_one(bid, cfg, include_faulted=True)
            if reading.controllable and not self._neutral(reading):
                return True
        return False

    def _neutral(self, reading):
        tol = float(self.settings.get("target_tolerance_w", 250))
        if reading.power_w is None or abs(reading.power_w) > tol:
            return False
        cfg = self.configs[reading.id]
        if cfg.get("control_kind") == "signed_number":
            target = self._number_target(cfg)
            return target is not None and abs(target) < 1e-6
        return True

    async def release_owned_targets(self):
        """Pause releases only acknowledged numeric targets still owned here."""
        if self.state.pending:
            return False
        await self._manual_number_changes()
        changed = False
        for bid, expected in list(self.state.expected_numbers.items()):
            cfg = self.configs.get(bid)
            if not cfg or cfg.get("control_kind") != "signed_number":
                continue
            reading = self._read_one(bid, cfg, include_faulted=True)
            native = self._number_target(cfg)
            if (reading.power_w is None or native is None
                    or abs(native - expected["target_w"]) > 1e-6):
                continue
            if abs(native) < 1e-6 and self._neutral(reading):
                self.state.expected_numbers.pop(bid, None)
                changed = True
                continue
            if "restart" in self.state.faults or bid in self.state.faults:
                continue
            if not reading.controllable or self._number_bounds(cfg) is None:
                continue
            return await self._send(bid, 0.0)
        if changed:
            await self._save()
        return False

    async def prepare_for_removal(self):
        """Move a SolarPilot-controlled battery to neutral/idle one at a time."""
        if self.state.pending or self.settings.get("control_enabled") is not True:
            return False
        await self._manual_number_changes()
        for bid, cfg in self.configs.items():
            reading = self._read_one(bid, cfg, include_faulted=True)
            if not reading.controllable:
                continue
            if reading.power_w is None:
                return False
            cfg = self.configs[reading.id]
            if (cfg.get("control_kind") == "signed_number" and
                    (self._number_target(cfg) is None or self._number_bounds(cfg) is None)):
                return False
            if not self._neutral(reading):
                if "restart" in self.state.faults or reading.id in self.state.faults:
                    return False
                return await self._send(reading.id, 0.0)
        # Runtime-only guard: once neutral, no more battery commands may be sent
        # during the pending removal session. Stored user configuration is not
        # rewritten merely because removal was prepared.
        self.settings["control_enabled"] = False
        self.state.expected_numbers.clear()
        await self._save()
        return False

    async def tick(self, *, grid_w, capacity_allowed_grid_w=None, allow_command=False):
        if not self.state.pending:
            await self._manual_number_changes()
        readings = self.read()
        # Keep real P1 for discharge/peak decisions; reduce only charging room
        # by the future commitment of devices temporarily outside control.
        isolated_reserve = max(0.0, finite(getattr(self.runtime, "isolated_reserve_w", 0)) or 0.0)
        allocation_settings = dict(self.settings)
        if isolated_reserve:
            allocation_settings["charge_reserve_w"] = (
                float(self.settings["charge_reserve_w"]) + isolated_reserve)
        self.recommendation = recommend(allocation_settings, readings, grid_w, capacity_allowed_grid_w)
        self.state.last_recommendation = self.recommendation.reason
        pending = self.state.pending
        if pending:
            reading = next((r for r in readings if r.id == pending.get("id")), None)
            cfg = self.configs.get(pending.get("id"), {})
            target, issued = finite(pending.get("target_w")), finite(pending.get("issued_wall"))
            if target is None or issued is None or not 0 < issued <= time.time() + 5:
                await self._fault(pending.get("id", "restart"), "Batterijopdrachtjournal ongeldig; controle vereist, geen herhaling")
                return False
            numeric = pending.get("kind", cfg.get("control_kind")) == "signed_number"
            native = self._number_target(cfg) if numeric else None
            native_matches = not numeric or (cfg.get("number_entity") == pending.get("entity_id", cfg.get("number_entity"))
                                             and native is not None and abs(native - target) < 1e-6)
            if (reading and reading.power_stamp > issued and native_matches
                    and self._target_matches(reading, target)):
                self.runtime.note(f'{reading.name}: latere HA-vermogenswaarneming past bij batterijdoel (geen rechtstreeks apparaat-ACK).')
                if numeric:
                    self.state.expected_numbers[reading.id] = {"entity_id": cfg["number_entity"], "target_w": target}
                self.state.pending = None
                await self._save()
            elif time.time() - issued > float(self.settings.get("ack_timeout_s", 120)):
                bid = pending.get("id")
                await self._fault(bid, "Batterijdoel niet tijdig bevestigd; automatische batterijbediening geblokkeerd, geen herhaling")
            return False
        if (not allow_command or self.settings.get("control_enabled") is not True or "restart" in self.state.faults
                or self.settings.get("strategy") == "advisory"
                or not self.recommendation or not self.recommendation.valid):
            return False
        min_interval = max(float(self.settings.get("command_min_interval_s", 30)), float(self.settings.get("settle_s", 30)))
        if self.state.last_command_mono is not None and time.monotonic() - self.state.last_command_mono < min_interval:
            return False
        if self.state.last_command_wall:
            grid_obj = self.runtime.hass.states.get(self.runtime.settings.get("grid_entity", ""))
            grid_stamp = self.runtime._reported_wall(grid_obj)
            if grid_stamp is None or grid_stamp <= self.state.last_command_wall:
                return False
        allocations = self.recommendation.control_allocations or {}
        # Release existing flow before transferring its target to another profile.
        # This keeps one-at-a-time commands from temporarily doubling the budget.
        def release_first(item):
            bid, target = item
            reading = next((r for r in readings if r.id == bid), None)
            cfg = self.configs.get(bid, {})
            native = self._number_target(cfg) if cfg.get("control_kind") == "signed_number" else None
            flows = (reading.power_w if reading else None, native)
            return 0 if any(flow is not None and (flow * target < 0 or abs(target) < abs(flow))
                            for flow in flows) else 1
        ordered = sorted(allocations.items(), key=release_first)
        for bid, target in ordered:
            if bid in self.state.faults:
                continue
            reading = next((r for r in readings if r.id == bid), None)
            if not reading or not reading.valid or not reading.controllable:
                continue
            cfg = self.configs[bid]
            if cfg.get("control_kind") == "signed_number" and self._number_target(cfg) is None:
                continue
            if self._command_matches(cfg, reading, target):
                continue
            # A direction change first releases the previous flow to neutral.
            if reading.power_w * target < 0:
                target = 0.0
            return await self._send(bid, target)
        return False

    def overview(self):
        readings = self.last or self.read()
        agg = aggregate(readings)
        rec = self.recommendation
        return {
            "enabled": bool(self.settings.get("enabled")),
            "control_enabled": bool(self.settings.get("control_enabled")),
            "strategy": self.settings.get("strategy", "loads_first"),
            "aggregate": agg,
            "recommendation_w": None if rec is None else round(rec.total_target_w, 1),
            "reason": "Nog geen batterijadvies" if rec is None else rec.reason,
            "pending": self.state.pending,
            "faults": dict(self.state.faults),
            "batteries": [{
                "id": r.id, "name": r.name, "valid": r.valid, "soc_pct": r.soc_pct, "power_w": r.power_w,
                "capacity_kwh": r.capacity_kwh, "controllable": r.controllable, "phase_hint": r.phase_hint,
                "control_kind": self.configs[r.id].get("control_kind", "read_only"),
                "control_enabled": bool(self.configs[r.id].get("control_enabled")),
                "exclusive_control_confirmed": bool(self.configs[r.id].get("exclusive_control_confirmed")),
            } for r in readings],
            "note": "Positief batterijvermogen = ontladen naar huis; negatief = laden. Regeling blijft read-only tot dubbele expliciete toestemming.",
        }
