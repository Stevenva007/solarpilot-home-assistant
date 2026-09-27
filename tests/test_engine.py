from dataclasses import replace
import math
import random
import pytest
from custom_components.solar_pilot.engine import Device, State, Site, plan


def dev(id="a", **kwargs):
    return Device(id=id, name=id, min_on_s=0, min_off_s=0,
                  start_delay_s=0, stop_delay_s=0, start_margin_w=0, **kwargs)


def site(grid=-2000, **kwargs):
    return Site(now=1000, grid_w=grid, filtered_grid_w=grid, reserve_w=0, **kwargs)


def owned(w=1000, **kwargs):
    return State(owned=True, on=True, measured_w=w, target_w=w, last_on=0, **kwargs)


def test_no_export_no_start():
    assert plan(site(0), [dev()], {"a": State()}).action is None


def test_start_with_enough_export():
    assert plan(site(-1000), [dev()], {"a": State()}).action.watts == 1000


def test_import_never_starts_solar():
    assert plan(site(1000), [dev()], {"a": State()}).action is None


def test_priority_number_smaller_wins():
    ds = [dev("a", priority=50), dev("b", priority=1)]
    assert plan(site(-1000), ds, {d.id: State() for d in ds}).action.id == "b"


def test_large_high_priority_can_be_skipped():
    ds = [dev("a", priority=1, nominal_w=3000), dev("b", priority=2, nominal_w=500)]
    assert plan(site(-700), ds, {d.id: State() for d in ds}).action.id == "b"


def test_owned_load_is_not_mistaken_for_disappeared_solar():
    p = plan(site(0), [dev()], {"a": owned()})
    assert p.action is None and p.targets["a"] == 1000


def test_shortage_stops_owned_load():
    assert plan(site(500), [dev()], {"a": owned()}).action.watts == 0


def test_external_load_never_taken_over_or_stopped():
    s = State(on=True, measured_w=1000)
    assert plan(site(5000), [dev()], {"a": s}).action is None


def test_manual_hold_prevents_restart():
    assert plan(site(-5000), [dev()], {"a": State(manual_until=2000)}).action is None


def test_disabled_device_does_not_start():
    assert plan(site(), [dev()], {"a": State(enabled=False)}).action is None


def test_demand_false_does_not_start():
    assert plan(site(), [dev()], {"a": State(demand=False)}).action is None


def test_interlock_false_does_not_start():
    assert plan(site(), [dev()], {"a": State(interlock=False)}).action is None


def test_bad_site_meter_stops_after_grace():
    p = plan(site(valid=False, fault_elapsed_s=35), [dev()], {"a": owned()})
    assert p.action.watts == 0


def test_bad_site_meter_grace_period():
    assert plan(site(valid=False, fault_elapsed_s=10), [dev()], {"a": owned()}).action is None


def test_bad_meter_never_starts():
    assert plan(site(-5000, valid=False), [dev()], {"a": State()}).action is None


def test_unavailable_device_skipped():
    assert plan(site(), [dev()], {"a": State(available=False)}).action is None


def test_start_delay_is_continuous():
    d = replace(dev(), start_delay_s=60)
    s = State()
    assert plan(site(), [d], {"a": s}).action is None
    assert plan(replace(site(), now=1030), [d], {"a": s}).action is None
    assert plan(replace(site(0), now=1050), [d], {"a": s}).action is None
    assert s.start_since is None
    assert plan(replace(site(), now=1060), [d], {"a": s}).action is None
    assert plan(replace(site(), now=1121), [d], {"a": s}).action is not None


def test_stop_delay_does_not_follow_single_cloud():
    d = replace(dev(), stop_delay_s=60)
    s = owned()
    assert plan(site(1000), [d], {"a": s}).action is None
    assert plan(replace(site(0), now=1030), [d], {"a": s}).action is None
    assert s.stop_since is None


def test_minimum_on_time_is_respected_even_on_pause():
    d = replace(dev(), min_on_s=1200)
    assert plan(site(1000, mode="paused"), [d], {"a": owned()}).action is None


def test_minimum_off_time_is_respected():
    d = replace(dev(), min_off_s=1200)
    assert plan(site(), [d], {"a": State(last_off=0)}).action is None


def test_non_interruptible_cycle_survives_pause_and_clouds():
    d = dev(kind="script", non_interruptible=True)
    assert plan(site(10000, mode="paused"), [d], {"a": owned()}).action is None


def test_cycle_does_not_restart_without_rearming():
    d = dev(kind="script", non_interruptible=True)
    assert plan(site(), [d], {"a": State(cycle_armed=False)}).action is None


def test_battery_discharge_not_counted_as_sunshine():
    assert plan(site(-1200, battery_discharge_w=1200), [dev()], {"a": State()}).action is None


def test_battery_soc_gate():
    assert plan(site(-5000, battery_ready=False), [dev()], {"a": State()}).action is None


def test_start_reserve():
    p = plan(replace(site(-1100), reserve_w=150), [dev()], {"a": State()})
    assert p.action is None


def test_boost_can_use_grid_but_respects_cap():
    s = State(boost_until=2000)
    p = plan(site(0, max_import_w=1500), [dev()], {"a": s})
    assert p.action.watts == 1000
    p = plan(site(700, max_import_w=1500), [dev()], {"a": s})
    assert p.action is None


def test_boost_never_bypasses_interlock():
    assert plan(site(0), [dev()], {"a": State(boost_until=2000, interlock=False)}).action is None


def test_boost_expiry_returns_to_solar():
    assert plan(site(0), [dev()], {"a": State(boost_until=999)}).action is None


def test_variable_quantization_and_minimum():
    d = dev(kind="number")
    assert d.quantize(1300) == 0
    assert d.quantize(1500) == 1380
    assert d.quantize(2000) == 1840
    assert d.quantize(5000) == 3680
    assert d.quantize(float("nan")) == 0


def test_variable_start_at_valid_step():
    p = plan(site(-2300), [dev(kind="number")], {"a": State()})
    assert p.action.watts == 2300


def test_smoothing_cannot_invent_headroom():
    p = plan(replace(site(0), filtered_grid_w=-5000), [dev()], {"a": State()})
    assert p.action is None


def test_number_increase_does_not_use_phantom_measured_consumption():
    s = owned(w=1380)
    s.measured_w = 0
    p = plan(site(-1000), [dev(kind="number")], {"a": s})
    assert p.action is None or p.action.watts < 1380


def test_committed_but_idle_load_is_not_double_allocated():
    ds = [dev("a"), dev("b")]
    states = {"a": owned(), "b": State()}
    states["a"].measured_w = 0
    p = plan(site(-1500), ds, states)
    assert p.action is None or p.action.id != "b"


def test_priority_reallocation_stops_lower_first():
    ds = [dev("a", priority=1), dev("b", priority=50)]
    p = plan(site(0), ds, {"a": State(), "b": owned()})
    assert p.action.id == "b" and p.action.watts == 0


def test_no_increase_without_fresh_post_command_sample():
    assert plan(site(-5000, can_increase=False), [dev()], {"a": State()}).action is None


def test_maximum_runtime_requests_release():
    d = dev(max_on_s=500)
    assert plan(site(-5000), [d], {"a": owned()}).action.watts == 0


def test_only_one_command_per_plan():
    ds = [dev(str(i), nominal_w=100) for i in range(5)]
    p = plan(site(-5000), ds, {d.id: State() for d in ds})
    assert p.action is not None and not isinstance(p.action, list)


def test_randomized_solar_start_never_exceeds_observed_headroom():
    rng = random.Random(42)
    for _ in range(3000):
        grid = rng.uniform(-15000, 5000)
        reserve = rng.uniform(0, 500)
        discharge = rng.uniform(0, 3000)
        ds = [dev(str(i), nominal_w=rng.uniform(50, 5000), priority=rng.randint(1, 100)) for i in range(5)]
        states = {d.id: State() for d in ds}
        p = plan(replace(site(grid), reserve_w=reserve, battery_discharge_w=discharge), ds, states)
        if p.action:
            assert p.action.watts <= -grid - reserve - discharge + 1e-5


def test_randomized_variable_commands_never_outside_range_or_step():
    rng = random.Random(53)
    d = dev(kind="number")
    for _ in range(2000):
        p = plan(site(rng.uniform(-15000, 5000)), [d], {"a": State()})
        if p.action and p.action.watts > 0:
            units = p.action.watts / d.watts_per_unit
            assert d.min_units <= units <= d.max_units
            assert math.isclose((units - d.min_units) % d.step_units, 0, abs_tol=1e-6)


def test_minimum_runtime_does_not_unnecessarily_throttle_variable_load():
    d = replace(dev(kind="number"), min_on_s=1200)
    s = owned(2300)
    p = plan(site(-2000), [d], {"a": s})
    assert p.targets["a"] == 3680 and p.action.watts == 3680


def test_minimum_runtime_reduces_variable_load_but_never_stops_it():
    d = replace(dev(kind="number"), min_on_s=1200)
    s = owned(2300)
    p = plan(site(5000), [d], {"a": s})
    assert p.action.watts == 1380


def test_daily_deadline_urgent_load_gets_priority_with_solar():
    ds = [dev("normal", priority=1, nominal_w=1000), dev("daily", priority=90, nominal_w=1000)]
    states = {"normal": State(), "daily": State(deadline_urgent=True)}
    p = plan(site(-1000), ds, states)
    assert p.action.id == "daily"
    assert "Dagminimum" in p.action.reason


def test_daily_deadline_grid_fallback_requires_explicit_flag_in_state():
    d = dev(min_daily_runtime_s=3600, deadline_grid_allowed=True)
    # Runtime policy only sets deadline_force when the configured grid fallback is allowed.
    p = plan(site(0, max_import_w=1500), [d], {"a": State(deadline_urgent=True, deadline_force=True)})
    assert p.action is not None and p.action.watts == 1000
    assert "netstroom toegestaan" in p.action.reason
    p = plan(site(0, max_import_w=1500), [d], {"a": State(deadline_urgent=True, deadline_force=False)})
    assert p.action is None


def test_daily_deadline_grid_fallback_still_respects_capacity_limit():
    d = dev(min_daily_runtime_s=3600, deadline_grid_allowed=True)
    p = plan(site(700, max_import_w=1500), [d], {"a": State(deadline_urgent=True, deadline_force=True)})
    assert p.action is None


def test_daily_maximum_blocks_new_start_but_running_noninterruptible_cycle_finishes():
    d = dev(max_daily_runtime_s=3600)
    s = State(daily_runtime_s=3600)
    assert plan(site(-5000), [d], {"a": s}).action is None
    assert "Dagmaximum" in plan(site(-5000), [d], {"a": s}).reasons["a"]
    cycle = dev(kind="script", non_interruptible=True, max_daily_runtime_s=3600)
    running = owned(daily_runtime_s=3600)
    p = plan(site(5000, mode="paused"), [cycle], {"a": running})
    assert p.targets["a"] == cycle.minimum and p.action is None


def test_planner_hold_only_blocks_new_start():
    s=State(planner_hold=True, planner_reason='Wacht op zon')
    p=plan(site(-5000),[dev()],{'a':s})
    assert p.action is None and p.reasons['a']=='Wacht op zon'
    running=owned(); running.planner_hold=True; running.planner_reason='Wacht op zon'
    p=plan(site(-100),[dev()],{'a':running})
    assert p.targets['a']==1000


def test_planner_cheap_grid_force_still_respects_grid_cap():
    s=State(planner_grid_force=True)
    p=plan(site(0,max_import_w=1500),[dev()],{'a':s})
    assert p.action and p.action.watts==1000
    p=plan(site(700,max_import_w=1500),[dev()],{'a':State(planner_grid_force=True)})
    assert p.action is None


def test_manual_force_can_start_with_grid_within_software_limit_even_when_excluded():
    s = State(enabled=False, manual_forced=True)
    p = plan(site(500, max_import_w=3500), [dev()], {"a": s})
    assert p.action is not None and p.action.id == "a" and p.action.watts == 1000
    assert "Manuele start" in p.action.reason


def test_manual_force_keeps_running_during_normal_shortage_but_not_pause():
    s = owned(manual_forced=True)
    p = plan(site(500, max_import_w=3500), [dev()], {"a": s})
    assert p.action is None and p.targets["a"] == 1000 and p.reasons["a"] == "Manueel actief"
    p = plan(site(500, mode="paused", max_import_w=3500), [dev()], {"a": s})
    assert p.action is not None and p.action.watts == 0


def test_manual_stop_request_respects_minimum_runtime_then_stops_without_cloud_delay():
    d = replace(dev(), min_on_s=300, stop_delay_s=900)
    s = replace(owned(), manual_stop_requested=True, last_on=900)
    assert plan(site(-3000), [d], {"a": s}).action is None
    p = plan(replace(site(-3000), now=1301), [d], {"a": s})
    assert p.action is not None and p.action.watts == 0
    assert p.action.reason == "Manuele stop gevraagd"
