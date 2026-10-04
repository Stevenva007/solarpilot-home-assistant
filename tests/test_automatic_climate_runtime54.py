"""Actual AUTO/OFF orchestration, durable intent and source-boundary regressions."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.thermal_climate import ClimateDecision
from custom_components.solar_pilot.thermal_runtime import SmartClimateManager
from test_thermal_runtime import setup_climate
from test_thermal_runtime_beta48 import (
    QuietCloudServices, climate_calls, clock, forecast, report, tick, user_mode_event,
)


def automatic(monkeypatch, *, mode="off", temp=21, outside=14, zones=None):
    runtime, hass = setup_climate(control=True, mode=mode, temp=temp)
    runtime.mode = "solar"
    manager = runtime.smart_climate
    manager.settings.update(automatic_zone_control=True, solar_gain_enabled=False,
                            automatic_min_run_h=1, automatic_min_off_h=1,
                            max_commands_per_day=2)
    if zones is not None:
        manager.settings["zone_entities"] = zones
    hass.services = QuietCloudServices(hass.states)
    wall = clock(monkeypatch, hass)
    hass.states.set("sensor.outdoor", outside, {"unit_of_measurement": "°C"})
    forecast(hass, wall[0], outside)
    return runtime, hass, manager, wall


def refresh(hass, wall, outside=14):
    for eid, obj in list(hass.states.data.items()):
        hass.states.set(eid, obj.state, obj.attributes)
    hass.states.set("sensor.outdoor", outside, {"unit_of_measurement": "°C"})
    forecast(hass, wall, outside)


@pytest.mark.asyncio
async def test_startup_unowned_off_heating_need_automatically_releases_auto(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5)
    await tick(manager, wall[0])
    assert [c[2] for c in climate_calls(hass)] == [
        {"entity_id": "climate.home", "hvac_mode": "auto"},
        {"entity_id": "climate.salon", "hvac_mode": "auto"},
    ]
    assert manager.busy
    assert manager.manual_off == set()
    assert all(d.urgent_auto for d in manager.zone_decisions.values())
    assert not any("temperature" in c[2] for c in climate_calls(hass))


@pytest.mark.asyncio
async def test_one_cold_zone_never_wakes_a_warm_self_cooling_room(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=22)
    report(hass, "climate.salon", current_temperature=19.5)
    await tick(manager, wall[0])
    assert [c[2]["entity_id"] for c in climate_calls(hass)] == ["climate.salon"]
    assert manager.zone_decisions["climate.home"].desired_mode == "off"
    assert manager.state.last_decision.desired_mode == "mixed"


@pytest.mark.asyncio
@pytest.mark.parametrize("temperature", [21, 22, 23])
async def test_winter_label_does_not_keep_no_demand_auto_working(monkeypatch, temperature):
    _, hass, manager, wall = automatic(monkeypatch, mode="auto", temp=temperature)
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 2
    assert all(c[2]["hvac_mode"] == "off" for c in climate_calls(hass))
    assert all(d.stage == "reactive" for d in manager.zone_decisions.values())
    assert manager.overview()["automatic_zone_control"] is True


@pytest.mark.asyncio
async def test_hot_room_in_hot_outlook_uses_auto_cooling_without_learned_model(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=23, outside=40)
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 2
    assert all(d.comfort_direction == "cooling" and d.urgent_auto for d in manager.zone_decisions.values())


@pytest.mark.asyncio
async def test_per_zone_minimum_run_does_not_restart_or_reset_on_each_guard(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    await tick(manager, wall[0])
    start = manager.zone_command_walls["climate.home"]
    wall[0] += 10
    report(hass, "climate.home", "auto", current_temperature=21)
    await tick(manager, wall[0])
    assert not manager.busy and len(climate_calls(hass)) == 1
    for elapsed in (100, 900, 3599):
        wall[0] = start + elapsed
        refresh(hass, wall[0])
        await tick(manager, wall[0])
        assert len(climate_calls(hass)) == 1
        assert manager.zone_command_walls["climate.home"] == start
    wall[0] = start + 3600
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 2
    assert climate_calls(hass)[-1][2]["hvac_mode"] == "off"


@pytest.mark.asyncio
async def test_comfort_required_auto_bypasses_cycle_hold_and_optimization_cap(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    manager.zone_command_walls["climate.home"] = wall[0]
    manager.zone_command_counts["climate.home"] = {"day": manager._local_day(), "count": 2, "optimization_count": 2}
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1
    assert manager.zone_command_counts["climate.home"]["optimization_count"] == 2


@pytest.mark.asyncio
async def test_two_comfort_cycles_in_one_day_end_off_despite_daily_limit(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    for _ in range(2):
        refresh(hass, wall[0])
        report(hass, "climate.home", "off", current_temperature=19.5)
        await tick(manager, wall[0])
        wall[0] += 10
        refresh(hass, wall[0])
        report(hass, "climate.home", "auto", current_temperature=21)
        await tick(manager, wall[0])
        wall[0] += 3590
        refresh(hass, wall[0])
        await tick(manager, wall[0])
        wall[0] += 10
        refresh(hass, wall[0])
        report(hass, "climate.home", "off", current_temperature=21)
        await tick(manager, wall[0])
        wall[0] += 3600
    assert [c[2]["hvac_mode"] for c in climate_calls(hass)] == ["auto", "off", "auto", "off"]
    assert not manager.busy
    assert manager.zone_command_counts["climate.home"]["count"] == 4
    assert manager.zone_command_counts["climate.home"]["optimization_count"] == 0


@pytest.mark.asyncio
async def test_old_manual_off_without_real_hold_migrates_to_automatic_permission(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    saved = {"manual_off": ["climate.home"], "pending_commands": {}, "zone_holds": {}}
    manager.restore(saved)
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1
    assert manager.manual_off == set()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["off", "auto"])
async def test_native_user_choice_has_temporary_persisted_hold_then_resumes(monkeypatch, mode):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5 if mode == "off" else 22,
                                            mode=mode, zones=["climate.home"])
    user_mode_event(manager, "climate.home", mode)
    saved = manager.snapshot()
    runtime.smart_climate = manager = SmartClimateManager(runtime)
    manager.settings.update(automatic_zone_control=True, solar_gain_enabled=False, zone_entities=["climate.home"])
    manager.restore(saved)
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    wall[0] += 12 * 3600 + 1
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1
    assert climate_calls(hass)[0][2]["hvac_mode"] != mode


@pytest.mark.asyncio
async def test_command_timeout_is_sticky_after_hold_expiry_and_restart(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    await tick(manager, wall[0])
    wall[0] += manager.COMMAND_TIMEOUT_S + 1
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert "climate.home" in manager.command_faults
    saved = manager.snapshot()
    wall[0] += 13 * 3600
    refresh(hass, wall[0])
    runtime.smart_climate = manager = SmartClimateManager(runtime)
    manager.settings.update(automatic_zone_control=True, solar_gain_enabled=False, zone_entities=["climate.home"])
    manager.restore(saved)
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1
    assert "climate.home" in manager.command_faults
    with pytest.raises(HomeAssistantError):
        await manager.async_set_override("climate.home", "auto")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["unavailable", "wrong_unit", "restored", "stale"])
async def test_explicit_bad_outside_never_falls_back_and_invalidates_learning_endpoint(monkeypatch, bad):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5)
    for profile in [manager.state.profile("climate.home"), manager.state.profile("climate.salon")]:
        profile.last = {"wall": wall[0] - 1, "indoor": 21, "outdoor": 14}
        profile.action_started = {"wall": wall[0] - 1}
    attrs = {"unit_of_measurement": "°F" if bad == "wrong_unit" else "°C"}
    if bad == "restored":
        attrs["restored"] = True
    hass.states.set("sensor.outdoor", "unavailable" if bad == "unavailable" else 14, attrs,
                    age=1801 if bad == "stale" else 0)
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert manager.last_outside is None
    assert all(p.last is None and p.action_started is None for p in manager.state.profiles.values())


@pytest.mark.asyncio
async def test_zone_outage_between_sample_ticks_does_not_bridge_observation(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch)
    await tick(manager, wall[0])
    assert manager.state.profile("climate.home").last is not None
    wall[0] += 1
    report(hass, "climate.home", "unavailable")
    await tick(manager, wall[0])
    assert manager.state.profile("climate.home").last is None
    view = manager.overview()
    zone = next(z for z in view["zones"] if z["entity_id"] == "climate.home")
    assert not zone["valid"] and not zone["available"]
    assert zone["current"] is None


@pytest.mark.asyncio
async def test_weather_await_mode_change_cannot_dispatch_cached_auto(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5)
    original = hass.services.async_call
    async def change_mode(domain, action, *args, **kwargs):
        result = await original(domain, action, *args, **kwargs)
        if domain == "weather":
            runtime.mode = "observe"
        return result
    hass.services.async_call = change_mode
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert not manager.pending_commands


@pytest.mark.asyncio
async def test_weather_await_updated_room_temperature_gets_new_per_zone_decision(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5)
    original = hass.services.async_call
    async def room_warmed(domain, action, *args, **kwargs):
        result = await original(domain, action, *args, **kwargs)
        if domain == "weather":
            report(hass, "climate.home", current_temperature=22)
        return result
    hass.services.async_call = room_warmed
    await tick(manager, wall[0])
    assert [c[2]["entity_id"] for c in climate_calls(hass)] == ["climate.salon"]


@pytest.mark.asyncio
async def test_first_zone_service_await_cannot_dispatch_stale_second_zone_temperature(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5)
    original = hass.services.async_call
    async def changed_second_zone(domain, action, *args, **kwargs):
        result = await original(domain, action, *args, **kwargs)
        if domain == "climate":
            report(hass, "climate.salon", current_temperature=22)
        return result
    hass.services.async_call = changed_second_zone
    await tick(manager, wall[0])
    assert [c[2]["entity_id"] for c in climate_calls(hass)] == ["climate.home"]
    assert "climate.salon" not in manager.pending_commands


@pytest.mark.asyncio
@pytest.mark.parametrize("race", ["pause", "outside", "temperature", "native_off"])
async def test_durable_save_await_rechecks_sources_mode_and_user_intent_before_write(monkeypatch, race):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    original = runtime.store.async_save
    called = []
    async def save_then_change(data):
        await original(data)
        if not called:
            called.append(True)
            if race == "pause":
                runtime.mode = "paused"
            elif race == "outside":
                hass.states.set("sensor.outdoor", "unavailable", {"unit_of_measurement": "°C"})
            elif race == "temperature":
                report(hass, "climate.home", current_temperature=22)
            else:
                user_mode_event(manager, "climate.home", "off")
    runtime.store.async_save = save_then_change
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert not manager.pending_commands
    assert not runtime.store.data["smart_climate"]["pending_commands"]


@pytest.mark.asyncio
async def test_actual_service_observes_durable_journal_before_call(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    runtime.store.async_delay_save = lambda *args: None
    original = hass.services.async_call
    async def verify_journal(domain, action, data=None, **kwargs):
        if domain == "climate":
            saved = runtime.store.data["smart_climate"]["pending_commands"][data["entity_id"]]
            assert saved["mode"] == data["hvac_mode"]
            assert saved["context_id"] == kwargs["context"].id
        return await original(domain, action, data, **kwargs)
    hass.services.async_call = verify_journal
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1


@pytest.mark.asyncio
async def test_failed_durable_save_never_writes_hardware(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    async def failed_save(data):
        raise OSError("test storage unavailable")
    runtime.store.async_save = failed_save
    with pytest.raises(HomeAssistantError, match="journal"):
        await tick(manager, wall[0])
    assert not climate_calls(hass) and not manager.pending_commands
    assert not manager.zone_command_counts


@pytest.mark.asyncio
async def test_dashboard_fixed_off_survives_restart_comfort_breach_and_pause(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, mode="auto", temp=21, zones=["climate.home"])
    await manager.async_set_override("climate.home", "off")
    await tick(manager, wall[0])
    wall[0] += 10
    report(hass, "climate.home", "off", current_temperature=19.5)
    await tick(manager, wall[0])
    assert not manager.state.expected_mode
    saved = manager.snapshot()
    runtime.smart_climate = manager = SmartClimateManager(runtime)
    manager.settings.update(automatic_zone_control=True, solar_gain_enabled=False, zone_entities=["climate.home"])
    manager.restore(saved)
    wall[0] += 24 * 3600
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    runtime.mode = "paused"
    assert not await manager.prepare_for_removal()
    assert len(climate_calls(hass)) == 1
    assert manager.dashboard_overrides == {"climate.home": "off"}
    assert manager.overview()["zones"][0]["control_stage"] == "dashboard_override"


@pytest.mark.asyncio
async def test_dashboard_fixed_auto_stays_available_until_returned_automatic(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, mode="off", temp=22, zones=["climate.home"])
    await manager.async_set_override("climate.home", "auto")
    await tick(manager, wall[0])
    wall[0] += 10
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])
    wall[0] += 3600
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1
    await manager.async_set_override("climate.home", "automatic")
    await tick(manager, wall[0])
    assert climate_calls(hass)[-1][2]["hvac_mode"] == "off"


@pytest.mark.asyncio
async def test_missing_zone_still_allows_clearing_dashboard_choice_without_clearing_fault(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, mode="off", zones=["climate.home"])
    await manager.async_set_override("climate.home", "off")
    manager.command_faults["climate.home"] = "Uncertain earlier request"
    report(hass, "climate.home", "unavailable")
    view = manager.overview()
    assert view["zones"][0]["dashboard_override"] == "off"
    assert not view["zones"][0]["available"]
    await manager.async_set_override("climate.home", "automatic")
    assert not manager.dashboard_overrides
    assert manager.command_faults["climate.home"] == "Uncertain earlier request"
    assert not climate_calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("cached", [False, True])
async def test_fahrenheit_weather_never_becomes_a_celsius_heatwave_or_bias_sample(monkeypatch, cached):
    _, hass, manager, wall = automatic(monkeypatch, temp=22, outside=14)
    if cached:
        manager.state.forecast = [{"valid_ts": wall[0] + (h + 1) * 3600, "temperature": 40} for h in range(48)]
        manager.state.last_forecast_wall = wall[0]
    report(hass, "weather.home", temperature=40, temperature_unit="°F")
    forecast(hass, wall[0], 40)
    await tick(manager, wall[0])
    assert not climate_calls(hass)  # Fresh actual outside is cool: OFF remains OFF.
    assert manager.state.forecast == []
    assert manager.state.weather_bias.pending == {}
    assert manager.zone_decisions["climate.home"].desired_mode == "off"


@pytest.mark.asyncio
async def test_weather_units_change_during_response_does_not_queue_wrong_forecast(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=22, outside=14)
    original = hass.services.async_call
    async def fahrenheit_after_response(domain, action, *args, **kwargs):
        result = await original(domain, action, *args, **kwargs)
        if domain == "weather":
            report(hass, "weather.home", temperature=40, temperature_unit="°F")
        return result
    hass.services.async_call = fahrenheit_after_response
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert manager.state.forecast == [] and not manager.state.weather_bias.pending


@pytest.mark.asyncio
async def test_failed_manual_choice_preserves_new_native_auto_hold_during_save(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=22, zones=["climate.home"])
    user_mode_event(manager, "climate.home", "off")
    async def fail_after_native_auto(data):
        user_mode_event(manager, "climate.home", "auto")
        raise OSError("test save failed")
    runtime.store.async_save = fail_after_native_auto
    with pytest.raises(HomeAssistantError):
        await manager.async_set_override("climate.home", "auto")
    assert not manager.dashboard_overrides
    assert "climate.home" not in manager.manual_off
    assert manager.zone_holds["climate.home"] > wall[0]
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_dashboard_manual_modes_do_not_start_or_score_automatic_coast_feedback(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, mode="auto", zones=["climate.home"])
    await manager.async_set_override("climate.home", "off")
    await tick(manager, wall[0])
    assert not manager._feedback_batches
    wall[0] += 10
    report(hass, "climate.home", "off")
    await tick(manager, wall[0])
    assert manager.state.coast_feedback.active is None
    assert manager.state.coast_feedback.scored == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("current_temperature", -30), ("current_temperature", 90),
                                           ("temperature", 50), ("temperature", 2)])
async def test_non_room_temperature_source_cannot_be_controlled_as_a_room(monkeypatch, field, value):
    _, hass, manager, wall = automatic(monkeypatch, mode="auto", zones=["climate.home"])
    report(hass, "climate.home", **{field: value})
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert "klimaatzones" in manager.state.fault


@pytest.mark.asyncio
async def test_target_outside_reported_native_bounds_blocks_room_command(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    report(hass, "climate.home", temperature=21, min_temp=22, max_temp=30)
    await tick(manager, wall[0])
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_native_service_intent_does_not_clear_previous_uncertain_command_fault(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    manager.command_faults["climate.home"] = "Earlier AUTO was never confirmed"
    user_mode_event(manager, "climate.home", "auto")
    assert manager.command_faults["climate.home"] == "Earlier AUTO was never confirmed"
    wall[0] += 13 * 3600
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_forecast_source_changes_to_fahrenheit_during_journal_save_blocks_old_weather_plan(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=23, outside=40, zones=["climate.home"])
    original = runtime.store.async_save
    changed = []
    async def save_then_wrong_unit(data):
        await original(data)
        if not changed:
            changed.append(True)
            report(hass, "weather.home", temperature=40, temperature_unit="°F")
    runtime.store.async_save = save_then_wrong_unit
    await tick(manager, wall[0])
    assert not climate_calls(hass) and not manager.pending_commands
    assert not runtime.store.data["smart_climate"]["pending_commands"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["off", "auto"])
async def test_dashboard_review_adopts_actual_mode_persistently_without_any_actuator_call(monkeypatch, mode):
    runtime, hass, manager, wall = automatic(monkeypatch, mode=mode, temp=19.5 if mode == "off" else 22)
    manager.command_faults = {"climate.home": "Older uncertain mode", "climate.salon": "Other uncertain mode"}
    manager.state.expected_mode["climate.home"] = "auto" if mode == "off" else "off"
    observed_permission = []
    original = runtime.store.async_save
    async def save_after_asserting_fault(data):
        observed_permission.append(manager.command_faults.get("climate.home"))
        await original(data)
    runtime.store.async_save = save_after_asserting_fault
    assert await manager.async_set_override("climate.home", "review") == mode
    assert observed_permission == ["Older uncertain mode"]
    assert manager.dashboard_overrides["climate.home"] == mode
    assert "climate.home" not in manager.command_faults
    assert manager.command_faults["climate.salon"] == "Other uncertain mode"
    assert "climate.home" not in manager.state.expected_mode
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    saved = manager.snapshot()
    runtime.smart_climate = manager = SmartClimateManager(runtime)
    manager.settings.update(automatic_zone_control=True, solar_gain_enabled=False)
    manager.restore(saved)
    wall[0] += 24 * 3600
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert manager.dashboard_overrides["climate.home"] == mode


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["pending", "ordinary_pending", "unavailable", "action", "unit", "native_heat", "capability"])
async def test_dashboard_review_rejects_pending_or_unsafe_source_without_clearing_fault(monkeypatch, guard):
    runtime, hass, manager, wall = automatic(monkeypatch, zones=["climate.home"])
    manager.command_faults["climate.home"] = "Uncertain old command"
    if guard == "pending":
        manager.pending_commands["climate.home"] = {"mode": "auto", "issued_wall": wall[0], "expires_wall": wall[0] + 180}
    elif guard == "ordinary_pending":
        runtime.pending = {"id": "a", "issued": 1}
    elif guard == "unavailable":
        report(hass, "climate.home", "unavailable")
    elif guard == "action":
        report(hass, "climate.home", hvac_action="unknown")
    elif guard == "unit":
        report(hass, "climate.home", temperature_unit="°F")
    elif guard == "native_heat":
        report(hass, "climate.home", "heat")
    else:
        report(hass, "climate.home", hvac_modes=["off"])
    with pytest.raises(HomeAssistantError):
        await manager.async_set_override("climate.home", "review")
    assert manager.command_faults["climate.home"] == "Uncertain old command"
    assert not manager.dashboard_overrides and not climate_calls(hass)


@pytest.mark.asyncio
async def test_failed_review_save_leaves_prior_manual_choice_fault_and_lease_intact(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, zones=["climate.home"])
    manager.command_faults["climate.home"] = "Uncertain old command"
    manager.dashboard_overrides["climate.home"] = "auto"
    manager.state.expected_mode["climate.home"] = "auto"
    before = manager.snapshot()
    async def failed_save(data):
        raise OSError("Test unavailable storage")
    runtime.store.async_save = failed_save
    with pytest.raises(HomeAssistantError):
        await manager.async_set_override("climate.home", "review")
    assert manager.snapshot() == before
    assert not climate_calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("race", ["unavailable", "native_auto"])
async def test_review_rechecks_source_and_preserves_new_native_hold_after_save(monkeypatch, race):
    runtime, hass, manager, wall = automatic(monkeypatch, zones=["climate.home"])
    manager.command_faults["climate.home"] = "Uncertain old command"
    manager.state.expected_mode["climate.home"] = "auto"
    original = runtime.store.async_save
    changed = []
    async def save_then_change(data):
        await original(data)
        if not changed:
            changed.append(True)
            if race == "unavailable":
                report(hass, "climate.home", "unavailable")
            else:
                report(hass, "climate.home", "auto")
                user_mode_event(manager, "climate.home", "auto")
    runtime.store.async_save = save_then_change
    with pytest.raises(HomeAssistantError):
        await manager.async_set_override("climate.home", "review")
    assert manager.command_faults["climate.home"] == "Uncertain old command"
    assert not manager.dashboard_overrides
    assert runtime.store.data["smart_climate"]["command_faults"]["climate.home"] == "Uncertain old command"
    assert not runtime.store.data["smart_climate"]["dashboard_overrides"]
    if race == "native_auto":
        assert manager.zone_holds["climate.home"] > wall[0]
        assert "climate.home" not in manager.state.expected_mode
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_review_clears_old_target_fault_hold_then_explicit_automatic_can_resume(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    manager.command_faults["climate.home"] = "Uncertain AUTO"
    manager.zone_holds["climate.home"] = wall[0] + 12 * 3600
    manager.manual_off.add("climate.home")
    manager.cancelled_auto["climate.home"] = wall[0]
    await manager.async_set_override("climate.home", "review")
    assert "climate.home" not in manager.zone_holds
    assert "climate.home" not in manager.manual_off
    assert "climate.home" not in manager.cancelled_auto
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    await manager.async_set_override("climate.home", "automatic")
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1
    assert climate_calls(hass)[0][2]["hvac_mode"] == "auto"


@pytest.mark.asyncio
@pytest.mark.parametrize("race", ["native_auto", "unavailable"])
async def test_review_race_followed_by_corrective_save_failure_restores_sticky_fault_safely(monkeypatch, race):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    runtime.store.async_delay_save = lambda *args: None
    manager.command_faults["climate.home"] = "Unconfirmed earlier AUTO"
    manager.state.expected_mode["climate.home"] = "auto"
    manager.zone_holds["climate.home"] = wall[0] + 600
    manager.manual_off.add("climate.home")
    original = runtime.store.async_save
    saves = []
    async def persist_first_then_fail_correction(data):
        saves.append(deepcopy(data))
        if len(saves) == 1:
            await original(data)
            if race == "native_auto":
                report(hass, "climate.home", "auto")
                user_mode_event(manager, "climate.home", "auto")
            else:
                report(hass, "climate.home", "unavailable")
        else:
            raise OSError("Corrective save failed")
    runtime.store.async_save = persist_first_then_fail_correction
    with pytest.raises(HomeAssistantError):
        await manager.async_set_override("climate.home", "review")
    assert len(saves) == 2
    durable = deepcopy(runtime.store.data["smart_climate"])
    assert durable["command_faults"]["climate.home"] == "Unconfirmed earlier AUTO"
    assert durable["expected_mode"]["climate.home"] == "auto"
    assert durable["zone_holds"]["climate.home"] == wall[0] + 600
    # Restart with the first save alone. Even the stale manual OFF proposal
    # must remain blocked by its retained fault beside a now-native AUTO zone.
    runtime.store.async_save = original
    runtime.smart_climate = manager = SmartClimateManager(runtime)
    manager.settings.update(automatic_zone_control=True, solar_gain_enabled=False, zone_entities=["climate.home"])
    manager.restore(durable)
    report(hass, "climate.home", "auto" if race == "native_auto" else "off")
    wall[0] += 13 * 3600
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert manager.command_faults["climate.home"] == "Unconfirmed earlier AUTO"
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_immediate_restart_after_successful_review_before_delayed_save_retains_safe_fault(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.home"])
    manager.command_faults["climate.home"] = "Unconfirmed earlier AUTO"
    manager.state.expected_mode["climate.home"] = "auto"
    runtime.store.async_delay_save = lambda *args: None
    await manager.async_set_override("climate.home", "review")
    assert "climate.home" not in manager.command_faults  # Current reviewed manager.
    durable = deepcopy(runtime.store.data["smart_climate"])
    assert durable["command_faults"]["climate.home"] == "Unconfirmed earlier AUTO"
    runtime.smart_climate = manager = SmartClimateManager(runtime)
    manager.settings.update(automatic_zone_control=True, solar_gain_enabled=False, zone_entities=["climate.home"])
    manager.restore(durable)
    await manager.async_set_override("climate.home", "automatic")
    wall[0] += 13 * 3600
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert "climate.home" in manager.command_faults
    assert not climate_calls(hass)
