"""Manual override and automatic priority, preserving physical limits and runtime."""
from datetime import datetime,timezone
from types import SimpleNamespace as NS
from copy import deepcopy
import pytest
from custom_components.solar_pilot.wallbox_policy import SESSION_DEFAULTS,classify_session,reclaim_permission
from custom_components.solar_pilot.wallbox import Reading
from test_house_runtime import setup,tick
from test_dhw_runtime import setup as dhw_setup,tick as dhw_tick
from test_runtime import build

@pytest.mark.parametrize('value', ['Manueel laden','Manueel laden · klaar','Manueel / solar uit'])
def test_manual_override_wins_even_configured_full_solar(value):
    c={**SESSION_DEFAULTS,'session_mode_entity':'sensor.effective'}
    assert classify_session(c,'full_solar',value).mode=='manual'

@pytest.mark.parametrize('value', [None,'unknown','unavailable','garbage','Zonne-auto','FOUT · offline'])
def test_unknown_session_never_grants_credit(value):
    c={**SESSION_DEFAULTS,'session_mode_entity':'sensor.effective'}
    assert classify_session(c,'full_solar',value).mode=='unknown'

@pytest.mark.parametrize('value',['Zonne-auto · laden','Zonne-auto · wacht op overschot'])
def test_confirmed_session_requires_both_sources(value):
    c={**SESSION_DEFAULTS,'session_mode_entity':'sensor.effective'}
    assert classify_session(c,'full_solar',value).mode=='full_solar'
    assert classify_session(c,'off',value).mode=='unknown'


def test_full_solar_setting_alone_is_not_default_permission():
    assert classify_session(SESSION_DEFAULTS,'full_solar',None).mode=='unknown'
    assert classify_session({**SESSION_DEFAULTS,'trust_solar_setting':True},'full_solar',None).mode=='full_solar'


def test_stopped_exact_match_no_solar_assumption():
    c={**SESSION_DEFAULTS,'session_mode_entity':'sensor.effective'}
    assert classify_session(c,'full_solar','Laden gestopt').mode=='stopped'
    assert classify_session(c,'full_solar','niet Manueel laden').mode=='unknown'

@pytest.mark.parametrize('cfg,before,meter,allowed', [({},True,True,True),({},False,True,False),({},True,False,False),
    ({'wallbox_power_policy':'never'},True,True,False),({'wallbox_power_policy':'legacy'},True,True,False),
    ({'wallbox_power_policy':'legacy','allow_wallbox_reclaim':True},True,True,True),
    ({'non_interruptible':True},True,True,False),({'kind':'dishwasher'},True,True,False),
    ({'kind':'script'},True,True,False),({'wallbox_power_policy':'invalid'},True,True,False)])
def test_configurable_consumer_permission(cfg,before,meter,allowed):
    assert reclaim_permission(cfg,before_wallbox=before,dedicated_meter=meter)[0] is allowed
    assert not reclaim_permission(cfg,before_wallbox=before,dedicated_meter=meter,blocked=True)[0]

@pytest.mark.asyncio
async def test_priority_consumer_automatically_can_start_with_long_minimum_runtime(monkeypatch):
    r,h,c=setup(monkeypatch,device={'min_on_s':1800,'allow_wallbox_reclaim':False},wallbox={'trust_solar_setting':False,'session_mode_entity':'sensor.session'})
    for t in range(0,31,5):
        h.states.set('sensor.session','Zonne-auto · laden');await tick(r,h,c,t)
    assert r.handover and h.states.get('switch.load').state=='on'
    for t in range(35,200,5):
        h.states.set('sensor.session','Manueel laden');await tick(r,h,c,t,grid=1000,load=1000)
    assert h.states.get('switch.load').state=='on' # failed transfer does NOT break compressor minimum
    assert len([x for x in h.services.calls if x[0]=='switch'])==1

@pytest.mark.asyncio
@pytest.mark.parametrize('policy',['never','legacy'])
async def test_policy_off_and_old_false_dont_take_ev_power(monkeypatch,policy):
    r,h,c=setup(monkeypatch,device={'wallbox_power_policy':policy,'allow_wallbox_reclaim':False})
    for t in range(0,120,5):await tick(r,h,c,t)
    assert not h.services.calls

@pytest.mark.asyncio
async def test_manual_car_no_reclaim_but_actual_surplus_can_start(monkeypatch):
    r,h,c=setup(monkeypatch,wallbox={'trust_solar_setting':False,'session_mode_entity':'sensor.session'})
    for t in range(0,120,5):
        h.states.set('sensor.session','Manueel laden');await tick(r,h,c,t)
    assert not h.services.calls and r.wallbox_guard.reclaimable_w==0
    for t in range(120,155,5):
        h.states.set('sensor.session','Manueel laden');await tick(r,h,c,t,grid=-2000)
    assert h.states.get('switch.load').state=='on' and r.handover is None

@pytest.mark.asyncio
async def test_physical_import_limit_not_inflated_by_ev_watts(monkeypatch):
    r,h,c=setup(monkeypatch,settings={'max_import_w':500})
    for t in range(0,150,5):await tick(r,h,c,t,ev=6000,grid=0)
    assert not h.services.calls

@pytest.mark.asyncio
async def test_missing_effective_session_preserves_only_real_surplus(monkeypatch):
    r,h,c=setup(monkeypatch,wallbox={'trust_solar_setting':False})
    for t in range(0,120,5):await tick(r,h,c,t)
    assert not h.services.calls and r._wallbox_reading().mode=='unknown'

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['manual','unknown'])
async def test_manual_charging_drops_owned_60_only_and_keeps_normal_comfort(mode):
    r,h=dhw_setup();r.wallbox_settings.update(enabled=True,manual_suspend_extra_dhw=True)
    r._wallbox_reading=lambda:Reading(4000,datetime.now(timezone.utc).timestamp(),True,'Charging',mode,True,'',0,True)
    # The manager already owns a 60 degree solar target; manual EV cancels luxury, not comfort.
    r.dhw.owned_target=60
    h.states.get('water_heater.boiler').attributes['temperature']=60
    await dhw_tick(r,grid=-5000)
    assert r.dhw.policy.result.target_c==50
    assert all(x[1]=='set_temperature' and x[2]['temperature']==50 for x in h.services.calls if x[0]!='persistent_notification')

@pytest.mark.asyncio
async def test_manual_charging_does_not_touch_sterilization():
    r,h=dhw_setup();r.wallbox_settings.update(enabled=True)
    r._wallbox_reading=lambda:Reading(4000,1,True,'Charging','manual',True,'',0,True)
    r.dhw.owned_target=60;h.states.set('binary_sensor.hygiene','on')
    await dhw_tick(r)
    assert not h.services.calls

@pytest.mark.asyncio
async def test_disconnected_ev_does_not_permanently_block_solar_buffer():
    r,h=dhw_setup();r.wallbox_settings.update(enabled=True)
    r._wallbox_reading=lambda:Reading(0,1,False,'Ready','unknown',True,'',0,False)
    await dhw_tick(r,grid=-5000)
    assert r.dhw.policy.result.target_c==60

@pytest.mark.asyncio
async def test_manual_dhw_protection_configurable_without_any_ev_write():
    r,h=dhw_setup();r.wallbox_settings.update(enabled=True,manual_suspend_extra_dhw=False)
    r._wallbox_reading=lambda:Reading(4000,1,True,'Charging','manual',True,'',0,True)
    await dhw_tick(r,grid=-5000)
    assert r.dhw.policy.result.target_c==60
    assert all(x[0] in ('water_heater','persistent_notification') for x in h.services.calls)

@pytest.mark.parametrize('raw',['Full Solar','Full green','CUSTOM_SOLAR_MODE'])
def test_exact_custom_solar_mode_survives_downstream_matching(raw):
    from custom_components.solar_pilot.wallbox import state_set
    c={**SESSION_DEFAULTS,'session_mode_entity':'sensor.actual','full_solar_states':raw}
    session=classify_session(c,raw,'Zonne-auto · laden')
    assert session.confirmed and session.mode.casefold() in state_set(c['full_solar_states'])

@pytest.mark.parametrize('attrs',[{'estimated':True},{'is_estimated':True},{'restored':True},{'friendly_name':'Geschat vermogen'}])
def test_default_reclaim_rejects_declared_estimated_meter(attrs):
    r,h=build(power=True);h.states.get('sensor.load').attributes.update(attrs)
    assert not r.devices()[0].allow_wallbox_reclaim

@pytest.mark.asyncio
async def test_manual_override_between_plan_and_dispatch_never_sends(monkeypatch):
    from custom_components.solar_pilot.engine import Action
    r,h,c=setup(monkeypatch,wallbox={'session_mode_entity':'sensor.session','trust_solar_setting':False})
    await tick(r,h,c,0)
    h.states.set('sensor.session','Manueel laden')
    await r._send(Action('a',1000,'test',reclaimed_w=1000),c.monotonic())
    assert not h.services.calls and not r.pending
    assert 'Laadsessie gewijzigd' in r.result.reasons['a']


@pytest.mark.parametrize("unconfirmed", ["false", "true", 1, None])
def test_trusting_solar_setting_requires_literal_boolean_permission(unconfirmed):
    config = {**SESSION_DEFAULTS, "trust_solar_setting": unconfirmed}
    assert classify_session(config, "full_solar", None).mode == "unknown"
