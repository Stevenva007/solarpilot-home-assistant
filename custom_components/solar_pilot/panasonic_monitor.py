"""Read-only Panasonic observations; no command or target ownership."""
from __future__ import annotations
import hashlib
import json
import math
import time
from .sg_config import normalize_config, meter_sources_overlap


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
            "tank_temperature_entity", "tank_target_entity", "activity_entity", "zone_entities", "power_entity",
            "power_supply1_entity", "power_supply2_entity", "compressor_frequency_entity", "sg_status_entity"))

    def update_config(self, config):
        self.settings = normalize_config(config)
        for key in ("tank_temperature_entity", "tank_target_entity", "activity_entity", "power_entity",
                    "power_supply1_entity", "power_supply2_entity", "compressor_frequency_entity", "sg_status_entity"):
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

    def _operation(self, frequency, frequency_obj, zones, target, activity):
        """Presentation evidence only; a selected programme is not operation.

        A configured compressor source is the specific source of truth for its
        motion. Missing/stale/invalid frequency must not be hidden by a broader
        native heat request, and electrical watts never prove heat production.
        With no such binding, explicit fresh native actions can report activity
        without claiming that the compressor is turning or that SG caused it.
        """
        result = {"state": "unknown", "label": "Bedrijf onbekend", "evidence": "none",
                  "observed_at": None, "stale_s": self.settings["stale_s"]}
        if self.settings["compressor_frequency_entity"]:
            if frequency is None:
                return {**result, "label": "Compressorstatus onbekend"}
            return {**result, "state": "active" if frequency > 0 else "idle",
                    "label": "Compressor draait" if frequency > 0 else "Compressor staat stil",
                    "evidence": "compressor_frequency",
                    "observed_at": self._reported_stamp(frequency_obj)}

        active = {"heating", "preheating", "cooling", "precooling", "dhw", "hot_water"}
        inactive = {"idle", "off", "inactive", "none"}

        def action_stamp(obj):
            if obj is None or any(obj.attributes.get(key) for key in ("estimated", "is_estimated")):
                return None
            return self._reported_stamp(obj)

        readings = []
        for row in zones:
            action = str(row.get("action") or "").strip().casefold()
            readings.append((action, action_stamp(self._object(row["entity_id"]))))
        tank_action = ""
        if self.settings["tank_target_entity"].startswith(("water_heater.", "climate.")):
            tank_action = str(target.attributes.get("hvac_action", "")).strip().casefold() if target else ""
            readings.append((tank_action, action_stamp(target)))
        if self.settings["activity_entity"]:
            # A generic activity sensor may actually expose a chosen programme
            # or valve position. Bare DHW/HOT_WATER is not an operating action.
            raw_action = str(activity.state).strip().casefold() if activity else ""
            readings.append((raw_action if raw_action in (active - {"dhw", "hot_water"}) | inactive else "",
                             action_stamp(activity)))
        valid = [(action, stamp) for action, stamp in readings
                 if action in active | inactive and stamp is not None]
        current = [(action, stamp) for action, stamp in valid if action in active]
        if current:
            actions = {action for action, _stamp in current}
            tank_only = bool(tank_action in active and not any(
                str(row.get("action") or "").strip().casefold() in active for row in zones)
                and not (activity and str(activity.state).strip().casefold() in active))
            label = ("Panasonic meldt koeling" if actions <= {"cooling", "precooling"} else
                     "Panasonic meldt tapwateropwarming" if actions <= {"dhw", "hot_water"} or tank_only else
                     "Panasonic meldt verwarming" if actions <= {"heating", "preheating"} else
                     "Panasonic meldt actief bedrijf")
            return {**result, "state": "active", "label": label,
                    "evidence": "native_action", "observed_at": max(stamp for _action, stamp in current)}
        # Inactivity needs all configured action sources, not merely one idle
        # zone while another source is unavailable or only reports a programme.
        if readings and len(valid) == len(readings):
            return {**result, "state": "idle", "label": "Panasonic meldt rust",
                    "evidence": "native_action", "observed_at": min(stamp for _action, stamp in valid)}
        return result

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
                "available": obj is not None, "read_only": True,
                "observed_at": self._reported_stamp(obj)})
        activity = self._object(c["activity_entity"])
        native = [self.native_program.read(eid) for eid in c["zone_entities"]]
        programs = {row["program"] for row in native if row.get("fresh")}
        actions = [str(z["action"]).strip().casefold() if z["action"] is not None else None for z in zones]
        tank_action = str(target.attributes.get("hvac_action", "")).strip().casefold() if target else ""
        # A programme/action describes native context, never compressor motion.
        # Explicit cooling outranks a simultaneous tank action; conflicting
        # zone/programme evidence remains ambiguous rather than made safe.
        heat_actions = any(action in ("heating", "preheating") for action in actions)
        cool_actions = any(action in ("cooling", "precooling") for action in actions)
        fresh_programs = [row for row in native if row.get("fresh") and row.get("program") in ("heating", "cooling", "off")]
        native_heat = bool(fresh_programs) and all(row["program"] in ("heating", "off") for row in fresh_programs) and any(row["program"] == "heating" for row in fresh_programs)
        native_cool = any(row["program"] == "cooling" for row in fresh_programs)
        modes = [str(z["mode"]).strip().casefold() for z in zones]
        heat_modes = bool(zones) and all(z["available"] and mode in ("heat", "off") for z, mode in zip(zones, modes)) and "heat" in modes
        cool_modes = any(z["available"] and mode == "cool" for z, mode in zip(zones, modes))
        conflict = ((heat_actions and cool_actions) or (native_heat and (cool_actions or cool_modes))
                    or (native_cool and (heat_actions or heat_modes)) or ("heating" in programs and "cooling" in programs))
        context_reliable = False
        context_stamps = []
        if conflict:
            context, status = "heatpump_unknown", "Tegenstrijdige Panasonic-bedrijfscontext; extra koeling niet veilig uitgesloten"
        elif cool_actions or native_cool or cool_modes:
            context, status = "space_cooling", "Panasonic meldt ruimtekoeling als actie of gekozen programma"
            context_reliable = True
            context_stamps = [self._reported_stamp(self._object(eid)) for eid in c["zone_entities"]]
            context_stamps.extend(row.get("observed_at") for row in fresh_programs)
        elif heat_actions or native_heat or heat_modes:
            context, status = "space_heating", "Panasonic meldt ruimteverwarming als actie of gekozen programma"
            context_reliable = True
            context_stamps = [self._reported_stamp(self._object(eid)) for eid in c["zone_entities"]]
            context_stamps.extend(row.get("observed_at") for row in fresh_programs)
        elif tank_action in ("heating", "preheating", "heat", "dhw", "hot_water"):
            context, status = "tapwater_heating", "Panasonic meldt warmwateropwarming"
            context_reliable = True
            context_stamps = [self._reported_stamp(target)]
        elif self.configured and (any(not z["available"] for z in zones) or c["activity_entity"] and
                (not activity or str(activity.state).strip().casefold() not in ("idle", "off", "inactive", "none"))
                or c["tank_target_entity"].startswith(("water_heater.", "climate.")) and target is None
                or any(action is not None and action not in ("idle", "off", "inactive", "none", "") for action in actions)
                or tank_action not in ("idle", "off", "inactive", "none", "")):
            context, status = "heatpump_unknown", "Panasonic-activiteit niet betrouwbaar beschikbaar"
        else:
            context, status = "normal", "Panasonic regelt zelfstandig; geen actieve warmte- of koelactie bevestigd"
            context_stamps = [self._reported_stamp(self._object(eid)) for eid in c["zone_entities"]]
            if activity:
                context_stamps.append(self._reported_stamp(activity))
            if target and c["tank_target_entity"].startswith(("water_heater.", "climate.")):
                context_stamps.append(self._reported_stamp(target))
            context_reliable = bool(context_stamps)
            # AUTO may expose an idle action while the real native programme is
            # unknown. Losing its programme poll is unavailable evidence, not a
            # proven inactive episode that can reset a completed SG session.
            if any(mode in ("auto", "heat_cool") and not (row.get("fresh") and row.get("program") == "off")
                   for mode, row in zip(modes, native)):
                context_reliable = False
        # A missing configured zone or conflicting AUTO interpretation cannot
        # certify that an ON lease is safe from potential cooling.
        if any(not z["available"] for z in zones):
            context_reliable = False
        stamps = [stamp for stamp in context_stamps if self._number(stamp) is not None]
        context_stamp = min(stamps) if context_reliable and stamps else None
        if context_stamp is None:
            context_reliable = False
        every_zone_heat_only = bool(zones) and all(
            z["available"] and (row.get("fresh") and row.get("program") in ("heating", "off")
                                or mode in ("heat", "off"))
            for z, row, mode in zip(zones, native, modes))
        cooling_possible = not (context_reliable and not conflict and not cool_actions and not cool_modes
            and not native_cool and every_zone_heat_only and (native_heat or heat_modes))
        # The semantic signature excludes samples and optional-provider proof
        # arrival/disappearance. Those cannot create another request by themselves.
        signature_payload = [context,
                             [[z["entity_id"], str(z["mode"]).casefold(), z["action"]] for z in zones]]
        if context == "tapwater_heating":
            signature_payload.append([c["tank_target_entity"], tank_action])
        context_signature = hashlib.sha256(json.dumps(signature_payload, sort_keys=True,
            separators=(",", ":"), default=str).encode()).hexdigest() if context_reliable else None
        frequency_obj = self._object(c["compressor_frequency_entity"])
        frequency = self._number(frequency_obj.state) if frequency_obj else None
        if (not c["compressor_frequency_entity"].startswith("sensor.") or not frequency_obj
                or frequency_obj.attributes.get("unit_of_measurement") != "Hz"
                or any(frequency_obj.attributes.get(k) for k in ("estimated", "is_estimated"))
                or frequency is None or not 0 <= frequency <= 200):
            frequency = None
        compressor_running = None if frequency is None else frequency > 0
        sg_obj = self._object(c["sg_status_entity"])
        sg_value = str(sg_obj.state).strip().casefold() if sg_obj else "unknown"
        # The explicit read role names a received SG-status source. Numeric
        # capacity codes are deliberately not guessed across provider enums.
        active_states, inactive_states = {"active", "on"}, {"inactive", "off"}
        if (c["sg_status_entity"] == c["entity_id"] or meter_sources_overlap(self.runtime.hass, c["sg_status_entity"], c["entity_id"])
                or not c["sg_status_entity"].startswith(("sensor.", "binary_sensor."))
                or not sg_obj or sg_obj.attributes.get("unit_of_measurement")
                or any(sg_obj.attributes.get(k) for k in ("estimated", "is_estimated"))):
            sg_value = "unknown"
        sg_status = "active" if sg_value in active_states else "inactive" if sg_value in inactive_states else "unknown"
        from .heatpump_budget import heatpump_power
        power = heatpump_power(self.runtime)
        from .power_activity import power_activity
        read_tank_action = getattr(self.native_program, "read_tank_action", None)
        native_tank_action = read_tank_action(c["tank_target_entity"]) if callable(read_tank_action) else {}
        # Automatic siblings belong only to presentation. They never amend
        # configured programme sources, native context, cooling or SG rights.
        discover = getattr(self.native_program, "display_sources", None)
        display_sources = discover([c["tank_target_entity"], c["tank_temperature_entity"],
            c["activity_entity"], *c["zone_entities"]]) if callable(discover) else {}
        display_tank_entity = (c["tank_target_entity"] if c["tank_target_entity"].startswith(("water_heater.", "climate."))
                               else display_sources.get("tank_entity", ""))
        is_display_zone = getattr(self.native_program, "is_display_zone", None)
        if callable(is_display_zone) and is_display_zone(display_tank_entity):
            display_tank_entity = display_sources.get("tank_entity", "")
        display_tank_obj = self._object(display_tank_entity)
        display_zone_ids = list(dict.fromkeys([*c["zone_entities"], *display_sources.get("zone_entities", [])]))
        display_zones = []
        for eid in display_zone_ids:
            obj = self._object(eid)
            attrs = getattr(obj, "attributes", {}) or {}
            display_zones.append({"entity_id": eid, "name": attrs.get("friendly_name", eid),
                "temperature_c": self._temperature(obj, attrs.get("current_temperature"), native=True),
                "target_c": self._temperature(obj, attrs.get("temperature"), native=True),
                "mode": obj.state if obj else "unknown", "action": attrs.get("hvac_action"),
                "available": obj is not None, "read_only": True, "observed_at": self._reported_stamp(obj),
                "action_valid": not any(attrs.get(key) for key in ("estimated", "is_estimated")),
                "automatic": eid not in c["zone_entities"]})
        read_device_action = getattr(self.native_program, "read_device_action", None)
        device_actions = [read_device_action(eid) for eid in display_zone_ids] if callable(read_device_action) else []
        display_tank_action = (native_tank_action if display_tank_entity == c["tank_target_entity"] else
                              read_tank_action(display_tank_entity) if callable(read_tank_action) else {})
        read_tank_context = getattr(self.native_program, "read_tank_context", None)
        route_context = read_tank_context(display_tank_entity) if callable(read_tank_context) else {}
        display_programs = [*native, *[{"program": row.get("program"), "fresh": row.get("fresh"),
            "observed_at": row.get("observed_at")} for row in device_actions if row.get("program")]]
        defrost_entity = display_sources.get("defrost_entity", "")
        defrost_obj = self._object(defrost_entity)
        defrost_attrs = getattr(defrost_obj, "attributes", {}) or {}
        defrost_state = str(defrost_obj.state).casefold() if defrost_obj else "unknown"
        if any(defrost_attrs.get(key) for key in ("estimated", "is_estimated")):
            defrost_state = "unknown"
        defrost = {"state": "active" if defrost_state == "on" else "inactive" if defrost_state == "off" else "unknown",
                   "label": "Panasonic meldt ontdooien" if defrost_state == "on" else "Geen ontdooimelding" if defrost_state == "off" else "Ontdooistatus onbekend",
                   "source": "aquarea_entity" if defrost_state in ("on", "off") else "none",
                   "entity_id": defrost_entity, "observed_at": self._reported_stamp(defrost_obj) if defrost_state in ("on", "off") else None,
                   "stale_s": c["stale_s"]}
        defrost_proofs = [row for row in [display_tank_action, *device_actions]
                          if row.get("fresh") is True and row.get("defrost_active") is True
                          and self._object(row.get("entity_id")) is not None]
        if defrost_proofs:
            defrost.update(state="active", label="Panasonic meldt ontdooien", source="aquarea_poll",
                           observed_at=min(min(row["observed_at"], self._reported_stamp(self._object(row["entity_id"])))
                                           for row in defrost_proofs))
        from .power_activity import task_observations
        native_task, task_context = task_observations(c, tank=display_tank_obj, tank_entity=display_tank_entity,
            tank_stamp=self._reported_stamp(display_tank_obj), tank_action=display_tank_action,
            device_actions=device_actions, zones=display_zones, native_programs=display_programs,
            route_context=route_context, defrost=defrost)
        power_display = power_activity(power, c, tank=display_tank_obj, tank_entity=display_tank_entity,
            tank_stamp=self._reported_stamp(display_tank_obj), tank_action=display_tank_action,
            device_actions=device_actions, zones=display_zones, native_programs=display_programs,
            context=context, context_reliable=context_reliable, context_stamp=context_stamp, conflict=conflict,
            native_actual=native_task, display_context=task_context, defrost=defrost)
        display_attrs = getattr(display_tank_obj, "attributes", {}) or {}
        display_temperature = self._temperature(display_tank_obj, display_attrs.get("current_temperature"), tank=True, native=True)
        display_target = self._temperature(display_tank_obj, display_attrs.get("temperature"), tank=True, native=True)
        display_tank = {"entity_id": display_tank_entity, "temperature_c": display_temperature, "target_c": display_target,
            "temperature_stamp": self._reported_stamp(display_tank_obj) if display_temperature is not None else None,
            "target_stamp": self._reported_stamp(display_tank_obj) if display_target is not None else None,
            "mode": display_attrs.get("operation_mode", display_tank_obj.state if display_tank_obj else "unknown"),
            "action": display_attrs.get("hvac_action"), "available": display_tank_obj is not None,
            "observed_at": self._reported_stamp(display_tank_obj), "read_only": True,
            "automatic": display_tank_entity != c["tank_target_entity"]}
        return {"configured": self.configured, "read_only": True, "temperature_c": temp,
            "temperature_entity": c["tank_temperature_entity"],
            "temperature_stamp": self._reported_stamp(tank) if temp is not None else None,
            "target_c": target_c, "power_w": power["watts"], "power_stamp": power["measured_wall"],
            "target_stamp": self._reported_stamp(target) if target_c is not None else None,
            "target_observed_at": self._reported_stamp(target) if target_c is not None else None,
            "source_stale_s": c["stale_s"], "power_observed_at": power["measured_wall"],
            "power_kind": "measured" if power["valid"] else "unknown",
            "power_scope": power["meter_scope"], "power_entity": c["power_entity"],
            "power_complete": power["complete"], "power_reason": power["reason"],
            "power_supply1_w": power["supplies"].get("supply1", {}).get("watts"),
            "power_supply2_w": power["supplies"].get("supply2", {}).get("watts"),
            "power_supply1_valid": power["supplies"].get("supply1", {}).get("valid", False),
            "power_supply2_valid": power["supplies"].get("supply2", {}).get("valid", False),
            "power_supply1_observed_at": power["supplies"].get("supply1", {}).get("measured_wall"),
            "power_supply2_observed_at": power["supplies"].get("supply2", {}).get("measured_wall"),
            "power_supply1_entity": c["power_supply1_entity"], "power_supply2_entity": c["power_supply2_entity"],
            "compressor_running": compressor_running, "compressor_frequency_hz": frequency,
            "compressor_stamp": self._reported_stamp(frequency_obj) if frequency is not None else None,
            "compressor_frequency_observed_at": self._reported_stamp(frequency_obj) if frequency is not None else None,
            "compressor_entity": c["compressor_frequency_entity"],
            "sg_status": sg_status, "sg_status_confirmed": sg_status != "unknown",
            "sg_status_stamp": self._reported_stamp(sg_obj) if sg_status != "unknown" else None,
            "sg_status_observed_at": self._reported_stamp(sg_obj) if sg_status != "unknown" else None,
            "sg_status_entity": c["sg_status_entity"], "sg_effect_confirmed": False,
            "zones": zones, "program": next(iter(programs)) if len(programs) == 1 else None,
            "activity": activity.state if activity else None,
            "operation": self._operation(frequency, frequency_obj, zones, target, activity),
            "power_activity": power_display,
            "native_task": native_task, "task_context": task_context, "defrost": defrost,
            "display_tank": display_tank, "display_zones": display_zones, "display_sources": display_sources,
            "context": context, "context_reliable": context_reliable, "context_stamp": context_stamp,
            "context_signature": context_signature, "cooling_possible": cooling_possible, "status": status,
            "note": "SG vraagt zonneboost. Het normale Panasonic-doel kan ongewijzigd blijven; dit bewijst geen relaisfout."}

    def learning_overview(self):
        # The exact historical model is retained privately and in full exports.
        # Live state must stay bounded rather than broadcasting the archive.
        return {"read_only": True, "archive_available": bool(self.learning_archive),
                "status": "Bestaande klimaatleerdata bewaard; geen automatische ruimtebediening"}
