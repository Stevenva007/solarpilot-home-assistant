"""Handler/permission tests with explicit HA doubles, not real websocket transport."""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace, ModuleType
import importlib.util
import sys
import pytest

from test_runtime import build


@pytest.fixture(params=["voluptuous", "probatio"])
def api(monkeypatch, request):
    # Both schema libraries may exist; match the engine used by the WS schema.
    for backend in ("voluptuous", "probatio"):
        lib=ModuleType(backend);lib.Required=lambda key:key;lib.Optional=lambda key:key
        monkeypatch.setitem(sys.modules,backend,lib)
    messages=ModuleType('homeassistant.components.websocket_api.messages')
    schema_cls=type('Schema', (), {'__module__':request.param+'.schema'})
    messages.BASE_COMMAND_MESSAGE_SCHEMA=schema_cls()
    monkeypatch.setitem(sys.modules,messages.__name__,messages)
    components=ModuleType('homeassistant.components');ws=ModuleType('homeassistant.components.websocket_api')
    def schema(definition):
        def wrap(f):f.test_schema=definition;return f
        return wrap
    ws.websocket_command=schema;ws.async_register_command=lambda hass,func:hass.registered.append(func)
    components.websocket_api=ws
    monkeypatch.setitem(sys.modules,'homeassistant.components',components)
    monkeypatch.setitem(sys.modules,'homeassistant.components.websocket_api',ws)
    for name in ('homeassistant.auth','homeassistant.auth.permissions','homeassistant.auth.permissions.const'):
        mod=ModuleType(name);mod.POLICY_READ='read';monkeypatch.setitem(sys.modules,name,mod)
    path=Path(__file__).resolve().parents[1]/'custom_components/solar_pilot/consumer_history_api.py'
    name='custom_components.solar_pilot._test_history_api'
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,name,module);spec.loader.exec_module(module)
    assert module.vol.__name__ == request.param
    return module


def context(admin=True,allowed=True):
    r,h=build();r._observe(10,datetime.now(timezone.utc));r.entry.domain='solar_pilot';r.entry.runtime_data=r
    h.config_entries=SimpleNamespace(async_get_entry=lambda i:r.entry if i=='test' else None)
    h.data={};h.registered=[]
    results=[];errors=[]
    user=SimpleNamespace(is_admin=admin,permissions=SimpleNamespace(check_entity=lambda entity,policy:allowed))
    c=SimpleNamespace(user=user,send_result=lambda i,d:results.append(d),send_error=lambda i,code,msg:errors.append(code))
    return r,h,c,results,errors


def test_admin_can_get_only_selected_consumers_history(api):
    r,h,c,out,errs=context();before=list(h.services.calls)
    api.websocket_consumer_history(h,c,{'id':1,'config_entry_id':'test','device_id':'a'})
    assert not errs and out[0]['device_id']=='a' and h.services.calls==before


@pytest.mark.parametrize('admin,allowed,success',[(False,True,True),(False,False,False),(True,False,True)])
def test_normal_entity_read_permissions(api,admin,allowed,success):
    _,h,c,out,errs=context(admin,allowed)
    api.websocket_consumer_history(h,c,{'id':1,'config_entry_id':'test','device_id':'a'})
    assert bool(out)==success
    if not success:assert errs==['unauthorized']


def test_no_anonymous_access(api):
    _,h,c,out,errs=context();c.user=None
    api.websocket_consumer_history(h,c,{'id':1,'config_entry_id':'test','device_id':'a'})
    assert not out and errs==['unauthorized']


@pytest.mark.parametrize('entry_id,device_id,error',[('wrong','a','not_loaded'),('test','../secrets','not_found')])
def test_unknown_entry_or_consumer_rejected(api,entry_id,device_id,error):
    _,h,c,out,errs=context()
    api.websocket_consumer_history(h,c,{'id':1,'config_entry_id':entry_id,'device_id':device_id})
    assert not out and errs==[error]


def test_unloaded_runtime_no_stale_data(api):
    r,h,c,out,errs=context();r._closed=True
    api.websocket_consumer_history(h,c,{'id':1,'config_entry_id':'test','device_id':'a'})
    assert not out and errs==['not_loaded']


def test_invalid_date_reports_error_without_control_action(api):
    _,h,c,out,errs=context()
    api.websocket_consumer_history(h,c,{'id':1,'config_entry_id':'test','device_id':'a','date':'wrong'})
    assert errs==['invalid_date'] and not h.services.calls


def test_registration_idempotent_across_reloads(api):
    _,h,_,_,_=context();api.async_register_history_api(h);api.async_register_history_api(h)
    assert len(h.registered)==1


def test_history_remove_is_limited_to_own_storage():
    text=(Path(__file__).resolve().parents[1]/'custom_components/solar_pilot/__init__.py').read_text()
    assert 'Store(hass, 1, history_storage_key(entry.entry_id)).async_remove()' in text
