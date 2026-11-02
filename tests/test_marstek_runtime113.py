"""Fictional Marstek measurements cannot grant physical battery authority."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.battery_profiles import (
    MARSTEK_PROFILE, battery_source_error, normalize_battery_config,
)
from custom_components.solar_pilot.battery_runtime import BatteryFleetManager
from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from custom_components.solar_pilot.runtime import SolarRuntime
from test_runtime import build
from test_battery_runtime import setup_battery


def marstek(*, power=0, soc=50, sign="discharge_positive", confirmed=True):
    runtime, hass = build(settings={"pv_entity": "sensor.fictional_pv"})
    hass.states.set("sensor.fictional_pv", 3000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fictional_storage_ac", power, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fictional_storage_soc", soc, {"unit_of_measurement": "%"})
    # Deliberately retain a generic writer's flags and references in the raw
    # input. The product capability must overrule all of them, including zero.
    profile = {"id": "storage", "profile": MARSTEK_PROFILE,
        "name": "Fictieve Venus E 3.0", "power_entity": "sensor.fictional_storage_ac",
        "soc_entity": "sensor.fictional_storage_soc", "power_sign": sign,
        "ac_power_confirmed": confirmed, "control_kind": "signed_number",
        "control_enabled": True, "exclusive_control_confirmed": True,
        "number_entity": "number.fictional_storage", "number_sign": "charge_positive",
        "charge_script": "script.fictional_charge", "discharge_script": "script.fictional_discharge",
        "idle_script": "script.fictional_idle"}
    runtime.entry.options.update(batteries=[profile], battery_fleet={"enabled": True, "control_enabled": True})
    runtime.battery_fleet = BatteryFleetManager(runtime)
    return runtime, hass


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["signed_number", "scripts"])
@pytest.mark.parametrize("target", [-1000, 0, 1000])
async def test_monitor_refuses_every_target_even_with_tampered_runtime_flags(kind, target):
    runtime, hass = marstek()
    manager = runtime.battery_fleet
    manager.configs["storage"].update(control_kind=kind, control_enabled=True,
        exclusive_control_confirmed=True, number_entity="number.fictional_storage",
        charge_script="script.fictional_charge", discharge_script="script.fictional_discharge",
        idle_script="script.fictional_idle")
    assert not await manager._send("storage", target)
    assert manager.state.pending is None and not runtime.store.saves
    assert not manager.read()[0].controllable
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_monitor_tick_pause_removal_and_reload_never_write_or_offer_targets():
    runtime, hass = marstek(power=800)
    manager = runtime.battery_fleet
    raw = deepcopy(runtime.entry.options["batteries"][0])
    assert manager.configs["storage"]["capacity_kwh"] == 5.12
    for key in ("number_entity", "number_sign", "charge_script", "discharge_script", "idle_script"):
        assert key not in manager.configs["storage"]
    assert not await manager.tick(grid_w=-2000, allow_command=True)
    assert manager.recommendation.allocations is None
    assert not await manager.release_owned_targets()
    assert not manager.removal_blocked()
    assert not await manager.prepare_for_removal()
    restarted = SolarRuntime(hass, runtime.entry)
    restarted.battery_fleet.restore({"expected_numbers": {
        "storage": {"entity_id": "number.fictional_storage", "target_w": 1000}}})
    assert not restarted.battery_fleet.state.expected_numbers
    assert not await restarted.battery_fleet.tick(grid_w=3000, allow_command=True)
    assert restarted.battery_fleet.overview()["batteries"][0]["monitor_only"]
    assert not restarted.battery_fleet.overview()["control_enabled"]
    assert runtime.entry.options["batteries"][0] == raw
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_live_profile_replaces_cached_generic_reading_and_writer_capability():
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    assert runtime.battery_fleet.read()[0].controllable
    profile = {**runtime.battery_fleet.configs["bat1"], "profile": MARSTEK_PROFILE,
               "ac_power_confirmed": True}
    runtime.live_options._apply_group("batteries", [profile], [])
    assert not runtime.battery_fleet.last
    current = runtime.battery_fleet.overview()["batteries"][0]
    assert current["monitor_only"] and not current["controllable"]
    assert "number_entity" not in runtime.battery_fleet.configs["bat1"]
    assert not await runtime.battery_fleet.tick(grid_w=-2000, allow_command=True)
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_profile_changed_during_intent_save_cannot_send_old_generic_command():
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    save = runtime.store.async_save

    async def changed(data):
        await save(data)
        runtime.battery_fleet.configs["bat1"]["profile"] = MARSTEK_PROFILE

    runtime.store.async_save = changed
    assert not await runtime.battery_fleet._send("bat1", -1000)
    assert not hass.services.calls
    assert runtime.battery_fleet.state.pending is None


@pytest.mark.parametrize("soc", [0, 11, "unknown", "unavailable", -1, 101])
def test_monitor_soc_never_introduces_a_reserve_policy_or_masks_known_power(soc):
    runtime, _hass = marstek(power=200, soc=soc)
    reading = runtime.battery_fleet.read()[0]
    assert reading.valid and reading.power_valid and reading.power_w == 200
    assert reading.soc_valid == (isinstance(soc, int) and 0 <= soc <= 100)
    if not reading.soc_valid:
        assert reading.soc_pct is None
        assert runtime.battery_fleet.overview()["aggregate"]["soc_pct"] is None
    _grid, valid, discharge, ready, _stamp = runtime._site_data()
    assert valid and ready and discharge == 200


@pytest.mark.parametrize("confirmation", [False, None, 1, "true"])
def test_ac_scope_requires_literal_confirmation(confirmation):
    runtime, _hass = marstek(power=800, confirmed=confirmation)
    reading = runtime.battery_fleet.read()[0]
    assert not reading.valid and not reading.power_valid and reading.power_w is None
    assert not runtime._site_data()[1]


def test_power_sign_has_no_implicit_marstek_default():
    raw = normalize_battery_config({"profile": MARSTEK_PROFILE})
    assert raw["power_sign"] == "" and raw["ac_power_confirmed"] is False
    runtime, _hass = marstek(sign="")
    assert not runtime._site_data()[1]


@pytest.mark.parametrize("sign,native,expected", [
    ("discharge_positive", .8, 800), ("charge_positive", -.8, 800),
    ("discharge_positive", -.8, -800), ("charge_positive", .8, -800),
])
def test_actual_signed_ac_flow_drives_budget_once(sign, native, expected):
    runtime, hass = marstek(sign=sign)
    hass.states.set("sensor.grid", -500, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fictional_storage_ac", native, {"unit_of_measurement": "kW"})
    reading = runtime.battery_fleet.read()[0]
    assert reading.power_w == expected
    budget = sg_solar_budget(runtime)
    assert budget["valid"]
    # Charging already reduces P1 export; it cannot be reclaimed as free sun.
    assert budget["eligible_w"] == (0 if expected > 0 else 500)


def test_site_budget_uses_battery_original_timestamp_and_stricter_sg_freshness():
    runtime, hass = marstek()
    hass.states.set("sensor.fictional_storage_ac", 0, {"unit_of_measurement": "W"}, reported_age=60)
    stamp = hass.states.get("sensor.fictional_storage_ac").last_reported.timestamp()
    assert runtime._site_data()[-1] == stamp
    assert sg_solar_budget(runtime)["grid_reported_at"] == stamp
    runtime.settings["stale_s"] = 300
    hass.states.set("sensor.fictional_storage_ac", 0, {"unit_of_measurement": "W"}, reported_age=200)
    assert runtime._site_data()[1]
    assert not sg_solar_budget(runtime)["valid"]


@pytest.mark.parametrize("source", ["unavailable", "stale", "estimated", "future"])
def test_one_good_battery_cannot_hide_an_unknown_active_sibling(source):
    runtime, hass = marstek()
    other = {**runtime.battery_fleet.configs["storage"], "id": "other", "power_entity": "sensor.fictional_other_ac"}
    runtime.battery_fleet.configs["other"] = other
    attrs, age, value = {"unit_of_measurement": "W"}, 0, 900
    if source == "unavailable": value = "unavailable"
    elif source == "stale": age = 121
    elif source == "future": age = -30
    else: attrs["estimated"] = True
    hass.states.set(other["power_entity"], value, attrs, reported_age=age)
    assert runtime.battery_fleet.read()[0].valid
    assert not runtime._site_data()[1]
    assert not sg_solar_budget(runtime)["valid"]
    other["enabled"] = False
    assert runtime._site_data()[1]


def test_legacy_central_source_must_have_explicit_nonconflicting_fleet_coverage():
    runtime, hass = marstek(power=800)
    runtime.settings["battery_power_entity"] = "sensor.fictional_legacy_ac"
    hass.states.set("sensor.fictional_legacy_ac", 500, {"unit_of_measurement": "W"})
    assert not runtime._site_data()[1]
    assert "overlap" in battery_source_error(runtime.battery_fleet.configs.values(), runtime.settings)
    runtime.settings["battery_power_entity"] = "sensor.fictional_storage_ac"
    assert runtime._site_data()[1:3] == (True, 800)  # Same meter counted once.
    runtime.settings["battery_sign"] = "charge_positive"
    assert not runtime._site_data()[1]


def test_duplicate_and_primary_source_bindings_never_become_battery_credit():
    runtime, _hass = marstek()
    runtime.battery_fleet.configs["other"] = {**runtime.battery_fleet.configs["storage"], "id": "other"}
    assert not runtime._site_data()[1]
    del runtime.battery_fleet.configs["other"]
    runtime.battery_fleet.configs["storage"]["power_entity"] = "sensor.grid"
    assert not runtime._site_data()[1]
