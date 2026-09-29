"""DHW comfort scheduling, solar reserve and guards; no real appliance commands."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from types import SimpleNamespace
import pytest
from custom_components.solar_pilot.dhw import DHW_DEFAULTS, DHWPolicy, DHWReading, validate_settings
from custom_components.solar_pilot.dhw_schedule import DHWComfortSchedule, TankLearning, elapsed_hours
from test_dhw_runtime import setup, tick

TZ=ZoneInfo('Europe/Brussels')
def at(h,m=0,day=29): return datetime(2026,9,day,h,m,tzinfo=TZ)
def conf(**kw): return {**DHW_DEFAULTS, 'hygiene_schedule_enabled':False, **kw}
def plan(m,now,temp=49,**kw):
    args=dict(c=conf(),now=now,temperature=temp,pv_w=0,grid_w=600,before_ev_w=0,night=now.hour<6 or now.hour>=23)
    args.update(kw)
    return m.plan(**args)

@pytest.mark.parametrize('flags',[{}, {'night_policy':'base'}])
def test_upgrade_no_new_comfort_commands(flags):
    m=DHWComfortSchedule(); p=plan(m,at(7),temp=48,c=conf(**flags))
    assert p.target_c is None and p.standby_target_c is None

def test_night_end_not_a_reheat_start_and_stability_retained():
    m=DHWComfortSchedule();c=conf(night_policy='minimum_until_solar')
    assert plan(m,at(5,59),temp=47,c=c).standby_target_c==50
    p=plan(m,at(6),temp=47,c=c);assert p.standby_target_c==50 and p.target_c is None
    assert plan(m,at(6,1),c=c,pv_w=1100).waiting_for_solar
    assert not plan(m,at(6,6),c=c,pv_w=1100).waiting_for_solar

def test_night_state_survives_restart_after_deadline():
    m=DHWComfortSchedule();c=conf(night_policy='minimum_until_solar')
    plan(m,at(5),c=c);n=DHWComfortSchedule();n.restore(m.snapshot())
    assert plan(n,at(10),c=c).standby_target_c==50

def test_below_minimum_is_monitored_and_never_latches_a_higher_target():
    m=DHWComfortSchedule();c=conf(night_policy='minimum_until_solar')
    p=plan(m,at(3),temp=43,c=c)
    assert p.target_c==50 and p.urgent and p.stage=='minimum_monitor'
    assert plan(m,at(3,5),temp=45,c=c).target_c==50
    assert plan(m,at(4),temp=49,c=c).target_c is None
    assert m.emergency is False

def test_morning_keeps_normal_target_and_does_not_force_start_at_six():
    m=DHWComfortSchedule();c=conf(night_policy='minimum_until_solar',morning_enabled=True)
    assert plan(m,at(6),temp=47,c=c).target_c is None
    p=plan(m,at(8),temp=46.5,c=c)
    assert p.stage=='morning' and p.urgent and p.target_c==50
    assert 'geen extra setpointverhoging' in p.reason and 'vóór Wallbox' in p.reason
    assert plan(m,at(8,5),temp=46.5,c=c).stage=='morning'

def test_warm_morning_tank_does_not_reheat_just_for_deadline():
    m=DHWComfortSchedule();c=conf(morning_enabled=True)
    assert plan(m,at(8),temp=49,c=c).target_c is None

def test_missed_deadline_reports_not_claims_success():
    m=DHWComfortSchedule();p=plan(m,at(9,1),temp=44,c=conf(morning_enabled=True))
    assert 'nog niet gehaald' in p.warning
    assert p.target_c is not None

def test_unachievable_lead_is_visible():
    m=DHWComfortSchedule();p=plan(m,at(6),temp=40,c=conf(morning_enabled=True,tank_heat_fallback_c_h=1))
    assert 'opwarmtijd' in p.warning

def test_morning_stops_after_hold_window():
    m=DHWComfortSchedule();c=conf(morning_enabled=True)
    plan(m,at(8),temp=44,c=c)
    assert plan(m,at(10),temp=44,c=c).stage!='morning'

def test_evening_uses_last_solar_slot_not_blind_sixty():
    m=DHWComfortSchedule();c=conf(morning_enabled=True,evening_enabled=True)
    p=plan(m,at(15),temp=49,c=c,pv_w=5000,grid_w=-4000,before_ev_w=4000,forecast_available=True,forecast_slots=[(at(16),3800),(at(18),2000)])
    assert p.stage=='evening' and 50<p.target_c<=55
    assert p.last_useful_solar.startswith('2026-09-29T16:00')
    assert 'vóór Wallbox' in p.reason

def test_evening_not_in_early_window():
    m=DHWComfortSchedule();c=conf(morning_enabled=True,evening_enabled=True)
    p=plan(m,at(10),c=c,pv_w=5000,before_ev_w=4500,forecast_available=True,forecast_slots=[(at(16),4500)])
    assert p.target_c is None

def test_evening_forecast_alone_cannot_start():
    m=DHWComfortSchedule();c=conf(morning_enabled=True,evening_enabled=True)
    p=plan(m,at(16),c=c,pv_w=5000,grid_w=4000,before_ev_w=0,forecast_available=True,forecast_slots=[(at(17),4500)])
    assert p.target_c is None

def test_evening_own_power_hold_requires_confirmed_ownership():
    c=conf(morning_enabled=True,evening_enabled=True);m=DHWComfortSchedule()
    assert plan(m,at(16),c=c,pv_w=5000,grid_w=-4000,before_ev_w=4000).stage=='evening'
    assert plan(m,at(16,1),c=c,pv_w=5000,grid_w=-100,before_ev_w=100).target_c is None
    assert plan(m,at(16,2),c=c,pv_w=5000,grid_w=-100,before_ev_w=100,holding_evening=True).stage=='evening'
    assert plan(m,at(16,3),c=c,pv_w=5000,grid_w=1000,before_ev_w=0,holding_evening=True).target_c is None

def test_protection_and_unavailable_never_schedule():
    for temp,protect in [(None,False),(40,True)]:
        p=plan(DHWComfortSchedule(),at(8),temp=temp,protected=protect,c=conf(morning_enabled=True,evening_enabled=True))
        assert p.target_c is None and p.standby_target_c is None

@pytest.mark.parametrize('change',[{'morning_c':float('nan')},{'morning_time':'26:00'},{'night_policy':'off'},{'morning_enabled':True,'morning_c':51},{'normal_c':70}, {'evening_cap_c':60}])
def test_invalid_schedule_rejected(change): assert validate_settings(conf(**change))

def test_twenty_four_hour_clock_and_dst_elapsed():
    a=datetime(2026,10,25,1,tzinfo=TZ);b=datetime(2026,10,25,9,tzinfo=TZ)
    assert elapsed_hours(b,a)==9
    a=datetime(2026,3,29,1,tzinfo=TZ);b=datetime(2026,3,29,9,tzinfo=TZ)
    assert elapsed_hours(b,a)==7

def test_tank_learning_ignores_draw_heating_and_gaps():
    m=TankLearning();t=at(15).timestamp()
    m.observe(t,52,day='a');m.observe(t+300,48,day='a');m.observe(t+600,49,day='a',heating=True)
    assert m.losses==[] and len(m.heating)==0
    m.observe(t+3000,48,day='a');assert m.losses==[]
    assert m.rates(conf(),t+3000)['heat_source']=='ingestelde terugvalwaarde'

def test_tank_loss_learning_and_restore_bounded():
    m=TankLearning();t=at(15).timestamp()
    for day in range(3):
        for i in range(13):m.observe(t+86400*day+300*i,55-.05*i,day=str(day))
    assert len(m.losses)>=6 and m.rates(conf(),t+3*86400)['loss_source']=='geleerd'
    n=TankLearning();n.restore(m.snapshot());assert n.losses==m.losses
    n.restore({'losses':[[t,'a',float('nan')]],'heating':'bad'});assert n.losses==[] and n.heating==[]

@pytest.mark.parametrize('cooling,predicted',[(True,False),(None,False),(False,True)])
def test_evening_cap_and_morning_cap_respect_cooling(cooling,predicted):
    p=DHWPolicy(conf(rise_delay_s=0,fall_delay_s=0,cooling_clear_s=0))
    for stage,urgent in [('evening',False),('morning',True)]:
        d=p.update(100,at(16),DHWReading(44,50,5000,5000,5000,-5000,cooling,comfort_target_c=55,comfort_stage=stage,comfort_urgent=urgent,predicted_cooling=predicted))
        assert d.target_c<=50

def test_optional_sixty_waits_for_ev_but_comfort_does_not():
    p=DHWPolicy(conf(rise_delay_s=0,cooling_clear_s=0))
    r=DHWReading(46,50,6000,5000,5000,-5000,False,luxury_allowed=False,comfort_target_c=55,comfort_stage='evening')
    assert p.update(100,at(16),r).target_c==55
    r.comfort_target_c=None
    assert p.update(110,at(16),r).target_c<=55
    r.luxury_allowed=True
    assert p.update(120,at(16),r).target_c==60

@pytest.mark.asyncio
async def test_morning_safety_confirmation_still_required():
    r,h=setup(config={'morning_enabled':True,'night_policy':'minimum_until_solar','safety_confirmed':False})
    await tick(r,grid=500,hour=8)
    assert not [c for c in h.services.calls if c[1]=='set_temperature']

@pytest.mark.asyncio
async def test_morning_no_solar_still_allowed_but_never_heat_pump_power_switch():
    r,h=setup(config={'morning_enabled':True,'night_policy':'minimum_until_solar'})
    r.pv_w=0
    obj=h.states.get('water_heater.boiler');h.states.set('water_heater.boiler',obj.state,{**obj.attributes,'temperature':48})
    await tick(r,grid=500,hour=8)
    calls=[c for c in h.services.calls if c[0]!='persistent_notification']
    assert len(calls)==1 and calls[0][1]=='set_temperature'
    assert 50<=calls[0][2]['temperature']<=55

def wb_context(r,power=0,mode='full_solar',demand=True,status='Waiting for green energy',valid=True):
    r.wallbox_settings.update(enabled=True,charging_threshold_w=50,full_solar_states='full_solar',idle_states='Ready;Paused')
    r._wallbox_reading=lambda:NSWB(power_w=power,mode=mode,demand=demand,status=status,valid=valid,connected=True)
NSWB=SimpleNamespace

def test_ev_watts_help_evening_but_never_become_sixty_export():
    r,h=setup(config={'morning_enabled':True,'evening_enabled':True,'hygiene_schedule_enabled':False})
    wb_context(r,power=4000,status='Charging');r.grid_w=-100;r.pv_w=6000
    h.states.set('sensor.water',49,{'unit_of_measurement':'°C'})
    rd=r.dhw.read(-100,True,0,at(16));r.dhw._prepare_comfort(at(16),rd)
    assert rd.export_w==100 and rd.comfort_stage=='evening' and rd.comfort_target_c<=55
    d=r.dhw.policy.update(100,at(16),rd);assert d.target_c<=55

def test_ev_watts_do_not_hide_existing_grid_import_for_evening():
    r,h=setup(config={'morning_enabled':True,'evening_enabled':True,'hygiene_schedule_enabled':False})
    wb_context(r,power=4000,status='Charging');r.grid_w=2000;r.pv_w=4000
    rd=r.dhw.read(2000,True,0,at(16));r.dhw._prepare_comfort(at(16),rd)
    assert rd.export_w==0 and rd.comfort_stage!='evening'

@pytest.mark.parametrize('power,status,demand,valid,allowed',[(0,'Waiting for green energy',True,True,False),(0,'Ready',False,True,True),(3000,'Charging',True,True,True),(0,'Unknown',None,False,False)])
def test_luxury_yields_to_waiting_ev_not_ready_or_running_ev(power,status,demand,valid,allowed):
    r,h=setup(config={'hygiene_schedule_enabled':False});wb_context(r,power=power,status=status,demand=demand,valid=valid)
    rd=r.dhw.read(-5000,True,0,at(16));r.dhw._prepare_comfort(at(16),rd)
    assert rd.luxury_allowed is allowed

@pytest.mark.asyncio
async def test_manufacturer_hygiene_still_blocks_morning_and_evening():
    r,h=setup(config={'morning_enabled':True,'evening_enabled':True})
    h.states.set('binary_sensor.hygiene','on');r.pv_w=0
    await tick(r,grid=700,hour=8)
    assert not [c for c in h.services.calls if c[1]=='set_temperature']

def test_predictive_cooling_requires_reliable_model_and_can_see_idle_cool(monkeypatch):
    r,h=setup(config={'predictive_cooling_enabled':True});p=NSWB(confidence=lambda c:.7,predict=lambda *a,**kw:[24,25])
    climate=NSWB(settings={'enabled':True,'zone_entities':['climate.home'],'model_confidence_min':.55,'forecast_refresh_s':3600,'soft_band_c':.5},configured=True,state=NSWB(fault='',last_forecast_wall=__import__('time').time(),profiles={'climate.home':p}),last_solar_hourly=[2,2],_zones=lambda:[dict(entity_id='climate.home',current=23,target=23,mode='cool')],_outside_hourly=lambda:[27,28])
    r.smart_climate=climate
    assert r.dhw._predicted_cooling()[0]
    p.confidence=lambda c:.2;r.dhw._prediction_check_wall=None
    assert not r.dhw._predicted_cooling()[0]
    p.confidence=lambda c:.7;climate.state.last_forecast_wall=0;r.dhw._prediction_check_wall=None
    assert not r.dhw._predicted_cooling()[0]


def test_integer_sensor_steps_learn_slow_loss():
    m=TankLearning();t=at(15).timestamp()
    for i in range(25):m.observe(t+300*i,55-i//12,day='d')
    assert m.losses and all(0 < x[2] <= 1.5 for x in m.losses)


def test_integer_heating_averages_plateaus_not_only_steps():
    m=TankLearning();t=at(15).timestamp()
    for i in range(13):m.observe(t+300*i,40+i//2,day='d',heating=True)
    # 6 degrees in one hour, NOT 12 deg/h inferred from each single 5-min jump.
    assert len(m.heating)>=3
    assert min(x[2] for x in m.heating)<=6
    assert max(x[2] for x in m.heating)<=8
