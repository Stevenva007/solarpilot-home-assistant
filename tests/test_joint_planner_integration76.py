"""Counterfactual integration checks on identical, fictitious forecasts."""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from custom_components.solar_pilot import unified_planner as module
from custom_components.solar_pilot.unified_planner import UnifiedPlanner

NOW = datetime(2026, 10, 12, 10, tzinfo=timezone.utc)
SEED = {'base_load_profile': {'median_w_by_hour': {str(h): 500 for h in range(24)}}}
DEVICES = [dict(id=name, name=name, priority=priority, enabled=True,
                forecast_deferrable=True, required_kwh=power/1000, power_w=power,
                daily_deadline='23:59:00', cheap_grid_allowed=False,
                deadline_grid_allowed=False, time_window_enabled=False)
           for name, priority, power in [('small', 10, 1000), ('large', 20, 2000)]]


def build(joint=True, **inputs):
    planner = UnifiedPlanner(dict(horizon_h=6, slot_min=60, pv_reserve_w=0,
                                  joint_optimisation=joint, capacity_penalty_enabled=False), SEED)
    plan = planner.build(local_now=NOW, pv_hourly_w=[2500, 1500, 0, 0, 0, 0],
                         import_prices=[.3]*6, export_prices=[.03]*6,
                         devices=deepcopy(DEVICES), **inputs)
    return planner, plan


def test_builtin_joint_search_improves_actual_legacy_greedy_plan():
    _, baseline = build(False)
    _, improved = build(True)
    assert baseline.devices['small'].selected_slots == [0]
    assert baseline.devices['large'].selected_slots == [0]
    assert improved.devices['small'].selected_slots == [1]
    assert improved.devices['large'].selected_slots == [0]
    assert improved.predicted_cost_eur == pytest.approx(baseline.predicted_cost_eur - .27)
    assert {key: p.planned_kwh for key, p in improved.devices.items()} == {
        key: p.planned_kwh for key, p in baseline.devices.items()}
    assert improved.optimisation['applied']
    assert improved.optimisation['global_optimality_proven'] is False
    json.dumps(improved.overview())


def test_optimizer_failure_preserves_legacy_feasible_plan(monkeypatch):
    _, baseline = build(False)
    def failure(*args):
        raise RuntimeError('fictitious advisory error')
    monkeypatch.setattr(module, 'optimize_joint_plan', failure)
    _, fallback = build(True)
    assert fallback.optimisation['status'] == 'fallback'
    assert fallback.slots == baseline.slots
    assert fallback.devices == baseline.devices
    assert fallback.predicted_cost_eur == baseline.predicted_cost_eur


def test_battery_projection_cannot_use_later_solar_for_first_slot():
    planner = UnifiedPlanner(dict(horizon_h=6, slot_min=60, pv_reserve_w=0), SEED)
    plan = planner.build(local_now=NOW, pv_hourly_w=[0, 2500, 0, 0, 0, 0],
                         import_prices=[.3]*6, export_prices=[.03]*6, devices=[],
                         battery=dict(available_kwh=10, soc_pct=20, min_soc_pct=20,
                                      max_soc_pct=95, charge_power_w=2000,
                                      discharge_power_w=2000, round_trip_efficiency=.8))
    assert plan.slots[0].battery_w == 0
    assert plan.slots[1].battery_w > 0
    assert plan.slots[2].battery_w < 0
    assert plan.battery_advice['round_trip_efficiency'] == .8
    assert len(plan.battery_advice['soc_trajectory']) == len(plan.slots)
    assert plan.battery_advice['globally_optimal'] is False
