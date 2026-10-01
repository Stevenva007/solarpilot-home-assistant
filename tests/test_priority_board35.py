"""Explicit priority migration and transactions, with HA doubles (no physical loads)."""
from copy import deepcopy
from types import SimpleNamespace as NS
import json
import time
import pytest
from homeassistant.exceptions import HomeAssistantError
from test_runtime import build
from test_pv_api_config33 import function, Connection
from custom_components.solar_pilot.const import DOMAIN
from custom_components.solar_pilot.runtime import SolarRuntime
from custom_components.solar_pilot.engine import Device, State, Site, plan
from custom_components.solar_pilot.dhw import DHWReading, DHWDecision
from custom_components.solar_pilot.priority_board import WALLBOX, EXTRA, device_key
from custom_components.solar_pilot.wallbox_policy import reclaim_permission
from custom_components.solar_pilot.wallbox import Reading


def multiple():
    r,h=build(power=True,device={'wallbox_precedence':'wallbox_first','priority':60,'nominal_w':350})
    second={**r.entry.options['devices'][0],'id':'second_consumer','name':'Tweede verbruiker','control_entity':'switch.second','power_entity':'sensor.second','priority':20}
    h.states.set('switch.second','off');h.states.set('sensor.second',0,{'unit_of_measurement':'W'})
    r.entry.options['devices'].append(second)
    return SolarRuntime(h,r.entry),h


def activate(r,order=None,power=None):
    b=r.priority_board
    r.entry.options['priority_board']={'schema':1,'order':order or b.order(),'wallbox_power':power or b.permissions()}


@pytest.mark.parametrize('others_first',[True,False])
def test_opening_legacy_order_is_read_only(others_first):
    r,h=multiple();r.others_first=others_first
    before=deepcopy(r.entry.options);modes=deepcopy(r.device_modes)
    d=[x.priority for x in r.devices()]
    for _ in range(10):
        view=r.priority_board.overview()
        assert not view['active']
        assert {x['id'] for x in view['rows']}=={'device:a','device:second_consumer',WALLBOX,EXTRA}
    assert r.entry.options==before and r.device_modes==modes and not h.services.calls
    assert [x.priority for x in r.devices()]==d
    assert all(not row['active'] for row in view['rows'] if row.get('device_id'))


@pytest.mark.asyncio
async def test_beta36_migration_activates_exact_existing_order_without_commands():
    r,h=multiple();r.others_first=True
    before_devices=deepcopy(r.entry.options['devices'])
    expected=r.priority_board.legacy_order()
    changed=await r.priority_board.migrate_beta36()
    assert changed
    assert r.priority_board.active
    assert r.priority_board.saved['schema']==2
    assert r.priority_board.order()==expected
    assert r.entry.options['devices']==before_devices
    assert not h.services.calls


def test_existing_preferred_dishwasher_precedes_wallbox_and_extra():
    r,h=multiple();r.configs['second_consumer'].update(kind='dishwasher',dishwasher_priority_enabled=True,wallbox_precedence='wallbox_first')
    order=r.priority_board.order()
    assert order.index('device:second_consumer')<order.index(WALLBOX)<order.index(EXTRA)


@pytest.mark.asyncio
async def test_noop_does_not_activate_or_write():
    r,h=multiple();b=r.priority_board;before=deepcopy(r.entry.options)
    await b.save(b.revision(),b.order(),b.permissions(),True)
    assert r.entry.options==before and not b.active and not h.services.calls


@pytest.mark.asyncio
async def test_explicit_save_persists_only_priority_and_preserves_running_state():
    r,h=multiple();r.mode='solar';r.device_modes['a']='auto';s=r.states['a'];s.on=s.owned=True;s.last_on=123;s.boost_until=1000
    old=deepcopy(r.entry.options);modes=deepcopy(r.device_modes);lock=r._lock;store=r.store
    b=r.priority_board;order=['device:a',WALLBOX,'device:second_consumer',EXTRA]
    answer=await b.save(b.revision(),order,b.permissions(),True)
    assert answer['active'] and b.order()==order
    assert r.entry.options['devices']==old['devices'] and r.states['a'] is s
    assert s.on and s.owned and s.last_on==123 and s.boost_until==1000
    assert r.mode=='solar' and r.device_modes==modes and r._lock is lock and r.store is store
    assert not h.services.calls
    fresh=SolarRuntime(h,r.entry)
    assert fresh.priority_board.order()==order and fresh.priority_board.active
    assert [d.priority for d in fresh.devices()]==[1,3]


@pytest.mark.asyncio
@pytest.mark.parametrize('pending',['pending','handover'])
async def test_save_waits_for_committed_command(pending):
    r,h=multiple();setattr(r,pending,NS(device_id='a'))
    b=r.priority_board;order=['device:a',WALLBOX,'device:second_consumer',EXTRA]
    with pytest.raises(HomeAssistantError,match='gewacht'):await b.save(b.revision(),order,b.permissions(),True)
    assert not b.active and not h.services.calls


@pytest.mark.parametrize('bad',[None,False,1,'true',[],{}])
def test_explicit_boolean_confirmation_required(bad):
    r,_=multiple();b=r.priority_board
    with pytest.raises(HomeAssistantError):b.validate(b.revision(),b.order(),b.permissions(),bad)


@pytest.mark.parametrize('order',[None,{},[],[WALLBOX,EXTRA],['device:a',WALLBOX,EXTRA,'device:a'],['device:a','device:unknown',WALLBOX,EXTRA],[WALLBOX,EXTRA,1,2]])
def test_reject_partial_duplicate_unknown_or_wrong_order_types(order):
    r,_=multiple();b=r.priority_board
    with pytest.raises(HomeAssistantError):b.validate(b.revision(),order,b.permissions(),True)


@pytest.mark.parametrize('value',[1,0,'false','true',None,{},[]])
def test_permission_must_be_boolean(value):
    r,_=multiple();b=r.priority_board;permissions=b.permissions();permissions['device:a']=value
    with pytest.raises(HomeAssistantError):b.validate(b.revision(),b.order(),permissions,True)


@pytest.mark.parametrize('permissions',[{},None,{'device:a':True},{'device:a':True,'device:second_consumer':True,'unknown':False}])
def test_permission_set_must_be_exact(permissions):
    r,_=multiple();b=r.priority_board
    with pytest.raises(HomeAssistantError):b.validate(b.revision(),b.order(),permissions,True)


def test_revision_ignores_telemetry_but_detects_settings_devices_and_legacy_controls():
    r,h=multiple();b=r.priority_board;rev=b.revision();r.grid_w=-500;r.states['a'].daily_runtime_s=800
    assert b.revision()==rev
    for mutate in [lambda:r.priorities.update(a=1),lambda:r.configs['a'].update(name='Nieuw label'),lambda:r.entry.options.update(_live_pending={'group:dhw':{'new':{}}})]:
        old=b.revision();mutate()
        with pytest.raises(HomeAssistantError,match='intussen'):b.validate(old,b.order(),b.permissions(),True)


def test_extra_cannot_overtake_wallbox_or_preferred_dishwasher():
    r,h=multiple();b=r.priority_board
    with pytest.raises(HomeAssistantError,match='Wallbox'):b.validate(b.revision(),[EXTRA,WALLBOX,'device:a','device:second_consumer'],b.permissions(),True)
    r.configs['a'].update(kind='dishwasher',dishwasher_priority_enabled=True)
    with pytest.raises(HomeAssistantError,match='voorrang'):b.validate(b.revision(),[WALLBOX,EXTRA,'device:a','device:second_consumer'],b.permissions(),True)


def test_new_id_not_granted_previous_mode_and_retired_id_not_displayed():
    r,h=multiple();b=r.priority_board;activate(r)
    old=r.configs.pop('a');r.configs['replacement']={**old,'id':'replacement','name':'Vervanger'}
    assert 'device:a' not in b.order()
    assert b.order().index(EXTRA) < b.order().index('device:replacement')
    assert b.order()[-1] == 'device:replacement'
    assert r.device_modes.get('replacement','disabled')=='disabled'
    assert 'device:replacement' in b.permissions()
    r.configs['new_aeg']={**old,'id':'new_aeg','name':'Nieuwe afwas','kind':'dishwasher','dishwasher_priority_enabled':True}
    assert b.order().index('device:new_aeg')<b.order().index(WALLBOX)


@pytest.mark.parametrize('before',[True,False])
@pytest.mark.parametrize('permission',[True,False])
@pytest.mark.parametrize('meter',[True,False])
def test_right_requires_position_permission_and_meter(before,permission,meter):
    r,h=multiple();order=['device:a',WALLBOX,'device:second_consumer',EXTRA] if before else [WALLBOX,'device:a','device:second_consumer',EXTRA]
    activate(r,order,{'device:a':permission,'device:second_consumer':True})
    c=r.priority_board.effective_config('a')
    allowed,_,_=reclaim_permission(c,before_wallbox=before,dedicated_meter=meter)
    assert allowed==(before and permission and meter)
    assert c['_priority_board_before_wallbox']==before
    assert r.configs['a']['priority']==60


def test_legacy_opt_in_toggles_without_relaxing_legacy_runtime_rule():
    r,h=multiple();r.configs['a'].update(wallbox_power_policy='legacy',allow_wallbox_reclaim=False)
    activate(r,['device:a',WALLBOX,'device:second_consumer',EXTRA],{'device:a':True,'device:second_consumer':True})
    c=r.priority_board.effective_config('a');allowed,long,_=reclaim_permission(c,before_wallbox=True,dedicated_meter=True)
    assert allowed and long and c['wallbox_power_policy']=='legacy'


def test_lower_rank_never_reclaims_wallbox_even_if_permission_saved():
    r,h=multiple()
    activate(r,[WALLBOX,'device:a','device:second_consumer',EXTRA],
             {'device:a':True,'device:second_consumer':False})
    r.wallbox_settings['enabled']=True
    r.consumer_wallbox.settings['enabled']=True
    r.filtered=-100
    reading=Reading(power_w=2000,stamp=time.time(),demand=True,status='Charging',
                    mode='full_solar',valid=True,age_s=0,connected=True,
                    raw_mode='full_solar',session_reason='ok',session_confirmed=True,
                    session_value='Zonne-auto · laden')
    _,_,no_reclaim=r._wallbox_device_constraints(time.monotonic(),reading,-100,True,0)
    assert 'a' in no_reclaim
    assert 'second_consumer' in no_reclaim


def test_board_rank_matches_planner_and_engine_configs():
    r,h=multiple();activate(r,['device:a',WALLBOX,'device:second_consumer',EXTRA])
    planned={d['id']:d['priority'] for d in r._planner_device_configs_for_overview()}
    assert planned=={d.id:d.priority for d in r.devices()}=={'a':1,'second_consumer':3}


@pytest.mark.asyncio
async def test_old_controls_cannot_override_active_board():
    r,h=multiple();activate(r)
    with pytest.raises(HomeAssistantError):await r.set_priority('a',1)
    with pytest.raises(HomeAssistantError):await r.set_others_first(True)
    assert not h.services.calls


def heat_context():
    r,h=multiple();activate(r,[WALLBOX,'device:a',EXTRA,'device:second_consumer'])
    r.mode='solar';r.dhw.settings.update(enabled=True,safety_confirmed=True,target_entity='water_heater.tank',temperature_entity='sensor.temp')
    r.dhw.config.update(r.dhw.settings);r.dhw.auto_enabled=True;r.dhw.needs_review=False;r.dhw.manual_hold=False;r.dhw.fault=''
    r.dhw.reading=DHWReading(temperature_c=50,actual_target_c=50,cooling=False,pv_w=8000,export_w=4500,grid_w=-4500)
    r.dhw.policy.result=DHWDecision(target_c=60,stage='surplus')
    h.states.set('water_heater.tank','heat',{'hvac_action':'idle'})
    r.grid_w=r.filtered=-4500
    return r,h


def test_optional_heat_waits_for_fitting_higher_consumer_only():
    r,h=heat_context();s=r.states['a'];s.enabled=s.available=s.demand=s.interlock=s.cycle_armed=True
    now=time.monotonic();reading=deepcopy(r.dhw.reading)
    r.priority_board.guard_extra(reading,now)
    assert not reading.luxury_allowed and r.configs['a']['name'] in reading.luxury_reason
    s.on=True;reading=deepcopy(r.dhw.reading);r.priority_board.guard_extra(reading,now)
    assert reading.luxury_allowed
    s.on=False;r.grid_w=r.filtered=-50;reading=deepcopy(r.dhw.reading);r.priority_board.guard_extra(reading,now)
    assert reading.luxury_allowed


@pytest.mark.parametrize('condition',['disabled','unknown','no_demand','interlock','not_armed','fault','manual','rest','planner'])
def test_nonclaiming_higher_consumer_does_not_block_optional_heat(condition):
    r,h=heat_context();s=r.states['a'];s.enabled=s.available=s.demand=s.interlock=s.cycle_armed=True;now=time.monotonic()
    if condition=='disabled':s.enabled=False
    elif condition=='unknown':s.available=False
    elif condition=='no_demand':s.demand=False
    elif condition=='interlock':s.interlock=False
    elif condition=='not_armed':s.cycle_armed=False
    elif condition=='fault':s.fault='stale'
    elif condition=='manual':s.manual_until=now+100
    elif condition=='rest':s.last_off=now;r.configs['a']['min_off_s']=100
    else:s.planner_hold=True
    reading=deepcopy(r.dhw.reading);r.priority_board.guard_extra(reading,now)
    assert reading.luxury_allowed


def test_extra_heat_blocks_only_new_lower_starts_not_running_higher_or_urgent():
    r,h=heat_context();now=time.monotonic();b=r.priority_board
    assert set(b.extra_start_blocks(now))=={'second_consumer'}
    for attr,value in [('on',True),('manual_forced',True),('boost_until',now+100),('deadline_force',True),('planner_grid_force',True)]:
        setattr(r.states['second_consumer'],attr,value)
        assert b.extra_start_blocks(now)=={}
        setattr(r.states['second_consumer'],attr,False)


@pytest.mark.parametrize('temp,heating,blocks',[(50,False,True),(57,False,False),(57,True,True),(60,True,False),(None,False,False)])
def test_extra_does_not_reserve_forever_above_native_restart_threshold(temp,heating,blocks):
    r,h=heat_context();r.dhw.reading.temperature_c=temp
    h.states.set('water_heater.tank','heat',{'hvac_action':'heating' if heating else 'idle'})
    assert bool(r.priority_board.extra_start_blocks(time.monotonic()))==blocks


@pytest.mark.parametrize('stage',['base','space_priority','protected','night','disabled','unavailable','solar'])
def test_only_real_surplus_policy_can_block_lower_loads(stage):
    r,h=heat_context();r.dhw.policy.result.stage=stage
    assert not r.priority_board.extra_start_blocks(time.monotonic())


def endpoint():return function('priority_api.py','websocket_priority_board',{'DOMAIN':DOMAIN,'HomeAssistantError':HomeAssistantError})


@pytest.mark.asyncio
@pytest.mark.parametrize('admin',[False,None])
async def test_api_denies_non_admin(admin):
    c=Connection(admin);await endpoint()(None,c,{'id':1,'config_entry_id':'test'})
    assert c.errors[0][1]=='unauthorized' and not c.results


@pytest.mark.asyncio
@pytest.mark.parametrize('entry',[None,NS(domain='other',runtime_data=NS()),NS(domain=DOMAIN,runtime_data=None)])
async def test_api_denies_wrong_unloaded_entry(entry):
    c=Connection(True);h=NS(config_entries=NS(async_get_entry=lambda _:entry))
    await endpoint()(h,c,{'id':1,'config_entry_id':'test'})
    assert c.errors[0][1]=='not_loaded'


@pytest.mark.asyncio
async def test_api_save_and_stale_revision_error_no_device_calls():
    r,h=multiple();r.entry.domain=DOMAIN;r.entry.runtime_data=r;h.config_entries=NS(async_get_entry=lambda _:r.entry)
    c=Connection(True);await endpoint()(h,c,{'id':1,'config_entry_id':'test'})
    before=c.results[0][1];save={'revision':before['revision'],'order':['device:a',WALLBOX,'device:second_consumer',EXTRA],'wallbox_power':before['wallbox_power'],'confirm':True}
    await endpoint()(h,c,{'id':2,'config_entry_id':'test','save':save})
    assert len(c.results)==2 and not c.errors and not h.services.calls
    await endpoint()(h,c,{'id':3,'config_entry_id':'test','save':save})
    assert c.errors[-1][1]=='invalid_options' and not h.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize('save',[None,[],{}, {'revision':'x'}, {'revision':'x','order':[],'wallbox_power':{},'confirm':True,'command':'on'}])
async def test_api_rejects_incomplete_or_extra_fields(save):
    r,h=multiple();r.entry.domain=DOMAIN;r.entry.runtime_data=r;h.config_entries=NS(async_get_entry=lambda _:r.entry)
    c=Connection(True);await endpoint()(h,c,{'id':1,'config_entry_id':'test','save':save})
    assert c.errors[-1][1]=='invalid_options' and not c.results and not h.services.calls


def test_export_includes_board_and_preserves_private_alias_joins():
    r,h=multiple();activate(r)
    report=r.analysis.build(include_names=False);text=json.dumps(report)
    assert 'priority_board' in report['components']
    assert 'second_consumer' not in text and 'Tweede verbruiker' not in text
    board=report['components']['priority_board']
    assert set(board['order'])=={row['id'] for row in board['rows']}
    assert not report['coverage']['section_errors'] and not h.services.calls


def test_central_order_overrides_legacy_dishwasher_group_without_breaking_legacy():
    from test_engine import dev, site
    devices=[dev('higher',priority=1),dev('preferred',priority=3)]
    states={d.id:State() for d in devices}
    legacy=plan(site(-1000,priority_ids={'preferred'}),devices,deepcopy(states))
    central=plan(site(-1000,priority_ids={'preferred'},ordered_priorities=True),devices,deepcopy(states))
    assert legacy.action.id=='preferred' and central.action.id=='higher'


@pytest.mark.parametrize('protected',[False,True])
def test_priority_change_does_not_cut_running_minimum_or_protected_program(protected):
    from test_engine import dev, site, owned
    devices=[dev('higher',priority=1),Device(id='running',name='Running',priority=4,non_interruptible=protected,min_on_s=1200,start_delay_s=0)]
    states={'higher':State(),'running':State(owned=True,on=True,measured_w=1000,target_w=1000,last_on=900)}
    result=plan(site(0,ordered_priorities=True),devices,states)
    assert result.targets['running']>=1000 and result.action is None


@pytest.mark.asyncio
@pytest.mark.parametrize('change',[{'name':'Nieuwe naam'}, {'appliance_type':'washing_machine'}])
async def test_central_board_retains_live_label_and_category_edits(change):
    r,h=multiple();activate(r);before=deepcopy(r.entry.options);after=deepcopy(before)
    after['devices'][0].update(change)
    await r.live_options.submit(before,after)
    assert r.configs['a'].items()>=change.items() and r.priority_board.active and not h.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize('key,value',[('priority',1),('wallbox_precedence','consumer_first'),('wallbox_power_policy','never'),('allow_wallbox_reclaim',True)])
async def test_old_open_native_form_cannot_rewrite_central_choices(key,value):
    r,h=multiple();activate(r);before=deepcopy(r.entry.options);after=deepcopy(before)
    after['devices'][0][key]=value
    with pytest.raises(HomeAssistantError,match='Voorrang'):await r.live_options.submit(before,after)
    assert r.entry.options==before and not h.services.calls


def test_dishwasher_yield_never_releases_higher_ranked_load():
    from test_dishwasher_priority32 import inputs, advance
    from custom_components.solar_pilot.dishwasher_priority import DishwasherPriority
    kw=inputs();kw['configs']['dw']['_priority_board_rank']=3;kw['configs']['low']['_priority_board_rank']=1
    result=advance(DishwasherPriority(),kw)
    assert not result.holds
    kw['configs']['low']['_priority_board_rank']=4
    result=advance(DishwasherPriority(),kw)
    assert 'low' in result.holds
