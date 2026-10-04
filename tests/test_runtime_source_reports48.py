"""Dispatch requires real source reports; static helpers need not change often."""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import time

import pytest

from test_runtime import build
from test_wallbox_runtime import setup as wallbox_setup


def actuators(hass):
    return [call for call in hass.services.calls if call[0] != "persistent_notification"]


def invalidate(hass, entity_id, kind):
    obj = hass.states.get(entity_id)
    if kind == "restored":
        obj.attributes["restored"] = True
    elif kind == "future":
        obj.last_reported = datetime.fromtimestamp(time.time() + 120, timezone.utc)
    elif kind == "missing_stamp":
        obj.last_reported = obj.last_updated = None
    elif kind == "malformed_stamp":
        obj.last_reported = "2026-10-03T12:00:00Z"
    elif kind == "nonfinite_stamp":
        obj.last_reported = SimpleNamespace(timestamp=lambda: float("nan"))
    else:
        raise AssertionError(kind)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [
    "restored", "future", "missing_stamp", "malformed_stamp", "nonfinite_stamp",
])
async def test_invalid_grid_report_cannot_start_a_consumer(invalid):
    runtime, hass = build()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.set("sensor.grid", -5000, {"unit_of_measurement": "W"})
    invalidate(hass, "sensor.grid", invalid)

    await runtime.tick()

    assert runtime.grid_w is None
    assert not actuators(hass)
    assert not runtime.states["a"].owned
    assert not runtime.problem.startswith("Interne fout")


@pytest.mark.asyncio
@pytest.mark.parametrize("fallback", ["missing_attribute", "none"])
async def test_missing_last_reported_uses_valid_last_updated_for_real_dispatch(fallback):
    runtime, hass = build()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.set("sensor.grid", -5000, {"unit_of_measurement": "W"})
    obj = hass.states.get("sensor.grid")
    if fallback == "missing_attribute":
        del obj.last_reported
    else:
        obj.last_reported = None

    await runtime.tick()

    assert runtime.grid_w == -5000
    assert actuators(hass) == [
        ("switch", "turn_on", {"entity_id": "switch.load"}),
    ]


@pytest.mark.asyncio
async def test_fresh_last_reported_takes_precedence_over_old_last_updated():
    runtime, hass = build()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.set("sensor.grid", -5000, {"unit_of_measurement": "W"},
                    age=86400, reported_age=0)

    await runtime.tick()

    assert runtime.grid_w == -5000
    assert actuators(hass) == [
        ("switch", "turn_on", {"entity_id": "switch.load"}),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("report_value", [True, "not a number", None, float("inf")])
async def test_invalid_timestamp_result_for_static_condition_blocks_start_without_internal_error(
        report_value):
    runtime, hass = build(device={"condition_entity": "input_boolean.ready"})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.get("input_boolean.ready").last_reported = SimpleNamespace(
        timestamp=lambda: report_value)

    await runtime.tick()

    assert not actuators(hass)
    assert not runtime.states["a"].demand
    assert runtime.mode == "solar"
    assert not runtime.problem.startswith("Interne fout")


@pytest.mark.asyncio
async def test_unexpected_decimal_timestamp_is_rejected_without_arithmetic_error():
    runtime, hass = build()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.get("sensor.grid").last_reported = SimpleNamespace(
        timestamp=lambda: Decimal(str(time.time())))

    await runtime.tick()

    assert runtime.grid_w is None
    assert not runtime.problem.startswith("Interne fout")
    assert runtime.mode == "solar"
    assert not actuators(hass)


@pytest.mark.asyncio
async def test_unchanged_old_condition_and_soc_helpers_still_allow_fresh_grid_dispatch():
    runtime, hass = build(device={"condition_entity": "input_boolean.ready"}, settings={
        "battery_soc_entity": "sensor.battery_soc", "battery_power_entity": "sensor.battery_power",
        "battery_min_soc": 20,
    })
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.set("input_boolean.ready", "on", age=7 * 86400)
    hass.states.set("sensor.battery_soc", 80, {"unit_of_measurement": "%"}, age=7 * 86400)
    hass.states.set("sensor.battery_power", 0, {"unit_of_measurement": "W"})

    await runtime.tick()

    assert runtime.states["a"].demand
    assert actuators(hass) == [
        ("switch", "turn_on", {"entity_id": "switch.load"}),
    ]


def confirmed_wallbox():
    runtime, hass = wallbox_setup(
        session_mode_entity="sensor.ev_session", connected_entity="binary_sensor.ev_connected",
        demand_entity="input_boolean.ev_demand", trust_solar_setting=False)
    hass.states.set("sensor.ev_session", "Zonne-auto · laden")
    hass.states.set("binary_sensor.ev_connected", "on")
    hass.states.set("input_boolean.ev_demand", "on")
    return runtime, hass


@pytest.mark.parametrize("entity_id", ["select.ev_solar", "sensor.ev_session"])
@pytest.mark.parametrize("invalid", ["restored", "future", "missing_stamp"])
def test_invalid_wallbox_solar_session_sources_never_confirm_full_solar(entity_id, invalid):
    runtime, hass = confirmed_wallbox()
    assert runtime._wallbox_reading().session_confirmed
    invalidate(hass, entity_id, invalid)

    reading = runtime._wallbox_reading()

    assert not reading.session_confirmed
    assert reading.mode == "unknown"
    assert not actuators(hass)


@pytest.mark.parametrize("entity_id", ["input_boolean.ev_demand", "binary_sensor.ev_connected"])
@pytest.mark.parametrize("invalid", ["restored", "future", "missing_stamp"])
def test_invalid_wallbox_request_or_connection_does_not_grant_ready_status(entity_id, invalid):
    runtime, hass = confirmed_wallbox()
    invalidate(hass, entity_id, invalid)

    reading = runtime._wallbox_reading()

    assert not reading.valid
    if entity_id == "input_boolean.ev_demand":
        assert reading.demand is None
    else:
        assert reading.connected is None
    assert not actuators(hass)


def test_old_unchanged_wallbox_demand_helper_remains_valid_with_fresh_native_sources():
    runtime, hass = confirmed_wallbox()
    hass.states.set("input_boolean.ev_demand", "on", age=7 * 86400)

    reading = runtime._wallbox_reading()

    assert reading.valid and reading.demand is True
    assert reading.session_confirmed and reading.mode == "full_solar"
    assert not actuators(hass)


@pytest.mark.parametrize("invalid", ["restored", "future", "missing_stamp"])
def test_invalid_wallbox_current_source_uses_explicit_manual_profile_without_live_claim(invalid):
    runtime, hass = confirmed_wallbox()
    runtime.wallbox_profile.settings.update(
        profile_auto=True, max_current_entity="number.ev_max_current", max_current_a=25)
    hass.states.set("number.ev_max_current", 16, {"unit_of_measurement": "A", "max": 32})
    invalidate(hass, "number.ev_max_current", invalid)

    profile = runtime.wallbox_profile.update()

    assert profile["max_current_a"] == 25
    assert profile["current_source"] == "handmatig bevestigd profiel"
    assert profile["warning"]
    assert not actuators(hass)


@pytest.mark.asyncio
async def test_restored_effective_wallbox_session_cannot_start_using_car_power():
    runtime, hass = confirmed_wallbox()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.set("sensor.grid", 0, {"unit_of_measurement": "W"})
    invalidate(hass, "sensor.ev_session", "restored")

    await runtime.tick()

    assert not runtime.wallbox_guard.reading.session_confirmed
    assert runtime.wallbox_guard.reading.mode == "unknown"
    assert not actuators(hass)
    assert not runtime.states["a"].owned


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["restored", "future"])
async def test_invalid_active_report_waits_at_restart_then_fresh_on_is_adopted_read_only(invalid):
    runtime, hass = build(device={"min_on_s": 600})
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "on")
    invalidate(hass, "switch.load", invalid)
    runtime.store.data = {
        "mode": "solar", "device_modes": {"a": "auto"},
        "leases": {"a": {"watts": 1000, "name": "Testtoestel"}},
    }
    await runtime.start()
    assert "a" in runtime.recovery and runtime.mode == "solar"
    assert not runtime.states["a"].owned

    hass.states.set("switch.load", "on")
    await runtime.tick()

    assert not runtime.recovery and runtime.mode == "solar"
    assert runtime.states["a"].owned
    assert not actuators(hass)


@pytest.mark.asyncio
async def test_long_unchanged_active_switch_with_durable_lease_resumes_without_replay():
    runtime, hass = build(device={"min_on_s": 600})
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "on", age=7 * 86400)
    runtime.store.data = {
        "mode": "solar", "device_modes": {"a": "auto"},
        "leases": {"a": {"watts": 1000, "name": "Testtoestel"}},
    }

    await runtime.start()

    assert not runtime.recovery and runtime.mode == "solar"
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert not actuators(hass)
