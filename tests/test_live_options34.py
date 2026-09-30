"""Live options transactions against real runtime and explicit HA doubles.

No real loads or Home Assistant server are used. Ordinary changes must preserve
object identity, serialised work, short native end events and explicit authority.
"""
from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
import asyncio
import ast
from pathlib import Path
import pytest
from homeassistant.exceptions import HomeAssistantError
from test_runtime import build
from test_dishwasher_app31 import configured, ready, event, move, stamp
from custom_components.solar_pilot.live_options import (merge_three, replacement_profile,
    PENDING, ARCHIVED, changed_keys, keyed)
from custom_components.solar_pilot.runtime import SolarRuntime
from custom_components.solar_pilot.platforms import LivePlatforms


def desired(r, **changes):
    base=deepcopy(dict(r.entry.options));after=deepcopy(base)
    after['devices'][0].update(changes)
    return base,after


@pytest.mark.parametrize('mode',['solar','paused','observe'])
@pytest.mark.parametrize('change',[{'name':'Nieuwe naam'}, {'priority':7}, {'appliance_type':'washing_machine'}])
@pytest.mark.asyncio
async def test_live_identity_and_timers_unchanged(mode,change):
    r,h=build();r.mode=mode;s=r.states['a'];s.owned=s.on=True;s.last_on=123;s.start_since=456;s.boost_until=900
    r.pending={'id':'a','watts':1000};r.device_modes['a']='auto';r.recovery={'a':'old'}
    pending=r.pending;lock=r._lock;store=r.store
    b,d=desired(r,**change)
    result=await r.live_options.submit(b,d)
    assert result[PENDING]=={}
    assert r.configs['a'].items()>=change.items()
    assert r.states['a'] is s and (s.last_on,s.start_since,s.boost_until)==(123,456,900)
    assert r.mode==mode and r._lock is lock and r.pending is pending and r.store is store
    assert not h.services.calls and r.recovery=={'a':'old'}


@pytest.mark.asyncio
@pytest.mark.parametrize('key,value',[('control_entity','switch.new'),('power_entity','sensor.new'),
                                    ('start_delay_s',300),('min_on_s',1800),('nominal_w',1500)])
async def test_sensitive_edit_queued_only_for_active_device(key,value):
    r,h=build();r.mode='solar';s=r.states['a'];s.owned=s.on=True;r.device_modes['a']='auto'
    before,after=desired(r,**{key:value})
    out=await r.live_options.submit(before,after)
    assert out['devices']==before['devices']
    assert 'device:a' in out[PENDING]
    assert r.states['a'] is s and r.states['a'].owned and r.mode=='solar'
    assert not h.services.calls
    await r.live_options.process_pending()
    assert 'device:a' in r.entry.options[PENDING]
    s.owned=s.on=False;h.states.set('switch.load','off')
    await r.live_options.process_pending()
    assert not r.entry.options[PENDING]
    assert r.configs['a'][key]==value
    assert not h.services.calls


@pytest.mark.asyncio
async def test_queued_effective_bindings_survive_reboot():
    r,h=build();r.states['a'].on=True
    b,d=desired(r,control_entity='switch.replacement')
    await r.live_options.submit(b,d)
    fresh=SolarRuntime(h,r.entry)
    assert fresh.configs['a']['control_entity']=='switch.load'
    assert fresh.entry.options[PENDING]['device:a']['new']['control_entity']=='switch.replacement'
    # Restored old physical status still on: do not apply during start.
    h.states.set('switch.load','on');await fresh.live_options.process_pending()
    assert fresh.configs['a']['control_entity']=='switch.load'


@pytest.mark.parametrize('fault',['recovery','faults','pending','handover','unavailable'])
@pytest.mark.asyncio
async def test_uncertain_device_cannot_rebind(fault):
    r,h=build();r.states['a'].observed_once=True
    if fault in ('recovery','faults'):getattr(r,fault)['a']='uncertain'
    elif fault=='pending':r.pending={'id':'a'}
    elif fault=='handover':r.handover=SimpleNamespace(device_id='a')
    else:h.states.set('switch.load','unavailable')
    b,d=desired(r,control_entity='switch.new')
    out,_=r.live_options.prepare(b,d)
    assert 'device:a' in out[PENDING]


@pytest.mark.asyncio
async def test_cancel_pending_changes_preserves_device_and_mode():
    r,h=build();r.mode='solar';r.states['a'].on=True
    b,d=desired(r,control_entity='switch.new');await r.live_options.submit(b,d)
    await r.live_options.cancel_pending(['device:a'])
    assert not r.entry.options[PENDING] and r.configs['a']['control_entity']=='switch.load'
    assert r.mode=='solar' and not h.services.calls


@pytest.mark.asyncio
async def test_queue_does_not_overwrite_later_edit():
    r,h=build();r.states['a'].on=True
    b,d=desired(r,control_entity='switch.new');await r.live_options.submit(b,d)
    b,d=desired(r,name='Concurrent')
    with pytest.raises(HomeAssistantError):await r.live_options.submit(b,d)
    assert r.configs['a']['name']=='Testtoestel'


def test_three_way_disjoint_leaf_merge():
    base={'economy':{'price':.3,'export':.04},'devices':[{'id':'a','name':'Old','priority':50}]}
    proposed=deepcopy(base);proposed['economy']['price']=.4
    current=deepcopy(base);current['economy']['export']=.1;current['devices'][0]['priority']=1
    merged=merge_three(base,proposed,current)
    assert merged['economy']=={'price':.4,'export':.1} and merged['devices'][0]['priority']==1


def test_three_way_same_leaf_conflict():
    with pytest.raises(HomeAssistantError):merge_three({'a':1},{'a':2},{'a':3})


def test_three_way_add_remove_reorder():
    b={'devices':[{'id':'a','v':1},{'id':'b','v':2}]}
    d={'devices':[{'id':'b','v':2},{'id':'a','v':1},{'id':'c','v':3}]}
    c={'devices':[{'id':'b','v':5}]}
    m=merge_three(b,d,c)
    assert keyed(m['devices'])=={'b':{'id':'b','v':5},'c':{'id':'c','v':3}}


def test_three_way_atomic_list_conflict():
    with pytest.raises(HomeAssistantError):merge_three({'zones':['a']},{'zones':['b']},{'zones':['c']})


@pytest.mark.parametrize('key',['control_entity','power_entity'])
@pytest.mark.asyncio
async def test_duplicate_new_binding_rejected_after_concurrent_merge(key):
    r,h=build();b,d=desired(r)
    d['devices'].append({'id':'b','name':'Second','kind':'switch',key:'sensor.same'})
    r.entry.options['devices'].append({'id':'c','name':'Concurrent','kind':'switch',key:'sensor.same'})
    with pytest.raises(HomeAssistantError):await r.live_options.submit(b,d)
    assert 'b' not in r.configs


@pytest.mark.asyncio
async def test_pending_binding_reserves_endpoint():
    r,h=build();r.states['a'].on=True
    b,d=desired(r,control_entity='switch.new');await r.live_options.submit(b,d)
    b,d=desired(r);d['devices'].append({'id':'b','name':'Other','kind':'switch','control_entity':'switch.new'})
    with pytest.raises(HomeAssistantError):await r.live_options.submit(b,d)


@pytest.mark.asyncio
async def test_storage_failure_no_changed_runtime():
    r,h=build();b,d=desired(r,name='Not stored')
    async def fail(*args):raise OSError('disk')
    r.store.async_save=fail
    with pytest.raises(HomeAssistantError):await r.live_options.submit(b,d)
    assert r.entry.options==b and r.configs['a']['name']=='Testtoestel'
    assert not h.services.calls


@pytest.mark.asyncio
async def test_storage_failure_rolls_back_request_fields(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w)
    beforeq=deepcopy(r.dishwasher_app.data['a']['request'])
    b,d=desired(r,dishwasher_start_deadline='11:00:00',dishwasher_deadline_grid_allowed=False)
    async def fail(*args):raise OSError('disk')
    r.store.async_save=fail
    with pytest.raises(HomeAssistantError):await r.live_options.submit(b,d,'current')
    assert r.entry.options==b and r.dishwasher_app.data['a']['request']==beforeq


@pytest.mark.parametrize('scope',['future','current'])
@pytest.mark.parametrize('grid',[False,True])
@pytest.mark.asyncio
async def test_deadline_scope_fixed_day_and_permission(monkeypatch,scope,grid):
    r,h,c,w=configured(monkeypatch,'2026-09-29T22:00');ready(r,h,c,w)
    q=deepcopy(r.dishwasher_app.data['a']['request']);b,d=desired(r,dishwasher_start_deadline='11:00:00',dishwasher_deadline_grid_allowed=grid)
    assert r.live_options.needs_request_choice(b,d)==['a']
    await r.live_options.submit(b,d,scope)
    actual=r.dishwasher_app.data['a']['request']
    assert actual['planned_day']=='2026-09-30' and actual['policy_locked']
    assert actual['deadline']==(stamp('2026-09-30T11:00') if scope=='current' else q['deadline'])
    assert actual['grid_allowed']==(grid if scope=='current' else q['grid_allowed'])
    assert not h.services.calls
    w[0]=actual['deadline']+60
    assert r.dishwasher_app.due(r.configs['a'],w[0]) == (grid if scope=='current' else q['grid_allowed'])


@pytest.mark.asyncio
async def test_automatic_update_never_synthesises_app_permission(monkeypatch):
    r,h,c,w=configured(monkeypatch)
    h.states.set('sensor.dw_remote','Enabled')
    b,d=desired(r,name='Kitchen')
    await r.live_options.submit(b,d)
    assert not r.dishwasher_app.data['a'].get('request')


@pytest.mark.asyncio
async def test_running_dishwasher_keeps_listener_and_catches_short_end(monkeypatch):
    r,h,c,w=configured(monkeypatch);ready(r,h,c,w)
    event(r,h,c,w,'dishwasher_state_entity','Running');await r.tick()
    app=r.dishwasher_app;st=r.states['a'];b,d=desired(r,dishwasher_state_entity='sensor.new_phase')
    await r.live_options.submit(b,d)
    assert r.dishwasher_app is app and r.states['a'] is st
    event(r,h,c,w,'dishwasher_state_entity','End Of Cycle')
    w[0]+=4;event(r,h,c,w,'dishwasher_state_entity','Off')
    assert app.data['a']['cycle']['status']=='completed'
    assert app.data['a'].get('end_pending')
    # Before observation consumes the event, source change cannot apply.
    await r.live_options.process_pending()
    assert r.configs['a']['dishwasher_state_entity']=='sensor.dw_phase'
    h.states.set('sensor.grid',500,{'unit_of_measurement':'W'})
    await r.tick()
    assert r.configs['a']['dishwasher_state_entity']=='sensor.new_phase'
    assert r.device_modes['a']=='disabled'
    assert r.live_options.archives['a']['dishwasher']['cycle']['status']=='completed'
    assert not [call for call in h.services.calls if call[0] in ('button','switch','script')]


@pytest.mark.asyncio
async def test_replace_inactive_new_identity_and_old_history(monkeypatch):
    r,h,c,w=configured(monkeypatch);r.learning.profiles['a']={'watts':[300,350]}
    r.cycle_learning.profiles['a']={'Eco':[{'energy_kwh':1}]}
    r.dishwasher.profiles['a']={'Eco':{'stages':{}}}
    r.device_modes['a']='auto';r.priorities['a']=5
    b=deepcopy(r.entry.options);new=replacement_profile(b['devices'][0]);new.update(name='New dishwasher',start_button='button.new_start')
    d={**b,'devices':[new]}
    await r.live_options.submit(b,d)
    assert 'a' not in r.configs and new['id'] in r.configs
    assert r.device_modes[new['id']]=='disabled' and new['id'] not in r.learning.profiles
    assert new['id'] not in r.cycle_learning.profiles
    assert not r.dishwasher_app.data.get(new['id'],{}).get('request')
    assert r.live_options.archives['a']['power_profile']['watts']==[300,350]
    assert 'a' in r.consumer_history.configs
    assert r.entry.options[ARCHIVED][0]['replaced_by']==new['id']
    assert not h.services.calls


@pytest.mark.asyncio
async def test_replace_running_is_atomic_and_deferred(monkeypatch):
    r,h,c,w=configured(monkeypatch);event(r,h,c,w,'dishwasher_state_entity','Running');await r.tick()
    b=deepcopy(r.entry.options);new=replacement_profile(b['devices'][0]);d={**b,'devices':[new]}
    await r.live_options.submit(b,d)
    assert set(r.configs)=={'a'} and keyed(r.entry.options['devices']).keys()=={'a'}
    assert 'device:a' in r.entry.options[PENDING]
    assert new['id'] not in r.states


@pytest.mark.parametrize('field',['power_entity','control_entity'])
@pytest.mark.asyncio
async def test_binding_edit_resets_meter_learning_and_permissions(field):
    r,h=build();r.device_modes['a']='auto';r.learning.profiles['a']={'watts':[900]}
    b,d=desired(r,**{field:'sensor.new'})
    await r.live_options.submit(b,d)
    assert 'a' not in r.learning.profiles and r.device_modes['a']=='disabled'
    assert r.live_options.archives['a']['power_profile']['watts']==[900]


@pytest.mark.parametrize('group,change',[
    ('economy',{'import_price':.4}),('planner',{'horizon_hours':48}),
    ('analysis',{'sample_interval_s':600}),('local_pv',{'enabled':False}),
    ('battery_analysis',{'round_trip_efficiency':.8})])
@pytest.mark.asyncio
async def test_live_global_group_keeps_runtime_and_models(group,change):
    r,h=build();r.mode='solar';r.states['a'].owned=True;r.pending={'id':'a'}
    baseline=r.entry.options.copy();proposal=deepcopy(baseline);proposal[group]=change
    models=(r.local_pv,r.battery_analysis,r.unified_planner,r.learning)
    await r.live_options.submit(baseline,proposal)
    assert not r.entry.options[PENDING]
    assert models==(r.local_pv,r.battery_analysis,r.unified_planner,r.learning)
    assert r.states['a'].owned and r.mode=='solar' and r.pending=={'id':'a'}
    assert not h.services.calls


@pytest.mark.asyncio
async def test_global_net_binding_waits_for_command_and_keeps_modes():
    r,h=build();r.mode='solar';r.pending={'id':'a'}
    b=deepcopy(r.entry.options);d={**b,'settings':{'grid_entity':'sensor.grid_new'}}
    await r.live_options.submit(b,d)
    assert 'group:settings' in r.entry.options[PENDING] and r.settings['grid_entity']=='sensor.grid'
    r.pending=None;await r.live_options.process_pending()
    assert r.settings['grid_entity']=='sensor.grid_new' and r.mode=='solar'
    assert not h.services.calls


@pytest.mark.asyncio
async def test_battery_scenarios_update_without_losing_unchanged_samples():
    r,h=build();r.battery_analysis.step(60,-1000)
    previous=r.battery_analysis.snapshot();b=deepcopy(r.entry.options)
    d={**b,'battery_analysis':{'capacities_kwh':[10], 'powers_kw':[5]}}
    await r.live_options.submit(b,d)
    assert r.battery_analysis.live_seconds==previous['live_seconds']


@pytest.mark.asyncio
async def test_add_device_does_not_touch_other_controller_and_defaults_excluded():
    r,h=build();r.states['a'].on=r.states['a'].owned=True;st=r.states['a'];r.mode='solar'
    b=deepcopy(r.entry.options);d=deepcopy(b)
    d['devices'].append({'id':'new','name':'New','kind':'switch','control_entity':'switch.new'})
    await r.live_options.submit(b,d)
    assert r.states['a'] is st and st.on and st.owned
    assert r.device_modes['new']=='disabled' and not r.states['new'].on
    assert r.mode=='solar' and not h.services.calls


@pytest.mark.asyncio
async def test_dynamic_platform_refresh_preserves_objects_for_existing_entities():
    r,h=build();counts=[]
    class E:
        def __init__(self,i,name):
            self._attr_unique_id=i;self._attr_name=name;self._attr_device_info={'name':name}
    def factory():return [E(i,c['name']) for i,c in r.configs.items()]
    r.platforms.register('sensor',lambda rows:counts.append(rows),factory)
    existing=r.platforms.entities['sensor']['a']
    b,d=desired(r,name='Renamed');await r.live_options.submit(b,d)
    assert r.platforms.entities['sensor']['a'] is existing and existing._attr_name=='Renamed'
    assert len(counts)==1
    b=deepcopy(r.entry.options);d=deepcopy(b);d['devices'].append({'id':'b','name':'Second','kind':'switch','control_entity':'switch.other'})
    await r.live_options.submit(b,d)
    assert len(counts)==2 and [e._attr_unique_id for e in counts[-1]]==['b']
    b=deepcopy(r.entry.options);d=deepcopy(b);d['devices']=[d['devices'][1]]
    await r.live_options.submit(b,d)
    assert set(r.platforms.entities['sensor'])=={'b'}
    assert 'a' in r.consumer_history.configs


@pytest.mark.asyncio
async def test_options_listener_uses_accept_not_reload():
    path=Path(__file__).parents[1]/'custom_components/solar_pilot/__init__.py'
    tree=ast.parse(path.read_text());fn=next(x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='_options_updated')
    calls=[x.func.attr for x in ast.walk(fn) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)]
    assert 'accept' in calls and 'async_reload' not in calls


def test_options_init_no_global_busy_gate():
    path=Path(__file__).parents[1]/'custom_components/solar_pilot/config_flow.py'
    tree=ast.parse(path.read_text());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='SolarPilotOptions')
    fn=next(x for x in cls.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='async_step_init')
    assert not any(isinstance(x,ast.Attribute) and x.attr=='_busy' for x in ast.walk(fn))


@pytest.mark.parametrize('setting,value',[('name','New'),('kind','dishwasher'),('appliance_type','tumble_dryer')])
def test_replacement_profile_preserves_only_preferences(setting,value):
    old={'id':'old','name':'Old','kind':'switch','power_entity':'sensor.p',
         'control_entity':'switch.s','nominal_w':1500,'dishwasher_mapping_confirmed':True,
         'priority':4,'dishwasher_start_deadline':'13:00:00',setting:value}
    new=replacement_profile(old)
    assert new['id']!='old' and new['priority']==4 and new[setting]==value
    assert not new.get('control_entity') and not new.get('power_entity')
    assert not new.get('dishwasher_mapping_confirmed')


@pytest.mark.asyncio
async def test_overview_includes_active_waiting_and_archived():
    r,h=build();r.states['a'].on=True
    b,d=desired(r,control_entity='switch.new');await r.live_options.submit(b,d)
    data=r.live_options.overview()
    assert data['editable_while_active'] and data['pending'] and data['devices'][0]['on']
    assert data['devices'][0]['pending']


@pytest.mark.parametrize('group,key',[('settings','grid_entity'),('settings','pv_entity'),('wallbox','power_entity'),('dhw','power_entity')])
@pytest.mark.asyncio
async def test_concurrent_scope_change_cannot_share_exclusive_meter(group,key):
    r,h=build(power=True);b=deepcopy(r.entry.options);d=deepcopy(b);d[group]={key:'sensor.load'}
    with pytest.raises(HomeAssistantError):await r.live_options.submit(b,d)
    assert r.entry.options==b


@pytest.mark.asyncio
async def test_queued_failure_does_not_pause_unrelated_dispatch():
    r,h=build();r.mode='solar'
    async def fail():raise RuntimeError('pending config error')
    r.live_options.process_pending=fail
    await r.tick()
    assert r.mode=='solar' and 'RuntimeError' in r.live_options.error


@pytest.mark.asyncio
async def test_new_priority_profile_rebuilds_global_wallbox_guard():
    from custom_components.solar_pilot.house_first import HouseFirstGuard
    r,h=build();r.others_first=False;r.wallbox_guard=r._make_wallbox_guard()
    b,d=desired(r,wallbox_precedence='consumer_first')
    await r.live_options.submit(b,d)
    assert isinstance(r.wallbox_guard,HouseFirstGuard)


@pytest.mark.asyncio
async def test_pv_source_edit_invalidates_discovery_without_erasing_model():
    r,h=build();r.pv_forecast.source.last_scan=20;r.pv_forecast.source.last_refresh=20
    r.pv_forecast.model.bins={'example':{'factor':.8}}
    model=r.pv_forecast.model;b=deepcopy(r.entry.options)
    await r.live_options.submit(b,{**b,'pv_forecast':{'power_now_entity':'sensor.pvforecast'}})
    assert r.pv_forecast.source.last_scan is None and r.pv_forecast.source.last_refresh is None
    assert r.pv_forecast.model is model and model.bins


@pytest.mark.asyncio
async def test_virtual_entity_retirement_never_removes_source_registry(monkeypatch):
    from homeassistant.helpers import entity_registry as er
    r,h=build();removed=[];entity_removed=[]
    class E:
        def __init__(self):
            self._attr_unique_id='test_a_status';self._attr_device_info={};self._attr_name='status'
            self.entity_id='sensor.solarpilot_a_status';self.hass=h;self.key='a'
        async def async_remove(self):entity_removed.append(self.entity_id)
    monkeypatch.setattr(er,'async_get',lambda hass:SimpleNamespace(async_get=lambda eid:True,async_remove=removed.append))
    r.platforms.register('sensor',lambda rows:None,lambda:[E()] if 'a' in r.configs else [])
    b=deepcopy(r.entry.options);await r.live_options.submit(b,{**b,'devices':[]})
    assert removed==['sensor.solarpilot_a_status'] and entity_removed==removed
    assert 'switch.load' not in removed


@pytest.mark.asyncio
async def test_archive_in_export_redacted_by_default():
    import json
    r,h=build();r.consumer_history.loaded=True
    b,d=desired(r,name='PrivateOldAppliance');await r.live_options.submit(b,d)
    b=deepcopy(r.entry.options);await r.live_options.submit(b,{**b,'devices':[]})
    report=r.analysis.build(hours=1,include_names=False)
    text=json.dumps(report)
    assert 'PrivateOldAppliance' not in text
    assert report['components']['device_management']['archives']


@pytest.mark.asyncio
async def test_dishwasher_transfer_watch_blocks_retirement(monkeypatch):
    r,h,c,w=configured(monkeypatch)
    r.dishwasher_priority.watches['a']={'started_at':w[0]}
    b=deepcopy(r.entry.options);d={**b,'devices':[]}
    out,effects=r.live_options.prepare(b,d)
    assert 'device:a' in out[PENDING]
    assert 'Wallbox' in out[PENDING]['device:a']['reason']
