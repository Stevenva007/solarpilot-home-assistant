"""Authenticated WS handler contracts against explicit HA doubles."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import sys
import json
import pytest
from test_consumer_history_api import context

@pytest.fixture(params=['voluptuous','probatio'])
def api(monkeypatch,request):
    for backend in ('voluptuous','probatio'):
        lib=ModuleType(backend);lib.Required=lambda key:key;lib.Optional=lambda key:key
        monkeypatch.setitem(sys.modules,backend,lib)
    messages=ModuleType('homeassistant.components.websocket_api.messages')
    messages.BASE_COMMAND_MESSAGE_SCHEMA=type('Schema',(),{'__module__':request.param+'.schema'})()
    monkeypatch.setitem(sys.modules,messages.__name__,messages)
    comp=ModuleType('homeassistant.components');ws=ModuleType('homeassistant.components.websocket_api')
    ws.websocket_command=lambda schema:lambda fn:fn
    ws.async_response=lambda fn:fn
    ws.async_register_command=lambda h,fn:h.registered.append(fn)
    comp.websocket_api=ws
    monkeypatch.setitem(sys.modules,'homeassistant.components',comp)
    monkeypatch.setitem(sys.modules,ws.__name__,ws)
    path=Path(__file__).resolve().parents[1]/'custom_components/solar_pilot/analysis_api.py'
    name='custom_components.solar_pilot._test_analysis_api'
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,name,mod);spec.loader.exec_module(mod)
    assert mod.vol.__name__==request.param
    return mod

@pytest.mark.asyncio
async def test_export_admin_download_only_no_writes(api):
    r,h,c,out,err=context();await r.tick();before=list(h.services.calls)
    await api.websocket_analysis_export(h,c,{'id':1,'config_entry_id':'test'})
    assert not err and out[0]['filename'].endswith('.json')
    data=json.loads(out[0]['content']);assert data['schema']=='solarpilot.analysis'
    assert h.services.calls==before and not r.analysis.exporting

@pytest.mark.asyncio
@pytest.mark.parametrize('admin',[False,None])
async def test_admin_required_not_just_read_access(api,admin):
    r,h,c,out,err=context(admin=False)
    if admin is None:c.user=None
    await api.websocket_analysis_export(h,c,{'id':1,'config_entry_id':'test'})
    assert err==['unauthorized'] and not out

@pytest.mark.asyncio
@pytest.mark.parametrize('value',[0,-1,2,24.0,True,169,100000,'24'])
async def test_period_strict_validation(api,value):
    r,h,c,out,err=context()
    await api.websocket_analysis_export(h,c,{'id':1,'config_entry_id':'test','hours':value})
    assert err==['invalid_options'] and not out

@pytest.mark.asyncio
async def test_unloaded_and_wrong_entry(api):
    r,h,c,out,err=context()
    await api.websocket_analysis_export(h,c,{'id':1,'config_entry_id':'wrong'})
    assert err==['not_loaded']

@pytest.mark.asyncio
async def test_rate_limit_and_only_explicit_names(api):
    r,h,c,out,err=context()
    await api.websocket_analysis_export(h,c,{'id':1,'config_entry_id':'test','include_names':True})
    assert 'sensor.grid' in out[0]['content']
    await api.websocket_analysis_export(h,c,{'id':2,'config_entry_id':'test'})
    assert err==['busy']

@pytest.mark.asyncio
async def test_worker_failure_releases_flag(api,monkeypatch):
    r,h,c,out,err=context();monkeypatch.setattr(api,'serialize_report',lambda p:(_ for _ in ()).throw(ValueError('large')))
    await api.websocket_analysis_export(h,c,{'id':1,'config_entry_id':'test'})
    assert err==['export_too_large'] and not r.analysis.exporting


def test_idempotent_registration(api):
    r,h,c,out,err=context();api.async_register_analysis_api(h);api.async_register_analysis_api(h)
    assert len(h.registered)==1
