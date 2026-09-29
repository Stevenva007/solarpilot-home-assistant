"""Physical APP edge, frozen local deadline, observed end; no real appliance calls."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import time
import pytest
from test_dishwasher import setup
from custom_components.solar_pilot.dishwasher import read, config_errors
from custom_components.solar_pilot.dishwasher_app import request_window
from custom_components.solar_pilot import runtime as runtime_module

ZONE=ZoneInfo('Europe/Brussels')
def stamp(text):return datetime.fromisoformat(text).replace(tzinfo=ZONE).timestamp()

@pytest.mark.parametrize('hour,day', [('00:15','2026-09-29'),('09:00','2026-09-29'),('12:59','2026-09-29'),('13:00','2026-09-30'),('17:00','2026-09-30'),('23:59','2026-09-30')])
def test_next_day_default(hour,day):
    w=request_window(stamp('2026-09-29T'+hour),{})
    assert w['planned_day']==day
    assert datetime.fromtimestamp(w['deadline'],ZONE).strftime('%H:%M')=='13:00'
    assert w['grid_allowed']
    assert w['expires']>w['deadline']

@pytest.mark.parametrize('text,day',[('2026-10-24T20:00','2026-10-25'),('2027-03-27T20:00','2027-03-28'),('2026-12-31T20:00','2027-01-01')])
def test_local_deadline_across_dst_and_year(text,day):
    w=request_window(stamp(text),{})
    assert datetime.fromtimestamp(w['deadline'],ZONE).isoformat().startswith(day+'T13:00:00')
    assert datetime.fromtimestamp(w['not_before'],ZONE).hour==0

@pytest.mark.parametrize('hour',['13:00','15:00','23:00'])
def test_same_day_explicit_alternative(hour):
    now=stamp('2026-09-29T'+hour)
    w=request_window(now,{'dishwasher_after_deadline':'same_day'})
    assert w['not_before']==w['deadline']==now


def configured(monkeypatch,when='2026-09-29T09:00',**values):
    wall=[stamp(when)]
    monkeypatch.setattr(time,'time',lambda:wall[0])
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.fromtimestamp(wall[0],tz or timezone.utc)
    monkeypatch.setattr(runtime_module,'datetime',Clock)
    r,h,c=setup(dishwasher_arming_mode='app',dishwasher_remote_states='Enabled',
                dishwasher_phase_entity='sensor.dw_stage',**values)
    h.config=SimpleNamespace(time_zone='Europe/Brussels')
    oldset=h.states.set
    def setval(eid,value,attrs=None,age=0,reported_age=None):
        oldset(eid,value,attrs,age,reported_age)
        x=h.states.get(eid);x.last_reported=datetime.fromtimestamp(wall[0]-(reported_age if reported_age is not None else age),timezone.utc);x.last_updated=x.last_reported
    h.states.set=setval
    for eid,x in list(h.states.data.items()):setval(eid,x.state,x.attributes)
    setval('sensor.dw_phase','Ready To Start')
    setval('sensor.dw_remote','Not Safety Relevant Enabled')
    setval('sensor.dw_stage','Unavailable')
    r.mode='solar';r.device_modes['a']='auto'
    r.dishwasher_app.seed(c)
    return r,h,c,wall


def event(r,h,c,wall,key,value):
    h.states.set(c[key],value)
    r.dishwasher_app.event(c,c[key],value,wall[0])


def ready(r,h,c,wall):event(r,h,c,wall,'dishwasher_remote_entity','Enabled')


def move(h,wall,newtime):
    wall[0]=stamp(newtime)
    for eid,x in list(h.states.data.items()):h.states.set(eid,x.state,x.attributes)

@pytest.mark.asyncio
async def test_app_start_with_ready_state_while_phase_unavailable(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w)
    await r.tick()
    assert len([x for x in h.services.calls if x[0]=='button'])==1
    assert r.store.data['dishwasher']['tickets']['a']['attempted']
    assert r.dishwasher_app.data['a']['request']['deadline']==stamp('2026-09-29T13:00')

@pytest.mark.asyncio
async def test_ready_without_app_never_starts(monkeypatch):
    r,h,c,w=configured(monkeypatch);await r.tick()
    assert not h.services.calls and not r.dishwasher_app.data['a'].get('request')

@pytest.mark.asyncio
async def test_app_after_13_cannot_start_today_even_with_plenty_of_sun(monkeypatch):
    r,h,c,w=configured(monkeypatch,'2026-09-29T14:00');ready(r,h,c,w);await r.tick()
    assert not h.services.calls
    assert 'volgende dag' in r.result.reasons['a']
    assert r.dishwasher.overview(c,w[0])['ticket_armed']

@pytest.mark.asyncio
async def test_tomorrow_no_sun_waits_then_grid_deadline(monkeypatch):
    r,h,c,w=configured(monkeypatch,'2026-09-29T22:00', start_delay_s=300)
    ready(r,h,c,w);h.states.set('sensor.grid',600,{'unit_of_measurement':'W'});await r.tick()
    move(h,w,'2026-09-30T08:00');await r.tick();assert not h.services.calls
    move(h,w,'2026-09-30T12:59');await r.tick();assert not h.services.calls
    move(h,w,'2026-09-30T13:00');await r.tick()
    assert len([x for x in h.services.calls if x[0]=='button'])==1
    assert 'deadline' in r.pending['reason']
    # Uses no native AEG timer and never controls a plug.
    assert not [x for x in h.services.calls if x[0] in ('number','switch')]

@pytest.mark.asyncio
async def test_deadline_not_shifted_when_repeated_cloud_reports_or_next_tick(monkeypatch):
    r,h,c,w=configured(monkeypatch,'2026-09-29T23:00');ready(r,h,c,w)
    q=deepcopy(r.dishwasher_app.data['a']['request'])
    move(h,w,'2026-09-30T10:00');ready(r,h,c,w)
    assert r.dishwasher_app.data['a']['request']==q

@pytest.mark.asyncio
@pytest.mark.parametrize('case',['open','offline','remote','unmapped','fault','paused','excluded','grid_stale','grid_limit','battery'])
async def test_deadline_respects_interlocks_and_global_guards(monkeypatch,case):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w)
    h.states.set('sensor.grid',700,{'unit_of_measurement':'W'})
    await r.tick();move(h,w,'2026-09-29T13:00')
    if case=='open':h.states.set('binary_sensor.dw_door','on')
    elif case=='offline':h.states.set('sensor.dw_connection','Disconnected')
    elif case=='remote':h.states.set('sensor.dw_remote','Not Safety Relevant Enabled')
    elif case=='unmapped':c['dishwasher_mapping_confirmed']=False
    elif case=='fault':r.faults['a']='fout'
    elif case=='paused':r.mode='paused'
    elif case=='excluded':r.device_modes['a']='disabled'
    elif case=='grid_stale':h.states.set('sensor.grid',700,{'unit_of_measurement':'W'},age=900)
    elif case=='grid_limit':h.states.set('sensor.grid',3000,{'unit_of_measurement':'W'})
    else:r.settings.update(battery_soc_entity='sensor.soc',battery_min_soc=50);h.states.set('sensor.soc',10)
    await r.tick()
    assert not [x for x in h.services.calls if x[0]=='button']

@pytest.mark.asyncio
async def test_explicit_grid_permission_off_still_waits(monkeypatch):
    r,h,c,w=configured(monkeypatch,dishwasher_deadline_grid_allowed=False);ready(r,h,c,w)
    h.states.set('sensor.grid',700,{'unit_of_measurement':'W'});move(h,w,'2026-09-29T13:01')
    await r.tick();assert not [x for x in h.services.calls if x[0]=='button']

@pytest.mark.asyncio
async def test_five_minute_solar_stability_and_reset(monkeypatch):
    r,h,c,w=configured(monkeypatch,start_delay_s=300);ready(r,h,c,w)
    await r.tick();assert r.states['a'].start_since is not None
    r.states['a'].start_since-=299;await r.tick();assert not h.services.calls
    h.states.set('sensor.grid',100,{'unit_of_measurement':'W'});await r.tick();assert r.states['a'].start_since is None
    h.states.set('sensor.grid',-2500,{'unit_of_measurement':'W'});r.filtered=-2500
    await r.tick();r.states['a'].start_since-=301;await r.tick()
    assert len([x for x in h.services.calls if x[0]=='button'])==1

@pytest.mark.asyncio
async def test_manual_running_consumes_request_no_start_at_13(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w);event(r,h,c,w,'dishwasher_state_entity','Running')
    await r.tick();move(h,w,'2026-09-29T13:00');await r.tick()
    assert not [x for x in h.services.calls if x[0]=='button']
    assert not r.dishwasher_app.data['a'].get('request')

@pytest.mark.asyncio
async def test_remote_drying_changes_cannot_rearm(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w);event(r,h,c,w,'dishwasher_state_entity','Running')
    event(r,h,c,w,'dishwasher_phase_entity','Ado Drying')
    event(r,h,c,w,'dishwasher_remote_entity','Not Safety Relevant Enabled')
    event(r,h,c,w,'dishwasher_door_entity','on');ready(r,h,c,w);await r.tick()
    assert not h.services.calls
    assert r.dishwasher_app.overview(c,w[0])['airdry']
    assert not r.dishwasher_app.data['a'].get('completion')

@pytest.mark.asyncio
async def test_short_end_saved_before_off_and_disconnect_even_when_lock_held(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w);await r.tick()
    w[0]+=3;event(r,h,c,w,'dishwasher_state_entity','Running');await r.tick()
    assert not r.pending and r.states['a'].owned
    w[0]+=200;event(r,h,c,w,'dishwasher_phase_entity','Ado Drying')
    event(r,h,c,w,'dishwasher_door_entity','on');await r.tick();assert r.states['a'].on
    async with r._lock:
        w[0]+=7200;ended=w[0];event(r,h,c,w,'dishwasher_state_entity','End Of Cycle')
        w[0]+=4;event(r,h,c,w,'dishwasher_state_entity','Off')
        h.states.set('sensor.dw_connection','Disconnected')
        assert r.store.data['dishwasher_app']['a']['completion']['ended_at']==ended
    await r.tick()
    assert not r.states['a'].on and not r.states['a'].owned
    assert r.overview()[0]['dishwasher']['cycle_status']=='completed'
    assert r.overview()[0]['dishwasher']['completion']['ended_at']==ended
    assert len([x for x in h.services.calls if x[0]=='button'])==1
    data=r._snapshot();r.dishwasher_app.restore(data['dishwasher_app'])
    assert r.dishwasher_app.overview(c,w[0])['completion']['ended_at']==ended

@pytest.mark.asyncio
@pytest.mark.parametrize('raw',['Off','unknown','Unavailable'])
async def test_no_success_without_explicit_end(monkeypatch,raw):
    r,h,c,w=configured(monkeypatch);event(r,h,c,w,'dishwasher_state_entity','Running')
    event(r,h,c,w,'dishwasher_state_entity',raw)
    assert not r.dishwasher_app.overview(c,w[0])['completion']

@pytest.mark.asyncio
async def test_disconnect_and_reconnect_does_not_create_app_request(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w);event(r,h,c,w,'dishwasher_state_entity','Running')
    event(r,h,c,w,'dishwasher_remote_entity','unavailable')
    ready(r,h,c,w);assert not r.dishwasher_app.data['a'].get('request')

@pytest.mark.asyncio
async def test_end_duplicate_is_idempotent(monkeypatch):
    r,h,c,w=configured(monkeypatch);event(r,h,c,w,'dishwasher_state_entity','Running')
    w[0]+=100;event(r,h,c,w,'dishwasher_state_entity','End Of Cycle');end=w[0]
    w[0]+=3;event(r,h,c,w,'dishwasher_state_entity','End Of Cycle')
    assert r.dishwasher_app.data['a']['completion']['ended_at']==end

@pytest.mark.asyncio
@pytest.mark.parametrize('which',['door','program','remote','cancel'])
async def test_waiting_permission_revocation(monkeypatch,which):
    r,h,c,w=configured(monkeypatch,'2026-09-29T19:00');ready(r,h,c,w);await r.tick()
    if which=='door':event(r,h,c,w,'dishwasher_door_entity','on')
    elif which=='program':event(r,h,c,w,'cycle_program_entity','Intensive')
    elif which=='remote':event(r,h,c,w,'dishwasher_remote_entity','Not Safety Relevant Enabled')
    else:await r.cancel_dishwasher('a')
    assert not r.dishwasher_app.data['a'].get('request')
    assert not r.dishwasher.tickets['a']['armed']

@pytest.mark.asyncio
async def test_initially_enabled_is_not_a_new_press(monkeypatch):
    r,h,c,w=configured(monkeypatch);r.dishwasher_app.data.clear();r.dishwasher_app._seeded.clear()
    h.states.set('sensor.dw_remote','Enabled');r.dishwasher_app.seed(c);await r.tick()
    assert not h.services.calls and not r.dishwasher_app.data['a'].get('request')

@pytest.mark.asyncio
async def test_deferred_sources_can_be_ready_after_app_edge(monkeypatch):
    r,h,c,w=configured(monkeypatch);h.states.set('binary_sensor.dw_door','on')
    ready(r,h,c,w);await r.tick();assert not h.services.calls
    event(r,h,c,w,'dishwasher_door_entity','off');await r.tick()
    assert len([x for x in h.services.calls if x[0]=='button'])==1

@pytest.mark.parametrize('vals,safe',[({'DISH_ALARM_I10':'OFF','DISH_ALARM_SALT_MISSING':'WARNING-NOT_NEEDED'},True),
    ({'DISH_ALARM_I10':'ON'},False),({'DISH_ALARM_I10':'unknown'},False),({},False),
    ({'DISH_ALARM_NEW':'ON','DISH_ALARM_I10':'OFF'},False)])
def test_aeg_count_is_not_a_fault_policy(monkeypatch,vals,safe):
    r,h,c,w=configured(monkeypatch,dishwasher_alert_entity='sensor.dw_alert',dishwasher_alert_mode='aeg_attributes')
    h.states.set('sensor.dw_remote','Enabled');h.states.set('sensor.dw_alert','2',vals)
    assert read(h,c).ready==safe

@pytest.mark.parametrize('bad',['Not Safety Relevant Enabled','enabled','Remote Control Enabled','Enabled;Not Safety Relevant Enabled'])
def test_app_requires_exact_enabled_mapping(monkeypatch,bad):
    r,h,c,w=configured(monkeypatch);c['dishwasher_remote_states']=bad;c['dishwasher_mapping_confirmed']=False
    assert config_errors(h,c)['dishwasher_remote_states']=='dishwasher_exact_remote'

@pytest.mark.asyncio
async def test_complete_data_in_analysis_snapshot(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w)
    assert 'dishwasher_app' in r._snapshot()
    assert r._snapshot()['dishwasher_app']['a']['request']['planned_day']=='2026-09-29'

@pytest.mark.asyncio
async def test_restart_keeps_waiting_day_and_never_rearms_old_enabled(monkeypatch):
    r,h,c,w=configured(monkeypatch,'2026-09-29T20:00');ready(r,h,c,w);await r.tick()
    saved=deepcopy(r._snapshot());q=deepcopy(saved['dishwasher_app']['a']['request'])
    r2,h2,c2,w2=configured(monkeypatch,'2026-09-30T07:00')
    h2.states.set('sensor.dw_remote','Enabled');h2.states.set('sensor.grid',800,{'unit_of_measurement':'W'})
    r2.store.data=saved;await r2.start()
    assert r2.dishwasher_app.data['a']['request']['deadline']==q['deadline']
    assert not [x for x in h2.services.calls if x[0]=='button']
    await r2.close()

@pytest.mark.asyncio
async def test_restart_without_previous_ticket_does_not_start_existing_ready_enabled(monkeypatch):
    r,h,c,w=configured(monkeypatch);h.states.set('sensor.dw_remote','Enabled')
    r.store.data={'mode':'solar','device_modes':{'a':'auto'}};await r.start()
    assert not [x for x in h.services.calls if x[0]=='button']
    await r.close()

@pytest.mark.asyncio
async def test_offline_start_first_valid_remote_is_only_baseline(monkeypatch):
    r,h,c,w=configured(monkeypatch)
    r.dishwasher_app.data={'a':{'remote':'Not Safety Relevant Enabled'}}
    r.dishwasher_app._seeded.clear();h.states.set('sensor.dw_remote','unavailable')
    r.dishwasher_app.seed(c);ready(r,h,c,w)
    assert not r.dishwasher_app.data['a'].get('request')

@pytest.mark.asyncio
async def test_finish_survives_runtime_restart_with_disconnected_device(monkeypatch):
    r,h,c,w=configured(monkeypatch);event(r,h,c,w,'dishwasher_state_entity','Running')
    w[0]+=100;event(r,h,c,w,'dishwasher_state_entity','End Of Cycle');w[0]+=4;event(r,h,c,w,'dishwasher_state_entity','Off')
    h.states.set('sensor.dw_connection','Disconnected');await r.tick();saved=deepcopy(r._snapshot())
    r2,h2,c2,w2=configured(monkeypatch);h2.states.set('sensor.dw_phase','Off');h2.states.set('sensor.dw_connection','Disconnected')
    r2.store.data=saved;await r2.start()
    assert r2.overview()[0]['dishwasher']['cycle_status']=='completed'
    assert r2.overview()[0]['dishwasher']['completion']['confirmed']
    assert not [x for x in h2.services.calls if x[0]=='button'];await r2.close()

@pytest.mark.asyncio
async def test_changed_appliance_binding_cannot_inherit_request(monkeypatch):
    r,h,c,w=configured(monkeypatch,'2026-09-29T20:00');ready(r,h,c,w);await r.tick()
    c['start_button']='button.other_start';h.states.set('button.other_start','unknown');await r.tick()
    assert not r.dishwasher_app.data['a'].get('request')
    assert not r.dishwasher.tickets['a']['armed']

@pytest.mark.asyncio
async def test_listener_installed_for_target_entities_and_removed(monkeypatch):
    import custom_components.solar_pilot.dishwasher_app as app
    r,h,c,w=configured(monkeypatch);callbacks=[];removed=[]
    def track(hass,ids,cb):callbacks.append((ids,cb));return lambda:removed.append(True)
    monkeypatch.setattr(app,'async_track_state_change_event',track)
    r.dishwasher_app.start();assert len(callbacks)==1
    assert c['dishwasher_state_entity'] in callbacks[0][0]
    assert 'sensor.grid' not in callbacks[0][0]
    e=SimpleNamespace(time_fired=datetime.fromtimestamp(w[0],timezone.utc),data={
        'entity_id':c['dishwasher_state_entity'],'new_state':SimpleNamespace(state='End Of Cycle',attributes={})})
    callbacks[0][1](e)
    assert r.dishwasher_app.data['a']['completion']['ended_at']==w[0]
    r.dishwasher_app.close();assert removed==[True]

@pytest.mark.asyncio
async def test_retained_end_uses_exact_event_time_in_history(monkeypatch):
    r,h,c,w=configured(monkeypatch);await r.tick()
    event(r,h,c,w,'dishwasher_state_entity','Running');await r.tick()
    seen=[];r.consumer_history.observe=lambda i,active,dt:seen.append((i,active,dt.timestamp()))
    w[0]+=100;event(r,h,c,w,'dishwasher_state_entity','End Of Cycle');end=w[0]
    w[0]+=4;event(r,h,c,w,'dishwasher_state_entity','Off');await r.tick()
    assert ('a',False,end) in seen

@pytest.mark.asyncio
async def test_new_belading_clears_current_finished_badge_but_keeps_last_end(monkeypatch):
    r,h,c,w=configured(monkeypatch);event(r,h,c,w,'dishwasher_state_entity','Running')
    w[0]+=100;event(r,h,c,w,'dishwasher_state_entity','End Of Cycle')
    event(r,h,c,w,'dishwasher_remote_entity','Not Safety Relevant Enabled')
    event(r,h,c,w,'dishwasher_state_entity','Ready To Start');ready(r,h,c,w)
    info=r.dishwasher_app.overview(c,w[0]);assert info['app_request'] and info['cycle_status']=='waiting'
    assert info['completion']['confirmed']

@pytest.mark.asyncio
async def test_blocked_deadline_alert_is_once_and_no_force(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w)
    h.states.set('sensor.grid',800,{'unit_of_measurement':'W'});await r.tick()
    move(h,w,'2026-09-29T13:01');h.states.set('sensor.dw_connection','Disconnected')
    await r.tick();await r.tick()
    assert not [x for x in h.services.calls if x[0]=='button']
    assert len([x for x in h.services.calls if x[0]=='persistent_notification'])==1

@pytest.mark.asyncio
async def test_expired_request_never_rolls_to_another_day(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w)
    move(h,w,'2026-09-29T15:01');await r.tick()
    assert not r.dishwasher_app.data['a'].get('request')
    move(h,w,'2026-09-30T13:00');ready(r,h,c,w);await r.tick()
    assert not [x for x in h.services.calls if x[0]=='button']

@pytest.mark.asyncio
async def test_shelly_phase_profile_uses_cyclephase_not_appliance_running(monkeypatch):
    r,h,c,w=configured(monkeypatch);h.states.set('sensor.dw_phase','Running');h.states.set('sensor.dw_stage','Prewash')
    reading=read(h,c)
    assert reading.active and reading.phase=='Prewash' and reading.raw=='Running'

@pytest.mark.asyncio
async def test_unsure_start_survives_restart_without_second_command(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w);await r.tick();saved=deepcopy(r._snapshot())
    r2,h2,c2,w2=configured(monkeypatch);h2.states.set('sensor.dw_remote','Enabled');r2.store.data=saved
    await r2.start();assert r2.faults['a']
    assert not [x for x in h2.services.calls if x[0]=='button'];await r2.close()

@pytest.mark.asyncio
async def test_ack_is_running_not_paused(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w);await r.tick()
    w[0]+=3;event(r,h,c,w,'dishwasher_state_entity','Paused');await r.tick();assert r.pending
    w[0]+=1;event(r,h,c,w,'dishwasher_state_entity','Running');await r.tick();assert not r.pending

@pytest.mark.asyncio
async def test_running_at_restart_has_unknown_actual_start_time(monkeypatch):
    r,h,c,w=configured(monkeypatch);r.dishwasher_app.data.clear();r.dishwasher_app._seeded.clear()
    h.states.set('sensor.dw_phase','Running');r.dishwasher_app.seed(c);await r.tick()
    assert r.dishwasher_app.data['a']['cycle']['started_at'] is None

@pytest.mark.asyncio
async def test_native_timer_is_never_written(monkeypatch):
    r,h,c,w=configured(monkeypatch,dishwasher_delay_entity='number.dw_delay');h.states.set('number.dw_delay',0)
    ready(r,h,c,w);await r.tick()
    assert all(x[:2]==('button','press') for x in h.services.calls)

@pytest.mark.asyncio
async def test_deadline_does_not_bypass_phase_guards(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w)
    h.states.set('sensor.grid',500,{'unit_of_measurement':'W'});await r.tick()
    r.phase_settings.update(enabled=True,control_starts=True,limit_w=7000,margin_w=300,start_headroom_w=500,
                            phase_1_entity='sensor.l1',phase_2_entity='sensor.l2',phase_3_entity='sensor.l3')
    for eid,value in [('sensor.l1',6900),('sensor.l2',-6400),('sensor.l3',0)]:h.states.set(eid,value,{'unit_of_measurement':'W'})
    move(h,w,'2026-09-29T13:00');await r.tick()
    assert not [x for x in h.services.calls if x[0]=='button']

@pytest.mark.asyncio
async def test_only_ev_solar_wait_may_be_ignored_at_grid_deadline(monkeypatch):
    from dataclasses import replace
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w)
    h.states.set('sensor.grid',500,{'unit_of_measurement':'W'})
    original=r.wallbox_guard.update
    def blocked(*args,**kwargs):
        result=replace(original(*args,**kwargs),block_increase=True,release_flexible=True,max_increase_w=0,reason='EV voorkeur wacht')
        r.wallbox_guard.result=result
        return result
    monkeypatch.setattr(r.wallbox_guard,'update',blocked)
    await r.tick();assert not h.services.calls
    move(h,w,'2026-09-29T13:00');await r.tick()
    assert len([x for x in h.services.calls if x[0]=='button'])==1
    assert r.pending['watts']==2000
    assert not [x for x in h.services.calls if x[0] in ('number','switch')]

@pytest.mark.asyncio
async def test_deadline_reserves_other_owned_but_unconsumed_commitments(monkeypatch):
    from custom_components.solar_pilot.const import DEVICE_DEFAULTS
    from custom_components.solar_pilot.engine import State
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w)
    h.states.set('sensor.grid',500,{'unit_of_measurement':'W'});await r.tick()
    # Non-interruptible owned cycle currently in a zero-W phase still reserves 2500 W.
    r.configs['other']={**DEVICE_DEFAULTS,'id':'other','name':'Other example','kind':'switch','control_entity':'switch.other',
                        'power_entity':'sensor.other_power','nominal_w':2500,'non_interruptible':True}
    r.states['other']=State(owned=True,on=True,target_w=2500,measured_w=0)
    r.device_modes['other']='auto';h.states.set('switch.other','on');h.states.set('sensor.other_power',0,{'unit_of_measurement':'W'})
    move(h,w,'2026-09-29T13:00');await r.tick()
    assert not [x for x in h.services.calls if x[0]=='button']
