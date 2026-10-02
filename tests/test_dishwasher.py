"""Explicit start admission and stage learning; fictitious appliance only."""
from datetime import datetime, timezone
from types import SimpleNamespace
import time
import pytest
from test_runtime import build
from custom_components.solar_pilot import dishwasher as dw
from homeassistant.helpers import entity_registry as er


def setup(**changes):
    cfg = {"start_button": "button.dw_start", "dishwasher_state_entity": "sensor.dw_phase",
           "dishwasher_connection_entity": "sensor.dw_connection", "dishwasher_remote_entity": "sensor.dw_remote",
           "dishwasher_door_entity": "binary_sensor.dw_door", "cycle_program_entity": "select.dw_program",
           "dishwasher_mapping_confirmed": True, "nominal_w": 2000, **changes}
    r,h=build(kind="dishwasher",device=cfg)
    for eid,state in [("button.dw_start","unknown"),("sensor.dw_phase","Idle"),("sensor.dw_connection","Connected"),
                      ("sensor.dw_remote","Enabled"),("binary_sensor.dw_door","off"),("select.dw_program","Eco")]:
        h.states.set(eid,state)
    return r,h,r.configs['a']


def test_valid_reading_not_permission_without_preparation():
    r,h,c=setup(); d=dw.read(h,c)
    assert d.active is False and d.ready
    assert not r.dishwasher.permitted(c,d,time.time())[0]
    assert c['non_interruptible'] and not c['allow_wallbox_reclaim']
    assert 'control_entity' not in c and 'stop_script' not in c

@pytest.mark.parametrize('eid,state,reason',[
 ('sensor.dw_connection','Disconnected','offline'),('sensor.dw_connection','unknown','offline'),
 ('sensor.dw_phase','Unavailable','onbekend'),('sensor.dw_phase','NewUnexpectedState','niet herkend'),
 ('sensor.dw_remote','Not Safety Relevant Enabled','afstand'),('sensor.dw_remote','Disabled','afstand'),
 ('binary_sensor.dw_door','on','Deur'),('select.dw_program','unknown','Programma'),('select.dw_program','No Program','Programma'),
 ('button.dw_start','unavailable','START')])
def test_readiness_fail_closed(eid,state,reason):
    r,h,c=setup(); h.states.set(eid,state); d=dw.read(h,c)
    assert not d.ready and reason.lower() in d.reason.lower()

def test_connectivity_heartbeat_rejects_stale_device():
    r,h,c=setup(); old=h.states.get('sensor.dw_connection');h.states.set('sensor.dw_connection',old.state,age=301)
    assert not dw.read(h,c).ready


def test_stale_cloud_report_is_visible_without_losing_the_existing_request():
    r, h, c = setup()
    r.dishwasher.arm(c, dw.read(h, c), time.time())
    h.states.set('sensor.dw_connection', 'Connected', reported_age=1080)
    reading = dw.read(h, c)
    r.dishwasher.readings['a'] = reading
    overview = r.dishwasher.overview(c)
    assert not reading.ready and reading.active is None
    assert overview['ticket_armed'] and not overview['prepared']
    assert not overview['gates']['connection']
    assert overview['connection_report']['state'] == 'Connected'
    assert overview['connection_report']['age_s'] == pytest.approx(1080, abs=1)
    assert overview['connection_report']['maximum_age_s'] == 300
    assert not overview['connection_report']['current']
    assert not h.services.calls


def test_successful_cloud_refresh_keeps_same_ticket_without_creating_start_permission():
    r, h, c = setup()
    r.dishwasher.arm(c, dw.read(h, c), time.time())
    ticket = dict(r.dishwasher.tickets['a'])
    h.states.set('sensor.dw_connection', 'Connected', reported_age=1080)
    assert not dw.read(h, c).ready
    h.states.set('sensor.dw_connection', 'Connected')
    assert dw.read(h, c).ready
    assert r.dishwasher.tickets['a'] == ticket
    assert not h.services.calls


@pytest.mark.parametrize('eid', ['sensor.dw_phase','sensor.dw_remote','binary_sensor.dw_door','select.dw_program'])
def test_unchanged_static_guard_may_be_old_when_connectivity_is_fresh(eid):
    r,h,c=setup(); old=h.states.get(eid);h.states.set(eid,old.state,age=3600)
    assert dw.read(h,c).ready

@pytest.mark.parametrize('state', ['Running','Washing','Prewash','Main wash','Rinsing','Drying','Ado Drying','Paused'])
def test_running_phase_not_zero_or_available_for_new_start(state):
    r,h,c=setup();h.states.set('sensor.dw_phase',state);h.states.set('binary_sensor.dw_door','on')
    d=dw.read(h,c);assert d.active is True and not d.ready and not d.finished

@pytest.mark.parametrize('state',['Finished','Completed','End','Cycle finished'])
def test_finished_is_explicit_and_does_not_rearm(state):
    r,h,c=setup();h.states.set('sensor.dw_phase',state);d=dw.read(h,c)
    assert d.finished and d.active is False and not d.ready

@pytest.mark.parametrize('bad',[0,1,-1,'unknown','5',float('nan')])
def test_native_delay_blocks_except_explicit_zero(bad):
    r,h,c=setup(dishwasher_delay_entity='number.dw_delay');h.states.set('number.dw_delay',bad)
    assert dw.read(h,c).ready == (bad==0)

@pytest.mark.parametrize('alarm',['Alarm','unavailable','unknown','Leak detected'])
def test_optional_alarm_guard(alarm):
    r,h,c=setup(dishwasher_alert_entity='sensor.dw_alarm');h.states.set('sensor.dw_alarm',alarm)
    assert not dw.read(h,c).ready


def test_old_restored_start_button_is_never_selected_as_ready():
    r,h,c=setup();h.states.set('button.dw_start','unknown',{'restored':True})
    assert not dw.read(h,c).ready
    assert dw.config_errors(h,c)['start_button']=='dishwasher_restored'


def test_mapping_must_be_confirmed_but_can_be_configured_unconfirmed():
    r,h,c=setup(dishwasher_mapping_confirmed=False)
    assert not dw.read(h,c).ready
    assert not dw.config_errors(h,c)


def test_same_appliance_source_validation(monkeypatch):
    r,h,c=setup()
    monkeypatch.setattr(er,'async_get',lambda h:SimpleNamespace(async_get=lambda e:SimpleNamespace(device_id='same')))
    assert not dw.config_errors(h,c)
    monkeypatch.setattr(er,'async_get',lambda h:SimpleNamespace(async_get=lambda e:SimpleNamespace(device_id='different' if e.startswith('button') else 'same')))
    assert dw.config_errors(h,c)['base']=='dishwasher_same_device'

@pytest.mark.parametrize('key',['dishwasher_ready_states','dishwasher_running_states','dishwasher_connected_states','dishwasher_remote_states','dishwasher_closed_states'])
def test_unknown_cannot_be_accepted_guard_value(key):
    r,h,c=setup(dishwasher_mapping_confirmed=False,**{key:'unknown'})
    assert dw.config_errors(h,c).get(key)=='dishwasher_unknown_state'


def test_overlap_rejected():
    r,h,c=setup(dishwasher_mapping_confirmed=False,dishwasher_ready_states='Idle;Washing')
    assert 'dishwasher_ready_states' in dw.config_errors(h,c)


def test_one_shot_program_and_expiry():
    r,h,c=setup();wall=time.time();d=dw.read(h,c);r.dishwasher.arm(c,d,wall)
    assert r.dishwasher.permitted(c,d,wall)[0]
    assert not r.dishwasher.permitted(c,d,wall+25*3600)[0]
    h.states.set('select.dw_program','Intensive');assert not r.dishwasher.permitted(c,dw.read(h,c),wall)[0]
    r.dishwasher.sent(c,wall);assert not r.dishwasher.permitted(c,d,wall)[0]
    with pytest.raises(ValueError):r.dishwasher.arm(c,d,wall)
    r.dishwasher.confirmed('a');assert not r.dishwasher.permitted(c,d,wall)[0]


def test_reopen_or_program_change_revokes_preparation():
    for eid,state in [('binary_sensor.dw_door','on'),('select.dw_program','Intensive')]:
        r,h,c=setup();r.dishwasher.arm(c,dw.read(h,c),time.time());h.states.set(eid,state)
        r.dishwasher.observe(c,dw.read(h,c),None,time.time())
        assert not r.dishwasher.tickets['a']['armed']


def test_profile_requires_complete_metered_cycle_not_a_screenshot():
    model=dw.DishwasherControl();cfg={'id':'a'}
    model.observe(cfg,dw.Reading(active=False,program='Eco',phase='Idle'),0,1000)
    model.observe(cfg,dw.Reading(active=True,program='Eco',phase='Washing'),1500,1005)
    for t in range(1010,1095,5):
        model.observe(cfg,dw.Reading(active=True,program='Eco',phase='Washing'),1500,t)
    model.observe(cfg,dw.Reading(active=True,program='Eco',phase='Drying'),0,1095)
    model.observe(cfg,dw.Reading(active=True,program='Eco',phase='Drying'),0,1100)
    sample=model.observe(cfg,dw.Reading(active=False,finished=True,program='Eco',phase='End'),0,1105)
    assert sample and sample['coverage']==1
    assert sample['stages']['Drying']['kwh']==0
    assert 'Rinsing' not in sample['stages']  # unmeasured is not zero
    assert sample['stages']['Washing']['peak_w']==1500

@pytest.mark.parametrize('bad',['gap','missing_meter','unknown_state','canceled','changed_program'])
def test_incomplete_cycles_do_not_train(bad):
    model=dw.DishwasherControl();cfg={'id':'a'}
    model.observe(cfg,dw.Reading(active=False,program='Eco'),0,1000)
    model.observe(cfg,dw.Reading(active=True,program='Eco',phase='Washing'),1000,1005)
    for t in range(1010,1100,5):
        if bad=='gap' and 1020<t<1060:continue
        d=dw.Reading(active=None if bad=='unknown_state' and t==1030 else True,
            program='Intensive' if bad=='changed_program' and t==1030 else 'Eco',phase='Washing')
        model.observe(cfg,d,None if bad=='missing_meter' else 1000,t)
    assert not model.observe(cfg,dw.Reading(active=False,finished=bad!='canceled',program='Eco'),0,1100)
    assert not model.profiles
