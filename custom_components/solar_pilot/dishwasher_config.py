"""Explicit AEG start-only configuration and local analysis settings."""
from copy import deepcopy
import voluptuous as vol
from homeassistant.helpers import selector
from .dishwasher import DISHWASHER_DEFAULTS, REFERENCE_KEYS, config_errors, normalize_config
from .analysis_export import ANALYSIS_DEFAULTS, SAFE_DOMAINS


def _entity(domains):
    return selector.EntitySelector({"domain": domains})


def _optional(key, d):
    return vol.Optional(key, description={"suggested_value": d[key]}) if d.get(key) else vol.Optional(key)


def _number(low, high, step=1):
    return selector.NumberSelector({"min": low, "max": high, "step": step, "mode": "box"})


class DishwasherOptionsMixin:
    def _base_options(self):
        if not hasattr(self, "_options_base"):
            from copy import deepcopy
            self._options_base = deepcopy(dict(self.config_entry.options))
        return self._options_base

    async def async_step_dishwasher_connection(self, user_input=None):
        d = normalize_config(self._device)
        errors = {}
        if user_input is not None:
            for key in ("power_entity", "dishwasher_alert_entity", "dishwasher_delay_entity", "dishwasher_phase_entity"):
                d.pop(key, None)
            d.update(user_input)
            errors = config_errors(self.hass, {**d, "dishwasher_mapping_confirmed": False})
            for other in self._base_options().get("devices", []):
                if other["id"] not in (d["id"], d.get("replaces_device_id")) and any(d.get(key) == other.get(key) and d.get(key) for key in ("start_button", "dishwasher_state_entity")):
                    errors["base"] = "duplicate"
            if d.get("power_entity"):
                obj = self.hass.states.get(d["power_entity"])
                if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
                    errors["power_entity"] = "power_unit"
                reserved = {self._site().get(key) for key in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity")}
                reserved.update(x.get("power_entity") for x in self._base_options().get("devices", []) if x["id"] not in (d["id"], d.get("replaces_device_id")))
                reserved.add(self._base_options().get("dhw", {}).get("power_entity"))
                reserved.add(self._base_options().get("wallbox", {}).get("power_entity"))
                if d["power_entity"] in reserved:
                    errors["power_entity"] = "dedicated_meter"
            if not errors:
                self._device = d
                return await self.async_step_dishwasher_states()
        schema = {}
        for key in REFERENCE_KEYS[:6]:
            domains = ["button"] if key == "start_button" else ["sensor", "select"] if key == "cycle_program_entity" else ["sensor", "binary_sensor"]
            schema[vol.Required(key, description={"suggested_value": d.get(key, "")})] = _entity(domains)
        schema[_optional("power_entity", d)] = _entity(["sensor"])
        schema[_optional("dishwasher_alert_entity", d)] = _entity(["sensor", "binary_sensor"])
        schema[_optional("dishwasher_phase_entity", d)] = _entity(["sensor"])
        schema[_optional("dishwasher_delay_entity", d)] = _entity(["sensor", "number"])
        return self.async_show_form(step_id="dishwasher_connection", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_dishwasher_states(self, user_input=None):
        d = normalize_config(self._device)
        errors = {}
        if user_input is not None:
            d.update(user_input)
            errors = config_errors(self.hass, d)
            if not errors:
                self._device = d
                return await self.async_step_device_behavior()
        schema = {}
        for key in ("dishwasher_ready_states", "dishwasher_running_states", "dishwasher_finished_states", "dishwasher_connected_states", "dishwasher_remote_states", "dishwasher_closed_states", "dishwasher_safe_states"):
            schema[vol.Required(key, default=d[key])] = selector.TextSelector()
        schema[vol.Required("dishwasher_stale_s", default=d["dishwasher_stale_s"])] = _number(60, 1800, 30)
        schema[vol.Required("dishwasher_ticket_hours", default=d["dishwasher_ticket_hours"])] = _number(1, 48)
        schema[vol.Required("dishwasher_arming_mode", default=d["dishwasher_arming_mode"])] = selector.SelectSelector({"options": [
            {"value": "app", "label": "Fysieke Delay Start / APP-knop — geen extra klaarzetten"},
            {"value": "manual", "label": "Handmatig één beurt klaarzetten in SolarPilot"}]})
        schema[vol.Required("dishwasher_start_deadline", default=d["dishwasher_start_deadline"])] = selector.TimeSelector()
        schema[vol.Required("dishwasher_after_deadline", default=d["dishwasher_after_deadline"])] = selector.SelectSelector({"options": [
            {"value": "next_day", "label": "Volgende dag, eerst zon (standaard)"},
            {"value": "same_day", "label": "Nog dezelfde dag, zo nodig direct netstroom"}]})
        schema[vol.Required("dishwasher_deadline_grid_allowed", default=d["dishwasher_deadline_grid_allowed"])] = selector.BooleanSelector()
        schema[vol.Required("dishwasher_deadline_grace_min", default=d["dishwasher_deadline_grace_min"])] = _number(1, 240)
        schema[vol.Required("dishwasher_alert_mode", default=d["dishwasher_alert_mode"])] = selector.SelectSelector({"options": [
            {"value": "state", "label": "Expliciete veilige alarmtoestanden"},
            {"value": "aeg_attributes", "label": "AEG DISH_ALARM-vlaggen; geen blokkering op alleen verbruiksmateriaal"}]})
        schema[vol.Required("dishwasher_priority_enabled", default=d["dishwasher_priority_enabled"])] = selector.BooleanSelector()
        schema[vol.Required("dishwasher_ev_solar_priority", default=d["dishwasher_ev_solar_priority"])] = selector.BooleanSelector()
        schema[vol.Required("dishwasher_mapping_confirmed", default=d["dishwasher_mapping_confirmed"])] = selector.BooleanSelector()
        if self._base_options().get("priority_board", {}).get("schema") in (1, 2):
            legacy = {"dishwasher_priority_enabled", "dishwasher_ev_solar_priority"}
            schema = {k:v for k,v in schema.items() if getattr(k,"schema",k) not in legacy}
        return self.async_show_form(step_id="dishwasher_states", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_analysis(self, user_input=None):
        c = {**ANALYSIS_DEFAULTS, **self._base_options().get("analysis", {})}
        errors = {}
        if user_input is not None:
            c = {**c, "extra_entities": [], **user_input}
            if any(not isinstance(e, str) or e.split(".")[0] not in SAFE_DOMAINS or self.hass.states.get(e) is None for e in c["extra_entities"]):
                errors["extra_entities"] = "entity_missing"
            if len(c["extra_entities"]) > 50:
                errors["extra_entities"] = "analysis_too_many"
            if not errors:
                opts = deepcopy(dict(self._base_options())); opts["analysis"] = c
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
            vol.Required("include_related_entities", default=c["include_related_entities"]): selector.BooleanSelector(),
            vol.Required("retention_days", default=c["retention_days"]): _number(1, 7),
            vol.Required("sample_interval_s", default=c["sample_interval_s"]): _number(60, 900, 60),
            vol.Optional("extra_entities", description={"suggested_value": c["extra_entities"]}): selector.EntitySelector({"domain": sorted(SAFE_DOMAINS), "multiple": True}),
        })
        return self.async_show_form(step_id="analysis", data_schema=schema, errors=errors)
