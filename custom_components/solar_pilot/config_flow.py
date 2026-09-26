"""UI-only configuration; adding/editing devices never enables them implicitly."""
from __future__ import annotations
from copy import deepcopy
import math
from uuid import uuid4
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import DEFAULTS, DEVICE_DEFAULTS, DOMAIN, NAME
from .wallbox import WALLBOX_DEFAULTS, READ_KEYS, state_set, conflicting_devices
from .house_first import HOUSE_DEFAULTS
from .dhw_config import DHWOptionsMixin
from .ems import CAPACITY_DEFAULTS, ECONOMY_DEFAULTS, FORECAST_DEFAULTS, PHASE_DEFAULTS
from .unified_planner import UNIFIED_PLANNER_DEFAULTS
from .pv_model import LOCAL_PV_DEFAULTS
from .battery_analysis import BATTERY_ANALYSIS_DEFAULTS
from .battery_fleet import BATTERY_DEFAULTS, BATTERY_FLEET_DEFAULTS
from .thermal_climate import SMART_CLIMATE_DEFAULTS
from .first_install import apply_first_install_suggestions


def entity(domains):
    return selector.EntitySelector({"domain": domains})


def num(low, high, step=1):
    return selector.NumberSelector({"min": low, "max": high, "step": step, "mode": "box"})


def optional(key, defaults):
    return vol.Optional(key, description={"suggested_value": defaults[key]}) if defaults.get(key) else vol.Optional(key)


def merged_site(values):
    return {**DEFAULTS, **(values or {})}


def initial_site_schema(values):
    """Short first-run form; safe operational defaults stay hidden until needed."""
    v = merged_site(values)
    return vol.Schema({
        vol.Required("grid_entity", description={"suggested_value": v.get("grid_entity", "")}): entity(["sensor", "input_number"]),
        vol.Required("grid_sign", default=v["grid_sign"]): selector.SelectSelector({"options": [
            {"value": "import_positive", "label": "Eén netto-meter: positief = afname"},
            {"value": "export_positive", "label": "Eén netto-meter: positief = injectie"},
            {"value": "separate", "label": "Twee meters: aparte afname en injectie"}]}),
        optional("export_entity", v): entity(["sensor", "input_number"]),
        optional("pv_entity", v): entity(["sensor", "input_number"]),
    })


def sources_schema(values):
    """Measurements only; keep control policy/timing out of the basic source form."""
    v = merged_site(values)
    return vol.Schema({
        vol.Required("grid_entity", description={"suggested_value": v.get("grid_entity", "")}): entity(["sensor", "input_number"]),
        vol.Required("grid_sign", default=v["grid_sign"]): selector.SelectSelector({"options": [
            {"value": "import_positive", "label": "Eén netto-meter: positief = afname"},
            {"value": "export_positive", "label": "Eén netto-meter: positief = injectie"},
            {"value": "separate", "label": "Twee meters: aparte afname en injectie"}]}),
        optional("export_entity", v): entity(["sensor", "input_number"]),
        optional("pv_entity", v): entity(["sensor", "input_number"]),
        optional("battery_power_entity", v): entity(["sensor", "input_number"]),
        vol.Required("battery_sign", default=v["battery_sign"]): selector.SelectSelector({"options": [
            {"value": "discharge_positive", "label": "Positief = ontladen"},
            {"value": "charge_positive", "label": "Positief = laden"}]}),
        optional("battery_soc_entity", v): entity(["sensor", "input_number"]),
    })


def power_policy_schema(values):
    v = merged_site(values)
    return vol.Schema({
        vol.Required("reserve_w", default=v["reserve_w"]): num(0, 5000, 10),
        vol.Required("max_import_w", default=v["max_import_w"]): num(0, 50000, 50),
        vol.Required("battery_min_soc", default=v["battery_min_soc"]): num(0, 100),
    })


def timing_schema(values):
    v = merged_site(values)
    return vol.Schema({
        vol.Required("interval_s", default=v["interval_s"]): num(2, 60),
        vol.Required("settle_s", default=v["settle_s"]): num(5, 300),
        vol.Required("stale_s", default=v["stale_s"]): num(15, 1800),
        vol.Required("filter_s", default=v["filter_s"]): num(1, 300),
        vol.Required("fault_grace_s", default=v["fault_grace_s"]): num(0, 300),
    })

def site_errors(hass, values):
    values = merged_site(values)
    errors = {}
    for key in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity"):
        entity_id = values.get(key)
        if not entity_id:
            continue
        obj = hass.states.get(entity_id)
        if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
            errors[key] = "power_unit"
    if values["grid_sign"] == "separate" and not values.get("export_entity"):
        errors["export_entity"] = "required"
    if values["grid_sign"] == "separate" and values.get("export_entity") == values.get("grid_entity"):
        errors["export_entity"] = "duplicate"
    if values.get("battery_soc_entity"):
        obj = hass.states.get(values["battery_soc_entity"])
        if obj is None or obj.attributes.get("unit_of_measurement") != "%":
            errors["battery_soc_entity"] = "soc_unit"
        if not values.get("battery_power_entity"):
            errors["battery_power_entity"] = "battery_power_required"
    if values["stale_s"] < values["interval_s"] * 2:
        errors["stale_s"] = "timing"
    return errors


def wallbox_errors_for(hass, c, site, devices):
    errors = {}
    if not c.get("enabled"):
        return errors
    if not c.get("power_entity"):
        errors["power_entity"] = "required"
    else:
        obj = hass.states.get(c["power_entity"])
        if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
            errors["power_entity"] = "power_unit"
    if not c.get("status_entity") and not c.get("demand_entity"):
        errors["base"] = "wallbox_demand_required"
    for key in READ_KEYS:
        if c.get(key) and hass.states.get(c[key]) is None:
            errors[key] = "entity_missing"
    if state_set(c.get("demand_states", "")) & state_set(c.get("idle_states", "")):
        errors["base"] = "wallbox_state_overlap"
    if conflicting_devices(hass, c, devices):
        errors["base"] = "wallbox_duplicate"
    if c.get("power_entity") in {site.get(k) for k in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity")} - {None, ""}:
        errors["power_entity"] = "wallbox_meter_duplicate"
    if c.get("reclaim_max_age_s", 0) > c.get("stale_s", 0) or c.get("handover_confirm_s", 0) >= c.get("handover_s", 0):
        errors["handover_s"] = "timing"
    if c.get("stable_s", 0) < 30 or c.get("cooldown_s", 0) < c.get("stable_s", 0):
        errors["cooldown_s"] = "timing"
    return errors


class SolarPilotFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        form_values = user_input or apply_first_install_suggestions(self.hass, {}, "site")
        candidate = merged_site(form_values)
        errors = site_errors(self.hass, candidate) if user_input is not None else {}
        if user_input is not None and not errors:
            return self.async_create_entry(title=NAME, data=candidate)
        return self.async_show_form(step_id="user", data_schema=initial_site_schema(form_values), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SolarPilotOptions()


class SolarPilotOptions(DHWOptionsMixin, config_entries.OptionsFlow):
    def __init__(self):
        self._device = {}
        self._editing = None
        self._battery = {}
        self._battery_editing = None

    def _runtime(self):
        return getattr(self.config_entry, "runtime_data", None)

    def _busy(self):
        rt = self._runtime()
        return rt is not None and not rt.editable

    def _site(self):
        return {**DEFAULTS, **self.config_entry.data, **self.config_entry.options.get("settings", {})}

    async def _save(self, options):
        rt = self._runtime()
        if rt is None:
            return self.async_create_entry(title="", data=options)
        async with rt._lock:
            if not rt.editable:
                return self.async_abort(reason="busy")
            return self.async_create_entry(title="", data=options)

    async def async_step_init(self, user_input=None):
        if self._busy():
            return self.async_abort(reason="busy")
        return self.async_show_menu(step_id="init", menu_options=[
            "overview", "energy_hub", "loads_hub", "comfort_hub",
            "storage_hub", "intelligence_hub", "advanced_hub"
        ])

    async def async_step_overview(self, user_input=None):
        if user_input is not None:
            return await self.async_step_init()
        rt = self._runtime()
        opts = self.config_entry.options
        site = self._site()
        ems = rt.ems_overview() if rt else {}
        conflicts = ems.get("legacy_conflicts", [])
        placeholders = {
            "mode": ({"observe":"Observatie", "solar":"Zonnestroom", "paused":"Pauze"}.get(rt.mode, rt.mode) if rt else "Niet geladen"),
            "grid": "gekoppeld" if site.get("grid_entity") else "ontbreekt",
            "pv": "gekoppeld" if site.get("pv_entity") else "niet gekoppeld",
            "devices": str(len(opts.get("devices", []))),
            "dhw": "actief" if opts.get("dhw", {}).get("enabled") else ("gekoppeld" if opts.get("dhw", {}).get("target_entity") else "niet gekoppeld"),
            "climate": "regeling aan" if opts.get("smart_climate", {}).get("control_enabled") else ("advies" if opts.get("smart_climate", {}).get("enabled") else "uit"),
            "wallbox": "monitor actief" if opts.get("wallbox", {}).get("enabled") else "uit",
            "batteries": str(len(opts.get("batteries", []))),
            "conflicts": "geen" if not conflicts else ", ".join(x.get("name", "onbekend") for x in conflicts[:3]),
        }
        return self.async_show_form(step_id="overview", data_schema=vol.Schema({}), description_placeholders=placeholders)

    async def async_step_energy_hub(self, user_input=None):
        return self.async_show_menu(step_id="energy_hub", menu_options=["settings", "power_policy", "capacity", "phase", "economy"])

    async def async_step_loads_hub(self, user_input=None):
        return self.async_show_menu(step_id="loads_hub", menu_options=["add", "edit", "remove"])

    async def async_step_comfort_hub(self, user_input=None):
        return self.async_show_menu(step_id="comfort_hub", menu_options=["dhw", "smart_climate", "smart_climate_advanced"])

    async def async_step_storage_hub(self, user_input=None):
        return self.async_show_menu(step_id="storage_hub", menu_options=["wallbox", "battery", "battery_analysis"])

    async def async_step_intelligence_hub(self, user_input=None):
        return self.async_show_menu(step_id="intelligence_hub", menu_options=["forecast", "local_pv", "planner"])

    async def async_step_advanced_hub(self, user_input=None):
        return self.async_show_menu(step_id="advanced_hub", menu_options=["timing", "phase_learning", "wallbox_advanced", "system_info"])

    async def async_step_system_info(self, user_input=None):
        if user_input is not None:
            return await self.async_step_init()
        from .current_guide import GUIDE_VERSION, GUIDE_UPDATED
        return self.async_show_form(
            step_id="system_info", data_schema=vol.Schema({}),
            description_placeholders={"version": GUIDE_VERSION, "updated": GUIDE_UPDATED}
        )

    async def async_step_settings(self, user_input=None):
        current = self._site()
        candidate = {**current, **(user_input or {})}
        errors = site_errors(self.hass, candidate) if user_input is not None else {}
        if user_input is not None and not errors:
            opts = deepcopy(dict(self.config_entry.options))
            previous = {**current, **opts.get("settings", {})}
            cleared = {k: "" for k in ("export_entity", "pv_entity", "battery_power_entity", "battery_soc_entity")}
            opts["settings"] = {**previous, **cleared, **user_input}
            return await self._save(opts)
        return self.async_show_form(step_id="settings", data_schema=sources_schema(user_input or current), errors=errors)

    async def async_step_power_policy(self, user_input=None):
        current = self._site()
        if user_input is not None:
            opts = deepcopy(dict(self.config_entry.options))
            opts["settings"] = {**current, **opts.get("settings", {}), **user_input}
            return await self._save(opts)
        return self.async_show_form(step_id="power_policy", data_schema=power_policy_schema(current), errors={})

    async def async_step_timing(self, user_input=None):
        current = self._site()
        errors = {}
        candidate = {**current, **(user_input or {})}
        if user_input is not None:
            if candidate["stale_s"] < candidate["interval_s"] * 2:
                errors["stale_s"] = "timing"
            if candidate["filter_s"] > candidate["stale_s"]:
                errors["filter_s"] = "timing"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options))
                opts["settings"] = {**current, **opts.get("settings", {}), **user_input}
                return await self._save(opts)
        return self.async_show_form(step_id="timing", data_schema=timing_schema(user_input or current), errors=errors)

    async def async_step_capacity(self, user_input=None):
        c = {**CAPACITY_DEFAULTS, **self.config_entry.options.get("capacity", {})}
        if not self.config_entry.options.get("capacity"):
            c = apply_first_install_suggestions(self.hass, c, "capacity")
        errors = {}
        if user_input is not None:
            c = {**CAPACITY_DEFAULTS, **user_input}
            if c["enabled"]:
                for key in ("average_demand_entity", "monthly_peak_entity"):
                    if not c.get(key):
                        errors[key] = "required"
                    else:
                        obj = self.hass.states.get(c[key])
                        if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
                            errors[key] = "power_unit"
            floor = c["billing_floor_w"] if c.get("respect_billing_floor") else 0
            if c["margin_w"] >= max(c["target_peak_w"], floor):
                errors["margin_w"] = "range"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options))
                opts["capacity"] = c
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
            optional("average_demand_entity", c): entity(["sensor", "input_number"]),
            optional("monthly_peak_entity", c): entity(["sensor", "input_number"]),
            vol.Required("target_peak_w", default=c["target_peak_w"]): num(500, 50000, 50),
            vol.Required("adaptive_to_month_peak", default=c["adaptive_to_month_peak"]): selector.BooleanSelector(),
            vol.Required("respect_billing_floor", default=c["respect_billing_floor"]): selector.BooleanSelector(),
            vol.Required("billing_floor_w", default=c["billing_floor_w"]): num(0, 10000, 50),
            vol.Required("margin_w", default=c["margin_w"]): num(0, 2000, 50),
            vol.Required("minimum_elapsed_s", default=c["minimum_elapsed_s"]): num(0, 300, 10),
            vol.Required("stale_s", default=c["stale_s"]): num(30, 900, 10),
            vol.Required("respect_optional_dhw", default=c["respect_optional_dhw"]): selector.BooleanSelector(),
        })
        return self.async_show_form(step_id="capacity", data_schema=schema, errors=errors)

    async def async_step_economy(self, user_input=None):
        c = {**ECONOMY_DEFAULTS, **self.config_entry.options.get("economy", {})}
        if not self.config_entry.options.get("economy"):
            c = apply_first_install_suggestions(self.hass, c, "economy")
        errors = {}
        if user_input is not None:
            c = {**ECONOMY_DEFAULTS, **user_input}
            for key in ("import_price_entity", "export_price_entity"):
                if c.get(key) and self.hass.states.get(c[key]) is None:
                    errors[key] = "entity_missing"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options))
                opts["economy"] = c
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
            optional("import_price_entity", c): entity(["sensor", "input_number"]),
            optional("export_price_entity", c): entity(["sensor", "input_number"]),
            vol.Required("fixed_import_eur_kwh", default=c["fixed_import_eur_kwh"]): num(-2, 5, 0.01),
            vol.Required("fixed_export_eur_kwh", default=c["fixed_export_eur_kwh"]): num(-2, 5, 0.01),
        })
        return self.async_show_form(step_id="economy", data_schema=schema, errors=errors)

    async def async_step_forecast(self, user_input=None):
        c = {**FORECAST_DEFAULTS, **self.config_entry.options.get("forecast", {})}
        if not self.config_entry.options.get("forecast"):
            c = apply_first_install_suggestions(self.hass, c, "forecast")
        errors = {}
        if user_input is not None:
            c = {**FORECAST_DEFAULTS, **user_input}
            if c["enabled"]:
                for key in ("current_hour_entity", "next_hour_entity", "remaining_today_entity", "tomorrow_entity"):
                    if c.get(key):
                        obj = self.hass.states.get(c[key])
                        if obj is None or obj.attributes.get("unit_of_measurement") != "kWh":
                            errors[key] = "energy_unit"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options))
                opts["forecast"] = c
                return await self._save(opts)
        schema = {vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector()}
        for key in ("current_hour_entity", "next_hour_entity", "remaining_today_entity", "tomorrow_entity"):
            schema[optional(key, c)] = entity(["sensor", "input_number"])
        schema[vol.Required("stale_s", default=c["stale_s"])] = num(300, 21600, 300)
        return self.async_show_form(step_id="forecast", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_local_pv(self, user_input=None):
        c = {**LOCAL_PV_DEFAULTS, **self.config_entry.options.get("local_pv", {})}
        if not self.config_entry.options.get("local_pv"):
            c = apply_first_install_suggestions(self.hass, c, "local_pv")
        errors = {}
        if user_input is not None:
            c = {**LOCAL_PV_DEFAULTS, **user_input}
            if c["enabled"]:
                power_id = c.get("forecast_power_entity")
                obj = self.hass.states.get(power_id) if power_id else None
                if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
                    errors["forecast_power_entity"] = "power_unit"
                if c.get("sun_entity") and self.hass.states.get(c["sun_entity"]) is None:
                    errors["sun_entity"] = "entity_missing"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options)); opts["local_pv"] = c
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
            optional("forecast_power_entity", c): entity(["sensor", "input_number"]),
            optional("sun_entity", c): entity(["sun"]),
            vol.Required("seed_enabled", default=c["seed_enabled"]): selector.BooleanSelector(),
            vol.Required("sample_interval_s", default=c["sample_interval_s"]): num(60, 3600, 60),
            vol.Required("min_forecast_w", default=c["min_forecast_w"]): num(0, 10000, 50),
            vol.Required("min_elevation_deg", default=c["min_elevation_deg"]): num(-5, 45, 1),
            vol.Required("azimuth_bin_deg", default=c["azimuth_bin_deg"]): num(1, 30, 1),
            vol.Required("elevation_bin_deg", default=c["elevation_bin_deg"]): num(1, 20, 1),
            vol.Required("min_days", default=c["min_days"]): num(2, 30, 1),
            vol.Required("min_confidence", default=c["min_confidence"]): num(0.1, 0.95, 0.05),
            vol.Required("shadow_factor", default=c["shadow_factor"]): num(0.2, 1.2, 0.02),
            vol.Required("shadow_drop", default=c["shadow_drop"]): num(0.05, 0.8, 0.02),
            vol.Required("recovery_delta", default=c["recovery_delta"]): num(0.05, 0.8, 0.02),
            vol.Required("horizon_min", default=c["horizon_min"]): num(15, 360, 15),
            vol.Required("projection_step_min", default=c["projection_step_min"]): num(5, 60, 5),
        })
        return self.async_show_form(step_id="local_pv", data_schema=schema, errors=errors)

    async def async_step_planner(self, user_input=None):
        c = {**UNIFIED_PLANNER_DEFAULTS, **self.config_entry.options.get("planner", {})}
        errors = {}
        if user_input is not None:
            c = {**UNIFIED_PLANNER_DEFAULTS, **user_input}
            if c["adaptive_power_max_multiplier"] < 1:
                errors["adaptive_power_max_multiplier"] = "range"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options))
                opts["planner"] = c
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
            vol.Required("horizon_h", default=c["horizon_h"]): num(12, 72, 1),
            vol.Required("slot_min", default=c["slot_min"]): selector.SelectSelector({"options":[15,30,60],"mode":"dropdown"}),
            vol.Required("replan_min", default=c["replan_min"]): selector.SelectSelector({"options":[15,30,60],"mode":"dropdown"}),
            vol.Required("pv_reserve_w", default=c["pv_reserve_w"]): num(0, 3000, 50),
            vol.Required("base_load_learning", default=c["base_load_learning"]): selector.BooleanSelector(),
            vol.Required("base_load_min_days", default=c["base_load_min_days"]): num(2, 30, 1),
            vol.Required("price_optimisation", default=c["price_optimisation"]): selector.BooleanSelector(),
            vol.Required("capacity_penalty_enabled", default=c["capacity_penalty_enabled"]): selector.BooleanSelector(),
            vol.Required("capacity_penalty_eur_kwh", default=c["capacity_penalty_eur_kwh"]): num(0, 5, 0.05),
            vol.Required("battery_advisory", default=c["battery_advisory"]): selector.BooleanSelector(),
            vol.Required("quality_tracking", default=c["quality_tracking"]): selector.BooleanSelector(),
            vol.Required("quality_retention_days", default=c["quality_retention_days"]): num(7, 90, 1),
            vol.Required("replay_enabled", default=c["replay_enabled"]): selector.BooleanSelector(),
            vol.Required("replay_retention_days", default=c["replay_retention_days"]): num(3, 30, 1),
            vol.Required("early_grid_enabled", default=c["early_grid_enabled"]): selector.BooleanSelector(),
            vol.Required("cheap_grid_limit_eur_kwh", default=c["cheap_grid_limit_eur_kwh"]): num(-2, 5, 0.01),
            vol.Required("early_grid_requires_forecast_shortfall", default=c["early_grid_requires_forecast_shortfall"]): selector.BooleanSelector(),
            vol.Required("adaptive_power_guard", default=c["adaptive_power_guard"]): selector.BooleanSelector(),
            vol.Required("adaptive_power_min_samples", default=c["adaptive_power_min_samples"]): num(5, 120, 1),
            vol.Required("adaptive_power_max_multiplier", default=c["adaptive_power_max_multiplier"]): num(1, 5, 0.1),
        })
        return self.async_show_form(step_id="planner", data_schema=schema, errors=errors)

    async def async_step_phase(self, user_input=None):
        """Basic phase monitoring/control. Learning details live in Advanced."""
        current = {**PHASE_DEFAULTS, **self.config_entry.options.get("phase", {})}
        if not self.config_entry.options.get("phase"):
            current = apply_first_install_suggestions(self.hass, current, "phase")
        c = {**current, **(user_input or {})}
        errors = {}
        if user_input is not None:
            if c["enabled"]:
                for key in ("phase_1_entity", "phase_2_entity", "phase_3_entity"):
                    if not c.get(key):
                        errors[key] = "required"
                    else:
                        obj = self.hass.states.get(c[key])
                        if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
                            errors[key] = "power_unit"
            if c["margin_w"] >= c["limit_w"]:
                errors["margin_w"] = "range"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options))
                opts["phase"] = {**current, **user_input}
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
            optional("phase_1_entity", c): entity(["sensor", "input_number"]),
            optional("phase_2_entity", c): entity(["sensor", "input_number"]),
            optional("phase_3_entity", c): entity(["sensor", "input_number"]),
            vol.Required("limit_w", default=c["limit_w"]): num(1000, 30000, 50),
            vol.Required("margin_w", default=c["margin_w"]): num(0, 5000, 50),
            vol.Required("start_headroom_w", default=c["start_headroom_w"]): num(0, 10000, 50),
            vol.Required("control_starts", default=c["control_starts"]): selector.BooleanSelector(),
            vol.Required("shed_on_overlimit", default=c["shed_on_overlimit"]): selector.BooleanSelector(),
        })
        return self.async_show_form(step_id="phase", data_schema=schema, errors=errors)

    async def async_step_phase_learning(self, user_input=None):
        current = {**PHASE_DEFAULTS, **self.config_entry.options.get("phase", {})}
        c = {**current, **(user_input or {})}
        errors = {}
        if user_input is not None:
            for entity_id in c.get("monitor_power_entities", []) or []:
                obj = self.hass.states.get(entity_id)
                if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
                    errors["monitor_power_entities"] = "power_unit"
                    break
            if c["learning_settle_s"] >= c["learning_max_window_s"]:
                errors["learning_max_window_s"] = "timing"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options))
                opts["phase"] = {**current, **user_input}
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("learning_enabled", default=c["learning_enabled"]): selector.BooleanSelector(),
            vol.Optional("monitor_power_entities", default=c.get("monitor_power_entities", [])): selector.EntitySelector({"domain": ["sensor", "input_number"], "multiple": True}),
            vol.Required("learning_min_delta_w", default=c["learning_min_delta_w"]): num(50, 5000, 50),
            vol.Required("learning_settle_s", default=c["learning_settle_s"]): num(2, 120, 1),
            vol.Required("learning_max_window_s", default=c["learning_max_window_s"]): num(10, 300, 5),
            vol.Required("learning_min_samples", default=c["learning_min_samples"]): num(2, 50, 1),
            vol.Required("learning_min_confidence", default=c["learning_min_confidence"]): num(0.5, 0.99, 0.01),
            vol.Required("use_learned_device_map", default=c["use_learned_device_map"]): selector.BooleanSelector(),
            vol.Required("stale_s", default=c["stale_s"]): num(15, 900, 5),
        })
        return self.async_show_form(step_id="phase_learning", data_schema=schema, errors=errors)

    async def async_step_battery_analysis(self, user_input=None):
        c = {**BATTERY_ANALYSIS_DEFAULTS, **self.config_entry.options.get("battery_analysis", {})}
        errors = {}
        def parse_list(value, low, high):
            try:
                vals = [float(x.strip()) for x in str(value).split(",") if x.strip()]
            except ValueError:
                return None
            return vals if vals and all(low <= x <= high for x in vals) else None
        display = {**c, "capacities_kwh": ",".join(f"{x:g}" for x in c.get("capacities_kwh", [])),
                   "powers_kw": ",".join(f"{x:g}" for x in c.get("powers_kw", []))}
        if user_input is not None:
            capacities = parse_list(user_input.get("capacities_kwh", ""), 1, 100)
            powers = parse_list(user_input.get("powers_kw", ""), .5, 50)
            if capacities is None: errors["capacities_kwh"] = "range"
            if powers is None: errors["powers_kw"] = "range"
            if not errors:
                c = {**BATTERY_ANALYSIS_DEFAULTS, **user_input, "capacities_kwh": capacities, "powers_kw": powers}
                opts = deepcopy(dict(self.config_entry.options)); opts["battery_analysis"] = c
                return await self._save(opts)
            display = {**user_input}
        schema = vol.Schema({
            vol.Required("enabled", default=display.get("enabled", True)): selector.BooleanSelector(),
            vol.Required("seed_enabled", default=display.get("seed_enabled", True)): selector.BooleanSelector(),
            vol.Required("roundtrip_efficiency", default=display.get("roundtrip_efficiency", .9)): num(.5, 1.0, .01),
            vol.Required("reserve_pct", default=display.get("reserve_pct", 0)): num(0, 90, 1),
            vol.Required("capacities_kwh", default=display.get("capacities_kwh", "5,10,15,20")): selector.TextSelector(),
            vol.Required("powers_kw", default=display.get("powers_kw", "3,5,10")): selector.TextSelector(),
        })
        return self.async_show_form(step_id="battery_analysis", data_schema=schema, errors=errors)


    async def async_step_smart_climate(self, user_input=None):
        """Primary climate choices: Panasonic keeps HEAT/COOL ownership."""
        current = {**SMART_CLIMATE_DEFAULTS, **self.config_entry.options.get("smart_climate", {})}
        if not self.config_entry.options.get("smart_climate"):
            current = apply_first_install_suggestions(self.hass, current, "smart_climate")
        c = {**current, **(user_input or {})}
        errors = {}
        if user_input is not None:
            if c["enabled"]:
                if not c.get("zone_entities"):
                    errors["zone_entities"] = "required"
                for entity_id in c.get("zone_entities", []) or []:
                    obj = self.hass.states.get(entity_id)
                    modes = {str(x).casefold() for x in (obj.attributes.get("hvac_modes", []) if obj else [])}
                    if obj is None or not {"auto", "off"}.issubset(modes):
                        errors["zone_entities"] = "climate_modes"
                        break
                weather_id = c.get("weather_entity")
                if not weather_id or self.hass.states.get(weather_id) is None:
                    errors["weather_entity"] = "required"
                outside_id = c.get("outside_temp_entity")
                if outside_id:
                    obj = self.hass.states.get(outside_id)
                    if obj is None or obj.attributes.get("unit_of_measurement") != "°C":
                        errors["outside_temp_entity"] = "temperature_unit"
            if c["hard_band_c"] < c["soft_band_c"]:
                errors["hard_band_c"] = "range"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options)); opts["smart_climate"] = {**current, **user_input}
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
            vol.Required("control_enabled", default=c["control_enabled"]): selector.BooleanSelector(),
            vol.Optional("zone_entities", default=c.get("zone_entities", [])): selector.EntitySelector({"domain": ["climate"], "multiple": True}),
            optional("weather_entity", c): entity(["weather"]),
            optional("outside_temp_entity", c): entity(["sensor", "input_number"]),
            vol.Required("soft_band_c", default=c["soft_band_c"]): num(0.2, 3, 0.1),
            vol.Required("hard_band_c", default=c["hard_band_c"]): num(0.3, 5, 0.1),
            vol.Required("decision_interval_h", default=c["decision_interval_h"]): num(6, 24, 1),
            vol.Required("forecast_horizon_h", default=c["forecast_horizon_h"]): num(12, 72, 1),
        })
        return self.async_show_form(step_id="smart_climate", data_schema=schema, errors=errors)

    async def async_step_smart_climate_advanced(self, user_input=None):
        current = {**SMART_CLIMATE_DEFAULTS, **self.config_entry.options.get("smart_climate", {})}
        c = {**current, **(user_input or {})}
        errors = {}
        if user_input is not None:
            if c["learning_min_days"] < 2 or c["learning_min_samples"] < 6:
                errors["learning_min_samples"] = "range"
            if c["hard_band_c"] < c["soft_band_c"]:
                errors["hard_band_c"] = "range"
            if c["season_extreme_delta_c"] <= c["shoulder_band_c"]:
                errors["season_extreme_delta_c"] = "range"
            if c["solar_preconditioning_enabled"] and not self._site().get("pv_entity"):
                errors["precondition_min_pv_w"] = "dhw_pv_required"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options)); opts["smart_climate"] = {**current, **user_input}
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("forecast_refresh_s", default=c["forecast_refresh_s"]): num(900, 21600, 300),
            vol.Required("shoulder_band_c", default=c["shoulder_band_c"]): num(0.5, 6, 0.5),
            vol.Required("season_extreme_delta_c", default=c["season_extreme_delta_c"]): num(1.5, 12, 0.5),
            vol.Required("allow_winter_summer_coast", default=c["allow_winter_summer_coast"]): selector.BooleanSelector(),
            vol.Required("min_coast_window_h", default=c["min_coast_window_h"]): num(2, 24, 1),
            vol.Required("min_state_hold_h", default=c["min_state_hold_h"]): num(2, 24, 1),
            vol.Required("thermal_start_margin_h", default=c["thermal_start_margin_h"]): num(0, 12, 0.5),
            vol.Required("manual_hold_h", default=c["manual_hold_h"]): num(1, 72, 1),
            vol.Required("sample_interval_s", default=c["sample_interval_s"]): num(300, 3600, 300),
            vol.Required("learning_min_samples", default=c["learning_min_samples"]): num(6, 240, 1),
            vol.Required("learning_min_days", default=c["learning_min_days"]): num(2, 30, 1),
            vol.Required("model_confidence_min", default=c["model_confidence_min"]): num(.25, .95, .05),
            vol.Required("solar_preconditioning_enabled", default=c["solar_preconditioning_enabled"]): selector.BooleanSelector(),
            vol.Required("precondition_min_pv_w", default=c["precondition_min_pv_w"]): num(0, 20000, 100),
            vol.Required("solar_precondition_extra_lead_h", default=c["solar_precondition_extra_lead_h"]): num(0, 12, 0.5),
            vol.Required("max_commands_per_day", default=c["max_commands_per_day"]): num(1, 6, 1),
            vol.Required("stale_s", default=c["stale_s"]): num(300, 7200, 60),
        })
        return self.async_show_form(step_id="smart_climate_advanced", data_schema=schema, errors=errors)

    async def async_step_battery(self, user_input=None):
        return self.async_show_menu(step_id="battery", menu_options=["battery_settings", "battery_add", "battery_edit", "battery_remove"])

    async def async_step_battery_settings(self, user_input=None):
        c = {**BATTERY_FLEET_DEFAULTS, **self.config_entry.options.get("battery_fleet", {})}
        errors = {}
        if user_input is not None:
            c = {**BATTERY_FLEET_DEFAULTS, **user_input}
            if c["discharge_reserve_w"] > self.config_entry.options.get("settings", {}).get("max_import_w", self.config_entry.data.get("max_import_w", 3500)):
                errors["discharge_reserve_w"] = "range"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options)); opts["battery_fleet"] = c
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
            vol.Required("control_enabled", default=c["control_enabled"]): selector.BooleanSelector(),
            vol.Required("strategy", default=c["strategy"]): selector.SelectSelector({"options":[
                {"value":"advisory","label":"Alleen advies / zelfconsumptie berekenen"}, {"value":"loads_first","label":"Flexibele lasten eerst, batterij gebruikt rest"},
                {"value":"peak_shaving","label":"Vooral kwartierpiek afvlakken"}, {"value":"hybrid","label":"Zelfconsumptie + kwartierpiek"}]}),
            vol.Required("grid_target_w", default=c["grid_target_w"]): num(-3000, 3000, 50),
            vol.Required("charge_reserve_w", default=c["charge_reserve_w"]): num(0, 5000, 50),
            vol.Required("discharge_reserve_w", default=c["discharge_reserve_w"]): num(0, 5000, 50),
            vol.Required("allow_grid_charge", default=c["allow_grid_charge"]): selector.BooleanSelector(),
            vol.Required("allow_export_discharge", default=c["allow_export_discharge"]): selector.BooleanSelector(),
            vol.Required("command_min_interval_s", default=c["command_min_interval_s"]): num(10, 600, 10),
            vol.Required("settle_s", default=c["settle_s"]): num(10, 600, 10),
            vol.Required("ack_timeout_s", default=c["ack_timeout_s"]): num(30, 900, 10),
            vol.Required("target_tolerance_w", default=c["target_tolerance_w"]): num(50, 2000, 50),
        })
        return self.async_show_form(step_id="battery_settings", data_schema=schema, errors=errors)

    def _battery_choice_schema(self):
        return vol.Schema({vol.Required("battery_id"): selector.SelectSelector({"options":[
            {"value": b["id"], "label": b.get("name", b["id"])} for b in self.config_entry.options.get("batteries", [])]})})

    async def async_step_battery_add(self, user_input=None):
        self._battery_editing = None
        self._battery = {**BATTERY_DEFAULTS, "id": uuid4().hex}
        return await self.async_step_battery_profile()

    async def async_step_battery_edit(self, user_input=None):
        batteries = self.config_entry.options.get("batteries", [])
        if not batteries:
            return self.async_abort(reason="no_batteries")
        if user_input is not None:
            self._battery_editing = user_input["battery_id"]
            self._battery = deepcopy(next(b for b in batteries if b["id"] == self._battery_editing))
            return await self.async_step_battery_profile()
        return self.async_show_form(step_id="battery_edit", data_schema=self._battery_choice_schema())

    async def async_step_battery_remove(self, user_input=None):
        if not self.config_entry.options.get("batteries"):
            return self.async_abort(reason="no_batteries")
        if user_input is not None:
            opts = deepcopy(dict(self.config_entry.options))
            opts["batteries"] = [b for b in opts.get("batteries", []) if b["id"] != user_input["battery_id"]]
            return await self._save(opts)
        return self.async_show_form(step_id="battery_remove", data_schema=self._battery_choice_schema())

    def _battery_validate_measurements(self, b):
        errors = {}
        for key, units in (("soc_entity", {"%"}), ("power_entity", {"W", "kW"})):
            obj = self.hass.states.get(b.get(key)) if b.get(key) else None
            if obj is None or obj.attributes.get("unit_of_measurement") not in units:
                errors[key] = "soc_unit" if key == "soc_entity" else "power_unit"
        if not (0 <= b["min_soc_pct"] <= b["reserve_soc_pct"] < b["max_soc_pct"] <= 100):
            errors["reserve_soc_pct"] = "range"
        refs = {b.get(k) for k in ("soc_entity", "power_entity") if b.get(k)}
        for other in self.config_entry.options.get("batteries", []):
            if other["id"] != b["id"] and refs & {other.get(k) for k in ("soc_entity", "power_entity")}:
                errors["base"] = "duplicate"
        return errors

    async def _save_battery_profile(self, b):
        opts = deepcopy(dict(self.config_entry.options))
        rows = [x for x in opts.get("batteries", []) if x["id"] != b["id"]]
        rows.append(b)
        opts["batteries"] = rows
        return await self._save(opts)

    async def async_step_battery_profile(self, user_input=None):
        """Battery identity and measurements; control adapter is a separate explicit step."""
        b = {**BATTERY_DEFAULTS, **self._battery}
        errors = {}
        if user_input is not None:
            b.update(user_input)
            errors = self._battery_validate_measurements(b)
            if not errors:
                self._battery = b
                if b.get("control_kind") == "read_only":
                    b["control_enabled"] = False
                    b["exclusive_control_confirmed"] = False
                    b["number_entity"] = ""
                    b["charge_script"] = b["discharge_script"] = b["idle_script"] = ""
                    return await self._save_battery_profile(b)
                return await self.async_step_battery_control()
        schema = vol.Schema({
            vol.Required("name", default=b["name"]): selector.TextSelector(),
            vol.Required("enabled", default=b["enabled"]): selector.BooleanSelector(),
            vol.Required("capacity_kwh", default=b["capacity_kwh"]): num(1, 200, 0.5),
            vol.Required("soc_entity", description={"suggested_value": b.get("soc_entity", "")}): entity(["sensor", "input_number"]),
            vol.Required("power_entity", description={"suggested_value": b.get("power_entity", "")}): entity(["sensor", "input_number"]),
            vol.Required("power_sign", default=b["power_sign"]): selector.SelectSelector({"options":[
                {"value":"discharge_positive","label":"Positief = ontladen"},{"value":"charge_positive","label":"Positief = laden"}]}),
            vol.Required("min_soc_pct", default=b["min_soc_pct"]): num(0, 100, 1),
            vol.Required("reserve_soc_pct", default=b["reserve_soc_pct"]): num(0, 100, 1),
            vol.Required("max_soc_pct", default=b["max_soc_pct"]): num(0, 100, 1),
            vol.Required("max_charge_w", default=b["max_charge_w"]): num(100, 50000, 100),
            vol.Required("max_discharge_w", default=b["max_discharge_w"]): num(100, 50000, 100),
            vol.Required("phase_hint", default=b["phase_hint"]): selector.SelectSelector({"options":[
                {"value":"unknown","label":"Onbekend"},{"value":"l1","label":"L1"},{"value":"l2","label":"L2"},{"value":"l3","label":"L3"},{"value":"three_phase","label":"3-fase"}]}),
            vol.Required("control_kind", default=b["control_kind"]): selector.SelectSelector({"options":[
                {"value":"read_only","label":"Alleen uitlezen"},{"value":"signed_number","label":"Bidirectioneel vermogenssetpoint"},{"value":"scripts","label":"Laad/ontlaad/idle scripts"}]}),
        })
        return self.async_show_form(step_id="battery_profile", data_schema=schema, errors=errors)

    async def async_step_battery_control(self, user_input=None):
        b = {**BATTERY_DEFAULTS, **self._battery}
        errors = {}
        if user_input is not None:
            # Cleared optional controls must stay cleared.
            for key in ("number_entity", "charge_script", "discharge_script", "idle_script"):
                b[key] = ""
            b.update(user_input)
            if b.get("control_enabled") and not b.get("exclusive_control_confirmed"):
                errors["exclusive_control_confirmed"] = "exclusive_control_required"
            if b.get("control_kind") == "signed_number":
                obj = self.hass.states.get(b.get("number_entity")) if b.get("number_entity") else None
                if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
                    errors["number_entity"] = "number_unit"
            if b.get("control_kind") == "scripts":
                for key in ("charge_script", "discharge_script", "idle_script"):
                    if not b.get(key) or self.hass.states.get(b[key]) is None:
                        errors[key] = "required"
            refs = {b.get(k) for k in ("number_entity", "charge_script", "discharge_script", "idle_script") if b.get(k)}
            for other in self.config_entry.options.get("batteries", []):
                if other["id"] != b["id"] and refs & {other.get(k) for k in ("number_entity", "charge_script", "discharge_script", "idle_script")}:
                    errors["base"] = "duplicate"
            if not errors:
                self._battery = b
                return await self._save_battery_profile(b)
        schema = {
            vol.Required("control_enabled", default=b["control_enabled"]): selector.BooleanSelector(),
            vol.Required("exclusive_control_confirmed", default=b["exclusive_control_confirmed"]): selector.BooleanSelector(),
        }
        if b.get("control_kind") == "signed_number":
            schema[vol.Required("number_entity", description={"suggested_value": b.get("number_entity", "")})] = entity(["number", "input_number"])
            schema[vol.Required("number_sign", default=b["number_sign"])] = selector.SelectSelector({"options":[
                {"value":"discharge_positive","label":"Setpoint positief = ontladen"},{"value":"charge_positive","label":"Setpoint positief = laden"}]})
        elif b.get("control_kind") == "scripts":
            schema[vol.Required("charge_script", description={"suggested_value": b.get("charge_script", "")})] = entity(["script"])
            schema[vol.Required("discharge_script", description={"suggested_value": b.get("discharge_script", "")})] = entity(["script"])
            schema[vol.Required("idle_script", description={"suggested_value": b.get("idle_script", "")})] = entity(["script"])
        return self.async_show_form(step_id="battery_control", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_wallbox(self, user_input=None):
        """Basic Wallbox monitoring. Fine tuning lives in Advanced."""
        current = {**WALLBOX_DEFAULTS, **HOUSE_DEFAULTS, **self.config_entry.options.get("wallbox", {})}
        if not self.config_entry.options.get("wallbox"):
            current = apply_first_install_suggestions(self.hass, current, "wallbox")
        c = {**current, **(user_input or {})}
        errors = {}
        if user_input is not None:
            errors = wallbox_errors_for(self.hass, c, self._site(), self.config_entry.options.get("devices", []))
            if not errors:
                opts = deepcopy(dict(self.config_entry.options))
                opts["wallbox"] = {**current, **user_input}
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
            vol.Required("name", default=c["name"]): selector.TextSelector(),
            optional("power_entity", c): entity(["sensor", "input_number"]),
            optional("status_entity", c): entity(["sensor"]),
            optional("demand_entity", c): entity(["binary_sensor", "input_boolean"]),
            optional("mode_entity", c): entity(["select", "sensor", "input_select"]),
            vol.Required("charging_threshold_w", default=c["charging_threshold_w"]): num(10, 1000, 10),
        })
        return self.async_show_form(step_id="wallbox", data_schema=schema, errors=errors)

    async def async_step_wallbox_advanced(self, user_input=None):
        current = {**WALLBOX_DEFAULTS, **HOUSE_DEFAULTS, **self.config_entry.options.get("wallbox", {})}
        c = {**current, **(user_input or {})}
        errors = {}
        if user_input is not None:
            errors = wallbox_errors_for(self.hass, c, self._site(), self.config_entry.options.get("devices", []))
            if not errors:
                opts = deepcopy(dict(self.config_entry.options))
                opts["wallbox"] = {**current, **user_input}
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("stale_s", default=c["stale_s"]): num(90, 1800),
            vol.Required("stable_s", default=c["stable_s"]): num(30, 1800),
            vol.Required("cooldown_s", default=c["cooldown_s"]): num(60, 7200),
            vol.Required("fault_grace_s", default=c["fault_grace_s"]): num(0, 300),
            vol.Required("drop_tolerance_w", default=c["drop_tolerance_w"]): num(50, 3000, 10),
            vol.Required("demand_states", default=c["demand_states"]): selector.TextSelector(),
            vol.Required("idle_states", default=c["idle_states"]): selector.TextSelector(),
            vol.Required("full_solar_states", default=c["full_solar_states"]): selector.TextSelector(),
            vol.Required("handover_s", default=c["handover_s"]): num(60, 600),
            vol.Required("handover_confirm_s", default=c["handover_confirm_s"]): num(5, 60),
            vol.Required("handover_import_w", default=c["handover_import_w"]): num(0, 300, 10),
            vol.Required("reclaim_max_age_s", default=c["reclaim_max_age_s"]): num(5, 300),
            vol.Required("max_takeover_w", default=c["max_takeover_w"]): num(100, 10000, 50),
        })
        return self.async_show_form(step_id="wallbox_advanced", data_schema=schema, errors=errors)

    async def async_step_add(self, user_input=None):
        self._editing = None
        self._device = {**DEVICE_DEFAULTS, "id": uuid4().hex}
        return await self.async_step_device()

    def _choice_schema(self):
        return vol.Schema({vol.Required("device_id"): selector.SelectSelector({"options": [
            {"value": d["id"], "label": d["name"]} for d in self.config_entry.options.get("devices", [])]})})

    async def async_step_edit(self, user_input=None):
        devices = self.config_entry.options.get("devices", [])
        if not devices:
            return self.async_abort(reason="no_devices")
        if user_input is not None:
            self._editing = user_input["device_id"]
            self._device = deepcopy(next(d for d in devices if d["id"] == self._editing))
            rt = self._runtime()
            if rt:
                self._device["priority"] = rt.priorities.get(self._editing, self._device["priority"])
            return await self.async_step_device()
        return self.async_show_form(step_id="edit", data_schema=self._choice_schema())

    async def async_step_remove(self, user_input=None):
        if not self.config_entry.options.get("devices"):
            return self.async_abort(reason="no_devices")
        if user_input is not None:
            self._editing = user_input["device_id"]
            return await self.async_step_confirm_remove()
        return self.async_show_form(step_id="remove", data_schema=self._choice_schema())

    async def async_step_confirm_remove(self, user_input=None):
        if user_input is not None:
            opts = deepcopy(dict(self.config_entry.options))
            opts["devices"] = [d for d in opts["devices"] if d["id"] != self._editing]
            return await self._save(opts)
        return self.async_show_form(step_id="confirm_remove", data_schema=vol.Schema({}))

    async def async_step_device(self, user_input=None):
        if user_input is not None:
            old_kind = self._device.get("kind")
            self._device.update(user_input)
            if old_kind != user_input["kind"]:
                for k in ("control_entity", "active_entity", "number_entity", "start_script", "stop_script"):
                    self._device.pop(k, None)
            if user_input["kind"] != "script":
                self._device["non_interruptible"] = False
            return await self.async_step_connection()
        d = {**DEVICE_DEFAULTS, **self._device}
        return self.async_show_form(step_id="device", data_schema=vol.Schema({
            vol.Required("name", default=d.get("name", "Nieuw toestel")): selector.TextSelector(),
            vol.Required("kind", default=d["kind"]): selector.SelectSelector({"options": [
                {"value": "switch", "label": "Aan/uit-toestel"},
                {"value": "number", "label": "Regelbaar vermogen of laadstroom"},
                {"value": "script", "label": "Start-/stop-script met terugmelding"}]}),
            vol.Required("priority", default=d["priority"]): num(1, 100),
        }))

    async def async_step_connection(self, user_input=None):
        d = self._device
        errors = {}
        if user_input is not None:
            for key in ("power_entity", "condition_entity", "interlock_entity"):
                d.pop(key, None)
            d.update(user_input)
            references = {d.get(k) for k in ("control_entity", "active_entity", "number_entity", "start_script", "stop_script")} - {None, ""}
            for other in self.config_entry.options.get("devices", []):
                if other["id"] != d["id"] and references & {other.get(k) for k in ("control_entity", "active_entity", "number_entity", "start_script", "stop_script")}:
                    errors["base"] = "duplicate"
            dhw = self.config_entry.options.get("dhw", {})
            if dhw.get("target_entity") in references:
                errors["base"] = "duplicate"
            if d.get("power_entity") and d["power_entity"] == dhw.get("power_entity"):
                errors["power_entity"] = "dedicated_meter"
            if d.get("start_script") and d.get("start_script") == d.get("stop_script"):
                errors["base"] = "duplicate"
            if any(self.hass.states.get(ref) is None for ref in references):
                errors["base"] = "entity_missing"
            if d.get("power_entity"):
                obj = self.hass.states.get(d["power_entity"])
                if obj is None or obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
                    errors["power_entity"] = "power_unit"
            if d.get("power_entity"):
                rt = self._runtime()
                site = rt.settings if rt else {**self.config_entry.data, **self.config_entry.options.get("settings", {})}
                reserved = {site.get(k) for k in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity")}
                reserved.update(x.get("power_entity") for x in self.config_entry.options.get("devices", []) if x["id"] != d["id"])
                if d["power_entity"] in reserved:
                    errors["power_entity"] = "dedicated_meter"
            if d["kind"] == "number":
                obj = self.hass.states.get(d["number_entity"])
                unit = obj.attributes.get("unit_of_measurement") if obj else None
                if unit not in ("W", "kW", "A", "%"):
                    errors["number_entity"] = "number_unit"
                else:
                    d["control_unit"] = unit
                    if unit in ("W", "kW"):
                        d["watts_per_unit"] = 1.0 if unit == "W" else 1000.0
            if conflicting_devices(self.hass, self.config_entry.options.get("wallbox", {}), [d]):
                errors["base"] = "wallbox_duplicate"
            if not errors:
                return await self.async_step_device_behavior()
        schema = {}
        if d["kind"] in ("switch", "number"):
            schema[vol.Required("control_entity", description={"suggested_value": d.get("control_entity", "")})] = entity(["switch", "input_boolean"])
        if d["kind"] == "number":
            schema[vol.Required("number_entity", description={"suggested_value": d.get("number_entity", "")})] = entity(["number", "input_number"])
        if d["kind"] == "script":
            for key in ("start_script", "stop_script"):
                schema[vol.Required(key, description={"suggested_value": d.get(key, "")})] = entity(["script"])
            schema[vol.Required("active_entity", description={"suggested_value": d.get("active_entity", "")})] = entity(["binary_sensor", "input_boolean", "switch"])
        power_key = vol.Required("power_entity", description={"suggested_value": d.get("power_entity", "")}) if d["kind"] == "number" else optional("power_entity", d)
        schema[power_key] = entity(["sensor", "input_number"])
        for key in ("condition_entity", "interlock_entity"):
            schema[optional(key, d)] = entity(["binary_sensor", "input_boolean", "schedule", "switch"])
        return self.async_show_form(step_id="connection", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_limits(self, user_input=None):
        # Compatibility alias for a flow that was already open during an update.
        return await self.async_step_device_behavior(user_input)

    async def async_step_device_behavior(self, user_input=None):
        d = {**DEVICE_DEFAULTS, **self._device}
        errors = {}
        if user_input is not None:
            d.update(user_input)
            if d["kind"] == "number":
                obj = self.hass.states.get(d["number_entity"])
                try:
                    if d.get("control_unit") in ("W", "kW") and d["watts_per_unit"] != (1.0 if d["control_unit"] == "W" else 1000.0):
                        errors["watts_per_unit"] = "number_unit"
                    native_min, native_max = float(obj.attributes["min"]), float(obj.attributes["max"])
                    native_step = float(obj.attributes.get("step", 1))
                    alignment = (d["min_units"] - native_min) / native_step
                    steps = d["step_units"] / native_step
                    if not (native_min <= d["min_units"] <= d["max_units"] <= native_max and native_step > 0
                            and abs(alignment - round(alignment)) < 1e-5 and abs(steps - round(steps)) < 1e-5):
                        errors["min_units"] = "number_range"
                except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
                    errors["min_units"] = "number_range"
            if d["non_interruptible"] and (d["kind"] != "script" or not d.get("condition_entity")):
                errors["non_interruptible"] = "cycle_requires_ready"
            if d["max_on_s"] and d["max_on_s"] < d["min_on_s"]:
                errors["max_on_s"] = "timing"
            if not errors:
                self._device = d
                return await self.async_step_device_schedule()
        schema = {vol.Required("nominal_w", default=d["nominal_w"]): num(1, 100000, 1)}
        if d["kind"] == "number":
            for key, low, high, step in (("min_units", 0.1, 100000, 0.1), ("max_units", 0.1, 100000, 0.1),
                                         ("step_units", 0.1, 10000, 0.1), ("watts_per_unit", 0.1, 5000, 0.1)):
                schema[vol.Required(key, default=d[key])] = num(low, high, step)
        for key, low, high in (("start_delay_s", 0, 3600), ("stop_delay_s", 0, 3600),
                               ("min_on_s", 0, 86400), ("min_off_s", 0, 86400),
                               ("start_margin_w", 0, 5000), ("ack_timeout_s", 10, 600),
                               ("manual_hold_s", 60, 86400), ("max_on_s", 0, 86400)):
            schema[vol.Required(key, default=d[key])] = num(low, high)
        if d["kind"] == "script":
            schema[vol.Required("non_interruptible", default=d["non_interruptible"])] = selector.BooleanSelector()
        return self.async_show_form(step_id="device_behavior", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_device_schedule(self, user_input=None):
        d = {**DEVICE_DEFAULTS, **self._device}
        errors = {}
        if user_input is not None:
            d.update(user_input)
            if (d.get("max_daily_runtime_s", 0) and
                    d.get("min_daily_runtime_s", 0) > d.get("max_daily_runtime_s", 0)):
                errors["max_daily_runtime_s"] = "daily_runtime"
            try:
                for time_key in ("daily_deadline", "time_window_start", "time_window_end"):
                    parts = [int(x) for x in str(d.get(time_key, "23:59:00")).split(":" )]
                    if len(parts) not in (2, 3) or not (0 <= parts[0] <= 23 and 0 <= parts[1] <= 59) or (len(parts) == 3 and not 0 <= parts[2] <= 59):
                        raise ValueError(time_key)
            except (TypeError, ValueError) as err:
                errors[str(err) if str(err) in ("daily_deadline", "time_window_start", "time_window_end") else "daily_deadline"] = "time"
            if d.get("allow_wallbox_reclaim"):
                max_wait = self.config_entry.options.get("wallbox", {}).get("handover_s", HOUSE_DEFAULTS["handover_s"])
                if not d.get("power_entity") or d["non_interruptible"] or d["min_on_s"] > max_wait:
                    errors["allow_wallbox_reclaim"] = "reclaim_requirements"
            if d.get("cycle_learning_enabled"):
                if not d.get("non_interruptible") or not d.get("power_entity"):
                    errors["cycle_learning_enabled"] = "cycle_learning_requires_meter"
            if d.get("cycle_program_entity") and self.hass.states.get(d.get("cycle_program_entity")) is None:
                errors["cycle_program_entity"] = "entity_missing"
            if d.get("cycle_energy_kwh",0) and not d.get("cycle_duration_min",0) and not d.get("cycle_learning_enabled"):
                errors["cycle_duration_min"] = "cycle_duration_required"
            if not errors:
                opts = deepcopy(dict(self.config_entry.options))
                devices = [x for x in opts.get("devices", []) if x["id"] != d["id"]]
                devices.append(d)
                opts["devices"] = devices
                rt = self._runtime()
                if rt and not self._busy():
                    rt.priorities.pop(d["id"], None)
                return await self._save(opts)
        schema = {
            vol.Required("min_daily_runtime_s", default=d["min_daily_runtime_s"]): num(0, 86400, 60),
            vol.Required("daily_energy_goal_kwh", default=d.get("daily_energy_goal_kwh",0.0)): num(0, 100, 0.1),
            vol.Required("max_daily_runtime_s", default=d["max_daily_runtime_s"]): num(0, 86400, 60),
            vol.Required("daily_deadline", default=d["daily_deadline"]): selector.TimeSelector(),
            vol.Required("deadline_grid_allowed", default=d["deadline_grid_allowed"]): selector.BooleanSelector(),
            vol.Required("time_window_enabled", default=d["time_window_enabled"]): selector.BooleanSelector(),
            vol.Required("time_window_start", default=d["time_window_start"]): selector.TimeSelector(),
            vol.Required("time_window_end", default=d["time_window_end"]): selector.TimeSelector(),
            vol.Required("forecast_deferrable", default=d["forecast_deferrable"]): selector.BooleanSelector(),
            vol.Required("cheap_grid_allowed", default=d["cheap_grid_allowed"]): selector.BooleanSelector(),
            vol.Required("phase_hint", default=d.get("phase_hint", "auto")): selector.SelectSelector({"options": [
                {"value":"auto","label":"Auto · lokaal leren"},{"value":"unknown","label":"Onbekend / niet gebruiken"},
                {"value":"l1","label":"L1"},{"value":"l2","label":"L2"},{"value":"l3","label":"L3"},
                {"value":"three_phase","label":"3-fase"},{"value":"l1_l2","label":"L1 + L2"},
                {"value":"l1_l3","label":"L1 + L3"},{"value":"l2_l3","label":"L2 + L3"}]}),
            vol.Required("allow_wallbox_reclaim", default=d["allow_wallbox_reclaim"]): selector.BooleanSelector(),
        }
        if d.get("non_interruptible"):
            schema[vol.Required("cycle_learning_enabled", default=d.get("cycle_learning_enabled",False))] = selector.BooleanSelector()
            schema[vol.Required("cycle_energy_kwh", default=d.get("cycle_energy_kwh",0.0))] = num(0, 25, 0.05)
            schema[vol.Required("cycle_duration_min", default=d.get("cycle_duration_min",0.0))] = num(0, 1440, 5)
            schema[vol.Required("cycle_program", default=d.get("cycle_program","standaard"))] = selector.TextSelector()
            schema[optional("cycle_program_entity", d)] = entity(["sensor","select","input_select"])
        return self.async_show_form(step_id="device_schedule", data_schema=vol.Schema(schema), errors=errors)

