"""Presentation clocks remain live without duplicating unchanged Recorder rows."""
from copy import deepcopy

import pytest

from test_runtime import build
from test_sensor_recorder59 import sensor
from test_switch_recorder60 import recorded, switch


@pytest.mark.parametrize("platform,suffix", [("switch", "sg_boost_enabled"), ("sensor", "sg_boost_status")])
def test_idle_sg_render_clock_and_actual_relay_reports_do_not_change_recorded_payload(platform, suffix):
    runtime, hass = build()
    manager = runtime.sg_boost
    clock = [1_800_000_000.0]
    manager._wall_clock = lambda: clock[0]
    manager._status({"output": False})
    entity = switch(runtime, suffix) if platform == "switch" else sensor(runtime, suffix)
    before = deepcopy(runtime._snapshot())
    first = entity.extra_state_attributes
    clock[0] += 15
    manager._status({"output": False})  # another genuine identical readback
    second = entity.extra_state_attributes
    assert first["observed_at"] < second["observed_at"]
    assert first["relay_observed_at"] < second["relay_observed_at"]
    assert recorded(entity, first) == recorded(entity, second)
    assert second == manager.overview()
    assert runtime._snapshot() == before and not hass.services.calls


@pytest.mark.parametrize("suffix,expected", [("panasonic_power", 1800), ("dhw_temperature", 48), ("dhw_target", 50)])
def test_new_panasonic_receipt_aliases_are_live_and_numeric_native_measurements_stay_recordable(suffix, expected):
    runtime, hass = build()
    runtime.panasonic.update_config({"power_entity": "sensor.hp_total", "power_scope": "total",
        "tank_temperature_entity": "sensor.hp_tank", "tank_target_entity": "sensor.hp_target"})
    hass.states.set("sensor.hp_total", 1800, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp_tank", 48, {"unit_of_measurement": "°C"})
    hass.states.set("sensor.hp_target", 50, {"unit_of_measurement": "°C"})
    entity = sensor(runtime, suffix)
    live = entity.extra_state_attributes
    archived = recorded(entity, live)
    assert entity.native_value == expected
    assert live["target_stamp"] == live["target_observed_at"]
    assert live["power_observed_at"] == live["power_stamp"]
    assert all(key not in archived for key in ("target_stamp", "target_observed_at", "power_observed_at"))
    assert archived["power_w"] == live["power_w"] == 1800
    assert archived["temperature_c"] == live["temperature_c"] == 48
    assert archived["target_c"] == live["target_c"] == 50
    assert not hass.services.calls
