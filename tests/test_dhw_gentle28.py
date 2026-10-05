"""Beta.28 gentle setpoint contract; all appliances are explicit test doubles."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
import pytest
from custom_components.solar_pilot.dhw import (
    DHW_DEFAULTS, DHWPolicy, DHWReading, effective_base_target,
    normalized_settings, validate_settings,
)
from custom_components.solar_pilot.dhw_schedule import DHWComfortSchedule
from custom_components.solar_pilot.dhw_runtime import DHWManager
from test_dhw_runtime import setup, tick, updates

TZ = ZoneInfo('Europe/Brussels')
def at(hour, minute=0, day=29):
    return datetime(2026, 9, day, hour, minute, tzinfo=TZ)
def config(**kw):
    return {**DHW_DEFAULTS, 'hygiene_schedule_enabled': False, **kw}
def schedule(model=None, *, temp=47, now=None, **kw):
    model = model or DHWComfortSchedule()
    args = dict(c=config(), now=now or at(8), temperature=temp,
                pv_w=0, grid_w=600, before_ev_w=0, night=(now or at(8)).hour < 6)
    args.update(kw)
    return model.plan(**args)
def actuator_calls(h):
    return [x for x in h.services.calls if x[0] != 'persistent_notification']

@pytest.mark.parametrize('floor,delta,buffer', [(46,-5,1),(48,-12,5),(40,-2,0)])
def test_floor_and_native_differential_never_raise_normal_target(floor, delta, buffer):
    c=config(minimum_c=floor,tank_differential_c=delta,minimum_buffer_c=buffer)
    assert effective_base_target(c)==50

@pytest.mark.parametrize('hour,temp', [(2,40),(5,45),(6,45.9),(8,46.2),(9,44),(16,45)])
def test_no_solar_morning_and_minimum_only_offer_fifty(hour,temp):
    p=schedule(temp=temp,now=at(hour),c=config(morning_enabled=True,evening_enabled=True,
               night_policy='minimum_until_solar',morning_cap_c=60))
    assert p.target_c in (None,50)
    assert p.standby_target_c in (None,50)
    assert p.native_restart_c==45
    assert 'geen gegarandeerd minimum' in p.limit_note

@pytest.mark.parametrize('minute', [0,15,30])
def test_morning_missing_floor_is_explicit_not_declared_success(minute):
    p=schedule(temp=45.5,now=at(9,minute),c=config(morning_enabled=True,morning_c=45))
    assert p.below_floor and 'nog niet gehaald' in p.warning and 'gewenst 46' in p.warning
    assert p.target_c==50

def test_old_emergency_and_morning_boost_are_never_replayed():
    m=DHWComfortSchedule();m.restore({'emergency':True,'morning_day':'2026-09-29','morning_target':55})
    p=schedule(m,temp=44,now=at(8),c=config(morning_enabled=True))
    assert p.target_c==50 and m.emergency is False and m.morning_target is None

def test_evening_works_without_forced_morning_control():
    p=schedule(temp=49,now=at(16),c=config(evening_enabled=True,morning_enabled=False),
               pv_w=5000,grid_w=-4000,before_ev_w=4000)
    assert p.stage=='evening' and 50 < p.target_c <= 55

def test_evening_reserve_does_not_raise_to_defeat_native_hysteresis():
    c=config(evening_enabled=True,tank_loss_fallback_c_h=.05,
             evening_draw_buffer_c=3,morning_margin_c=1)
    p=schedule(temp=50.1,now=at(16),c=c,pv_w=5000,grid_w=-4000,before_ev_w=4000)
    # 46 + 17*.05 + 3 + 1 = 50.85 -> 51, NOT current temperature + 5 + margin.
    assert p.target_c==51
    assert 'herstartdrempel' in p.warning

def test_evening_single_reserve_does_not_creep_up_and_survives_restart():
    m=DHWComfortSchedule();c=config(evening_enabled=True)
    p=schedule(m,temp=49,now=at(15),c=c,pv_w=5000,grid_w=-4000,before_ev_w=4000)
    target=p.target_c
    p=schedule(m,temp=target,now=at(15,10),c=c,pv_w=5000,grid_w=-4000,before_ev_w=4000)
    assert p.evening_completed and p.target_c is None
    n=DHWComfortSchedule();n.restore(m.snapshot())
    p=schedule(n,temp=48,now=at(17),c=c,pv_w=5000,grid_w=-4000,before_ev_w=4000)
    assert p.evening_completed and p.target_c is None
    p=schedule(n,temp=48,now=at(16,day=30),c=c,pv_w=5000,grid_w=-4000,before_ev_w=4000)
    assert not p.evening_completed and p.stage=='evening'

@pytest.mark.parametrize('pv,before',[(0,5000),(5000,0),(5000,3300),(None,5000)])
def test_evening_requires_real_solar_not_only_forecast(pv,before):
    p=schedule(temp=48,now=at(16),c=config(evening_enabled=True),pv_w=pv,
              before_ev_w=before,forecast_available=True,forecast_slots=[(at(17),5000)])
    assert p.target_c is None

@pytest.mark.parametrize('busy', [True,None])
def test_optional_heat_waits_for_space_climate_but_normal_target_remains(busy):
    p=DHWPolicy(config(rise_delay_s=0,fall_delay_s=0,cooling_clear_s=0))
    r=DHWReading(47,50,5000,4000,4000,-4000,False,space_climate_busy=busy)
    d=p.update(1,at(15),r)
    assert d.target_c==50 and d.stage=='space_priority'
    r.temperature_c=44;r.actual_target_c=48;r.pv_w=0;r.export_w=0
    d=p.update(2,at(15),r)
    assert d.target_c==50

def test_space_heating_does_not_interrupt_an_already_requested_high_target():
    p=DHWPolicy(config(rise_delay_s=0,fall_delay_s=0,cooling_clear_s=0))
    r=DHWReading(48,60,6000,4500,4500,-4500,False,space_climate_busy=True)
    assert p.update(1,at(15),r).target_c==60

@pytest.mark.parametrize('action', ['heating','preheating','cooling','defrosting'])
def test_real_space_actions_are_detected(action):
    r,h=setup();h.states.set('climate.home','auto',{'hvac_action':action})
    assert r.dhw._space_activity()[0] is True

def test_heat_mode_idle_is_not_actual_heating():
    r,h=setup();h.states.set('climate.home','heat',{'hvac_action':'idle'})
    assert r.dhw._space_activity()==(False,'')

def test_unknown_space_status_is_not_treated_as_idle():
    r,h=setup();h.states.set('climate.home','unavailable')
    assert r.dhw._space_activity()[0] is None

@pytest.mark.asyncio
@pytest.mark.parametrize('hour',[2,6,8,9])
async def test_low_no_solar_never_commands_fifty_two_force_dhw_or_modes(hour):
    r,h=setup(config={'morning_enabled':True,'evening_enabled':True,
                      'night_policy':'minimum_until_solar','morning_cap_c':60})
    r.pv_w=0;updates(h,'water_heater.boiler',temperature=48)
    await tick(r,grid=800,hour=hour);await tick(r,grid=800,hour=hour)
    assert actuator_calls(h)==[('water_heater','set_temperature',{'entity_id':'water_heater.boiler','temperature':50})]

@pytest.mark.asyncio
async def test_stable_fifty_does_not_spam_commands_even_below_floor():
    r,h=setup(config={'morning_enabled':True});r.pv_w=0
    for _ in range(80):await tick(r,grid=800,hour=8)
    assert actuator_calls(h)==[]
    assert r.dhw.overview()['comfort_plan']['below_floor']

@pytest.mark.asyncio
async def test_space_heat_does_not_force_boiler_when_ample_solar():
    r,h=setup();h.states.set('climate.home','heat',{'hvac_action':'heating'})
    await tick(r,grid=-5000,hour=15)
    assert actuator_calls(h)==[] and r.dhw.policy.result.target_c==50

@pytest.mark.asyncio
async def test_optional_interval_keeps_hysteresis_from_authorizing_untested_export():
    r,h=setup(config={'optional_raise_interval_s':1800})
    r.dhw.last_command_wall=time.time()
    await tick(r,grid=-4500,hour=15)
    assert actuator_calls(h)==[] and 'wacht nog' in r.dhw.status
    assert r.dhw.policy.current is None
    # No former *unexecuted* high state may use the lower 2700 W hold threshold.
    r.dhw.last_command_wall=time.time()-1801
    await tick(r,grid=-2800,hour=15)
    assert actuator_calls(h)==[]
    await tick(r,grid=-4500,hour=15)
    assert actuator_calls(h)[0][2]['temperature']==60

@pytest.mark.asyncio
async def test_optional_interval_does_not_delay_real_import_reduction():
    r,h=setup();await tick(r,grid=-4500,hour=15);await tick(r,grid=-4500,hour=15)
    await tick(r,grid=1000,hour=15)
    assert [x[2]['temperature'] for x in actuator_calls(h)]==[60,50]

@pytest.mark.asyncio
@pytest.mark.parametrize('mode,approved',[('observe',True),('paused',True),('solar',False)])
async def test_gentle_features_preserve_permissions_and_modes(mode,approved):
    r,h=setup(config={'morning_enabled':True,'evening_enabled':True,'safety_confirmed':approved})
    r.mode=mode;r.pv_w=0;updates(h,'water_heater.boiler',temperature=48)
    await tick(r,grid=1000,hour=8)
    assert actuator_calls(h)==[]

@pytest.mark.asyncio
async def test_factory_sterilization_never_lowered_by_floor_or_solar():
    r,h=setup(config={'morning_enabled':True,'evening_enabled':True})
    updates(h,'water_heater.boiler',temperature=62)
    h.states.set('binary_sensor.hygiene','on')
    await tick(r,grid=3000,hour=15)
    assert actuator_calls(h)==[]

def test_command_interval_survives_restart_without_replaying_a_command():
    r,h=setup();r.dhw.last_command_wall=time.time()-5
    data=r.dhw.snapshot();n=DHWManager(r);n.restore(data)
    assert n.last_command_wall==data['last_command_wall']
    assert n.pending is None and n.owned_target is None

def test_new_defaults_are_fifty_forty_six_and_not_automatically_enabled():
    c=normalized_settings()
    assert (c['normal_c'],c['minimum_c'])==(50,46)
    assert not c['enabled'] and not c['safety_confirmed']
    assert c['respect_space_climate'] and c['optional_raise_interval_s']==1800

@pytest.mark.parametrize('old,normal,floor',[
    ({'minimum_c':43,'tank_differential_c':-5,'minimum_buffer_c':1},49,43),
    ({'minimum_c':44,'tank_differential_c':-4,'minimum_buffer_c':1},49,44),
    ({'normal_c':50,'minimum_c':46,'minimum_buffer_c':5},50,46),
])
def test_old_target_migration_preserves_choices_and_new_normal_is_independent(old,normal,floor):
    c=normalized_settings(old)
    assert c['normal_c']==normal and c['minimum_c']==floor
    c['minimum_c']=46;c['tank_differential_c']=-12
    assert normalized_settings(c)['normal_c']==normal

@pytest.mark.parametrize('bad',[float('nan'),float('inf'),60.1,30])
def test_invalid_normal_target_rejected(bad):
    assert validate_settings(config(normal_c=bad))

@pytest.mark.asyncio
async def test_under_floor_log_is_not_repeated_every_cycle():
    r,h=setup();r.pv_w=0
    for _ in range(80):await tick(r,grid=800,hour=8)
    rows=[x for x in r.logs if 'onder bewaakte comfortgrens' in x['message']]
    assert len(rows)==1


def test_new_settings_are_exposed_with_release_bound_help():
    import json
    from pathlib import Path
    from custom_components.solar_pilot.dhw import DHW_NUMBERS
    assert {'normal_c','minimum_c'} <= set(DHW_NUMBERS)
    assert 'minimum_buffer_c' not in DHW_NUMBERS
    catalog=json.loads((Path(__file__).parents[1]/'custom_components/solar_pilot/frontend/option-help.json').read_text())
    for step,key in [('dhw_rules','normal_c'),('dhw_rules','minimum_c'),
                     ('dhw_stability','respect_space_climate'),('dhw_stability','optional_raise_interval_s')]:
        assert len(' '.join(catalog['entries'][step+'.'+key]['paragraphs']))>100


def test_low_tank_never_bypasses_solar_stability_for_optional_sixty():
    p=DHWPolicy(config(rise_delay_s=300,cooling_clear_s=0))
    r=DHWReading(44,50,6000,5000,5000,-5000,False)
    for t in range(0,300,5):
        d=p.update(t,at(16),r)
        assert d.target_c==50 and d.remaining_s>0
    assert p.update(300,at(16),r).target_c==60


def test_evening_native_step_cannot_round_above_configured_ceiling():
    r,h=setup(config={'evening_enabled':True, 'hygiene_schedule_enabled':False,
                       'evening_cap_c':55, 'morning_c':46,
                       'evening_draw_buffer_c':3})
    updates(h,'water_heater.boiler',min_temp=40,target_temp_step=2,current_temperature=49)
    h.states.set('sensor.water',49,{'unit_of_measurement':'°C'})
    reading=r.dhw.read(-5000,True,0,at(16))
    r.dhw._prepare_comfort(at(16),reading)
    assert r.dhw.comfort.result.evening_target_c==55
    assert reading.comfort_target_c is None
    assert 'geen afronding boven de limiet' in r.dhw.comfort.result.warning
