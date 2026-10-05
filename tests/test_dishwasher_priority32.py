"""Beta.32 priority tests: physical doubles only, no live devices or networks."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
import time
import pytest
from custom_components.solar_pilot.dishwasher_priority import DishwasherPriority, enabled
from custom_components.solar_pilot.engine import Device, State, Site, Action, plan
from custom_components.solar_pilot.wallbox import Reading
from custom_components.solar_pilot.house_first import HouseFirstGuard
from custom_components.solar_pilot.const import DEVICE_DEFAULTS
from custom_components.solar_pilot.dishwasher import normalize_config
from test_dishwasher_app31 import configured, ready, event, move


def inputs(**overrides):
    d=Device('dw',kind='dishwasher',priority=50,nominal_w=2000,start_delay_s=300,non_interruptible=True,min_off_s=0)
    low=Device('low',priority=1,nominal_w=350,min_on_s=1800,min_off_s=1800)
    return {"now":1000.,"wall":10000.,"mode":"solar",
        "configs":{"dw":{"kind":"dishwasher"},"low":{"kind":"switch"}},
        "devices":{"dw":d,"low":low},"states":{"dw":State(),"low":State(owned=True,on=True,measured_w=350,target_w=350,last_on=-1000)},
        "permitted_ids":{"dw"},"actual_grid":-1900.,"filtered_grid":-1900.,"pv_w":5000.,
        "discharge_w":0.,"reserve_w":150.,"max_import_w":3500.,
        "reading":Reading(valid=True,power_w=0.,mode="full_solar",status="Charging",stamp=10000.,age_s=0,demand=True,connected=True),
        "wallbox_settings":{"enabled":True,"max_takeover_w":2500},"stable_ev_credit_w":0.,
        "lower_measured":{"low":350.},**overrides}


def advance(p,kw,seconds=300):
    result=None
    for t in range(0,seconds+1,5):
        result=p.evaluate(**{**kw,"now":kw['now']+t,"wall":kw['wall']+t})
    return result


def test_default_policy_preconfigured_for_dishwasher_only():
    assert enabled({'kind':'dishwasher'})
    assert not enabled({'kind':'switch'})
    assert not enabled({'kind':'dishwasher','dishwasher_priority_enabled':False})
    c=normalize_config({'kind':'dishwasher','id':'a','priority':70})
    assert c['dishwasher_priority_enabled'] and c['dishwasher_ev_solar_priority']
    assert c['non_interruptible'] and not c['allow_wallbox_reclaim']
    assert not c['dishwasher_mapping_confirmed']


def test_small_surplus_does_not_turn_off_lower_load():
    p=DishwasherPriority();v=advance(p,inputs(actual_grid=-600,filtered_grid=-600))
    assert not v.holds and not v.stable_ids


def test_releases_only_needed_low_load_after_stability():
    p=DishwasherPriority();kw=inputs(actual_grid=-1950,filtered_grid=-1950)
    assert not p.evaluate(**kw).holds
    assert advance(p,kw).holds.keys()=={'low'}


def test_does_not_release_lower_if_both_fit():
    p=DishwasherPriority();v=advance(p,inputs(actual_grid=-3000,filtered_grid=-3000))
    assert v.stable_ids=={'dw'} and not v.holds

@pytest.mark.parametrize('what',['external','manual','boost','deadline','grid_goal','protected','unavailable','fault'])
def test_never_preempts_protected_or_external_lower(what):
    kw=inputs(actual_grid=-1950,filtered_grid=-1950)
    s=kw['states']['low']
    if what=='external':s.owned=False
    if what=='manual':s.manual_forced=True
    if what=='boost':s.boost_until=5000
    if what=='deadline':s.deadline_force=True
    if what=='grid_goal':s.planner_grid_force=True
    if what=='protected':kw['devices']['low']=replace(kw['devices']['low'],non_interruptible=True)
    if what=='unavailable':s.available=False
    if what=='fault':s.fault='failure'
    v=advance(DishwasherPriority(),kw)
    assert not v.holds

@pytest.mark.parametrize('key,value', [('actual_grid',None),('filtered_grid',None),('pv_w',None),('pv_w',float('nan')),
    ('discharge_w',-1),('site_ready',False),('max_import_w',float('inf'))])
def test_unreliable_meter_never_creates_credit_or_release(key,value):
    kw=inputs(**{key:value})
    p=DishwasherPriority();v=advance(p,kw)
    assert not v.ev_credit and not v.holds

@pytest.mark.parametrize('key,value',[('mode','disabled'),('valid',False),('age_s',121),('connected',False),('demand',False)])
def test_only_fresh_full_solar_can_supply_conditional_credit(key,value):
    kw=inputs(actual_grid=0,filtered_grid=0,lower_measured={})
    kw['reading']=replace(kw['reading'],power_w=3000,**{key:value});kw['stable_ev_credit_w']=3000
    v=advance(DishwasherPriority(),kw)
    assert not v.ev_credit and not v.stable_ids


def test_positive_stable_ev_credit_does_not_exceed_real_power_or_pv():
    kw=inputs(actual_grid=0,filtered_grid=0,lower_measured={})
    kw['reading']=replace(kw['reading'],power_w=3000);kw['stable_ev_credit_w']=4000
    v=advance(DishwasherPriority(),kw)
    assert v.ev_credit['dw']==2500 and v.stable_ids=={'dw'}
    kw['pv_w']=1000
    assert not advance(DishwasherPriority(),kw).ev_credit


def test_start_power_diagnostics_include_wallbox_even_below_start_threshold():
    kw = inputs(actual_grid=-600, filtered_grid=-600, lower_measured={})
    kw['reading'] = replace(kw['reading'], power_w=1000)
    kw['stable_ev_credit_w'] = 1000
    p = DishwasherPriority()
    v = advance(p, kw)
    pool = v.start_power['dw']
    assert pool['net_solar_after_reserves_w'] == 450
    assert pool['wallbox_solar_w'] == 1000
    assert pool['available_solar_w'] == 1450
    assert pool['required_start_w'] == 2100
    assert pool['not_a_start_guarantee']
    assert pool['source'] == 'dishwasher_priority.evaluate'
    assert not v.ev_credit and not v.stable_ids and not p.since


def test_start_power_diagnostics_use_same_pv_and_comfort_caps_as_admission():
    kw = inputs(actual_grid=-2000, filtered_grid=-2000, lower_measured={},
                pv_w=1800, comfort_reserve_w=300)
    kw['reading'] = replace(kw['reading'], power_w=2500)
    kw['stable_ev_credit_w'] = 2500
    v = advance(DishwasherPriority(), kw)
    pool = v.start_power['dw']
    assert pool['net_solar_after_reserves_w'] == 1550
    assert pool['wallbox_solar_w'] == 2500
    assert pool['pv_ceiling_w'] == pool['available_solar_w'] == 1650
    assert pool['comfort_reserve_w'] == 300
    assert not v.ev_credit and not v.stable_ids


@pytest.mark.parametrize('cause', ['manual', 'stale', 'permission', 'latched_failure'])
def test_start_power_diagnostics_never_count_forbidden_wallbox_watts(cause):
    kw = inputs(actual_grid=-600, filtered_grid=-600, lower_measured={})
    kw['reading'] = replace(kw['reading'], power_w=3000)
    kw['stable_ev_credit_w'] = 3000
    p = DishwasherPriority()
    if cause == 'manual':
        kw['reading'] = replace(kw['reading'], mode='disabled')
    elif cause == 'stale':
        kw['reading'] = replace(kw['reading'], age_s=121)
    elif cause == 'permission':
        kw['configs']['dw']['dishwasher_ev_solar_priority'] = False
    else:
        p.ev_blocks['dw'] = 'Vorige reactie niet bevestigd'
    pool = advance(p, kw).start_power['dw']
    assert pool['wallbox_solar_w'] == 0
    assert pool['available_solar_w'] == 450


@pytest.mark.parametrize('change', [{'permitted_ids': set()}, {'site_ready': False},
                                  {'mode': 'observe'}, {'actual_grid': None},
                                  {'comfort_block': 'Gewoon comfort eerst'}])
def test_no_current_start_pool_is_invented_without_verified_candidate(change):
    p = DishwasherPriority()
    assert not p.evaluate(**inputs(**change)).start_power


def test_ev_sharing_can_be_disabled_without_losing_priority():
    kw=inputs(actual_grid=0,filtered_grid=0,lower_measured={})
    kw['configs']['dw']['dishwasher_ev_solar_priority']=False
    kw['reading']=replace(kw['reading'],power_w=3000);kw['stable_ev_credit_w']=3000
    v=advance(DishwasherPriority(),kw)
    assert v.candidate_ids == {'dw'} and not v.fitting_ids and not v.ev_credit
    assert not v.luxury_block


def test_tomorrow_or_unarmed_has_no_priority_claim():
    v=advance(DishwasherPriority(),inputs(permitted_ids=set()))
    assert not v.candidate_ids and not v.luxury_block and not v.holds


def dhw_allocation(priority=None, **overrides):
    priority = priority or DishwasherPriority()
    values = dict(mode='solar', actual_grid=-6000, filtered_grid=-6000,
        pv_w=9000, discharge_w=0, reserve_w=150,
        unmetered_aeg_reserve_w=2000, surplus_threshold_w=3500,
        holding_owned_high=False, restart_proof_required=False,
        capacity_guard_enabled=False, capacity_valid=True,
        optional_import_headroom_w=None, estimated_heat_power_w=3200,
        states={'dw': State(owned=True, on=True, target_w=2000, measured_w=2000)})
    values.update(overrides)
    return priority.dhw_luxury_allocation(**values)


def test_active_unmetered_aeg_is_reserved_but_not_an_absolute_60c_veto():
    p = DishwasherPriority()
    p.view.active_ids = {'dw'}
    result = dhw_allocation(p)
    assert result.allowed
    assert result.usable_surplus_w == 3850
    assert result.unmetered_aeg_reserve_w == 2000
    assert 'Wallboxvermogen telt niet mee' in result.reason


def test_new_60c_accepts_threshold_after_house_and_aeg_reserves():
    at_boundary = dhw_allocation(actual_grid=-5650, filtered_grid=-5650)
    assert at_boundary.allowed
    assert at_boundary.usable_surplus_w == at_boundary.required_surplus_w == 3500
    holding = dhw_allocation(actual_grid=-2800, filtered_grid=-2800,
                             holding_owned_high=True)
    assert holding.allowed
    assert holding.required_surplus_w == 0
    assert holding.usable_surplus_w == 650


def test_holding_60c_releases_if_other_reserves_exceed_real_export():
    result = dhw_allocation(actual_grid=-1800, filtered_grid=-1800,
                            holding_owned_high=True)
    assert not result.allowed
    assert result.grid_surplus_w == -350


def test_idle_tank_at_native_restart_threshold_reacquires_full_start_proof():
    result = dhw_allocation(actual_grid=-2800, filtered_grid=-2800,
        holding_owned_high=True, restart_proof_required=True)
    assert not result.allowed
    assert result.required_surplus_w == 3500


def test_new_or_native_restart_60c_respects_quarter_hour_capacity():
    short = dhw_allocation(capacity_guard_enabled=True,
        optional_import_headroom_w=3199)
    assert not short.allowed
    assert short.optional_import_headroom_w == 3199
    assert '3200 W nodig' in short.reason
    assert dhw_allocation(capacity_guard_enabled=True,
        optional_import_headroom_w=3200).allowed
    restart = dhw_allocation(holding_owned_high=True,
        restart_proof_required=True, capacity_guard_enabled=True,
        optional_import_headroom_w=0)
    assert not restart.allowed and 'kwartierpiekruimte' in restart.reason


def test_verified_owned_60c_heater_is_not_counted_twice_by_capacity_guard():
    result = dhw_allocation(actual_grid=-2800, filtered_grid=-2800,
        holding_owned_high=True, capacity_guard_enabled=True,
        optional_import_headroom_w=0)
    assert result.allowed
    assert result.optional_import_headroom_w == 0


@pytest.mark.parametrize('valid,headroom', [(False, 5000), (True, None),
                                            (True, float('nan'))])
def test_capacity_guard_fails_closed_on_unknown_or_invalid_headroom(valid, headroom):
    result = dhw_allocation(capacity_guard_enabled=True,
        capacity_valid=valid, optional_import_headroom_w=headroom)
    assert not result.allowed
    assert 'niet betrouwbaar bekend' in result.reason


def test_dhw_allocation_uses_more_conservative_raw_or_filtered_p1():
    result = dhw_allocation(actual_grid=-7000, filtered_grid=-5000)
    assert not result.allowed
    assert result.grid_surplus_w == result.usable_surplus_w == 2850


@pytest.mark.parametrize('key,value', [
    ('actual_grid', None), ('filtered_grid', None), ('pv_w', None),
    ('pv_w', float('nan')), ('discharge_w', -1),
    ('unmetered_aeg_reserve_w', None), ('reserve_w', -1),
])
def test_dhw_allocation_fails_closed_on_unknown_or_invalid_evidence(key, value):
    result = dhw_allocation(**{key: value})
    assert not result.allowed
    assert 'niet volledig betrouwbaar bekend' in result.reason


def test_dhw_allocation_fails_closed_on_unreliable_owned_commitment():
    state = State(owned=True, on=True, target_w=1000, measured_w=200)
    state.available = False
    result = dhw_allocation(states={'other': state})
    assert not result.allowed
    assert 'toegewezen toestelvermogen' in result.reason


def test_dhw_allocation_fails_closed_on_unreliable_active_aeg():
    p = DishwasherPriority()
    p.view.active_ids = {'dw'}
    state = State(on=True, available=False)
    result = dhw_allocation(p, states={'dw': state})
    assert not result.allowed
    assert 'afwasstatus of -vermogen' in result.reason


def test_owned_unconsumed_commitment_is_reserved_for_dhw_allocation():
    other = State(owned=True, on=True, target_w=1000, measured_w=200)
    result = dhw_allocation(actual_grid=-6400, filtered_grid=-6400,
                            states={'other': other})
    assert not result.allowed
    assert result.unconsumed_commitment_w == 800
    assert result.usable_surplus_w == 3450


def test_fitting_idle_aeg_gets_first_chance_even_with_ample_surplus():
    p = DishwasherPriority()
    p.view.candidate_ids = p.view.fitting_ids = {'dw'}
    result = dhw_allocation(p, actual_grid=-10000, filtered_grid=-10000)
    assert not result.allowed
    assert 'eerst startkans' in result.reason


def test_wallbox_credit_never_increases_dhw_60c_allocation():
    p = DishwasherPriority()
    p.view.active_ids = {'dw'}
    p.view.ev_credit = {'dw': 5000}
    result = dhw_allocation(p, actual_grid=-5000, filtered_grid=-5000)
    assert not result.allowed
    assert result.usable_surplus_w == 2850

@pytest.mark.parametrize('mode',['observe','paused'])
def test_modes_never_release_lower_or_share_ev(mode):
    v=advance(DishwasherPriority(),inputs(mode=mode))
    assert not v.holds and not v.ev_credit


def test_sample_gap_resets_stability():
    p=DishwasherPriority();kw=inputs(actual_grid=-1950,filtered_grid=-1950)
    p.evaluate(**kw)
    assert not p.evaluate(**{**kw,'now':kw['now']+400}).holds


def test_minimum_compressor_runtime_wins_over_priority_hold():
    kw=inputs(actual_grid=-1950,filtered_grid=-1950);v=advance(DishwasherPriority(),kw)
    kw['states']['low'].last_on=1200
    site=Site(now=1300,grid_w=-1950,filtered_grid_w=-1950,priority_ids={'dw'},device_holds=v.holds)
    result=plan(site,list(kw['devices'].values()),kw['states'])
    assert not result.action
    assert 'minimale looptijd' in result.reasons['low']


def test_release_is_serialized_before_a_dishwasher_start():
    kw=inputs(actual_grid=-1950,filtered_grid=-1950);v=advance(DishwasherPriority(),kw)
    site=Site(now=1300,grid_w=-1950,filtered_grid_w=-1950,priority_ids={'dw'},device_holds=v.holds)
    result=plan(site,list(kw['devices'].values()),kw['states'])
    assert result.action.id=='low' and result.action.watts==0


def test_preferred_dishwasher_outweighs_lower_numeric_priority():
    kw=inputs();states=kw['states'];states['low']=State()
    ds=[replace(d,start_delay_s=0,min_off_s=0) for d in kw['devices'].values()]
    p=plan(Site(now=1000,grid_w=-2400,filtered_grid_w=-2400,priority_ids={'dw'}),ds,states)
    assert p.action.id=='dw'


def test_engine_protected_sharing_separate_from_rollback_handover():
    d=Device('dw',kind='dishwasher',nominal_w=2000,non_interruptible=True,start_delay_s=0,min_off_s=0)
    site=Site(now=1000,grid_w=0,filtered_grid_w=0,reclaimable_w=2500,
              priority_ids={'dw'},protected_ev_credit={'dw':2500})
    result=plan(site,[d],{'dw':State()})
    assert result.action.watts==2000
    assert result.action.protected_ev_w==2000 and result.action.reclaimed_w==0
    assert not plan(replace(site,max_import_w=1900),[d],{'dw':State()}).action
    assert not plan(replace(site,device_increase_limits={'dw':1500}),[d],{'dw':State()}).action

@pytest.mark.parametrize('mut', [dict(priority_ids=set()),dict(protected_ev_credit={}),dict(no_reclaim_ids={'dw'}),dict(can_increase=False),dict(mode='paused'),dict(valid=False)])
def test_sharing_never_bypasses_explicit_engine_guards(mut):
    d=Device('dw',kind='dishwasher',nominal_w=2000,non_interruptible=True,start_delay_s=0,min_off_s=0)
    s=Site(now=1000,grid_w=0,filtered_grid_w=0,reclaimable_w=2500,priority_ids={'dw'},protected_ev_credit={'dw':2500})
    assert not plan(replace(s,**mut),[d],{'dw':State()}).action


def test_other_noninterruptible_cannot_use_dishwasher_credit():
    d=Device('dw',kind='script',nominal_w=2000,non_interruptible=True,start_delay_s=0,min_off_s=0)
    s=Site(now=1000,grid_w=0,filtered_grid_w=0,reclaimable_w=2500,priority_ids={'dw'},protected_ev_credit={'dw':2500})
    assert not plan(s,[d],{'dw':State()}).action


def test_future_commitment_and_comfort_reserve_are_not_ev_headroom():
    d=Device('dw',kind='dishwasher',nominal_w=2000,non_interruptible=True,start_delay_s=0,min_off_s=0)
    s=Site(now=1000,grid_w=0,filtered_grid_w=0,reclaimable_w=2500,
           priority_ids={'dw'},protected_ev_credit={'dw':2500},comfort_reserve_w=1600)
    assert not plan(s,[d],{'dw':State()}).action


def test_no_pseudo_start_or_stop_from_monitor_and_timeout_only_once():
    p=DishwasherPriority();p.started('dw',100,2000,3000)
    wb=Reading(valid=True,power_w=3000,stamp=200)
    active=SimpleNamespace(active=True,finished=False,stamp=120)
    assert not p.observe(wall=999,readings={'dw':active},grid_w=2000,grid_stamp=999,wb=wb)
    messages=p.observe(wall=1000,readings={'dw':active},grid_w=2000,grid_stamp=1000,wb=wb)
    assert len(messages)==1 and 'dw' in p.ev_blocks
    assert not p.observe(wall=1100,readings={'dw':active},grid_w=2000,grid_stamp=1100,wb=wb)
    p2=DishwasherPriority();p2.restore(p.snapshot(),{'dw':{'kind':'dishwasher'}})
    assert p2.ev_blocks==p.ev_blocks


def test_monitor_needs_new_running_grid_and_ev_evidence():
    p=DishwasherPriority();p.started('dw',100,2000,3000)
    run=SimpleNamespace(active=True,finished=False,stamp=120)
    wb=Reading(valid=True,power_w=1200,stamp=110)
    p.observe(wall=110,readings={'dw':run},grid_w=0,grid_stamp=110,wb=wb)
    p.observe(wall=141,readings={'dw':run},grid_w=0,grid_stamp=110,wb=wb)
    assert p.watches['dw']['status']=='waiting'
    p.observe(wall=145,readings={'dw':run},grid_w=0,grid_stamp=145,wb=wb)
    assert p.watches['dw']['status']=='balanced'
    p.observe(wall=160,readings={'dw':SimpleNamespace(active=False,finished=True)},grid_w=0,grid_stamp=160,wb=wb)
    assert not p.watches


def solar_case(monkeypatch, **cfg):
    r,h,c,w=configured(monkeypatch,**cfg)
    r.settings.update(pv_entity='sensor.pv',reserve_w=150)
    h.states.set('sensor.pv',5000,{'unit_of_measurement':'W'})
    h.states.set('sensor.grid',0,{'unit_of_measurement':'W'})
    r.wallbox_settings.update(enabled=True,stable_s=0,policy='house_first',max_takeover_w=2500,power_entity='sensor.ev')
    r.wallbox_guard=HouseFirstGuard(r.wallbox_settings)
    r._wallbox_reading=lambda:Reading(valid=True,power_w=3000,status='Charging',mode='full_solar',
        age_s=0,stamp=w[0],connected=True,demand=True)
    ready(r,h,c,w)
    return r,h,c,w

@pytest.mark.asyncio
async def test_end_to_end_priority_start_without_shelly_never_writes_wallbox(monkeypatch):
    r,h,c,w=solar_case(monkeypatch)
    await r.tick()
    assert [x[:2] for x in h.services.calls]==[('button','press')], (r.result, r.problem, r.dishwasher_priority.view, r.dhw.status, r.wallbox_guard.result, r.states)
    assert r.pending and r.dishwasher_priority.watches['a']['borrowed_w']==2000
    assert r.handover is None
    assert r.store.data['dishwasher_priority']['watches']['a']['issued_wall']==w[0]
    assert r.overview()[0]['dishwasher']['priority_policy']['configured']

@pytest.mark.asyncio
@pytest.mark.parametrize('limit',[0,1000,1999])
async def test_runtime_does_not_start_if_immediate_grid_headroom_missing(monkeypatch,limit):
    r,h,c,w=solar_case(monkeypatch);r.settings['max_import_w']=limit
    await r.tick()
    assert not [x for x in h.services.calls if x[0]=='button']

@pytest.mark.asyncio
async def test_live_mode_not_full_solar_remains_only_real_surplus(monkeypatch):
    r,h,c,w=solar_case(monkeypatch)
    r._wallbox_reading=lambda:Reading(valid=True,power_w=3000,status='Charging',mode='disabled',age_s=0,stamp=w[0],connected=True,demand=True)
    await r.tick();assert not [x for x in h.services.calls if x[0]=='button']

@pytest.mark.asyncio
async def test_user_can_disable_ev_sharing_now(monkeypatch):
    r,h,c,w=solar_case(monkeypatch,dishwasher_ev_solar_priority=False)
    await r.tick();assert not [x for x in h.services.calls if x[0]=='button']
    assert r.dishwasher_priority.view.candidate_ids == {'a'}
    assert not r.dishwasher_priority.view.luxury_block

@pytest.mark.asyncio
async def test_after_priority_start_program_cannot_be_stopped_even_on_grid(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);await r.tick()
    w[0]+=3;event(r,h,c,w,'dishwasher_state_entity','Running')
    h.states.set('sensor.grid',2800,{'unit_of_measurement':'W'})
    await r.tick();r.mode='paused';await r.tick();await r._send(Action('a',0,'test'),time.monotonic())
    assert [x[:2] for x in h.services.calls if x[0]!='persistent_notification']==[('button','press')]

@pytest.mark.asyncio
async def test_latched_end_clears_priority_after_brief_end_event(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);await r.tick()
    w[0]+=3;event(r,h,c,w,'dishwasher_state_entity','Running');await r.tick()
    w[0]+=100;event(r,h,c,w,'dishwasher_state_entity','End Of Cycle')
    w[0]+=4;event(r,h,c,w,'dishwasher_state_entity','Off');await r.tick()
    assert not r.dishwasher_priority.watches
    assert not r.dishwasher_priority.view.luxury_block

@pytest.mark.asyncio
async def test_dispatch_rejects_changed_ev_mode_after_plan(monkeypatch):
    r,h,c,w=solar_case(monkeypatch)
    original=r._send
    async def changed(action,now):
        r._wallbox_reading=lambda:Reading(valid=True,power_w=3000,status='Charging',mode='disabled',age_s=0,stamp=w[0],connected=True,demand=True)
        await original(action,now)
    r._send=changed;await r.tick()
    assert not [x for x in h.services.calls if x[0]=='button']


def boiler(r,h,target=50,temp=50,protected=False):
    from custom_components.solar_pilot.dhw_runtime import DHWManager
    h.config=SimpleNamespace(time_zone='Europe/Brussels',units=SimpleNamespace(temperature_unit='°C'))
    r.entry.options['dhw']={'enabled':True,'safety_confirmed':True,'target_entity':'water_heater.tank',
        'temperature_entity':'sensor.tank','cooling_entities':['climate.floor'],'normal_c':50,
        'solar_c':50,'surplus_c':60,'night_enabled':False,'hygiene_schedule_enabled':False,
        'optional_raise_interval_s':0,'rise_delay_s':0,'fall_delay_s':0,'minimum_c':46}
    h.states.set('water_heater.tank','idle',{'temperature':target,'temperature_unit':'°C','min_temp':40,'max_temp':65,'target_temp_step':1,'supported_features':1})
    h.states.set('sensor.tank',temp,{'unit_of_measurement':'°C'})
    h.states.set('climate.floor','auto',{'hvac_action':'idle'})
    r.dhw=DHWManager(r)
    if protected:
        r.dhw.config['hygiene_entity']='binary_sensor.hygiene';h.states.set('binary_sensor.hygiene','on')


def test_runtime_dhw_allocation_receives_existing_capacity_guard(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);boiler(r,h)
    r.states['a'].on=True
    r.dishwasher_priority.view.active_ids={'a'}
    r._dishwasher_unmetered_reserve=2000
    r.filtered=-6000
    r.pv_w=9000
    r.capacity=SimpleNamespace(enabled=True,valid=True,optional_headroom_w=500)
    r.capacity_settings['respect_optional_dhw']=True
    local=datetime.fromtimestamp(w[0],timezone.utc)
    reading=r.dhw.read(-6000,True,0,local)
    r.dhw._prepare_comfort(local,reading)
    assert not reading.luxury_allowed
    assert '500 W kwartierpiekruimte' in reading.luxury_reason

@pytest.mark.asyncio
async def test_priority_blocks_extra60_but_not_normal50(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);boiler(r,h)
    h.states.set('sensor.grid',-5000,{'unit_of_measurement':'W'})
    await r.tick()
    assert not [x for x in h.services.calls if x[0]=='water_heater' and x[2].get('temperature')==60]
    assert r.dhw.policy.result.target_c==50
    assert [x for x in h.services.calls if x[0]=='button']


async def running_aeg_with_boiler(monkeypatch, export_w):
    r,h,c,w=solar_case(monkeypatch)
    await r.tick()
    w[0]+=3
    event(r,h,c,w,'dishwasher_state_entity','Running')
    await r.tick()
    assert r.states['a'].on and r.states['a'].owned and not r.pending
    boiler(r,h)
    h.services.calls.clear()
    w[0]+=30
    h.states.set('sensor.pv',9000,{'unit_of_measurement':'W'})
    h.states.set('sensor.grid',-export_w,{'unit_of_measurement':'W'})
    r.filtered=-export_w
    r.last_issued=-1e12
    await r.tick()
    return r,h,c,w


@pytest.mark.asyncio
async def test_active_unmetered_aeg_allows_60c_with_enough_real_surplus(monkeypatch):
    r,h,_,_=await running_aeg_with_boiler(monkeypatch,6000)
    assert r._dishwasher_unmetered_reserve == 2000
    assert r.dhw.reading.luxury_allowed
    assert r.dhw.policy.result.target_c == 60
    assert [x for x in h.services.calls
            if x[0]=='water_heater' and x[2].get('temperature')==60]
    assert not [x for x in h.services.calls if x[0]=='button']


@pytest.mark.asyncio
async def test_active_unmetered_aeg_blocks_60c_when_reserved_surplus_is_short(monkeypatch):
    r,h,_,_=await running_aeg_with_boiler(monkeypatch,5000)
    assert not r.dhw.reading.luxury_allowed
    assert r.dhw.policy.result.target_c == 50
    assert '2850 W werkelijk vrij' in r.dhw.reading.luxury_reason
    assert not [x for x in h.services.calls if x[0]=='water_heater']


@pytest.mark.asyncio
async def test_confirmed_60c_does_not_count_verified_own_heater_twice(monkeypatch):
    r,h,_,w=await running_aeg_with_boiler(monkeypatch,6000)
    r.dhw.config['power_entity']=r.dhw.settings['power_entity']='sensor.boiler_power'
    h.states.set('sensor.boiler_power',3200,{'unit_of_measurement':'W'})
    tank=h.states.get('water_heater.tank')
    h.states.set('water_heater.tank','idle',
        {**tank.attributes,'temperature':60,'hvac_action':'heating'})
    r.dhw.pending=None
    r.dhw.owned_target=60
    h.services.calls.clear()
    w[0]+=30
    h.states.set('sensor.grid',-2800,{'unit_of_measurement':'W'})
    r.filtered=-2800
    r.last_issued=-1e12
    await r.tick()
    assert r.dhw.reading.luxury_allowed
    assert r.dhw.policy.result.target_c == 60
    assert not [x for x in h.services.calls if x[0]=='water_heater']


@pytest.mark.asyncio
async def test_confirmed_60c_releases_when_aeg_reserve_exceeds_export(monkeypatch):
    r,h,_,w=await running_aeg_with_boiler(monkeypatch,6000)
    r.dhw.config['power_entity']=r.dhw.settings['power_entity']='sensor.boiler_power'
    h.states.set('sensor.boiler_power',3200,{'unit_of_measurement':'W'})
    tank=h.states.get('water_heater.tank')
    h.states.set('water_heater.tank','idle',
        {**tank.attributes,'temperature':60,'hvac_action':'heating'})
    r.dhw.pending=None
    r.dhw.owned_target=60
    h.services.calls.clear()
    w[0]+=30
    h.states.set('sensor.grid',-1800,{'unit_of_measurement':'W'})
    r.filtered=-1800
    r.last_issued=-1e12
    await r.tick()
    assert not r.dhw.reading.luxury_allowed
    assert r.dhw.policy.result.target_c == 50
    assert [x for x in h.services.calls
            if x[0]=='water_heater' and x[2].get('temperature')==50]


@pytest.mark.asyncio
async def test_holding_60c_without_heating_proof_invents_no_own_power(monkeypatch):
    r,h,_,w=await running_aeg_with_boiler(monkeypatch,6000)
    tank=h.states.get('water_heater.tank')
    h.states.set('water_heater.tank','idle',
        {**tank.attributes,'temperature':60,'hvac_action':'idle'})
    r.dhw.pending=None
    r.dhw.owned_target=60
    h.services.calls.clear()
    w[0]+=30
    h.states.set('sensor.grid',-2800,{'unit_of_measurement':'W'})
    r.filtered=-2800
    r.last_issued=-1e12
    await r.tick()
    assert not r.dhw.reading.luxury_allowed
    assert r.dhw.policy.result.target_c == 50
    assert '650 W werkelijk vrij' in r.dhw.reading.luxury_reason


@pytest.mark.asyncio
async def test_active_aeg_never_weakens_cooling_cap(monkeypatch):
    r,h,_,w=await running_aeg_with_boiler(monkeypatch,6000)
    tank=h.states.get('water_heater.tank')
    h.states.set('water_heater.tank','idle',
        {**tank.attributes,'temperature':60})
    r.dhw.pending=None
    r.dhw.owned_target=60
    h.services.calls.clear()
    w[0]+=30
    h.states.set('climate.floor','cool',{'hvac_action':'cooling'})
    h.states.set('sensor.grid',-8000,{'unit_of_measurement':'W'})
    r.filtered=-8000
    r.last_issued=-1e12
    await r.tick()
    assert r.dhw.policy.result.cooling_block
    assert r.dhw.policy.result.target_c == 50
    assert [x for x in h.services.calls
            if x[0]=='water_heater' and x[2].get('temperature')==50]

@pytest.mark.asyncio
async def test_normal_comfort_is_dispatched_before_dishwasher(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);boiler(r,h,target=45,temp=44)
    await r.tick()
    calls=[x for x in h.services.calls if x[0]!='persistent_notification']
    assert calls and calls[0][:2]==('water_heater','set_temperature'), (r.dhw.status, r.result, r.problem)
    assert calls[0][2]['temperature']==50
    assert not [x for x in calls if x[0]=='button']

@pytest.mark.asyncio
async def test_sterilization_not_lowered_for_dishwasher(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);boiler(r,h,target=62,temp=52,protected=True)
    await r.tick()
    assert not [x for x in h.services.calls if x[0] in ('water_heater','button')]
    assert r.dhw.reading.protected and r._dishwasher_comfort_reserve >= 3200

@pytest.mark.asyncio
async def test_active_floor_not_shut_off_and_can_share_if_enough_real_power(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);boiler(r,h)
    h.states.set('climate.floor','heat',{'hvac_action':'heating'})
    h.states.set('sensor.grid',-2500,{'unit_of_measurement':'W'})
    await r.tick()
    assert [x for x in h.services.calls if x[0]=='button']
    assert not [x for x in h.services.calls if x[0]=='climate']

@pytest.mark.asyncio
async def test_deadline_still_reserves_imminent_normal_hot_water(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);boiler(r,h,target=50,temp=44)
    h.states.set('sensor.grid',400,{'unit_of_measurement':'W'})
    move(h,w,'2026-09-29T13:00')
    await r.tick()
    assert r._dishwasher_comfort_reserve==3200
    assert not [x for x in h.services.calls if x[0]=='button']
    assert r.dhw.policy.result.target_c==50

@pytest.mark.asyncio
async def test_deadline_unknown_boiler_does_not_bypass_comfort_block(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);boiler(r,h)
    move(h,w,'2026-09-29T13:00');h.states.set('sensor.tank','unavailable')
    await r.tick()
    assert 'a' in r.dishwasher_priority.view.blocks
    assert not [x for x in h.services.calls if x[0]=='button']

@pytest.mark.asyncio
async def test_sterilization_with_ample_power_does_not_veto_all_washes(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);boiler(r,h,target=62,temp=52,protected=True)
    h.states.set('sensor.grid',-6500,{'unit_of_measurement':'W'});h.states.set('sensor.pv',9000,{'unit_of_measurement':'W'})
    await r.tick()
    assert [x for x in h.services.calls if x[0]=='button']
    assert not [x for x in h.services.calls if x[0]=='water_heater']

@pytest.mark.asyncio
async def test_operating_mode_heating_is_not_measured_compressor_activity(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);boiler(r,h,target=50,temp=44)
    state=h.states.get('water_heater.tank')
    h.states.set('water_heater.tank','heating',state.attributes)
    await r.tick()
    assert r._dishwasher_comfort_reserve==3200
    assert not [x for x in h.services.calls if x[0]=='button']

@pytest.mark.asyncio
async def test_tomorrow_request_does_not_impose_today_reservations(monkeypatch):
    r,h,c,w=solar_case(monkeypatch,when='2026-09-29T16:00');boiler(r,h,target=50,temp=44)
    await r.tick()
    assert r._dishwasher_comfort_reserve==0
    assert not r.dishwasher_priority.view.luxury_block

@pytest.mark.asyncio
async def test_running_unmetered_cycle_retains_future_heater_reservation(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);await r.tick()
    w[0]+=3;event(r,h,c,w,'dishwasher_state_entity','Running')
    await r.tick()
    assert r._dishwasher_unmetered_reserve==2000
    assert r.overview()[0]['dishwasher']['priority_policy']['unmetered_reserve_w']==2000
    assert not r.handover

@pytest.mark.asyncio
async def test_real_solar_still_works_after_failed_ev_sharing(monkeypatch):
    r,h,c,w=solar_case(monkeypatch)
    r.dishwasher_priority.ev_blocks['a']='Controle vereist voor EV-vermogen'
    h.states.set('sensor.grid',-2500,{'unit_of_measurement':'W'})
    await r.tick()
    assert [x for x in h.services.calls if x[0]=='button']
    assert not r.dishwasher_priority.watches


def test_multiple_lower_loads_release_only_the_minimum_set():
    kw=inputs(actual_grid=-2000,filtered_grid=-2000)
    kw['devices']['low2']=Device('low2',priority=99,nominal_w=300)
    kw['states']['low2']=State(owned=True,on=True,measured_w=300,target_w=300)
    kw['configs']['low2']={'kind':'switch'};kw['lower_measured']['low2']=300
    v=advance(DishwasherPriority(),kw)
    assert set(v.holds)=={'low2'}


def test_one_ev_credit_pool_is_not_allocated_to_multiple_claimants():
    kw=inputs(actual_grid=0,filtered_grid=0,lower_measured={})
    kw['devices']['dw2']=replace(kw['devices']['dw'],id='dw2',priority=60)
    kw['states']['dw2']=State();kw['configs']['dw2']={'kind':'dishwasher'}
    kw['permitted_ids'].add('dw2');kw['reading']=replace(kw['reading'],power_w=3000)
    kw['stable_ev_credit_w']=3000
    v=advance(DishwasherPriority(),kw)
    assert set(v.ev_credit)=={'dw'}

@pytest.mark.asyncio
async def test_needed_evening_reserve_has_priority_but_luxury_does_not(monkeypatch):
    r,h,c,w=solar_case(monkeypatch);boiler(r,h,target=55,temp=48)
    r.dhw.read(0,True,0,datetime.fromtimestamp(w[0],timezone.utc))
    assert r._dishwasher_comfort_context()[0]==3200
    state=h.states.get('water_heater.tank')
    h.states.set('water_heater.tank','idle',{**state.attributes,'temperature':60})
    r.dhw.read(0,True,0,datetime.fromtimestamp(w[0],timezone.utc))
    assert r._dishwasher_comfort_context()[0]==0
