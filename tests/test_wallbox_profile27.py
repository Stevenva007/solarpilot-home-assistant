"""Auto-read profile: same-device sources, live provenance, safe fallback, no writes."""
import time
from types import SimpleNamespace as NS
import pytest
from homeassistant.helpers import entity_registry as er
from custom_components.solar_pilot.wallbox_profile import WallboxProfile,validate_profile
from test_runtime import build

def setup(**settings):
    _,h=build();return WallboxProfile(h,settings),h

def test_default_fallback_is_1phase25a_and_readonly():
    p,h=setup();x=p.update();assert x['phases']==1 and x['max_current_a']==25
    assert x['maximum_power_w']==5750 and x['minimum_power_w']==1380 and x['warning']
    assert x['current_source']=='handmatig bevestigd profiel' and not h.services.calls

@pytest.mark.parametrize('amps,phases,power',[(25,1,5750),(16,3,11040),(6,1,1380)])
def test_reads_current_and_explicit_phases(amps,phases,power):
    p,h=setup(max_current_entity='number.ev_current',phases_entity='sensor.ev_phases')
    h.states.set('number.ev_current',amps,{'max':32});h.states.set('sensor.ev_phases',phases)
    d=p.update();assert d['maximum_power_w']==power and d['current_source']=='Wallbox-integratie'
    assert d['phase_source']=='expliciete Wallbox-bron' and not h.services.calls

@pytest.mark.parametrize('entity,value,unit,age',[('sensor.current','nan','A',0),('sensor.current',25,'kW',0),('number.ev_current',25,None,301),('number.max_icp_current',32,None,0),('number.ev_current','unavailable',None,0)])
def test_bad_and_icp_sources_never_claim_live(entity,value,unit,age):
    p,h=setup(max_current_entity=entity);h.states.set(entity,value,{'unit_of_measurement':unit},age=age)
    d=p.update();assert d['max_current_a']==25 and d['current_source']!='Wallbox-integratie' and d['warning']

@pytest.mark.parametrize('value',[0,2,4,25,'unknown'])
def test_never_infers_phases_from_bad_value_or_amps(value):
    p,h=setup(phases_entity='sensor.phases');h.states.set('sensor.phases',value)
    assert p.update()['phases']==1

def test_new_state_not_hardware_max_is_used_and_hardware_cap_respected():
    p,h=setup(max_current_entity='number.ev_current');h.states.set('number.ev_current',16,{'max':25})
    assert p.update()['max_current_a']==16
    h.states.set('number.ev_current',32,{'max':25});assert p.update()['max_current_a']==25

def test_discovery_matches_same_wallbox_device_without_names(monkeypatch):
    p,h=setup(power_entity='sensor.charger_power');rows={
        'sensor.charger_power':NS(entity_id='sensor.charger_power',device_id='ev',platform='wallbox',translation_key='charging_power',disabled_by=None),
        'number.right':NS(entity_id='number.right',device_id='ev',platform='wallbox',translation_key='max_charging_current',disabled_by=None),
        'number.other':NS(entity_id='number.other',device_id='other',platform='wallbox',translation_key='max_charging_current',disabled_by=None),
        'sensor.mirror':NS(entity_id='sensor.mirror',device_id='ev',platform='wallbox',translation_key='max_charging_current',disabled_by=None)}
    monkeypatch.setattr(er,'async_get',lambda _:NS(entities=rows,async_get=rows.get))
    h.states.set('number.right',20);h.states.set('number.other',32)
    d=p.update();assert d['current_entity']=='number.right' and d['max_current_a']==20

def test_ambiguous_discovery_does_not_guess(monkeypatch):
    p,h=setup(power_entity='sensor.ref');rows={'sensor.ref':NS(entity_id='sensor.ref',device_id='ev',platform='wallbox',translation_key='power',disabled_by=None)}
    for n in ['a','b']:rows[n]=NS(entity_id='number.'+n,device_id='ev',platform='wallbox',translation_key='max_charging_current',disabled_by=None)
    monkeypatch.setattr(er,'async_get',lambda _:NS(entities=rows,async_get=rows.get));assert p.update()['current_entity'] is None

def test_discovery_is_rate_limited(monkeypatch):
    p,h=setup();hits=[];monkeypatch.setattr(er,'async_get',lambda _:(hits.append(1) or NS()))
    for t in range(120):p.update(monotonic=t)
    assert len(hits)==1

@pytest.mark.parametrize('c',[{'charging_phases':2},{'max_current_a':float('nan')},{'max_current_a':5},{'voltage_v':400},{'minimum_current_a':16,'max_current_a':10},{'max_current_entity':'number.maximum_icp_current'}])
def test_profile_invalid_inputs(c):assert validate_profile(c)

def test_profile_string_numbers_validate_without_type_error():assert not validate_profile({'charging_phases':'3','max_current_a':'25','minimum_current_a':'6'})

def test_live_current_limit_below_minimum_does_not_starve_lower_loads():
    from custom_components.solar_pilot.consumer_wallbox import ConsumerWallboxPriority
    from custom_components.solar_pilot.wallbox import Reading
    p=ConsumerWallboxPriority({'enabled':True,'priority_min_power_w':1380,'priority_max_power_w':0,'full_solar_states':'full_solar'})
    r=Reading(power_w=0,stamp=1,demand=True,status='Waiting for green energy',mode='full_solar',valid=True,connected=True)
    result=p.update(now=10,reading=r,grid_w=-3000,filtered_grid_w=-3000,discharge_w=0,owned_lower={},has_lower=True)
    assert result.state=='current_limit' and not result.block_starts and not result.yield_loads
