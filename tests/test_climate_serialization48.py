"""Runtime serialization and listener lifecycle for unconfirmed climate modes."""
import asyncio
from copy import deepcopy
import time
from types import SimpleNamespace

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot import thermal_runtime
from custom_components.solar_pilot.thermal_climate import SMART_CLIMATE_DEFAULTS
from custom_components.solar_pilot.thermal_runtime import SmartClimateManager
from test_dhw_runtime import setup as setup_dhw
from test_dishwasher import setup as setup_dishwasher
from test_dishwasher_app31 import configured as setup_app, ready as app_ready, stamp
from test_thermal_runtime import ClimateServices
from test_thermal_runtime_beta48 import clock, user_mode_event


class CombinedServices(ClimateServices):
    async def async_call(self, domain, action, data=None, blocking=False, **kwargs):
        if domain == "water_heater" and action == "set_temperature":
            self.calls.append((domain, action, data))
            obj = self.states.get(data["entity_id"])
            self.states.set(data["entity_id"], obj.state, {
                **obj.attributes, "temperature": data["temperature"],
            })
            return None
        return await super().async_call(domain, action, data, blocking, **kwargs)


def attach_climate(runtime, hass, monkeypatch):
    hass.services = CombinedServices(hass.states)
    hass.config = SimpleNamespace(time_zone="Europe/Brussels",
                                 units=SimpleNamespace(temperature_unit="°C"))
    attrs = {"current_temperature": 21, "temperature": 21, "temperature_unit": "°C",
             "hvac_action": "idle", "hvac_modes": ["off", "auto"]}
    hass.states.set("climate.home", "off", attrs)
    hass.states.set("climate.salon", "off", attrs)
    hass.states.set("sensor.outdoor", 21, {"unit_of_measurement": "°C"})
    hass.states.set("sensor.native_program", "heat_cool", {})
    runtime.entry.options["smart_climate"] = {
        **SMART_CLIMATE_DEFAULTS, "enabled": True, "control_enabled": False,
        "zone_entities": ["climate.home"], "outside_temp_entity": "sensor.outdoor",
        "operation_mode_entity": "sensor.native_program",
    }
    runtime.smart_climate = SmartClimateManager(runtime)
    runtime.settings["settle_s"] = 0
    return clock(monkeypatch, hass)


async def request_auto(runtime):
    assert await runtime.smart_climate._send_mode("auto", runtime.smart_climate._zones())
    assert runtime.smart_climate.busy
    saved = runtime.store.data["smart_climate"]
    assert saved["pending_commands"]["climate.home"]["mode"] == "auto"


def fresh_grid(hass, watts=-5000):
    hass.states.set("sensor.grid", watts, {"unit_of_measurement": "W"})


@pytest.mark.asyncio
async def test_runtime_defers_boiler_until_later_climate_report_then_resumes(monkeypatch):
    runtime, hass = setup_dhw()
    wall = attach_climate(runtime, hass, monkeypatch)
    await request_auto(runtime)
    fresh_grid(hass)

    await runtime.tick()
    wall[0] += 11
    fresh_grid(hass)
    await runtime.tick()

    # Waiting alone does not confirm the optimistic report or permit DHW.
    assert runtime.smart_climate.busy
    assert [call[0] for call in hass.services.calls] == ["climate"]

    obj = hass.states.get("climate.home")
    hass.states.set("climate.home", "auto", obj.attributes)
    await runtime.tick()
    assert not runtime.smart_climate.busy
    await runtime.tick()

    assert [call[0] for call in hass.services.calls] == ["climate", "water_heater"]
    assert hass.services.calls[-1][2]["temperature"] == 60


@pytest.mark.asyncio
async def test_pending_climate_blocks_concurrent_ordinary_starts_and_survives_restore(monkeypatch):
    runtime, hass = setup_dhw(config={"enabled": False})
    wall = attach_climate(runtime, hass, monkeypatch)
    runtime.device_modes["a"] = "auto"
    await request_auto(runtime)
    saved = deepcopy(runtime.smart_climate.snapshot())
    runtime.smart_climate = SmartClimateManager(runtime)
    runtime.smart_climate.restore(saved)
    fresh_grid(hass)

    await asyncio.gather(runtime.tick(), runtime.tick(), runtime.tick())

    assert runtime.smart_climate.busy
    assert runtime.pending is None
    assert hass.states.get("switch.load").state == "off"
    assert [call[0] for call in hass.services.calls] == ["climate"]

    wall[0] += 11
    obj = hass.states.get("climate.home")
    hass.states.set("climate.home", "auto", obj.attributes)
    fresh_grid(hass)
    await runtime.tick()

    assert not runtime.smart_climate.busy
    assert runtime.pending and runtime.pending["id"] == "a"
    assert [call[0] for call in hass.services.calls] == ["climate", "switch"]


@pytest.mark.asyncio
async def test_climate_pending_does_not_block_safe_flexible_consumer_reduction(monkeypatch):
    runtime, hass = setup_dhw(config={"enabled": False})
    attach_climate(runtime, hass, monkeypatch)
    runtime.device_modes["a"] = "auto"
    hass.states.set("switch.load", "on")
    state = runtime.states["a"]
    state.owned = state.on = True
    state.target_w = 1000
    state.last_on = time.monotonic()
    await request_auto(runtime)
    fresh_grid(hass, 5000)

    await runtime.tick()

    assert runtime.smart_climate.busy
    assert hass.services.calls[-1] == ("switch", "turn_off", {"entity_id": "switch.load"})


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["solar", "paused"])
async def test_pending_climate_never_stops_or_restarts_active_aeg_cycle(monkeypatch, mode):
    runtime, hass, _ = setup_dishwasher()
    wall = attach_climate(runtime, hass, monkeypatch)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    runtime.smart_climate.state.expected_mode["climate.home"] = "off"
    await runtime.arm_dishwasher("a")
    wall[0] += 1
    hass.states.set("sensor.dw_phase", "Washing")
    await runtime.tick()
    assert runtime.states["a"].owned and runtime.pending is None
    await request_auto(runtime)
    runtime.mode = mode
    fresh_grid(hass, 5000)

    await runtime.tick()
    await runtime.tick()

    assert runtime.smart_climate.busy
    assert runtime.states["a"].owned
    assert [call[:2] for call in hass.services.calls] == [
        ("button", "press"), ("climate", "set_hvac_mode"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["unavailable", "restored", "stale"])
async def test_lost_climate_report_times_out_without_permanent_global_block(monkeypatch, missing):
    runtime, hass = setup_dhw(config={"enabled": False})
    wall = attach_climate(runtime, hass, monkeypatch)
    runtime.device_modes["a"] = "auto"
    await request_auto(runtime)
    wall[0] += 181
    obj = hass.states.get("climate.home")
    if missing == "unavailable":
        hass.states.set("climate.home", "unavailable", obj.attributes)
    elif missing == "restored":
        hass.states.set("climate.home", "auto", {**obj.attributes, "restored": True})
    else:
        hass.states.set("climate.home", "auto", obj.attributes, age=1801)
    fresh_grid(hass)

    await runtime.tick()

    assert not runtime.smart_climate.busy
    assert "climate.home" in runtime.smart_climate.command_faults
    assert "climate.home" not in runtime.smart_climate.state.expected_mode
    assert runtime.store.data["smart_climate"]["command_faults"]
    writes = [call for call in hass.services.calls if call[0] != "persistent_notification"]
    assert [call[0] for call in writes] == ["climate", "switch"]
    notices = [call for call in hass.services.calls if call[0] == "persistent_notification"]
    assert len(notices) == 1 and notices[0][1] == "create"
    assert notices[0][2]["notification_id"] == "solar_pilot_test_action_required"
    assert "Ruimteklimaat" in notices[0][2]["message"]


@pytest.mark.asyncio
async def test_explicit_user_off_cancels_pending_and_persists_during_runtime_guard(monkeypatch):
    runtime, hass = setup_dhw(config={"enabled": False})
    attach_climate(runtime, hass, monkeypatch)
    await request_auto(runtime)
    user_mode_event(runtime.smart_climate, "climate.home", "off")
    obj = hass.states.get("climate.home")
    hass.states.set("climate.home", "off", {**obj.attributes, "current_temperature": 23})
    saved = deepcopy(runtime.smart_climate.snapshot())
    runtime.smart_climate = SmartClimateManager(runtime)
    runtime.smart_climate.restore(saved)
    runtime.smart_climate.settings["control_enabled"] = True

    await runtime.tick()

    assert not runtime.smart_climate.busy
    assert runtime.smart_climate.manual_off == {"climate.home"}
    assert not runtime.smart_climate.state.expected_mode
    assert hass.states.get("climate.home").state == "off"
    assert len(hass.services.calls) == 1


@pytest.mark.asyncio
async def test_zone_update_rebinds_listeners_and_close_removes_current_subscriptions(monkeypatch):
    runtime, hass = setup_dhw(config={"enabled": False})
    attach_climate(runtime, hass, monkeypatch)
    active_states, active_services = [], []

    def states_listener(_hass, ids, handler):
        item = (list(ids), handler)
        active_states.append(item)
        return lambda: active_states.remove(item)

    def service_listener(event, handler):
        item = (event, handler)
        active_services.append(item)
        return lambda: active_services.remove(item)

    monkeypatch.setattr(thermal_runtime, "async_track_state_change_event", states_listener)
    hass.bus = SimpleNamespace(async_listen=service_listener)
    manager = runtime.smart_climate
    hass.states.set("weather.home", "partlycloudy", {"temperature": 21, "temperature_unit": "°C"})
    manager.settings["weather_entity"] = "weather.home"
    manager.start()
    assert len(active_states) == len(active_services) == 1
    assert active_states[0][0] == ["climate.home"]

    await manager.async_set_setting("zone_entities", ["climate.salon"])

    assert len(active_states) == len(active_services) == 1
    assert active_states[0][0] == ["climate.salon"]
    user_mode_event(manager, "climate.home", "off")
    assert not manager.manual_off
    user_mode_event(manager, "climate.salon", "off")
    assert manager.manual_off == {"climate.salon"}
    manager.close()
    manager.close()
    assert not active_states and not active_services


@pytest.mark.asyncio
@pytest.mark.parametrize("inactive", ["disabled", "unconfigured"])
@pytest.mark.parametrize("lost_source", [False, True])
async def test_inactive_module_resolves_pending_timeout_without_learning_or_global_block(
        monkeypatch, inactive, lost_source):
    runtime, hass = setup_dhw(config={"enabled": False})
    wall = attach_climate(runtime, hass, monkeypatch)
    runtime.device_modes["a"] = "auto"
    await request_auto(runtime)
    manager = runtime.smart_climate
    if inactive == "disabled":
        # Simulate a legacy/external saved setting; the API now rejects disabling a pending command.
        manager.settings["enabled"] = False
    else:
        # A legacy/options replacement may remove the binding while the saved
        # command still needs reconciliation; it must not become a global lock.
        manager.settings["zone_entities"] = []
    if lost_source:
        hass.states.set("climate.home", "unavailable")
    else:
        # Its optimistic command-side state remains too early to confirm.
        assert hass.states.get("climate.home").state == "auto"
    before_model = (manager.state.last_sample_wall, manager.state.last_decision_wall)
    wall[0] += 181
    fresh_grid(hass)

    await runtime.tick()

    assert not manager.busy
    assert "climate.home" in manager.command_faults
    assert all(profile.samples == 0 and profile.last is None for profile in manager.state.profiles.values())
    assert (manager.state.last_sample_wall, manager.state.last_decision_wall) == before_model
    writes = [call for call in hass.services.calls if call[0] != "persistent_notification"]
    assert [call[0] for call in writes] == ["climate", "switch"]
    notices = [call for call in hass.services.calls if call[0] == "persistent_notification"]
    assert len(notices) == 1 and notices[0][1] == "create"
    assert notices[0][2]["notification_id"] == "solar_pilot_test_action_required"
    assert "Ruimteklimaat" in notices[0][2]["message"]


@pytest.mark.asyncio
async def test_disabled_module_confirms_fresh_pending_report_without_learning_or_command(monkeypatch):
    runtime, hass = setup_dhw(config={"enabled": False})
    wall = attach_climate(runtime, hass, monkeypatch)
    await request_auto(runtime)
    manager = runtime.smart_climate
    # Legacy/external saved settings must still reconcile a pending command.
    manager.settings["enabled"] = False
    before_model = (manager.state.last_sample_wall, manager.state.last_decision_wall)
    wall[0] += 11
    obj = hass.states.get("climate.home")
    hass.states.set("climate.home", "auto", obj.attributes)

    await runtime.tick()

    assert not manager.busy and not manager.command_faults
    assert all(profile.samples == 0 and profile.last is None for profile in manager.state.profiles.values())
    assert (manager.state.last_sample_wall, manager.state.last_decision_wall) == before_model
    assert [call[0] for call in hass.services.calls] == ["climate"]


@pytest.mark.asyncio
@pytest.mark.parametrize("ownership", ["owned_off", "pending_off", "pending_auto"])
async def test_direct_zone_rebinding_preserves_journal_until_confirmed_auto_release(monkeypatch, ownership):
    runtime, hass = setup_dhw(config={"enabled": False})
    wall = attach_climate(runtime, hass, monkeypatch)
    manager = runtime.smart_climate
    hass.states.set("weather.home", "partlycloudy", {"temperature": 21, "temperature_unit": "°C"})
    manager.settings["weather_entity"] = "weather.home"
    if ownership == "owned_off":
        manager.state.expected_mode["climate.home"] = "off"
    elif ownership == "pending_off":
        obj = hass.states.get("climate.home")
        hass.states.set("climate.home", "auto", obj.attributes)
        assert await manager._send_mode("off", manager._zones())
    else:
        await request_auto(runtime)
    before_settings = deepcopy(manager.settings)
    before_options = deepcopy(runtime.entry.options)
    before_journal = deepcopy(manager.snapshot())

    with pytest.raises(HomeAssistantError, match="nog in beheer"):
        await manager.async_set_setting("zone_entities", ["climate.salon"])

    assert manager.settings == before_settings
    assert runtime.entry.options == before_options
    assert manager.snapshot() == before_journal
    if manager.pending_commands:
        mode = manager.pending_commands["climate.home"]["mode"]
        wall[0] += 11
        obj = hass.states.get("climate.home")
        hass.states.set("climate.home", mode, obj.attributes)
        await runtime.tick()
    if manager.state.expected_mode.get("climate.home") == "off":
        await request_auto(runtime)
        wall[0] += 11
        obj = hass.states.get("climate.home")
        hass.states.set("climate.home", "auto", obj.attributes)
        await runtime.tick()
    assert not manager.busy and not manager.removal_blocked()

    await manager.async_set_setting("zone_entities", ["climate.salon"])

    assert manager.settings["zone_entities"] == ["climate.salon"]
    assert not manager.state.expected_mode and not manager.pending_commands


@pytest.mark.asyncio
async def test_due_aeg_grid_deadline_waits_for_pending_climate_confirmation(monkeypatch):
    runtime, hass, config, app_wall = setup_app(monkeypatch, "2026-09-29T12:59")
    wall = attach_climate(runtime, hass, monkeypatch)
    app_ready(runtime, hass, config, app_wall)
    fresh_grid(hass, 500)
    await request_auto(runtime)
    app_wall[0] = wall[0] = stamp("2026-09-29T13:00")
    for entity, obj in list(hass.states.data.items()):
        if entity != "climate.home":
            hass.states.set(entity, obj.state, obj.attributes)

    await runtime.tick()

    assert runtime.smart_climate.busy
    assert runtime.pending is None
    assert not any(call[0] == "button" for call in hass.services.calls)
    obj = hass.states.get("climate.home")
    hass.states.set("climate.home", "auto", obj.attributes)

    await runtime.tick()

    assert not runtime.smart_climate.busy
    assert runtime.pending and runtime.pending["id"] == "a"
    assert "deadline" in runtime.pending["reason"]
    assert len([call for call in hass.services.calls if call[0] == "button"]) == 1
