"""Synthetic actual-meter evidence for SG solar attribution and priority."""
from datetime import datetime, timezone
from copy import deepcopy
from dataclasses import replace

import pytest

from custom_components.solar_pilot.heatpump_budget import heatpump_power, sg_solar_budget
from test_sg_budget_priority62 import configured


def metered(*, grid=-1000, pv=4000, hp=2000, reserve=0, discharge=0):
    runtime, hass = configured(export=-grid, reserve=reserve)
    hass.states.set("sensor.public_pv", pv, {"unit_of_measurement": "W"})
    hass.states.set("sensor.public_hp", hp, {"unit_of_measurement": "W"})
    if discharge:
        runtime.settings["battery_power_entity"] = "sensor.public_battery"
        hass.states.set("sensor.public_battery", discharge, {"unit_of_measurement": "W"})
    return runtime, hass


def test_running_hp_solar_counts_towards_start_threshold_without_changing_actual_export():
    runtime, _ = metered()
    before = deepcopy(runtime.sg_boost.settings)
    budget = sg_solar_budget(runtime)
    assert budget["valid"]
    assert budget["available_w"] == 1000
    assert budget["hp_power_w"] == budget["hp_solar_w"] == 2000
    assert budget["eligible_w"] == 3000
    # This read neither makes HP consumption owned nor changes a native setpoint.
    assert runtime.sg_boost.settings == before
    assert runtime._dishwasher_comfort_context() == (0.0, "")
    assert runtime.hass.services.calls == []


@pytest.mark.parametrize("grid,pv,hp,discharge,eligible,residual,credit", [
    (500, 4000, 2000, 0, 1500, 0, 1500),
    (500, 4000, 2000, 500, 1000, 0, 1000),
    (-1000, 4000, 2000, 500, 2500, 500, 2000),
    (-1000, 2500, 2000, 500, 2500, 500, 2000),
    (500, 600, 2000, 0, 0, 0, 0),  # HP exceeds the current whole-site load.
    (0, 0, 2000, 0, 0, 0, 0),
    (-10000, 4000, 2000, 0, 4000, 4000, 0),
    (2500, 4000, 2000, 0, 0, 0, 0),
    (-1000, 4000, 0, 0, 1000, 1000, 0),
])
def test_non_solar_energy_is_removed_and_combined_credit_never_exceeds_measured_pv(
        grid, pv, hp, discharge, eligible, residual, credit):
    runtime, _ = metered(grid=grid, pv=pv, hp=hp, discharge=discharge)
    budget = sg_solar_budget(runtime)
    assert budget["eligible_w"] == eligible
    assert budget["available_w"] == residual
    assert budget["hp_solar_w"] == credit
    assert 0 <= credit <= hp
    assert eligible <= pv


def test_house_buffer_and_filtered_grid_remain_without_future_appliance_reserve():
    runtime, _ = metered(reserve=150)
    runtime._dishwasher_comfort_reserve = 200
    runtime.filtered = -500
    budget = sg_solar_budget(runtime)
    assert budget["reserve_w"] == 150
    assert budget["conservative_grid_w"] == -500
    assert budget["available_w"] == 350
    assert budget["eligible_w"] == 2350
    assert budget["hp_solar_w"] == 2000


def test_offline_device_or_future_cycle_peak_does_not_reduce_measured_surplus():
    runtime, hass = metered(reserve=150)
    runtime.states["a"].available = False
    hass.states.set("sensor.load", 700, {"unit_of_measurement": "W"})
    runtime._dishwasher_comfort_reserve = 200
    budget = sg_solar_budget(runtime)
    assert runtime.isolated_reserve_w == 0
    assert budget["reserve_w"] == 150
    assert budget["available_w"] == 850
    assert budget["eligible_w"] == 2850
    assert budget["hp_solar_w"] == 2000


def test_coherent_site_balance_only_counts_pv_left_after_other_actual_loads():
    for pv in (0, 500, 2500):
        for hp in (0, 33, 2000):
            for other in (0, 700, 4000):
                for battery in (0, 500, 3000):
                    grid = hp+other-pv-battery
                    runtime, _ = metered(grid=grid, pv=pv, hp=hp, discharge=battery)
                    budget = sg_solar_budget(runtime)
                    assert budget["valid"]
                    assert budget["eligible_w"] == max(0, pv-other)
                    assert budget["available_w"] == max(0, pv-hp-other)
                    assert 0 <= budget["hp_solar_w"] <= hp


@pytest.mark.parametrize("scope", ["unconfirmed", "supply1", "supply2"])
def test_partial_or_unconfirmed_legacy_meter_never_grants_solar_credit(scope):
    runtime, _ = metered()
    runtime.panasonic.settings["power_scope"] = scope
    assert heatpump_power(runtime)["valid"]
    budget = sg_solar_budget(runtime)
    assert budget["eligible_w"] == budget["available_w"] == 1000
    assert budget["hp_solar_w"] == 0 and budget["hp_power_w"] is None


@pytest.mark.parametrize("value,attrs,age", [
    (-1, {"unit_of_measurement": "W"}, 0),
    (100001, {"unit_of_measurement": "W"}, 0),
    (float("nan"), {"unit_of_measurement": "W"}, 0),
    (float("inf"), {"unit_of_measurement": "W"}, 0),
    ("unavailable", {"unit_of_measurement": "W"}, 0),
    (2000, {"unit_of_measurement": "W"}, 121),
    (2000, {"unit_of_measurement": "W", "estimated": True}, 0),
    (2000, {"unit_of_measurement": "W", "restored": True}, 0),
    (2, {"unit_of_measurement": "kWh"}, 0),
])
def test_rejected_hp_report_never_grants_credit(value, attrs, age):
    runtime, hass = metered()
    hass.states.set("sensor.public_hp", value, attrs, age=age)
    budget = sg_solar_budget(runtime)
    assert budget["valid"] and budget["eligible_w"] == budget["available_w"] == 1000
    assert budget["hp_solar_w"] == 0


@pytest.mark.parametrize("source", ["sensor.grid", "sensor.public_pv", "sensor.public_battery"])
@pytest.mark.parametrize("flag", ["estimated", "is_estimated", "restored"])
def test_explicitly_estimated_or_restored_required_sources_do_not_grant_sg_solar(source, flag):
    runtime, hass = metered(discharge=100)
    obj = hass.states.get(source)
    hass.states.set(source, obj.state, {**obj.attributes, flag: True})
    budget = sg_solar_budget(runtime)
    assert not budget["valid"]
    assert budget["eligible_w"] == budget["available_w"] == budget["hp_solar_w"] == 0


@pytest.mark.parametrize("missing", ["unbound", "absent"])
def test_missing_hp_meter_leaves_real_export_usable_without_extra_credit(missing):
    runtime, hass = metered()
    if missing == "unbound":
        runtime.panasonic.settings["power_entity"] = ""
    else:
        hass.states.data.pop("sensor.public_hp")
    budget = sg_solar_budget(runtime)
    assert budget["valid"] and budget["eligible_w"] == budget["available_w"] == 1000
    assert budget["hp_solar_w"] == 0


def test_sg_age_limit_is_applied_even_if_monitor_accepts_older_hp_report():
    runtime, hass = metered()
    runtime.sg_boost.settings["stale_s"] = 30
    hass.states.set("sensor.public_hp", 2000, {"unit_of_measurement": "W"}, age=60)
    assert heatpump_power(runtime)["complete"]
    budget = sg_solar_budget(runtime)
    assert budget["hp_solar_w"] == 0 and budget["eligible_w"] == 1000


@pytest.mark.parametrize("overlap", ["sensor.grid", "sensor.public_pv", "sensor.load", "sensor.public_ev"])
def test_overlap_with_site_pv_consumer_or_wallbox_cannot_become_hp_solar(overlap):
    runtime, hass = metered()
    runtime.wallbox_settings["power_entity"] = "sensor.public_ev"
    hass.states.set("sensor.public_hp", 2000, {"unit_of_measurement": "W", "source_entity": overlap})
    budget = sg_solar_budget(runtime)
    assert budget["hp_solar_w"] == 0 and budget["eligible_w"] == 1000


def split_metered(runtime, hass, *, confirmed=True, second_age=0, second_value=0):
    runtime.panasonic.settings.update(power_entity="", power_supply1_entity="sensor.public_supply1",
                                      power_supply2_entity="sensor.public_supply2",
                                      split_power_confirmed=confirmed)
    hass.states.set("sensor.public_supply1", 2, {"unit_of_measurement": "kW"})
    hass.states.set("sensor.public_supply2", second_value, {"unit_of_measurement": "W"}, age=second_age)


def test_confirmed_disjoint_split_with_measured_zero_is_a_complete_hp_total():
    runtime, hass = metered()
    split_metered(runtime, hass)
    budget = sg_solar_budget(runtime)
    assert budget["eligible_w"] == 3000 and budget["hp_solar_w"] == 2000


@pytest.mark.parametrize("confirmed,second_age,second_value", [(False, 0, 0), (True, 121, 0), (True, 0, "unavailable")])
def test_split_requires_both_actual_reports_and_local_coverage_confirmation(confirmed, second_age, second_value):
    runtime, hass = metered()
    split_metered(runtime, hass, confirmed=confirmed, second_age=second_age, second_value=second_value)
    budget = sg_solar_budget(runtime)
    assert budget["eligible_w"] == 1000 and budget["hp_solar_w"] == 0


def test_split_overlap_cannot_double_count_one_supply():
    runtime, hass = metered()
    split_metered(runtime, hass, second_value=2000)
    hass.states.set("sensor.public_supply2", 2000,
                    {"unit_of_measurement": "W", "source_entity": "sensor.public_supply1"})
    assert sg_solar_budget(runtime)["hp_solar_w"] == 0


def test_credit_stamp_keeps_actual_hp_report_and_rearm_keeps_separate_export_stamp():
    runtime, hass = metered()
    hass.states.set("sensor.public_hp", 2000, {"unit_of_measurement": "W"}, age=30)
    budget = sg_solar_budget(runtime)
    assert budget["stamp"] == heatpump_power(runtime)["measured_wall"]
    assert budget["residual_stamp"] > budget["stamp"]
    for _ in range(3):
        assert sg_solar_budget(runtime)["stamp"] == budget["stamp"]


def test_already_solar_running_hp_avoids_unnecessary_lower_load_pause():
    runtime, _ = metered()
    runtime.wallbox_guard.reclaimable_w = 9000  # EV reclaim is not this credit.
    assert runtime.priority_board.extra_reclaim_action(100, datetime.now(timezone.utc)) is None
    assert runtime.priority_board.extra_reclaim["state"] == "idle"
    runtime.states["a"].on = runtime.states["a"].owned = False
    assert "a" in runtime.priority_board.extra_start_blocks(100)


def test_higher_load_fitting_actual_export_keeps_priority_even_with_hp_credit():
    runtime, _ = metered(grid=-1200)
    runtime.entry.options["priority_board"]["order"] = ["device:a", "wallbox", "dhw_extra"]
    runtime.states["a"].on = runtime.states["a"].owned = False
    assert runtime.priority_board.sg_priority_allowed(100) is False
    # Existing HP solar is unavailable to another consumer's start threshold.
    runtime, _ = metered(grid=-500)
    runtime.entry.options["priority_board"]["order"] = ["device:a", "wallbox", "dhw_extra"]
    runtime.states["a"].on = runtime.states["a"].owned = False
    assert sg_solar_budget(runtime)["eligible_w"] == 2500
    assert runtime.priority_board.sg_priority_allowed(100) is True


def test_prospective_lower_pause_first_pays_import_instead_of_adding_clipped_watts():
    runtime, _ = metered(grid=1000, hp=0)
    runtime.sg_boost.settings.update(threshold_w=1000, expected_power_w=100)
    # A 1 kW OFF proposal would only cancel the present 1 kW import.
    assert runtime.priority_board._extra_candidates(100) == [("a", 1000)]
    assert runtime.priority_board.extra_reclaim_action(100, datetime.now(timezone.utc)) is None
    assert runtime.priority_board.extra_reclaim["state"] == "idle"


def test_lower_reclaim_cannot_borrow_active_wallbox_reserved_power():
    runtime, _ = metered(grid=-2000, hp=0)
    runtime.wallbox_settings["enabled"] = True
    runtime.sg_wallbox_guard.result = replace(runtime.sg_wallbox_guard.result,
                                             block_increase=False, max_increase_w=2000)
    assert runtime.priority_board.extra_reclaim_action(100, datetime.now(timezone.utc)) is None
    assert runtime.priority_board.extra_reclaim["state"] == "idle"
    assert "Wallbox" in runtime.priority_board.extra_reclaim["reason"]


def test_expected_total_hp_draw_deducts_only_its_complete_current_measurement():
    runtime, _ = metered(grid=-1000)
    assert sg_solar_budget(runtime)["eligible_w"] == runtime.sg_boost.settings["threshold_w"]
    # 3.2 kW total minus the already measured 2 kW leaves a 1.2 kW increase.
    allowed, _ = runtime.heat_pump_increase_allowed()
    assert allowed  # -1 kW + 1.2 kW fits the unchanged 0.5 kW import limit.
