"""AEG uses only button.press, explicit permissions and new status confirmation."""
import time
from datetime import datetime, timezone
import pytest
from test_dishwasher import setup
from custom_components.solar_pilot.engine import Action
from homeassistant.exceptions import HomeAssistantError

async def arm(r):
    r.mode='solar';r.device_modes['a']='auto'
    await r.arm_dishwasher('a')

@pytest.mark.asyncio
async def test_automatic_one_start_then_running_then_no_second_start():
    r,h,c=setup();await arm(r)
    assert [x[:2] for x in h.services.calls]==[('button','press')]
    assert h.services.calls[0][2]['entity_id']=='button.dw_start'
    assert r.pending and r.store.data['dishwasher']['tickets']['a']['attempted']
    h.states.set('sensor.dw_phase','Washing');await r.tick()
    assert not r.pending and r.states['a'].owned
    h.states.set('sensor.dw_phase','Finished');await r.tick()
    h.states.set('sensor.dw_phase','Idle');await r.tick()
    assert len(h.services.calls)==1
    assert not r.dishwasher.tickets['a']['armed']

@pytest.mark.asyncio
async def test_no_permission_after_enabling_mode_alone():
    r,h,c=setup();r.mode='solar';r.device_modes['a']='auto';await r.tick()
    assert not h.services.calls
    assert 'Klaarzetten' in r.result.reasons['a']

@pytest.mark.asyncio
async def test_preparation_observation_does_not_start():
    r,h,c=setup();r.device_modes['a']='auto';await r.arm_dishwasher('a')
    assert not h.services.calls
    assert r.dishwasher.tickets['a']['armed']

@pytest.mark.asyncio
async def test_with_insufficient_sun_remains_prepared():
    r,h,c=setup();h.states.set('sensor.grid',-400,{'unit_of_measurement':'W'});await arm(r)
    assert not h.services.calls and r.dishwasher.tickets['a']['armed']

@pytest.mark.asyncio
async def test_check_again_at_dispatch_when_door_changed():
    r,h,c=setup();r.dishwasher.arm(c,__import__('custom_components.solar_pilot.dishwasher',fromlist=['read']).read(h,c),time.time())
    r.mode='solar';h.states.set('binary_sensor.dw_door','on');await r._send(Action('a',2000,'zon'),time.monotonic())
    assert not h.services.calls

@pytest.mark.asyncio
@pytest.mark.parametrize('scenario',['paused','manual_stop','power_lost','excluded','max_runtime','phase_hold'])
async def test_running_cycle_never_cut_for_energy_or_manual_release(scenario):
    r,h,c=setup();await arm(r);h.states.set('sensor.dw_phase','Drying');await r.tick()
    if scenario=='paused':r.mode='paused'
    elif scenario=='manual_stop':await r.manual_stop('a')
    elif scenario=='excluded':r.device_modes['a']='disabled'
    elif scenario=='max_runtime':r.states['a'].last_on=time.monotonic()-100000
    elif scenario=='phase_hold':r.phase_settings.update(enabled=True,control_release=True)
    else:h.states.set('sensor.grid',4000,{'unit_of_measurement':'W'})
    await r.tick();await r._send(Action('a',0,'stop test'),time.monotonic())
    writes=[x for x in h.services.calls if x[0]!='persistent_notification']
    assert len(writes)==1 and writes[0][:2]==('button','press')

@pytest.mark.asyncio
async def test_manual_start_and_boost_cannot_bypass_readiness():
    r,h,c=setup()
    with pytest.raises(HomeAssistantError):await r.manual_start('a')
    with pytest.raises(HomeAssistantError):await r.boost('a')
    assert not h.services.calls

@pytest.mark.asyncio
async def test_ack_requires_report_newer_than_command_and_timeout_no_retry():
    r,h,c=setup(ack_timeout_s=10);await arm(r)
    h.states.set('sensor.dw_phase','Washing',reported_age=5)
    await r._confirm_pending(time.monotonic());assert r.pending
    h.states.set('sensor.dw_phase','Idle');r.pending['issued']-=11
    await r.tick();await r.tick()
    assert r.faults and r.dishwasher.tickets['a']['attempted']
    assert len([x for x in h.services.calls if x[0]=='button'])==1

@pytest.mark.asyncio
@pytest.mark.parametrize('active',['Idle','Washing','unknown'])
async def test_restart_never_replays_unconfirmed_start(active):
    r,h,c=setup();await arm(r);stored=r._snapshot()
    r2,h2,c2=setup();h2.states.set('sensor.dw_phase',active);r2.store.data=stored
    await r2.start()
    assert not [x for x in h2.services.calls if x[0]=='button']
    if active=='Washing':assert r2.states['a'].owned
    else:assert r2.faults
    await r2.close()

@pytest.mark.asyncio
async def test_failed_start_call_never_retried():
    r,h,c=setup();h.services.fail=True;r.notify=lambda m:__import__('asyncio').sleep(0)
    await arm(r);await r.tick()
    assert r.faults and r.dishwasher.tickets['a']['attempted']
    writes=[call for call in h.services.calls if call[0]!='persistent_notification']
    assert writes==[('button','press',{'entity_id':'button.dw_start'})]
    notices=[call for call in h.services.calls if call[0]=='persistent_notification']
    # Notification transport also fails in this double. Retrying that message
    # must never retry the uncertain physical dishwasher START.
    assert len(notices)==2 and all(call[1]=='create' for call in notices)
    assert all(call[2]['notification_id']=='solar_pilot_test_action_required' for call in notices)
    assert all('Controle afronden' in call[2]['message'] for call in notices)
    assert not r.action_notifications.snapshot()['active']
    h.services.fail=False
    await r.tick();await r.tick()
    assert [call for call in h.services.calls if call[0]!='persistent_notification']==writes
    assert len([call for call in h.services.calls if call[0]=='persistent_notification'])==3
    assert r.action_notifications.snapshot()['active']

@pytest.mark.asyncio
async def test_shelly_is_only_read_no_relays_written():
    r,h,c=setup(power_entity='sensor.shelly_meter');h.states.set('sensor.shelly_meter',0,{'unit_of_measurement':'kW'})
    await arm(r);h.states.set('sensor.dw_phase','Washing');h.states.set('sensor.shelly_meter',1.65,{'unit_of_measurement':'kW'});await r.tick()
    assert r.states['a'].measured_w==1650
    assert [x[:2] for x in h.services.calls]==[('button','press')]

@pytest.mark.asyncio
async def test_missing_cloud_never_turns_drying_into_completed():
    r,h,c=setup();await arm(r);h.states.set('sensor.dw_phase','Drying');await r.tick()
    h.states.set('sensor.dw_connection','Disconnected');await r.tick()
    assert r.states['a'].on and not r.states['a'].available
    assert not [x for x in h.services.calls if x[1] in ('turn_off','set_value')]
