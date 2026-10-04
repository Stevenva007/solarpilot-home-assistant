"""Home Assistant runtime wrapper for slow Panasonic AUTO/coast planning."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import time
from zoneinfo import ZoneInfo

from homeassistant.core import Context, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event

from .thermal_climate import (
    SMART_CLIMATE_DEFAULTS,
    CLIMATE_SETTING_SPECS,
    SmartClimateState,
    decide_mode,
    finite,
)
from .wallbox import protected_entity


class SmartClimateManager:
    def __init__(self, runtime):
        self.runtime = runtime
        self.settings = {**SMART_CLIMATE_DEFAULTS, **runtime.entry.options.get("smart_climate", {})}
        self.state = SmartClimateState()
        self.last_zones = []
        self.last_outside = None
        self.last_forecast_error = ""
        self.last_weather_corrections = []
        self.last_solar_hourly = []
        self.manual_off = set()
        self.zone_holds = {}
        self.pending_commands = {}
        self.observed_modes = {}
        self.zone_command_walls = {}
        self.command_faults = {}
        self.cancelled_auto = {}
        self._contexts = {}
        self._unsub_states = None
        self._unsub_services = None
        self._started = False
        self._feedback_batches = {}

    COMMAND_TIMEOUT_S = 180
    REPORT_DELAY_S = 10

    @property
    def configured(self):
        return bool(self.settings.get("zone_entities"))

    @property
    def busy(self):
        return bool(self.pending_commands)

    def snapshot(self):
        return {**self.state.snapshot(), "manual_off": sorted(self.manual_off),
                "zone_holds": dict(self.zone_holds),
                "pending_commands": deepcopy(self.pending_commands),
                "zone_command_walls": dict(self.zone_command_walls),
                "command_faults": dict(self.command_faults), "cancelled_auto": dict(self.cancelled_auto)}

    def restore(self, data):
        self.state.restore(data, self.settings.get("zone_entities", []), self.settings)
        if not isinstance(data, dict):
            return
        selected = set(self.settings.get("zone_entities", []) or [])
        maps = {key: data.get(key) if isinstance(data.get(key), dict) else {} for key in (
            "zone_holds", "zone_command_walls", "command_faults", "pending_commands", "cancelled_auto")}
        self.state.expected_mode = {eid: mode for eid, mode in self.state.expected_mode.items()
                                    if eid in selected and mode in ("off", "auto")}
        manual = data.get("manual_off")
        self.manual_off = {eid for eid in (manual if isinstance(manual, (list, tuple, set)) else [])
                           if isinstance(eid, str) and eid in selected}
        now = time.time()
        limit = now + float(self.settings.get("manual_hold_h", 12)) * 3600
        self.zone_holds = {eid: min(limit, value) for eid, raw in maps["zone_holds"].items()
                           if eid in selected and (value := finite(raw)) is not None and value > now}
        self.zone_command_walls = {eid: value for eid, raw in maps["zone_command_walls"].items()
                                   if eid in selected and (value := finite(raw)) is not None and 0 <= value <= now}
        self.command_faults = {eid: str(reason) for eid, reason in maps["command_faults"].items()
                               if eid in selected and reason}
        self.pending_commands = {}
        self.cancelled_auto = {eid: value for eid, raw in maps["cancelled_auto"].items()
                               if eid in selected and (value := finite(raw)) is not None and 0 <= value <= now + 5}
        for eid, raw in maps["pending_commands"].items():
            if eid not in selected:
                continue
            issued = finite(raw.get("issued_wall")) if isinstance(raw, dict) else None
            if (not isinstance(raw, dict) or raw.get("mode") not in ("off", "auto")
                    or issued is None or not 0 < issued <= now):
                if self.state.expected_mode.get(eid) == "off":
                    self.manual_off.add(eid)
                self.state.expected_mode.pop(eid, None)
                self.command_faults[eid] = "Opgeslagen klimaatopdracht ongeldig; geen opdracht herhaald"
                self.zone_holds[eid] = limit
                continue
            # Feedback batches exist only in memory. Do not restore their group
            # or arbitrary damaged journal fields into the operational command.
            self.pending_commands[eid] = {"mode": raw["mode"], "issued_wall": issued,
                                          "restart_wall": now, "expires_wall": now + self.COMMAND_TIMEOUT_S}
            context_id = raw.get("context_id")
            if isinstance(context_id, str) and context_id:
                self.pending_commands[eid]["context_id"] = context_id
                self._contexts[context_id] = now + self.COMMAND_TIMEOUT_S
        if "pending_commands" in data and not isinstance(data.get("pending_commands"), dict):
            for eid in list(self.state.expected_mode):
                if self.state.expected_mode[eid] == "off":
                    self.manual_off.add(eid)
                self.state.expected_mode.pop(eid, None)
                self.zone_holds[eid] = limit
                self.command_faults[eid] = "Klimaatopdrachtjournal ongeldig; eigendom niet automatisch hervat"

    def start(self):
        self.close()
        self._started = True
        ids = list(self.settings.get("zone_entities", []) or [])
        if ids:
            self._unsub_states = async_track_state_change_event(self.runtime.hass, ids, self.on_event)
        bus = getattr(self.runtime.hass, "bus", None)
        if bus is not None:
            self._unsub_services = bus.async_listen("call_service", self.on_service_event)

    def close(self):
        for unsubscribe in (self._unsub_states, self._unsub_services):
            if unsubscribe is not None:
                unsubscribe()
        self._unsub_states = self._unsub_services = None
        self._started = False

    def _dirty(self):
        self.runtime.store.async_delay_save(self.runtime._snapshot, 1)

    def _manual_mode(self, entity_id, mode):
        """An external choice revokes only this zone's control ownership."""
        if mode == "off" and (self.pending_commands.get(entity_id, {}).get("mode") == "auto"
                              or self.state.expected_mode.get(entity_id) == "auto"):
            self.cancelled_auto[entity_id] = time.time()
        elif mode == "auto":
            self.cancelled_auto.pop(entity_id, None)
        self.pending_commands.pop(entity_id, None)
        self.state.expected_mode.pop(entity_id, None)
        self.command_faults.pop(entity_id, None)
        if mode == "auto":
            self.zone_holds.pop(entity_id, None)
        else:
            self.zone_holds[entity_id] = time.time() + float(self.settings.get("manual_hold_h", 12)) * 3600
        if mode == "off":
            self.manual_off.add(entity_id)
        else:
            self.manual_off.discard(entity_id)
        self.observed_modes[entity_id] = mode
        self._feedback_batches.clear()
        self.state.coast_feedback.abort_manual(time.time(), self.last_zones, self.settings)
        self.runtime.note(f"Slim klimaatbeheer: handmatige {mode.upper()} behouden voor {entity_id}; geen comfortregel overschrijft UIT.")
        self._dirty()
        self.runtime.publish()

    @callback
    def on_service_event(self, event):
        """Capture explicit user OFF even when the entity is already OFF."""
        if self.runtime._closed or not getattr(getattr(event, "context", None), "user_id", None):
            return
        data = event.data
        if data.get("domain") != "climate":
            return
        service_data = data.get("service_data", {}) or {}
        mode = service_data.get("hvac_mode") if data.get("service") == "set_hvac_mode" else {
            "turn_off": "off", "turn_on": "auto"}.get(data.get("service"))
        if mode not in ("off", "auto", "heat", "cool"):
            return
        ids = service_data.get("entity_id", [])
        if isinstance(ids, str):
            ids = [ids]
        if not isinstance(ids, (list, tuple)):
            return
        if "all" in ids:
            ids = self.settings.get("zone_entities", []) or []
        for eid in ids:
            if eid in (self.settings.get("zone_entities", []) or []):
                self._manual_mode(eid, mode)

    @callback
    def on_event(self, event):
        if self.runtime._closed:
            return
        eid = event.data.get("entity_id")
        new = event.data.get("new_state")
        if eid not in (self.settings.get("zone_entities", []) or []) or new is None or not self._fresh(new):
            return
        mode = str(new.state).casefold()
        if mode not in ("off", "auto", "heat", "cool"):
            return
        context = getattr(new, "context", None) or getattr(event, "context", None)
        own = getattr(context, "id", None) in self._contexts
        if own:
            return
        if getattr(context, "user_id", None):
            self._manual_mode(eid, mode)
            return
        old = event.data.get("old_state")
        if old is None or str(old.state).casefold() == mode or eid in self.pending_commands:
            return
        if mode == "auto" and eid in self.manual_off and eid in self.cancelled_auto:
            return
        # A real external transition is respected without guessing its actor.
        self._manual_mode(eid, mode)

    def _temp_unit_ok(self, obj):
        unit = obj.attributes.get("temperature_unit") or obj.attributes.get("unit_of_measurement")
        if unit is None:
            units = getattr(getattr(self.runtime.hass, "config", None), "units", None)
            unit = getattr(units, "temperature_unit", None)
        return unit == "°C"

    def _fresh(self, obj):
        if obj.attributes.get("restored"):
            return False
        stamp = getattr(obj, "last_reported", None) or getattr(obj, "last_updated", None)
        if stamp is None:
            return False
        try:
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
            return -5 <= age <= float(self.settings.get("stale_s", 1800))
        except Exception:
            return False

    def _zones(self):
        out = []
        for entity_id in self.settings.get("zone_entities", []) or []:
            obj = self.runtime.hass.states.get(entity_id)
            if obj is None or obj.state in ("unknown", "unavailable", "") or not self._temp_unit_ok(obj) or not self._fresh(obj):
                continue
            current = finite(obj.attributes.get("current_temperature"))
            target = finite(obj.attributes.get("temperature"))
            if current is None or target is None:
                continue
            out.append({
                "entity_id": entity_id,
                "name": obj.attributes.get("friendly_name") or entity_id,
                "current": current,
                "target": target,
                "mode": str(obj.state),
                "action": str(obj.attributes.get("hvac_action") or "unknown").casefold(),
                "action_known": str(obj.attributes.get("hvac_action") or "").casefold() in ("idle", "off", "heating", "cooling"),
                "hvac_modes": list(obj.attributes.get("hvac_modes", [])),
            })
        self.last_zones = out
        return out

    def _outside(self):
        entity_id = self.settings.get("outside_temp_entity")
        if entity_id:
            obj = self.runtime.hass.states.get(entity_id)
            if obj is not None and obj.state not in ("unknown", "unavailable", "") and self._fresh(obj):
                value = finite(obj.state)
                if value is not None:
                    self.last_outside = value
                    return value
        weather_id = self.settings.get("weather_entity")
        obj = self.runtime.hass.states.get(weather_id) if weather_id else None
        value = finite(obj.attributes.get("temperature")) if obj and self._fresh(obj) and self._temp_unit_ok(obj) else None
        self.last_outside = value
        return value

    @staticmethod
    def _parse_forecast_ts(value):
        if value is None:
            return None
        try:
            text = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            return None

    async def _refresh_forecast(self):
        weather_id = self.settings.get("weather_entity")
        if not weather_id or not self.runtime.hass.states.get(weather_id):
            return
        if time.time() - self.state.last_forecast_wall < float(self.settings.get("forecast_refresh_s", 3600)):
            return
        self.state.last_forecast_wall = time.time()
        try:
            response = await self.runtime.hass.services.async_call(
                "weather", "get_forecasts", {"type": "hourly"},
                target={"entity_id": weather_id}, blocking=True, return_response=True)
            rows = (response or {}).get(weather_id, {}).get("forecast", [])
            forecast = []
            for row in rows:
                temp = finite(row.get("temperature"))
                if temp is None:
                    continue
                valid_ts = self._parse_forecast_ts(row.get("datetime"))
                if valid_ts is None:
                    continue
                forecast.append({
                    "datetime": row.get("datetime"), "valid_ts": valid_ts,
                    "temperature": temp, "condition": row.get("condition"),
                    "humidity": row.get("humidity"), "cloud_coverage": row.get("cloud_coverage"),
                })
            if forecast:
                self.state.forecast = sorted(forecast, key=lambda row: row["valid_ts"])[:96]
                if self.settings.get("weather_bias_enabled", True):
                    self.state.weather_bias.queue(self.state.forecast, time.time())
                self.last_forecast_error = ""
            else:
                self.last_forecast_error = "Weerdienst gaf geen bruikbare uurtemperaturen"
        except Exception as err:
            self.last_forecast_error = f"Uurvoorspelling niet beschikbaar: {err}"

    def _current_forecast_rows(self, hours):
        """Use consecutive upcoming hours, never a past forecast or a hidden gap."""
        now = time.time()
        rows, previous = [], None
        for row in self.state.forecast:
            stamp = finite(row.get("valid_ts"))
            if stamp is None or stamp < (now // 3600) * 3600:
                continue
            if previous is None and stamp > now + 5400:
                break
            if previous is not None:
                if stamp <= previous:
                    continue
                if not 3300 <= stamp - previous <= 3900:
                    break
            rows.append(row)
            previous = stamp
            if len(rows) >= hours:
                break
        return rows

    def _outside_hourly(self):
        hours = max(6, int(float(self.settings.get("forecast_horizon_h", 48))))
        rows = self._current_forecast_rows(hours)
        out, corrections = [], []
        now = time.time()
        for idx, row in enumerate(rows):
            raw = finite(row.get("temperature"))
            if raw is None:
                continue
            valid_ts = finite(row.get("valid_ts"))
            lead_h = max(0.0, (valid_ts - now) / 3600.0) if valid_ts is not None else idx + 1
            bias, confidence = self.state.weather_bias.correction_for(lead_h, self.settings)
            corrected = raw + bias
            out.append(float(corrected))
            corrections.append({"lead_h": round(lead_h, 1), "raw_c": raw, "bias_c": round(bias, 2),
                                "corrected_c": round(corrected, 2), "confidence": round(confidence, 3)})
        self.last_weather_corrections = corrections
        return out

    def _solar_hourly(self, local_now, hours):
        """Keep missing PV intervals unknown in the thermal irradiation proxy.

        The modern source supplies exact elapsed-hour intervals. Independent
        legacy energy sources can supply a coarse hourly shape; weather rows and
        cached local estimates alone cannot establish that future PV is zero.
        """
        rows = self._current_forecast_rows(hours)
        if not rows:
            self.last_solar_hourly = []
            return []
        anchor = local_now.replace(minute=0, second=0, microsecond=0)
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=timezone.utc)
        indices = [int((row["valid_ts"] - anchor.timestamp()) // 3600) for row in rows]
        legacy = self.runtime._legacy_planner_pv_hourly(anchor, max(indices) + 1)
        modern = getattr(self.runtime, "pv_forecast", None)
        out = []
        for row, index in zip(rows, indices):
            dt = datetime.fromtimestamp(row["valid_ts"], tz=anchor.tzinfo)
            values = modern.hourly(dt, 1) if modern is not None else []
            value = finite(values[0]) if values else None
            if value is None and 0 <= index < len(legacy):
                value = legacy[index]
            out.append(round(value, 1) if value is not None else None)
        self.last_solar_hourly = out
        return list(self.last_solar_hourly)

    def _observe(self, zones, outside, local_now):
        if outside is None or time.time() - self.state.last_sample_wall < float(self.settings.get("sample_interval_s", 900)):
            return
        self.state.last_sample_wall = time.time()
        self.state.weather_bias.observe(time.time(), outside, local_now.date().isoformat())
        for z in zones:
            if not z.get("action_known"):
                # A missing action must not silently become an idle observation.
                profile = self.state.profile(z["entity_id"])
                profile.last = profile.action_started = None
                continue
            self.state.profile(z["entity_id"]).observe(
                wall_ts=time.time(), day=local_now.date().isoformat(),
                indoor_c=z["current"], outdoor_c=outside, hvac_action=z["action"],
                pv_w=self.runtime.pv_w, settings=self.settings,
            )

    def removal_blocked(self):
        """Return True only while SolarPilot still owns a climate coast/release."""
        if self.pending_commands:
            return True
        expected = self.state.expected_mode or {}
        if not expected:
            return False
        zones = self._zones()
        live_ids = {z["entity_id"] for z in zones}
        if any(eid not in live_ids for eid, mode in expected.items() if mode in ("off", "auto")):
            return True
        if not zones:
            return True
        for z in zones:
            want = str(expected.get(z["entity_id"], "")).casefold()
            have = str(z.get("mode", "")).casefold()
            if want == "off" and have == "off":
                return True
            if want == "auto" and have != "auto":
                return True
        return False

    async def prepare_for_removal(self):
        """Return any SolarPilot-created coast state to Panasonic AUTO."""
        if self.pending_commands:
            return False
        expected = self.state.expected_mode or {}
        if not expected:
            return False
        zones = self._zones()
        live_ids = {z["entity_id"] for z in zones}
        if any(eid not in live_ids for eid, mode in expected.items() if mode in ("off", "auto")):
            return False
        if not zones:
            return False
        pairs = [(str(expected.get(z["entity_id"], "")).casefold(), str(z.get("mode", "")).casefold()) for z in zones]
        # A previously requested AUTO must actually be reported before ownership
        # is released. This avoids removing the integration while a non-blocking
        # climate command is still in flight.
        if any(want == "auto" and have != "auto" for want, have in pairs):
            return False
        # If SolarPilot still owns an OFF/coast state, explicitly give Panasonic
        # AUTO back.  We never choose HEAT or COOL here.
        owned_off = [
            z for z in zones
            if str(expected.get(z["entity_id"], "")).casefold() == "off"
            and str(z.get("mode", "")).casefold() == "off"
        ]
        if owned_off:
            return await self._send_mode("auto", owned_off)
        # An expected OFF which is no longer OFF was changed externally; preserve
        # that manual state and relinquish ownership without writing anything.
        if any(want == "off" and have != "off" for want, have in pairs):
            self.state.expected_mode = {}
            self.runtime.note("Slim klimaatbeheer: handmatige toestand behouden tijdens verwijderen.")
            return False
        if all((not want) or (want == have) for want, have in pairs):
            self.state.expected_mode = {}
        return False

    def _manual_override_detected(self, zones):
        """Compatibility predicate; pending state and intent are reconciled per zone."""
        for z in zones:
            expected = self.state.expected_mode.get(z["entity_id"])
            if expected and z["entity_id"] not in self.pending_commands and str(z["mode"]).casefold() != str(expected).casefold():
                return True
        return False

    def _reconcile(self, zones):
        now = time.time()
        self._contexts = {key: expiry for key, expiry in self._contexts.items() if expiry > now}
        dirty = False
        live_ids = {z["entity_id"] for z in zones}
        for eid, pending in list(self.pending_commands.items()):
            if eid not in live_ids and now >= pending["expires_wall"]:
                self.pending_commands.pop(eid, None)
                self.state.expected_mode.pop(eid, None)
                self.command_faults[eid] = "Klimaatbron ontbreekt bij opdracht-timeout; geen bevestiging of herhaling"
                self.zone_holds[eid] = now + float(self.settings.get("manual_hold_h", 12)) * 3600
                if pending["mode"] == "off":
                    self.manual_off.add(eid)
                self._feedback_batches.pop(pending.get("feedback_group"), None)
                self.state.coast_feedback.active = self.state.coast_feedback.pending = None
                dirty = True
        for z in zones:
            eid, have = z["entity_id"], str(z["mode"]).casefold()
            pending = self.pending_commands.get(eid)
            previous = self.observed_modes.get(eid)
            if pending:
                # Polling fallback after an observed AUTO also respects a quick
                # return to OFF; a cloud mismatch is never permission to resend.
                if pending["mode"] == "auto" and previous == "auto" and have == "off":
                    self._manual_mode(eid, "off")
                    continue
                obj = self.runtime.hass.states.get(eid)
                stamp = getattr(obj, "last_reported", None) or getattr(obj, "last_updated", None)
                report_wall = stamp.timestamp() if stamp is not None else 0
                reference = max(pending["issued_wall"], pending.get("restart_wall", 0))
                if have == pending["mode"] and now >= reference + self.REPORT_DELAY_S and report_wall >= reference + self.REPORT_DELAY_S:
                    self.pending_commands.pop(eid, None)
                    self.command_faults.pop(eid, None)
                    group = self._feedback_batches.get(pending.get("feedback_group"))
                    if group is not None:
                        group["confirmed"][eid] = dict(z)
                        if set(group["zones"]) <= set(group["confirmed"]):
                            confirmed_zones = list(group["confirmed"].values())
                            if group["mode"] == "off":
                                self.state.coast_feedback.start(now, confirmed_zones, group["decision"], self.settings)
                            else:
                                self.state.coast_feedback.release_to_auto(now, confirmed_zones, group["decision"].reason, self.settings)
                            self._feedback_batches.pop(pending.get("feedback_group"), None)
                    self.runtime.note(f"Slim klimaatbeheer: latere HA-modebevestiging ontvangen voor {z['name']}.")
                    dirty = True
                elif now >= pending["expires_wall"]:
                    self.pending_commands.pop(eid, None)
                    self.state.expected_mode.pop(eid, None)
                    self.command_faults[eid] = "Klimaatopdracht niet later bevestigd; actuele stand behouden, geen automatische herhaling"
                    self.zone_holds[eid] = now + float(self.settings.get("manual_hold_h", 12)) * 3600
                    if have == "off":
                        self.manual_off.add(eid)
                    self._feedback_batches.pop(pending.get("feedback_group"), None)
                    self.state.coast_feedback.active = self.state.coast_feedback.pending = None
                    dirty = True
            else:
                expected = self.state.expected_mode.get(eid)
                if expected and have != expected:
                    self._manual_mode(eid, have)
                elif have == "off" and expected != "off" and eid not in self.manual_off:
                    self.manual_off.add(eid)
                    dirty = True
                elif (have == "auto" and eid in self.manual_off and previous == "off"
                      and eid not in self.cancelled_auto):
                    self._manual_mode(eid, "auto")
            self.observed_modes[eid] = have
        if dirty:
            self._dirty()

    def _has_fixed_heat_cool(self, zones):
        return any(str(z.get("mode", "")).casefold() in ("heat", "cool") for z in zones)

    def _command_targets(self, decision, zones):
        """Select only zones SolarPilot may change for this global decision.

        Only a SolarPilot-owned coast can be released to AUTO. A manually OFF
        zone is preserved even outside the comfort band; native Panasonic
        protections remain responsible for physical safety.
        """
        mode = str(decision.desired_mode).casefold()
        eligible = [z for z in zones if z["entity_id"] not in self.pending_commands
                    and z["entity_id"] not in self.manual_off
                    and time.time() >= self.zone_holds.get(z["entity_id"], 0)]
        if mode == "off":
            return [z for z in eligible if str(z.get("mode", "")).casefold() == "auto" and z.get("action_known")]
        if mode != "auto":
            return []

        hard = max(
            float(self.settings.get("soft_band_c", 0.5)),
            float(self.settings.get("hard_band_c", 1.0)),
        )
        expected = self.state.expected_mode or {}
        targets = []
        for zone in eligible:
            if str(zone.get("mode", "")).casefold() == "auto":
                continue
            entity_id = zone["entity_id"]
            if str(expected.get(entity_id, "")).casefold() == "off":
                # A hard override must be justified by this zone's current data,
                # rather than an old cached breach or another manual OFF zone.
                if not decision.hard_override or zone["current"] < zone["target"] - hard or zone["current"] > zone["target"] + hard:
                    targets.append(zone)
                continue
        return targets

    async def _send_mode(self, mode, zones):
        # Hard invariant: SolarPilot never chooses HEAT or COOL. Panasonic AUTO owns it.
        if mode not in ("auto", "off"):
            return False
        for z in zones:
            if protected_entity(self.runtime.hass, self.runtime.wallbox_settings, z["entity_id"]):
                raise HomeAssistantError("Wallbox-entiteit mag niet als klimaatregeling worden gebruikt")
            if mode not in [str(x).casefold() for x in z.get("hvac_modes", [])]:
                raise HomeAssistantError(f'{z["name"]} ondersteunt mode {mode} niet')
        now = time.time()
        issued_any = False
        feedback_group = Context().id
        for z in zones:
            eid = z["entity_id"]
            # Earlier service awaits can deliver user events for a later zone.
            if eid in self.manual_off or eid in self.pending_commands or time.time() < self.zone_holds.get(eid, 0):
                continue
            if self._has_fixed_heat_cool(self._zones()):
                break
            context = Context()
            batch = self._feedback_batches.setdefault(feedback_group, {
                "mode": mode, "decision": self.state.last_decision, "zones": {}, "confirmed": {}})
            batch["zones"][eid] = dict(z)
            # Journal before awaiting: an explicit user event may cancel this
            # intent while the service yields, and must not be overwritten later.
            self._contexts[context.id] = now + self.COMMAND_TIMEOUT_S
            self.pending_commands[eid] = {"mode": mode, "issued_wall": now,
                                          "expires_wall": now + self.COMMAND_TIMEOUT_S,
                                          "context_id": context.id, "feedback_group": feedback_group}
            self.state.expected_mode[eid] = mode
            self.zone_command_walls[eid] = now
            self._dirty()
            issued_any = True
            try:
                await self.runtime.hass.services.async_call(
                    "climate", "set_hvac_mode", {"entity_id": eid, "hvac_mode": mode},
                    blocking=False, context=context)
            except HomeAssistantError as err:
                if self.pending_commands.get(eid, {}).get("context_id") == context.id:
                    self.pending_commands.pop(eid, None)
                    self.state.expected_mode.pop(eid, None)
                    self.zone_holds[eid] = now + float(self.settings.get("manual_hold_h", 12)) * 3600
                    if str(z["mode"]).casefold() == "off":
                        self.manual_off.add(eid)
                    self.command_faults[eid] = f"Klimaatopdracht mislukt; geen automatische herhaling: {err}"
                    self._feedback_batches.pop(feedback_group, None)
                    self.state.coast_feedback.active = self.state.coast_feedback.pending = None
                    self._dirty()
        if not issued_any:
            return False
        self.state.last_command_wall = now
        self.state.last_command_mode = mode
        local_day = self._local_day()
        if self.state.command_day != local_day:
            self.state.command_day, self.state.commands_today = local_day, 0
        self.state.commands_today += 1
        label = "AUTO aangevraagd" if mode == "auto" else "ruimteklimaatpauze aangevraagd"
        self.runtime.note(f"Slim klimaatbeheer: {label} — {self.state.last_decision.reason}")
        self._dirty()
        return True

    def _local_day(self):
        zone = getattr(getattr(self.runtime.hass, "config", None), "time_zone", "Europe/Brussels")
        return datetime.now(ZoneInfo(zone)).date().isoformat()

    def _coerce_setting(self, key, value):
        if key not in CLIMATE_SETTING_SPECS:
            raise HomeAssistantError(f"Onbekende klimaatinstelling: {key}")
        spec = CLIMATE_SETTING_SPECS[key]
        kind = spec["type"]
        if kind == "boolean":
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "on", "aan")
            return bool(value)
        if kind == "number":
            val = finite(value)
            if val is None:
                raise HomeAssistantError(f"{spec['label']}: geen geldig getal")
            if val < float(spec["min"]) or val > float(spec["max"]):
                raise HomeAssistantError(f"{spec['label']}: kies {spec['min']} t/m {spec['max']}")
            return val
        if kind == "climate_entities":
            if isinstance(value, str):
                value = [x.strip() for x in value.split(",") if x.strip()]
            if not isinstance(value, (list, tuple)):
                raise HomeAssistantError("Panasonic-zones: selecteer één of meer climate-entiteiten")
            return [str(x) for x in value if str(x)]
        return str(value or "")

    def _validate_candidate(self, candidate):
        if candidate.get("hard_band_c", 1) < candidate.get("soft_band_c", .5):
            raise HomeAssistantError("De harde comfortgrens moet minstens even groot zijn als de zachte comfortband.")
        if candidate.get("season_extreme_delta_c", 5) <= candidate.get("shoulder_band_c", 3):
            raise HomeAssistantError("Duidelijke zomer/winter moet buiten de tussenseizoen-band liggen.")
        if candidate.get("coast_feedback_min_adjust_h", -2) > 0 or candidate.get("coast_feedback_max_adjust_h", 3) < 0:
            raise HomeAssistantError("Coast-aanpassingsgrenzen zijn ongeldig.")
        zones = candidate.get("zone_entities", []) or []
        if candidate.get("enabled") and not zones:
            raise HomeAssistantError("Kies eerst minstens één Panasonic-klimaatzone.")
        for entity_id in zones:
            obj = self.runtime.hass.states.get(entity_id)
            modes = {str(x).casefold() for x in (obj.attributes.get("hvac_modes", []) if obj else [])}
            if obj is None or not {"auto", "off"}.issubset(modes):
                raise HomeAssistantError(f"{entity_id} moet AUTO en OFF ondersteunen.")
        weather_id = candidate.get("weather_entity")
        if candidate.get("enabled") and (not weather_id or self.runtime.hass.states.get(weather_id) is None):
            raise HomeAssistantError("Kies een geldige weather-entiteit voor de uurvoorspelling.")
        outside_id = candidate.get("outside_temp_entity")
        if outside_id:
            obj = self.runtime.hass.states.get(outside_id)
            if obj is None or obj.attributes.get("unit_of_measurement") != "°C":
                raise HomeAssistantError("De buitentemperatuurbron moet °C rapporteren.")
        if candidate.get("control_enabled") and not candidate.get("enabled"):
            raise HomeAssistantError("Zet eerst het thermische model en advies aan.")

    async def async_set_setting(self, key, value):
        """Persist one dashboard setting without reloading the entire integration."""
        value = self._coerce_setting(key, value)
        if (key == "zone_entities" and list(value) != list(self.settings.get(key, []) or [])
                and self.removal_blocked()):
            raise HomeAssistantError("Klimaatzones zijn nog in beheer of wachten op een modebevestiging. Geef de bestaande eigen pauze eerst veilig terug aan Panasonic vóór je de koppeling wijzigt.")
        if (key in ("enabled", "control_enabled") and not value and self.settings.get(key)
                and self.removal_blocked()):
            raise HomeAssistantError("Klimaatregeling is nog in beheer of wacht op een modebevestiging. Kies eerst Pauze en wacht tot de eigen klimaatpauze veilig aan Panasonic is teruggegeven vóór je de regeling uitschakelt.")
        candidate = {**self.settings, key: value}
        self._validate_candidate(candidate)
        old_weather = self.settings.get("weather_entity")
        old_outside = self.settings.get("outside_temp_entity")
        old_zones = list(self.settings.get("zone_entities", []) or [])
        self.settings = candidate

        # Store in config_entry.options as the canonical configuration. The update
        # listener skips this one reload because the manager has already applied it.
        entry = self.runtime.entry
        opts = deepcopy(dict(getattr(entry, "options", {}) or {}))
        opts["smart_climate"] = {**opts.get("smart_climate", {}), key: value}
        config_entries = getattr(self.runtime.hass, "config_entries", None)
        if config_entries is not None and hasattr(config_entries, "async_update_entry"):
            self.runtime._skip_options_reload_once = True
            config_entries.async_update_entry(entry, options=opts)
        else:
            entry.options = opts

        if key == "weather_entity" and value != old_weather:
            self.state.forecast = []
            self.state.weather_bias.reset()
            # Without a separate physical outdoor sensor the weather entity also
            # supplied the actual outdoor reference used by the thermal model.
            if not self.settings.get("outside_temp_entity"):
                self.state.profiles = {}
                self.last_forecast_error = "Weerbron gewijzigd; weerscorrectie en thermisch model leren opnieuw."
            else:
                self.last_forecast_error = "Weerbron gewijzigd; lokale weerscorrectie leert opnieuw."
        if key == "outside_temp_entity" and value != old_outside:
            self.state.weather_bias.reset()
            self.state.profiles = {}
            self.last_forecast_error = "Buitentemperatuurbron gewijzigd; weerscorrectie en thermisch model leren veilig opnieuw."
        if key == "zone_entities" and list(value) != old_zones:
            # Keep profiles for retained zones; new zones start safely with no confidence.
            self.state.profiles = {eid: p for eid, p in self.state.profiles.items() if eid in value}
            self.manual_off.intersection_update(value)
            for mapping in (self.state.expected_mode, self.zone_holds, self.pending_commands,
                            self.observed_modes, self.zone_command_walls, self.command_faults, self.cancelled_auto):
                for eid in set(mapping) - set(value):
                    mapping.pop(eid, None)
            if self._started:
                self.start()
        self.runtime.store.async_delay_save(self.runtime._snapshot, 1)
        self.runtime.note(f"Slim klimaatbeheer: instelling '{CLIMATE_SETTING_SPECS[key]['label']}' gewijzigd naar {value}.")
        self.runtime.publish()
        return value

    async def tick(self, *, local_now, allow_command=False):
        active = self.settings.get("enabled") and self.configured
        if not active and not self.pending_commands:
            return False
        zones = self._zones()
        self._reconcile(zones)
        # Disabling advice/control does not cancel an already journalled call.
        # Resolve its later report or timeout without learning or another write.
        if not active:
            return False
        outside = self._outside()
        configured_zones = list(self.settings.get("zone_entities", []) or [])
        if not zones or len(zones) != len(configured_zones):
            self.state.fault = "Niet alle geselecteerde klimaatzones hebben actuele, bruikbare temperatuurdata"
            return False
        if outside is None:
            self.state.fault = "Actuele buitentemperatuur ontbreekt of is te oud"
            return False
        self.state.fault = ""
        self._observe(zones, outside, local_now)
        await self._refresh_forecast()
        if not self.busy:
            self.state.coast_feedback.update(zones, self.settings)
            self.state.coast_feedback.observe_after_release(time.time(), zones, self.settings)

        hard = float(self.settings.get("hard_band_c", 1.0))
        planning_zones = [z for z in zones if str(z["mode"]).casefold() != "off"
                          or (self.state.expected_mode.get(z["entity_id"]) == "off" and z["entity_id"] not in self.manual_off)]
        # Still show an advisory model when every selected room is manually OFF.
        advisory_zones = planning_zones or zones
        hard_breach = any(z["current"] < z["target"] - hard or z["current"] > z["target"] + hard for z in planning_zones)
        due = time.time() - self.state.last_decision_wall >= float(self.settings.get("decision_interval_h", 12)) * 3600
        guard_due = (
            any(str(z.get("mode", "")).casefold() == "off" for z in zones)
            and time.time() - self.state.last_guard_wall >= float(self.settings.get("guard_recheck_s", 900))
        )

        command_candidate = any(str(z["mode"]).casefold() != self.state.last_decision.desired_mode
                                for z in planning_zones) and self.state.last_decision.desired_mode in ("auto", "off")
        if due or hard_breach or guard_due or self.state.last_decision.hard_override or command_candidate:
            outside_hourly = self._outside_hourly()
            solar_hourly = self._solar_hourly(local_now, len(outside_hourly)) if self.settings.get("solar_gain_enabled") else []
            # Evaluate only a complete common horizon when PV ends before the
            # weather source. Never skip an internal PV gap or invent its tail.
            # decide_mode still requires a full minimum useful coast period.
            if solar_hourly:
                known = [i for i, value in enumerate(solar_hourly) if value is not None]
                if known:
                    end = known[-1] + 1
                    if end < len(solar_hourly) and all(value is not None for value in solar_hourly[:end]):
                        outside_hourly = outside_hourly[:end]
                        solar_hourly = solar_hourly[:end]
            pv_precondition = bool(
                self.settings.get("solar_preconditioning_enabled")
                and (self.runtime.pv_w or 0) >= float(self.settings.get("precondition_min_pv_w", 3000))
            )
            decision = decide_mode(
                settings=self.settings, zones=advisory_zones, outside_hourly=outside_hourly,
                profiles=self.state.profiles, solar_precondition=pv_precondition,
                solar_hourly_w=solar_hourly,
                coast_window_adjust_h=self.state.coast_feedback.adjust_h if self.settings.get("coast_feedback_enabled") else 0.0,
            )
            self.state.last_decision = decision
            if due:
                self.state.last_decision_wall = time.time()
            if guard_due:
                self.state.last_guard_wall = time.time()

        decision = self.state.last_decision
        safety_release = (decision.desired_mode == "auto" and bool(decision.missing_components)
                          and any(self.state.expected_mode.get(z["entity_id"]) == "off" for z in planning_zones))
        if not (allow_command and self.settings.get("control_enabled")):
            return False
        if self._has_fixed_heat_cool(zones):
            return False
        if time.time() < self.state.manual_hold_until:
            return False

        local_day = local_now.date().isoformat()
        commands = self.state.commands_today if self.state.command_day == local_day else 0
        if commands >= int(self.settings.get("max_commands_per_day", 2)) and not decision.hard_override and not safety_release:
            return False
        if decision.desired_mode not in ("auto", "off"):
            return False
        targets = self._command_targets(decision, zones)
        if not targets:
            return False
        if self.state.last_command_wall and not decision.hard_override and not safety_release:
            targets = [z for z in targets if (time.time() - self.zone_command_walls.get(
                z["entity_id"], self.state.last_command_wall if z["entity_id"] in self.state.expected_mode else 0)) / 3600.0 >= float(self.settings.get("min_state_hold_h", 8.0))]
            if not targets:
                return False
        return await self._send_mode(decision.desired_mode, targets)

    def _alerts(self, zones, confidences):
        alerts = []
        if self.state.fault:
            alerts.append({"severity": "error", "title": "Klimaatregeling geblokkeerd", "message": self.state.fault})
        if self.last_forecast_error:
            alerts.append({"severity": "warning", "title": "Weersvoorspelling", "message": self.last_forecast_error})
        if self._has_fixed_heat_cool(zones):
            alerts.append({"severity": "info", "title": "Handmatige Panasonic-stand", "message": "HEAT/COOL wordt nooit overschreven; SolarPilot blijft adviserend tot je zelf terugkeert naar AUTO/OFF."})
        manual_off = [
            z["name"] for z in zones
            if str(z.get("mode", "")).casefold() == "off"
            and str((self.state.expected_mode or {}).get(z["entity_id"], "")).casefold() != "off"
        ]
        if manual_off:
            alerts.append({
                "severity": "info",
                "title": "Handmatige OFF-zone behouden",
                "message": f"{', '.join(manual_off)} blijft UIT, ook buiten de comfortband. Zet de betreffende zone zelf op AUTO om automatische bediening weer toe te staan.",
            })
        unknown = [z["name"] for z in zones if not z.get("action_known")]
        if unknown:
            alerts.append({"severity": "warning", "title": "Klimaatactie ontbreekt",
                           "message": f"{', '.join(unknown)}: geen betrouwbare heating/cooling/idle/off-actie. Deze intervallen worden niet geleerd en er start geen automatische pauze."})
        if self.command_faults:
            alerts.append({"severity": "warning", "title": "Klimaatopdracht onzeker",
                           "message": "; ".join(self.command_faults.values())})
        late_auto = [z["name"] for z in zones if z["entity_id"] in self.manual_off and str(z["mode"]).casefold() == "auto"]
        if late_auto:
            alerts.append({"severity": "warning", "title": "UIT-keuze en bronstand verschillen",
                           "message": f"{', '.join(late_auto)} meldt AUTO na een behouden UIT-keuze. SolarPilot geeft geen nieuwe AUTO-opdracht; controleer de native stand of kies zelf expliciet AUTO om de UIT-bescherming op te heffen."})
        if self.pending_commands:
            alerts.append({"severity": "info", "title": "Wachten op latere modebevestiging",
                           "message": "Een latere actuele HA-rapportage moet de gevraagde stand bevestigen; er wordt geen opdracht herhaald."})
        model_conf = self.state.last_decision.prediction_confidence
        min_conf = float(self.settings.get("model_confidence_min", .55))
        if self.settings.get("enabled") and model_conf < min_conf:
            reason = self.state.last_decision.block_reason or "Benodigde leeronderdelen zijn nog onvolledig"
            alerts.append({"severity": "info", "title": "Benodigde modelgegevens ontbreken", "message": f"{reason}. Automatisch pauzeren vraagt minstens {min_conf:.0%} voor de benodigde onderdelen."})
        if self.settings.get("solar_gain_enabled") and (self.runtime.pv_w is None):
            alerts.append({"severity": "warning", "title": "Zonnewinst zonder PV-bron", "message": "Zonnewinst staat aan maar er is geen actuele PV-meting; zonne-invloed wordt dan niet geleerd."})
        if not self.settings.get("control_enabled"):
            alerts.append({"severity": "info", "title": "Adviesmodus", "message": "Het model leert en adviseert, maar stuurt Panasonic AUTO/OFF niet fysiek."})
        return alerts

    def _settings_catalog(self):
        out = []
        for key, spec in CLIMATE_SETTING_SPECS.items():
            row = {"key": key, "value": self.settings.get(key), "default": SMART_CLIMATE_DEFAULTS.get(key), **spec}
            out.append(row)
        return out

    def overview(self):
        zones = self.last_zones or self._zones()
        coeffs = {}
        confidences = []
        for z in zones:
            p = self.state.profile(z["entity_id"])
            k, heat, cool, delay = p.coefficients()
            conf = p.confidence(self.settings)
            confidences.append(conf)
            components = p.confidence_components(self.settings)
            coeffs[z["entity_id"]] = {
                "samples": p.samples, "days": len(p.days), "confidence": round(conf, 3),
                "reliability_status": p.confidence_status(conf, p.samples),
                "confidence_components": components,
                "passive_k_per_h": round(k, 4), "thermal_time_constant_h": round(1.0 / max(k, .001), 1),
                "heat_gain_c_h": round(heat, 3), "heat_gain_learned": len(p.heat_gain) >= 6,
                "cool_gain_c_h": round(cool, 3), "cool_gain_learned": len(p.cool_gain) >= 6,
                "response_delay_h": round(delay, 2), "response_delay_learned": len(p.response_delays_h) >= 4,
                "solar_gain_c_h_per_kw_pv": round(p.solar_coefficient(), 4),
                "solar_gain_samples": len(p.solar_gain_per_kw),
                "solar_gain_confidence": round(p.solar_confidence(self.settings), 3),
            }
        d = self.state.last_decision
        weather = self.state.weather_bias.overview(self.settings)
        coast = self.state.coast_feedback.overview(self.settings)
        weather_values = [float(x.get("confidence", 0) or 0) for x in weather.get("horizons", [])]
        weather_conf = max(weather_values, default=0.0)
        weather_samples = int(weather.get("total_samples", 0) or 0)
        coast_need = max(1, int(self.settings.get("coast_feedback_min_episodes", 4)))
        coast_conf = min(0.98, float(coast.get("scored", 0) or 0) / coast_need)
        coast_samples = int(coast.get("scored", 0) or 0)
        complete_conf = min(confidences) if confidences else 0.0
        overall_conf = d.prediction_confidence
        reliability = {
            "automatic_coast": {
                "confidence": round(overall_conf, 3),
                "control_ready": d.control_ready,
                "block_reason": d.block_reason,
                "status": self.state.profile(zones[0]["entity_id"]).confidence_status(overall_conf, sum(p.samples for p in self.state.profiles.values())) if zones else "Nog niet geleerd",
            },
            "weather_forecast_correction": {
                "confidence": round(weather_conf, 3),
                "samples": weather_samples,
                "status": self.state.profile(zones[0]["entity_id"]).confidence_status(weather_conf, weather_samples) if zones else "Nog niet geleerd",
            },
            "coast_off_feedback": {
                "confidence": round(coast_conf, 3),
                "samples": coast_samples,
                "status": self.state.profile(zones[0]["entity_id"]).confidence_status(coast_conf, coast_samples) if zones else "Nog niet geleerd",
            },
        }
        solar_values = self.last_solar_hourly
        covered = [x for x in solar_values if x is not None]
        first_day = solar_values[:24]
        solar_summary = {
            "enabled": bool(self.settings.get("solar_gain_enabled")),
            "forecast_hours": len(solar_values),
            "covered_hours": len(covered),
            "next_24h_kwh_proxy": (round(sum(first_day) / 1000.0, 2)
                                    if len(first_day) == 24 and all(x is not None for x in first_day) else None),
            "peak_w_proxy": round(max(covered), 0) if covered and len(covered) == len(solar_values) else None,
            "note": "PV is alleen een lokale instralingsproxy voor het thermische model; niet hetzelfde als zonnewarmte door ramen.",
        }
        return {
            "enabled": bool(self.settings.get("enabled")),
            "control_enabled": bool(self.settings.get("control_enabled")),
            "zones": [{**z, "manual_off": z["entity_id"] in self.manual_off
                       or (str(z["mode"]).casefold() == "off" and self.state.expected_mode.get(z["entity_id"]) != "off"),
                       "pending_mode": self.pending_commands.get(z["entity_id"], {}).get("mode", ""),
                       "hold_remaining_h": max(0, (self.zone_holds.get(z["entity_id"], 0) - time.time()) / 3600)} for z in zones],
            "outside_c": self.last_outside,
            "forecast_hours": len(self.state.forecast), "forecast_error": self.last_forecast_error,
            "fault": self.state.fault,
            "decision": {
                "mode": d.desired_mode, "reason": d.reason, "hard_override": d.hard_override,
                "evaluated_forecast_h": d.evaluated_forecast_h,
                "confidence": round(d.prediction_confidence, 3), "predicted_min_c": d.predicted_min_c,
                "predicted_max_c": d.predicted_max_c, "crossing_h": d.crossing_h,
                "required_lead_h": d.required_lead_h, "season_context": d.season_context,
                "season_strength": round(d.season_strength, 3), "comfort_direction": d.comfort_direction,
                "effective_coast_window_h": d.effective_coast_window_h,
                "solar_gain_used": d.solar_gain_used,
                "forecast_confidence": d.forecast_confidence, "control_ready": d.control_ready,
                "required_components": d.required_components, "missing_components": d.missing_components,
                "readiness_by_zone": deepcopy(d.readiness_by_zone), "block_reason": d.block_reason,
            },
            "season_context": d.season_context,
            "manual_fixed_mode": self._has_fixed_heat_cool(zones),
            "manual_hold_remaining_h": max(0.0, (self.state.manual_hold_until - time.time()) / 3600),
            "commands_today": self.state.commands_today if self.state.command_day == self._local_day() else 0,
            "last_command_mode": self.state.last_command_mode,
            "model_confidence": round(overall_conf, 3),
            "complete_model_confidence": round(complete_conf, 3),
            "manual_off_zones": sorted(self.manual_off),
            "zone_holds": {eid: max(0, (wall - time.time()) / 3600) for eid, wall in self.zone_holds.items()},
            "pending_commands": [{"entity_id": eid, "mode": p["mode"],
                                  "remaining_s": max(0, p["expires_wall"] - time.time())}
                                 for eid, p in self.pending_commands.items()],
            "reliability": reliability,
            "profiles": coeffs,
            "weather_bias": weather,
            "solar_gain": solar_summary,
            "coast_feedback": coast,
            "alerts": self._alerts(zones, confidences),
            "settings": dict(self.settings),
            "settings_catalog": self._settings_catalog(),
            "service": "solar_pilot.set_climate_setting",
            "note": "Panasonic beslist HEAT versus COOL. SolarPilot wijzigt nooit die keuze of het thermostaatdoel; het kan alleen AUTO vrijgeven of vooral in het tussenseizoen langdurig coasten via OFF.",
            "explanation": [
                "Zonnewinst: werkelijke PV dient als lokale instralingsproxy. SolarPilot leert per zone hoeveel extra opwarming daarmee samenhangt en begrenst de invloed.",
                "Weerscorrectie: forecastfouten op 6/12/24/48 uur worden lokaal geleerd. Een bias wordt pas toegepast na voldoende verschillende samples en dagen.",
                "Betrouwbaarheid: passieve drift, zonnewinst, verwarmingsrespons, koelrespons, reactievertraging, weerscorrectie en coast-feedback worden afzonderlijk beoordeeld. Ontbrekende onderdelen worden nooit als 100% weergegeven.",
                "Coast-evaluatie: een SolarPilot-coast wordt achteraf gescoord als correct, te lang of te voorzichtig. Alleen het minimale nuttige coastvenster mag binnen ingestelde grenzen verschuiven.",
                "Open ramen/deuren zijn bewust géén onderdeel van deze versie; de regeling blijft gericht op halve-dag/daggedrag van vloer en bouwschil.",
            ],
        }
