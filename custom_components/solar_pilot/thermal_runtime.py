"""Home Assistant runtime wrapper for slow Panasonic AUTO/coast planning."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import time

from homeassistant.exceptions import HomeAssistantError

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

    @property
    def configured(self):
        return bool(self.settings.get("zone_entities"))

    @property
    def busy(self):
        return False

    def snapshot(self):
        return self.state.snapshot()

    def restore(self, data):
        self.state.restore(data, self.settings.get("zone_entities", []))

    def _temp_unit_ok(self, obj):
        unit = obj.attributes.get("temperature_unit") or obj.attributes.get("unit_of_measurement")
        if unit is None:
            units = getattr(getattr(self.runtime.hass, "config", None), "units", None)
            unit = getattr(units, "temperature_unit", None)
        return unit == "°C"

    def _fresh(self, obj):
        stamp = getattr(obj, "last_reported", None) or getattr(obj, "last_updated", None)
        if stamp is None:
            return True
        try:
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds() <= float(self.settings.get("stale_s", 1800))
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
                "action": obj.attributes.get("hvac_action", "idle"),
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
        value = finite(obj.attributes.get("temperature")) if obj else None
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
                forecast.append({
                    "datetime": row.get("datetime"), "valid_ts": valid_ts,
                    "temperature": temp, "condition": row.get("condition"),
                    "humidity": row.get("humidity"), "cloud_coverage": row.get("cloud_coverage"),
                })
            if forecast:
                self.state.forecast = forecast[:96]
                if self.settings.get("weather_bias_enabled", True):
                    self.state.weather_bias.queue(self.state.forecast, time.time())
                self.last_forecast_error = ""
            else:
                self.last_forecast_error = "Weerdienst gaf geen bruikbare uurtemperaturen"
        except Exception as err:
            self.last_forecast_error = f"Uurvoorspelling niet beschikbaar: {err}"

    def _outside_hourly(self):
        hours = max(6, int(float(self.settings.get("forecast_horizon_h", 48))))
        rows = self.state.forecast[:hours]
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
        """Build a conservative hourly PV proxy for thermal solar-gain prediction.

        Current/next-hour values use the live local PV model when sufficiently
        trusted. Longer horizons use the historical local hourly shape scaled by
        Forecast.Solar's remaining-today/tomorrow energy. This is an irradiation
        proxy only; it never becomes the realtime dispatch meter.
        """
        rows = list(self.state.forecast[:hours])
        if not rows:
            self.last_solar_hourly = []
            return []
        seed = getattr(self.runtime, "historical_seed", {}) or {}
        profile = seed.get("pv_profile", {}).get("median_normalized_pct_by_hour", {}) or {}
        forecast_vals = self.runtime._forecast_values() if hasattr(self.runtime, "_forecast_values") else {}
        today_kwh = finite(forecast_vals.get("remaining_today_kwh"))
        tomorrow_kwh = finite(forecast_vals.get("tomorrow_kwh"))

        parsed = []
        for idx, row in enumerate(rows):
            valid_ts = finite(row.get("valid_ts"))
            if valid_ts is not None:
                try:
                    dt = datetime.fromtimestamp(valid_ts, tz=local_now.tzinfo or timezone.utc)
                except Exception:
                    dt = local_now + timedelta(hours=idx + 1)
            else:
                dt = local_now + timedelta(hours=idx + 1)
            try:
                weight = max(0.0, float(profile.get(str(dt.hour), 0.0) or 0.0))
            except Exception:
                weight = 0.0
            parsed.append({"dt": dt, "weight": weight, "w": 0.0})

        today = local_now.date()
        tomorrow = today + timedelta(days=1)
        for date_value, energy_kwh in ((today, today_kwh), (tomorrow, tomorrow_kwh)):
            candidates = [r for r in parsed if r["dt"].date() == date_value]
            if energy_kwh is None or not candidates:
                continue
            total_weight = sum(r["weight"] for r in candidates)
            if total_weight <= 0:
                continue
            for r in candidates:
                # kWh apportioned to one-hour bucket -> average W for that hour.
                r["w"] = energy_kwh * 1000.0 * r["weight"] / total_weight

        # Current / next hour are more valuable than the coarse long-horizon shape.
        local_pv = self.runtime.local_pv.overview() if getattr(self.runtime, "local_pv", None) else {}
        min_conf = float(getattr(self.runtime, "local_pv_settings", {}).get("min_confidence", .55))
        if parsed and local_pv.get("confidence", 0) >= min_conf and local_pv.get("corrected_power_w") is not None:
            parsed[0]["w"] = max(0.0, float(local_pv["corrected_power_w"]))
        elif parsed and hasattr(self.runtime, "_forecast_power"):
            current_power = self.runtime._forecast_power()
            if current_power is not None:
                parsed[0]["w"] = max(0.0, float(current_power))
        if len(parsed) > 1:
            corrected_next = local_pv.get("corrected_next_hour_kwh") if local_pv.get("confidence", 0) >= min_conf else None
            next_kwh = corrected_next if corrected_next is not None else finite(forecast_vals.get("next_hour_kwh"))
            if next_kwh is not None:
                parsed[1]["w"] = max(0.0, float(next_kwh) * 1000.0)

        modern = getattr(self.runtime, "pv_forecast", None)
        if modern is not None and modern.source.valid:
            for row in parsed:
                values = modern.hourly(row["dt"],1)
                if values and values[0] is not None:
                    row["w"] = values[0]
        self.last_solar_hourly = [round(r["w"], 1) for r in parsed]
        return list(self.last_solar_hourly)

    def _observe(self, zones, outside, local_now):
        if outside is None or time.time() - self.state.last_sample_wall < float(self.settings.get("sample_interval_s", 900)):
            return
        self.state.last_sample_wall = time.time()
        self.state.weather_bias.observe(time.time(), outside, local_now.date().isoformat())
        for z in zones:
            self.state.profile(z["entity_id"]).observe(
                wall_ts=time.time(), day=local_now.date().isoformat(),
                indoor_c=z["current"], outdoor_c=outside, hvac_action=z["action"],
                pv_w=self.runtime.pv_w, settings=self.settings,
            )

    def removal_blocked(self):
        """Return True only while SolarPilot still owns a climate coast/release."""
        expected = self.state.expected_mode or {}
        if not expected:
            return False
        zones = self._zones()
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
        expected = self.state.expected_mode or {}
        if not expected:
            return False
        zones = self._zones()
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
        if any(want == "off" and have == "off" for want, have in pairs):
            return await self._send_mode("auto", zones)
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
        if not self.state.expected_mode or time.time() - self.state.last_command_wall < 180:
            return False
        for z in zones:
            expected = self.state.expected_mode.get(z["entity_id"])
            if expected and str(z["mode"]).casefold() != str(expected).casefold():
                return True
        return False

    def _has_fixed_heat_cool(self, zones):
        return any(str(z.get("mode", "")).casefold() in ("heat", "cool") for z in zones)

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
        if mode == "auto":
            self.state.coast_feedback.release_to_auto(now, zones, self.state.last_decision.reason, self.settings)
        for z in zones:
            await self.runtime.hass.services.async_call(
                "climate", "set_hvac_mode", {"entity_id": z["entity_id"], "hvac_mode": mode}, blocking=False)
        self.state.expected_mode = {z["entity_id"]: mode for z in zones}
        self.state.last_command_wall = now
        self.state.last_command_mode = mode
        if mode == "off":
            self.state.coast_feedback.start(now, zones, self.state.last_decision, self.settings)
        local_day = datetime.now().astimezone().date().isoformat()
        if self.state.command_day != local_day:
            self.state.command_day, self.state.commands_today = local_day, 0
        self.state.commands_today += 1
        label = "AUTO vrijgegeven" if mode == "auto" else "coast / ruimteklimaat uit"
        self.runtime.note(f"Slim klimaatbeheer: {label} — {self.state.last_decision.reason}")
        return True

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
        self.runtime.store.async_delay_save(self.runtime._snapshot, 1)
        self.runtime.note(f"Slim klimaatbeheer: instelling '{CLIMATE_SETTING_SPECS[key]['label']}' gewijzigd naar {value}.")
        self.runtime.publish()
        return value

    async def tick(self, *, local_now, allow_command=False):
        if not self.settings.get("enabled") or not self.configured:
            return False
        zones = self._zones()
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
        self.state.coast_feedback.update(zones, self.settings)
        self.state.coast_feedback.observe_after_release(time.time(), zones, self.settings)

        if self._manual_override_detected(zones):
            self.state.coast_feedback.abort_manual(time.time(), zones, self.settings)
            self.state.manual_hold_until = time.time() + float(self.settings.get("manual_hold_h", 12)) * 3600
            self.state.expected_mode = {}
            self.runtime.note("Slim klimaatbeheer: handmatige Panasonic-modewijziging gedetecteerd; tijdelijke rustperiode.")

        hard = float(self.settings.get("hard_band_c", 1.0))
        hard_breach = any(z["current"] < z["target"] - hard or z["current"] > z["target"] + hard for z in zones)
        due = time.time() - self.state.last_decision_wall >= float(self.settings.get("decision_interval_h", 12)) * 3600
        guard_due = (
            any(str(z.get("mode", "")).casefold() == "off" for z in zones)
            and time.time() - self.state.last_guard_wall >= float(self.settings.get("guard_recheck_s", 900))
        )

        if due or hard_breach or guard_due:
            outside_hourly = self._outside_hourly()
            solar_hourly = self._solar_hourly(local_now, len(outside_hourly)) if self.settings.get("solar_gain_enabled") else []
            pv_precondition = bool(
                self.settings.get("solar_preconditioning_enabled")
                and (self.runtime.pv_w or 0) >= float(self.settings.get("precondition_min_pv_w", 3000))
            )
            decision = decide_mode(
                settings=self.settings, zones=zones, outside_hourly=outside_hourly,
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
        if not (allow_command and self.settings.get("control_enabled")):
            return False
        if self._has_fixed_heat_cool(zones):
            return False
        if time.time() < self.state.manual_hold_until and not decision.hard_override:
            return False

        local_day = local_now.date().isoformat()
        commands = self.state.commands_today if self.state.command_day == local_day else 0
        if commands >= int(self.settings.get("max_commands_per_day", 2)) and not decision.hard_override:
            return False
        if decision.desired_mode not in ("auto", "off"):
            return False
        if all(str(z["mode"]).casefold() == decision.desired_mode for z in zones):
            return False
        if self.state.last_command_wall and not decision.hard_override:
            elapsed_h = (time.time() - self.state.last_command_wall) / 3600.0
            if elapsed_h < float(self.settings.get("min_state_hold_h", 8.0)):
                return False
        return await self._send_mode(decision.desired_mode, zones)

    def _alerts(self, zones, confidences):
        alerts = []
        if self.state.fault:
            alerts.append({"severity": "error", "title": "Klimaatregeling geblokkeerd", "message": self.state.fault})
        if self.last_forecast_error:
            alerts.append({"severity": "warning", "title": "Weersvoorspelling", "message": self.last_forecast_error})
        if self._has_fixed_heat_cool(zones):
            alerts.append({"severity": "info", "title": "Handmatige Panasonic-stand", "message": "HEAT/COOL wordt nooit overschreven; SolarPilot blijft adviserend tot je zelf terugkeert naar AUTO/OFF."})
        model_conf = min(confidences) if confidences else 0.0
        min_conf = float(self.settings.get("model_confidence_min", .55))
        if self.settings.get("enabled") and model_conf < min_conf:
            alerts.append({"severity": "info", "title": "Model leert nog", "message": f"Thermisch model {model_conf:.0%}; automatische coast start pas vanaf {min_conf:.0%}."})
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
        overall_conf = min(confidences) if confidences else 0.0
        reliability = {
            "automatic_coast": {
                "confidence": round(overall_conf, 3),
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
        solar_nonzero = [x for x in self.last_solar_hourly if x > 0]
        solar_summary = {
            "enabled": bool(self.settings.get("solar_gain_enabled")),
            "forecast_hours": len(self.last_solar_hourly),
            "next_24h_kwh_proxy": round(sum(self.last_solar_hourly[:24]) / 1000.0, 2) if self.last_solar_hourly else None,
            "peak_w_proxy": round(max(solar_nonzero), 0) if solar_nonzero else 0.0,
            "note": "PV is alleen een lokale instralingsproxy voor het thermische model; niet hetzelfde als zonnewarmte door ramen.",
        }
        return {
            "enabled": bool(self.settings.get("enabled")),
            "control_enabled": bool(self.settings.get("control_enabled")),
            "zones": zones, "outside_c": self.last_outside,
            "forecast_hours": len(self.state.forecast), "forecast_error": self.last_forecast_error,
            "fault": self.state.fault,
            "decision": {
                "mode": d.desired_mode, "reason": d.reason, "hard_override": d.hard_override,
                "confidence": round(d.prediction_confidence, 3), "predicted_min_c": d.predicted_min_c,
                "predicted_max_c": d.predicted_max_c, "crossing_h": d.crossing_h,
                "required_lead_h": d.required_lead_h, "season_context": d.season_context,
                "season_strength": round(d.season_strength, 3), "comfort_direction": d.comfort_direction,
                "effective_coast_window_h": d.effective_coast_window_h,
                "solar_gain_used": d.solar_gain_used,
            },
            "season_context": d.season_context,
            "manual_fixed_mode": self._has_fixed_heat_cool(zones),
            "manual_hold_remaining_h": max(0.0, (self.state.manual_hold_until - time.time()) / 3600),
            "commands_today": self.state.commands_today if self.state.command_day == datetime.now().astimezone().date().isoformat() else 0,
            "last_command_mode": self.state.last_command_mode,
            "model_confidence": round(overall_conf, 3),
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
