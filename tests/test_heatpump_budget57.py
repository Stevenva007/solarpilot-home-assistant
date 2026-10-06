"""One shared heat-pump meter and current-source power-budget regressions."""
from types import SimpleNamespace as NS
import time

import pytest

from custom_components.solar_pilot.heatpump_budget import (
    climate_solar_budget, heatpump_power, heatpump_shared, shared_commitment,
)
from test_runtime import build


def setup(*, grid=-3000, pv=5000, hp=0, reserve=150):
    runtime, hass = build(settings={"pv_entity": "sensor.pv", "reserve_w": reserve})
    hass.states.set("sensor.grid", grid, {"unit_of_measurement": "W"})
    hass.states.set("sensor.pv", pv, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp", hp, {"unit_of_measurement": "W"})
    runtime.dhw.config.update(target_entity="water_heater.tank", power_entity="sensor.hp")
    runtime.smart_climate.settings.update(zone_entities=["climate.room_a", "climate.room_b"])
    runtime.filtered = grid
    return runtime, hass


def test_current_export_counts_all_heatpump_consumption_once():
    runtime, _ = setup(grid=-700, hp=2400)
    budget = climate_solar_budget(runtime)
    assert budget["valid"]
    assert budget["available_w"] == budget["residual_w"] == 550
    assert budget["compensated_w"] == 2950
    assert budget["heatpump_w"] == 2400
    assert budget["heatpump_meter_valid"]


def test_start_threshold_has_no_credit_for_existing_hp_draw():
    runtime, _ = setup(grid=-2000, hp=3000)
    budget = climate_solar_budget(runtime)
    assert budget["available_w"] < 2500
    assert budget["compensated_w"] == 4850
    assert not runtime.hass.services.calls


def test_no_separate_zone_additions_or_forecast_credit():
    runtime, _ = setup(grid=-500, hp=2000)
    runtime.smart_climate.settings.update(zone_entities=[f"climate.room_{i}" for i in range(10)])
    runtime.heatpump_learning = NS(samples={"tapwater_heating": [9000], "space_heating": [9000]})
    assert climate_solar_budget(runtime)["compensated_w"] == 2350


def test_pv_caps_both_actual_and_compensated_power():
    runtime, _ = setup(grid=-7000, pv=2500, hp=4500)
    budget = climate_solar_budget(runtime)
    assert budget["available_w"] == budget["compensated_w"] == 2350
    assert budget["solar_ceiling_w"] == 2350


def test_battery_export_is_excluded_before_one_shared_meter_addback():
    runtime, hass = setup(grid=-3500, pv=5000, hp=2000)
    runtime.settings.update(battery_power_entity="sensor.battery", battery_sign="discharge_positive")
    hass.states.set("sensor.battery", 1000, {"unit_of_measurement": "W"})
    budget = climate_solar_budget(runtime)
    assert budget["available_w"] == 2350
    assert budget["compensated_w"] == 4350


def test_reserves_and_filtered_worst_case_applied_to_every_pool():
    runtime, _ = setup(grid=-4000, hp=2000)
    runtime.filtered = -3000
    runtime._dishwasher_comfort_reserve = 700
    # Use an isolated source journal to exercise the actual computed property.
    runtime.recovery["a"] = {"reason": "source unavailable"}
    runtime.states["a"].owned = True
    runtime.states["a"].on = True
    runtime.states["a"].target_w = 1000
    runtime.hass.states.data.pop("switch.load")
    budget = climate_solar_budget(runtime)
    isolated = runtime.isolated_reserve_w
    assert isolated > 0
    assert budget["available_w"] == max(0, 3000 - 150 - 700 - isolated)
    assert budget["compensated_w"] == max(0, 5000 - 150 - 700 - isolated)


def test_same_hp_future_reservation_is_not_deducted_from_its_own_pool_twice():
    runtime, _ = setup(grid=-500, hp=2000, reserve=0)
    runtime._dishwasher_comfort_reserve = 1200
    runtime._shared_heatpump_comfort_reserve_w = 1200
    budget = climate_solar_budget(runtime)
    assert budget["available_w"] == 500
    assert budget["compensated_w"] == 2500
    assert budget["shared_heatpump_reserve_w"] == 1200
    assert budget["protected_reserve_w"] == 0
    # Additional dishwasher demand is a genuinely separate physical appliance.
    runtime._dishwasher_comfort_reserve = 2200
    assert climate_solar_budget(runtime)["compensated_w"] == 1500


def test_invalid_shared_reserve_cannot_cancel_other_appliance_reservations():
    runtime, _ = setup()
    runtime._dishwasher_comfort_reserve = 1200
    runtime._shared_heatpump_comfort_reserve_w = 1500
    assert not climate_solar_budget(runtime)["valid"]


@pytest.mark.parametrize("source", ["sensor.grid", "sensor.pv", "sensor.battery"])
@pytest.mark.parametrize("failure", ["missing", "stale", "restored", "wrong_unit", "nan"])
def test_unreliable_site_inputs_fail_closed(source, failure):
    runtime, hass = setup()
    runtime.settings.update(battery_power_entity="sensor.battery", battery_sign="discharge_positive")
    hass.states.set("sensor.battery", 0, {"unit_of_measurement": "W"})
    if failure == "missing":
        hass.states.data.pop(source)
    elif failure == "stale":
        hass.states.set(source, -3000 if source == "sensor.grid" else 5000,
                        {"unit_of_measurement": "W"}, reported_age=1000)
    elif failure == "restored":
        hass.states.get(source).attributes["restored"] = True
    elif failure == "wrong_unit":
        hass.states.get(source).attributes["unit_of_measurement"] = "kWh"
    else:
        hass.states.get(source).state = "nan"
    budget = climate_solar_budget(runtime)
    assert not budget["valid"]
    assert budget["available_w"] == budget["compensated_w"] == 0


@pytest.mark.parametrize("failure", ["missing", "stale", "restored", "estimated", "negative", "nan"])
def test_unreliable_hp_meter_grants_no_addback_but_does_not_discard_export(failure):
    runtime, hass = setup(grid=-3000, hp=2000)
    if failure == "missing":
        hass.states.data.pop("sensor.hp")
    elif failure == "stale":
        hass.states.set("sensor.hp", 2000, {"unit_of_measurement": "W"}, reported_age=500)
    elif failure in ("restored", "estimated"):
        hass.states.get("sensor.hp").attributes[failure] = True
    else:
        hass.states.get("sensor.hp").state = "-1" if failure == "negative" else "nan"
    budget = climate_solar_budget(runtime)
    assert budget["valid"] and not budget["heatpump_meter_valid"]
    assert budget["available_w"] == budget["compensated_w"] == 2850


@pytest.mark.parametrize("role", ["grid", "export", "pv", "battery", "ordinary", "wallbox", "fleet"])
def test_overlapping_physical_meter_is_never_added_back(role):
    runtime, _ = setup(hp=2000)
    if role in ("grid", "export", "pv", "battery"):
        runtime.settings[{"grid": "grid_entity", "export": "export_entity", "pv": "pv_entity",
                          "battery": "battery_power_entity"}[role]] = "sensor.hp"
    elif role == "ordinary":
        runtime.configs["a"]["power_entity"] = "sensor.hp"
    elif role == "wallbox":
        runtime.wallbox_settings["power_entity"] = "sensor.hp"
    else:
        runtime.battery_fleet.configs["b"] = {"power_entity": "sensor.hp"}
    assert not heatpump_power(runtime)["valid"]


def test_disabled_control_does_not_change_physical_meter_scope():
    runtime, _ = setup()
    runtime.smart_climate.settings.update(enabled=False, control_enabled=False)
    assert heatpump_shared(runtime)
    runtime.smart_climate.settings["zone_entities"] = []
    assert not heatpump_shared(runtime)


def test_shared_tank_only_meter_is_not_a_total_heatpump_power_credit():
    runtime, _ = setup(hp=2000)
    runtime.dhw.config["power_meter_scope"] = "tank"
    assert heatpump_shared(runtime)
    assert not heatpump_power(runtime)["valid"]
    assert climate_solar_budget(runtime)["compensated_w"] == 2850
    runtime.smart_climate.settings["zone_entities"] = []
    assert heatpump_power(runtime)["valid"]


def test_unrecognized_meter_scope_is_not_inferred_from_an_entity_name():
    runtime, _ = setup(hp=2000)
    runtime.dhw.config["power_meter_scope"] = "unknown"
    assert not heatpump_power(runtime)["valid"]


def test_meter_timestamp_is_independent_from_value_change_time():
    runtime, hass = setup(hp=2300)
    hass.states.set("sensor.hp", 2300, {"unit_of_measurement": "W"}, age=86400, reported_age=2)
    hp = heatpump_power(runtime)
    assert hp["valid"] and hp["watts"] == 2300


def test_budget_proves_p1_and_pv_individually_after_a_command():
    runtime, hass = setup()
    hass.states.set("sensor.pv", 5000, {"unit_of_measurement": "W"}, reported_age=25)
    command_wall = time.time() - 5
    budget = climate_solar_budget(runtime)
    assert budget["valid"] and budget["measured_wall"] < command_wall
    assert hass.states.get("sensor.grid").last_reported.timestamp() > command_wall


def test_shared_commitment_counts_the_same_appliance_once():
    assert shared_commitment(3200, 3200, 2000) == 1200
    assert shared_commitment(3200, 2500, 2000) == 1200
    assert shared_commitment(0, 3200, 2000) == 1200
    assert shared_commitment(3200, 3200, 4000) == 0
    assert shared_commitment(3200, 3200) == 3200


@pytest.mark.parametrize("value", [-1, True, "3200", float("inf"), float("nan"), None])
def test_bad_planned_commitment_is_not_interpreted_as_free_capacity(value):
    with pytest.raises(ValueError):
        shared_commitment(value, 3200, 2000)
    with pytest.raises(ValueError):
        shared_commitment(3200, value, 2000)


@pytest.mark.parametrize("value", [-1, True, "3200", float("inf"), float("nan")])
def test_bad_measured_draw_preserves_full_shared_reservation(value):
    assert shared_commitment(3200, 2500, value) == 3200


def test_invalid_filter_or_reserve_never_manufactures_headroom():
    runtime, _ = setup()
    runtime.filtered = float("nan")
    assert not climate_solar_budget(runtime)["valid"]
    runtime.filtered = None
    assert climate_solar_budget(runtime)["valid"]
    runtime._dishwasher_comfort_reserve = -1
    assert not climate_solar_budget(runtime)["valid"]
