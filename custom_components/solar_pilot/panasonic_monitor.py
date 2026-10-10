"""Read-only Panasonic observations; no command or target ownership."""
from __future__ import annotations
import math
import time
from .sg_config import normalize_config


class PanasonicMonitor:
    def __init__(self, runtime, config=None):
        self.runtime = runtime
        self.update_config(config)
        self.learning_archive = {}
        from .native_program import NativeClimateProgram
        self.native_program = NativeClimateProgram(runtime)

    @property
    def configured(self):
        return any(self.settings.get(k) for k in (
            "tank_temperature_entity", "tank_target_entity", "activity_entity", "zone_entities", "power_entity"))

    def update_config(self, config):
        self.settings = normalize_config(config)
        for key in ("tank_temperature_entity", "tank_target_entity", "activity_entity", "power_entity"):
            if not isinstance(self.settings.get(key), str):
                self.settings[key] = ""
        zones = self.settings.get("zone_entities")
        self.settings["zone_entities"] = [eid for eid in zones if isinstance(eid, str) and eid.startswith("climate.")] if isinstance(zones, list) else []
        stale = self._number(self.settings.get("stale_s"))
        self.settings["stale_s"] = stale if stale is not None and 15 <= stale <= 600 else 120

    def _object(self, entity_id):
        obj = self.runtime.hass.states.get(entity_id) if entity_id else None
        if obj is None or str(obj.state).strip().casefold() in ("unknown", "unavailable", "") or obj.attributes.get("restored"):
            return None
        return obj if self._reported_stamp(obj) is not None else None

    def _reported_stamp(self, obj):
        if obj is None:
            return None
        stamp = getattr(obj, "last_reported", None)
        if stamp is None:
            stamp = getattr(obj, "last_updated", None)
        try:
            timestamp = stamp.timestamp()
            if (isinstance(timestamp, bool) or not isinstance(timestamp, (int,float))
                    or not math.isfinite(timestamp) or not -5 <= time.time()-timestamp <= self.settings["stale_s"]):
                return None
        except (AttributeError, TypeError, ValueError, OverflowError, OSError):
            return None
        return timestamp

    @staticmethod
    def _number(value):
        if isinstance(value, bool):
            return None
        try:
            value = float(value)
            return value if math.isfinite(value) else None
        except (ValueError, TypeError, OverflowError):
            return None

    def _temperature(self, obj, value, *, tank=False, native=False):
        number = self._number(value)
        if obj is None or number is None:
            return None
        unit = obj.attributes.get("temperature_unit") if native else obj.attributes.get("unit_of_measurement")
        if native and not unit:
            unit = getattr(getattr(getattr(self.runtime.hass, "config", None), "units", None), "temperature_unit", None)
        if unit in ("°F", "F"):
            number = (number-32)*5/9
        elif unit not in ("°C", "C"):
            return None
        return round(number, 2) if (0 if tank else -50) <= number <= (100 if tank else 80) else None

    def overview(self):
        c = self.settings
        tank = self._object(c["tank_temperature_entity"])
        target = self._object(c["tank_target_entity"])
        temp = self._temperature(tank, tank.attributes.get("current_temperature") if tank and
            c["tank_temperature_entity"].startswith(("water_heater.", "climate.")) else tank.state if tank else None,
            tank=True, native=c["tank_temperature_entity"].startswith(("water_heater.", "climate.")))
        target_c = self._temperature(target, target.attributes.get("temperature") if target and
            c["tank_target_entity"].startswith(("water_heater.", "climate.")) else target.state if target else None,
            tank=True, native=c["tank_target_entity"].startswith(("water_heater.", "climate.")))
        zones = []
        for eid in c["zone_entities"]:
            obj = self._object(eid)
            zones.append({"entity_id": eid, "name": obj.attributes.get("friendly_name", eid) if obj else eid,
                "temperature_c": self._temperature(obj, obj.attributes.get("current_temperature"), native=True) if obj else None,
                "target_c": self._temperature(obj, obj.attributes.get("temperature"), native=True) if obj else None,
                "mode": obj.state if obj else "unknown",
                "action": obj.attributes.get("hvac_action") if obj else None,
                "available": obj is not None, "read_only": True})
        activity = self._object(c["activity_entity"])
        native = [self.native_program.read(eid) for eid in c["zone_entities"]]
        programs = {row["program"] for row in native if row.get("fresh")}
        actions = [str(z["action"]).strip().casefold() if z["action"] is not None else None for z in zones]
        tank_action = str(target.attributes.get("hvac_action", "")).strip().casefold() if target else ""
        if tank_action in ("heating", "preheating", "heat", "dhw", "hot_water"):
            context, status = "tapwater_heating", "Panasonic meldt warmwateropwarming"
        elif any(action in ("cooling", "precooling") for action in actions):
            context, status = "space_cooling", "Panasonic meldt ruimtekoeling"
        elif any(action in ("heating", "preheating") for action in actions):
            context, status = "space_heating", "Panasonic meldt ruimteverwarming"
        elif self.configured and (any(not z["available"] for z in zones) or c["activity_entity"] and
                (not activity or str(activity.state).strip().casefold() not in ("idle", "off", "inactive", "none"))
                or c["tank_target_entity"].startswith(("water_heater.", "climate.")) and target is None
                or any(action is not None and action not in ("idle", "off", "inactive", "none", "") for action in actions)
                or tank_action not in ("idle", "off", "inactive", "none", "")):
            context, status = "heatpump_unknown", "Panasonic-activiteit niet betrouwbaar beschikbaar"
        else:
            context, status = "normal", "Panasonic regelt zelfstandig; geen actieve warmte- of koelactie bevestigd"
        from .heatpump_budget import heatpump_power
        power = heatpump_power(self.runtime)
        return {"configured": self.configured, "read_only": True, "temperature_c": temp,
            "temperature_entity": c["tank_temperature_entity"],
            "temperature_stamp": self._reported_stamp(tank) if temp is not None else None,
            "target_c": target_c, "power_w": power["watts"],
            "power_kind": "measured" if power["valid"] else "unknown",
            "power_scope": c["power_scope"], "power_entity": c["power_entity"],
            "zones": zones, "program": next(iter(programs)) if len(programs) == 1 else None,
            "activity": activity.state if activity else None,
            "context": context, "status": status,
            "note": "SG vraagt zonneboost. Het normale Panasonic-doel kan ongewijzigd blijven; dit bewijst geen relaisfout."}

    def learning_overview(self):
        # The exact historical model is retained privately and in full exports.
        # Live state must stay bounded rather than broadcasting the archive.
        return {"read_only": True, "archive_available": bool(self.learning_archive),
                "status": "Bestaande klimaatleerdata bewaard; geen automatische ruimtebediening"}
