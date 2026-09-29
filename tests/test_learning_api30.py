"""Admin authorization, stale approvals, no hidden actuator authority."""
from pathlib import Path
from types import ModuleType
import importlib.util
import sys
import pytest
from test_consumer_history_api import context


@pytest.fixture(params=['voluptuous','probatio'])
def api(monkeypatch,request):
    for backend in ('voluptuous','probatio'):
        lib=ModuleType(backend);lib.Required=lambda k:k;lib.Optional=lambda k:k
        monkeypatch.setitem(sys.modules,backend,lib)
    msg=ModuleType('homeassistant.components.websocket_api.messages')
    msg.BASE_COMMAND_MESSAGE_SCHEMA=type('Schema',(),{'__module__':request.param+'.schema'})()
    monkeypatch.setitem(sys.modules,msg.__name__,msg)
    comp=ModuleType('homeassistant.components');ws=ModuleType('homeassistant.components.websocket_api')
    ws.websocket_command=lambda s:lambda fn:fn;ws.async_response=lambda fn:fn
    ws.async_register_command=lambda h,fn:h.registered.append(fn);comp.websocket_api=ws
    monkeypatch.setitem(sys.modules,comp.__name__,comp);monkeypatch.setitem(sys.modules,ws.__name__,ws)
    path=Path(__file__).resolve().parents[1]/'custom_components/solar_pilot/learning_api.py'
    name='custom_components.solar_pilot._learning_api_test';spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,name,mod);spec.loader.exec_module(mod)
    assert mod.vol.__name__==request.param
    return mod


@pytest.mark.asyncio
async def test_read_models_evidence_not_devices(api):
    r,h,c,out,err=context();before=list(h.services.calls)
    await api.websocket_learning(h,c,{'id':1,'config_entry_id':'test'})
    assert not err and len(out[0]['models'])==7 and out[0]['questions']
    assert h.services.calls==before


@pytest.mark.asyncio
@pytest.mark.parametrize('operation',['read','answer','policy'])
@pytest.mark.parametrize('user',[None,False])
async def test_only_admin_can_query_or_answer(api,operation,user):
    r,h,c,out,err=context(admin=False)
    if user is None:c.user=None
    await api.websocket_learning(h,c,{'id':1,'config_entry_id':'test','operation':operation})
    assert err==['unauthorized'] and not out and not h.services.calls


@pytest.mark.asyncio
async def test_correct_answer_updates_model_policy_only(api):
    r,h,c,out,err=context();q=r.learning_hub.refresh()['questions'][0]
    await api.websocket_learning(h,c,{'id':1,'config_entry_id':'test','operation':'answer','question':q['id'],'revision':q['revision'],'choice':'auto'})
    assert not err and r.learning_hub.policy['adaptation']=='automatic'
    assert r.mode=='observe' and not h.services.calls


@pytest.mark.asyncio
async def test_old_question_refused_after_config_change(api):
    r,h,c,out,err=context();q=r.learning_hub.refresh()['questions'][0];r.settings['pv_entity']='sensor.other'
    await api.websocket_learning(h,c,{'id':1,'config_entry_id':'test','operation':'answer','question':q['id'],'revision':q['revision'],'choice':'auto'})
    assert err==['stale_question'] and not r.unified_planner.base_load.adaptive_enabled


@pytest.mark.asyncio
@pytest.mark.parametrize('operation',['delete','call_service','exec','start'])
async def test_no_arbitrary_operation(api,operation):
    r,h,c,out,err=context()
    await api.websocket_learning(h,c,{'id':1,'config_entry_id':'test','operation':operation})
    assert err==['invalid_operation'] and not h.services.calls


@pytest.mark.asyncio
async def test_write_failure_rolls_back_model_permissions(api):
    r,h,c,out,err=context()
    async def failed(data):raise OSError('full disk')
    r.store.async_save=failed
    await api.websocket_learning(h,c,{'id':1,'config_entry_id':'test','operation':'policy','setting':'adaptation','value':'automatic'})
    assert err==['learning_failed'] and r.learning_hub.policy['adaptation']=='assisted'
    assert not r.unified_planner.base_load.adaptive_enabled and not h.services.calls


@pytest.mark.asyncio
async def test_wrong_entry_and_unloaded_no_operations(api):
    r,h,c,out,err=context()
    await api.websocket_learning(h,c,{'id':1,'config_entry_id':'wrong'})
    assert err==['not_loaded'] and not out
    r._closed=True
    await api.websocket_learning(h,c,{'id':2,'config_entry_id':'test'})
    assert err==['not_loaded','not_loaded']


def test_register_idempotently(api):
    r,h,c,out,err=context();api.async_register_learning_api(h);api.async_register_learning_api(h)
    assert len(h.registered)==1
