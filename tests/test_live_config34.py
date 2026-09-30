"""Real live options mixin with schema/selector doubles. No HA Core server."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from copy import deepcopy
import pytest
from test_runtime import build
from test_dishwasher_app31 import configured, ready


@pytest.fixture
def flow_class(monkeypatch):
    lib=ModuleType('voluptuous');lib.Required=lambda key,**kw:key;lib.Optional=lambda key,**kw:key;lib.Schema=lambda v:v
    monkeypatch.setitem(sys.modules,'voluptuous',lib)
    selectors=ModuleType('homeassistant.helpers.selector')
    for n in ('BooleanSelector','SelectSelector'):
        setattr(selectors,n,lambda *args,**kw:args[0] if args else {})
    monkeypatch.setitem(sys.modules,selectors.__name__,selectors)
    import homeassistant.helpers as helpers
    monkeypatch.setattr(helpers,'selector',selectors,raising=False)
    path=Path(__file__).parents[1]/'custom_components/solar_pilot/live_config.py'
    spec=importlib.util.spec_from_file_location('custom_components.solar_pilot._flow34',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    class F(module.LiveOptionsMixin):
        def __init__(self,r):self.r=r;self.config_entry=r.entry;self.hass=r.hass
        def _runtime(self):return self.r
        def async_show_form(self,**kw):return kw
        def async_create_entry(self,**kw):return {'type':'create_entry',**kw}
        def async_abort(self,**kw):return {'type':'abort',**kw}
        def _choice_schema(self):return {}
        async def async_step_device(self):return {'step_id':'device'}
        async def async_step_connection(self):return {'step_id':'connection'}
        async def async_step_device_schedule(self):return {'step_id':'device_schedule'}
    return F


@pytest.mark.asyncio
async def test_ordinary_final_confirmation_requires_explicit_checkbox(flow_class):
    r,h=build();r.mode='solar';f=flow_class(r);d=deepcopy(f._base_options());d['devices'][0]['name']='Changed'
    answer=await f._live_save(d)
    assert answer['step_id']=='apply_changes' and 'confirm' in answer['data_schema']
    answer=await f.async_step_apply_changes({'confirm':False})
    assert answer['errors'] and r.configs['a']['name']=='Testtoestel'
    answer=await f.async_step_apply_changes({'confirm':True})
    assert answer['type']=='create_entry' and r.configs['a']['name']=='Changed'
    assert r.mode=='solar' and not h.services.calls


@pytest.mark.asyncio
async def test_scope_question_present_only_for_current_request(flow_class,monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w);f=flow_class(r)
    d=deepcopy(f._base_options());d['devices'][0]['dishwasher_start_deadline']='12:00:00'
    result=await f._live_save(d)
    assert 'request_scope' in result['data_schema']
    assert [x['value'] for x in result['data_schema']['request_scope']['options']]==['future','current']


@pytest.mark.asyncio
async def test_save_after_concurrent_conflict_is_rejected(flow_class):
    r,h=build();f=flow_class(r);d=deepcopy(f._base_options());d['devices'][0]['name']='Mine'
    r.entry.options['devices'][0]['name']='Elsewhere'
    await f._live_save(d)
    result=await f.async_step_apply_changes({'confirm':True})
    assert result['errors']['base']=='live_change' and 'elders' in result['description_placeholders']['issue']


@pytest.mark.asyncio
@pytest.mark.parametrize('section,next_step',[('settings','device'),('connections','connection'),('planning','device_schedule')])
async def test_management_routes_reuse_current_native_wizard(flow_class,section,next_step):
    r,h=build();r.mode='solar';r.priorities['a']=3;f=flow_class(r)
    result=await f.async_step_manage_device({'device_id':'a','section':section})
    assert result['step_id']==next_step and f._device['priority']==3
    assert f._device is not r.configs['a']


@pytest.mark.asyncio
async def test_replacement_requires_explicit_consent_and_fresh_sources(flow_class):
    r,h=build();f=flow_class(r)
    result=await f.async_step_replace({'device_id':'a'})
    assert result['step_id']=='confirm_replace'
    result=await f.async_step_confirm_replace({'confirm':False})
    assert result['step_id']=='confirm_replace'
    result=await f.async_step_confirm_replace({'confirm':True})
    assert result['step_id']=='device' and f._device['id']!='a' and not f._device.get('control_entity')
    assert r.configs['a']['control_entity']=='switch.load'


@pytest.mark.asyncio
async def test_pending_form_can_cancel_one_without_pausing_other_device(flow_class):
    r,h=build();r.mode='solar';r.states['a'].on=True
    b=deepcopy(r.entry.options);d=deepcopy(b);d['devices'][0]['nominal_w']=1500
    await r.live_options.submit(b,d)
    f=flow_class(r);result=await f.async_step_pending_changes()
    assert 'cancel' in result['data_schema']
    result=await f.async_step_pending_changes({'cancel':['device:a']})
    assert result['type']=='create_entry' and not r.entry.options['_live_pending'] and r.mode=='solar'
