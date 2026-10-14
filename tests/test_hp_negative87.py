"""Explicit consumption flooring retains signed raw proof and hard site limits.

All entities and source values are fictional. Flooring an HP-consumption input
does not diagnose its sign or certify a physical compressor state.
"""
import pytest

from custom_components.solar_pilot.heatpump_budget import heatpump_power, sg_solar_budget
from test_sg_budget_priority62 import configured
from test_sg_observations64 import split


@pytest.mark.parametrize("value,unit,raw", [
    (-0.001, "W", -0.001), (-2400, "W", -2400), (-100000, "W", -100000),
    (-0.001, "kW", -1), (-2.4, "kW", -2400), (-100, "kW", -100000),
])
def test_fresh_finite_negative_hp_consumption_uses_zero_with_original_signed_source(value, unit, raw):
    runtime, hass = configured(export=3500)
    hass.states.set("sensor.public_hp", value, {"unit_of_measurement": unit})
    obj = hass.states.get("sensor.public_hp")
    original = obj.last_reported.timestamp()
    before = runtime._power("sensor.public_hp")
    reading = heatpump_power(runtime)
    assert reading["valid"] and reading["complete"] and reading["watts"] == 0
    assert reading["source_value"] == str(value) and reading["source_unit"] == unit
    assert reading["source_watts"] == raw
    assert reading["source_reported_wall"] == reading["measured_wall"] == original
    assert reading["normalized"] and reading["normalization_reason"] == "negative_as_zero"
    assert runtime._power("sensor.public_hp") == before == (raw, original)
    assert hass.states.get("sensor.public_hp") is obj and not hass.services.calls
    quality = runtime.panasonic.overview()["power_source_quality"]["total"]
    assert quality["watts"] == 0 and quality["source_watts"] == raw
    assert quality["normalized"] and quality["normalization_reason"] == "negative_as_zero"


@pytest.mark.parametrize("value", [0, -0.0, 0.001, 2500, 100000])
def test_nonnegative_values_keep_ordinary_measured_consumption(value):
    runtime, hass = configured()
    hass.states.set("sensor.public_hp", value, {"unit_of_measurement": "W"})
    reading = heatpump_power(runtime)
    assert reading["valid"] and reading["watts"] == value
    assert reading["normalized"] is False and reading["normalization_reason"] is None


@pytest.mark.parametrize("bad", ["stale", "future", "invalid_unit", "missing", "estimated", "restored",
                                 "nan", "bool", "huge_w", "huge_kw", "reserved"])
def test_negative_policy_does_not_turn_unusable_source_into_zero(bad):
    runtime, hass = configured()
    attrs, value, age = {"unit_of_measurement": "W"}, -1000, 0
    if bad in ("estimated", "restored"):
        attrs[bad] = True
    elif bad == "invalid_unit":
        attrs["unit_of_measurement"] = "kWh"
    elif bad == "stale":
        age = 121
    elif bad == "future":
        age = -6
    elif bad == "nan":
        value = float("nan")
    elif bad == "bool":
        value = True
    elif bad == "huge_w":
        value = -100001
    elif bad == "huge_kw":
        value, attrs["unit_of_measurement"] = -100.001, "kW"
    elif bad == "reserved":
        runtime.wallbox_settings["power_entity"] = "sensor.public_hp"
    hass.states.set("sensor.public_hp", value, attrs, age=age)
    if bad == "missing":
        hass.states.data.pop("sensor.public_hp")
    reading = heatpump_power(runtime)
    assert not reading["valid"] and reading["watts"] is None
    assert reading["normalized"] is False and reading["normalization_reason"] is None


@pytest.mark.parametrize("returned", [(500, "W"), (-2, "kW"), ("unavailable", "W")])
def test_reentrant_second_read_cannot_mix_raw_negative_with_different_effective_value(returned):
    runtime, hass = configured()
    hass.states.set("sensor.public_hp", -1000, {"unit_of_measurement": "W"})
    power = runtime._power

    def changed_source(entity, stale=None):
        hass.states.set(entity, returned[0], {"unit_of_measurement": returned[1]})
        return power(entity, stale)

    runtime._power = changed_source
    reading = heatpump_power(runtime)
    assert not reading["valid"] and reading["watts"] is None
    assert reading["source_watts"] == -1000 and not reading["normalized"]


@pytest.mark.parametrize("other", ["known", "missing", "stale"])
def test_two_feed_total_requires_both_current_sources_even_when_one_is_normalized_zero(other):
    runtime, hass = split()
    hass.states.set("sensor.hp_supply_one", -4, {"unit_of_measurement": "kW"})
    hass.states.set("sensor.hp_supply_two", 600, {"unit_of_measurement": "W"}, age=121 if other == "stale" else 0)
    if other == "missing":
        hass.states.data.pop("sensor.hp_supply_two")
    reading = heatpump_power(runtime)
    assert reading["supplies"]["supply1"]["watts"] == 0
    assert reading["supplies"]["supply1"]["source_watts"] == -4000
    assert reading["supplies"]["supply1"]["normalized"]
    if other == "known":
        assert reading["valid"] and reading["complete"] and reading["watts"] == 600
    else:
        assert not reading["valid"] and not reading["complete"] and reading["watts"] is None
        assert reading["supplies"]["supply2"]["watts"] is None


def test_normalized_hp_zero_adds_no_solar_credit_and_preserves_full_future_envelope():
    runtime, hass = configured(export=3500)
    runtime.entry.runtime_data = runtime
    hass.states.set("sensor.public_hp", -2400, {"unit_of_measurement": "W"})
    budget = sg_solar_budget(runtime)
    assert budget["valid"] and budget["hp_power_w"] == 0 and budget["hp_solar_w"] == 0
    assert budget["available_w"] == budget["eligible_w"] == 3350
    assert runtime._power("sensor.grid")[0] == -3500
    assert runtime.sg_dispatch_allowed()
    hass.states.set("sensor.grid", 0, {"unit_of_measurement": "W"})
    assert not runtime.sg_dispatch_allowed(ignore_solar=True)
