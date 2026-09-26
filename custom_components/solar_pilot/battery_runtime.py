"""Runtime adapter for generic multi-battery profiles.

Read-only by default.  Optional control is intentionally generic and must be
explicitly enabled both globally and per battery after the user confirms there is
no second controller writing the same setpoint.
"""
from __future__ import annotations
import time
from homeassistant.exceptions import HomeAssistantError
from .battery_fleet import BATTERY_DEFAULTS, BATTERY_FLEET_DEFAULTS, BatteryReading, BatteryFleetState, aggregate, recommend
from .wallbox import protected_entity


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

    def _read_one(self, battery_id, cfg):
        soc = self.runtime._number(cfg.get("soc_entity")) if cfg.get("soc_entity") else None
        power, _stamp = self.runtime._power(cfg.get("power_entity"), self.runtime.settings.get("stale_s", 120)) if cfg.get("power_entity") else (None, 0)
        if power is not None and cfg.get("power_sign") == "charge_positive":
            power = -power
        valid = bool(cfg.get("enabled", True) and soc is not None and 0 <= soc <= 100 and power is not None)
        controllable = bool(cfg.get("control_enabled") and cfg.get("exclusive_control_confirmed") and cfg.get("control_kind") != "read_only")
        return BatteryReading(
            id=battery_id, name=cfg.get("name", battery_id), valid=valid, soc_pct=soc,
            power_w=power, capacity_kwh=float(cfg.get("capacity_kwh", 0) or 0),
            min_soc_pct=float(cfg.get("min_soc_pct", 0) or 0), reserve_soc_pct=float(cfg.get("reserve_soc_pct", 0) or 0),
            max_soc_pct=float(cfg.get("max_soc_pct", 100) or 100),
            max_charge_w=float(cfg.get("max_charge_w", 0) or 0), max_discharge_w=float(cfg.get("max_discharge_w", 0) or 0),
            controllable=controllable, phase_hint=cfg.get("phase_hint", "unknown"))

    def read(self):
        self.last = [self._read_one(i, c) for i, c in self.configs.items()]
        return self.last

    def _target_matches(self, reading, target):
        tol = float(self.settings.get("target_tolerance_w", 250))
        if target > tol:
            return reading.power_w is not None and reading.power_w >= max(tol, target - tol)
        if target < -tol:
            return reading.power_w is not None and reading.power_w <= min(-tol, target + tol)
        return reading.power_w is not None and abs(reading.power_w) <= tol

    async def _send(self, battery_id, target_w):
        cfg = self.configs[battery_id]
        if not (self.settings.get("control_enabled") and cfg.get("control_enabled") and cfg.get("exclusive_control_confirmed")):
            return False
        kind = cfg.get("control_kind", "read_only")
        if kind == "read_only":
            return False
        if protected_entity(self.runtime.hass, self.runtime.wallbox_settings, cfg.get("number_entity", "")):
            raise HomeAssistantError("Wallbox-entiteiten mogen niet als batterij-actuator worden gebruikt")
        if kind == "signed_number":
            entity_id = cfg.get("number_entity")
            if not entity_id:
                raise HomeAssistantError("Batterij heeft geen vermogenssetpoint")
            value = float(target_w)
            if cfg.get("number_sign") == "charge_positive":
                value = -value
            obj = self.runtime.hass.states.get(entity_id)
            if obj is None:
                raise HomeAssistantError("Batterijsetpoint ontbreekt")
            unit = obj.attributes.get("unit_of_measurement")
            if unit == "kW": value /= 1000.0
            elif unit != "W": raise HomeAssistantError("Batterijsetpoint moet W of kW gebruiken")
            lo, hi = obj.attributes.get("min"), obj.attributes.get("max")
            if lo is not None: value = max(float(lo), value)
            if hi is not None: value = min(float(hi), value)
            await self.runtime.hass.services.async_call("number", "set_value", {"entity_id": entity_id, "value": value}, blocking=False)
        elif kind == "scripts":
            if target_w > 1:
                script = cfg.get("discharge_script")
            elif target_w < -1:
                script = cfg.get("charge_script")
            else:
                script = cfg.get("idle_script")
            if not script:
                raise HomeAssistantError("Batterijscript ontbreekt voor gevraagde richting")
            await self.runtime.hass.services.async_call("script", "turn_on", {
                "entity_id": script,
                "variables": {"power_w": abs(float(target_w)), "power_kw": abs(float(target_w))/1000.0,
                              "signed_power_w": float(target_w)}}, blocking=False)
        else:
            raise HomeAssistantError("Onbekend batterij-controltype")
        self.state.pending = {"id": battery_id, "target_w": float(target_w), "issued_wall": time.time()}
        self.state.last_command_mono = time.monotonic()
        self.runtime.note(f'{cfg.get("name",battery_id)}: batterijdoel {target_w:+.0f} W aangevraagd.')
        return True

    def removal_blocked(self):
        if self.state.pending:
            return True
        if not self.settings.get("control_enabled"):
            return False
        tol = float(self.settings.get("target_tolerance_w", 250))
        for reading in self.read():
            if reading.controllable and reading.power_w is not None and abs(reading.power_w) > tol:
                return True
        return False

    async def prepare_for_removal(self):
        """Move a SolarPilot-controlled battery to neutral/idle one at a time."""
        if self.state.pending or not self.settings.get("control_enabled"):
            return False
        tol = float(self.settings.get("target_tolerance_w", 250))
        for reading in self.read():
            if not reading.controllable or reading.power_w is None:
                continue
            if abs(reading.power_w) > tol:
                return await self._send(reading.id, 0.0)
        # Runtime-only guard: once neutral, no more battery commands may be sent
        # during the pending removal session. Stored user configuration is not
        # rewritten merely because removal was prepared.
        self.settings["control_enabled"] = False
        return False

    async def tick(self, *, grid_w, capacity_allowed_grid_w=None, allow_command=False):
        readings = self.read()
        self.recommendation = recommend(self.settings, readings, grid_w, capacity_allowed_grid_w)
        self.state.last_recommendation = self.recommendation.reason
        pending = self.state.pending
        if pending:
            reading = next((r for r in readings if r.id == pending.get("id")), None)
            if reading and self._target_matches(reading, float(pending.get("target_w", 0))):
                self.runtime.note(f'{reading.name}: batterijopdracht bevestigd.')
                self.state.pending = None
            elif time.time() - float(pending.get("issued_wall", time.time())) > float(self.settings.get("ack_timeout_s", 120)):
                bid = pending.get("id")
                self.state.faults[bid] = "Batterijdoel niet tijdig bevestigd; automatische batterijbediening geblokkeerd"
                self.state.pending = None
                self.runtime.note(f'{self.configs.get(bid,{}).get("name",bid)}: batterijopdracht niet bevestigd; controle vereist.')
            return False
        if (not allow_command or not self.settings.get("control_enabled") or self.settings.get("strategy") == "advisory"
                or not self.recommendation or not self.recommendation.valid):
            return False
        min_interval = max(float(self.settings.get("command_min_interval_s", 30)), float(self.settings.get("settle_s", 30)))
        if time.monotonic() - self.state.last_command_mono < min_interval:
            return False
        for bid, target in (self.recommendation.control_allocations or {}).items():
            if bid in self.state.faults:
                continue
            reading = next((r for r in readings if r.id == bid), None)
            if not reading or not reading.controllable:
                continue
            if self._target_matches(reading, target):
                continue
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
