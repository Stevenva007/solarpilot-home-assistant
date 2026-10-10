"""Automatic task presentation never supplies SG/control or compressor proof."""
from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot.power_activity import power_activity, task_observations
from test_heatpump_power_activity66 import complete, task_display
from test_native_display_sources67 import display_setup
from test_sg_observations64 import split


def route(stamp=990):
    return {"function": "tapwater_heating", "source": "aquarea_entity", "kind": "tank_route", "observed_at": stamp}


def metered(main=2170, heater=0, *, stamp=999, complete_coverage=True):
    return {"valid": True, "complete": complete_coverage, "watts": main + heater,
            "measured_wall": stamp, "meter_scope": "total", "supplies": {
                "supply1": {"valid": True, "watts": main, "measured_wall": stamp},
                "supply2": {"valid": True, "watts": heater, "measured_wall": stamp}}}


def interpret(main=2170, heater=0, *, now=1000, **kwargs):
    return power_activity(metered(main, heater), {"stale_s": 120, "power_supply1_role": "main",
        "power_supply2_role": "heater", "power_supply_profile": "panasonic_standard"},
        tank=NS(state="heating", attributes={"operation_mode": "heating"}),
        tank_entity="water_heater.tank", tank_stamp=990, now_wall=now, **kwargs)


@pytest.mark.parametrize("function,action", [("space_heating", "heating"), ("space_cooling", "cooling"),
    ("tapwater_heating", "dhw")])
def test_explicit_native_task_is_independent_of_any_meter(function, action):
    kwargs = {"zones": [{"entity_id": "climate.room", "available": True, "action": action, "observed_at": 990}]}
    if function == "tapwater_heating":
        kwargs = {"tank": NS(state="on", attributes={"hvac_action": action}),
                  "tank_entity": "water_heater.tank", "tank_stamp": 990}
    actual, context = task_observations({}, now_wall=1000, **kwargs)
    assert actual["function"] == function and actual["observed_at"] == 990
    assert actual["source"] == "native_hvac_action" and context["function"] is None


@pytest.mark.parametrize("watts", [0, 58, 199, 2170])
def test_monitor_keeps_actual_task_even_below_interpretation_threshold(watts):
    runtime, hass = split(zone_entities=["climate.room"])
    hass.states.set("climate.room", "auto", {"hvac_action": "heating"})
    hass.states.set("sensor.hp_supply_one", watts, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"})
    view = runtime.panasonic.overview()
    assert view["native_task"]["function"] == "space_heating"
    assert view["power_activity"]["active"] is (watts >= 200)
    hass.states.data.pop("sensor.hp_supply_two")
    partial = runtime.panasonic.overview()
    assert partial["native_task"]["function"] == "space_heating"
    assert partial["power_activity"]["function"] is None and not partial["power_complete"]
    assert not hass.services.calls


def test_registered_tank_route_plus_active_main_is_explicitly_inferred():
    view = interpret(route_context=route())
    assert view["function"] == "tapwater_heating" and view["label"] == "Sanitair water opwarmen"
    assert view["function_source"] == "aquarea_entity" and view["function_kind"] == "tank_route"
    assert "hoofdcircuit en Panasonic-tankroute" in view["note"]
    assert view["context_observed_at"] == view["observed_at"] == 990
    assert all(row["role_assumed"] for row in view["supplies"])


@pytest.mark.parametrize("main,heater", [(0, 3000), (58, 3000), (199, 3000)])
def test_only_heater_draw_is_not_called_main_heat_pump_or_dhw(main, heater):
    view = interpret(main, heater, route_context=route())
    assert view["activity_kind"] == "heater" and view["label"] == "Elektrische bijverwarming actief"
    assert view["active"] and view["function"] is None
    assert view["context_observed_at"] is None and view["function_kind"] == "none"


def test_dhw_actual_action_and_selected_cool_programme_are_orthogonal():
    proof = {"entity_id": "water_heater.tank", "source": "aquarea_poll", "fresh": True,
             "raw_action": "HEATING_WATER", "action": "tapwater_heating", "observed_at": 980}
    programme = [{"program": "cooling", "fresh": True, "observed_at": 970}]
    view = interpret(tank_action=proof, native_programs=programme)
    assert view["function"] == "tapwater_heating" and view["function_kind"] == "native_action"
    assert view["function_source"] == "aquarea_poll"
    # WATER route plus active main draw is also a qualified inference; the
    # selected space programme does not mean space cooling is happening now.
    assert interpret(route_context=route(), native_programs=programme,
                     context="space_cooling", context_reliable=True, context_stamp=970)["function"] == "tapwater_heating"
    conflict = interpret(tank_action=proof, zones=[{"entity_id": "climate.room", "available": True,
        "action": "cooling", "observed_at": 990}], native_programs=programme)
    assert conflict["function"] is None and "niet eenduidig" in conflict["note"]


@pytest.mark.parametrize("raw,action", [("IDLE", "idle"), ("OFF", "off")])
def test_fresh_global_idle_does_not_leave_an_old_active_attribute_claim(raw, action):
    proof = {"entity_id": "water_heater.tank", "source": "aquarea_poll", "fresh": True,
             "raw_action": raw, "action": action, "observed_at": 995}
    tank = NS(state="heating", attributes={"hvac_action": "heating"})
    actual, _ = task_observations({}, tank=tank, tank_entity="water_heater.tank", tank_stamp=990,
                                 tank_action=proof, now_wall=1000)
    assert actual["function"] is None and actual["conflict"]


def test_estimated_zone_cannot_return_as_a_selected_controller_context():
    runtime, hass = split(tank_target_entity="water_heater.tank", zone_entities=["climate.room"])
    hass.states.set("water_heater.tank", "idle", {"operation_mode": "idle"})
    hass.states.set("climate.room", "heat", {"hvac_action": "heating", "estimated": True})
    view = runtime.panasonic.overview()
    assert view["context"] == "space_heating"  # Controller semantics untouched.
    assert view["task_context"]["function"] is None and view["native_task"]["function"] is None
    assert view["power_activity"]["function"] is None
    assert not hass.services.calls


@pytest.mark.parametrize("kind", ["route", "action"])
def test_new_meter_report_cannot_refresh_old_task_or_routing_context(kind):
    kwargs = {"route_context": route(879)} if kind == "route" else {
        "tank_action": {"entity_id": "water_heater.tank", "source": "aquarea_poll", "fresh": True,
                        "raw_action": "HEATING_WATER", "action": "tapwater_heating", "observed_at": 879}}
    view = interpret(**kwargs)
    assert view["function"] is None and view["label"] == "Warmtepomp werkt"
    assert view["observed_at"] != 879


def automatic_monitor(monkeypatch):
    env = display_setup(monkeypatch)
    runtime, hass = split()
    hass.config_entries = env.helper.runtime.hass.config_entries
    hass.states.data.update(env.helper.runtime.hass.states.data)
    env.helper.runtime.hass.states = hass.states
    env.state("sensor.hp_supply_one", 2170, {"unit_of_measurement": "W"})
    env.state("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"})
    return env, runtime, hass


def test_unbound_unique_native_sources_appear_only_in_display_and_do_not_change_sg(monkeypatch):
    env, runtime, hass = automatic_monitor(monkeypatch)
    before = deepcopy(runtime.panasonic.settings), deepcopy(runtime._snapshot())
    view = runtime.panasonic.overview()
    assert view["display_sources"]["tank_entity"] == env.sources["tank_entity"]
    assert {row["entity_id"] for row in view["display_zones"]} == set(env.sources["zone_entities"])
    assert view["task_context"]["kind"] == "tank_route"
    assert view["native_task"]["function"] is None
    assert view["power_activity"]["function"] == "tapwater_heating"
    assert view["zones"] == [] and view["target_c"] is None and view["temperature_c"] is None
    assert view["context"] == "normal" and view["cooling_possible"] is True
    assert (runtime.panasonic.settings, runtime._snapshot()) == before
    assert not hass.services.calls and not env.coordinator.api_calls


def test_automatic_fresh_defrost_overrides_inferred_or_reported_heating(monkeypatch):
    env, runtime, hass = automatic_monitor(monkeypatch)
    env.state(env.sources["zone_entities"][0], "auto", {"hvac_action": "heating"})
    env.state(env.sources["defrost_entity"], "on")
    view = runtime.panasonic.overview()
    assert view["defrost"]["state"] == "active" and view["defrost"]["observed_at"] is not None
    assert view["native_task"]["function"] is None and "ontdooien" in view["native_task"]["label"]
    assert view["power_activity"]["function"] is None and view["power_activity"]["active"]
    assert not hass.services.calls


@pytest.mark.parametrize("has_tank", [True, False])
def test_registered_space_zone_misbound_as_tank_cannot_invent_dhw(monkeypatch, has_tank):
    env, runtime, hass = automatic_monitor(monkeypatch)
    zone = env.sources["zone_entities"][0]
    runtime.panasonic.settings["tank_target_entity"] = zone
    env.state(zone, "auto", {"hvac_action": "heating"})
    env.state(env.sources["tank_entity"], "idle", {"operation_mode": "idle"})
    if not has_tank:
        env.rows.pop(env.sources["tank_entity"])
        hass.states.data.pop(env.sources["tank_entity"])
    view = runtime.panasonic.overview()
    assert view["display_tank"]["entity_id"] == (env.sources["tank_entity"] if has_tank else "")
    assert view["native_task"]["function"] == "space_heating"
    assert view["power_activity"]["function"] == "space_heating"
    assert runtime.panasonic.settings["tank_target_entity"] == zone
    assert not hass.services.calls


@pytest.mark.parametrize("flag", ["restored", "estimated", "is_estimated"])
def test_unreliable_defrost_flag_cannot_become_task_proof(monkeypatch, flag):
    env, runtime, hass = automatic_monitor(monkeypatch)
    env.state(env.sources["zone_entities"][0], "auto", {"hvac_action": "heating"})
    env.state(env.sources["defrost_entity"], "on", {flag: True})
    view = runtime.panasonic.overview()
    assert view["defrost"]["state"] == "unknown"
    assert view["native_task"]["function"] == "space_heating"
