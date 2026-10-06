"""Build the offline SolarPilot card example with fictitious data.

The generated page never contacts Home Assistant and never sends device commands.
"""
from pathlib import Path
import importlib.util
import json
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
card = (ROOT / "custom_components" / "solar_pilot" / "frontend" / "solar-pilot-card.js").read_text(encoding="utf-8")
help_data = json.loads((ROOT / "custom_components" / "solar_pilot" / "frontend" / "option-help.json").read_text(encoding="utf-8"))
helper_code = (ROOT / "custom_components" / "solar_pilot" / "frontend" / "option-help.js").read_text(encoding="utf-8")
card = "globalThis.SOLAR_PILOT_HELP_DATA = " + json.dumps(help_data, ensure_ascii=False) + ";\n" + helper_code + "\n" + card
spec = importlib.util.spec_from_file_location("current_guide_example", ROOT / "custom_components" / "solar_pilot" / "current_guide.py")
guide_mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(guide_mod)

thermal_spec = importlib.util.spec_from_file_location("thermal_climate_example", ROOT / "custom_components" / "solar_pilot" / "thermal_climate.py")
thermal_mod = importlib.util.module_from_spec(thermal_spec)
assert thermal_spec.loader is not None
sys.modules[thermal_spec.name] = thermal_mod
thermal_spec.loader.exec_module(thermal_mod)
CLIMATE_DEFAULTS = thermal_mod.SMART_CLIMATE_DEFAULTS
CLIMATE_SPECS = thermal_mod.CLIMATE_SETTING_SPECS

# Load planner modules under a small synthetic package so their relative
# imports work without importing SolarPilot's Home Assistant entry point.
EXAMPLE_PKG = "solar_pilot_example"
pkg = types.ModuleType(EXAMPLE_PKG)
pkg.__path__ = [str(ROOT / "custom_components" / "solar_pilot")]
sys.modules[EXAMPLE_PKG] = pkg

def load_example_module(short_name):
    full_name = f"{EXAMPLE_PKG}.{short_name}"
    spec = importlib.util.spec_from_file_location(full_name, ROOT / "custom_components" / "solar_pilot" / f"{short_name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod

load_example_module("planner_quality")
planner_mod = load_example_module("unified_planner")
PLANNER_DEFAULTS = planner_mod.UNIFIED_PLANNER_DEFAULTS

def planner_catalog(settings):
    return planner_mod.planner_settings_catalog(settings)

def climate_catalog(settings):
    return [{"key": key, "value": settings.get(key), "default": CLIMATE_DEFAULTS.get(key), **spec}
            for key, spec in CLIMATE_SPECS.items()]

def climate_demo_profile(samples, days, passive_k, heat_gain, delay_h, solar_gain):
    """Fictitious heating-only evidence, using the actual confidence contract."""
    profile = thermal_mod.ThermalProfile(
        passive_k=[passive_k] * 60, heat_gain=[heat_gain] * 24,
        cool_gain=[], solar_gain_per_kw=[solar_gain] * 38,
        response_delays_h=[delay_h] * 6,
        days={f"2026-09-{day + 1:02d}" for day in range(days)}, samples=samples,
    )
    confidence = profile.confidence(CLIMATE_DEFAULTS)
    k, heat, cool, delay = profile.coefficients()
    details = {
        "samples": profile.samples, "days": len(profile.days),
        "confidence": confidence,
        "reliability_status": profile.confidence_status(confidence, samples),
        "confidence_components": profile.confidence_components(CLIMATE_DEFAULTS),
        "passive_k_per_h": k, "thermal_time_constant_h": round(1 / k, 1),
        "heat_gain_c_h": heat, "heat_gain_learned": True,
        "cool_gain_c_h": cool, "cool_gain_learned": False,
        "response_delay_h": delay, "response_delay_learned": True,
        "solar_gain_c_h_per_kw_pv": profile.solar_coefficient(),
        "solar_gain_samples": len(profile.solar_gain_per_kw),
        "solar_gain_confidence": profile.solar_confidence(CLIMATE_DEFAULTS),
    }
    readiness = profile.readiness(CLIMATE_DEFAULTS, directions=("heating",), use_solar=True)
    readiness["forecast_confidence"] = profile.readiness(CLIMATE_DEFAULTS, use_solar=True)["confidence"]
    return details, readiness

demo_profile_1, demo_readiness_1 = climate_demo_profile(126, 16, .028, .11, 2.5, .028)
demo_profile_2, demo_readiness_2 = climate_demo_profile(118, 15, .031, .10, 2.7, .021)
demo_coast_confidence = demo_readiness_2["confidence"]
demo_required_components = demo_readiness_2["required_components"]
guide_attributes = {
    "solar_pilot_guide": True,
    "title": guide_mod.CURRENT_GUIDE["title"],
    "version": guide_mod.GUIDE_VERSION,
    "updated": guide_mod.GUIDE_UPDATED,
    "intro": guide_mod.CURRENT_GUIDE["intro"],
    "sections": guide_mod.CURRENT_GUIDE["sections"],
    "rules_hash": guide_mod.GUIDE_HASH,
}

attributes = {
    "solar_pilot": True,
    "mode": "solar",
    "problem": "",
    "pv_w": 6200,
    "grid_w": -150,
    "energy_display": {
        "inverter_limit_w": 8000,
        "stale_s": 120,
        "pv": {"value_w": 6200, "reported_at": 0},
        "grid": {"value_w": -150, "reported_at": 0},
    },
    "free_w": 0,
    "managed_w": 2000,
    "budget_w": 5000,
    "reserve_w": 150,
    "max_import_w": 3500,
    "recovery": [],
    "mode_entity": "select.voorbeeld_modus",
    "auto_resume_after_restart": True,
    "auto_resume_after_restart_entity": "switch.voorbeeld_automatisch_hervatten",
    "pause_cause": "",
    "pause_reason": "",
    "restart_requested_mode": None,
    "reset_entity": "button.voorbeeld_reset",
    "guide_entity": "sensor.solarpilot_actuele_uitleg",
    "integration_version": guide_mod.GUIDE_VERSION,
    "editable": False,
    "energy_kwh": 4.8,
    "energy_estimated": False,
    "ems": {
        "capacity": {
            "enabled": True,
            "valid": True,
            "current_average_w": 3100,
            "monthly_peak_w": 5549,
            "configured_target_w": 3500,
            "effective_target_w": 5549,
            "allowed_grid_w": 5800,
            "optional_headroom_w": 5650,
            "reason": "Kwartierpiekdoel 5549 W; resterende importgrens 5800 W",
        },
        "phase": {"enabled": True, "valid": True, "phase_w": [1200, 900, 700], "limit_w": 7360, "guarded_limit_w": 7060, "max_import_w": 1200, "headroom_w": 5860, "block_increase": False, "release_flexible": False, "reason": "Fasebewaking: kleinste vrije faseruimte 5860 W"},
        "legacy_conflicts": [],
        "ready": True,
        "warnings": [],
        "advice": [
            "Eigen PV gebruiken vermijdt ongeveer € 0,270/kWh aan marginale energiekost tegenover injecteren",
            "Zonnevoorspelling stijgt volgend uur; niet-dringende geplande lasten kunnen later gunstiger zijn",
        ],
        "economy": {
            "enabled": True,
            "import_eur_kwh": 0.30,
            "export_eur_kwh": 0.03,
            "self_use_value_eur_kwh": 0.27,
        },
        "forecast": {
            "enabled": True,
            "current_hour_kwh": 1.0,
            "next_hour_kwh": 1.8,
            "remaining_today_kwh": 8.2,
            "tomorrow_kwh": 32.9,
        },
        "local_pv": {"enabled": True, "samples": 184, "distinct_live_days": 9, "factor": 0.43, "confidence": 0.84,
                     "source": "live zonnestand 2D", "corrected_power_w": 2800, "corrected_current_hour_kwh": 0.75,
                     "corrected_next_hour_kwh": 1.45, "next_factor": 0.72, "next_confidence": 0.81,
                     "state": "recovery_expected", "event_eta_min": 45,
                     "reason": "Herstel na lokale schaduw verwacht over ongeveer 45 min (factor 0.43→0.72)", "seed_days": 79},
        "phase_learning": {"enabled": True, "accepted_events": 17, "rejected_events": 4, "use_for_control": False,
                           "minimum_confidence_for_control": 0.75, "devices": {}},
        "phase_attribution": {"enabled": True, "valid": True, "mapped_devices": 2, "unmapped_measured_devices": 1,
                              "phases": [
                                  {"name":"L1","net_w":1200,"known_device_w":550,"battery_net_w":0,"residual_net_w":650,"devices":[{"name":"Flexlast · voorbeeld","power_w":550,"confidence":.92}],"batteries":[]},
                                  {"name":"L2","net_w":900,"known_device_w":0,"battery_net_w":0,"residual_net_w":900,"devices":[],"batteries":[]},
                                  {"name":"L3","net_w":700,"known_device_w":180,"battery_net_w":-600,"residual_net_w":1120,"devices":[{"name":"Extra verbruiker","power_w":180,"confidence":.79}],"batteries":[{"name":"Toekomstige batterij · voorbeeld","net_w":-600}]},
                              ]},
        "historical_phase_profile": {"stats": {
            "L1 max W":{"p95_import_w":1223,"max_import_w":3271},
            "L2 max W":{"p95_import_w":1192,"max_import_w":6238},
            "L3 max W":{"p95_import_w":2876.55,"max_import_w":6498}}},
        "battery_analysis": {"enabled": True, "advisory_only": True, "roundtrip_efficiency": .80, "reserve_pct": 0,
            "seed_period":{"start":"2026-05-01T00:00:00","end":"2026-09-20T23:45:00","days":142.99},
            "scenarios":[
                {"capacity_kwh":5,"power_kw":5,"avoided_import_kwh":722.8,"used_export_kwh":903.4},
                {"capacity_kwh":10,"power_kw":5,"avoided_import_kwh":1121.8,"used_export_kwh":1402.2},
                {"capacity_kwh":15,"power_kw":5,"avoided_import_kwh":1353.1,"used_export_kwh":1691.3},
                {"capacity_kwh":20,"power_kw":5,"avoided_import_kwh":1478.6,"used_export_kwh":1848.2}],
            "note":"What-if op werkelijk gemeten import/export. Geen batterijbediening, degradatie-, financierings- of wintergarantie."},
        "battery_fleet": {
            "enabled": True, "control_enabled": False, "strategy": "loads_first",
            "aggregate": {"valid": True, "count": 1, "valid_count": 1, "capacity_kwh": 10, "soc_pct": 62.4, "power_w": 600, "discharge_w": 600, "charge_w": 0, "discharge_available_w": 5000, "charge_available_w": 5000},
            "recommendation_w": 0, "reason": "Flexibele lasten eerst; batterij gebruikt pas het resterende netoverschot",
            "faults": {}, "batteries": [{"id":"bat_demo","name":"Toekomstige batterij · voorbeeld","valid":True,"soc_pct":62.4,"power_w":600,"capacity_kwh":10,"controllable":False,"phase_hint":"three_phase","control_kind":"read_only","control_enabled":False,"exclusive_control_confirmed":False}],
            "note":"Voorbeeldprofiel. Positief batterijvermogen = ontladen naar huis; fysieke regeling blijft uit tot expliciete dubbele toestemming."
        },
        "smart_climate": {
            "enabled": True, "control_enabled": False, "outside_c": 20.5, "forecast_hours": 48, "forecast_error":"",
            "decision": {"mode":"off","reason":"Tussenseizoen: circa 18 uur bruikbare coasttijd vóór Panasonic AUTO opnieuw nodig wordt; aangeleerde zonnewinst is meegewogen","hard_override":False,"confidence":demo_coast_confidence,"forecast_confidence":demo_readiness_2["forecast_confidence"],"control_ready":True,"required_components":demo_required_components,"missing_components":[],"readiness_by_zone":{"climate.heat_pump_zone_2":demo_readiness_2},"block_reason":"","predicted_min_c":20.4,"predicted_max_c":21.3,"crossing_h":22,"required_lead_h":4.0,"season_context":"shoulder","season_strength":0.10,"comfort_direction":"heating","effective_coast_window_h":8.5,"solar_gain_used":True},
            "season_context":"shoulder", "manual_fixed_mode":False, "manual_hold_remaining_h":0, "commands_today":0, "last_command_mode":"", "model_confidence":demo_coast_confidence,
            "complete_model_confidence":0, "manual_off_zones":["climate.heat_pump_zone_1"], "zone_holds":{}, "pending_commands":[],
            "reliability":{"automatic_coast":{"confidence":demo_coast_confidence,"control_ready":True,"block_reason":"","status":"Betrouwbaar"}},
            "zones":[
                {"entity_id":"climate.heat_pump_zone_1","name":"Zone 1","current":21.0,"target":21.0,"mode":"off","action":"off","action_known":True,"manual_off":True,"hvac_modes":["heat","off","cool","auto"],"execution_reason":"Alleen advies: de handmatige UIT-keuze blijft behouden","native_program":{"program":"heating","source":"configured_entity","fresh":True}},
                {"entity_id":"climate.heat_pump_zone_2","name":"Zone 2","current":21.1,"target":21.0,"mode":"off","action":"off","action_known":True,"manual_off":False,"hvac_modes":["heat","off","cool","auto"],"execution_reason":"Automatische bediening staat uit; de ruimte blijft nu op temperatuur","native_program":{"program":"heating","source":"configured_entity","fresh":True}}],
            "profiles": {
                "climate.heat_pump_zone_1":demo_profile_1,
                "climate.heat_pump_zone_2":demo_profile_2,
            },
            "weather_bias": {"enabled":True,"total_samples":52,"pending":4,"horizons":[
                {"horizon_h":6,"bias_c":0.3,"applied_c":0.3,"confidence":0.82,"samples":18,"days":9},
                {"horizon_h":12,"bias_c":0.5,"applied_c":0.5,"confidence":0.76,"samples":16,"days":8},
                {"horizon_h":24,"bias_c":0.7,"applied_c":0.7,"confidence":0.62,"samples":12,"days":6},
                {"horizon_h":48,"bias_c":1.1,"applied_c":0.0,"confidence":0.31,"samples":6,"days":3}],
                "note":"Positief = de gekozen weersdienst voorspelde lokaal gemiddeld te koud; negatief = gemiddeld te warm."},
            "solar_gain": {"enabled":True,"forecast_hours":48,"next_24h_kwh_proxy":18.4,"peak_w_proxy":5400,"note":"PV is alleen een lokale instralingsproxy voor het thermische model; niet hetzelfde als zonnewarmte door ramen."},
            "coast_feedback": {"enabled":True,"counts":{"correct":6,"te_lang":1,"te_voorzichtig":2,"handmatig":0},"scored":9,"adjustment_h":0.5,"effective_min_coast_window_h":8.5,"total_coast_h":73.5,"note":"Alleen het minimale nuttige coastvenster wordt begrensd aangepast; comfortbanden blijven ongewijzigd."},
            "alerts":[{"severity":"info","title":"Adviesmodus","message":"Het model leert en adviseert, maar stuurt Panasonic AUTO/OFF nog niet fysiek."}],
            "settings": {**CLIMATE_DEFAULTS, "enabled": True, "control_enabled": False,
                "weather_entity": "weather.home",
                "outside_temp_entity": "sensor.outdoor_temperature",
                "zone_entities": ["climate.heat_pump_zone_1", "climate.heat_pump_zone_2"]},
            "settings_catalog": climate_catalog({**CLIMATE_DEFAULTS, "enabled": True, "control_enabled": False,
                "weather_entity": "weather.home",
                "outside_temp_entity": "sensor.outdoor_temperature",
                "zone_entities": ["climate.heat_pump_zone_1", "climate.heat_pump_zone_2"]}),
            "service":"solar_pilot.set_climate_setting",
            "note":"SolarPilot vraagt alleen AUTO of UIT en controleert het werkelijke warmtepompprogramma. De Panasonic-integratie bepaalt hoe die opdracht op het toestel wordt uitgevoerd.",
            "explanation":[
                "Zonnewinst: werkelijke PV dient als lokale instralingsproxy. SolarPilot leert per zone hoeveel extra opwarming daarmee samenhangt en begrenst de invloed.",
                "Weerscorrectie: forecastfouten op 6/12/24/48 uur worden lokaal geleerd en pas bij voldoende vertrouwen toegepast.",
                "Coast-evaluatie: eerdere coastperioden worden beoordeeld als correct, te lang of te voorzichtig. Alleen het minimale nuttige coastvenster mag binnen grenzen verschuiven.",
                "Open ramen/deuren zijn bewust géén onderdeel van deze versie."
            ]
        },
        "planner": {
            "enabled": True, "horizon_h": 36, "slot_min": 15, "confidence": 0.74, "plan_runs": 38,
            "predicted_import_kwh": 5.2, "predicted_export_kwh": 8.7, "predicted_cost_eur": 1.18,
            "predicted_self_use_kwh": 18.4, "base_load_samples": 27,
            "quality": {
                "last_7d": {"days":7,"samples":132,"pv_mae_w":385.0,"pv_bias_w":-74.0,"base_mae_w":168.0,"base_bias_w":31.0,"net_mae_w":442.0,"net_bias_w":-52.0,"execution_match_pct":91.7,"quality_score":82.4},
                "last_30d": {"days":21,"samples":401,"pv_mae_w":421.0,"pv_bias_w":-61.0,"base_mae_w":191.0,"base_bias_w":27.0,"net_mae_w":476.0,"net_bias_w":-45.0,"execution_match_pct":89.6,"quality_score":79.8},
                "findings": ["De recente plannerfouten zijn binnen de ingestelde waarschuwingsbanden."]
            },
            "replay": {
                "ready": True, "reason":"Plannerreplay op recente gemeten PV/basislast; geen fysieke appliance-simulatie",
                "buffer":{"samples":1184,"days":13,"retention_days":14,"from":"2026-09-11T00:00:00+02:00","to":"2026-09-24T12:45:00+02:00"},
                "scenarios":[
                    {"label":"Huidig","import_kwh":58.7,"export_kwh":71.2,"cost_eur":15.48,"peak_w":4210,"planned_kwh":18.5,"days":7},
                    {"label":"Meer PV benutten","import_kwh":57.9,"export_kwh":70.3,"cost_eur":15.22,"peak_w":4390,"planned_kwh":18.5,"days":7,"delta_import_kwh":-0.8,"delta_export_kwh":-0.9,"delta_cost_eur":-0.26,"delta_peak_w":180},
                    {"label":"Piek strenger","import_kwh":59.1,"export_kwh":71.6,"cost_eur":15.57,"peak_w":3770,"planned_kwh":18.5,"days":7,"delta_import_kwh":0.4,"delta_export_kwh":0.4,"delta_cost_eur":0.09,"delta_peak_w":-440},
                    {"label":"Prijs niet meewegen","import_kwh":59.4,"export_kwh":71.9,"cost_eur":15.73,"peak_w":4260,"planned_kwh":18.5,"days":7,"delta_import_kwh":0.7,"delta_export_kwh":0.7,"delta_cost_eur":0.25,"delta_peak_w":50}
                ]
            },
            "warnings": [],
            "findings": ["Lokale namiddagschaduw is in de PV-horizon verwerkt", "Toekomstige batterijruimte is alleen adviserend meegetekend"],
            "devices": {
                "flex_load": {"name":"Flexlast · voorbeeld","required_kwh":1.10,"planned_kwh":1.24,"selected_slots":[3,4,5,6],"cheap_grid_slots":[],"reason":"Dagdoel volledig ingepland","contiguous_cycle":False,"cycle_program":"","cycle_confidence":0,"cycle_duration_min":0},
                "dishwasher": {"name":"Vaatwasser","required_kwh":0.82,"planned_kwh":0.82,"selected_slots":[10,11,12,13,14,15],"cheap_grid_slots":[],"reason":"Beschermde cyclus aaneengesloten ingepland (Eco)","contiguous_cycle":True,"cycle_program":"Eco","cycle_confidence":0.86,"cycle_duration_min":88},
                "extra": {"name":"Extra verbruiker","required_kwh":0.55,"planned_kwh":0.60,"selected_slots":[8],"cheap_grid_slots":[],"reason":"Dagdoel volledig ingepland","contiguous_cycle":False,"cycle_program":"","cycle_confidence":0,"cycle_duration_min":0}
            },
            "timeline": [
                {"start":"2026-09-24T12:00:00+02:00","pv_w":4200,"base_w":1150,"planned_load_w":0,"battery_w":600,"net_w":-2450,"devices":[],"import_price":0.30,"export_price":0.03},
                {"start":"2026-09-24T12:15:00+02:00","pv_w":4700,"base_w":1180,"planned_load_w":0,"battery_w":800,"net_w":-2720,"devices":[],"import_price":0.30,"export_price":0.03},
                {"start":"2026-09-24T12:30:00+02:00","pv_w":5200,"base_w":1200,"planned_load_w":550,"battery_w":1000,"net_w":-2450,"devices":["flex_load"],"import_price":0.30,"export_price":0.03},
                {"start":"2026-09-24T12:45:00+02:00","pv_w":5400,"base_w":1220,"planned_load_w":550,"battery_w":1000,"net_w":-2630,"devices":["flex_load"],"import_price":0.30,"export_price":0.03},
                {"start":"2026-09-24T13:00:00+02:00","pv_w":5100,"base_w":1260,"planned_load_w":550,"battery_w":1000,"net_w":-2290,"devices":["flex_load"],"import_price":0.30,"export_price":0.03},
                {"start":"2026-09-24T13:15:00+02:00","pv_w":4800,"base_w":1280,"planned_load_w":550,"battery_w":900,"net_w":-2070,"devices":["flex_load"],"import_price":0.30,"export_price":0.03},
                {"start":"2026-09-24T13:30:00+02:00","pv_w":4300,"base_w":1300,"planned_load_w":0,"battery_w":700,"net_w":-2300,"devices":[],"import_price":0.30,"export_price":0.03},
                {"start":"2026-09-24T13:45:00+02:00","pv_w":3900,"base_w":1320,"planned_load_w":0,"battery_w":500,"net_w":-2080,"devices":[],"import_price":0.30,"export_price":0.03},
                {"start":"2026-09-24T14:00:00+02:00","pv_w":3500,"base_w":1350,"planned_load_w":2400,"battery_w":0,"net_w":250,"devices":["extra"],"import_price":0.24,"export_price":0.03}
            ],
            "settings": {**PLANNER_DEFAULTS},
            "settings_catalog": planner_catalog({**PLANNER_DEFAULTS}),
            "held_devices": ["Extra verbruiker"], "early_grid_devices": [],
            "price_sources": {"import":"tijdgestempelde prijsreeks","export":"vaste prijs"},
            "adaptive_power_guard": True
        },
        "today": {"date":"2026-09-21", "site_import_kwh":2.1, "site_export_kwh":5.4, "pv_kwh":21.5, "pv_self_used_kwh":16.1, "managed_kwh":4.8, "managed_solar_kwh":4.2, "managed_grid_kwh":0.6, "managed_battery_kwh":0, "estimated_value_eur":1.13, "samples_s":36000, "self_consumption_pct":74.9},
    },
    "devices": [
        {
            "id": "flex_load",
            "name": "Flexlast · voorbeeld",
            "priority": 2,
            "kind": "switch",
            "mode": "auto",
            "owned": True,
            "on": True,
            "available": True,
            "power_w": 550,
            "target_w": 550,
            "reason": "Beschikbaar overschot; dagminimum heeft voorrang",
            "boost_seconds": 0,
            "manual_seconds": 0,
            "non_interruptible": False,
            "estimated": False,
            "priority_entity": "number.voorbeeld_ontvochtiger_prioriteit",
            "mode_entity": "select.voorbeeld_ontvochtiger_modus",
            "boost_entity": "button.voorbeeld_ontvochtiger_boost",
            "cancel_entity": "button.voorbeeld_ontvochtiger_annuleren",
            "status_entity": "sensor.voorbeeld_ontvochtiger_status",
            "takeover_entity": "button.voorbeeld_ontvochtiger_overnemen",
            "allow_wallbox_reclaim": True,
            "daily_runtime_s": 4500,
            "min_daily_runtime_s": 7200,
            "max_daily_runtime_s": 14400,
            "daily_deadline": "18:00:00",
            "deadline_grid_allowed": False,
            "deadline_urgent": True,
            "time_window_enabled": True, "time_window_start":"09:00:00", "time_window_end":"18:00:00",
            "forecast_deferrable": True, "planner_hold": False, "planner_reason":"Planner laat start toe", "planner_grid_force": False,
            "configured_nominal_w": 550, "effective_nominal_w": 575,
            "learning": {"samples": 42, "p90_w": 575},
            "phase": {"classification":"L1","confidence":.92,"samples":8,"distinct_days":5,"phase_shares":[.96,.02,.02]},
        },
        {
            "id": "dishwasher",
            "name": "Vaatwasser",
            "priority": 3,
            "kind": "script",
            "mode": "auto",
            "owned": False,
            "on": False,
            "available": True,
            "power_w": 0,
            "target_w": 0,
            "reason": "Startklaar; planner wacht op beste aaneengesloten cyclusvenster",
            "boost_seconds": 0,
            "manual_seconds": 0,
            "non_interruptible": True,
            "estimated": False,
            "priority_entity": "number.voorbeeld_dishwasher_prioriteit",
            "mode_entity": "select.voorbeeld_dishwasher_modus",
            "boost_entity": "button.voorbeeld_dishwasher_boost",
            "cancel_entity": "button.voorbeeld_dishwasher_annuleren",
            "status_entity": "sensor.voorbeeld_dishwasher_status",
            "takeover_entity": "button.voorbeeld_dishwasher_overnemen",
            "daily_runtime_s": 0,
            "min_daily_runtime_s": 0,
            "max_daily_runtime_s": 0,
            "daily_deadline": "23:59:00",
            "deadline_grid_allowed": False,
            "deadline_urgent": False,
            "time_window_enabled": False, "time_window_start":"00:00:00", "time_window_end":"23:59:00",
            "forecast_deferrable": True, "planner_hold": True, "planner_reason":"Eco-cyclus aaneengesloten gepland vanaf 14:30", "planner_grid_force": False,
            "configured_nominal_w": 1800, "effective_nominal_w": 1800,
            "cycle_learning": {"program":"Eco","energy_kwh":0.82,"duration_min":88,"peak_w":1870,"average_w":559,"confidence":0.86,"cycles":9,"days":7,"source":"geleerd"},
            "phase": {"classification":"unknown","confidence":0,"samples":0,"distinct_days":0,"phase_shares":[0,0,0]},
        },
        {
            "id": "extra",
            "name": "Extra verbruiker",
            "priority": 4,
            "kind": "switch",
            "mode": "disabled",
            "owned": False,
            "on": False,
            "available": True,
            "power_w": 0,
            "target_w": 0,
            "reason": "Uitgesloten van regeling",
            "boost_seconds": 0,
            "manual_seconds": 0,
            "non_interruptible": False,
            "estimated": True,
            "priority_entity": "number.voorbeeld_extra_prioriteit",
            "mode_entity": "select.voorbeeld_extra_modus",
            "boost_entity": "button.voorbeeld_extra_boost",
            "cancel_entity": "button.voorbeeld_extra_annuleren",
            "status_entity": "sensor.voorbeeld_extra_status",
            "takeover_entity": "button.voorbeeld_extra_overnemen",
            "daily_runtime_s": 0,
            "min_daily_runtime_s": 0,
            "max_daily_runtime_s": 0,
            "daily_deadline": "23:59:00",
            "deadline_grid_allowed": False,
            "deadline_urgent": False,
            "time_window_enabled": True, "time_window_start":"10:00:00", "time_window_end":"19:00:00",
            "forecast_deferrable": True, "planner_hold": True, "planner_reason":"Volgend uur circa 0,80 kWh meer PV voorspeld; optionele start uitgesteld", "planner_grid_force": False,
            "configured_nominal_w": 900, "effective_nominal_w": 900,
            "phase": {"classification":"L3","confidence":.79,"samples":6,"distinct_days":4,"phase_shares":[.05,.07,.88]},
        },
    ],
    "recent_decisions": [
        {"time": "2026-09-21T11:24:15+00:00", "message": "Ontvochtiger kreeg restvermogen; Wallbox regelde zelfstandig terug."},
        {"time": "2026-09-21T11:22:10+00:00", "message": "Andere toestellen voorrang staat aan. Geen Wallbox-opdrachten."},
    ],
    "wallbox": {
        "enabled": True,
        "name": "Wallbox",
        "policy": "house_first",
        "read_only": True,
        "state": "house_first",
        "reason": "Andere toestellen eerst; Wallbox gebruikt het resterende overschot",
        "power_w": 3000,
        "reported_status": "Charging",
        "reported_mode": "full_solar",
        "last_report_age_s": 36,
        "remaining_s": 0,
        "stable_extra_w": 2000,
        "warning": "",
        "possible_interactions": 0,
        "block_increase": False,
        "release_flexible": False,
        "others_first": True,
        "priority_switch": "switch.voorbeeld_andere_toestellen_voorrang",
        "reclaimable_w": 3000,
        "handover": {
            "state": "success",
            "device_name": "Flexlast · voorbeeld",
            "reason": "Overname bevestigd; Wallbox regelde zelf terug.",
        },
    },
    "learning": {
        "enabled": True,
        "status": "Leren; begrensde aanpassing actief",
        "samples": 8,
        "successes": 8,
        "failures": 0,
        "response_p90_s": 105,
        "configured_stable_s": 180,
        "effective_stable_s": 180,
        "switch_entity": "switch.voorbeeld_lokaal_leren",
        "reset_entity": "button.voorbeeld_leergegevens_wissen",
    },
    "dhw": {
        "configured": True,
        "enabled": True,
        "status": "Extra voorraad wacht op het einde van de koelactiviteit",
        "execution": {"reason":"Extra voorraad wacht op het einde van de koelactiviteit", "surplus_target_c":60,
                      "gates":[{"code":"cooling","passed":False,"reason":"Er is nog gemelde koelactiviteit"}],
                      "last_change":{"at":"2026-09-24T12:00:00+02:00","reason":"Toesteldoel 50 °C teruggelezen; verhoging blijft begrensd tijdens koeling. Dit bewijst geen opwarming.","source":"solarpilot","confirmed":True}},
        "reason": "Voldoende zonneopbrengst; verhoging naar 60 °C geblokkeerd door koeling",
        "stage": "solar",
        "temperature_c": 46.2,
        "actual_target_c": 50,
        "proposed_target_c": 50,
        "base_target_c": 50,
        "normal_target_c": 50,
        "minimum_c": 46,
        "tank_differential_c": -5,
        "normal_c": 50,
        "expected_restart_c": 45,
        "night": False,
        "cooling": True,
        "cooling_block": True,
        "capacity_block": False,
        "optional_import_headroom_w": 5650,
        "low_temperature": False,
        "pending": False,
        "owned": True,
        "needs_review": False,
        "manual_hold": False,
        "fault": "",
        "pv_w": 6200,
        "measured_solar_export_w": 150,
        "before_boiler_w": None,
        "own_meter_available": False,
        "remaining_s": 0,
        "last_success": None,
        "switch_entity": "switch.voorbeeld_boiler_regeling",
        "review_entity": "button.voorbeeld_boilercontrole",
        "takeover_entity": "button.voorbeeld_boiler_overnemen",
        "number_entities": {
            "minimum_c": "number.voorbeeld_boiler_minimum_c",
            "tank_differential_c": "number.voorbeeld_boiler_tank_differential_c",
            "normal_c": "number.voorbeeld_boiler_normal_c",
            "solar_c": "number.voorbeeld_boiler_solar_c",
            "surplus_c": "number.voorbeeld_boiler_surplus_c",
            "cooling_cap_c": "number.voorbeeld_boiler_cooling_cap_c",
            "pv_threshold_w": "number.voorbeeld_boiler_pv_threshold_w",
            "surplus_threshold_w": "number.voorbeeld_boiler_surplus_threshold_w",
            "estimated_heat_power_w": "number.voorbeeld_boiler_estimated_heat_power_w",
        },
        "settings": {
            "minimum_c": 46,
            "tank_differential_c": -5,
            "normal_c": 50,
            "solar_c": 50,
            "surplus_c": 60,
            "cooling_cap_c": 50,
            "pv_threshold_w": 1000,
            "surplus_threshold_w": 3000,
            "estimated_heat_power_w": 3200,
            "night_enabled": True,
            "night_start": "23:00:00",
            "night_end": "06:00:00",
            "rise_delay_s": 300,
            "fall_delay_s": 300,
            "cooling_clear_s": 1800,
            "cooling_detection": "action",
        },
    },
}


# Fictitious beta.28 gentle DHW fixture; never a household measurement.
attributes['dhw']['settings'].update(normal_c=50, minimum_c=46, morning_enabled=True,
    morning_c=46, morning_time='09:00:00', evening_enabled=True, evening_cap_c=55,
    respect_space_climate=True, optional_raise_interval_s=1800)
attributes['dhw']['comfort_plan']={
    'native_restart_c':45, 'comfort_floor_c':46, 'projected_c':46.3,
    'evening_target_c':53, 'evening_completed':False,
    'limit_note':'50 °C normaal en -5 °C differentie: native herstart rond 45 °C. 46 °C is een bewaakte comfortgrens, geen gegarandeerd minimum.',
    'reason':'Fictief voorbeeld: voorraad beoordeeld; geen tijdelijke herstelboost.'}
attributes['dhw']['tank_learning']={'loss_c_h':.25,'heat_c_h':6,
    'loss_source':'ingestelde terugvalraming','heat_source':'ingestelde terugvalraming'}

# Fictitious beta.24 display fixtures; not read from household data.
attributes["ems"]["electricity_today"] = {
    "date": "2026-09-27", "basis": "gemeten tot nu toe", "partial": False,
    "import_kwh": 10, "export_kwh": 6, "pv_kwh": 11, "direct_pv_kwh": 5,
    "import_cost_eur": 3, "export_revenue_eur": .18, "net_cost_eur": 2.82,
    "pv_avoided_cost_eur": 1.5, "coverage_pct": 100,
    "coverage_note": "Vandaag tot nu toe; fictieve voorbeeldmetingen",
    "solar_note": "Directe zon is al verwerkt in de lagere netafname.",
    "note": "Netafnamekost min injectievergoeding; eigen zon niet nogmaals aftrekken. Exclusief vaste kosten en capaciteitstarief.",
}
attributes["ems"]["planner"]["cost_breakdown"] = {
    "import_cost_eur": 1.56, "export_revenue_eur": .38, "net_cost_eur": 1.18,
    "includes_pv_and_export": True,
}
attributes["wallbox"]["per_device_priority"] = True
attributes["wallbox"]["priority_min_power_w"] = 4140
attributes["wallbox"]["consumer_priority"] = {
    "state": "yield", "reason": "Genoeg voor Wallbox: lagere lasten vrijgeven na hun minimumlooptijd",
    "minimum_w": 4140, "potential_w": 4350, "block_starts": True, "yield_loads": True,
}
attributes["devices"][0]["wallbox_first"] = True
attributes["devices"][0]["wallbox_precedence"] = "wallbox_first"

# Fictitious beta.35 priority data, not household preferences or live HA state.
attributes["config_entry_id"] = "offline-example"
_order = ["device:dishwasher", "wallbox", "device:flex_load", "device:extra", "dhw_extra"]
_names = {"device:" + d["id"]: d["name"] for d in attributes["devices"]}
_names.update(wallbox="Auto laden · Wallbox", dhw_extra="Extra boilerwarmte · 60 °C")
attributes["priority_board"] = {
    "active": False, "revision": "fictitious-beta35-example", "order": _order,
    "wallbox_power": {key: True for key in _order if key.startswith("device:")},
    "rows": [{"id": key, "name": _names[key], "position": n + 1, "active": True,
        "kind": "dishwasher" if key == "device:dishwasher" else "switch" if key.startswith("device:") else key,
        **({"device_id": key[7:], "status": "Auto", "wallbox_power": True} if key.startswith("device:") else {}),
        "power_label": "Alleen werkelijk vrij zonneoverschot" if key == "dhw_extra" else "Gebruikt het resterende zonnevermogen" if key == "wallbox" else "Ja, onder voorwaarden" if key == "device:dishwasher" else "Nee · Wallbox heeft voorrang",
        "reason": "Voorbeeld: lopende beurt wordt niet onderbroken." if key == "device:dishwasher" else "Voorbeeld: gekozen positie en actuele voorwaarden blijven gelden."} for n, key in enumerate(_order)],
    "protected": [{"id": key, "name": title, "active": True, "power_label": "Blijft beschermd", "reason": explanation} for key, title, explanation in [
        ("safety", "Beveiliging en hygiëne", "Fabrikantbeveiliging en het bestaande sterilisatieprogramma blijven gelden."),
        ("dhw_comfort", "Gewoon warm water", "Bestaand normaal doel en comfortgrens; Panasonic bepaalt de herverwarming."),
        ("dhw_evening", "Noodzakelijke avondvoorraad", "Volgens het bestaande voorraadplan, niet de extra 60 °C-buffer."),
        ("space_comfort", "Ruimteverwarming en koeling", "Thermostaatdoelen en handmatige standen blijven behouden.")]],
    "constraints": [{"before": "wallbox", "after": "dhw_extra", "reason": "Extra boilerwarmte blijft na de Wallbox."},
        {"before": "device:dishwasher", "after": "dhw_extra", "reason": "De afwas behoudt voorrang op extra boilerwarmte."}],
    "note": "Fictief voorbeeld: de bestaande voorrang blijft behouden totdat je een wijziging bevestigt. Deze pagina slaat niets op.",
}

html = f'''<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SolarPilot {guide_mod.GUIDE_VERSION} Control Center voorbeeld</title><style>body{{margin:0;padding:18px;background:#f3f5f7;max-width:520px;margin-inline:auto}}solar-pilot-card{{display:block}}</style></head><body><p style="font:13px/1.5 system-ui">Fictieve voorbeeldgegevens · geen live bediening of opslag</p><solar-pilot-card></solar-pilot-card><script>{card}</script><script>
const attributes = {json.dumps(attributes, ensure_ascii=False)};
// Start the explicitly fictitious meter snapshot when the example opens.
for(const source of ['pv','grid']) attributes.energy_display[source].reported_at=Date.now()/1000;
const card=document.querySelector('solar-pilot-card'); card.setConfig({{}});
const guideAttributes = {json.dumps(guide_attributes, ensure_ascii=False)};
card.hass={{user:{{is_admin:true}},callWS:async msg=>{{if(msg.type==='solar_pilot/priority_board'&&!msg.save)return structuredClone(attributes.priority_board);throw new Error('Offline voorbeeld: er wordt niets opgeslagen of opgehaald.');}},states:{{'sensor.solarpilot_status':{{state:'Zonnestroom',attributes}},'sensor.solarpilot_actuele_uitleg':{{state:guideAttributes.version,attributes:guideAttributes}}}}, callService:async()=>{{throw new Error('Deze voorbeeldpagina bedient geen apparaten. Gebruik de kaart binnen Home Assistant voor echte bediening.');}}}};
card.addEventListener('hass-more-info',()=>window.alert('Dit is een offline voorbeeld.'));
</script></body></html>'''
(ROOT / "SolarPilot-voorbeeld.html").write_text(html, encoding="utf-8")
print("SolarPilot-voorbeeld.html rebuilt")
