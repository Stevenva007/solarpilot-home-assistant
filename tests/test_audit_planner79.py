"""Fictitious regressions for the full planner/learning code audit."""
from datetime import datetime, timezone
import pytest

from custom_components.solar_pilot.cycle_learning import CycleEnergyModel
from custom_components.solar_pilot.battery_analysis import BatteryOpportunitySimulator
from custom_components.solar_pilot.electricity_cost import DailyElectricityCost
from custom_components.solar_pilot.ems import accounting_step
from custom_components.solar_pilot.learning import LocalLearning, fingerprint
from custom_components.solar_pilot.phase_learning import PhaseLearning
from custom_components.solar_pilot.pv_model import LocalPVModel
from custom_components.solar_pilot.pv_calibration import PVCalibration
from custom_components.solar_pilot.pv_forecast_source import PV_FORECAST_DEFAULTS
from custom_components.solar_pilot.savings import SavingsHistory
from custom_components.solar_pilot.unified_planner import UnifiedPlanner
from custom_components.solar_pilot.unified_planner import PlannedSlot, DevicePlan
from custom_components.solar_pilot.joint_optimizer import optimize_joint_plan
from datetime import timedelta


NOW = datetime(2026, 10, 12, 10, tzinfo=timezone.utc)


def planner(**settings):
    return UnifiedPlanner({"horizon_h": 6, "slot_min": 15, "joint_optimisation": False,
                           "early_grid_enabled": True, "capacity_penalty_enabled": False,
                           **settings})


def device(**settings):
    return {"id": "fixture", "forecast_deferrable": True, "required_kwh": .25,
            "power_w": 1000, "daily_deadline": "18:00:00",
            "cheap_grid_allowed": True, "deadline_grid_allowed": True, **settings}


def build(model, cfg, prices=None):
    return model.build(local_now=NOW, pv_hourly_w=[0] * 6,
                       import_prices=prices or [.3] * 24, export_prices=[.03] * 24,
                       devices=[cfg])


def test_baseline_slot_must_fit_whole_time_window():
    plan = build(planner(), device(time_window_enabled=True,
                                  time_window_start="10:00:00", time_window_end="10:05:00"))
    assert plan.devices["fixture"].selected_slots == []


def test_baseline_slot_must_finish_by_daily_goal_deadline():
    plan = build(planner(), device(daily_deadline="10:00:00"))
    assert plan.devices["fixture"].selected_slots == []


def test_price_disabled_applies_to_contiguous_cycles_too():
    cfg = device(contiguous_cycle=True, cycle_duration_min=15, cycle_average_w=1000)
    prices = [.9, -.9] + [.9] * 22
    plan = build(planner(price_optimisation=False), cfg, prices)
    assert plan.devices["fixture"].selected_slots == [0]


def test_power_guard_cannot_use_old_binding_before_next_meter_sample():
    model = LocalLearning()
    old = {"power_entity": "sensor.fixture_old", "nominal_w": 1000}
    model.profiles["fixture"] = {"fingerprint": fingerprint(old), "watts": [2000] * 12}
    rebound = {**old, "power_entity": "sensor.fixture_rebound"}
    assert model.conservative_power("fixture", rebound) == 1000


def test_passive_phase_change_requires_all_previous_meters_still_present():
    model = PhaseLearning({"learning_min_delta_w": 200})
    model.observe(now=100, day="2026-10-12", phase_values=(0, 0, 0),
                  device_powers={"fixture_a": 0, "fixture_b": 0})
    model.observe(now=110, day="2026-10-12", phase_values=(300, 1000, 0),
                  device_powers={"fixture_a": 1000})
    assert model.profile("fixture_a")["samples"] == 0


def test_partial_meter_coverage_cannot_become_a_complete_cycle():
    model = CycleEnergyModel()
    model.begin("fixture", "Eco", 1000, "2026-10-12")
    model.observe("fixture", 1000, 120)
    model.observe("fixture", 1000, 120)
    assert model.finish("fixture", 1000 + 3 * 3600) is None


def test_cycle_restore_is_bounded_and_skips_malformed_neighbours():
    model = CycleEnergyModel()
    valid = {"day": "2026-10-12", "energy_kwh": 1, "duration_min": 60, "peak_w": 2000}
    model.restore({"profiles": {"fixture": {"Eco": [None, valid], "invalid": None},
                                "invalid_device": []}, "accepted": "broken"})
    assert model.estimate("fixture", "Eco").energy_kwh == 1
    assert model.estimate("fixture", "invalid").cycles == 0
    assert model.estimate("invalid_device").cycles == 0


def test_local_learning_restore_skips_malformed_fields_and_keeps_valid_profile():
    model = LocalLearning()
    cfg = {"nominal_w": 1000, "power_entity": "sensor.fixture"}
    model.restore({"responses_s": None, "report_intervals_s": [], "successes": "broken",
                   "profiles": {"fixture": {"fingerprint": fingerprint(cfg), "watts": [1000, True]}}},
                  {"fixture": cfg})
    assert model.overview(30)["profiles"]["fixture"]["samples"] == 1


def test_legacy_pv_restore_skips_bad_shapes_and_bounds_valid_days():
    model = LocalPVModel()
    model.restore({"bins": {"180:30": {"days": {"2026-10-12": [.7, True],
                                                 "2026-10-11": None}},
                            "broken": {"days": []}}, "samples": "broken"})
    assert model.bins["180:30"]["days"] == {"2026-10-12": [.7]}


def test_battery_what_if_restore_rejects_nonfinite_state_without_startup_failure():
    model = BatteryOpportunitySimulator()
    key = next(iter(model.scenarios))
    model.restore({"scenarios": {key: {"soc_kwh": "broken", "live_avoided_import_kwh": float("inf")}},
                   "live_seconds": "broken", "live_import_kwh": float("inf")})
    row = next(x for x in model.overview()["scenarios"] if x["id"] == key)
    assert row["soc_kwh_virtual"] == 0 and row["live_avoided_import_kwh"] == 0
    assert model.live_import_kwh == 0


def test_passive_phase_event_rejects_combined_other_meter_changes():
    model = PhaseLearning({"learning_min_delta_w": 250})
    model.observe(now=100, day="2026-10-12", phase_values=(0, 0, 0),
                  device_powers={"fixture_a": 0, "fixture_b": 0, "fixture_c": 0})
    model.observe(now=110, day="2026-10-12", phase_values=(1000, 400, 0),
                  device_powers={"fixture_a": 1000, "fixture_b": 200, "fixture_c": 200})
    assert model.profile("fixture_a")["samples"] == 0


def test_managed_solar_attribution_is_bounded_by_actual_available_production():
    row = accounting_step({}, day="2026-10-12", dt_s=60, grid_w=500, pv_w=0,
                          managed_w=2000, import_price_eur_kwh=.3, export_price_eur_kwh=.03)
    assert row["managed_solar_kwh"] == 0
    assert row["estimated_value_eur"] == 0
    assert row["managed_unattributed_kwh"] == 1500 * 60 / 3_600_000


def test_direct_pv_cost_integration_splits_zero_self_use_crossing():
    model = DailyElectricityCost()
    model.update(now=NOW, grid_w=-1000, pv_w=0, import_price=.3, export_price=.03)
    end = NOW.replace(minute=1)
    row = model.update(now=end, grid_w=-500, pv_w=1000, import_price=.3, export_price=.03)
    # Direct PV rises from a physically inconsistent negative residual to +500W.
    # Count only its positive final 20s triangle; missing consistency is not PV.
    assert abs(row["direct_pv_kwh"] - 500 * 20 / 2 / 3_600_000) < .000001


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["grid", "soc", "power_unavailable", "pause", "close", "strategy", "net_permission"])
async def test_battery_native_context_changed_during_intent_save_blocks_dispatch(change):
    from test_battery_runtime import setup_battery
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    runtime.mode = "solar"
    native_save = runtime.store.async_save
    altered = False

    async def save(payload):
        nonlocal altered
        await native_save(payload)
        if altered:
            return
        altered = True
        if change == "grid":
            hass.states.set("sensor.grid", 2000, {"unit_of_measurement": "W"})
        elif change == "soc":
            hass.states.set("sensor.bat_soc", 99, {"unit_of_measurement": "%"})
        elif change == "power_unavailable":
            hass.states.set("sensor.bat_power", "unavailable", {"unit_of_measurement": "W"})
        elif change == "pause":
            runtime.mode = "paused"
        elif change == "strategy":
            runtime.battery_fleet.settings["strategy"] = "advisory"
        elif change == "net_permission":
            runtime.battery_fleet.settings["allow_grid_charge"] = True
        else:
            runtime._closed = True

    runtime.store.async_save = save
    sent = await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    assert not sent
    assert hass.services.calls == []
    assert runtime.battery_fleet.state.pending is None
    assert not runtime.battery_fleet.state.faults


@pytest.mark.asyncio
async def test_known_unsent_battery_intent_can_be_reassessed_without_replaying_old_target():
    from test_battery_runtime import setup_battery
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    runtime.mode = "solar"
    native_save = runtime.store.async_save
    changed = False

    async def save(payload):
        nonlocal changed
        await native_save(payload)
        if not changed:
            changed = True
            hass.states.set("sensor.grid", 2000, {"unit_of_measurement": "W"})

    runtime.store.async_save = save
    assert not await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    assert runtime.battery_fleet.state.last_command_mono is None
    assert await runtime.battery_fleet.tick(grid_w=2000, allow_command=True)
    assert hass.services.calls == [("number", "set_value",
                                   {"entity_id": "number.bat_setpoint", "value": 1900.0})]


@pytest.mark.asyncio
async def test_battery_equal_native_heartbeat_is_allowed_and_neutral_release_needs_no_pv():
    from test_battery_runtime import setup_battery
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    native_save = runtime.store.async_save

    async def save(payload):
        await native_save(payload)
        obj = hass.states.get("sensor.grid")
        hass.states.set("sensor.grid", obj.state, obj.attributes)

    runtime.store.async_save = save
    assert await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    runtime.battery_fleet.state.pending = None
    hass.states.set("sensor.grid", "unavailable", {"unit_of_measurement": "W"})
    runtime.mode = "paused"
    assert await runtime.battery_fleet._send("bat1", 0)
    assert hass.services.calls[-1][2]["value"] == 0


def test_baseline_grid_slot_classification_accounts_for_prior_device_allocations():
    model = planner()
    cfgs = [device(id="fixture_a", priority=1), device(id="fixture_b", priority=2)]
    plan = model.build(local_now=NOW, pv_hourly_w=[1600] * 6,
                       import_prices=[-.9] + [.3] * 23, export_prices=[.03] * 24,
                       devices=cfgs)
    assert plan.devices["fixture_a"].selected_slots == [0]
    assert plan.devices["fixture_b"].selected_slots == [0]
    assert plan.devices["fixture_b"].cheap_grid_slots == [0]


def test_joint_grid_classification_uses_same_low_power_solar_threshold_as_baseline():
    slots = [PlannedSlot(NOW + timedelta(minutes=15*i), 270, 0, price, .03)
             for i, price in enumerate([.9, -.9])]
    slots[0].planned_load_w = 300
    slots[0].devices = ["fixture"]
    plans = {"fixture": DevicePlan("fixture", "Fictief", .075, .075, [0], "fixture", [0])}
    cfg = device(power_w=300, required_kwh=.075)
    result = optimize_joint_plan(slots, plans, [cfg], {"early_grid_enabled": True, "pv_reserve_w": 150}, .25)
    assert result["applied"]
    assert plans["fixture"].selected_slots == [1]
    assert plans["fixture"].cheap_grid_slots == [1]


@pytest.mark.parametrize("version", [2, 99, True])
def test_unsupported_cost_schema_is_opaque_and_preserved_across_live_updates(version):
    model = DailyElectricityCost()
    payload = {"version": version, "data": {"date": "2026-10-12", "coverage_s": 120,
               "import_kwh": 99, "import_cost_eur": 999}, "future_field": ["opaque"]}
    model.restore(payload)
    assert model.overview(NOW)["net_cost_eur"] is None
    assert model.overview(NOW)["import_kwh"] is None
    model.update(now=NOW, grid_w=1000, pv_w=0, import_price=.3, export_price=.03)
    model.update(now=NOW + timedelta(minutes=1), grid_w=1000, pv_w=0, import_price=.3, export_price=.03)
    assert model.snapshot() == payload
    snapshot = model.snapshot()
    snapshot["future_field"].append("caller mutation")
    assert model.snapshot() == payload


@pytest.mark.parametrize("version", [2, 99, True])
def test_unsupported_pv_schema_is_not_applied_or_replaced_with_current_empty_schema(version):
    model = PVCalibration(dict(PV_FORECAST_DEFAULTS))
    payload = {"version": version, "binding": "fixture", "bins": {
        "4:clock:40": {"factor": .5, "days": {f"2026-10-{day:02d}": [.5] for day in range(1, 9)}}},
        "future_field": ["opaque"]}
    model.restore(payload)
    assert model.factor(NOW)[0] == 1
    model.observe(now=NOW, actual_w=1000, raw_w=2000, meter_stamp=NOW.timestamp(), binding="fixture")
    assert model.snapshot() == payload


@pytest.mark.parametrize("version", [2, 99, True])
def test_unsupported_savings_schema_preserves_history_without_using_its_records(version):
    model = SavingsHistory()
    payload = {"version": version, "records": [{"date": "2026-10-12", "automatic": {
        "coverage_s": 120, "priced_s": 120, "estimated_value_eur": 999}}], "future": ["opaque"]}
    model.restore(payload)
    assert model.report(current_date="2026-10-12")["today"]["estimated_benefit_eur"] is None
    model.capture({"date": "2026-10-12", "samples_s": 60, "managed_kwh": 1})
    assert model.snapshot() == payload


def test_absent_first_install_snapshots_allow_normal_new_model_persistence():
    for model in (DailyElectricityCost(), PVCalibration(dict(PV_FORECAST_DEFAULTS)), SavingsHistory()):
        model.restore({})
        assert model.snapshot()["version"] == 1

