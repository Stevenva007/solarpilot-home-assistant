"""Pause gives back owned controls and keeps unknown/manual states protected.

Uses explicit HA service/state doubles; no physical installation.
"""
from copy import deepcopy
from datetime import datetime

import pytest
from homeassistant.exceptions import HomeAssistantError

from test_battery_runtime import setup_battery

@pytest.mark.asyncio
async def test_pause_neutralizes_acknowledged_owned_battery_target_only():
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    manager = runtime.battery_fleet
    profile = manager.configs["bat1"]
    hass.states.set("number.bat_setpoint", -1800, {"min": -3000, "max": 3000,
                                                   "step": 1, "unit_of_measurement": "W"})
    hass.states.set("sensor.bat_power", -1800, {"unit_of_measurement": "W"})
    manager.state.expected_numbers[profile["id"]] = {
        "entity_id": "number.bat_setpoint", "target_w": -1800}
    runtime.mode = "solar"
    await runtime.set_mode("paused")
    assert manager.busy and manager.state.pending["target_w"] == 0
    calls = [call for call in hass.services.calls if call[0] == "number"]
    assert calls == [("number", "set_value", {"entity_id": "number.bat_setpoint", "value": 0.0})]
    hass.states.set("sensor.bat_power", 0, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert not manager.busy
    await runtime.tick()  # Reconcile and release the acknowledged neutral target.
    assert not manager.state.expected_numbers
    assert manager.settings["control_enabled"] is True  # Permission retained for deliberate resume.
    await runtime.set_mode("observe")
    assert runtime.mode == "observe"
    assert len([call for call in hass.services.calls if call[0] == "number"]) == 1
