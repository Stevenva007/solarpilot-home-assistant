"""Rejected source facts remain inspectable without becoming usable power."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import time

import pytest

from custom_components.solar_pilot.heatpump_budget import heatpump_power, sg_solar_budget
from test_runtime import build


def metered(**config):
    runtime, hass = build(power=True, settings={"pv_entity": "sensor.sun", "reserve_w": 0})
    runtime.panasonic.update_config({"power_entity": "sensor.hp_total", "power_scope": "total", "stale_s": 120, **config})
    hass.states.set("sensor.sun", 6000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp_total", 1800, {"unit_of_measurement": "W"})
    return runtime, hass


@pytest.mark.parametrize("value,unit,age,reason,source_watts", [
    (1.8, "kW", 121, "stale", 1800),
    (-25, "W", 0, "negative", -25),
    ("unavailable", "W", 0, "invalid_value", None),
    ("nan", "W", 0, "invalid_value", None),
    ("inf", "W", 0, "invalid_value", None),
    (3.3, "kWh", 0, "unsupported_unit", None),
    (1800, None, 0, "unsupported_unit", None),
    (100001, "W", 0, "out_of_range", 100001),
    (1800, "W", -6, "future_timestamp", 1800),
])
def test_rejected_measurements_preserve_source_evidence_without_usable_watts(value, unit, age, reason, source_watts):
    runtime, hass = metered()
    hass.states.set("sensor.hp_total", value, {"unit_of_measurement": unit}, age=age)
    source = hass.states.get("sensor.hp_total")
    reading = heatpump_power(runtime)
    if reason == "negative":
        assert reading["valid"] and reading["complete"] and reading["watts"] == 0
        assert reading["measured_wall"] == source.last_reported.timestamp()
        assert reading["normalized"] and reading["normalization_reason"] == "negative_as_zero"
    else:
        assert not reading["valid"] and not reading["complete"]
        assert reading["watts"] is None and reading["measured_wall"] is None
    assert reading["source_value"] == str(value)
    assert reading["source_unit"] == unit
    assert reading["source_watts"] == source_watts
    assert reading["source_reported_wall"] == source.last_reported.timestamp()
    assert reading["source_age_s"] == pytest.approx(age, abs=0.2)
    assert reading["source_timestamp_kind"] == "last_reported"
    if reason == "negative":
        assert reading["rejection_reason"] is None and reading["reason"] == ""
    else:
        assert reading["rejection_reason"] == reason and reading["reason"]
    assert not hass.services.calls


@pytest.mark.parametrize("flag", ["restored", "estimated", "is_estimated"])
def test_placeholder_reports_keep_original_timestamp_and_are_rejected(flag):
    runtime, hass = metered()
    hass.states.set("sensor.hp_total", 1800, {"unit_of_measurement": "W", flag: True})
    source = hass.states.get("sensor.hp_total")
    reading = heatpump_power(runtime)
    assert not reading["valid"] and reading["measured_wall"] is None
    assert reading["source_reported_wall"] == source.last_reported.timestamp()
    assert reading["rejection_reason"] == ("restored" if flag == "restored" else "estimated")


def test_missing_and_unconfigured_sources_have_separate_reasons_from_a_measured_zero():
    runtime, hass = metered()
    hass.states.data.pop("sensor.hp_total")
    missing = heatpump_power(runtime)
    assert missing["rejection_reason"] == "missing"
    assert missing["source_reported_wall"] is None and missing["watts"] is None
    runtime.panasonic.settings["power_entity"] = ""
    assert heatpump_power(runtime)["rejection_reason"] == "not_configured"
    runtime.panasonic.settings["power_entity"] = "sensor.hp_total"
    hass.states.set("sensor.hp_total", 0, {"unit_of_measurement": "W"})
    zero = heatpump_power(runtime)
    assert zero["valid"] and zero["complete"] and zero["watts"] == zero["source_watts"] == 0
    assert zero["rejection_reason"] is None and zero["reason"] == ""


def test_unchanged_zero_with_new_source_report_is_fresh_but_attribute_updates_cannot_refresh_old_report():
    runtime, hass = metered()
    hass.states.set("sensor.hp_total", 0, {"unit_of_measurement": "W"}, age=86400, reported_age=1)
    reading = heatpump_power(runtime)
    assert reading["valid"] and reading["watts"] == 0
    assert reading["source_age_s"] == pytest.approx(1, abs=0.2)
    # A newer last_updated/last_changed or UI attribute is not the chosen report.
    obj = hass.states.get("sensor.hp_total")
    obj.attributes["friendly_name"] = "Warmtepomp aangepast"
    obj.last_updated = obj.last_changed = datetime.now(timezone.utc)
    obj.last_reported = datetime.fromtimestamp(time.time()-121, timezone.utc)
    stamp = obj.last_reported.timestamp()
    first = heatpump_power(runtime)
    second = heatpump_power(runtime)
    assert first["rejection_reason"] == second["rejection_reason"] == "stale"
    assert first["source_reported_wall"] == second["source_reported_wall"] == stamp
    assert first["measured_wall"] is None and second["measured_wall"] is None
    assert obj.last_reported.timestamp() == stamp


@pytest.mark.parametrize("stamp", ["invalid", "", 0, SimpleNamespace(timestamp=lambda: float("nan")),
                                   SimpleNamespace(timestamp=lambda: True), SimpleNamespace(timestamp=lambda: "1000")])
def test_malformed_report_timestamp_does_not_fall_back_to_newer_last_updated(stamp):
    runtime, hass = metered()
    obj = hass.states.get("sensor.hp_total")
    obj.last_reported = stamp
    reading = heatpump_power(runtime)
    assert not reading["valid"] and reading["source_reported_wall"] is None
    assert reading["source_timestamp_kind"] == "last_reported"
    assert reading["rejection_reason"] == "invalid_timestamp"


def test_absent_report_timestamp_uses_original_last_updated_without_creating_new_time():
    runtime, hass = metered()
    obj = hass.states.get("sensor.hp_total")
    obj.last_reported = None
    stamp = obj.last_updated.timestamp()
    first = heatpump_power(runtime)
    second = heatpump_power(runtime)
    assert first["valid"] and second["valid"]
    assert first["source_timestamp_kind"] == "last_updated"
    assert first["source_reported_wall"] == second["source_reported_wall"] == stamp
    assert first["measured_wall"] == second["measured_wall"] == stamp


def test_split_failure_keeps_each_source_rejection_and_does_not_change_actual_solar_budget_or_ownership():
    runtime, hass = metered(power_entity="", power_supply1_entity="sensor.hp_main",
                            power_supply2_entity="sensor.hp_extra", split_power_confirmed=True)
    hass.states.set("sensor.hp_main", 1.8, {"unit_of_measurement": "kW"}, age=121)
    hass.states.set("sensor.hp_extra", 0, {"unit_of_measurement": "W"})
    snapshot = deepcopy(runtime._snapshot())
    budget = sg_solar_budget(runtime)
    reading = heatpump_power(runtime)
    assert not reading["valid"] and not reading["complete"] and reading["watts"] is None
    one, two = reading["supplies"]["supply1"], reading["supplies"]["supply2"]
    assert not one["valid"] and one["rejection_reason"] == "stale" and one["source_watts"] == 1800
    assert one["source_reported_wall"] is not None and one["measured_wall"] is None
    assert two["valid"] and two["watts"] == 0 and two["rejection_reason"] is None
    assert "voeding 1" in reading["reason"] and "oud" in reading["reason"]
    assert sg_solar_budget(runtime) == budget
    assert runtime._snapshot() == snapshot and not hass.services.calls
