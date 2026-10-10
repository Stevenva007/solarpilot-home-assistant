"""Read-only heat-pump presentation evidence with fictitious local bindings."""
from copy import deepcopy

import pytest

from test_sg_observations64 import observed, split
from test_sg_transport62 import native, writes


@pytest.mark.parametrize("frequency,state,label", [
    (35, "active", "Compressor draait"), (0, "idle", "Compressor staat stil")])
def test_compressor_is_primary_operation_evidence_without_sg_effect(frequency, state, label):
    runtime, hass = observed(compressor_frequency_entity="sensor.hp_frequency",
                             zone_entities=["climate.room"])
    hass.states.set("sensor.hp_frequency", frequency, {"unit_of_measurement": "Hz"}, reported_age=1)
    hass.states.set("climate.room", "heat", {"hvac_action": "heating"})
    before = deepcopy(runtime._snapshot())
    view = runtime.panasonic.overview()
    operation = view["operation"]
    assert operation["state"] == state and operation["label"] == label
    assert operation["evidence"] == "compressor_frequency"
    assert operation["observed_at"] == view["compressor_stamp"] == view["compressor_frequency_observed_at"]
    assert operation["stale_s"] == view["source_stale_s"] == 120
    assert view["sg_effect_confirmed"] is False
    assert runtime._snapshot() == before and not hass.services.calls


@pytest.mark.parametrize("case", ["missing", "stale", "restored", "unit", "unknown", "negative"])
def test_configured_unreliable_compressor_source_cannot_fall_back_to_native_action(case):
    runtime, hass = observed(compressor_frequency_entity="sensor.hp_frequency",
                             zone_entities=["climate.room"])
    hass.states.set("climate.room", "heat", {"hvac_action": "heating"})
    if case != "missing":
        attrs = {"unit_of_measurement": "W" if case == "unit" else "Hz"}
        if case == "restored":
            attrs["restored"] = True
        hass.states.set("sensor.hp_frequency", {"unknown": "unknown", "negative": -1}.get(case, 35),
                        attrs, reported_age=121 if case == "stale" else 0)
    view = runtime.panasonic.overview()
    assert view["operation"]["state"] == "unknown"
    assert view["operation"]["observed_at"] is None
    assert view["compressor_frequency_observed_at"] is None
    assert view["context"] == "space_heating"  # context stays separate


@pytest.mark.parametrize("mode,action,state", [
    ("heat", "heating", "active"), ("cool", "cooling", "active"),
    ("heat", "idle", "idle"), ("off", "off", "idle"),
    ("heat", None, "unknown"), ("auto", None, "unknown")])
def test_only_explicit_native_action_is_activity_fallback(mode, action, state):
    runtime, hass = observed(zone_entities=["climate.room"])
    attrs = {"hvac_action": action} if action is not None else {}
    hass.states.set("climate.room", mode, attrs)
    operation = runtime.panasonic.overview()["operation"]
    assert operation["state"] == state
    assert operation["evidence"] == ("none" if state == "unknown" else "native_action")
    assert not hass.services.calls


@pytest.mark.parametrize("direction", ["WATER", "DHW", "HOT_WATER", "PUMP", "ON", "HEAT", "AUTO_HEAT"])
def test_valve_programme_and_electrical_watts_cannot_prove_operation(direction):
    runtime, hass = observed(activity_entity="sensor.hp_direction", power_entity="sensor.hp_total",
                             power_scope="total")
    hass.states.set("sensor.hp_direction", direction)
    hass.states.set("sensor.hp_total", 2400, {"unit_of_measurement": "W"})
    view = runtime.panasonic.overview()
    assert view["operation"]["state"] == "unknown"
    assert view["power_w"] == 2400 and view["power_complete"]
    assert view["power_observed_at"] == view["power_stamp"]
    assert view["activity"] == direction


def test_one_native_idle_action_cannot_hide_missing_second_zone():
    runtime, hass = observed(zone_entities=["climate.room", "climate.other_room"])
    hass.states.set("climate.room", "heat", {"hvac_action": "idle"})
    assert runtime.panasonic.overview()["operation"]["state"] == "unknown"
    hass.states.set("climate.other_room", "off", {"hvac_action": "idle"}, reported_age=1)
    assert runtime.panasonic.overview()["operation"]["state"] == "idle"
    hass.states.set("climate.other_room", "heat", {"hvac_action": "heating"}, reported_age=121)
    assert runtime.panasonic.overview()["operation"]["state"] == "unknown"


@pytest.mark.parametrize("estimated", [False, True])
def test_explicit_tank_action_is_labelled_as_hot_water_and_estimates_are_not_proof(estimated):
    runtime, hass = observed(tank_target_entity="water_heater.tank")
    hass.states.set("water_heater.tank", "on", {"hvac_action": "heating", "estimated": estimated,
                    "temperature_unit": "°C", "temperature": 50})
    operation = runtime.panasonic.overview()["operation"]
    assert operation["state"] == ("unknown" if estimated else "active")
    if not estimated:
        assert operation["label"] == "Panasonic meldt tapwateropwarming"


@pytest.mark.parametrize("age,state", [(1, "active"), (121, "unknown")])
def test_explicit_native_activity_sensor_uses_source_freshness(age, state):
    runtime, hass = observed(activity_entity="sensor.hp_action")
    hass.states.set("sensor.hp_action", "heating", reported_age=age)
    assert runtime.panasonic.overview()["operation"]["state"] == state


@pytest.mark.parametrize("flag", ["estimated", "is_estimated"])
def test_estimated_generic_activity_cannot_confirm_heatpump_operation(flag):
    runtime, hass = observed(activity_entity="sensor.hp_action")
    hass.states.set("sensor.hp_action", "heating", {flag: True})
    operation = runtime.panasonic.overview()["operation"]
    assert operation["state"] == "unknown" and operation["observed_at"] is None
    assert operation["evidence"] == "none" and not hass.services.calls


def test_temperature_target_and_zones_have_independent_real_report_stamps():
    runtime, hass = observed(tank_temperature_entity="sensor.hp_tank", tank_target_entity="water_heater.tank",
                             zone_entities=["climate.room"])
    hass.states.set("sensor.hp_tank", 49, {"unit_of_measurement": "°C"}, reported_age=1)
    hass.states.set("water_heater.tank", "on", {"temperature_unit": "°C", "temperature": 50}, reported_age=2)
    hass.states.set("climate.room", "heat", {"hvac_action": "idle", "temperature_unit": "°C",
                    "current_temperature": 19, "temperature": 20}, reported_age=3)
    first, second = runtime.panasonic.overview(), runtime.panasonic.overview()
    assert first["temperature_stamp"] == second["temperature_stamp"] == hass.states.get("sensor.hp_tank").last_reported.timestamp()
    assert first["target_observed_at"] == first["target_stamp"] == second["target_stamp"]
    assert first["target_stamp"] == hass.states.get("water_heater.tank").last_reported.timestamp()
    assert first["zones"][0]["observed_at"] == hass.states.get("climate.room").last_reported.timestamp()
    hass.states.set("water_heater.tank", "on", {"temperature_unit": "°C", "temperature": 50}, reported_age=121)
    hass.states.set("climate.room", "heat", {"hvac_action": "idle"}, reported_age=121)
    expired = runtime.panasonic.overview()
    assert expired["target_c"] is None and expired["target_stamp"] is None and expired["target_observed_at"] is None
    assert expired["temperature_c"] == 49
    assert expired["zones"][0]["observed_at"] is None and expired["zones"][0]["available"] is False


def test_reading_overview_does_not_refresh_operation_or_independent_source_stamps():
    runtime, hass = split(compressor_frequency_entity="sensor.hp_frequency",
                          sg_status_entity="binary_sensor.hp_received_sg")
    hass.states.set("sensor.hp_frequency", 35, {"unit_of_measurement": "Hz"}, reported_age=1)
    hass.states.set("binary_sensor.hp_received_sg", "on", reported_age=2)
    first, second = runtime.panasonic.overview(), runtime.panasonic.overview()
    for key in ("operation", "power_observed_at", "power_supply1_observed_at",
                "power_supply2_observed_at", "compressor_frequency_observed_at", "sg_status_observed_at"):
        assert first[key] == second[key]
    assert first["sg_status_observed_at"] == hass.states.get("binary_sensor.hp_received_sg").last_reported.timestamp()
    hass.states.set("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"}, reported_age=121)
    incomplete = runtime.panasonic.overview()
    assert incomplete["power_observed_at"] is None and incomplete["power_supply2_observed_at"] is None
    assert incomplete["power_supply1_observed_at"] == first["power_supply1_observed_at"]
    assert incomplete["power_supply1_w"] == 1400 and incomplete["power_w"] is None


@pytest.mark.asyncio
async def test_sg_render_clock_is_separate_from_live_relay_readback_clock():
    from test_sg_controller62 import fixture

    manager, adapter, clock, _runtime = fixture()
    await manager.start()
    first = manager.overview()
    assert first["relay_confirmed"] and first["relay_observed_at"] == clock()
    snapshot = deepcopy(manager.snapshot())
    clock.advance(15)
    second = manager.overview()
    assert second["relay_observed_at"] == first["relay_observed_at"]
    assert second["observed_at"] > first["observed_at"]
    assert manager.snapshot() == snapshot
    await manager._read(force=True)
    assert manager.overview()["relay_observed_at"] == clock()
    assert not adapter.calls


@pytest.mark.asyncio
async def test_relay_stamp_requires_successful_native_rpc_and_is_not_restored(native):
    from test_sg_controller62 import fixture

    manager, _adapter, clock, _runtime = fixture()
    manager._adapter = native.adapter
    await manager.start()
    first = manager.overview()
    assert "Switch.GetStatus" in [method for method, _params, _timeout in native.device.calls]
    assert first["relay_observed_at"] == clock() and first["relay_on"] is False
    calls = len(native.device.calls)
    clock.advance(15)
    assert manager.overview()["relay_observed_at"] == first["relay_observed_at"]
    assert len(native.device.calls) == calls
    native.device.error_method = "Switch.GetStatus"
    await manager._read(force=True)
    unavailable = manager.overview()
    assert unavailable["relay_on"] is None and unavailable["relay_observed_at"] is None
    assert unavailable["relay_confirmed"] is False
    assert not writes(native) and not native.hass.services.calls
    replacement, _adapter, _clock, _runtime = fixture()
    replacement.restore(manager.snapshot())
    assert replacement.overview()["relay_observed_at"] is None


@pytest.mark.parametrize("remaining,output,deadline", [(30, True, 30), (0, True, None),
    (None, True, None), ("invalid", True, None), (601, True, None), (30, False, None)])
def test_relay_source_deadline_is_only_evidence_of_the_last_actual_timer_readback(remaining, output, deadline):
    from test_sg_controller62 import fixture

    manager, adapter, clock, _runtime = fixture()
    manager._status({"output": output, "lease_remaining_s": remaining})
    first = manager.overview()
    expected = None if deadline is None else clock() + deadline
    assert first["relay_valid_until"] == expected
    before = deepcopy(manager.snapshot())
    clock.advance(31)
    expired = manager.overview()
    assert expired["relay_valid_until"] == expected  # render cannot renew source proof
    assert expired["relay_observed_at"] == first["relay_observed_at"]
    assert expired["relay_on"] is output  # presentation does not alter the control state
    assert manager.snapshot() == before and not adapter.calls
    if output and deadline is not None:
        # A later genuine ON report without a timer still proves contact ON;
        # it provides no local permission. No stale permission is carried over.
        manager._status({"output": True})
        fresh = manager.overview()
        assert fresh["relay_on"] is True and fresh["relay_valid_until"] is None
        assert fresh["relay_observed_at"] == clock() and fresh["lease_confirmed"] is False
