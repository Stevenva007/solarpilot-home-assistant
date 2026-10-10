"""Start explanation must expose real conservative allocation, not raw export.

These are pure engine/adapter doubles. No physical consumer, Wallbox or heat
pump is started and no native Panasonic operating mode is changed.
"""
from datetime import datetime
import time

import pytest

from custom_components.solar_pilot.engine import Device, Site, State, plan
from test_runtime import build

def load(identifier="dry", **kw):
    return Device(id=identifier, name="Ontvochtiger", nominal_w=321,
                  min_on_s=0, min_off_s=0, start_delay_s=0,
                  stop_delay_s=0, start_margin_w=100, **kw)

def site(*, grid=-5370, filtered=None, comfort=0, **kw):
    return Site(now=1000, grid_w=grid, filtered_grid_w=grid if filtered is None else filtered,
                reserve_w=150, comfort_reserve_w=comfort, **kw)

def running_wash():
    device = Device(id="wash", kind="dishwasher", priority=1, nominal_w=2000,
                    non_interruptible=True)
    state = State(owned=True, on=True, measured_w=2000, target_w=2000, last_on=0)
    return device, state

def test_5220_free_export_is_only_20_start_watts_after_5200_protected_reservation():
    wash, active = running_wash()
    dry = load()
    result = plan(site(comfort=5200), [wash, dry], {"wash": active, "dry": State()})
    allocation = result.start_power["dry"]
    assert result.free_w == 5220
    assert allocation["filtered_free_w"] == 5220
    assert allocation["comfort_and_cycle_reserve_w"] == 5200
    assert allocation["available_w"] == 20
    assert allocation["required_w"] == 421
    assert not allocation["sufficient"] and not allocation["grid_allowed"]
    assert result.action is None
    assert result.reasons["dry"] == "Wacht op vermogen / hogere prioriteit"
    assert result.targets["wash"] == 2000  # Protected wash cannot be sacrificed.

def test_confirmed_no_future_boiler_reserve_can_leave_room_without_stopping_wash():
    wash, active = running_wash()
    result = plan(site(comfort=2000), [wash, load()], {"wash": active, "dry": State()})
    assert result.start_power["dry"]["available_w"] == 3220
    assert result.start_power["dry"]["sufficient"]
    assert result.action.id == "dry" and result.action.watts == 321
    assert result.targets["wash"] == 2000

@pytest.mark.parametrize("raw,filtered", [(-5370, -450), (-450, -8150)])
def test_filtered_and_raw_readings_use_the_more_conservative_export(raw, filtered):
    result = plan(site(grid=raw, filtered=filtered), [load()], {"dry": State()})
    assert result.start_power["dry"]["available_w"] == 300
    assert result.start_power["dry"]["filtered_free_w"] == 300
    assert result.start_power["dry"]["required_w"] == 421
    assert not result.start_power["dry"]["sufficient"]
    assert result.action is None

def test_battery_discharge_is_removed_before_claiming_available_solar():
    result = plan(site(grid=-950, battery_discharge_w=500), [load()], {"dry": State()})
    assert result.free_w == 300
    assert result.start_power["dry"]["available_w"] == 300
    assert not result.start_power["dry"]["sufficient"]

def test_grid_boost_is_a_separate_basis_not_solar_or_start_margin_credit():
    result = plan(site(grid=0), [load()], {"dry": State(boost_until=2000)})
    allocation = result.start_power["dry"]
    assert result.free_w == 0
    assert allocation["grid_allowed"]
    assert allocation["required_w"] == 321  # No solar start margin for authorised boost.
    assert allocation["sufficient"]
    assert result.action.id == "dry"

def test_grid_boost_still_respects_reserved_physical_headroom():
    result = plan(site(grid=0, comfort=3200, max_import_w=3200), [load()],
                  {"dry": State(boost_until=2000)})
    assert result.start_power["dry"]["grid_allowed"]
    assert result.start_power["dry"]["available_w"] == 0
    assert not result.start_power["dry"]["sufficient"]
    assert result.action is None

def test_lower_priority_without_wallbox_permission_does_not_see_ev_credit():
    result = plan(site(grid=-250, reclaimable_w=3000, no_reclaim_ids={"dry"}),
                  [load(allow_wallbox_reclaim=True, priority_reclaim=True)], {"dry": State()})
    assert result.start_power["dry"]["available_w"] == 100
    assert not result.start_power["dry"]["sufficient"]
    assert result.action is None

def test_available_allocation_is_not_a_start_guarantee_when_other_guard_blocks():
    result = plan(site(can_increase=False, increase_reason="Wacht op verse fasecontrole"),
                  [load()], {"dry": State()})
    assert result.start_power["dry"]["sufficient"]
    assert result.action is None
    assert result.reasons["dry"] == "Wacht op verse fasecontrole"

def test_runtime_lists_power_shortage_even_when_all_nonpower_requirements_met():
    runtime, _ = build(device={"nominal_w": 321, "start_margin_w": 100})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    state = runtime.states["a"]
    state.observed_once = True
    state.last_off = -1e12  # Match the pure planner clock, not runtime monotonic time.
    wash, active = running_wash()
    dry = load("a")
    runtime.result = plan(site(comfort=5200), [wash, dry], {"wash": active, "a": state})
    runtime._start_context = {"measurement_valid": True, "can_increase": True,
                              "effective_import_limit_w": 3500}
    requirements, explanation = runtime._device_start_diagnostics(
        dry, state, runtime.configs["a"], time.monotonic())
    assert explanation["missing"] == ["allocated_start_power"]
    assert all(value["met"] for key, value in requirements.items() if key != "allocated_start_power")
    assert not explanation["listed_requirements_met"]
    assert explanation["power"]["measured_free_w"] == 5220
    assert explanation["power"]["allocation"]["available_w"] == 20
    assert explanation["power"]["allocation"]["required_w"] == 421
    assert explanation["summary"] == runtime.result.reasons["a"]

def test_invalid_measurement_hides_allocation_even_if_old_plan_had_plenty():
    runtime, _ = build(device={"nominal_w": 321, "start_margin_w": 100})
    state = runtime.states["a"]
    state.observed_once = True
    state.last_off = -1e12
    dry = load("a")
    runtime.result = plan(site(), [dry], {"a": state})
    runtime._start_context = {"measurement_valid": False, "can_increase": False}
    _, explanation = runtime._device_start_diagnostics(dry, state, runtime.configs["a"], time.monotonic())
    assert explanation["power"]["measured_free_w"] is None
    assert explanation["power"]["allocation"] is None
    assert "allocated_start_power" in explanation["missing"]
