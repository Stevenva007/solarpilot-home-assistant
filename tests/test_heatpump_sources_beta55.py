"""Synthetic activity-source regressions; no HA, exports or actuator calls."""
from datetime import datetime, timezone
from types import SimpleNamespace as NS
import time

import pytest

from custom_components.solar_pilot.heatpump_learning import (
    CONTEXT_COOLING,
    CONTEXT_DHW,
    CONTEXT_HEATING,
    CONTEXT_NORMAL,
    CONTEXT_UNKNOWN,
    classify_heatpump,
)
from test_runtime import build


def metered_heatpump(*, tank=False, task=None):
    runtime, hass = build(settings={"pv_entity": "sensor.pv"})
    hass.states.set("sensor.pv", 3000, {"unit_of_measurement": "W"})
    runtime.panasonic.settings.update(zone_entities=["climate.zone"])
    hass.states.set("climate.zone", "off", {"hvac_action": "off"})
    if tank:
        runtime.panasonic.settings["tank_target_entity"] = "water_heater.tank"
        hass.states.set("water_heater.tank", "heat", {"hvac_action": "idle"})
    if task is not None:
        runtime.panasonic.settings["activity_entity"] = "sensor.task"
        hass.states.set("sensor.task", task)
    return runtime, hass


def observe(runtime):
    return runtime.learning_hub.observe(datetime.now(timezone.utc), time.monotonic())


def invalidate(hass, entity_id, invalid):
    obj = hass.states.get(entity_id)
    if invalid == "missing":
        del hass.states.data[entity_id]
    elif invalid in {"unknown", "unavailable", "blank"}:
        obj.state = " " if invalid == "blank" else invalid
    elif invalid == "restored_old":
        obj.attributes["restored"] = True
        obj.last_reported = datetime.fromtimestamp(time.time() - 30 * 86400, timezone.utc)
    elif invalid == "restored_fresh":
        obj.attributes["restored"] = True
    elif invalid == "missing_stamp":
        obj.last_reported = obj.last_updated = None
    elif invalid == "malformed_stamp":
        obj.last_reported = "2026-10-03T12:00:00Z"
    elif invalid == "empty_stamp":
        obj.last_reported = ""
    elif invalid == "zero_stamp":
        obj.last_reported = 0
    elif invalid in {"nan", "inf", "bool", "string_result"}:
        value = {"nan": float("nan"), "inf": float("inf"),
                 "bool": True, "string_result": str(time.time())}[invalid]
        obj.last_reported = NS(timestamp=lambda: value)
    elif invalid == "os_error":
        def invalid_timestamp():
            raise OSError("public fixture invalid clock")
        obj.last_reported = NS(timestamp=invalid_timestamp)
    elif invalid == "future":
        obj.last_reported = datetime.fromtimestamp(time.time() + 120, timezone.utc)
    elif invalid == "stale":
        obj.last_reported = datetime.fromtimestamp(time.time() - 7201, timezone.utc)
    else:
        raise AssertionError(invalid)


@pytest.mark.parametrize("role", ["zone", "tank"])
@pytest.mark.parametrize("action", ["heating", "idle"])
@pytest.mark.parametrize("invalid", [
    "missing", "unknown", "unavailable", "blank", "restored_old", "restored_fresh",
    "missing_stamp", "malformed_stamp", "empty_stamp", "zero_stamp",
    "nan", "inf", "bool", "string_result", "os_error", "future", "stale",
])
def test_unreliable_activity_cannot_train_household_or_active_power(role, action, invalid):
    runtime, hass = metered_heatpump(tank=role == "tank")
    entity_id = "climate.zone" if role == "zone" else "water_heater.tank"
    hass.states.get(entity_id).attributes["hvac_action"] = action
    invalidate(hass, entity_id, invalid)

    sample = observe(runtime)

    assert sample["valid"] and sample["context"] == CONTEXT_UNKNOWN
    assert runtime.unified_planner.base_load.accepted == 0
    assert runtime.heatpump_learning.unknown_observations == 1
    assert all(not values for values in runtime.heatpump_learning.samples.values())
    assert not hass.services.calls


@pytest.mark.parametrize("role,age,short,long", [
    ("zone", 450, 300, 600),
    ("tank", 450, 300, 600),
])
@pytest.mark.parametrize("action", ["heating", "idle"])
def test_each_native_activity_report_uses_shared_read_only_freshness_limit(role, age, short, long, action):
    runtime, hass = metered_heatpump(tank=role == "tank")
    entity_id = "climate.zone" if role == "zone" else "water_heater.tank"
    manager = runtime.panasonic
    hass.states.set(entity_id, "auto", {"hvac_action": action}, reported_age=age)

    manager.settings["stale_s"] = short
    assert classify_heatpump(runtime, datetime.now(timezone.utc))[0] == CONTEXT_UNKNOWN
    manager.settings["stale_s"] = long
    expected = CONTEXT_NORMAL if action == "idle" else (
        CONTEXT_HEATING if role == "zone" else CONTEXT_DHW)
    assert classify_heatpump(runtime, datetime.now(timezone.utc))[0] == expected


@pytest.mark.parametrize("role", ["zone", "tank"])
@pytest.mark.parametrize("fallback", ["missing", "none"])
def test_absent_reported_timestamp_uses_actual_updated_timestamp(role, fallback):
    runtime, hass = metered_heatpump(tank=role == "tank")
    entity_id = "climate.zone" if role == "zone" else "water_heater.tank"
    obj = hass.states.get(entity_id)
    if fallback == "missing":
        del obj.last_reported
    else:
        obj.last_reported = None

    assert observe(runtime)["context"] == CONTEXT_NORMAL
    assert runtime.unified_planner.base_load.accepted == 1
    assert not hass.services.calls


@pytest.mark.parametrize("role", ["zone", "tank"])
def test_recent_reported_timestamp_can_refresh_unchanged_native_state(role):
    runtime, hass = metered_heatpump(tank=role == "tank")
    entity_id = "climate.zone" if role == "zone" else "water_heater.tank"
    hass.states.set(entity_id, "off", {"hvac_action": "idle"},
                    age=30 * 86400, reported_age=0)

    assert observe(runtime)["context"] == CONTEXT_NORMAL
    assert runtime.unified_planner.base_load.accepted == 1


def test_missing_zone_is_unknown_despite_off_sibling_and_idle_task():
    runtime, hass = metered_heatpump(tank=True, task="IDLE")
    runtime.panasonic.settings["zone_entities"].append("climate.missing")

    assert observe(runtime)["context"] == CONTEXT_UNKNOWN
    assert runtime.unified_planner.base_load.accepted == 0
    assert not hass.services.calls


@pytest.mark.parametrize("action,expected", [
    ("heating", CONTEXT_HEATING), ("cooling", CONTEXT_COOLING),
])
def test_explicit_active_sibling_keeps_safe_classification_with_missing_zone(action, expected):
    runtime, hass = metered_heatpump(task="PUMP")
    runtime.panasonic.settings["zone_entities"].append("climate.missing")
    hass.states.get("climate.zone").attributes["hvac_action"] = action

    assert observe(runtime)["context"] == expected
    assert runtime.unified_planner.base_load.accepted == 0


@pytest.mark.parametrize("task", ["PUMP", "WATER", "MYSTERY"])
def test_ambiguous_task_is_not_normal_even_when_native_zone_off_and_tank_idle(task):
    runtime, hass = metered_heatpump(tank=True, task=task)

    assert observe(runtime)["context"] == CONTEXT_UNKNOWN
    assert runtime.unified_planner.base_load.accepted == 0
    assert not hass.services.calls


@pytest.mark.parametrize("entity_id", ["number.tank", "input_number.tank"])
@pytest.mark.parametrize("report", ["missing", "old", "no_timestamp"])
def test_numeric_boiler_setpoint_without_activity_remains_optional(entity_id, report):
    runtime, hass = metered_heatpump(task="IDLE")
    runtime.panasonic.settings["tank_target_entity"] = entity_id
    if report != "missing":
        hass.states.set(entity_id, 50, {"unit_of_measurement": "°C"}, age=30 * 86400)
        if report == "no_timestamp":
            hass.states.get(entity_id).last_reported = None
            hass.states.get(entity_id).last_updated = None

    assert observe(runtime)["context"] == CONTEXT_NORMAL
    assert runtime.unified_planner.base_load.accepted == 1
    assert not hass.services.calls


@pytest.mark.parametrize("code", [
    "site_source", "battery_source", "wallbox_source", "consumer_source", "settling", "balance",
])
def test_invalid_measurement_is_counted_by_actual_source_failure(code):
    runtime, hass = metered_heatpump()
    if code == "site_source":
        hass.states.set("sensor.pv", "unavailable", {"unit_of_measurement": "W"})
    elif code == "battery_source":
        runtime.settings["battery_power_entity"] = "sensor.missing_battery"
    elif code == "wallbox_source":
        runtime.wallbox_settings.update(enabled=True, power_entity="sensor.missing_ev")
    elif code == "consumer_source":
        state = runtime.states["a"]
        state.owned = state.on = state.available = True
    elif code == "settling":
        runtime.pending = {"intent": "pending"}
    elif code == "balance":
        hass.states.set("sensor.grid", -5000, {"unit_of_measurement": "W"})

    sample = observe(runtime)

    assert not sample["valid"] and sample["code"] == code
    assert next(iter(runtime.learning_hub.days.values())) == {code: 1}
    assert runtime.unified_planner.base_load.accepted == 0
    assert runtime.heatpump_learning.unknown_observations == 0
    assert not hass.services.calls


def test_new_source_failure_does_not_relabel_historical_heatpump_counters():
    runtime, hass = metered_heatpump()
    day = datetime.now(timezone.utc).date().isoformat()
    runtime.learning_hub.restore({"days": {day: {
        "site_source": 2, "heatpump_unknown": 9, "heatpump_heatpump_unknown": 3,
    }}})
    hass.states.set("sensor.pv", "unavailable", {"unit_of_measurement": "W"})

    observe(runtime)

    assert runtime.learning_hub.days[day] == {
        "site_source": 3, "heatpump_unknown": 9, "heatpump_heatpump_unknown": 3,
    }
