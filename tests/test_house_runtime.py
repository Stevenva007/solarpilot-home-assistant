"""Closed-loop scenarios with controllable time and simulated HA entities.

This is NOT a physical charger test, and does not use Home Assistant Core.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
import time as real_time
import pytest
from custom_components.solar_pilot import runtime as module
from custom_components.solar_pilot.runtime import SolarRuntime
from custom_components.solar_pilot.house_first import HouseFirstGuard
from custom_components.solar_pilot.wallbox import WallboxGuard
from test_runtime import Services


class Clock:
    def __init__(self):
        self.t=0
        self.base=real_time.time()
    def monotonic(self): return 10000+self.t
    def time(self): return self.base+self.t


class States:
    def __init__(self, clock): self.c=clock; self.data={}
    def get(self, key): return self.data.get(key)
    def set(self,key,value,attrs=None,age=0):
        stamp=datetime.fromtimestamp(self.c.time()-age, timezone.utc)
        self.data[key]=SimpleNamespace(state=str(value),attributes=attrs or {},last_updated=stamp,last_reported=stamp)


def setup(monkeypatch, device=None, wallbox=None, settings=None):
    c=Clock(); monkeypatch.setattr(module,'time',c)
    states=States(c); h=SimpleNamespace(states=states,services=Services(states))
    entry=SimpleNamespace(entry_id='test',data={'grid_entity':'sensor.grid','reserve_w':150,
                                              'settle_s':5,'filter_s':5,**(settings or {})},options={
        'wallbox': {'enabled':True,'power_entity':'sensor.ev','status_entity':'sensor.ev_status',
                    'mode_entity':'select.ev_mode','stable_s':30,'handover_s':120,
                    'handover_confirm_s':15,'cooldown_s':120,**(wallbox or {})},
        'devices':[{'id':'a','name':'Toestel','kind':'switch','control_entity':'switch.load',
                    'power_entity':'sensor.load','nominal_w':1000,'min_on_s':0,'min_off_s':0,
                    'start_delay_s':0,'stop_delay_s':0,'start_margin_w':0,
                    'allow_wallbox_reclaim':True, **(device or {})}]})
    states.set('switch.load','off')
    r=SolarRuntime(h,entry); r.mode='solar'; r.device_modes['a']='auto'
    return r,h,c


async def tick(r,h,c,t,*,ev=4000,grid=-150,load=0,mode='full_solar',status='Charging',refresh_ev=True):
    c.t=t
    h.states.set('sensor.grid',grid,{'unit_of_measurement':'W'})
    h.states.set('sensor.load',load,{'unit_of_measurement':'W'})
    if refresh_ev:
        h.states.set('sensor.ev',ev,{'unit_of_measurement':'W'})
        h.states.set('sensor.ev_status',status)
        h.states.set('select.ev_mode',mode)
    await r.tick()
    assert not r.problem.startswith('Interne fout'), r.problem


async def start_transfer(r,h,c):
    for t in range(0,31,5): await tick(r,h,c,t)
    assert r.handover and r.pending
    assert h.states.get('switch.load').state=='on'


@pytest.mark.asyncio
async def test_default_switch_on_and_only_metered_load_is_started_after_stability(monkeypatch):
    r,h,c=setup(monkeypatch)
    assert r.others_first and isinstance(r.wallbox_guard,HouseFirstGuard)
    await start_transfer(r,h,c)
    assert r.result.free_w==0
    assert r.handover.borrowed_w==1000
    assert len(h.services.calls)==1
    assert h.services.calls[0][2]['entity_id']=='switch.load'
    assert r.store.data['others_first'] is True
    assert 'a' in r.store.data['leases']


@pytest.mark.asyncio
async def test_successful_loop_holds_during_ev_response_and_never_commands_wallbox(monkeypatch):
    r,h,c=setup(monkeypatch)
    await start_transfer(r,h,c)
    for t in range(35,60,5): await tick(r,h,c,t,grid=850,load=1000)
    assert r.handover.status=='waiting' and len(h.services.calls)==1
    for t in range(60,80,5): await tick(r,h,c,t,ev=3000,grid=-150,load=1000)
    assert r.handover is None and r.learning.successes==1
    assert len(h.services.calls)==1 and r.states['a'].owned
    assert r.last_handover['state']=='success'
    for t in range(80,150,5): await tick(r,h,c,t,ev=3000,grid=-150,load=1000)
    assert len(h.services.calls)==1 and r.states['a'].owned
    assert r.managed_w==1000  # EV's 3000 W is not managed usage.


@pytest.mark.asyncio
async def test_timeout_rolls_back_and_latches_reclaim_block_without_blind_retry(monkeypatch):
    r,h,c=setup(monkeypatch)
    await start_transfer(r,h,c)
    for t in range(35,151,5): await tick(r,h,c,t,grid=850,load=1000)
    assert h.states.get('switch.load').state=='off' and 'a' in r.reclaim_blocks
    assert r.learning.failures==1 and r.learning.successes==0
    await tick(r,h,c,155)
    assert r.handover is None
    for t in range(160,400,5): await tick(r,h,c,t)
    assert len(h.services.calls)==2 and not r.devices()[0].allow_wallbox_reclaim


@pytest.mark.asyncio
async def test_failed_transfer_can_later_use_real_export_without_borrowing(monkeypatch):
    r,h,c=setup(monkeypatch)
    r.reclaim_blocks['a']='Previously not confirmed'
    for t in range(0,31,5): await tick(r,h,c,t,ev=0,grid=-1500,status='Ready')
    assert len(h.services.calls)==1 and r.handover is None


@pytest.mark.asyncio
async def test_switch_off_yields_existing_flexible_load_without_charger_calls(monkeypatch):
    r,h,c=setup(monkeypatch)
    await start_transfer(r,h,c)
    for t in range(35,65,5): await tick(r,h,c,t,ev=3000,grid=-150,load=1000)
    assert r.handover is None
    await r.set_others_first(False)
    assert isinstance(r.wallbox_guard,WallboxGuard) and not r.others_first
    assert h.states.get('switch.load').state=='off'
    assert all(call[2].get('entity_id')=='switch.load' for call in h.services.calls)
    assert r.store.data['others_first'] is False


@pytest.mark.asyncio
async def test_switch_during_handover_cancels_without_losing_control(monkeypatch):
    r,h,c=setup(monkeypatch)
    await start_transfer(r,h,c)
    await tick(r,h,c,35,grid=850,load=1000)
    await r.set_others_first(False)
    assert r.handover.status=='rollback'
    assert h.states.get('switch.load').state=='off'
    assert r.reclaim_blocks and not r.others_first


@pytest.mark.asyncio
async def test_invalid_mode_cannot_trigger_claim(monkeypatch):
    r,h,c=setup(monkeypatch)
    for t in range(0,60,5): await tick(r,h,c,t,mode='eco_mode')
    assert not h.services.calls and not r.handover


@pytest.mark.asyncio
async def test_mode_change_during_handover_requests_rollback(monkeypatch):
    r,h,c=setup(monkeypatch)
    await start_transfer(r,h,c)
    await tick(r,h,c,35,mode='eco_mode',grid=850,load=1000)
    assert h.states.get('switch.load').state=='off' and r.reclaim_blocks


@pytest.mark.asyncio
async def test_actual_import_above_limit_requests_rollback(monkeypatch):
    r,h,c=setup(monkeypatch)
    await start_transfer(r,h,c)
    await tick(r,h,c,35,grid=4000,load=1000)
    assert h.states.get('switch.load').state=='off' and r.reclaim_blocks


@pytest.mark.asyncio
async def test_observation_never_starts_or_creates_a_handover(monkeypatch):
    r,h,c=setup(monkeypatch); r.mode='observe'
    for t in range(0,60,5): await tick(r,h,c,t)
    assert r.result.action is not None and not r.handover and not h.services.calls


@pytest.mark.asyncio
async def test_restore_remembers_user_switch_and_learned_data_but_starts_observe(monkeypatch):
    r,h,c=setup(monkeypatch)
    r.store.data={'others_first':False,'learning':{'enabled':True,'responses_s':[200]*5}}
    await tick(r,h,c,0)
    r.mode='observe'
    await r.start()
    assert not r.others_first and isinstance(r.wallbox_guard,WallboxGuard)
    assert r.mode=='observe' and len(r.learning.responses)==5
    assert r.wallbox_guard.settings['stable_s']==230
    assert not h.services.calls


@pytest.mark.asyncio
async def test_beta2_preferences_migrate_once_to_new_default_on(monkeypatch):
    r,h,c=setup(monkeypatch,wallbox={'policy':'priority'})
    r.store.data={'priorities':{'a':2},'energy_kwh':1.5}
    r.mode='observe'
    await tick(r,h,c,0)
    await r.start()
    assert r.others_first and r.priorities['a']==2 and r.energy_kwh==1.5
    assert not h.services.calls


@pytest.mark.asyncio
async def test_restart_with_pending_lease_requires_manual_recovery(monkeypatch):
    r,h,c=setup(monkeypatch)
    r.store.data={'others_first':True,'leases':{'a':{'watts':1000,'name':'Toestel'}}}
    r.mode='observe'
    await tick(r,h,c,0)
    await r.start()
    assert r.recovery and not r.handover
    assert all(call[0]=='persistent_notification' for call in h.services.calls)


@pytest.mark.asyncio
async def test_missing_appliance_meter_is_not_implicitly_allowed(monkeypatch):
    r,h,c=setup(monkeypatch,device={'power_entity':''})
    for t in range(0,60,5): await tick(r,h,c,t)
    assert not h.services.calls and not r.devices()[0].allow_wallbox_reclaim


@pytest.mark.asyncio
async def test_reset_learning_does_not_change_priority_or_safety(monkeypatch):
    r,h,c=setup(monkeypatch)
    r.mode='observe'; r.learning.record_handover(True,100)
    await tick(r,h,c,0)
    await r.reset_learning()
    assert r.others_first and not r.learning.responses
    assert r.settings['max_import_w']==3500 and not h.services.calls


@pytest.mark.asyncio
async def test_pause_during_transfer_requests_own_rollback(monkeypatch):
    r,h,c=setup(monkeypatch)
    await start_transfer(r,h,c)
    await tick(r,h,c,35,grid=850,load=1000)
    await r.set_mode('paused')
    assert h.states.get('switch.load').state=='off'
    assert r.handover.status=='rollback' and r.mode=='paused'


@pytest.mark.asyncio
async def test_priority_switch_has_no_dispatch_effect_without_wallbox_monitor(monkeypatch):
    r,h,c=setup(monkeypatch,wallbox={'enabled':False})
    await tick(r,h,c,0,grid=-2000)
    await tick(r,h,c,5,grid=-1000,load=1000)
    assert r.states['a'].owned
    calls=len(h.services.calls)
    await r.set_others_first(False)
    assert not r._yield_to_wallbox
    assert h.states.get('switch.load').state=='on' and len(h.services.calls)==calls


@pytest.mark.asyncio
@pytest.mark.parametrize('meter',['sensor.grid','sensor.pv'])
async def test_site_meter_cannot_masquerade_as_dedicated_appliance_meter(monkeypatch,meter):
    r,h,c=setup(monkeypatch,device={'power_entity':meter},settings={'pv_entity':'sensor.pv'})
    h.states.set('sensor.pv',6000,{'unit_of_measurement':'W'})
    for t in range(0,60,5): await tick(r,h,c,t)
    assert not r.devices()[0].allow_wallbox_reclaim
    assert 'exclusief' in r.states['a'].fault and not h.services.calls
