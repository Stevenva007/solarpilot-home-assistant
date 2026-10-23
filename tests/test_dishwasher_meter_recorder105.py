"""Exercise the real history recorder without providing actuator services."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
import asyncio
import importlib.util
import sys
import pytest

ROOT=Path(__file__).parents[1]/'custom_components/solar_pilot'
BASE=datetime(2026,1,1,12,tzinfo=timezone.utc)
CFG={'id':'test_dishwasher','name':'Test dishwasher','kind':'dishwasher',
    'power_entity':'sensor.example_power','energy_entity':'sensor.example_energy'}

@pytest.fixture
def recorder(monkeypatch):
    package=ModuleType('meter105_test');package.__path__=[str(ROOT)]
    monkeypatch.setitem(sys.modules,'meter105_test',package)
    class Store:
        def __init__(self,*args): self.data=None;self.saved=[];self.callbacks=[]
        async def async_load(self): return self.data
        async def async_save(self,data): self.saved.append(data)
        def async_delay_save(self,callback,*args): self.callbacks.append(callback)
    storage=ModuleType('homeassistant.helpers.storage');storage.Store=Store
    monkeypatch.setitem(sys.modules,'homeassistant.helpers.storage',storage)
    for name in ('const','consumer_history','dishwasher_meter','consumer_history_runtime'):
        spec=importlib.util.spec_from_file_location('meter105_test.'+name,ROOT/(name+'.py'))
        mod=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,spec.name,mod);spec.loader.exec_module(mod)
    states={}
    hass=SimpleNamespace(states=SimpleNamespace(get=states.get),config=SimpleNamespace(time_zone='Europe/Brussels'))
    entry=SimpleNamespace(entry_id='fixture',runtime_data=SimpleNamespace(_dedicated_meter=lambda key:True))
    r=mod.ConsumerHistoryRecorder(hass,entry,{'test_dishwasher':dict(CFG)},5)
    r.now=lambda:BASE
    asyncio.run(r.start())
    def tick(second,watts,*,energy=None,native=None,finished=False):
        now=BASE+timedelta(seconds=second);r.now=lambda:now
        for key,value,unit in [('power_entity',watts,'W'),('energy_entity',energy if energy is not None else 10+second*.00001,'kWh')]:
            states[r.configs['test_dishwasher'][key]]=SimpleNamespace(state=value,attributes={'unit_of_measurement':unit,'state_class':'total_increasing'},last_reported=now,last_updated=now)
        r.observe('test_dishwasher',native,now,native_finished=finished)
    return r,tick,states,mod

def test_history_records_manual_run_cloud_unknown(recorder):
    r,tick,_,_=recorder
    tick(0,0)
    for t in range(5,100,5):tick(t,100)
    d=r.detail('test_dishwasher')
    assert len(d['sessions'])==1
    assert d['sessions'][0]['start_source']=='external'
    assert d['sessions'][0]['activity_source']=='exclusive_power_meter'
    assert d['on_s']>0 and d['meter']['power_w']==100
    assert d['meter_day']['kwh']>0
    assert not r.error

def test_no_solarpilot_attribution_without_confirmed_command(recorder):
    r,tick,_,_=recorder
    tick(0,0);r.command('test_dishwasher',1000,'test request')
    for t in range(5,100,5):tick(t,100)
    assert r.detail('test_dishwasher')['sessions'][0]['start_source']!='solarpilot'

def test_idle_end_never_claims_completed_program(recorder):
    r,tick,_,_=recorder
    tick(0,0)
    for t in range(5,100,5):tick(t,100)
    for t in range(100,1005,5):tick(t,0)
    detail=r.detail('test_dishwasher');session=detail['sessions'][0]
    assert session['end'] is not None and session['stop_confirmed'] is False
    assert session['stop_source']=='unknown' and detail['stops']==0

def test_gap_does_not_invent_zero_watts_or_off(recorder):
    r,tick,_,_=recorder
    tick(0,0)
    for t in range(5,100,5):tick(t,100)
    tick(100,'unavailable')
    d=r.detail('test_dishwasher')
    assert d['meter']['power_w'] is None
    assert d['sessions'][0]['stop_confirmed'] is False

def test_snapshot_preserves_energy_and_access_sources(recorder):
    r,tick,_,_=recorder
    tick(0,0);tick(5,0)
    data=r._checkpoint()
    assert data['dishwasher_meters']
    sources,complete=r.access_sources('test_dishwasher')
    assert complete and 'sensor.example_energy' in sources

def test_invalid_history_kept_unwritable(recorder):
    r,tick,_,mod=recorder
    other=mod.ConsumerHistoryRecorder(r.hass,r.entry,r.configs)
    other.store.data={'version':1,'timezone':'Europe/Brussels','devices':{},'dishwasher_meters':[]}
    asyncio.run(other.start())
    assert not other._writable and other.error

def test_counter_rebinding_does_not_relabel_old_totals(recorder):
    r,tick,_,_=recorder
    tick(0,0);tick(5,0)
    old_key=r._meter_key('test_dishwasher');before=r._checkpoint()['dishwasher_meters'][old_key]
    r.configs['test_dishwasher']['energy_entity']='sensor.example_second_energy'
    tick(10,0)
    assert r._checkpoint()['dishwasher_meters'][old_key]==before
    assert r.detail('test_dishwasher')['meter_day']['kwh'] is None

def test_read_only_brief_does_not_refresh_stale_meter(recorder):
    r,tick,_,_=recorder
    tick(0,0)
    r.now=lambda:BASE+timedelta(seconds=200)
    b=r.brief('test_dishwasher')['meter']
    assert b['power_valid'] is False and b['power_w'] is None
    assert b['active'] is None

def test_runtime_source_isolation_does_not_use_meter_for_actuator():
    text=(ROOT/'runtime.py').read_text()
    start=text.index('    def _active(');end=text.index('    def _number(',start)
    assert 'meter' not in text[start:end]
    assert 'read_dishwasher' in text[start:end]


def test_changed_thresholds_reset_debounce_preserve_measured_energy(recorder):
    r,tick,_,_=recorder
    tick(0,0);tick(5,100);tick(60,100)
    before=r.detail('test_dishwasher')['meter_day']['kwh']
    r.configs['test_dishwasher']['dishwasher_meter_start_s']=120
    tick(65,100)
    assert r.detail('test_dishwasher')['meter']['active'] is None
    assert r.detail('test_dishwasher')['meter_day']['kwh']==before
    tick(125,100)
    assert r.detail('test_dishwasher')['meter']['active'] is None
    tick(185,100)
    assert r.detail('test_dishwasher')['meter']['active'] is True
