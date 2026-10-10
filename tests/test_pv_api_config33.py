"""Execute actual HTTP-independent command/flow methods against explicit HA doubles."""
import ast
import asyncio
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
from datetime import datetime,timezone
import json
import pytest
from test_runtime import build
from custom_components.solar_pilot.pv_forecast_source import PV_FORECAST_DEFAULTS,ENTITY_ROLES,finite
from custom_components.solar_pilot.const import DOMAIN

C=Path(__file__).resolve().parents[1]/'custom_components/solar_pilot'

def function(path,name,namespace):
    tree=ast.parse((C/path).read_text(encoding='utf-8'))
    node=next(n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    node.decorator_list=[]
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(C/path),'exec'),namespace)
    return namespace[name]

class Connection:
    def __init__(self,admin):self.user=NS(is_admin=admin) if admin is not None else None;self.errors=[];self.results=[]
    def send_error(self,*args):self.errors.append(args)
    def send_result(self,*args):self.results.append(args)


def endpoint():return function('pv_forecast_api.py','websocket_pv_diagnostics',{'DOMAIN':DOMAIN,'deepcopy':deepcopy})

@pytest.mark.asyncio
@pytest.mark.parametrize('admin',[False,None])
async def test_diagnostics_only_admin(admin):
    c=Connection(admin);await endpoint()(None,c,{'id':1,'config_entry_id':'x'})
    assert c.errors[0][1]=='unauthorized' and not c.results

@pytest.mark.asyncio
async def test_wrong_entry_never_returns_other_integration():
    c=Connection(True);h=NS(config_entries=NS(async_get_entry=lambda _:NS(domain='other',runtime_data=None)))
    await endpoint()(h,c,{'id':1,'config_entry_id':'x'})
    assert c.errors[0][1]=='not_loaded'


def loaded():
    r,h=build();r.entry.domain=DOMAIN;r.entry.runtime_data=r;r._closed=False
    h.config_entries=NS(async_get_entry=lambda _:r.entry)
    return r,h

@pytest.mark.asyncio
@pytest.mark.parametrize('reset',['true',1,None,[]])
async def test_reset_requires_literal_boolean(reset):
    r,h=loaded();c=Connection(True)
    await endpoint()(h,c,{'id':1,'config_entry_id':'test','reset_confirm':reset})
    assert c.errors[0][1]=='invalid_options' and not h.services.calls

@pytest.mark.asyncio
async def test_read_diagnostics_no_reset_or_write():
    r,h=loaded();c=Connection(True);before=deepcopy(r.pv_forecast.snapshot())
    await endpoint()(h,c,{'id':1,'config_entry_id':'test'})
    assert c.results and not c.errors and r.pv_forecast.snapshot()==before and not h.services.calls

@pytest.mark.asyncio
async def test_reset_only_pv_preserves_other_learning_and_device_state():
    r,h=loaded();r.pv_forecast.model.counts['accepted']=20;r.pv_forecast.model.revision=20
    r.sg_boost._clock=lambda:100.0;r.sg_boost._wall_clock=lambda:1000.0
    r.pv_forecast.cached={'available':True,'factor':.6};before=r._snapshot()
    c=Connection(True);await endpoint()(h,c,{'id':1,'config_entry_id':'test','reset_confirm':True})
    assert not c.errors and r.pv_forecast.model.counts['accepted']==0
    assert not c.results[0][1]['summary']['available'] and not h.services.calls
    after=r._snapshot()
    for key in ('dishwasher','dishwasher_app','panasonic_archive','sg_boost','learning','phase_learning','priorities','device_modes'):
        assert before.get(key)==after.get(key),key

@pytest.mark.asyncio
async def test_reset_save_failure_restores_pv_and_cache():
    r,h=loaded();r.pv_forecast.model.counts['accepted']=20;r.pv_forecast.cached={'available':True,'factor':.6}
    before=deepcopy(r.pv_forecast.snapshot());cache=deepcopy(r.pv_forecast.cached)
    async def fail(*a):raise OSError('Disk failed')
    r.store.async_save=fail
    c=Connection(True);await endpoint()(h,c,{'id':1,'config_entry_id':'test','reset_confirm':True})
    assert c.errors[0][1]=='save_failed' and not c.results
    assert r.pv_forecast.snapshot()==before and r.pv_forecast.cached==cache and not h.services.calls


def flow():
    r,h=build()
    class Flow:
        config_entry=r.entry;hass=h
        def _base_options(self): return self.config_entry.options
        async def _save(self,opts):self.saved=opts;return {'saved':True}
        def async_show_form(self,**kwargs):return kwargs
    vol=NS(Required=lambda x,**kw:x,Optional=lambda x,**kw:x,Schema=lambda x:x)
    selector=NS(BooleanSelector=lambda:{},SelectSelector=lambda x:x,TextSelector=lambda:{})
    method=function('config_flow.py','async_step_pv_forecast',dict(PV_FORECAST_DEFAULTS=PV_FORECAST_DEFAULTS,
        ENTITY_ROLES=ENTITY_ROLES,finite=finite,deepcopy=deepcopy,vol=vol,selector=selector,
        optional=lambda key,c:key,entity=lambda domains:{'domain':domains},num=lambda *args:{}))
    return Flow(),h,method

@pytest.mark.asyncio
@pytest.mark.parametrize('key,value',[('learning_preset','bad'),('inverter_limit_w',float('nan')),('panel_peak_wp',0),
    ('minimum_days',4),('minimum_days',5.5),('history_days',31),('stale_s',1),('tilt_deg',91),('azimuth_deg',361),
    ('enabled','true'),('calibration_enabled',1),('auto_discover',None),('shadow_enabled',[]),('show_raw','false')])
async def test_config_bad_values_block_save(key,value):
    f,h,method=flow();result=await method(f,{key:value})
    assert result['errors'].get(key)=='invalid_pv_setting' and not hasattr(f,'saved')

@pytest.mark.asyncio
async def test_config_13800_and_10000_separate_and_no_physical_rights():
    f,h,method=flow();original=deepcopy(f.config_entry.options)
    result=await method(f,{'panel_peak_wp':13800,'inverter_limit_w':10000,'tilt_deg':25,'azimuth_deg':180})
    assert result=={'saved':True}
    assert f.saved['pv_forecast']['panel_peak_wp']==13800 and f.saved['pv_forecast']['inverter_limit_w']==10000
    for k in original:assert f.saved[k]==original[k]
    assert not h.services.calls

@pytest.mark.asyncio
@pytest.mark.parametrize('role,unit',[('now_entity','kWh'),('remaining_entity','W'),('next_hour_entity','A')])
async def test_selectors_do_not_accept_wrong_units(role,unit):
    f,h,method=flow();h.states.set('sensor.source',123,{'unit_of_measurement':unit})
    result=await method(f,{role:'sensor.source'});assert role in result['errors'] and not hasattr(f,'saved')


def test_every_new_option_has_long_help_and_current_docs():
    j=json.loads((C/'frontend/option-help.json').read_text(encoding='utf-8'))
    for step in ('pv_forecast','wallbox','wallbox_advanced','device_schedule'):
        for key in j['steps'][step]['data']:
            assert len(' '.join(j['entries'][f'{step}.{key}']['paragraphs']))>180
    guide=(C/'docs/ACTUELE_WERKING.md').read_text(encoding='utf-8')
    # The current guide describes configurable site values; it must not embed
    # an installation's private inverter/panel ratings as required defaults.
    for phrase in ('effectieve','clipping','Wattpiekvermogen','AC-omvormergrens',
                   'kwartier','Full Solar','PV-diagnose','13:00'):
        assert phrase in guide
