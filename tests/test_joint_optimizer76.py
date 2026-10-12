"""Safety and counterexample tests for the native joint planning improvement."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math

import pytest

from custom_components.solar_pilot.joint_optimizer import optimize_joint_plan
from custom_components.solar_pilot.unified_planner import DevicePlan, PlannedSlot


def fixture(pv, prices=None, duration=1.0):
    start = datetime(2026, 10, 12, 10, tzinfo=timezone.utc)
    prices = prices or [0.3] * len(pv)
    slots = [PlannedSlot(start + timedelta(hours=i * duration), value, 0.0,
                         prices[i], 0.03) for i, value in enumerate(pv)]
    return slots, {}, [], {"pv_reserve_w": 0, "price_optimisation": True,
                          "early_grid_enabled": True, "capacity_penalty_enabled": False}


def add(slots, plans, devices, device_id, selected, power=1000, grid=True,
        contiguous=False, duration=1.0, **cfg):
    energy = power * len(selected) * duration / 1000
    plan = DevicePlan(device_id, device_id, energy, energy, list(selected), "incumbent",
                      contiguous_cycle=contiguous,
                      cycle_duration_min=len(selected) * duration * 60 if contiguous else 0)
    config = {"id": device_id, "priority": len(devices) * 10,
              "enabled": True, "forecast_deferrable": True,
              "required_kwh": energy, "power_w": power,
              "cheap_grid_allowed": grid, "deadline_grid_allowed": grid,
              "daily_deadline": "23:59:00", "contiguous_cycle": contiguous,
              "cycle_average_w": power,
              "cycle_duration_min": len(selected) * duration * 60 if contiguous else 0,
              **cfg}
    plans[device_id] = plan
    devices.append(config)
    for index in selected:
        slots[index].planned_load_w += power
        slots[index].devices.append(device_id)
    return plan, config


def test_pair_exchange_escapes_a_greedy_trap_no_single_move_improves():
    slots, plans, devices, settings = fixture([2000, 1000])
    add(slots, plans, devices, "small", [0], power=1000, grid=False)
    add(slots, plans, devices, "large", [1], power=2000, grid=False)
    energies = {key: value.planned_kwh for key, value in plans.items()}
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["applied"] and meta["status"] == "best_found"
    assert math.isclose(meta["improvement_eur"], 0.27)
    assert plans["small"].selected_slots == [1]
    assert plans["large"].selected_slots == [0]
    assert {key: value.planned_kwh for key, value in plans.items()} == energies
    assert not meta["global_optimality_proven"]
    assert all(not plan.cheap_grid_slots for plan in plans.values())


def test_fixed_active_cycle_cannot_move_or_lose_committed_energy():
    slots, plans, devices, settings = fixture([0] * 4, [0.5, 0.4, 0.2, 0.1])
    fixed, _ = add(slots, plans, devices, "running", [0, 1], power=500,
                   contiguous=True, fixed_active_cycle=True)
    add(slots, plans, devices, "flex", [0])
    preserved = deepcopy(fixed)
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["applied"]
    assert fixed == preserved
    assert plans["flex"].selected_slots == [3]
    assert slots[0].planned_load_w == slots[1].planned_load_w == 500
    assert "running" in slots[0].devices and "running" in slots[1].devices


def test_contiguous_cycle_uses_whole_block_and_keeps_energy():
    slots, plans, devices, settings = fixture([0] * 5, [0.4, 0.4, 0.1, 0.1, 0.0])
    plan, _ = add(slots, plans, devices, "cycle", [0, 1], power=500,
                  contiguous=True, time_window_enabled=True,
                  time_window_start="10:00:00", time_window_end="14:00:00")
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["applied"]
    assert plan.selected_slots == [2, 3]
    assert plan.planned_kwh == plan.required_kwh == 1.0


def test_deadline_and_window_cover_end_of_slot_not_just_start():
    slots, plans, devices, settings = fixture([0] * 4, [0.5, 0.4, 0.3, 0.0])
    plan, _ = add(slots, plans, devices, "flex", [0], daily_deadline="13:30:00",
                  time_window_enabled=True, time_window_start="10:00:00",
                  time_window_end="14:00:00")
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["applied"]
    assert plan.selected_slots == [2]  # 13:00-14:00 misses the 13:30 deadline.


def test_cheaper_tomorrow_cannot_receive_todays_committed_goal():
    # Horizon starts at 10:00; indexes 14 onward are the following local day.
    prices = [0.4] + [0.5] * 13 + [0.01] * 10
    slots, plans, devices, settings = fixture([0] * 24, prices)
    plan, _ = add(slots, plans, devices, "today", [0])
    before = deepcopy((slots, plans))
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["status"] == "unchanged" and not meta["applied"]
    assert plan.selected_slots == [0] and (slots, plans) == before


def test_multiday_allocation_keeps_each_days_energy_when_improved():
    prices = [0.4, 0.1] + [0.5] * 12 + [0.4, 0.1] + [0.5] * 8
    slots, plans, devices, settings = fixture([0] * 24, prices)
    plan, _ = add(slots, plans, devices, "both_days", [0, 14])
    initial_days = [slots[i].start.date() for i in plan.selected_slots]
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["applied"]
    assert plan.selected_slots == [1, 15]
    assert [slots[i].start.date() for i in plan.selected_slots] == initial_days
    assert plan.planned_kwh == plan.required_kwh == 2


def test_invalid_incumbent_end_coverage_is_left_untouched():
    slots, plans, devices, settings = fixture([0] * 3, [0.4, 0.3, 0.1])
    add(slots, plans, devices, "flex", [1], daily_deadline="11:30:00")
    before = deepcopy((slots, plans))
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["status"] == "fallback" and not meta["applied"]
    assert (slots, plans) == before


def test_missing_forecast_does_not_create_implicit_grid_permission():
    slots, plans, devices, settings = fixture([1000, 5000], [0.3, -0.1])
    slots[1].pv_available = False
    add(slots, plans, devices, "solar", [0], grid=False)
    before = deepcopy((slots, plans))
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert not meta["applied"] and (slots, plans) == before
    assert meta["baseline_objective_eur"] == 0
    devices[0].update(cheap_grid_allowed=True, deadline_grid_allowed=True)
    # Unknown PV contributes zero, even if a stale nonzero numeric value exists.
    slots[1].pv_w = 0
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["applied"] and plans["solar"].selected_slots == [1]
    assert plans["solar"].cheap_grid_slots == [1]


def test_whole_joint_candidate_rechecks_lower_priority_solar_requirement():
    slots, plans, devices, settings = fixture([1000, 1000], [0.3, -1.0])
    add(slots, plans, devices, "grid", [0], grid=True)
    add(slots, plans, devices, "solar", [1], grid=False)
    before = deepcopy((slots, plans))
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert not meta["applied"]
    assert (slots, plans) == before


@pytest.mark.parametrize("defect", ["nan", "membership", "battery", "negative"])
def test_invalid_inputs_fallback_atomically(defect):
    slots, plans, devices, settings = fixture([0, 0], [0.4, 0.1])
    add(slots, plans, devices, "flex", [0])
    if defect == "nan":
        slots[1].import_price = float("nan")
    elif defect == "membership":
        slots[0].devices.clear()
    elif defect == "battery":
        slots[0].battery_w = 100
    else:
        slots[0].planned_load_w = -1
    snapshot = deepcopy((slots, plans))
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["status"] == "fallback" and not meta["applied"]
    # NaN is deliberately not reflexively equal; compare the mutable schedules.
    assert plans == snapshot[1]
    assert [s.devices for s in slots] == [s.devices for s in snapshot[0]]
    assert [s.planned_load_w for s in slots] == [s.planned_load_w for s in snapshot[0]]


def test_budget_is_bounded_and_best_incumbent_is_retained():
    slots, plans, devices, settings = fixture([0] * 4, [0.4, 0.1, 0.3, 0.2])
    add(slots, plans, devices, "flex", [0])
    settings["joint_optimizer_max_evaluations"] = 1
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["status"] == "budget" and meta["evaluations"] == 1
    assert meta["applied"] and plans["flex"].selected_slots == [1]
    assert meta["optimized_objective_eur"] < meta["baseline_objective_eur"]


def test_zero_time_budget_makes_no_changes():
    slots, plans, devices, settings = fixture([0, 0], [0.4, 0.1])
    add(slots, plans, devices, "flex", [0])
    settings["joint_optimizer_time_budget_s"] = 0
    before = deepcopy((slots, plans))
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["status"] == "budget" and meta["evaluations"] == 0
    assert (slots, plans) == before


def test_no_improvement_preserves_every_field():
    slots, plans, devices, settings = fixture([0, 0], [0.1, 0.4])
    add(slots, plans, devices, "flex", [0])
    before = deepcopy((slots, plans))
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["status"] == "unchanged" and meta["improvement_eur"] == 0
    assert (slots, plans) == before


def test_disabled_and_no_goal_devices_stay_fixed():
    slots, plans, devices, settings = fixture([0, 0], [0.4, 0.1])
    add(slots, plans, devices, "disabled", [0], enabled=False)
    plan, _ = add(slots, plans, devices, "no_goal", [0])
    plan.required_kwh = 0
    before = deepcopy((slots, plans))
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["status"] == "unchanged" and (slots, plans) == before


def test_price_optimisation_disabled_retains_existing_preference():
    slots, plans, devices, settings = fixture([0, 0], [0.4, 0.1])
    add(slots, plans, devices, "flex", [0])
    settings["price_optimisation"] = False
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["status"] == "unchanged" and plans["flex"].selected_slots == [0]


def test_injected_commit_failure_restores_all_slot_and_plan_attributes():
    class FailingSlot(PlannedSlot):
        armed = False

        def __setattr__(self, name, value):
            if self.armed and name == "devices":
                raise RuntimeError("Injected assignment failure")
            super().__setattr__(name, value)

    slots, plans, devices, settings = fixture([0, 0], [0.4, 0.1])
    slots[1] = FailingSlot(**vars(slots[1]))
    add(slots, plans, devices, "flex", [0])
    before = deepcopy((slots, plans))
    slots[1].armed = True
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0)
    assert meta["status"] == "fallback" and not meta["applied"]
    assert plans == before[1]
    assert [(s.planned_load_w, s.devices) for s in slots] == [(s.planned_load_w, s.devices) for s in before[0]]


def test_evaluation_limit_is_hard_capped_even_if_setting_requests_more():
    slots, plans, devices, settings = fixture([1000] * 48, [0.3] * 48, duration=0.25)
    add(slots, plans, devices, "left", list(range(12)), duration=0.25)
    add(slots, plans, devices, "right", list(range(12, 24)), duration=0.25)
    settings.update(joint_optimizer_max_evaluations=10**9,
                    joint_optimizer_time_budget_s=10**9)
    meta = optimize_joint_plan(slots, plans, devices, settings, 0.25)
    assert meta["status"] == "budget"
    assert meta["evaluations"] <= 1000


def test_peak_term_is_an_explicit_soft_penalty_not_a_hard_power_limit():
    slots, plans, devices, settings = fixture([0, 0], [0.1, 0.3])
    slots[0].base_w = 2000
    add(slots, plans, devices, "flex", [0])
    settings.update(capacity_penalty_enabled=True, capacity_penalty_eur_kwh=1)
    meta = optimize_joint_plan(slots, plans, devices, settings, 1.0, capacity_target_w=2000)
    assert meta["applied"] and plans["flex"].selected_slots == [1]
    assert meta["objective"] == "net_import_export_cost_plus_soft_peak_penalty"
