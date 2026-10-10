"""New wizard validation with explicit selector/schema doubles, not real HA."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import pytest
from test_dishwasher import setup
from homeassistant.helpers import entity_registry as er

@pytest.fixture
def form(monkeypatch):
    lib=ModuleType('voluptuous')
    lib.Required=lambda key,**kw:key
    lib.Optional=lambda key,**kw:key
    lib.Schema=lambda val:val
    monkeypatch.setitem(sys.modules,'voluptuous',lib)
    selectors=ModuleType('homeassistant.helpers.selector')
    for name in ('EntitySelector','NumberSelector','TextSelector','BooleanSelector','SelectSelector','TimeSelector'):
        setattr(selectors,name,lambda *args,**kwargs:args[0] if args else {})
    monkeypatch.setitem(sys.modules,selectors.__name__,selectors)
    import homeassistant.helpers as helpers
    monkeypatch.setattr(helpers,'selector',selectors,raising=False)
    spec=importlib.util.spec_from_file_location('custom_components.solar_pilot._config29',Path(__file__).resolve().parents[1]/'custom_components/solar_pilot/dishwasher_config.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    r,h,c=setup(dishwasher_mapping_confirmed=False)
    class Flow(mod.DishwasherOptionsMixin):
        def __init__(self):self.hass=h;self.config_entry=r.entry;self._device=dict(c)
        def _site(self):return r.settings
        def async_show_form(self,**kw):return kw
        async def async_step_device_behavior(self):return {'step_id':'device_behavior'}
        async def _save(self,opts):self.saved=opts;return {'step_id':'saved'}
    monkeypatch.setattr(er,'async_get',lambda h:SimpleNamespace(async_get=lambda eid:SimpleNamespace(device_id='aeg')))
    return Flow(),h,c

@pytest.mark.asyncio
async def test_initial_connection_has_required_guards_not_power_actuator(form):
    f,h,c=form;result=await f.async_step_dishwasher_connection()
    for key in ('start_button','dishwasher_state_entity','dishwasher_connection_entity','dishwasher_door_entity','dishwasher_remote_entity','cycle_program_entity'):
        assert key in result['data_schema']
    assert 'power_entity' in result['data_schema']
    assert 'control_entity' not in result['data_schema'] and 'stop_script' not in result['data_schema']

@pytest.mark.asyncio
async def test_connection_without_shelly_can_be_saved_unconfirmed(form):
    f,h,c=form;result=await f.async_step_dishwasher_connection(c)
    assert result['step_id']=='dishwasher_states'
    assert not f._device['dishwasher_mapping_confirmed']

@pytest.mark.asyncio
@pytest.mark.parametrize('source',['sensor.grid','sensor.dw_shared','sensor.dw_badunit'])
async def test_wrong_shared_power_source_blocked(form,source):
    f,h,c=form
    h.states.set('sensor.dw_shared',0,{'unit_of_measurement':'W'})
    h.states.set('sensor.dw_badunit',0,{'unit_of_measurement':'kWh'})
    f.config_entry.options['wallbox']={'power_entity':'sensor.dw_shared'}
    result=await f.async_step_dishwasher_connection({**c,'power_entity':source})
    assert 'power_entity' in result['errors']


@pytest.mark.asyncio
async def test_panasonic_readonly_meter_remains_exclusive_from_dishwasher(form):
    f,h,c=form
    h.states.set('sensor.generic_heatpump',0,{'unit_of_measurement':'W'})
    f.config_entry.options['sg_boost']={'power_entity':'sensor.generic_heatpump'}
    calls=list(h.services.calls)
    result=await f.async_step_dishwasher_connection({**c,'power_entity':'sensor.generic_heatpump'})
    assert result['errors']['power_entity']=='dedicated_meter'
    assert h.services.calls==calls

@pytest.mark.asyncio
async def test_mapping_confirmation_requires_same_device(form,monkeypatch):
    f,h,c=form;monkeypatch.setattr(er,'async_get',lambda h:SimpleNamespace(async_get=lambda eid:SimpleNamespace(device_id=None)))
    result=await f.async_step_dishwasher_states({'dishwasher_mapping_confirmed':True})
    assert result['errors']['base']=='dishwasher_same_device'

@pytest.mark.asyncio
async def test_valid_states_proceed_to_existing_protection_step(form):
    f,h,c=form;result=await f.async_step_dishwasher_states({'dishwasher_mapping_confirmed':True})
    assert result['step_id']=='device_behavior'

@pytest.mark.asyncio
async def test_stale_restored_start_button_not_accepted(form):
    f,h,c=form;h.states.set('button.dw_start','unknown',{'restored':True})
    result=await f.async_step_dishwasher_connection(c)
    assert result['errors']['start_button']=='dishwasher_restored'

@pytest.mark.asyncio
async def test_export_settings_do_not_write_to_devices(form):
    f,h,c=form;calls=list(h.services.calls)
    result=await f.async_step_analysis({'enabled':False,'extra_entities':['sensor.grid']})
    assert result['step_id']=='saved' and not f.saved['analysis']['enabled']
    assert h.services.calls==calls

@pytest.mark.asyncio
@pytest.mark.parametrize('eid',['camera.x','person.x','device_tracker.x','lock.x','sensor.missing'])
async def test_export_extra_source_not_supported_or_missing(form,eid):
    f,h,c=form
    if eid!='sensor.missing':h.states.set(eid,'test')
    result=await f.async_step_analysis({'extra_entities':[eid]})
    assert 'extra_entities' in result['errors']

@pytest.mark.asyncio
async def test_export_source_count_capped(form):
    f,h,c=form;ids=['sensor.x'+str(n) for n in range(51)]
    for eid in ids:h.states.set(eid,'1')
    result=await f.async_step_analysis({'extra_entities':ids})
    assert result['errors']['extra_entities']=='analysis_too_many'
