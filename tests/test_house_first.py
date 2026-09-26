"""New conditional allocation and bounded handover tests, without HA Core."""
from dataclasses import replace
import pytest
from custom_components.solar_pilot.engine import Device, State, Site, plan
from custom_components.solar_pilot.wallbox import Reading
from custom_components.solar_pilot.house_first import HouseFirstGuard, Handover


def read(**kw):
    return replace(Reading(4000, 1000, True, "Charging", "full_solar", True, "", 0), **kw)


def guard(**kw):
    return HouseFirstGuard({"enabled": True, "mode_entity": "select.solar", "stable_s": 30, **kw})


def stable(g, r=None, grid=-150, start=0, end=30, reserve=150, discharge=0):
    for n in range(start, end+1, 5):
        v = g.update(n, r or read(), grid, reserve, discharge)
    return v


def dev(**kw):
    return Device("a", min_on_s=0, min_off_s=0, start_delay_s=0, stop_delay_s=0,
                  start_margin_w=0, allow_wallbox_reclaim=True, **kw)


def site(**kw):
    return Site(now=1000, grid_w=-150, filtered_grid_w=-150, reserve_w=150, reclaimable_w=4000, **kw)


def test_house_first_can_allocate_without_real_export_after_reserve():
    g = guard()
    v = stable(g)
    assert v.state == "house_first" and not v.block_increase
    assert g.reclaimable_w == 4000 and v.max_increase_w == 2500


def test_waiting_for_sun_does_not_give_ev_priority_in_house_first():
    v = stable(guard(), read(power_w=0), grid=-2000)
    assert not v.block_increase and not v.release_flexible


def test_expected_ev_drop_never_triggers_wallbox_first_conflict_logic():
    g = guard(); stable(g); g.note_action(30, 1001, 0, 1000)
    v = g.update(35, read(power_w=3000, stamp=1002), -150, 150)
    assert v.state == "settling" and not v.release_flexible and g.conflict_count == 0


@pytest.mark.parametrize("mode", [None, "eco_mode", "disabled"])
def test_full_solar_confirmation_required_for_any_credit(mode):
    g = guard(); v = stable(g, read(mode=mode), grid=-150)
    assert g.reclaimable_w == 0 and v.max_increase_w == 0 and v.warning


def test_old_but_not_offline_wallbox_meter_is_not_transferable():
    g = guard(); v = stable(g, read(age_s=121), grid=-1000)
    assert g.reclaimable_w == 0 and v.max_increase_w == 850


def test_real_surplus_and_conditional_credit_are_distinct_in_engine():
    p = plan(site(), [dev()], {"a": State()})
    assert p.free_w == 0 and p.budget_w == 4000
    assert p.action.watts == 1000 and p.action.reclaimed_w == 1000


def test_actual_import_ceiling_never_receives_ev_credit():
    p = plan(site(max_import_w=500), [dev()], {"a": State()})
    assert p.action is None  # Would import 850 W, not 500 W.


def test_unknown_appliance_cannot_borrow_by_default():
    d = replace(dev(), allow_wallbox_reclaim=False)
    assert plan(site(), [d], {"a": State()}).action is None


def test_non_interruptible_cycle_never_started_on_expected_ev_reduction():
    assert plan(site(), [dev(non_interruptible=True)], {"a": State()}).action is None


def test_minimum_run_time_longer_than_deadline_disallows_borrowing():
    d = replace(dev(), min_on_s=300)
    assert plan(site(handover_s=240), [d], {"a": State()}).action is None


def test_start_can_use_real_surplus_without_borrow_even_when_not_eligible():
    p = plan(replace(site(), grid_w=-2000, filtered_grid_w=-2000),
             [replace(dev(), allow_wallbox_reclaim=False)], {"a": State()})
    assert p.action.watts == 1000 and p.action.reclaimed_w == 0


def test_partial_real_surplus_reduces_the_amount_borrowed():
    p = plan(replace(site(), grid_w=-650, filtered_grid_w=-650), [dev()], {"a": State()})
    assert p.action.reclaimed_w == 500


def test_maximum_conditional_step_is_honoured():
    assert plan(site(max_takeover_w=500), [dev()], {"a": State()}).action is None


def test_priority_skips_noneligible_large_cycle_and_starts_eligible_load():
    a=dev(non_interruptible=True, priority=1)
    b=replace(dev(priority=2), id="b")
    p = plan(site(), [a,b], {"a":State(), "b":State()})
    assert p.action.id == "b"


def test_battery_discharge_is_not_reclassified_as_solar():
    p=plan(site(battery_discharge_w=4000), [dev()], {"a":State()})
    assert p.action is None


def test_offline_monitor_does_not_make_claim_about_power():
    g=guard(); stable(g)
    v=g.update(35, Reading(), 0, 150)
    assert v.block_increase and g.reclaimable_w == 0


def test_missed_ticks_require_a_new_observation_window():
    g=guard(); stable(g, end=10)
    assert g.update(100, read(), -150, 150).block_increase


def test_rollback_respects_minimum_run_time_and_reverts_previous_setpoint():
    d = replace(dev(), min_on_s=200)
    s = State(owned=True,on=True,measured_w=1000,target_w=1000,last_on=900)
    p = plan(site(rollback_device="a", rollback_target_w=0, can_increase=False), [d], {"a":s})
    assert p.action is None
    s.last_on = 0
    p = plan(site(rollback_device="a", rollback_target_w=0, can_increase=False), [d], {"a":s})
    assert p.action.watts == 0


def handover():
    return Handover("a", 0, 1000, 1000, 4000, 10, 1000, 120)


def eval_transfer(t, now, **kw):
    defaults=dict(grid_w=-150,grid_stamp=1001+now,reading=read(power_w=3000,stamp=1001+now),
                  measured_w=1000,measured_stamp=1001+now,available=True,allowed=True,
                  discharge_w=0,ceiling_w=3500,import_tolerance_w=100,confirm_s=15)
    t.evaluate(now, **(defaults|kw))


def test_completion_requires_time_and_fresh_grid_sample():
    t=handover(); eval_transfer(t,20,grid_stamp=1020)
    eval_transfer(t,35,grid_stamp=1020)
    assert t.status == "waiting"
    eval_transfer(t,40,grid_stamp=1040)
    assert t.status == "success"


@pytest.mark.parametrize("kw", [
    {"reading":read(power_w=4000,stamp=1100)}, {"measured_w":0}, {"measured_stamp":999},
    {"reading":read(power_w=3000,stamp=999)}, {"grid_w":101}, {"discharge_w":100},
    {"grid_stamp":999},
])
def test_incomplete_evidence_cannot_confirm_transfer(kw):
    t=handover(); eval_transfer(t,20,**kw); eval_transfer(t,40,**kw)
    assert t.status == "waiting"


def test_timeout_requests_rollback_not_infinite_trial():
    t=handover(); eval_transfer(t,131)
    assert t.status == "rollback"


def test_grid_limit_violation_aborts_before_timeout():
    t=handover(); eval_transfer(t,11,grid_w=3501)
    assert t.status == "rollback"


@pytest.mark.parametrize("kw", [{"allowed":False},{"available":False},{"grid_w":None},{"reading":Reading()}])
def test_loss_of_preconditions_aborts(kw):
    t=handover(); eval_transfer(t,11,**kw)
    assert t.status == "rollback"


def test_randomised_conditional_starts_obey_actual_import_and_transfer_limits():
    import random
    rng=random.Random(73417)
    for _ in range(2500):
        grid=rng.uniform(-5000,4000)
        limit=rng.uniform(0,6000)
        reserve=rng.uniform(0,400)
        credit=rng.uniform(0,11000)
        step=rng.uniform(200,3000)
        d=dev(nominal_w=rng.uniform(100,4500))
        p=plan(Site(now=1000,grid_w=grid,filtered_grid_w=grid,reserve_w=reserve,
                    max_import_w=limit,reclaimable_w=credit,max_takeover_w=step),[d],{'a':State()})
        if p.action:
            assert grid+p.action.watts <= limit+1e-5
            assert p.action.reclaimed_w <= min(credit,step)+1e-5
            assert p.action.watts <= max(0,-grid-reserve)+credit+1e-5
