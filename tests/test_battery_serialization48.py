"""Real runtime paths serialize battery writes and finish neutral removal ACK."""
from types import SimpleNamespace
import time

import pytest

from test_battery_runtime import setup_battery
from custom_components.solar_pilot.battery_runtime import BatteryFleetManager

@pytest.mark.asyncio
async def test_battery_neutral_removal_command_is_confirmed_then_removal_finishes():
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    hass.states.set("sensor.bat_power", 1000, {"unit_of_measurement": "W"})
    await runtime.prepare_removal()
    assert runtime.battery_fleet.busy
    assert runtime.battery_fleet.state.pending["target_w"] == 0
    assert not runtime.removal_overview()["ready"]
    # A native power report must still be reconciled while removal is active.
    hass.states.set("sensor.bat_power", 0, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert not runtime.battery_fleet.busy
    await runtime.tick()
    assert runtime.removal_overview()["ready"]
    assert not runtime.battery_fleet.settings["control_enabled"]
    assert [call for call in hass.services.calls if call[0] == "number"] == [
        ("number", "set_value", {"entity_id": "number.bat_setpoint", "value": 0.0}),
    ]

@pytest.mark.asyncio
async def test_unconfirmed_battery_removal_command_advances_timeout_without_repeating():
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    hass.states.set("sensor.bat_power", 1000, {"unit_of_measurement": "W"})
    await runtime.prepare_removal()
    runtime.battery_fleet.state.pending["issued_wall"] -= runtime.battery_fleet.settings["ack_timeout_s"]+1
    await runtime.tick()
    assert not runtime.battery_fleet.busy
    assert "bat1" in runtime.battery_fleet.state.faults
    assert not runtime.removal_overview()["ready"]
    assert len([call for call in hass.services.calls if call[0] == "number"]) == 1
