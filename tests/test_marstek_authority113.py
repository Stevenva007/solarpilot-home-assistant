"""An explicitly monitored battery cannot gain a different SolarPilot writer.

Fictitious HA registry/service doubles only; no battery or network access.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot.battery_runtime import BatteryFleetManager
from test_battery_runtime import setup_battery
from test_runtime import build


def monitor_profile(**changes):
    return {
        "id": "monitor",
        "name": "Test monitored battery",
        "profile": "marstek_venus_e3",
        "enabled": True,
        "soc_entity": "sensor.monitor_soc",
        "power_entity": "sensor.monitor_ac",
        "power_sign": "discharge_positive",
        "ac_power_confirmed": True,
        **changes,
    }


def install_registry(monkeypatch):
    rows = {}

    def register(entity, device="monitored-device", platform="marstek"):
        rows[entity] = SimpleNamespace(
            entity_id=entity, device_id=device, platform=platform,
            config_entry_id="provider-entry", unique_id=f"test_{entity}",
        )

    for entity in (
        "sensor.monitor_soc", "sensor.monitor_ac", "switch.monitor_enable",
        "number.monitor_setpoint", "button.monitor_action",
    ):
        register(entity)
    register("switch.unrelated", "different-device")
    monkeypatch.setattr(er, "async_get", lambda _hass:
                        SimpleNamespace(async_get=rows.get, entities=rows))
    return rows, register


def monitored_runtime(monkeypatch, *, location="both", enabled=True):
    runtime, hass = build()
    profile = monitor_profile(enabled=enabled)
    if location in {"raw", "both"}:
        runtime.entry.options["batteries"] = [deepcopy(profile)]
    if location in {"runtime", "both"}:
        runtime.battery_fleet.configs[profile["id"]] = deepcopy(profile)
    rows, register = install_registry(monkeypatch)
    return runtime, hass, rows, register


@pytest.mark.asyncio
@pytest.mark.parametrize("entity,service,extra", [
    ("switch.monitor_enable", "turn_on", None),
    ("switch.monitor_enable", "turn_off", None),
    ("number.monitor_setpoint", "set_value", {"value": 500}),
    ("number.monitor_setpoint", "set_value", {"value": 0}),
    ("button.monitor_action", "press", None),
])
async def test_generic_writer_cannot_operate_monitored_battery_siblings(
    monkeypatch, entity, service, extra,
):
    runtime, hass, _rows, _register = monitored_runtime(monkeypatch)
    with pytest.raises(HomeAssistantError):
        await runtime._call(entity, service, extra)
    assert hass.services.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("location", ["raw", "runtime", "both"])
@pytest.mark.parametrize("enabled", [True, False])
async def test_monitor_protection_survives_partial_live_update_and_disabled_profile(
    monkeypatch, location, enabled,
):
    runtime, hass, _rows, _register = monitored_runtime(
        monkeypatch, location=location, enabled=enabled,
    )
    with pytest.raises(HomeAssistantError):
        await runtime._call("number.monitor_setpoint", "set_value", {"value": 0})
    assert hass.services.calls == []


@pytest.mark.asyncio
async def test_unrelated_device_with_same_provider_remains_controllable(monkeypatch):
    runtime, hass, _rows, _register = monitored_runtime(monkeypatch)
    await runtime._call("switch.unrelated", "turn_on")
    assert hass.services.calls == [
        ("switch", "turn_on", {"entity_id": "switch.unrelated"}),
    ]


@pytest.mark.asyncio
async def test_registry_rebinding_invalidates_earlier_generic_authority(monkeypatch):
    runtime, hass, _rows, register = monitored_runtime(monkeypatch)
    runtime.command_authority.assert_allowed("switch", "turn_on", "switch.unrelated")
    register("switch.unrelated")
    with pytest.raises(HomeAssistantError):
        await runtime._call("switch.unrelated", "turn_on")
    assert hass.services.calls == []


@pytest.mark.asyncio
async def test_static_nested_script_cannot_proxy_monitored_battery(monkeypatch):
    runtime, hass, _rows, _register = monitored_runtime(monkeypatch)
    sequences = {
        "script.outer": [{"action": "script.inner"}],
        "script.inner": [{
            "action": "homeassistant.turn_off",
            "target": {"entity_id": "switch.monitor_enable"},
        }],
    }
    hass.data["script"] = SimpleNamespace(get_entity=lambda entity:
        SimpleNamespace(script=SimpleNamespace(sequence=sequences[entity]))
        if entity in sequences else None)
    with pytest.raises(HomeAssistantError):
        await runtime._call("script.outer", "turn_on")
    assert hass.services.calls == []


def test_dishwasher_start_exception_does_not_own_battery_sibling(monkeypatch):
    runtime, _hass, _rows, _register = monitored_runtime(monkeypatch)
    runtime.configs["a"].update(kind="dishwasher", start_button="button.monitor_action")
    with pytest.raises(HomeAssistantError):
        runtime.command_authority.assert_dishwasher_profile("a", "button.monitor_action")


@pytest.mark.asyncio
@pytest.mark.parametrize("watts", [-500, 0, 500])
async def test_generic_battery_profile_cannot_write_same_monitored_device(
    monkeypatch, watts,
):
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    # Disabled monitoring still means no actuator authority over that device.
    runtime.entry.options["batteries"].append(monitor_profile(enabled=False))
    runtime.battery_fleet = BatteryFleetManager(runtime)
    _rows, register = install_registry(monkeypatch)
    register("number.bat_setpoint")
    assert not await runtime.battery_fleet._send("bat1", watts)
    assert hass.services.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("watts", [-500, 0, 500])
async def test_registry_change_during_saved_intent_blocks_generic_battery_dispatch(
    monkeypatch, watts,
):
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    runtime.entry.options["batteries"].append(monitor_profile(enabled=False))
    runtime.battery_fleet = BatteryFleetManager(runtime)
    _rows, register = install_registry(monkeypatch)
    register("number.bat_setpoint", "different-device")
    original_save = runtime.store.async_save
    saves = []

    async def save_then_rebind(data):
        saves.append(deepcopy(data))
        await original_save(data)
        register("number.bat_setpoint")

    runtime.store.async_save = save_then_rebind
    # The existing dispatcher returns True after handling a saved-intent
    # failure as well; physical service calls are the authority evidence.
    await runtime.battery_fleet._send("bat1", watts)
    assert saves, "Exercise the actual post-persistence authority boundary"
    assert hass.services.calls == []
