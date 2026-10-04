"""Pause gives back owned controls and keeps unknown/manual states protected.

Uses explicit HA service/state doubles; no physical installation.
"""
from copy import deepcopy
from datetime import datetime

import pytest
from homeassistant.exceptions import HomeAssistantError

from test_thermal_runtime import setup_climate
from test_thermal_runtime_beta48 import clock, report, forecast, climate_calls, ZONE
from test_battery_runtime import setup_battery


@pytest.mark.asyncio
async def test_pause_releases_owned_off_only_and_waits_for_later_auto_report(monkeypatch):
    runtime, hass = setup_climate(control=True, mode="off")
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    runtime.mode = "solar"
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.home": "off"}
    await runtime.set_mode("paused")
    assert climate_calls(hass) == [("climate", "set_hvac_mode", {
        "entity_id": "climate.home", "hvac_mode": "auto"})]
    assert hass.states.get("climate.salon").state == "off"
    assert manager.busy and manager.removal_blocked()
    before = deepcopy(manager.settings)
    with pytest.raises(HomeAssistantError, match="Pauze"):
        await manager.async_set_setting("enabled", False)
    assert manager.settings == before
    wall[0] += 11
    report(hass, "climate.home", "auto")
    await runtime.tick()
    await runtime.tick()
    assert not manager.busy and not manager.removal_blocked()
    await manager.async_set_setting("control_enabled", False)
    await manager.async_set_setting("enabled", False)
    assert manager.settings["enabled"] is False
    assert len(climate_calls(hass)) == 1
    assert hass.states.get("climate.salon").state == "off"


@pytest.mark.asyncio
async def test_pause_with_all_manual_off_zones_sends_no_auto(monkeypatch):
    runtime, hass = setup_climate(control=True, mode="off")
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    runtime.mode = "solar"
    await runtime.set_mode("paused")
    assert not climate_calls(hass)
    assert hass.states.get("climate.home").state == "off"
    assert hass.states.get("climate.salon").state == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize("setting", ["enabled", "control_enabled"])
async def test_owned_off_prevents_disabling_climate_before_safe_pause(setting):
    runtime, hass = setup_climate(control=True, mode="off")
    runtime.smart_climate.state.expected_mode = {"climate.home": "off"}
    before = deepcopy(runtime.smart_climate.settings)
    options = deepcopy(runtime.entry.options)
    with pytest.raises(HomeAssistantError, match="Pauze"):
        await runtime.smart_climate.async_set_setting(setting, False)
    assert runtime.smart_climate.settings == before
    assert runtime.entry.options == options
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["off", "auto"])
async def test_one_missing_owned_zone_cannot_be_released_through_available_sibling(mode):
    runtime, hass = setup_climate(control=True, mode="off")
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.salon": mode}
    report(hass, "climate.salon", "unavailable")
    assert manager.removal_blocked()
    assert await manager.prepare_for_removal() is False
    assert manager.state.expected_mode == {"climate.salon": mode}
    assert not climate_calls(hass)
    with pytest.raises(HomeAssistantError, match="beheer"):
        await manager.async_set_setting("zone_entities", ["climate.home"])
    assert manager.state.expected_mode == {"climate.salon": mode}


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


@pytest.mark.asyncio
@pytest.mark.parametrize("coverage", [24, 8, 2])
async def test_thermal_decision_reports_only_complete_common_forecast_tail(monkeypatch, coverage):
    runtime, hass = setup_climate(control=True)
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    manager = runtime.smart_climate
    manager._solar_hourly = lambda now, hours: [0]*coverage + [None]*(hours-coverage)
    await manager.tick(local_now=datetime.fromtimestamp(wall[0], ZONE), allow_command=False)
    decision = manager.state.last_decision
    assert decision.evaluated_forecast_h == coverage
    for row in decision.readiness_by_zone.values():
        assert row["forecast_hours"] == coverage
    if coverage == 2:
        assert "hourly_forecast" in decision.missing_components
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_internal_thermal_pv_gap_cannot_be_hidden_by_trimming_later_known_hours(monkeypatch):
    runtime, hass = setup_climate(control=True)
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    manager = runtime.smart_climate
    manager._solar_hourly = lambda now, hours: [0]*4 + [None] + [0]*19 + [None]*(hours-24)
    await manager.tick(local_now=datetime.fromtimestamp(wall[0], ZONE), allow_command=False)
    decision = manager.state.last_decision
    assert decision.evaluated_forecast_h == 48
    assert "solar_forecast" in decision.missing_components
    assert not climate_calls(hass)
