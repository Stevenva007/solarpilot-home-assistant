"""Dynamic display inference never amends native operation or SG evidence."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from test_sg_observations64 import split


def known_native_program(monkeypatch, runtime, hass, entity_id, programme="heating"):
    def read(eid):
        if eid != entity_id:
            return {"fresh": False, "program": None}
        stamp = runtime.panasonic._reported_stamp(hass.states.get(eid))
        return {"entity_id": eid, "fresh": True, "program": programme,
                "raw_mode": "AUTO_HEAT" if programme == "heating" else "AUTO_COOL", "observed_at": stamp}
    monkeypatch.setattr(runtime.panasonic.native_program, "read", read)
    monkeypatch.setattr(runtime.panasonic.native_program, "read_device_action", lambda eid: {})


@pytest.mark.parametrize("programme,function", [("heating", "space_heating"), ("cooling", "space_cooling")])
def test_idle_and_active_main_resolve_display_task_without_native_or_sg_changes(monkeypatch, programme, function):
    runtime, hass = split(tank_target_entity="water_heater.tank", zone_entities=["climate.room"],
                          compressor_frequency_entity="sensor.hp_frequency", power_activity_threshold_w=2000)
    hass.states.set("sensor.hp_supply_one", 1360, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp_frequency", 0, {"unit_of_measurement": "Hz"})
    hass.states.set("water_heater.tank", "idle", {"operation_mode": "idle", "current_temperature": 49, "temperature": 50})
    hass.states.set("climate.room", "auto", {"hvac_action": "idle", "current_temperature": 22, "temperature": 21})
    known_native_program(monkeypatch, runtime, hass, "climate.room", programme)
    proof = {"entity_id": "water_heater.tank", "source": "aquarea_poll", "fresh": True,
             "raw_action": "IDLE", "action": "idle",
             "observed_at": runtime.panasonic._reported_stamp(hass.states.get("water_heater.tank"))}
    monkeypatch.setattr(runtime.panasonic.native_program, "read_tank_action", lambda eid: deepcopy(proof))
    before = runtime.panasonic.overview()
    budget = sg_solar_budget(runtime)
    journal, permissions, calls = deepcopy(runtime._snapshot()), deepcopy(runtime.sg_boost.config), list(hass.services.calls)
    assert before["power_activity"]["function"] is None and before["native_task"]["inactive_action"] == "idle"
    runtime.panasonic.settings["power_activity_threshold_w"] = 200
    after = runtime.panasonic.overview()
    assert after["power_activity"]["function"] == function
    assert after["power_activity"]["function_kind"] == "selected_program"
    assert after["power_activity"]["function_source"] == "native_program"
    assert after["native_task"] == before["native_task"] and after["native_task"]["inactive"] is True
    assert after["operation"] == before["operation"] and after["operation"]["state"] == "idle"
    for key in ("context", "context_reliable", "context_signature", "cooling_possible", "compressor_running", "sg_status"):
        assert after[key] == before[key]
    assert sg_solar_budget(runtime) == budget
    assert runtime._snapshot() == journal and runtime.sg_boost.config == permissions
    assert hass.services.calls == calls == []


def test_estimated_opposite_zone_does_not_veto_valid_display_programme_or_amend_sg_conflict(monkeypatch):
    runtime, hass = split(zone_entities=["climate.native_room", "climate.estimated_room"],
                          power_activity_threshold_w=2000)
    hass.states.set("sensor.hp_supply_one", 1360, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"})
    hass.states.set("climate.native_room", "auto", {"hvac_action": "idle"})
    hass.states.set("climate.estimated_room", "cool", {"hvac_action": "cooling", "estimated": True})
    known_native_program(monkeypatch, runtime, hass, "climate.native_room")
    before = runtime.panasonic.overview()
    journal, budget, permissions = deepcopy(runtime._snapshot()), sg_solar_budget(runtime), deepcopy(runtime.sg_boost.config)
    assert before["context"] == "heatpump_unknown" and before["cooling_possible"] is True
    assert before["task_context"]["function"] == "space_heating"
    assert before["native_task"]["function"] is None
    runtime.panasonic.settings["power_activity_threshold_w"] = 200
    after = runtime.panasonic.overview()
    assert after["power_activity"]["function"] == "space_heating"
    assert after["power_activity"]["function_kind"] == "selected_program"
    assert after["context"] == before["context"] and after["cooling_possible"] == before["cooling_possible"]
    assert after["native_task"] == before["native_task"]
    assert runtime._snapshot() == journal and sg_solar_budget(runtime) == budget
    assert runtime.sg_boost.config == permissions and hass.services.calls == []
