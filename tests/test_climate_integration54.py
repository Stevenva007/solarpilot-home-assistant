"""Automatic room control through the production EMS and live option path.

These are HA API doubles; they do not prove hardware or cloud acknowledgement.
"""
from copy import deepcopy
import time
from types import SimpleNamespace

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.engine import Action
from custom_components.solar_pilot.live_options import PENDING
from custom_components.solar_pilot.thermal_climate import ThermalProfile
from test_climate_serialization48 import attach_climate, fresh_grid
from test_dhw_runtime import setup as setup_dhw
from test_entry_lifecycle49 import entry_functions
from test_thermal_runtime_beta48 import climate_calls, report


def automatic_runtime(monkeypatch, *, dhw=False, temp=19.3, mode="off"):
    runtime, hass = setup_dhw(config={"enabled": dhw})
    wall = attach_climate(runtime, hass, monkeypatch)
    manager = runtime.smart_climate
    manager.settings.update(automatic_zone_control=True, control_enabled=True,
                            weather_entity="weather.home", solar_gain_enabled=False)
    runtime.entry.options["smart_climate"] = dict(manager.settings)
    hass.states.set("weather.home", "cloudy", {"temperature": 5, "temperature_unit": "°C"})
    hass.states.set("sensor.outdoor", 5, {"unit_of_measurement": "°C"})
    hass.services.forecast = [{**row, "temperature": 5} for row in hass.services.forecast]
    report(hass, "climate.home", mode, current_temperature=temp,
           hvac_action="off" if mode == "off" else "idle")
    runtime.mode = "solar"
    return runtime, hass, wall


async def dashboard(runtime, hass, *, mode, entity="climate.home"):
    hass.config_entries = SimpleNamespace(async_entries=lambda _domain: [runtime.entry])
    runtime.entry.runtime_data = runtime
    call = SimpleNamespace(data={"config_entry_id": runtime.entry.entry_id,
                                "entity_id": entity, "mode": mode})
    await entry_functions()["_handle_set_climate_override"](hass, call)


@pytest.mark.asyncio
async def test_full_ems_can_start_native_off_room_on_current_demand_without_model_training(monkeypatch):
    runtime, hass, _ = automatic_runtime(monkeypatch)
    await runtime.tick()
    assert climate_calls(hass) == [("climate", "set_hvac_mode", {
        "entity_id": "climate.home", "hvac_mode": "auto"})]
    assert runtime.smart_climate.pending_commands["climate.home"]["mode"] == "auto"
    assert runtime.problem_kind != "internal_fault"


@pytest.mark.asyncio
@pytest.mark.parametrize("grid", ["unavailable", 5000])
async def test_current_comfort_recovery_remains_available_without_solar_export(monkeypatch, grid):
    runtime, hass, _ = automatic_runtime(monkeypatch)
    hass.states.set("sensor.grid", grid, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert len(climate_calls(hass)) == 1
    assert climate_calls(hass)[0][2]["hvac_mode"] == "auto"
    assert runtime.smart_climate.zone_decisions["climate.home"].comfort_required
    assert not runtime.smart_climate.zone_decisions["climate.home"].solar_gain_used


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["observe", "paused"])
async def test_dashboard_auto_intent_waits_for_global_automatic_mode(monkeypatch, mode):
    runtime, hass, _ = automatic_runtime(monkeypatch)
    runtime.mode = mode
    await dashboard(runtime, hass, mode="auto")
    assert runtime.smart_climate.dashboard_overrides == {"climate.home": "auto"}
    assert runtime.store.data["smart_climate"]["dashboard_overrides"] == {"climate.home": "auto"}
    assert not climate_calls(hass)
    runtime.mode = "solar"
    await runtime.tick()
    assert len(climate_calls(hass)) == 1


@pytest.mark.asyncio
async def test_dashboard_choice_shares_ordinary_pending_command_serialization(monkeypatch):
    runtime, hass, _ = automatic_runtime(monkeypatch)
    hass.services.respond = False
    await runtime._send(Action("a", 1000, "Test bestaande opdracht"), time.monotonic())
    assert runtime.pending
    await dashboard(runtime, hass, mode="auto")
    assert runtime.smart_climate.dashboard_overrides == {"climate.home": "auto"}
    assert runtime.pending and not climate_calls(hass)
    hass.services.respond = True
    hass.states.set("switch.load", "on")
    fresh_grid(hass)
    await runtime.tick()
    assert runtime.pending is None
    assert len(climate_calls(hass)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("protection", ["hygiene", "powerful"])
async def test_full_ems_keeps_boiler_hygiene_and_manual_functions_ahead_of_room_auto(monkeypatch, protection):
    runtime, hass, _ = automatic_runtime(monkeypatch, dhw=True)
    entity = "binary_sensor.hygiene" if protection == "hygiene" else "switch.powerful"
    hass.states.set(entity, "on")
    await runtime.tick()
    assert runtime.dhw.reading.protected
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_full_ems_does_not_send_room_auto_while_boiler_target_waits_for_feedback(monkeypatch):
    runtime, hass, wall = automatic_runtime(monkeypatch, dhw=True)
    runtime.dhw.pending = {"target": 60, "issued": time.monotonic(),
                           "issued_wall": wall[0], "release": False, "ack_poll_min_s": 10}
    await runtime.tick()
    assert runtime.dhw.pending
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_full_ems_does_not_send_room_auto_while_battery_write_is_uncertain(monkeypatch):
    runtime, hass, wall = automatic_runtime(monkeypatch)
    runtime.battery_fleet.state.pending = {"id": "battery", "target_w": 500,
                                           "issued_wall": wall[0]}
    await runtime.tick()
    assert runtime.battery_fleet.busy
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_bad_room_source_cannot_be_hidden_by_dashboard_auto_choice(monkeypatch):
    runtime, hass, _ = automatic_runtime(monkeypatch)
    await runtime.smart_climate.async_set_override("climate.home", "auto")
    report(hass, "climate.home", current_temperature="not a temperature")
    await runtime.tick()
    assert not climate_calls(hass)
    assert "bruikbare temperatuurdata" in runtime.smart_climate.state.fault


@pytest.mark.asyncio
async def test_climate_fault_is_sticky_but_does_not_disable_another_reliable_cold_room(monkeypatch):
    runtime, hass, wall = automatic_runtime(monkeypatch)
    manager = runtime.smart_climate
    manager.settings["zone_entities"] = ["climate.home", "climate.salon"]
    report(hass, "climate.salon", "off", current_temperature=19.3, hvac_action="off")
    manager.command_faults["climate.home"] = "Eerdere opdracht niet bevestigd"
    manager.zone_holds["climate.home"] = wall[0] - 1
    await runtime.tick()
    assert climate_calls(hass) == [("climate", "set_hvac_mode", {
        "entity_id": "climate.salon", "hvac_mode": "auto"})]
    assert manager.command_faults["climate.home"]


@pytest.mark.asyncio
async def test_fixed_dashboard_off_survives_later_confirmation_pause_and_removal(monkeypatch):
    runtime, hass, wall = automatic_runtime(monkeypatch, temp=21, mode="auto")
    await dashboard(runtime, hass, mode="off")
    assert climate_calls(hass)[-1][2]["hvac_mode"] == "off"
    wall[0] += 11
    report(hass, "climate.home", "off", hvac_action="off")
    await runtime.tick()
    assert not runtime.smart_climate.busy
    assert runtime.smart_climate.state.expected_mode == {}
    before = list(climate_calls(hass))
    runtime.mode = "paused"
    await runtime.tick()
    await runtime.prepare_removal()
    await runtime.tick()
    assert climate_calls(hass) == before
    assert hass.states.get("climate.home").state == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize("choice,native", [("off", "auto"), ("auto", "off")])
async def test_dashboard_fixed_choices_execute_even_when_autonomous_zone_policy_is_opted_out(monkeypatch, choice, native):
    runtime, hass, _ = automatic_runtime(monkeypatch, mode=native)
    runtime.smart_climate.settings["automatic_zone_control"] = False
    await dashboard(runtime, hass, mode=choice)
    assert climate_calls(hass) == [("climate", "set_hvac_mode", {
        "entity_id": "climate.home", "hvac_mode": choice})]
    assert runtime.smart_climate.dashboard_overrides == {"climate.home": choice}
    assert hass.states.get("climate.home").state == choice


@pytest.mark.asyncio
@pytest.mark.parametrize("choice", ["auto", "automatic"])
async def test_failed_dashboard_persistence_preserves_existing_intent_and_temporary_native_hold(monkeypatch, choice):
    runtime, hass, wall = automatic_runtime(monkeypatch)
    manager = runtime.smart_climate
    manager.dashboard_overrides["climate.home"] = "off"
    manager.zone_holds["climate.home"] = wall[0] + 600
    manager.manual_off.add("climate.home")
    manager.cancelled_auto["climate.home"] = wall[0]
    await runtime.store.async_save(runtime._snapshot())
    saved = deepcopy(manager.snapshot())

    async def fail_save(_snapshot):
        raise OSError("test storage unavailable")

    runtime.store.async_save = fail_save
    with pytest.raises((HomeAssistantError, OSError)):
        await dashboard(runtime, hass, mode=choice)
    assert manager.snapshot() == saved
    assert runtime.store.data["smart_climate"] == saved
    assert not climate_calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("choice", ["auto", "automatic"])
async def test_failed_dashboard_save_does_not_undo_native_auto_arriving_during_storage_await(monkeypatch, choice):
    runtime, hass, wall = automatic_runtime(monkeypatch)
    manager = runtime.smart_climate
    manager.dashboard_overrides["climate.home"] = "off"
    manager.zone_holds["climate.home"] = wall[0] + 600
    manager.manual_off.add("climate.home")

    async def native_then_fail(_snapshot):
        report(hass, "climate.home", "auto", hvac_action="idle")
        manager._manual_mode("climate.home", "auto")
        raise OSError("test storage unavailable")

    runtime.store.async_save = native_then_fail
    with pytest.raises(HomeAssistantError):
        await dashboard(runtime, hass, mode=choice)
    assert manager.dashboard_overrides == {"climate.home": "off"}
    assert manager.zone_holds["climate.home"] == wall[0] + manager.settings["manual_hold_h"] * 3600
    assert manager.manual_off == set()
    assert manager.observed_modes["climate.home"] == "auto"
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_room_journal_is_durable_before_service_even_when_delayed_saves_do_not_run(monkeypatch):
    runtime, hass, _ = automatic_runtime(monkeypatch)
    runtime.store.async_delay_save = lambda *_args: None
    original = hass.services.async_call

    async def call(domain, action, data=None, **kwargs):
        if domain == "climate":
            saved = runtime.store.data["smart_climate"]
            assert saved["pending_commands"][data["entity_id"]]["mode"] == data["hvac_mode"]
            assert saved["expected_mode"][data["entity_id"]] == data["hvac_mode"]
            assert runtime.store.saves
        return await original(domain, action, data, **kwargs)

    hass.services.async_call = call
    await runtime.tick()
    assert len(climate_calls(hass)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["observe", "source_loss", "dhw_protection", "native_user_off"])
async def test_final_guard_after_durable_save_cancels_an_unissued_climate_call(monkeypatch, change):
    runtime, hass, _ = automatic_runtime(monkeypatch)
    original_save = runtime.store.async_save
    changed = False

    async def save(snapshot):
        nonlocal changed
        await original_save(snapshot)
        if snapshot["smart_climate"]["pending_commands"] and not changed:
            changed = True
            if change == "observe":
                runtime.mode = "observe"
            elif change == "source_loss":
                hass.states.set("climate.home", "unavailable")
            elif change == "dhw_protection":
                runtime.dhw.reading = SimpleNamespace(protected=True)
            else:
                runtime.smart_climate._manual_mode("climate.home", "off")

    runtime.store.async_save = save
    await runtime.tick()
    assert changed
    assert not climate_calls(hass)
    assert not runtime.smart_climate.pending_commands
    assert not runtime.store.data["smart_climate"]["pending_commands"]
    assert not runtime.smart_climate.command_faults
    if change != "native_user_off":
        assert not runtime.smart_climate.zone_command_counts
        assert not runtime.smart_climate.zone_command_walls


@pytest.mark.asyncio
async def test_failed_durable_journal_does_not_issue_a_room_command(monkeypatch):
    runtime, hass, _ = automatic_runtime(monkeypatch)

    async def fail_save(_snapshot):
        raise OSError("test storage unavailable")

    runtime.store.async_save = fail_save
    await runtime.tick()
    assert not climate_calls(hass)
    assert runtime.mode == "paused"
    assert not runtime.smart_climate.pending_commands
    assert not runtime.smart_climate.zone_command_counts


@pytest.mark.asyncio
async def test_live_removed_zone_loses_old_dashboard_intent_before_it_can_be_added_again(monkeypatch):
    runtime, hass, _ = automatic_runtime(monkeypatch)
    manager = runtime.smart_climate
    manager.settings["zone_entities"] = ["climate.home", "climate.salon"]
    runtime.entry.options["smart_climate"] = dict(manager.settings)
    runtime.live_options.applied = deepcopy(runtime.entry.options)
    manager.dashboard_overrides = {"climate.home": "off", "climate.salon": "auto"}
    manager.zone_holds = {"climate.home": time.time() + 600, "climate.salon": time.time() + 600}
    manager.zone_command_counts = {"climate.home": {"day": "today", "count": 2}}
    manager.state.profiles = {"climate.home": ThermalProfile(), "climate.salon": ThermalProfile()}
    retained = manager.state.profiles["climate.salon"]
    before = deepcopy(runtime.entry.options)
    after = deepcopy(before)
    after["smart_climate"]["zone_entities"] = ["climate.salon"]
    await runtime.live_options.submit(before, after)
    assert not runtime.entry.options.get(PENDING)
    assert manager.dashboard_overrides == {"climate.salon": "auto"}
    assert manager.zone_holds == {"climate.salon": manager.zone_holds["climate.salon"]}
    assert manager.zone_command_counts == {}
    assert manager.state.profiles == {"climate.salon": retained}
    before = deepcopy(runtime.entry.options)
    after = deepcopy(before)
    after["smart_climate"]["zone_entities"] = ["climate.home", "climate.salon"]
    await runtime.live_options.submit(before, after)
    assert "climate.home" not in manager.dashboard_overrides
    assert "climate.home" not in manager.zone_holds
    assert "climate.home" not in manager.state.profiles
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("physical_reference", [False, True])
async def test_live_weather_binding_change_invalidates_same_models_as_dashboard_edit(monkeypatch, physical_reference):
    runtime, hass, _ = automatic_runtime(monkeypatch)
    manager = runtime.smart_climate
    manager.settings["outside_temp_entity"] = "sensor.outdoor" if physical_reference else ""
    runtime.entry.options["smart_climate"] = dict(manager.settings)
    runtime.live_options.applied = deepcopy(runtime.entry.options)
    profile = manager.state.profile("climate.home")
    profile.samples = 633
    manager.state.forecast = [{"temperature": 5}]
    manager.state.last_forecast_wall = time.time()
    manager.state.weather_bias.errors["12"] = [1]
    hass.states.set("weather.new", "cloudy", {"temperature": 6, "temperature_unit": "°C"})
    before = deepcopy(runtime.entry.options)
    after = deepcopy(before)
    after["smart_climate"]["weather_entity"] = "weather.new"
    await runtime.live_options.submit(before, after)
    assert manager.settings["weather_entity"] == "weather.new"
    assert manager.state.forecast == [] and manager.state.last_forecast_wall == 0
    assert not any(manager.state.weather_bias.errors.values())
    assert (manager.state.profiles.get("climate.home") is profile) is physical_reference
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_live_outdoor_reference_change_restarts_learning_without_touching_dashboard_intent(monkeypatch):
    runtime, hass, _ = automatic_runtime(monkeypatch)
    manager = runtime.smart_climate
    manager.state.profile("climate.home").samples = 633
    manager.state.weather_bias.errors["12"] = [1]
    manager.dashboard_overrides["climate.home"] = "off"
    manager.last_outside = 5
    hass.states.set("sensor.outdoor_new", 6, {"unit_of_measurement": "°C"})
    before = deepcopy(runtime.entry.options)
    after = deepcopy(before)
    after["smart_climate"]["outside_temp_entity"] = "sensor.outdoor_new"
    await runtime.live_options.submit(before, after)
    assert manager.state.profiles == {}
    assert not any(manager.state.weather_bias.errors.values())
    assert manager.last_outside is None
    assert manager.dashboard_overrides == {"climate.home": "off"}
    assert not hass.services.calls
