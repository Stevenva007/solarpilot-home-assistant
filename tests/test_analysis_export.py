"""Analysis is comprehensive, bounded, private by default and never sends commands."""
from collections import deque
from datetime import datetime, timezone
from types import SimpleNamespace
import json
import logging
import time
import pytest
from test_runtime import build
from custom_components.solar_pilot import analysis_export as ae
from homeassistant.helpers import entity_registry as er


def report_context():
    r,h=build();r._observe(time.monotonic(),datetime.now(timezone.utc))
    r.grid_w=-2500;r.pv_w=3500
    r.analysis.capture(3.2)
    return r,h


def test_all_modules_and_sources_present_without_writes():
    r,h=report_context();r.note('Regelvoorbeeld');before=list(h.services.calls)
    data=r.analysis.build(include_names=True)
    assert data['schema']=='solarpilot.analysis'
    for k in ['runtime_and_models','energy_planning_climate','consumers','wallbox','dhw','consumer_history','dishwasher']:
        assert k in data['components']
    for k in ['local_pv','battery_analysis','battery_fleet','smart_climate','phase_learning','unified_planner','electricity_cost']:
        assert k in data['components']['runtime_and_models']
    assert data['entities']['sensor.grid']['attributes']['unit_of_measurement']=='W'
    assert data['entities']['sensor.grid']['last_reported']
    assert data['telemetry']['samples'] and data['telemetry']['fast']
    assert not data['coverage']['section_errors']
    assert h.services.calls==before


def test_no_retrospective_raw_data_claim():
    r,h=build();data=r.analysis.build()
    assert not data['telemetry']['samples']
    assert data['coverage']['first_sample'] is None
    assert 'geen Recorder-backfill' in data['coverage']['note']


def test_pseudonyms_consistent_default_not_names():
    r,h=report_context();h.states.get('sensor.grid').attributes['friendly_name']='Meter van de woning'
    r.note('Testtoestel leest sensor.grid')
    data=r.analysis.build();text=json.dumps(data)
    assert 'sensor.grid' not in text and 'Testtoestel' not in text and 'Meter van de woning' not in text
    alias=data['configuration']['site']['grid_entity']
    assert alias in data['entities'] and alias.startswith('sensor.source_')
    assert data['telemetry']['samples'][0]['entities'][alias][0]=='-2500'
    assert not data['privacy']['entity_names_included']


def test_names_explicit_option_still_filters_secrets():
    r,h=report_context();r.entry.options['debug']={'password':'PRIVATE_PASSWORD','token':'PRIVATE_TOKEN','latitude':51.123}
    r.note('Bearer SuperSecretValue https://example.com/secret?key=secret')
    data=r.analysis.build(include_names=True);text=json.dumps(data)
    assert 'sensor.grid' in text
    assert 'PRIVATE_PASSWORD' not in text and 'PRIVATE_TOKEN' not in text and 'SuperSecretValue' not in text
    assert 'example.com' not in text and '51.123' not in text

@pytest.mark.parametrize('key',['api_key','access_token','refreshToken','password','credentials','latitude','longitude','email','mac_address','ip_address','serial_number'])
def test_sensitive_keys_removed(key):
    assert ae.safe({key:'PERSONALVALUE'})[key]=='[REDACTED]'


def test_metadata_temperatures_and_related_alarm_attributes():
    r,h=report_context();h.states.set('sensor.alarm','OK',{'DISH_ALARM_IF1':'OFF','password':'SECRET','unit_of_measurement':'W'})
    data=ae.entity_snapshot(h,'sensor.alarm',time.time())
    assert data['attributes']['DISH_ALARM_IF1']=='OFF'
    assert 'password' not in data['attributes']


def test_unknown_and_nan_not_encoded_as_zero():
    assert ae.safe(float('nan')) is None
    assert ae.safe(float('inf')) is None
    assert ae.safe({'a':'unavailable'})['a']=='unavailable'
    assert '[unsupported' in ae.safe(object())


def test_changed_source_static_attributes_exported_once_dynamic_in_each_sample(monkeypatch):
    r,h=build();wall=time.time();monkeypatch.setattr(ae,'time',SimpleNamespace(time=lambda:wall,monotonic=lambda:5))
    r.entry.options['analysis']={'extra_entities':['climate.zone']}
    h.states.set('climate.zone','heat',{'temperature':21,'current_temperature':20,'hvac_action':'heating'})
    r.analysis.capture(1);wall+=301
    h.states.set('climate.zone','heat',{'temperature':21,'current_temperature':20.2,'hvac_action':'heating'})
    r.analysis.capture(2)
    data=r.analysis.build(include_names=True)
    assert len(data['telemetry']['samples'])==2
    assert data['telemetry']['samples'][-1]['entities']['climate.zone'][3]['current_temperature']==20.2
    assert len([x for x in data['telemetry']['changes'] if x['entity_id']=='climate.zone'])==1


def test_freshness_not_faked_when_states_stay_same(monkeypatch):
    r,h=build();wall=time.time();monkeypatch.setattr(ae,'time',SimpleNamespace(time=lambda:wall,monotonic=lambda:5))
    r.analysis.capture(1);stamp=r.analysis.samples[0]['entities']['sensor.grid'][1];wall+=301;r.analysis.capture(1)
    assert r.analysis.samples[-1]['entities']['sensor.grid'][1]==stamp


def test_related_device_expansion_has_private_domain_exclusion_and_cap(monkeypatch):
    r,h=build()
    rows=[SimpleNamespace(entity_id=f'sensor.related_{i}',disabled_by=None) for i in range(300)]
    rows += [SimpleNamespace(entity_id=x,disabled_by=None) for x in ['camera.house','person.user','sensor.api_token','lock.frontdoor']]
    monkeypatch.setattr(er,'async_get',lambda h:SimpleNamespace(async_get=lambda e:SimpleNamespace(device_id='d1')))
    monkeypatch.setattr(er,'async_entries_for_device',lambda reg,id:rows,raising=False)
    refs=r.analysis.refs()
    assert len(refs)==250 and 'sensor.grid' in refs
    assert not {'camera.house','person.user','sensor.api_token','lock.frontdoor'} & set(refs)
    data=r.analysis.build();assert data['coverage']['sources_omitted_by_cap']>0


def test_events_sample_and_changes_have_caps():
    r,h=build()
    for _ in range(ae.MAX_EVENTS+3):r.analysis.event('test','value')
    assert len(r.analysis.events)==ae.MAX_EVENTS and r.analysis.dropped['events']==3
    for _ in range(ae.MAX_SAMPLES+2):r.analysis._append('samples',{'ts':time.time()})
    assert len(r.analysis.samples)==ae.MAX_SAMPLES and r.analysis.dropped['samples']==2


def test_retention_prunes_old_data():
    r,h=build();wall=time.time()
    r.analysis.samples.extend([{'ts':wall-8*86400},{'ts':wall-1}]);r.analysis.prune(wall)
    assert len(r.analysis.samples)==1


def test_disabled_collection_stops_new_samples_events():
    r,h=build();r.analysis.settings['enabled']=False
    r.analysis.capture(10);r.note('should not be recorded')
    assert not r.analysis.samples and not r.analysis.events and not r.analysis.fast
    assert not r.analysis.build()['coverage']['collection_enabled']


def test_partial_error_does_not_hide_other_modules():
    r,h=report_context();r.ems_overview=lambda:(_ for _ in ()).throw(ValueError('fail'))
    data=r.analysis.build();assert data['coverage']['section_errors']=={'energy_planning_climate':'ValueError'}
    assert data['components']['dhw']


def test_payload_snapshot_is_detached_for_worker():
    r,h=report_context();data=r.analysis.prepare();r.analysis.samples[-1]['grid_w']=99;r.configs['a']['nominal_w']=123
    assert data['telemetry']['samples'][-1]['grid_w']!=99
    assert data['effective_configuration']['devices']['a']['nominal_w']!=123


def test_export_size_guard(monkeypatch):
    monkeypatch.setattr(ae,'MAX_EXPORT_BYTES',100)
    with pytest.raises(ValueError):ae.serialize_report({'a':'x'*101})

@pytest.mark.asyncio
async def test_storage_roundtrip_and_fast_trace_not_backfilled():
    r,h=report_context();await r.analysis.start();r.analysis.capture(1);await r.analysis.close()
    stored=r.analysis.store.data
    r2,h2=build();r2.analysis.store.data=stored;await r2.analysis.start()
    assert r2.analysis.samples and not r2.analysis.fast
    await r2.analysis.close()

@pytest.mark.asyncio
async def test_only_solarpilot_warnings_logs_no_global_hass_data():
    r,h=build();await r.analysis.start()
    logging.getLogger('custom_components.solar_pilot.dishwasher').warning('Test alarm secret=PRIVATEVAL')
    logging.getLogger('unrelated_homeassistant').warning('DO_NOT_EXPORT')
    text=json.dumps(r.analysis.build(include_names=True))
    assert 'Test alarm' in text and 'PRIVATEVAL' not in text and 'DO_NOT_EXPORT' not in text
    await r.analysis.close();assert r.analysis.log_handler is None

@pytest.mark.asyncio
async def test_analysis_failures_do_not_prevent_controller_or_shutdown():
    r,h=build();r.analysis.capture=lambda *x:(_ for _ in ()).throw(ValueError('telemetry failure'))
    r.mode='solar';r.device_modes['a']='auto';await r.tick()
    assert h.services.calls and r.mode=='solar' and 'onvolledig' in r.analysis.error
    r.analysis.loaded=True
    async def fail(data):raise OSError('disk')
    r.analysis.store.async_save=fail
    await r.close();assert r.store.data


def test_fast_ram_trace_never_outlives_two_hours():
    r,h=build();wall=time.time()
    r.analysis.fast.extend([{'ts':wall-7201},{'ts':wall-10}]);r.analysis.prune(wall)
    assert len(r.analysis.fast)==1


def test_export_keeps_model_context_but_filters_old_session_detail():
    r,h=report_context();wall=time.time()
    row=r.consumer_history.model.devices['a']
    row['sessions']=[{'id':1,'start':wall-100000,'end':wall-90000},{'id':2,'start':wall-10,'end':None,'observed_until':wall}]
    row['events']=[{'at':wall-100000},{'at':wall-1}]
    result=r.analysis.build(hours=1,include_names=True)
    out=result['components']['consumer_history']['devices']['a']
    assert len(out['sessions'])==1 and len(out['events'])==1
    assert len(row['sessions'])==2  # Export doesn't mutate stored history.


def test_current_registry_metadata_without_device_identifiers(monkeypatch):
    import sys
    from types import ModuleType
    from homeassistant import helpers
    dr=ModuleType('homeassistant.helpers.device_registry')
    dr.async_get=lambda h:SimpleNamespace(async_get=lambda i:SimpleNamespace(manufacturer='AEG',model='test',sw_version='1',hw_version='2',serial_number='PRIVATE_SERIAL'))
    monkeypatch.setitem(sys.modules,dr.__name__,dr);monkeypatch.setattr(helpers,'device_registry',dr,raising=False)
    monkeypatch.setattr(er,'async_get',lambda h:SimpleNamespace(async_get=lambda i:SimpleNamespace(device_id='PRIVATE_DEVICE',platform='electrolux_status')))
    r,h=build();out=ae.source_metadata(h,['sensor.grid'])
    assert out['sensor.grid']['platform']=='electrolux_status'
    assert out['sensor.grid']['device_ref']=='device_1'
    assert 'PRIVATE' not in json.dumps(out)
