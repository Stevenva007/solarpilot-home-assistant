"""No real charger commands. Pure policy, engine and HA-double regression tests."""
from dataclasses import replace
import pytest
from custom_components.solar_pilot.consumer_wallbox import ConsumerWallboxPriority, follows_wallbox
from custom_components.solar_pilot.wallbox import WALLBOX_DEFAULTS, Reading
from custom_components.solar_pilot.engine import Device, State, Site, plan
from custom_components.solar_pilot.runtime import SolarRuntime
from test_runtime import build


def guard(**settings):
    return ConsumerWallboxPriority({**WALLBOX_DEFAULTS, 'enabled': True, 'priority_min_power_w': 4140,
                                    'priority_start_margin_w': 150, 'priority_stable_s': 120,
                                    'priority_release_s': 300, **settings})


def read(power=0, status='Waiting for green energy', demand=True, **kw):
    return Reading(power_w=power, stamp=1000, demand=demand, status=status,
                   mode='full_solar', valid=True, age_s=0, connected=True, **kw)


def tick(g, now, export, own=None, r=None):
    return g.update(now=now, reading=r or read(), grid_w=-export, filtered_grid_w=-export,
                    discharge_w=0, owned_lower=own or {}, has_lower=True, sample_gap_s=1000)


def test_default_global_and_explicit_priorities():
    assert not follows_wallbox({}, True)
    assert follows_wallbox({}, False)
    assert follows_wallbox({'wallbox_precedence':'wallbox_first'}, True)
    assert not follows_wallbox({'wallbox_precedence':'consumer_first'}, False)


def test_small_surplus_allowed_even_with_car_waiting():
    x=tick(guard(), 10, 1500)
    assert x.state=='small_surplus' and not x.block_starts and not x.yield_loads


def test_releasable_own_load_counts_to_threshold_but_not_to_free_export():
    g=guard()
    assert tick(g, 0, 4000, {'dry':350}).state=='threshold_delay'
    x=tick(g, 120, 4000, {'dry':350})
    assert x.state=='yield' and x.potential_w==4350
    # Actual load switches off: its 350 W becomes real export, not a lost credit.
    x=tick(g, 121, 4350)
    assert x.state=='wait_ev_start' and x.block_starts


def test_short_peak_does_not_cause_release():
    g=guard()
    tick(g, 0, 4500, {'dry':350})
    assert tick(g, 10, 1000, {'dry':350}).state=='small_surplus'
    assert tick(g, 120, 4500, {'dry':350}).state=='threshold_delay'


def test_sample_gap_restarts_stability():
    g=guard()
    tick(g, 0, 4400)
    x=g.update(now=125,reading=read(),grid_w=-4400,filtered_grid_w=-4400,
               discharge_w=0,owned_lower={},has_lower=True,sample_gap_s=30)
    assert x.state=='threshold_delay' and x.remaining_s==120


@pytest.mark.parametrize('status', ['Ready','Paused','Scheduled','Waiting for car demand','Locked','Locked, car connected'])
def test_plugged_but_no_request_never_reserves(status):
    g=guard()
    # Idle status defeats even a stale/misconfigured demand override.
    x=tick(g,0,6000,r=read(status=status,demand=True))
    assert x.state=='no_request' and not x.block_starts


def test_confirmed_unplugged_never_reserves():
    x=tick(guard(),0,5000,r=replace(read(),connected=False))
    assert not x.block_starts and x.state=='no_request'


def test_unknown_data_not_treated_as_unplugged_or_as_a_stop_command():
    x=tick(guard(),0,5000,{'dry':350},r=replace(read(),valid=False,connected=None))
    assert x.block_starts and not x.yield_loads


def test_non_solar_wait_does_not_reserve():
    x=tick(guard(),0,5000,r=replace(read(),mode='disabled'))
    assert x.state=='not_solar' and not x.block_starts


def test_minimum_needs_confirmation_not_derived_from_house_fuses():
    x=tick(guard(priority_min_power_w=0),0,5000)
    assert x.state=='unconfigured' and x.block_starts


def test_battery_discharge_is_not_a_solar_start_opportunity():
    g=guard()
    x=g.update(now=0,reading=read(),grid_w=-4400,filtered_grid_w=-4400,
               discharge_w=1000,owned_lower={},has_lower=True)
    assert x.potential_w==3400 and x.state=='small_surplus'


def test_car_no_start_has_bounded_wait_and_retry_cooldown():
    g=guard(priority_stable_s=0,priority_start_timeout_s=600,priority_retry_s=1800)
    assert tick(g,0,4500).state=='wait_ev_start'
    assert tick(g,600,4500).state=='retry_wait'
    assert tick(g,1200,4500).state=='retry_wait'
    assert tick(g,2400,4500).state=='wait_ev_start'


def test_no_start_timeout_waits_for_compressor_protection():
    g=guard(priority_stable_s=0)
    assert tick(g,0,4100,{'dry':350}).yield_loads
    assert tick(g,700,4100,{'dry':350}).state=='yield'
    assert tick(g,1800,4450).state=='wait_ev_start'
    assert tick(g,2399,4450).state=='wait_ev_start'


def test_hysteresis_prevents_yoyo_near_threshold():
    g=guard(priority_stable_s=0)
    tick(g,0,4500)
    assert tick(g,20,4100).block_starts  # below enter threshold, still above exit
    assert tick(g,30,3000).block_starts
    assert tick(g,329,3000).block_starts
    assert tick(g,330,3000).state=='small_surplus'


def test_charging_yields_fallback_but_allows_real_leftovers_afterwards():
    g=guard()
    tick(g,0,1600,{'dry':350})
    assert tick(g,5,100,{'dry':350},r=read(power=4200,status='Charging')).yield_loads
    x=tick(g,10,450,r=read(power=4200,status='Charging'))
    assert x.state=='charging_residual' and not x.block_starts


def test_ev_drop_after_lower_start_requests_safe_release():
    g=guard()
    tick(g,0,800,r=read(power=7000,status='Charging'))
    g.note_action(1,1001,'dry',0,350,read(power=7000,status='Charging'))
    x=tick(g,180,0,{'dry':350},r=replace(read(power=6650,status='Charging'),stamp=1100))
    assert x.yield_loads


def test_engine_yields_after_minimum_runtime_not_after_extra_cloud_buffer():
    d=Device('dry',nominal_w=350,min_on_s=1800,stop_delay_s=900)
    st=State(owned=True,on=True,measured_w=350,target_w=350,last_on=0)
    reason={'dry':'Wallbox voorrang'}
    site=Site(100,grid_w=-4100,filtered_grid_w=-4100,device_holds=reason)
    p=plan(site,[d],{'dry':st})
    assert p.action is None and p.targets['dry']==350
    p=plan(replace(site,now=1800),[d],{'dry':st})
    assert p.action and p.action.watts==0


def test_engine_never_interrupts_protected_cycle_for_wallbox():
    d=Device('cycle',nominal_w=350,non_interruptible=True,min_on_s=0)
    st=State(owned=True,on=True,measured_w=350,target_w=350,last_on=0)
    p=plan(Site(9999,grid_w=-4100,filtered_grid_w=-4100,device_holds={'cycle':'yield'}),[d],{'cycle':st})
    assert p.action is None


def test_engine_subordinate_cannot_borrow_ev_power():
    d=Device('dry',nominal_w=350,start_delay_s=0,min_off_s=0,allow_wallbox_reclaim=True,min_on_s=0)
    s=State()
    site=Site(100,grid_w=0,filtered_grid_w=0,reclaimable_w=4000,no_reclaim_ids={'dry'})
    assert plan(site,[d],{'dry':s}).action is None


def test_engine_per_device_hold_leaves_higher_priority_device_alone():
    devices=[Device('first',nominal_w=600,start_delay_s=0,min_off_s=0),Device('dry',nominal_w=350,start_delay_s=0,min_off_s=0)]
    p=plan(Site(100,grid_w=-2000,filtered_grid_w=-2000,device_start_blocks={'dry':'Wallbox'}),devices,{'first':State(),'dry':State()})
    assert p.action and p.action.id=='first'


@pytest.mark.asyncio
async def test_runtime_new_priority_reads_only_and_no_borrow_for_lower_load():
    old,h=build(power=True, device={'wallbox_precedence':'wallbox_first','nominal_w':350})
    old.entry.options['wallbox']={**WALLBOX_DEFAULTS,'enabled':True,'trust_solar_setting':True,'priority_min_power_w':4140,
        'power_entity':'sensor.ev','status_entity':'sensor.ev_status','mode_entity':'select.ev_solar','stable_s':0}
    h.states.set('sensor.ev',0,{'unit_of_measurement':'W'})
    h.states.set('sensor.ev_status','Waiting for green energy')
    h.states.set('select.ev_solar','full_solar')
    r=SolarRuntime(h,old.entry);r.mode='solar';r.device_modes['a']='auto'
    await r.tick()
    assert r.consumer_wallbox.result.state=='small_surplus'
    assert r.pending and r.pending['id']=='a'
    assert all(x[0]=='switch' and x[2]['entity_id']=='switch.load' for x in h.services.calls)
    assert r.overview()[0]['wallbox_first'] is True
    assert r.wallbox_overview()['per_device_priority']


@pytest.mark.asyncio
async def test_explicit_consumer_first_bypasses_global_wallbox_preference():
    old,h=build(power=True,device={'wallbox_precedence':'consumer_first','nominal_w':350})
    old.entry.options['wallbox']={**WALLBOX_DEFAULTS,'enabled':True,'trust_solar_setting':True,'priority_min_power_w':4140,
        'power_entity':'sensor.ev','status_entity':'sensor.ev_status','mode_entity':'select.ev_solar','stable_s':0}
    h.states.set('sensor.ev',0,{'unit_of_measurement':'W'});h.states.set('sensor.ev_status','Waiting for green energy');h.states.set('select.ev_solar','full_solar')
    r=SolarRuntime(h,old.entry);r.mode='solar';r.others_first=False;r.wallbox_guard=r._make_wallbox_guard();r.device_modes['a']='auto'
    await r.tick()
    assert r.pending and r.pending['id']=='a'


@pytest.mark.asyncio
async def test_explicit_consumer_first_handover_completes_when_global_prefers_wallbox(monkeypatch):
    from test_house_runtime import setup, start_transfer, tick as loop_tick
    r, h, c = setup(monkeypatch, device={"wallbox_precedence": "consumer_first"})
    r.others_first = False
    r.wallbox_guard = r._make_wallbox_guard()
    await start_transfer(r, h, c)
    for t in range(35, 60, 5):
        await loop_tick(r, h, c, t, grid=850, load=1000)
    assert r.handover.status == "waiting"
    for t in range(60, 80, 5):
        await loop_tick(r, h, c, t, ev=3000, grid=-150, load=1000)
    assert r.handover is None and r.last_handover["state"] == "success"
    assert all(call[2].get("entity_id") == "switch.load" for call in h.services.calls)


@pytest.mark.asyncio
async def test_no_daily_goal_cannot_be_permanently_blocked_by_forecast_opt_in():
    r, h = build(power=True, device={"forecast_deferrable": True, "nominal_w": 350,
                                   "min_daily_runtime_s": 0, "daily_energy_goal_kwh": 0})
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    await r.tick()
    assert not r.states["a"].planner_hold
    assert r.pending and r.pending["id"] == "a"
