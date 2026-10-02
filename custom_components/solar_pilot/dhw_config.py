"""Boiler options forms. All bindings are selected, never guessed from names."""
from copy import deepcopy
from uuid import uuid4
import voluptuous as vol
from homeassistant.helpers import selector
from .dhw import (DHW_DEFAULTS, DHW_NUMBERS, finite, validate_settings,
                  effective_base_target, normalized_settings, state_values)
from .wallbox import protected_entity
from .dhw_schedule import SCHEDULE_DEFAULTS, validate_schedule
from .first_install import apply_first_install_suggestions


def entity(domains, multiple=False):
    return selector.EntitySelector({"domain": domains, "multiple": multiple})


def num(low, high, step=1):
    return selector.NumberSelector({"min": low, "max": high, "step": step, "mode": "box"})


def optional(key, c):
    return vol.Optional(key, description={"suggested_value": c[key]}) if c.get(key) else vol.Optional(key)


def source_schema(c):
    schema = {
        vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
        optional("target_entity", c): entity(["water_heater", "climate", "number", "input_number"]),
        optional("temperature_entity", c): entity(["sensor", "water_heater", "climate", "input_number"]),
        optional("power_entity", c): entity(["sensor", "input_number"]),
        optional("cooling_entities", c): entity(["climate", "binary_sensor", "input_boolean"], True),
        optional("space_activity_entity", c): entity(["sensor", "binary_sensor"]),
        vol.Required("space_activity_active_states", default=c["space_activity_active_states"]): selector.TextSelector(),
        vol.Required("space_activity_inactive_states", default=c["space_activity_inactive_states"]): selector.TextSelector(),
        optional("hygiene_entity", c): entity(["binary_sensor", "input_boolean", "switch", "schedule"]),
        optional("manual_entity", c): entity(["binary_sensor", "input_boolean", "switch", "schedule", "select", "input_select"]),
        optional("manual_entities", c): entity(["binary_sensor", "input_boolean", "switch", "schedule", "select", "input_select"], True),
        vol.Required("manual_active_states", default=c["manual_active_states"]): selector.TextSelector(),
        vol.Required("safety_confirmed", default=c["safety_confirmed"]): selector.BooleanSelector(),
    }
    return vol.Schema(schema)


def sources_errors(hass, c, site, wallbox, devices):
    errors = {}
    if not c["enabled"] and not c.get("target_entity"):
        return errors
    if not c.get("target_entity"):
        errors["target_entity"] = "required"
    if c["enabled"] and not c["safety_confirmed"]:
        errors["safety_confirmed"] = "dhw_safety"
    if c["enabled"] and not site.get("pv_entity"):
        errors["base"] = "dhw_pv_required"
    ids = [c.get(k) for k in ("target_entity", "temperature_entity", "power_entity",
                              "space_activity_entity", "hygiene_entity", "manual_entity")]
    ids += c.get("manual_entities", [])
    ids += c.get("cooling_entities", [])
    if any(hass.states.get(i) is None for i in ids if i):
        errors["base"] = "entity_missing"
    if c.get("target_entity") and protected_entity(hass, wallbox, c["target_entity"]):
        errors["target_entity"] = "wallbox_duplicate"
    target = c.get("target_entity", "")
    for device in devices:
        if target and target in {device.get(k) for k in ("control_entity", "active_entity", "number_entity", "start_script", "stop_script")}:
            errors["target_entity"] = "duplicate"
    if target in c.get("cooling_entities", []):
        errors["cooling_entities"] = "duplicate"
    space_activity = c.get("space_activity_entity", "")
    if space_activity and (space_activity == target or space_activity in c.get("cooling_entities", [])):
        errors["space_activity_entity"] = "duplicate"
    if space_activity:
        active_raw = c.get("space_activity_active_states")
        inactive_raw = c.get("space_activity_inactive_states")
        active = state_values(active_raw)
        inactive = state_values(inactive_raw)
        if not isinstance(active_raw, str) or not active or active & inactive:
            errors["space_activity_active_states"] = "dhw_space_activity_states"
        if not isinstance(inactive_raw, str) or not inactive or active & inactive:
            errors["space_activity_inactive_states"] = "dhw_space_activity_states"
    reserved = {site.get(k) for k in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity")}
    reserved.update(d.get("power_entity") for d in devices)
    if wallbox.get("enabled"):
        reserved.add(wallbox.get("power_entity"))
    if c.get("power_entity"):
        obj = hass.states.get(c["power_entity"])
        if c["power_entity"] in reserved:
            errors["power_entity"] = "dedicated_meter"
        if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
            errors["power_entity"] = "power_unit"
    if not c.get("temperature_entity") and target.startswith(("number.", "input_number.")):
        errors["temperature_entity"] = "required"
    return errors


def rules_schema(c):
    schema = {vol.Required(k, default=c[k]): num(low, high, step)
              for k, (_, low, high, step, _) in DHW_NUMBERS.items()}
    schema[vol.Required("night_enabled", default=c["night_enabled"])] = selector.BooleanSelector()
    for k in ("night_start", "night_end"):
        schema[vol.Required(k, default=c[k])] = selector.TimeSelector()
    schema[vol.Required("hygiene_schedule_enabled", default=c["hygiene_schedule_enabled"])] = selector.BooleanSelector()
    schema[vol.Required("hygiene_weekdays", default=c["hygiene_weekdays"])] = selector.TextSelector()
    schema[vol.Required("hygiene_start", default=c["hygiene_start"])] = selector.TimeSelector()
    schema[vol.Required("hygiene_target_c", default=c["hygiene_target_c"])] = num(55, 65, 1)
    schema[vol.Required("hygiene_guard_before_s", default=c["hygiene_guard_before_s"])] = num(0, 7200, 60)
    schema[vol.Required("hygiene_guard_after_s", default=c["hygiene_guard_after_s"])] = num(900, 21600, 300)
    return vol.Schema(schema)


def stability_schema(c):
    schema = {}
    for k, low, high, step in (
            ("rise_delay_s", 0, 1800, 1), ("fall_delay_s", 0, 1800, 1),
            ("optional_raise_interval_s", 0, 21600, 60),
            ("pv_hysteresis_w", 0, 5000, 50), ("surplus_hysteresis_w", 0, 5000, 50),
            ("cooling_clear_s", 0, 3600, 1), ("stale_s", 30, 3600, 1),
            ("ack_timeout_s", 15, 600, 1), ("max_surplus_import_w", 0, 3000, 50)):
        schema[vol.Required(k, default=c[k])] = num(low, high, step)
    schema[vol.Required("respect_space_climate", default=c["respect_space_climate"])]=selector.BooleanSelector()
    schema[vol.Required("cooling_detection", default=c["cooling_detection"])]=selector.SelectSelector({"options": [
        {"value": "action", "label": "Actief koelen; koelmodus als actieve terugmelding ontbreekt"},
        {"value": "mode", "label": "Ook blokkeren zolang koelmodus ingeschakeld is"}]})
    schema[vol.Required("compensate_own_power", default=c["compensate_own_power"])]=selector.BooleanSelector()
    return vol.Schema(schema)


class DHWOptionsMixin:
    def _base_options(self):
        if not hasattr(self, "_options_base"):
            from copy import deepcopy
            self._options_base = deepcopy(dict(self.config_entry.options))
        return self._options_base

    async def async_step_dhw(self, user_input=None):
        rt = self._runtime()
        current = normalized_settings(self._base_options().get("dhw", {}))
        if not self._base_options().get("dhw"):
            current = apply_first_install_suggestions(self.hass, current, "dhw")
        if rt:
            current = {**current, **rt.dhw.settings, "enabled": rt.dhw.auto_enabled}
        c = getattr(self, "_dhw", current)
        errors = {}
        if user_input is not None:
            c = {**c, **{k: deepcopy(DHW_DEFAULTS[k]) for k in (
                "target_entity", "temperature_entity", "power_entity", "cooling_entities",
                "space_activity_entity", "space_activity_active_states", "space_activity_inactive_states",
                "hygiene_entity", "manual_entity", "manual_entities")}, **user_input}
            site = rt.settings if rt else {**self.config_entry.data, **self._base_options().get("settings", {})}
            errors = sources_errors(self.hass, c, site, self._base_options().get("wallbox", {}), self._base_options().get("devices", []))
            self._dhw = c
            if not errors:
                return await self.async_step_dhw_rules()
        return self.async_show_form(step_id="dhw", data_schema=source_schema(c), errors=errors)

    async def async_step_dhw_rules(self, user_input=None):
        c = self._dhw
        errors = {}
        if user_input is not None:
            c.update(user_input)
            errors = {k: v for k, v in validate_settings(c).items() if k in (*DHW_NUMBERS, "base", "night_start", "night_end",
                "hygiene_weekdays", "hygiene_start", "hygiene_target_c", "hygiene_guard_before_s", "hygiene_guard_after_s")}
            if not errors:
                return await self.async_step_dhw_comfort()
        return self.async_show_form(step_id="dhw_rules", data_schema=rules_schema(c), errors=errors)

    async def async_step_dhw_comfort(self, user_input=None):
        c = self._dhw
        errors = {}
        if user_input is not None:
            c.update(user_input)
            errors = validate_schedule(c)
            if not errors:
                return await self.async_step_dhw_stability()
        schema = {
            vol.Required("night_policy", default=c["night_policy"]): selector.SelectSelector({"options": [
                {"value": "base", "label": "Normaal doel behouden; Panasonic blijft zelfstandig regelen"},
                {"value": "minimum_until_solar", "label": "Wachten op stabiele zon voor extra buffer; normaal doel blijft staan"}]}),
        }
        for k in ("morning_enabled", "evening_enabled", "predictive_cooling_enabled"):
            schema[vol.Required(k, default=c[k])] = selector.BooleanSelector()
        for k in ("morning_time", "evening_fallback_start"):
            schema[vol.Required(k, default=c[k])] = selector.TimeSelector()
        for k, lo, hi, step in (
            ("morning_c",40,50,1),("morning_margin_c",0,3,.5),
            ("morning_max_lead_min",30,360,5),("morning_extra_lead_min",0,120,5),("morning_hold_min",0,120,5),
            ("tank_loss_fallback_c_h",.05,1.5,.05),("tank_heat_fallback_c_h",1,30,.5),
            ("evening_cap_c",50,59,1),("evening_lookahead_h",.5,6,.5),("evening_draw_buffer_c",0,10,.5),
            ("evening_margin_w",0,1000,50),("predictive_cooling_horizon_h",.5,6,.5)):
            schema[vol.Required(k, default=c[k])] = num(lo,hi,step)
        return self.async_show_form(step_id="dhw_comfort", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_dhw_stability(self, user_input=None):
        c = self._dhw
        errors = {}
        if user_input is not None:
            c.update(user_input)
            errors = validate_settings(c)
            # Validate current °C range/support using the same runtime adapter that
            # will send commands, without ever making a service call here.
            rt = self._runtime()
            if c.get("target_entity") and rt:
                from .dhw_runtime import DHWManager
                probe = DHWManager(rt)
                probe.config = probe.settings = c
                targets = [effective_base_target(c), c["solar_c"], c["surplus_c"], c["cooling_cap_c"]]
                if c.get("evening_enabled"):
                    targets.append(c["evening_cap_c"])
                if c.get("night_policy") == "minimum_until_solar":
                    targets.append(effective_base_target(c))
                for target in targets:
                    if probe.check_target(target):
                        errors["base"] = "dhw_target_invalid"
                if probe._temperature() is None:
                    errors["base"] = "dhw_temperature_invalid"
            if not errors:
                opts = deepcopy(dict(self._base_options()))
                opts["dhw"] = {**c, "config_revision": uuid4().hex}
                return await self._save(opts)
        return self.async_show_form(step_id="dhw_stability", data_schema=stability_schema(c), errors=errors)
