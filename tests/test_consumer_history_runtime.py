"""Observe and persist consumer history without changing existing control semantics."""
from datetime import datetime, timedelta, timezone
import time
import pytest

from test_runtime import build
from custom_components.solar_pilot.engine import Action
from custom_components.solar_pilot.consumer_history_runtime import ConsumerHistoryRecorder

BASE=datetime(2026,9,27,8,tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_runtime_records_only_acknowledged_transition_and_action_reason():
    r,h=build();mono=time.monotonic();r.consumer_history.now=lambda:BASE
    r._observe(mono,BASE)
    await r._send(Action('a',1000,'Voldoende zonnestroom'),mono)
    assert not r.consumer_history.model.detail('a',None,BASE)['sessions']
    r.consumer_history.now=lambda:BASE+timedelta(seconds=5)
    await r._confirm_pending(mono+5);r._observe(mono+5,BASE+timedelta(seconds=5))
    r.consumer_history.now=lambda:BASE+timedelta(seconds=20)
    await r._send(Action('a',0,'Regelaar gepauzeerd'),mono+20)
    r.consumer_history.now=lambda:BASE+timedelta(seconds=25)
    await r._confirm_pending(mono+25);r._observe(mono+25,BASE+timedelta(seconds=25))
    d=r.consumer_history.detail('a')
    assert d['on_s']==20 and len(d['sessions'])==1
    assert d['sessions'][0]['start_reason']=='Voldoende zonnestroom'
    assert d['sessions'][0]['stop_reason']=='Regelaar gepauzeerd'
    assert [c[1] for c in h.services.calls]==['turn_on','turn_off']


@pytest.mark.asyncio
async def test_failed_start_adds_history_warning_not_running_session():
    r,h=build();h.services.respond=False;r.consumer_history.now=lambda:BASE
    r._observe(time.monotonic(),BASE)
    await r._send(Action('a',1000,'Zonnestroom'),time.monotonic())
    await r._confirm_pending(time.monotonic()+100)
    assert not r.consumer_history.detail('a')['sessions']
    assert len(r.consumer_history.detail('a')['events'])==1


@pytest.mark.asyncio
async def test_service_error_does_not_create_physical_start_history():
    r,h=build();h.services.fail=True;r.consumer_history.now=lambda:BASE
    r._observe(time.monotonic(),BASE)
    # Notifications also fail with this test double; this does not affect the history assertion.
    async def notify(_):pass
    r.notify=notify
    await r._send(Action('a',1000,'Zonnestroom'),time.monotonic())
    assert not r.consumer_history.detail('a')['sessions']
    assert r.consumer_history.detail('a')['events'][0]['kind']=='warning'


@pytest.mark.asyncio
async def test_histories_are_separate_from_core_snapshot_and_lightweight_state_attributes():
    r,h=build();await r.tick()
    assert 'consumer_history' not in r._snapshot()
    row=r.overview()[0]
    assert 'history' in row and 'sessions' not in row['history']
    assert len(str(row['history']))<220


@pytest.mark.asyncio
async def test_read_only_observation_never_adopts_or_controls_external_load():
    r,h=build();h.states.set('switch.load','on');r.mode='observe'
    await r.tick()
    assert h.services.calls==[] and not r.states['a'].owned
    d=r.consumer_history.detail('a')
    assert d['sessions'][0]['start_source']=='unknown'


@pytest.mark.asyncio
async def test_history_failure_cannot_stop_core_energy_control(monkeypatch):
    r,h=build();r.mode='solar';r.device_modes['a']='auto'
    def broken(*args,**kwargs):raise ValueError('broken optional telemetry')
    monkeypatch.setattr(r.consumer_history.model,'observe',broken)
    await r.tick()
    assert r.mode=='solar' and r.pending and r.consumer_history.error


@pytest.mark.asyncio
async def test_external_takeover_event_does_not_claim_stop():
    r,h=build();h.states.set('switch.load','on');await r.tick()
    await r.takeover('a')
    d=r.consumer_history.detail('a')
    assert d['stops']==0 and d['sessions'][0]['ongoing']
    assert any('GEEN uitschakelopdracht' in e['reason'] for e in d['events'])


@pytest.mark.asyncio
async def test_checkpoint_restored_after_reload_with_no_downtime_runtime():
    r,h=build();rec=r.consumer_history;rec.now=lambda:BASE;await rec.start()
    rec.observe('a',True,BASE);rec.observe('a',True,BASE+timedelta(seconds=20))
    await rec.close();data=rec.store.data
    other=ConsumerHistoryRecorder(h,r.entry,r.configs);other.now=lambda:BASE+timedelta(hours=1)
    other.store.data=data;await other.start()
    other.observe('a',True,BASE+timedelta(hours=1))
    assert other.detail('a')['on_s']==20
    assert other.detail('a')['sessions'][0]['stop_confirmed'] is False


@pytest.mark.asyncio
async def test_no_storage_writes_on_every_five_second_observation(monkeypatch):
    r,h=build();rec=r.consumer_history;rec.now=lambda:BASE;await rec.start()
    callbacks=[]
    rec.store.async_delay_save=lambda cb,delay:callbacks.append(cb)
    rec.observe('a',False,BASE)
    for i in range(1,12):rec.observe('a',False,BASE+timedelta(seconds=i*5))
    assert len(callbacks)==1  # The already-scheduled checkpoint is not postponed every tick.
    callbacks.pop()()
    for i in range(12,15):rec.observe('a',False,BASE+timedelta(seconds=i*5))
    assert callbacks==[]


@pytest.mark.asyncio
async def test_history_storage_failure_does_not_prevent_main_runtime_snapshot(monkeypatch):
    r,h=build();await r.consumer_history.start()
    async def failed_save(_):raise OSError('disk failure in optional history')
    monkeypatch.setattr(r.consumer_history.store,'async_save',failed_save)
    await r.close()
    assert r._closed and r.consumer_history.error
    assert r.store.data is not None
