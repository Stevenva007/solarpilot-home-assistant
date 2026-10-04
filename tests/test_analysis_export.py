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


def test_pseudonyms_do_not_rewrite_schema_or_measurement_keys():
    r,h=report_context()
    r.configs['a']['name']='temperature'
    h.states.get('sensor.grid').attributes['friendly_name']='schema'
    report=r.analysis.build()
    assert report['schema']=='solarpilot.analysis'
    assert report['units']['temperature']=='degC'
    assert 'temperature' not in next(iter(report['effective_configuration']['devices'].values()))['name']


def test_short_device_and_entity_names_are_private_by_default():
    r,h=report_context()
    r.configs['a']['name']='EV'
    h.states.get('sensor.grid').attributes['friendly_name']='WC'
    report=r.analysis.build()
    assert next(iter(report['effective_configuration']['devices'].values()))['name']!='EV'
    assert all(row.get('attributes',{}).get('friendly_name')!='WC' for row in report['entities'].values())


def test_default_export_hides_old_friendly_names_after_entity_rename():
    r,h=report_context()
    wall=time.time()
    h.states.get('sensor.grid').attributes['friendly_name']='Nieuwe meter'
    r.analysis.changes.append({'ts':wall-1,'entity_id':'sensor.grid','attributes':{'friendly_name':'Oude privémeter'}})
    report=r.analysis.build()
    assert 'Oude privémeter' not in json.dumps(report,ensure_ascii=False)


@pytest.mark.parametrize('label',['auto','W','sensor'])
def test_private_labels_preserve_protocol_modes_units_and_entity_joins(label):
    r,h=report_context()
    r.configs['a']['name']=label
    r.note(f'{label} gebruikt sensor.grid; Wattmeting en automatische regeling.')
    r.smart_climate.state.expected_mode={'climate.zone':'auto'}
    report=r.analysis.build()
    assert next(iter(report['effective_configuration']['devices'].values()))['name']!=label
    assert report['units']['power']=='W'
    assert report['components']['runtime_and_models']['smart_climate']['expected_mode']
    assert set(report['components']['runtime_and_models']['smart_climate']['expected_mode'].values())=={'auto'}
    grid=report['configuration']['site']['grid_entity']
    assert grid.startswith('sensor.source_') and grid in report['entities']
    assert 'Wattmeting' in json.dumps(report,ensure_ascii=False)


def test_pseudonyms_preserve_escaped_labels_and_replace_only_complete_words():
    r,h=report_context()
    label='WC'
    private_name='Meter "privé" \\ kelder'
    r.configs['a']['name']=label
    h.states.get('sensor.grid').attributes['friendly_name']=private_name
    r.note(f'WC meet WClicht; {private_name} leest sensor.grid')
    report=r.analysis.build()
    text=json.dumps(report,ensure_ascii=False)
    assert 'WClicht' in text
    assert json.dumps(private_name,ensure_ascii=False)[1:-1] not in text
    assert next(iter(report['effective_configuration']['devices'].values()))['name']!='WC'


def test_pseudonyms_accept_multiple_entity_references_in_diagnostic_data():
    r,h=report_context()
    r.analysis.event('diagnostic','Meerdere bronnen',{'entity_id':['sensor.grid','sensor.pv'],'friendly_name':'Privégroep'})
    report=r.analysis.build()
    event=next(row for row in report['telemetry']['events'] if row['kind']=='diagnostic')
    assert all(entity.startswith('sensor.source_') for entity in event['data']['entity_id'])
    assert event['data']['friendly_name']!='Privégroep'


def test_short_consumer_ids_are_pseudonymized_consistently_in_all_device_maps():
    r,h=report_context()
    r.device_modes['a']='auto'
    report=r.analysis.build()
    devices=report['effective_configuration']['devices']
    alias=next(iter(devices))
    assert alias.startswith('consumer_') and alias!='a'
    assert devices[alias]['id']==alias
    assert report['configuration']['options']['devices'][0]['id']==alias
    assert alias in report['telemetry']['fast'][0]['devices']
    assert alias in report['components']['runtime_and_models']['device_modes']
    assert alias in report['components']['consumer_history']['devices']


@pytest.mark.parametrize('device_id',['auto','schema','temperature','W'])
def test_consumer_id_collisions_preserve_machine_fields_and_nested_mode_values(device_id):
    r,h=report_context()
    raw=json.loads(json.dumps(r.analysis.prepare()).replace('"a"',json.dumps(device_id)))
    raw['components']['runtime_and_models']['mode']='auto'
    raw['components']['runtime_and_models']['device_modes']={device_id:'auto'}
    report=ae.AnalysisRecorder.finalize(raw)
    alias=next(iter(report['effective_configuration']['devices']))
    assert alias.startswith('consumer_')
    assert report['schema']=='solarpilot.analysis'
    assert report['units']['power']=='W' and report['units']['temperature']=='degC'
    assert report['components']['runtime_and_models']['mode']=='auto'
    assert report['components']['runtime_and_models']['device_modes']=={alias:'auto'}


def test_battery_names_and_stable_ids_are_private_with_consistent_alias_joins():
    r,h=report_context()
    private_id='marstek_kapsalon'
    private_name='Marstek van privé-kapsalon'
    r.entry.options['batteries']=[{'id':private_id,'name':private_name,'power_entity':'sensor.battery_power','soc_entity':'sensor.battery_soc'}]
    raw=r.analysis.prepare()
    raw['components']['runtime_and_models']['battery_fleet']={'faults':{private_id:'Controle gevraagd'},'pending':{'battery_id':private_id},'expected_numbers':{private_id:{'entity_id':'number.battery','target':500}}}
    raw['components']['energy_planning_climate']['battery_fleet']={'batteries':[{'id':private_id,'name':private_name,'power_w':500}]}
    report=ae.AnalysisRecorder.finalize(raw)
    battery=report['configuration']['options']['batteries'][0]
    alias=battery['id']
    assert alias.startswith('battery_') and private_id not in json.dumps(report)
    assert private_name not in json.dumps(report,ensure_ascii=False)
    journal=report['components']['runtime_and_models']['battery_fleet']
    assert journal['pending']['battery_id']==alias
    assert alias in journal['faults'] and alias in journal['expected_numbers']
    assert report['components']['energy_planning_climate']['battery_fleet']['batteries'][0]['id']==alias


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


def test_beta36_export_reports_real_coverage_instead_of_requested_window():
    r,h=build();now=time.time()
    r.analysis.samples.extend([
        {"ts":now-4*3600,"grid_w":-500,"pv_w":1500},
        {"ts":now-4*3600+300,"grid_w":-450,"pv_w":1450},
        {"ts":now-3600,"grid_w":-300,"pv_w":1200},
        {"ts":now-3600+300,"grid_w":-250,"pv_w":1150},
    ])
    r.analysis.fast.extend([{"ts":now-1200},{"ts":now-60}])
    r.analysis.events.append({"ts":now-1800,"kind":"restart","message":"test"})
    data=r.analysis.build(hours=168,include_names=True)
    cov=data["coverage_summary"]
    assert cov["requested_hours"]==168
    assert 3.0 < cov["available_raw_hours"] < 4.1
    assert 0 < cov["covered_hours"] < 1
    assert cov["coverage_pct"] < 1
    assert cov["offline_or_unregistered_gap_hours"] > 2
    assert cov["restart_count"]==1
    assert 0 < cov["fast_telemetry_hours"] < 1
    assert data["schema_version"]==2
    assert "solarpilot_live_learning" in data["data_provenance"]
    assert "extra meettijd" in data["data_provenance"]["calculated_start_profiles"]
