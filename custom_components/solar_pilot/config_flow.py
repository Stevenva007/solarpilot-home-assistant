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
from .consumer_wallbox import PRIORITY_DEFAULTS
from .wallbox_profile import PROFILE_DEFAULTS, validate_profile
from .wallbox_policy import SESSION_DEFAULTS, RECLAIM_POLICIES, discover_session_candidate
from .pv_forecast_source import PV_FORECAST_DEFAULTS, ENTITY_ROLES, finite
from .house_first import HOUSE_DEFAULTS
from .sg_config import SG_DEFAULTS, normalize_config as normalize_sg, source_errors as sg_errors
from .live_config import LiveOptionsMixin
from .dishwasher_config import DishwasherOptionsMixin
from .dishwasher import normalize_config as normalize_dishwasher, config_errors as dishwasher_errors, REFERENCE_KEYS as DISHWASHER_KEYS
from .ems import CAPACITY_DEFAULTS, ECONOMY_DEFAULTS, FORECAST_DEFAULTS, PHASE_DEFAULTS
from .unified_planner import UNIFIED_PLANNER_DEFAULTS
from .pv_model import LOCAL_PV_DEFAULTS
from .battery_analysis import BATTERY_ANALYSIS_DEFAULTS
from .battery_fleet import BATTERY_DEFAULTS, BATTERY_FLEET_DEFAULTS
from .first_install import apply_first_install_suggestions
from .private_bundle import build_private_import, private_bundle_overview, load_private_bundle, bundle_historical_seed


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
    groups = [state_set(c.get(k, SESSION_DEFAULTS[k])) for k in ("session_solar_states", "session_manual_states", "session_stopped_states")]
    if any(groups[i] & groups[j] for i in range(3) for j in range(i+1,3)):
        errors["base"] = "wallbox_state_overlap"
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


class SolarPilotOptions(LiveOptionsMixin, DishwasherOptionsMixin, config_entries.OptionsFlow):
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
        return {**DEFAULTS, **self.config_entry.data, **self._base_options().get("settings", {})}

    async def _save(self, options):
        return await self._live_save(options)

    async def async_step_init(self, user_input=None):
        self._base_options()
        return self.async_show_menu(step_id="init", menu_options=[
            "overview", "energy_hub", "loads_hub", "comfort_hub",
            "storage_hub", "intelligence_hub", "advanced_hub"
        ])

    async def async_step_overview(self, user_input=None):
        if user_input is not None:
            return await self.async_step_init()
        rt = self._runtime()
        opts = self._base_options()
        site = self._site()
        bundle = await self.hass.async_add_executor_job(load_private_bundle)
        ems = rt.ems_overview() if rt else {}
        conflicts = ems.get("legacy_conflicts", [])
        placeholders = {
            "mode": ({"observe":"Observatie", "solar":"Zonnestroom", "paused":"Pauze"}.get(rt.mode, rt.mode) if rt else "Niet geladen"),
            "grid": "gekoppeld" if site.get("grid_entity") else "ontbreekt",
            "pv": "gekoppeld" if site.get("pv_entity") else "niet gekoppeld",
            "devices": str(len(opts.get("devices", []))),
            "sg_boost": "automatische zonneboost aan" if opts.get("sg_boost", {}).get("enabled") else "automatische zonneboost uit",
            "wallbox": "monitor actief" if opts.get("wallbox", {}).get("enabled") else "uit",
            "batteries": str(len(opts.get("batteries", []))),
            "conflicts": "geen" if not conflicts else ", ".join(x.get("name", "onbekend") for x in conflicts[:3]),
            "private_bundle": private_bundle_overview(opts, bundle=bundle),
        }
        return self.async_show_form(step_id="overview", data_schema=vol.Schema({}), description_placeholders=placeholders)

    async def async_step_energy_hub(self, user_input=None):
        return self.async_show_menu(step_id="energy_hub", menu_options=["settings", "power_policy", "capacity", "phase", "economy"])

    async def async_step_loads_hub(self, user_input=None):
        return self.async_show_menu(step_id="loads_hub", menu_options=["add", "manage_device", "edit", "replace", "remove", "pending_changes"])

    async def async_step_comfort_hub(self, user_input=None):
        return self.async_show_menu(step_id="comfort_hub", menu_options=["sg_boost", "sg_sources", "sg_advanced"])

    async def async_step_storage_hub(self, user_input=None):
        return self.async_show_menu(step_id="storage_hub", menu_options=["wallbox", "battery", "battery_analysis"])

    async def async_step_intelligence_hub(self, user_input=None):
        return self.async_show_menu(step_id="intelligence_hub", menu_options=["pv_forecast", "forecast", "local_pv", "planner"])

    async def async_step_advanced_hub(self, user_input=None):
        return self.async_show_menu(step_id="advanced_hub", menu_options=["timing", "phase_learning", "wallbox_advanced", "analysis", "private_bundle", "system_info", "pending_changes"])

    async def async_step_private_bundle(self, user_input=None):
        """Apply/reload a private profile + historical bootstrap from userfiles."""
        bundle = await self.hass.async_add_executor_job(load_private_bundle)
        history = bundle_historical_seed(bundle)
        if user_input is not None and user_input.get("apply_now"):
            opts, result = build_private_import(
                self.hass, dict(self.config_entry.data), dict(self._base_options()), force=True, bundle=bundle
            )
            if result.get("changed"):
                return await self._save(opts)
        meta = self._base_options().get("_private_bundle", {})
        missing = meta.get("missing_groups", []) if isinstance(meta, dict) else []
        placeholders = {
            "status": private_bundle_overview(self._base_options(), bundle=bundle),
            "history": (
                f"aanwezig · {history.get('source', {}).get('homewizard_start', '?')} → "
                f"{history.get('source', {}).get('homewizard_end', '?')}" if history else "niet aanwezig"
            ),
            "missing": ", ".join(missing) if missing else "geen",
        }
        schema = vol.Schema({vol.Required("apply_now", default=False): selector.BooleanSelector()})
        return self.async_show_form(
            step_id="private_bundle", data_schema=schema, description_placeholders=placeholders
        )

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
            opts = deepcopy(dict(self._base_options()))
            previous = {**current, **opts.get("settings", {})}
            cleared = {k: "" for k in ("export_entity", "pv_entity", "battery_power_entity", "battery_soc_entity")}
            opts["settings"] = {**previous, **cleared, **user_input}
            return await self._save(opts)
        return self.async_show_form(step_id="settings", data_schema=sources_schema(user_input or current), errors=errors)

    async def async_step_power_policy(self, user_input=None):
        current = self._site()
        if user_input is not None:
            opts = deepcopy(dict(self._base_options()))
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
                opts = deepcopy(dict(self._base_options()))
                opts["settings"] = {**current, **opts.get("settings", {}), **user_input}
                return await self._save(opts)
        return self.async_show_form(step_id="timing", data_schema=timing_schema(user_input or current), errors=errors)

    async def async_step_capacity(self, user_input=None):
        c = {**CAPACITY_DEFAULTS, **self._base_options().get("capacity", {})}
        if not self._base_options().get("capacity"):
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
                opts = deepcopy(dict(self._base_options()))
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
        })
        return self.async_show_form(step_id="capacity", data_schema=schema, errors=errors)

    async def async_step_economy(self, user_input=None):
        c = {**ECONOMY_DEFAULTS, **self._base_options().get("economy", {})}
        if not self._base_options().get("economy"):
            c = apply_first_install_suggestions(self.hass, c, "economy")
        errors = {}
        if user_input is not None:
            c = {**ECONOMY_DEFAULTS, **user_input}
            for key in ("import_price_entity", "export_price_entity"):
                if c.get(key) and self.hass.states.get(c[key]) is None:
                    errors[key] = "entity_missing"
            if not errors:
                opts = deepcopy(dict(self._base_options()))
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

    async def async_step_pv_forecast(self, user_input=None):
        c = {**PV_FORECAST_DEFAULTS, **self._base_options().get("pv_forecast", {}), **(user_input or {})}
        errors = {}
        if user_input is not None:
            for key in ("enabled","auto_discover","calibration_enabled","shadow_enabled","show_raw"):
                if type(c.get(key)) is not bool:
                    errors[key]="invalid_pv_setting"
            if c.get("learning_preset") not in ("normal", "slow", "responsive"):
                errors["learning_preset"] = "invalid_pv_setting"
            for key, lower, upper in (("inverter_limit_w",100,1000000),("panel_peak_wp",100,1000000),("tilt_deg",0,90),("azimuth_deg",0,360),("minimum_days",5,30),("history_days",1,30),("stale_s",300,21600)):
                v=finite(c.get(key))
                if v is None or not lower<=v<=upper or (key in ("minimum_days","history_days","stale_s") and v != int(v)):
                    errors[key]="invalid_pv_setting"
                else:
                    c[key]=int(v) if key in ("minimum_days","history_days","stale_s") else v
            for role, (_,kind) in ENTITY_ROLES.items():
                if c.get(role):
                    obj=self.hass.states.get(c[role])
                    if obj is None or obj.attributes.get("unit_of_measurement") not in (("W","kW") if kind=="power" else ("Wh","kWh")):
                        errors[role]="power_unit" if kind=="power" else "energy_unit"
            if not errors:
                opts=deepcopy(dict(self._base_options()));opts["pv_forecast"]=c
                return await self._save(opts)
        schema={}
        for key in ("enabled","auto_discover","calibration_enabled","shadow_enabled","show_raw"):
            schema[vol.Required(key,default=c[key])]=selector.BooleanSelector()
        schema[vol.Required("learning_preset",default=c["learning_preset"])]=selector.SelectSelector({"options":[
            {"value":"normal","label":"Normaal — geleidelijk leren"},
            {"value":"slow","label":"Rustig — extra dagen bevestiging"},
            {"value":"responsive","label":"Vlotter — nog steeds begrensd"}]})
        schema[vol.Optional("forecast_entry_id",description={"suggested_value":c.get("forecast_entry_id","")})]=selector.TextSelector()
        for role in ENTITY_ROLES:
            schema[optional(role,c)]=entity(["sensor"])
        for key,lo,hi,step in (("panel_peak_wp",100,1000000,100),("inverter_limit_w",100,1000000,100),("tilt_deg",0,90,1),("azimuth_deg",0,360,1),("minimum_days",5,30,1),("history_days",1,30,1),("stale_s",300,21600,300)):
            schema[vol.Required(key,default=c[key])]=num(lo,hi,step)
        return self.async_show_form(step_id="pv_forecast",data_schema=vol.Schema(schema),errors=errors)

    async def async_step_forecast(self, user_input=None):
        c = {**FORECAST_DEFAULTS, **self._base_options().get("forecast", {})}
        if not self._base_options().get("forecast"):
            c = apply_first_install_suggestions(self.hass, c, "forecast")
        errors = {}
        if user_input is not None:
            c = {**FORECAST_DEFAULTS, **user_input}
            if c["enabled"]:
                for key in ("current_hour_entity", "next_hour_entity", "remaining_today_entity", "tomorrow_entity"):
                    if c.get(key):
                        obj = self.hass.states.get(c[key])
                        if obj is None or obj.attributes.get("unit_of_measurement") not in ("Wh", "kWh"):
                            errors[key] = "energy_unit"
            if not errors:
                opts = deepcopy(dict(self._base_options()))
                opts["forecast"] = c
                return await self._save(opts)
        schema = {vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector()}
        for key in ("current_hour_entity", "next_hour_entity", "remaining_today_entity", "tomorrow_entity"):
            schema[optional(key, c)] = entity(["sensor", "input_number"])
        schema[vol.Required("stale_s", default=c["stale_s"])] = num(300, 21600, 300)
        return self.async_show_form(step_id="forecast", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_local_pv(self, user_input=None):
        c = {**LOCAL_PV_DEFAULTS, **self._base_options().get("local_pv", {})}
        if not self._base_options().get("local_pv"):
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
                opts = deepcopy(dict(self._base_options())); opts["local_pv"] = c
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
        c = {**UNIFIED_PLANNER_DEFAULTS, **self._base_options().get("planner", {})}
        errors = {}
        if user_input is not None:
            c = {**UNIFIED_PLANNER_DEFAULTS, **user_input}
            if c["adaptive_power_max_multiplier"] < 1:
                errors["adaptive_power_max_multiplier"] = "range"
            if not errors:
                opts = deepcopy(dict(self._base_options()))
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
        current = {**PHASE_DEFAULTS, **self._base_options().get("phase", {})}
        if not self._base_options().get("phase"):
            current = apply_first_install_suggestions(self.hass, current, "phase")
        c = {**current, **(user_input or {})}
        if user_input is None and not c.get("session_mode_entity"):
            candidate = discover_session_candidate(self.hass, c)
            if candidate:
                c["session_mode_entity"] = candidate
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
                opts = deepcopy(dict(self._base_options()))
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
        current = {**PHASE_DEFAULTS, **self._base_options().get("phase", {})}
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
                opts = deepcopy(dict(self._base_options()))
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
        c = {**BATTERY_ANALYSIS_DEFAULTS, **self._base_options().get("battery_analysis", {})}
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
                opts = deepcopy(dict(self._base_options())); opts["battery_analysis"] = c
                return await self._save(opts)
            display = {**user_input}
        schema = vol.Schema({
            vol.Required("enabled", default=display.get("enabled", True)): selector.BooleanSelector(),
            vol.Required("seed_enabled", default=display.get("seed_enabled", True)): selector.BooleanSelector(),
            vol.Required("roundtrip_efficiency", default=display.get("roundtrip_efficiency", .8)): num(.5, 1.0, .01),
            vol.Required("reserve_pct", default=display.get("reserve_pct", 0)): num(0, 90, 1),
            vol.Required("capacities_kwh", default=display.get("capacities_kwh", "5,10,15,20")): selector.TextSelector(),
            vol.Required("powers_kw", default=display.get("powers_kw", "3,5,10")): selector.TextSelector(),
        })
        return self.async_show_form(step_id="battery_analysis", data_schema=schema, errors=errors)


    def _sg_values(self):
        current = normalize_sg(self._base_options().get("sg_boost", {}))
        if not self._base_options().get("sg_boost"):
            current = apply_first_install_suggestions(self.hass, current, "sg_boost")
        return current

    def _refresh_sg_base(self):
        """Reopen one SG form with current proof; retain other edit baselines."""
        entry = getattr(self, "config_entry", None)
        if entry is not None:
            self._base_options()["sg_boost"] = deepcopy(entry.options.get("sg_boost", {}))

    def _sg_errors(self, values):
        return sg_errors(self.hass, values, site=self._site(),
                         devices=self._base_options().get("devices", []),
                         wallbox=self._base_options().get("wallbox", {}),
                         batteries=self._base_options().get("batteries", []))

    async def _sg_save_form(self, step_id, user_input, schema, *, cleared=()):
        if user_input is None:
            self._refresh_sg_base()
            self._sg_profile_review = None
            self._sg_split_review = None
            self._sg_local_confirmed_roles = None
        current = self._sg_values()
        candidate = {**current, **{k: deepcopy(SG_DEFAULTS[k]) for k in cleared}, **(user_input or {})}
        # Changing a physical endpoint invalidates commissioning proof even if
        # an old browser form retains both checked boxes.
        if user_input is not None and candidate["entity_id"] != current["entity_id"]:
            candidate.update(enabled=False, commissioning_confirmed=False, watchdog_confirmed=False,
                             profile_confirmed=False, cooling_protection_confirmed=False)
        errors = self._sg_errors(candidate) if user_input is not None else {}
        # A checkbox carried over from the old scope is not local confirmation
        # of a new one. First show the proposed scope with fresh unchecked
        # proof; only the next explicit submission can confirm it.
        if user_input is not None and candidate["profile"] != current["profile"]:
            review = (current["profile"], candidate["profile"])
            if getattr(self, "_sg_profile_review", None) != review:
                self._sg_profile_review = review
                candidate.update(enabled=False, profile_confirmed=False,
                                 cooling_protection_confirmed=False)
                errors["profile_confirmed"] = "sg_profile_review"
            elif user_input.get("profile_confirmed") is not True:
                candidate.update(enabled=False, profile_confirmed=False)
                errors["profile_confirmed"] = "sg_profile_review"
        if user_input is not None and step_id == "sg_sources":
            if any(candidate[key] != current[key] for key in ("activity_entity", "zone_entities", "tank_target_entity")):
                # A new read-only operating source can change the cooling
                # context. Retain no old local cooling proof by implication.
                candidate["cooling_protection_confirmed"] = user_input.get("cooling_protection_confirmed") is True
            old_split = (current["power_supply1_entity"], current["power_supply2_entity"])
            new_split = (candidate["power_supply1_entity"], candidate["power_supply2_entity"])
            review = (old_split, new_split)
            standard_roles = (candidate["power_supply_profile"] == "panasonic_standard"
                and candidate["power_supply1_role"] in ("unconfirmed", "main")
                and candidate["power_supply2_role"] in ("unconfirmed", "heater"))
            if old_split != new_split and getattr(self, "_sg_split_review", None) != review:
                self._sg_split_review = review
                candidate["split_power_confirmed"] = False
                if user_input.get("split_power_confirmed") is True or current["split_power_confirmed"] is True:
                    errors["split_power_confirmed"] = "sg_split_review"
                for index, (old_meter, new_meter) in enumerate(zip(old_split, new_split), 1):
                    role_key = f"power_supply{index}_role"
                    if old_meter != new_meter and not standard_roles:
                        # The old supply function belongs to its old meter.
                        # Display roles are never inferred from names or from
                        # full meter coverage. Reuse the current pair review.
                        candidate[role_key] = "unconfirmed"
                        candidate["power_supply_profile"] = "unconfirmed"
                        if current[role_key] != "unconfirmed" or user_input.get(role_key, "unconfirmed") != "unconfirmed":
                            errors[role_key] = "sg_supply_role_review"
        entry = getattr(self, "config_entry", None)
        if user_input is not None and entry is not None and normalize_sg(entry.options.get("sg_boost", {})) != current:
            # A firmware/device change may revoke both checked proofs while
            # this form is open. Require a fresh review rather than treating
            # stale checked boxes as a new commissioning decision.
            self._refresh_sg_base()
            candidate = self._sg_values()
            self._sg_profile_review = None
            self._sg_split_review = None
            errors = {"base": "sg_reopen"}
        if user_input is not None and not errors:
            opts = deepcopy(dict(self._base_options()))
            opts["sg_boost"] = normalize_sg(candidate)
            self._sg_local_confirmed_profile = ((current["profile"], candidate["profile"])
                if candidate["profile"] != current["profile"] and user_input.get("profile_confirmed") is True else None)
            old_split = (current["power_supply1_entity"], current["power_supply2_entity"])
            new_split = (candidate["power_supply1_entity"], candidate["power_supply2_entity"])
            self._sg_local_confirmed_split = ((old_split, new_split)
                if old_split != new_split and user_input.get("split_power_confirmed") is True else None)
            self._sg_local_confirmed_roles = ((old_split, new_split)
                if old_split != new_split and getattr(self, "_sg_split_review", None) == (old_split, new_split)
                and any(user_input.get(key) in ("main", "heater") for key in
                        ("power_supply1_role", "power_supply2_role")) else None)
            return await self._save(opts)
        return self.async_show_form(step_id=step_id, data_schema=vol.Schema(schema(candidate)), errors=errors)

    async def async_step_sg_boost(self, user_input=None):
        def schema(c):
            return {
                optional("entity_id", c): entity(["switch"]),
                vol.Required("profile", default=c["profile"]): selector.SelectSelector({"options": [
                    {"value": "dhw_only", "label": "Uitsluitend tapwater"},
                    {"value": "general", "label": "Algemene SG-boost volgens Panasonic-bedrijf"}]}),
                vol.Required("profile_confirmed", default=c["profile_confirmed"]): selector.BooleanSelector(),
                vol.Required("cooling_protection_confirmed", default=c["cooling_protection_confirmed"]): selector.BooleanSelector(),
                vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
                vol.Required("commissioning_confirmed", default=c["commissioning_confirmed"]): selector.BooleanSelector(),
                vol.Required("watchdog_confirmed", default=c["watchdog_confirmed"]): selector.BooleanSelector(),
                vol.Required("threshold_w", default=c["threshold_w"]): num(500, 20000, 50),
                vol.Required("expected_power_w", default=c["expected_power_w"]): num(100, 30000, 50),
            }
        return await self._sg_save_form("sg_boost", user_input, schema, cleared=("entity_id",) if user_input is not None else ())

    async def async_step_sg_sources(self, user_input=None):
        def schema(c):
            def supply_role():
                return selector.SelectSelector({"options": [
                    {"value": "unconfirmed", "label": "Automatisch volgens Panasonic-voedingen"},
                    {"value": "main", "label": "Hoofdvoeding: warmtepomp, regeling en pompen"},
                    {"value": "heater", "label": "Elektrische ondersteuning"}]})
            return {
                optional("tank_temperature_entity", c): entity(["sensor", "water_heater", "climate"]),
                optional("tank_target_entity", c): entity(["water_heater", "climate", "number", "sensor"]),
                optional("power_entity", c): entity(["sensor"]),
                vol.Required("power_scope", default=c["power_scope"]): selector.SelectSelector({"options": [
                    {"value": "unconfirmed", "label": "Dekking nog niet bevestigd"},
                    {"value": "total", "label": "Hele warmtepomp inclusief elektrische hulp"},
                    {"value": "supply1", "label": "Alleen voeding 1 — gedeeltelijke meting"},
                    {"value": "supply2", "label": "Alleen voeding 2 — gedeeltelijke meting"}]}),
                optional("power_supply1_entity", c): entity(["sensor"]),
                vol.Required("power_supply1_role", default=c["power_supply1_role"]): supply_role(),
                optional("power_supply2_entity", c): entity(["sensor"]),
                vol.Required("power_supply2_role", default=c["power_supply2_role"]): supply_role(),
                vol.Required("split_power_confirmed", default=c["split_power_confirmed"]): selector.BooleanSelector(),
                vol.Required("power_activity_threshold_w", default=c["power_activity_threshold_w"]): num(10, 2000, 10),
                optional("activity_entity", c): entity(["sensor", "binary_sensor"]),
                optional("compressor_frequency_entity", c): entity(["sensor"]),
                optional("sg_status_entity", c): entity(["sensor", "binary_sensor"]),
                vol.Optional("zone_entities", default=c["zone_entities"]): selector.EntitySelector({"domain": ["climate"], "multiple": True}),
            }
        return await self._sg_save_form("sg_sources", user_input, schema,
            cleared=("tank_temperature_entity", "tank_target_entity", "power_entity", "power_supply1_entity",
                     "power_supply2_entity", "activity_entity", "compressor_frequency_entity",
                     "sg_status_entity", "zone_entities") if user_input is not None else ())

    async def async_step_sg_advanced(self, user_input=None):
        def schema(c):
            return {vol.Required(k, default=c[k]): num(low, high, step) for k, low, high, step in (
                ("start_delay_s", 30, 1800, 10), ("stop_delay_s", 5, 600, 5),
                ("hysteresis_w", 0, 5000, 50), ("rest_s", 60, 7200, 60),
                ("max_session_s", 300, 14400, 60), ("lease_s", 60, 600, 30),
                ("renew_s", 10, 120, 10), ("ack_timeout_s", 5, 60, 1),
                ("stale_s", 15, 600, 5))}
        return await self._sg_save_form("sg_advanced", user_input, schema)

    async def async_step_battery(self, user_input=None):
        return self.async_show_menu(step_id="battery", menu_options=["battery_settings", "battery_add", "battery_edit", "battery_remove"])

    async def async_step_battery_settings(self, user_input=None):
        c = {**BATTERY_FLEET_DEFAULTS, **self._base_options().get("battery_fleet", {})}
        errors = {}
        if user_input is not None:
            c = {**BATTERY_FLEET_DEFAULTS, **user_input}
            if c["discharge_reserve_w"] > self._base_options().get("settings", {}).get("max_import_w", self.config_entry.data.get("max_import_w", 3500)):
                errors["discharge_reserve_w"] = "range"
            if not errors:
                opts = deepcopy(dict(self._base_options())); opts["battery_fleet"] = c
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
            {"value": b["id"], "label": b.get("name", b["id"])} for b in self._base_options().get("batteries", [])]})})

    async def async_step_battery_add(self, user_input=None):
        self._battery_editing = None
        self._battery = {**BATTERY_DEFAULTS, "id": uuid4().hex}
        return await self.async_step_battery_profile()

    async def async_step_battery_edit(self, user_input=None):
        batteries = self._base_options().get("batteries", [])
        if not batteries:
            return self.async_abort(reason="no_batteries")
        if user_input is not None:
            self._battery_editing = user_input["battery_id"]
            self._battery = deepcopy(next(b for b in batteries if b["id"] == self._battery_editing))
            return await self.async_step_battery_profile()
        return self.async_show_form(step_id="battery_edit", data_schema=self._battery_choice_schema())

    async def async_step_battery_remove(self, user_input=None):
        if not self._base_options().get("batteries"):
            return self.async_abort(reason="no_batteries")
        if user_input is not None:
            opts = deepcopy(dict(self._base_options()))
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
        for other in self._base_options().get("batteries", []):
            if other["id"] != b["id"] and refs & {other.get(k) for k in ("soc_entity", "power_entity")}:
                errors["base"] = "duplicate"
        return errors

    async def _save_battery_profile(self, b):
        opts = deepcopy(dict(self._base_options()))
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
            for other in self._base_options().get("batteries", []):
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
        current = {**WALLBOX_DEFAULTS, **HOUSE_DEFAULTS, **PRIORITY_DEFAULTS, **PROFILE_DEFAULTS, **SESSION_DEFAULTS, **self._base_options().get("wallbox", {})}
        if not self._base_options().get("wallbox"):
            current = apply_first_install_suggestions(self.hass, current, "wallbox")
        c = {**current, **(user_input or {})}
        errors = {}
        if user_input is not None:
            errors = {**wallbox_errors_for(self.hass, c, self._site(), self._base_options().get("devices", [])), **validate_profile(c)}
            if not errors:
                opts = deepcopy(dict(self._base_options()))
                opts["wallbox"] = {**current, **user_input}
                return await self._save(opts)
        schema = vol.Schema({
            vol.Required("enabled", default=c["enabled"]): selector.BooleanSelector(),
            vol.Required("name", default=c["name"]): selector.TextSelector(),
            optional("power_entity", c): entity(["sensor", "input_number"]),
            optional("status_entity", c): entity(["sensor"]),
            optional("demand_entity", c): entity(["binary_sensor", "input_boolean"]),
            optional("connected_entity", c): entity(["binary_sensor"]),
            optional("mode_entity", c): entity(["select", "sensor", "input_select"]),
            optional("session_mode_entity", c): entity(["sensor", "select", "input_select"]),
            vol.Required("trust_solar_setting", default=c["trust_solar_setting"]): selector.BooleanSelector(),
            vol.Required("charging_threshold_w", default=c["charging_threshold_w"]): num(10, 1000, 10),
            vol.Required("priority_min_power_w", default=c["priority_min_power_w"]): num(0, 22000, 10),
            vol.Required("priority_start_margin_w", default=c["priority_start_margin_w"]): num(0, 2000, 10),
            vol.Required("profile_auto", default=c["profile_auto"]): selector.BooleanSelector(),
            optional("max_current_entity", c): entity(["number", "sensor"]),
            optional("phases_entity", c): entity(["sensor", "number"]),
            vol.Required("charging_phases", default=str(c["charging_phases"])): selector.SelectSelector({"options": [
                {"value": "1", "label": "1 fase (bevestigd)"}, {"value": "3", "label": "3 fasen (bevestigd)"}]}),
            vol.Required("max_current_a", default=c["max_current_a"]): num(6, 80, 1),
            vol.Required("voltage_v", default=c["voltage_v"]): num(207, 253, 1),
            vol.Required("minimum_current_a", default=c["minimum_current_a"]): num(6, 16, 1),
            vol.Required("minimum_from_profile", default=c["minimum_from_profile"]): selector.BooleanSelector(),
        })
        return self.async_show_form(step_id="wallbox", data_schema=schema, errors=errors)

    async def async_step_wallbox_advanced(self, user_input=None):
        current = {**WALLBOX_DEFAULTS, **HOUSE_DEFAULTS, **PRIORITY_DEFAULTS, **PROFILE_DEFAULTS, **SESSION_DEFAULTS, **self._base_options().get("wallbox", {})}
        c = {**current, **(user_input or {})}
        errors = {}
        if user_input is not None:
            errors = {**wallbox_errors_for(self.hass, c, self._site(), self._base_options().get("devices", [])), **validate_profile(c)}
            if not errors:
                opts = deepcopy(dict(self._base_options()))
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
            vol.Required("session_solar_states", default=c["session_solar_states"]): selector.TextSelector(),
            vol.Required("session_manual_states", default=c["session_manual_states"]): selector.TextSelector(),
            vol.Required("session_stopped_states", default=c["session_stopped_states"]): selector.TextSelector(),
            vol.Required("priority_stable_s", default=c["priority_stable_s"]): num(30, 1800, 10),
            vol.Required("priority_release_s", default=c["priority_release_s"]): num(60, 3600, 10),
            vol.Required("priority_hysteresis_w", default=c["priority_hysteresis_w"]): num(50, 2000, 10),
            vol.Required("priority_start_timeout_s", default=c["priority_start_timeout_s"]): num(180, 1800, 30),
            vol.Required("priority_retry_s", default=c["priority_retry_s"]): num(300, 7200, 60),
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
            {"value": d["id"], "label": d["name"]} for d in self._base_options().get("devices", [])]})})

    async def async_step_edit(self, user_input=None):
        devices = self._base_options().get("devices", [])
        if not devices:
            return self.async_abort(reason="no_devices")
        if user_input is not None:
            self._editing = user_input["device_id"]
            self._device = deepcopy(next(d for d in devices if d["id"] == self._editing))
            rt = self._runtime()
            if rt and not rt.priority_board.active:
                self._device["priority"] = rt.priorities.get(self._editing, self._device["priority"])
            return await self.async_step_device()
        return self.async_show_form(step_id="edit", data_schema=self._choice_schema())

    async def async_step_remove(self, user_input=None):
        if not self._base_options().get("devices"):
            return self.async_abort(reason="no_devices")
        if user_input is not None:
            self._editing = user_input["device_id"]
            return await self.async_step_confirm_remove()
        return self.async_show_form(step_id="remove", data_schema=self._choice_schema())

    async def async_step_confirm_remove(self, user_input=None):
        if user_input is not None:
            opts = deepcopy(dict(self._base_options()))
            opts["devices"] = [d for d in opts["devices"] if d["id"] != self._editing]
            return await self._save(opts)
        return self.async_show_form(step_id="confirm_remove", data_schema=vol.Schema({}))

    async def async_step_device(self, user_input=None):
        if user_input is not None:
            old_kind = self._device.get("kind")
            self._device.update(user_input)
            if user_input["kind"] == "dishwasher":
                self._device["appliance_type"] = "dishwasher"
            if old_kind != user_input["kind"]:
                for k in ("control_entity", "active_entity", "number_entity", "start_script", "stop_script"):
                    self._device.pop(k, None)
            if user_input["kind"] not in ("script", "dishwasher"):
                self._device["non_interruptible"] = False
            if user_input["kind"] == "dishwasher":
                self._device = normalize_dishwasher(self._device)
                if old_kind != "dishwasher":
                    self._device.update(priority=10, wallbox_precedence="consumer_first", nominal_w=2000, start_delay_s=300, ack_timeout_s=300, max_on_s=21600, dishwasher_arming_mode="app", dishwasher_remote_states="Enabled", dishwasher_ready_states="Ready To Start", dishwasher_running_states="Running;Paused", dishwasher_finished_states="End Of Cycle", dishwasher_alert_mode="aeg_attributes")
            elif old_kind == "dishwasher":
                for key in list(self._device):
                    if key.startswith("dishwasher_") or key == "start_button":
                        self._device.pop(key, None)
            return await self.async_step_connection()
        d = {**DEVICE_DEFAULTS, **self._device}
        schema = {
            vol.Required("name", default=d.get("name", "Nieuw toestel")): selector.TextSelector(),
            vol.Required("kind", default=d["kind"]): selector.SelectSelector({"options": [
                {"value": "switch", "label": "Aan/uit-toestel"},
                {"value": "number", "label": "Regelbaar vermogen of laadstroom"},
                {"value": "script", "label": "Start-/stop-script met terugmelding"},
                {"value": "dishwasher", "label": "AEG/Electrolux afwasmachine — alleen starten"}]}),
            vol.Required("appliance_type", default=d.get("appliance_type", "dishwasher" if d["kind"] == "dishwasher" else "other")): selector.SelectSelector({"options": [
                {"value":"dishwasher","label":"Afwasmachine"}, {"value":"washing_machine","label":"Wasmachine"},
                {"value":"tumble_dryer","label":"Droogkast"}, {"value":"other","label":"Andere verbruiker"}]}),
            vol.Required("priority", default=d["priority"]): num(1, 100),
        }
        if self._base_options().get("priority_board", {}).get("schema") in (1, 2):
            schema = {k:v for k,v in schema.items() if getattr(k,"schema",k) != "priority"}
        return self.async_show_form(step_id="device", data_schema=vol.Schema(schema))

    async def async_step_connection(self, user_input=None):
        if self._device.get("kind") == "dishwasher":
            return await self.async_step_dishwasher_connection(user_input)
        d = self._device
        errors = {}
        if user_input is not None:
            for key in ("power_entity", "condition_entity", "interlock_entity"):
                d.pop(key, None)
            d.update(user_input)
            references = {d.get(k) for k in ("control_entity", "active_entity", "number_entity", "start_script", "stop_script")} - {None, ""}
            for other in self._base_options().get("devices", []):
                if other["id"] not in (d["id"], d.get("replaces_device_id")) and references & {other.get(k) for k in ("control_entity", "active_entity", "number_entity", "start_script", "stop_script")}:
                    errors["base"] = "duplicate"
            sg = self._base_options().get("sg_boost", {})
            if sg.get("entity_id") and sg["entity_id"] in references:
                errors["base"] = "sg_duplicate"
            monitor_refs = {sg.get(k) for k in ("tank_target_entity", "tank_temperature_entity", "activity_entity")}
            monitor_refs.update(sg.get("zone_entities", []))
            if references & (monitor_refs - {None, ""}):
                errors["base"] = "panasonic_read_only"
            if d.get("power_entity") and d["power_entity"] == sg.get("power_entity"):
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
                site = rt.settings if rt else {**self.config_entry.data, **self._base_options().get("settings", {})}
                reserved = {site.get(k) for k in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity")}
                reserved.update(x.get("power_entity") for x in self._base_options().get("devices", []) if x["id"] not in (d["id"], d.get("replaces_device_id")))
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
            if conflicting_devices(self.hass, self._base_options().get("wallbox", {}), [d]):
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
            if d["non_interruptible"] and d["kind"] != "dishwasher" and (d["kind"] != "script" or not d.get("condition_entity")):
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
        central_priority = self._base_options().get("priority_board", {}).get("schema") in (1, 2)
        errors = {}
        if user_input is not None:
            d.update(user_input)
            wallbox_choice = d.pop("wallbox_energy_choice", None)
            for minute_key, seconds_key in (
                ("min_daily_runtime_min", "min_daily_runtime_s"),
                ("max_daily_runtime_min", "max_daily_runtime_s"),
            ):
                if minute_key in d:
                    d[seconds_key] = int(round(float(d.pop(minute_key)) * 60))
            if central_priority:
                # A form opened before central priority became active cannot
                # overwrite the now-central order or car-power permission.
                for key in ("wallbox_precedence", "wallbox_power_policy", "allow_wallbox_reclaim"):
                    if key in self._device:
                        d[key] = self._device[key]
                    else:
                        # Preserve the raw legacy record exactly.  Materialising
                        # a missing default here would look like a forbidden
                        # priority edit to LiveOptions even though this field is
                        # hidden and the user changed only planning settings.
                        d.pop(key, None)
            elif wallbox_choice == "priority":
                d.update(wallbox_power_policy="priority", allow_wallbox_reclaim=False)
            elif wallbox_choice == "never":
                d.update(wallbox_power_policy="never", allow_wallbox_reclaim=False)
            elif wallbox_choice == "short_cycle":
                d.update(wallbox_power_policy="legacy", allow_wallbox_reclaim=True)
            elif wallbox_choice is not None:
                errors["wallbox_energy_choice"] = "invalid_precedence"
            if (d.get("max_daily_runtime_s", 0) and
                    d.get("min_daily_runtime_s", 0) > d.get("max_daily_runtime_s", 0)):
                errors["max_daily_runtime_min"] = "daily_runtime"
            try:
                for time_key in ("daily_deadline", "time_window_start", "time_window_end"):
                    parts = [int(x) for x in str(d.get(time_key, "23:59:00")).split(":" )]
                    if len(parts) not in (2, 3) or not (0 <= parts[0] <= 23 and 0 <= parts[1] <= 59) or (len(parts) == 3 and not 0 <= parts[2] <= 59):
                        raise ValueError(time_key)
            except (TypeError, ValueError) as err:
                errors[str(err) if str(err) in ("daily_deadline", "time_window_start", "time_window_end") else "daily_deadline"] = "time"
            if not central_priority:
                if d.get("wallbox_precedence", "global") not in ("global", "consumer_first", "wallbox_first"):
                    errors["wallbox_precedence"] = "invalid_precedence"
                if d.get("wallbox_precedence") == "wallbox_first" and d.get("allow_wallbox_reclaim"):
                    errors["wallbox_energy_choice"] = "priority_reclaim_conflict"
                if d.get("wallbox_power_policy", "priority") not in RECLAIM_POLICIES:
                    errors["wallbox_energy_choice"] = "invalid_precedence"
                if d.get("allow_wallbox_reclaim") and d.get("wallbox_power_policy", "priority") == "legacy":
                    max_wait = self._base_options().get("wallbox", {}).get("handover_s", HOUSE_DEFAULTS["handover_s"])
                    if not d.get("power_entity") or d["non_interruptible"] or d["min_on_s"] > max_wait:
                        errors["wallbox_energy_choice"] = "reclaim_requirements"
            if d.get("cycle_learning_enabled"):
                if not d.get("non_interruptible") or not d.get("power_entity"):
                    errors["cycle_learning_enabled"] = "cycle_learning_requires_meter"
            if d.get("cycle_program_entity") and self.hass.states.get(d.get("cycle_program_entity")) is None:
                errors["cycle_program_entity"] = "entity_missing"
            if d.get("cycle_energy_kwh",0) and not d.get("cycle_duration_min",0) and not d.get("cycle_learning_enabled"):
                errors["cycle_duration_min"] = "cycle_duration_required"
            if d.get("kind") == "dishwasher":
                d = normalize_dishwasher(d)
                errors.update(dishwasher_errors(self.hass, d))
            if not errors:
                opts = deepcopy(dict(self._base_options()))
                devices = [x for x in opts.get("devices", []) if x["id"] not in (d["id"], d.get("replaces_device_id"))]
                devices.append(d)
                opts["devices"] = devices
                return await self._save(opts)
        current_wallbox_choice = (
            "short_cycle" if d.get("wallbox_power_policy") == "legacy" and d.get("allow_wallbox_reclaim")
            else "never" if d.get("wallbox_power_policy") in ("never", "legacy")
            else "priority"
        )
        schema = {
            vol.Required("min_daily_runtime_min", default=d["min_daily_runtime_s"] / 60): num(0, 1440, 1),
            vol.Required("daily_energy_goal_kwh", default=d.get("daily_energy_goal_kwh",0.0)): num(0, 100, 0.1),
            vol.Required("max_daily_runtime_min", default=d["max_daily_runtime_s"] / 60): num(0, 1440, 1),
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
            vol.Required("wallbox_precedence", default=d.get("wallbox_precedence", "global")): selector.SelectSelector({"options": [
                {"value": "global", "label": "Gezamenlijke volgorde gebruiken"},
                {"value": "consumer_first", "label": "Dit toestel vóór Auto laden"},
                {"value": "wallbox_first", "label": "Auto laden vóór dit toestel"}]}),
            vol.Required("wallbox_energy_choice", default=current_wallbox_choice): selector.SelectSelector({"options": [
                {"value": "priority", "label": "Ja · als volgorde en veiligheid het toelaten"},
                {"value": "never", "label": "Nee · alleen vrij zonneoverschot"},
                {"value": "short_cycle", "label": "Ja · alleen voor een kort, gemeten en onderbreekbaar toestel"}]}),
        }
        if d.get("non_interruptible"):
            schema[vol.Required("cycle_learning_enabled", default=d.get("cycle_learning_enabled",False))] = selector.BooleanSelector()
            schema[vol.Required("cycle_energy_kwh", default=d.get("cycle_energy_kwh",0.0))] = num(0, 25, 0.05)
            schema[vol.Required("cycle_duration_min", default=d.get("cycle_duration_min",0.0))] = num(0, 1440, 5)
            schema[vol.Required("cycle_program", default=d.get("cycle_program","standaard"))] = selector.TextSelector()
            schema[optional("cycle_program_entity", d)] = entity(["sensor","select","input_select"])
        if central_priority:
            central_fields = {"wallbox_precedence", "wallbox_energy_choice"}
            schema = {k:v for k,v in schema.items() if getattr(k,"schema",k) not in central_fields}
        return self.async_show_form(step_id="device_schedule", data_schema=vol.Schema(schema), errors=errors)
