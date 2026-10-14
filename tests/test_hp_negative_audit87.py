"""Independent HP-only zero-floor audits with fictional meters and preserved raw proof."""
from copy import deepcopy
from itertools import product

import pytest

from custom_components.solar_pilot.heatpump_budget import heatpump_power, sg_solar_budget
from custom_components.solar_pilot.heatpump_history import HeatpumpHistory
from test_sg_observations64 import observed, split
from test_sg_budget_priority62 import configured
from test_heatpump_history81 import tank_source
from test_heatpump_history70 import BASE, observe


@pytest.mark.parametrize("value,unit,raw_watts", [
    (-0.001, "W", -0.001), (-1, "W", -1), (-99999.99, "W", -99999.99),
    (-100000, "W", -100000), (-0.25, "kW", -250), (-100, "kW", -100000),
])
def test_only_fresh_finite_plausible_hp_negatives_are_zero_with_original_raw_report(value, unit, raw_watts):
    runtime, hass = observed(power_entity="sensor.fictional_hp", power_scope="total")
    hass.states.set("sensor.fictional_hp", value, {"unit_of_measurement": unit}, reported_age=7)
    obj = hass.states.get("sensor.fictional_hp")
    original_state, original_attrs = obj.state, deepcopy(obj.attributes)
    reported = obj.last_reported.timestamp()
    result = heatpump_power(runtime)
    assert result["valid"] and result["complete"] and result["watts"] == 0
    assert result["normalized"] is True and result["normalization_reason"] == "negative_as_zero"
    assert result["source_value"] == str(value) and result["source_unit"] == unit
    assert result["source_watts"] == raw_watts
    assert result["source_reported_wall"] == result["measured_wall"] == reported
    assert result["source_timestamp_kind"] == "last_reported"
    assert obj.state == original_state and obj.attributes == original_attrs
    view = runtime.panasonic.overview()
    quality = view["power_source_quality"]["total"]
    assert quality["normalized"] is True and quality["normalization_reason"] == "negative_as_zero"
    assert quality["source_watts"] == raw_watts and quality["source_reported_wall"] == reported
    assert view["power_w"] == 0 and view["power_stamp"] == reported
    assert view["compressor_running"] is None and not view["sg_effect_confirmed"]
    assert not hass.services.calls


@pytest.mark.parametrize("bad", ["missing", "nan", "infinity", "boolean", "stale", "future", "unit",
    "restored", "estimated", "overlap", "huge_negative_w", "huge_negative_kw", "bad_original_time"])
def test_zero_floor_never_promotes_unusable_measurements_to_fresh_measured_zero(bad):
    runtime, hass = observed(power_entity="sensor.fictional_hp", power_scope="total")
    attrs, value, reported_age = {"unit_of_measurement": "W"}, -20, 0
    if bad == "nan":
        value = float("nan")
    elif bad == "infinity":
        value = float("-inf")
    elif bad == "boolean":
        value = True
    elif bad == "stale":
        reported_age = 121
    elif bad == "future":
        reported_age = -6
    elif bad == "unit":
        attrs["unit_of_measurement"] = "kWh"
    elif bad in ("restored", "estimated"):
        attrs[bad] = True
    elif bad == "overlap":
        runtime.panasonic.settings["power_entity"] = runtime.settings["grid_entity"]
    elif bad == "huge_negative_w":
        value = -100000.1
    elif bad == "huge_negative_kw":
        value, attrs["unit_of_measurement"] = -100.001, "kW"
    if bad != "missing":
        hass.states.set(runtime.panasonic.settings["power_entity"], value, attrs, reported_age=reported_age)
    if bad == "bad_original_time":
        hass.states.get("sensor.fictional_hp").last_reported = "invalid"
    result = heatpump_power(runtime)
    assert not result["valid"] and not result["complete"] and result["watts"] is None
    assert result["normalized"] is False and result["normalization_reason"] is None
    assert result["measured_wall"] is None
    if bad == "stale":
        assert result["source_watts"] == -20 and result["rejection_reason"] == "stale"
    assert not hass.services.calls


@pytest.mark.parametrize("first,second", list(product((-20, 0, 1400, None), (-10, 0, 600, None))))
def test_split_truth_table_retains_known_parts_but_never_completes_an_unknown_feed(first, second):
    runtime, hass = split(power_supply1_role="main", power_supply2_role="heater")
    for name, value in (("sensor.hp_supply_one", first), ("sensor.hp_supply_two", second)):
        if value is None:
            hass.states.data.pop(name)
        else:
            hass.states.set(name, value, {"unit_of_measurement": "W"})
    result = heatpump_power(runtime)
    complete = first is not None and second is not None
    expected = max(0, first) + max(0, second) if complete else None
    assert result["valid"] is complete and result["complete"] is complete
    assert result["watts"] == expected
    for name, value in (("supply1", first), ("supply2", second)):
        part = result["supplies"][name]
        assert part["watts"] == (max(0, value) if value is not None else None)
        assert part["valid"] is (value is not None)
        assert part["normalized"] is (value is not None and value < 0)
        assert part["source_watts"] == value
    view = runtime.panasonic.overview()
    assert view["power_w"] == expected and view["power_complete"] is complete
    for part, value in zip(view["power_activity"]["supplies"], (first, second)):
        assert part["normalized"] is (value is not None and value < 0)
        assert part["watts"] == (max(0, value) if value is not None else None)
    assert view["compressor_running"] is None and not view["sg_effect_confirmed"]


def test_negative_hp_zero_has_no_solar_credit_and_cannot_reduce_full_future_electrical_envelope():
    runtime, hass = configured(export=1000, reserve=150)
    hass.states.set("sensor.public_hp", -4000, {"unit_of_measurement": "W"})
    budget = sg_solar_budget(runtime)
    assert budget["valid"] and budget["hp_power_w"] == 0 and budget["hp_solar_w"] == 0
    assert budget["available_w"] == budget["eligible_w"] == 850
    assert runtime.sg_boost.settings["expected_power_w"] == 3200
    assert not runtime.sg_dispatch_allowed()
    hass.states.set("sensor.grid", -2699, {"unit_of_measurement": "W"})
    assert not runtime.sg_dispatch_allowed(ignore_solar=True)  # -2699 + full3200 exceeds500.
    hass.states.set("sensor.grid", -2700, {"unit_of_measurement": "W"})
    assert runtime.sg_dispatch_allowed(ignore_solar=True)
    assert not runtime.sg_dispatch_allowed()  # No fictitious HPcredit for threshold.
    assert not hass.services.calls


def test_p1_pv_battery_and_phase_original_signs_are_unaffected_by_hp_zero_floor():
    runtime, hass = configured(export=4000, reserve=0)
    values = {"sensor.grid": -4000, "sensor.public_pv": -50,
              "sensor.fictional_battery": -600, "sensor.fictional_phase": -700}
    for entity, value in values.items():
        hass.states.set(entity, value, {"unit_of_measurement": "W"})
    hass.states.set("sensor.public_hp", -10, {"unit_of_measurement": "W"})
    assert heatpump_power(runtime)["watts"] == 0
    for entity, value in values.items():
        assert runtime._power(entity)[0] == value
    assert not sg_solar_budget(runtime)["valid"]  # NegativePV remains invalid.
    assert not runtime.sg_dispatch_allowed()


@pytest.mark.parametrize("change", ["new_negative", "new_positive", "new_same_value", "same_object_unit",
    "same_object_restored", "same_object_value", "returned_watts", "returned_stamp"])
def test_reentrant_power_read_never_pairs_original_negative_metadata_with_a_different_report(change):
    runtime, hass = observed(power_entity="sensor.fictional_hp", power_scope="total")
    hass.states.set("sensor.fictional_hp", -100, {"unit_of_measurement": "W"})
    old = hass.states.get("sensor.fictional_hp")
    original = runtime._power
    reported = old.last_reported.timestamp()

    def changed_read(entity, stale_s=None):
        if entity != "sensor.fictional_hp":
            return original(entity, stale_s)
        if change in ("new_negative", "new_positive", "new_same_value"):
            value = {"new_negative": -200, "new_positive": 800, "new_same_value": -100}[change]
            hass.states.set(entity, value, {"unit_of_measurement": "W"})
            if change == "new_same_value":
                hass.states.get(entity).last_reported = old.last_reported
        elif change == "same_object_unit":
            old.attributes["unit_of_measurement"] = "kW"
        elif change == "same_object_restored":
            old.attributes["restored"] = True
        elif change == "same_object_value":
            old.state = "400"
        elif change == "returned_watts":
            return -200, reported
        elif change == "returned_stamp":
            return -100, reported + 1
        return original(entity, stale_s)

    runtime._power = changed_read
    result = heatpump_power(runtime)
    assert not result["valid"] and result["watts"] is None
    assert result["rejection_reason"] in ({"source_changed", "unusable_report"} if change == "same_object_restored" else {"source_changed"})
    assert result["source_value"] == "-100" and result["source_watts"] == -100
    assert result["source_reported_wall"] == reported and result["measured_wall"] is None
    assert result["normalized"] is False and result["normalization_reason"] is None


def test_new_zero_policy_does_not_rewrite_existing_unknown_legacy_history():
    model = HeatpumpHistory()
    legacy = tank_source(BASE)
    legacy.update(power_supply1_w=-7, power_supply1_valid=False, power_complete=False,
                  power_supply2_w=0, power_supply2_valid=True)
    observe(model, BASE, p=legacy)
    before = deepcopy(model.snapshot())
    old_point = deepcopy(model.detail(None, BASE)["native_evidence"]["points"][0])
    runtime, hass = split()
    hass.states.set("sensor.hp_supply_one", -7, {"unit_of_measurement": "W"})
    assert heatpump_power(runtime)["watts"] == 0
    for _ in range(3):
        runtime.panasonic.overview()
    assert model.snapshot() == before
    assert model.detail(None, BASE)["native_evidence"]["points"][0] == old_point
    assert old_point["supplies"][0]["watts"] is None
