"""Real runtime paths serialize battery writes and finish neutral removal ACK."""
from types import SimpleNamespace
import time

import pytest

from test_battery_runtime import setup_battery
from test_thermal_runtime import ClimateServices
from test_dhw_runtime import setup as setup_dhw
from custom_components.solar_pilot.battery_runtime import BatteryFleetManager


def pending_climate(runtime, hass):
    hass.config = SimpleNamespace(time_zone="Europe/Brussels",
                                  units=SimpleNamespace(temperature_unit="°C"))
    hass.states.set("climate.home", "off", {
        "current_temperature": 21, "temperature": 21, "temperature_unit": "°C",
        "hvac_action": "off", "hvac_modes": ["auto", "off"],
    })
    hass.states.set("sensor.outdoor", 21, {"unit_of_measurement": "°C"})
    manager = runtime.smart_climate
    manager.settings.update(enabled=True, control_enabled=False,
                            zone_entities=["climate.home"], outside_temp_entity="sensor.outdoor")
    now = time.time()
    manager.state.expected_mode["climate.home"] = "auto"
    manager.pending_commands["climate.home"] = {
        "mode": "auto", "issued_wall": now, "expires_wall": now+180,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("removal", [False, True])
async def test_pending_climate_blocks_new_battery_setpoint_including_removal(removal):
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    pending_climate(runtime, hass)
    runtime.mode = "paused" if removal else "solar"
    runtime.removal_requested = removal
    if removal:
        hass.states.set("sensor.bat_power", 1000, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.smart_climate.busy
    assert not runtime.battery_fleet.busy
    assert not [call for call in hass.services.calls if call[0] in ("number", "script", "climate")]


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


@pytest.mark.asyncio
async def test_pending_battery_command_blocks_new_climate_auto_release():
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    hass.config = SimpleNamespace(time_zone="Europe/Brussels",
                                  units=SimpleNamespace(temperature_unit="°C"))
    hass.services = ClimateServices(hass.states)
    hass.states.set("climate.home", "off", {
        "current_temperature": 19.5, "temperature": 21, "temperature_unit": "°C",
        "hvac_action": "off", "hvac_modes": ["auto", "off"],
    })
    # A cold outside reading establishes a real heating need for the automatic
    # controller; a neutral 21 °C outside reading is not heating evidence.
    hass.states.set("sensor.outdoor", 5, {"unit_of_measurement": "°C"})
    # The source also proves a matching programme; outside temperature alone
    # cannot authorize AUTO while the device is configured for cooling.
    hass.states.set("sensor.native_program", "HEAT", {})
    manager = runtime.smart_climate
    manager.settings.update(enabled=True, control_enabled=True,
                            zone_entities=["climate.home"], outside_temp_entity="sensor.outdoor",
                            operation_mode_entity="sensor.native_program")
    # This OFF belongs to SolarPilot, so a fresh cold comfort breach genuinely
    # needs an AUTO release as soon as the outstanding battery write settles.
    manager.state.expected_mode["climate.home"] = "off"
    await runtime.battery_fleet._send("bat1", -1800)
    assert runtime.battery_fleet.busy
    hass.services.calls.clear()
    runtime.mode = "solar"
    await runtime.tick()
    assert runtime.battery_fleet.busy
    assert not [call for call in hass.services.calls if call[0] == "climate"]
    # Later fresh battery consumption settles the existing command. Climate
    # control resumes on the next normal tick, without re-sending the battery.
    hass.states.set("sensor.bat_power", -1800, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert not runtime.battery_fleet.busy
    await runtime.tick()
    assert [call for call in hass.services.calls if call[0] == "climate"] == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]


@pytest.mark.asyncio
async def test_pending_battery_command_blocks_new_boiler_target_until_ack():
    runtime, hass = setup_dhw()
    # This case isolates serialization; settling is tested separately.
    runtime.settings["settle_s"] = 0
    battery_runtime, battery_hass = setup_battery(
        global_control=True, profile_control=True, exclusive=True)
    for key in ("battery_fleet", "batteries"):
        runtime.entry.options[key] = battery_runtime.entry.options[key]
    for entity in ("sensor.bat_soc", "sensor.bat_power", "number.bat_setpoint"):
        obj = battery_hass.states.get(entity)
        hass.states.set(entity, obj.state, obj.attributes)
    runtime.battery_fleet = BatteryFleetManager(runtime)
    hass.states.set("sensor.grid", -4500, {"unit_of_measurement": "W"})
    hass.states.set("sensor.pv", 8000, {"unit_of_measurement": "W"})
    await runtime.battery_fleet._send("bat1", -1800)
    assert runtime.battery_fleet.busy
    hass.services.calls.clear()
    await runtime.tick()
    assert runtime.battery_fleet.busy
    assert not [call for call in hass.services.calls if call[1] == "set_temperature"]
    hass.states.set("sensor.bat_power", -1800, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert not runtime.battery_fleet.busy
    hass.states.set("sensor.grid", -4500, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert [call for call in hass.services.calls if call[1] == "set_temperature"] == [
        ("water_heater", "set_temperature", {"entity_id": "water_heater.boiler", "temperature": 60.0}),
    ]
