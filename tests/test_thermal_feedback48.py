"""Climate feedback requires confirmed commands and current hourly coverage."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.thermal_climate import ClimateDecision
from test_thermal_runtime import mature, setup_climate
from test_thermal_runtime_beta48 import (
    QuietCloudServices, climate_calls, clock, forecast, report, tick, user_mode_event,
)


@pytest.mark.asyncio
async def test_first_late_blank_auto_after_timeout_cannot_revoke_cancelled_user_off(monkeypatch):
    runtime, hass = setup_climate(control=True, mode="auto")
    hass.services = QuietCloudServices(hass.states)
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    report(hass, "climate.home", "off", current_temperature=19.5)
    manager.state.expected_mode = {"climate.home": "off"}
    forecast(hass, wall[0])
    await tick(manager, wall[0])
    user_mode_event(manager, "climate.home", "off")

    previous = deepcopy(hass.states.get("climate.home"))
    wall[0] += manager.COMMAND_TIMEOUT_S + 1
    report(hass, "climate.home", "auto")
    manager.on_event(SimpleNamespace(data={
        "entity_id": "climate.home", "old_state": previous,
        "new_state": hass.states.get("climate.home"),
    }, context=SimpleNamespace(id="late-cloud-refresh", user_id=None)))
    await tick(manager, wall[0])

    assert "climate.home" in manager.manual_off
    assert "climate.home" in manager.cancelled_auto
    assert manager.zone_holds["climate.home"] > wall[0]
    assert "climate.home" not in manager.state.expected_mode
    assert len(climate_calls(hass)) == 1
    user_mode_event(manager, "climate.home", "auto")
    assert "climate.home" not in manager.manual_off
    assert "climate.home" not in manager.cancelled_auto


@pytest.mark.asyncio
async def test_release_feedback_scores_only_after_later_auto_confirmation(monkeypatch):
    runtime, hass = setup_climate(control=True, mode="auto")
    hass.services = QuietCloudServices(hass.states)
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    report(hass, "climate.home", "off", current_temperature=19.5)
    zones = [zone for zone in manager._zones() if zone["entity_id"] == "climate.home"]
    manager.state.expected_mode = {"climate.home": "off"}
    manager.state.coast_feedback.start(wall[0] - 3600, zones, ClimateDecision("off", "confirmed coast"), manager.settings)
    forecast(hass, wall[0])

    await tick(manager, wall[0])
    assert manager.pending_commands
    assert manager.state.coast_feedback.scored == 0
    assert manager.state.coast_feedback.history == []

    wall[0] += manager.REPORT_DELAY_S
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])
    assert not manager.pending_commands
    assert manager.state.coast_feedback.scored == 1
    assert manager.state.coast_feedback.history[0]["outcome"] == "te_lang"
    wall[0] += manager.REPORT_DELAY_S
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])
    assert manager.state.coast_feedback.scored == 1


@pytest.mark.asyncio
async def test_fresh_fixed_heat_mode_cannot_create_a_phantom_coast_episode(monkeypatch):
    runtime, hass = setup_climate(control=True, mode="auto")
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    before_await_zones = manager._zones()
    report(hass, "climate.home", "heat")
    manager.state.last_decision = ClimateDecision("off", "advice before weather await")

    result = await manager._send_mode("off", before_await_zones)

    assert not result and not climate_calls(hass)
    assert manager.state.coast_feedback.active is None
    assert manager.state.coast_feedback.pending is None
    assert manager.state.coast_feedback.scored == 0
    assert not manager.pending_commands


@pytest.mark.asyncio
async def test_expired_forecast_cannot_authorize_a_new_coast(monkeypatch):
    runtime, hass = setup_climate(control=True, mode="auto")
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    manager.settings["solar_gain_enabled"] = False
    mature(manager)
    forecast(hass, wall[0] - 72 * 3600)

    await tick(manager, wall[0])

    assert not climate_calls(hass)
    assert not manager.state.last_decision.control_ready
    assert "hourly_forecast" in manager.state.last_decision.missing_components


@pytest.mark.asyncio
async def test_gap_in_near_hourly_forecast_cannot_be_compacted_into_safe_coverage(monkeypatch):
    runtime, hass = setup_climate(control=True, mode="auto")
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    manager.settings["solar_gain_enabled"] = False
    mature(manager)
    forecast(hass, wall[0])
    del hass.services.forecast[3]

    await tick(manager, wall[0])

    assert not climate_calls(hass)
    assert len(manager._outside_hourly()) == 3
    assert "hourly_forecast" in manager.state.last_decision.missing_components


@pytest.mark.asyncio
async def test_fresh_hourly_forecast_permits_coast_after_discarding_past_rows(monkeypatch):
    runtime, hass = setup_climate(control=True, mode="auto")
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    manager.settings["solar_gain_enabled"] = False
    mature(manager)
    forecast(hass, wall[0] - 72 * 3600, temperature=-100)
    past_rows = list(hass.services.forecast)
    forecast(hass, wall[0], temperature=21)
    hass.services.forecast = past_rows + hass.services.forecast

    await tick(manager, wall[0])

    assert manager._outside_hourly() == [21.] * 48
    assert manager.state.last_decision.control_ready
    assert manager.state.last_decision.desired_mode == "off"
    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "off"}),
        ("climate", "set_hvac_mode", {"entity_id": "climate.salon", "hvac_mode": "off"}),
    ]
    assert manager.state.coast_feedback.active is None
    wall[0] += manager.REPORT_DELAY_S
    report(hass, "climate.home", "off")
    report(hass, "climate.salon", "off")
    await tick(manager, wall[0])
    assert not manager.pending_commands
    assert manager.state.coast_feedback.active is not None


@pytest.mark.asyncio
async def test_lost_forecast_releases_owned_off_despite_daily_and_hold_limits_without_waking_manual_zone(monkeypatch):
    runtime, hass = setup_climate(control=True, mode="off")
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    manager.settings["solar_gain_enabled"] = False
    mature(manager)
    manager.state.expected_mode = {"climate.home": "off"}
    user_mode_event(manager, "climate.salon", "off")
    manager.state.last_command_wall = wall[0]
    manager.zone_command_walls["climate.home"] = wall[0]
    manager.state.command_day = manager._local_day()
    manager.state.commands_today = manager.settings["max_commands_per_day"]
    forecast(hass, wall[0] - 72 * 3600)

    await tick(manager, wall[0])

    assert "hourly_forecast" in manager.state.last_decision.missing_components
    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]
    assert hass.states.get("climate.home").state == "auto"
    assert hass.states.get("climate.salon").state == "off"
    assert "climate.salon" in manager.manual_off


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["current_temperature", "temperature"])
async def test_boolean_zone_temperature_blocks_actuation_and_learning(monkeypatch, field):
    runtime, hass = setup_climate(control=True, mode="off")
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    mature(manager)
    manager.state.expected_mode = {"climate.home": "off"}
    report(hass, "climate.home", **{field: True})
    forecast(hass, wall[0])
    before = manager.state.profiles["climate.home"].snapshot()

    await tick(manager, wall[0])

    assert not climate_calls(hass)
    assert "klimaatzones" in manager.state.fault
    assert manager.state.profiles["climate.home"].snapshot() == before
