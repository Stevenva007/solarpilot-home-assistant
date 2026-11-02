"""Production battery form + live transaction with explicit HA doubles.

Core's options manager/storage is checked separately by
tools/check_real_ha_battery_options115.py. These tests issue no device commands.
"""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.battery_profiles import MARSTEK_PROFILE, normalize_battery_config
from custom_components.solar_pilot.runtime import SolarRuntime
from homeassistant.exceptions import HomeAssistantError
from test_live_config34 import flow_class
from test_marstek_config_ui113 import flow as marstek_flow, inputs
from test_runtime import build


def monitor(identity="fixture_monitor", **changes):
    return normalize_battery_config({"id": identity, "profile": MARSTEK_PROFILE,
        "name": "Saved monitor", "power_entity": "sensor.fixture_ac", "soc_entity": "sensor.fixture_soc",
        "power_sign": "discharge_positive", "ac_power_confirmed": True, "phase_hint": "l2", **changes})


@pytest.fixture
def configured_flow(marstek_flow, flow_class, monkeypatch):
    # Keep actual SolarPilotOptions methods and actual LiveOptionsMixin methods;
    # only HA schema rendering/transport is doubled by the existing fixtures.
    options_class = type(marstek_flow).__bases__[0]

    class Flow(options_class, flow_class):
        def async_show_menu(self, **kwargs):
            return kwargs

    from homeassistant.helpers import entity_registry as er
    monkeypatch.setattr(er, "async_get", lambda hass: type("Registry", (), {
        "async_get": staticmethod(lambda entity: None)})())

    def make(batteries=()):
        old_runtime, hass = build()
        entry = old_runtime.entry
        entry.options["batteries"] = deepcopy(list(batteries))
        hass.states.set("sensor.fixture_ac", 200, {"unit_of_measurement": "W"})
        hass.states.set("sensor.fixture_soc", 67, {"unit_of_measurement": "%"})
        runtime = SolarRuntime(hass, entry)
        entry.runtime_data = runtime

        def reopen():
            result = Flow()
            result.hass, result.config_entry = hass, entry
            return result

        return runtime, hass, reopen

    return make


@pytest.mark.asyncio
async def test_single_saved_monitor_opens_with_values_and_updates_same_id(configured_flow):
    saved = monitor()
    runtime, hass, reopen = configured_flow([saved])
    flow = reopen()
    before = deepcopy(runtime.entry.options)

    form = await flow.async_step_battery_marstek()
    assert form["step_id"] == "battery_marstek"
    assert flow._battery == saved and flow._battery is not runtime.entry.options["batteries"][0]
    assert flow._battery_editing == saved["id"]
    result = await flow.async_step_battery_marstek(inputs(name="Updated monitor", soc_entity="sensor.fixture_soc", phase_hint="l1"))
    assert result["step_id"] == "apply_changes"
    assert runtime.entry.options == before
    assert runtime.battery_fleet.configs[saved["id"]] == saved
    declined = await flow.async_step_apply_changes({"confirm": False})
    assert declined["errors"]["base"] == "live_change" and runtime.entry.options == before

    final = await flow.async_step_apply_changes({"confirm": True})
    assert final["type"] == "create_entry"
    rows = runtime.entry.options["batteries"]
    assert len(rows) == 1 and rows[0]["id"] == saved["id"]
    assert rows[0]["name"] == "Updated monitor" and rows[0]["phase_hint"] == "l1"
    assert runtime.battery_fleet.configs[saved["id"]] == rows[0]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_final_save_reopens_and_reloads_without_losing_values_or_adding_row(configured_flow):
    runtime, hass, reopen = configured_flow()
    flow = reopen()
    menu = await flow.async_step_battery()
    assert "battery_marstek_add" not in menu["menu_options"]
    await flow.async_step_battery_marstek()
    identity = flow._battery["id"]
    pending = await flow.async_step_battery_marstek(inputs(soc_entity="sensor.fixture_soc", phase_hint="l3"))
    assert pending["step_id"] == "apply_changes" and not runtime.entry.options["batteries"]
    await flow.async_step_apply_changes({"confirm": True})
    saved = deepcopy(runtime.entry.options["batteries"])

    reopened = reopen()
    await reopened.async_step_battery_marstek()
    assert reopened._battery == saved[0] and reopened._battery["ac_power_confirmed"] is True
    assert reopened._battery["id"] == identity
    assert "battery_marstek_add" in (await reopened.async_step_battery())["menu_options"]
    restored = SolarRuntime(hass, runtime.entry)
    assert restored.battery_fleet.configs == {identity: saved[0]}
    assert runtime.entry.options["batteries"] == saved and len(saved) == 1
    assert saved[0]["control_kind"] == "read_only" and not saved[0]["control_enabled"]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_opening_unconfirmed_saved_monitor_does_not_confirm_or_replace_it(configured_flow):
    saved = monitor(ac_power_confirmed=False, power_entity="", soc_entity="", power_sign="")
    runtime, hass, reopen = configured_flow([saved])
    flow = reopen()
    await flow.async_step_battery_marstek()
    assert flow._battery == saved and flow._battery["ac_power_confirmed"] is False
    assert flow._battery["id"] == saved["id"]
    assert runtime.entry.options["batteries"] == [saved] and not hass.services.calls


@pytest.mark.asyncio
async def test_another_monitor_requires_explicit_add_action_and_keeps_existing(configured_flow):
    saved = monitor()
    runtime, hass, reopen = configured_flow([saved])
    flow = reopen()
    await flow.async_step_battery_marstek()
    assert flow._battery["id"] == saved["id"]
    await flow.async_step_battery_marstek_add()
    assert flow._battery["id"] != saved["id"] and not flow._battery["power_sign"]
    identity = flow._battery["id"]
    hass.states.set("sensor.fixture_second_ac", -100, {"unit_of_measurement": "W"})
    await flow.async_step_battery_marstek(inputs(name="Second monitor", power_entity="sensor.fixture_second_ac"))
    assert runtime.entry.options["batteries"] == [saved]
    await flow.async_step_apply_changes({"confirm": True})
    rows = {row["id"]: row for row in runtime.entry.options["batteries"]}
    assert set(rows) == {saved["id"], identity} and rows[saved["id"]] == saved
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_multiple_monitors_require_explicit_choice_and_exclude_generic_batteries(configured_flow):
    first, second = monitor(), monitor("fixture_second", name="Second monitor", power_entity="sensor.fixture_second_ac")
    generic = {"id": "generic_fixture", "name": "Generic battery", "profile": "generic"}
    runtime, hass, reopen = configured_flow([first, second, generic])
    before = deepcopy(runtime.entry.options)
    flow = reopen()
    result = await flow.async_step_battery_marstek()
    assert result["step_id"] == "battery_marstek_select"
    assert {item["value"] for item in result["data_schema"]["battery_id"]["options"]} == {first["id"], second["id"]}
    invalid = await flow.async_step_battery_marstek_select({"battery_id": generic["id"]})
    assert invalid["errors"] == {"battery_id": "required"}
    assert not flow._battery
    form = await flow.async_step_battery_marstek_select({"battery_id": second["id"]})
    assert form["step_id"] == "battery_marstek" and flow._battery == second
    assert runtime.entry.options == before and not hass.services.calls


@pytest.mark.asyncio
async def test_validation_retry_keeps_draft_and_does_not_persist_until_final_confirmation(configured_flow):
    runtime, hass, reopen = configured_flow([monitor()])
    before = deepcopy(runtime.entry.options)
    flow = reopen()
    await flow.async_step_battery_marstek()
    invalid = await flow.async_step_battery_marstek(inputs(name="Draft name", power_sign="", soc_entity="sensor.fixture_soc"))
    assert invalid["errors"] == {"power_sign": "required"}
    assert flow._battery["name"] == "Draft name" and flow._battery["soc_entity"] == "sensor.fixture_soc"
    assert runtime.entry.options == before
    await flow.async_step_battery_marstek(inputs(name="Draft name", soc_entity="sensor.fixture_soc"))
    assert runtime.entry.options == before
    await flow.async_step_apply_changes({"confirm": True})
    assert runtime.entry.options["batteries"][0]["name"] == "Draft name"
    assert len(runtime.entry.options["batteries"]) == 1 and not hass.services.calls


@pytest.mark.asyncio
async def test_battery_confirmation_preserves_concurrent_unrelated_change(configured_flow):
    runtime, hass, reopen = configured_flow([monitor()])
    flow = reopen()
    await flow.async_step_battery_marstek()
    await flow.async_step_battery_marstek(inputs(name="Updated monitor"))
    runtime.entry.options["devices"][0]["name"] = "Concurrent device name"
    await flow.async_step_apply_changes({"confirm": True})
    assert runtime.entry.options["devices"][0]["name"] == "Concurrent device name"
    assert runtime.entry.options["batteries"][0]["name"] == "Updated monitor" and not hass.services.calls


@pytest.mark.asyncio
async def test_persistence_failure_keeps_saved_monitor_and_allows_same_draft_retry(configured_flow, monkeypatch):
    runtime, hass, reopen = configured_flow([monitor()])
    flow = reopen()
    before = deepcopy(runtime.entry.options)
    await flow.async_step_battery_marstek()
    await flow.async_step_battery_marstek(inputs(name="Retry monitor"))
    persist = runtime.live_options._persist

    def fail(options):
        raise HomeAssistantError("Synthetic storage failure")

    monkeypatch.setattr(runtime.live_options, "_persist", fail)
    failed = await flow.async_step_apply_changes({"confirm": True})
    assert failed["errors"]["base"] == "live_change" and runtime.entry.options == before
    assert runtime.battery_fleet.configs["fixture_monitor"]["name"] == "Saved monitor"
    monkeypatch.setattr(runtime.live_options, "_persist", persist)
    saved = await flow.async_step_apply_changes({"confirm": True})
    assert saved["type"] == "create_entry"
    assert runtime.entry.options["batteries"][0]["name"] == "Retry monitor"
    assert len(runtime.entry.options["batteries"]) == 1 and not hass.services.calls
