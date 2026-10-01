"""Adapter/integration tests with explicit Home Assistant doubles."""
import asyncio
from datetime import datetime
from types import SimpleNamespace
import time
import pytest
from custom_components.solar_pilot.dhw import DHW_DEFAULTS
from custom_components.solar_pilot.dhw_runtime import DHWManager
from test_runtime import build, Services
from homeassistant.exceptions import HomeAssistantError


class BoilerServices(Services):
    async def async_call(self,domain,action,data,blocking=False):
        # Model asynchronous device feedback after the command. Without this
        # delay, datetime's microsecond precision can timestamp the fake response
        # just before time.time() on fast Windows runs, for any boiler adapter.
        await asyncio.sleep(0.001)
        if action == 'set_temperature':
            self.calls.append((domain,action,data))
            if self.on_call: self.on_call(domain,action,data)
            if self.fail: raise HomeAssistantError('offline')
            if self.respond:
                obj=self.states.get(data['entity_id'])
                self.states.set(data['entity_id'],obj.state,{**obj.attributes,'temperature':data['temperature']})
        else:
            await super().async_call(domain,action,data,blocking)


def setup(kind='water_heater',config=None):
    r,h=build(settings={'pv_entity':'sensor.pv'})
    h.config=SimpleNamespace(time_zone='Europe/Brussels',units=SimpleNamespace(temperature_unit='°C'))
    h.services=BoilerServices(h.states)
    target=f'{kind}.boiler'
    attrs={'temperature':50,'current_temperature':44,'min_temp':30,'max_temp':65,
           'supported_features':1,'target_temp_step':0.5,'temperature_unit':'°C'}
    h.states.set(target,'heat_pump' if kind=='water_heater' else 'heat',attrs)
    if kind in ('number','input_number'):
        h.states.set(target,50,{'min':30,'max':65,'step':0.5,'unit_of_measurement':'°C'})
    h.states.set('sensor.water',44,{'unit_of_measurement':'°C'})
    h.states.set('sensor.pv',5000,{'unit_of_measurement':'W'})
    h.states.set('climate.home','cool',{'hvac_action':'idle'})
    h.states.set('climate.salon','off',{'hvac_action':'off'})
    h.states.set('binary_sensor.hygiene','off')
    h.states.set('switch.powerful','off')
    h.states.set('sensor.boiler_power',0,{'unit_of_measurement':'W'})
    r.entry.options['dhw']={**DHW_DEFAULTS,'enabled':True,'safety_confirmed':True,
        'target_entity':target,'temperature_entity':'sensor.water',
        'cooling_entities':['climate.home','climate.salon'],
        'hygiene_entity':'binary_sensor.hygiene','manual_entity':'switch.powerful',
        'rise_delay_s':0,'fall_delay_s':0,'cooling_clear_s':0,**(config or {})}
    r.dhw=DHWManager(r)
    r.mode='solar'
    r.pv_w=5000
    return r,h


async def tick(r,grid=-4000,valid=True,discharge=0,hour=12,allow=True):
    return await r.dhw.tick(time.monotonic(),grid,valid,discharge,allow,
                           datetime(2026,9,22,hour))


def updates(h,id,**attrs):
    obj=h.states.get(id)
    h.states.set(id,obj.state,{**obj.attributes,**attrs})


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['water_heater','climate','number','input_number'])
async def test_supported_adapters_only_write_setpoints(kind):
    r,h=setup(kind)
    await tick(r)
    calls=[c for c in h.services.calls if c[0]!='persistent_notification']
    assert len(calls)==1 and calls[0][0]==kind
    assert calls[0][1] == ('set_value' if kind in ('number','input_number') else 'set_temperature')
    assert list(calls[0][2].values())[-1] == 60
    await tick(r)
    assert r.dhw.pending is None and r.dhw.owned_target == 60


@pytest.mark.asyncio
async def test_observation_never_writes_even_at_night_below_minimum():
    r,h=setup();r.mode='observe'
    h.states.set('sensor.water',40,{'unit_of_measurement':'°C'})
    await tick(r,hour=2)
    assert h.services.calls == [] and r.dhw.policy.result.low_temperature


@pytest.mark.asyncio
async def test_original_unconfigured_integration_does_not_command_boiler():
    r,h=build();r.mode='solar'
    await r.tick()
    assert not r.dhw.configured and h.services.calls==[]


@pytest.mark.asyncio
async def test_minimum_regime_at_night_even_without_energy_readings():
    r,h=setup();r.pv_w=None
    updates(h,'water_heater.boiler',temperature=49)
    await tick(r,grid=None,valid=False,hour=2)
    assert h.services.calls[-1][2]['temperature']==50


@pytest.mark.asyncio
async def test_50_production_rule_not_blocked_by_grid_import():
    r,h=setup();r.pv_w=1000
    updates(h,'water_heater.boiler',temperature=49)
    await tick(r,grid=3000)
    assert h.services.calls[-1][2]['temperature']==50


@pytest.mark.asyncio
async def test_either_cooling_zone_caps_60_at_50():
    r,h=setup()
    h.states.set('climate.salon','cool',{'hvac_action':'cooling'})
    updates(h,'water_heater.boiler',temperature=60)
    await tick(r)
    assert h.services.calls[-1][2]['temperature']==50


@pytest.mark.asyncio
async def test_unknown_cooling_caps_60():
    r,h=setup()
    h.states.set('climate.salon','unavailable')
    await tick(r)
    assert r.dhw.policy.result.target_c == 50
    assert not h.services.calls


@pytest.mark.asyncio
async def test_no_cooling_entities_blocks_60():
    r,h=setup(config={'cooling_entities':[]})
    await tick(r)
    assert r.dhw.policy.result.target_c==50


@pytest.mark.asyncio
@pytest.mark.parametrize('guard',['binary_sensor.hygiene','switch.powerful'])
async def test_guard_blocks_all_writes_even_night(guard):
    r,h=setup();h.states.set(guard,'on')
    await tick(r,hour=2)
    assert not h.services.calls and r.dhw.policy.result.target_c is None


@pytest.mark.asyncio
async def test_unknown_hygiene_blocks_all_writes():
    r,h=setup();h.states.set('binary_sensor.hygiene','unknown')
    await tick(r,hour=2)
    assert not h.services.calls


@pytest.mark.asyncio
async def test_hygiene_is_never_lowered_and_auto_resumes_only_after_factory_restores_normal_target():
    r,h=setup();await tick(r);await tick(r)
    assert r.dhw.owned_target == 60
    h.states.set('binary_sensor.hygiene','on')
    updates(h,'water_heater.boiler',temperature=62)
    await tick(r)
    assert r.dhw.owned_target is None and not r.dhw.manual_hold
    count=len(h.services.calls)
    h.states.set('binary_sensor.hygiene','off')
    await tick(r)
    # Still 62 °C: the high manufacturer target itself remains protected.
    assert len(h.services.calls)==count and r.dhw.policy.result.target_c is None
    updates(h,'water_heater.boiler',temperature=50)
    await tick(r)
    assert not r.dhw.manual_hold and r.dhw.policy.result.target_c == 60


@pytest.mark.asyncio
async def test_prior_high_target_never_lowered_without_check():
    r,h=setup();updates(h,'water_heater.boiler',temperature=65)
    await tick(r,hour=2)
    assert r.dhw.policy.result.target_c is None and not h.services.calls


@pytest.mark.asyncio
async def test_safety_confirmation_required():
    r,h=setup(config={'safety_confirmed':False})
    await tick(r)
    assert not h.services.calls


@pytest.mark.asyncio
async def test_controller_does_not_turn_on_off_boiler():
    r,h=setup();h.states.set('water_heater.boiler','off',h.states.get('water_heater.boiler').attributes)
    await tick(r)
    assert not h.services.calls


@pytest.mark.asyncio
async def test_stale_temperature_no_command():
    r,h=setup();h.states.set('sensor.water',44,{'unit_of_measurement':'°C'},age=1000)
    await tick(r)
    assert not h.services.calls


@pytest.mark.asyncio
async def test_stale_cooling_blocks_high_but_not_solar50():
    r,h=setup();h.states.set('climate.home','off',{},age=1000)
    await tick(r)
    assert r.dhw.policy.result.target_c==50


@pytest.mark.asyncio
async def test_intent_journal_written_before_call():
    r,h=setup()
    def verify(*args):
        assert r.store.data['dhw']['pending']['target']==60
    h.services.on_call=verify
    await tick(r)


@pytest.mark.asyncio
async def test_ack_requires_new_report_not_just_optimistic_intent():
    r,h=setup();h.services.respond=False
    await tick(r)
    assert r.dhw.pending
    h.states.set('water_heater.boiler','heat_pump',
                 {**h.states.get('water_heater.boiler').attributes,'temperature':60},age=10)
    await tick(r)
    assert r.dhw.pending
    updates(h,'water_heater.boiler',temperature=60)
    await tick(r)
    assert r.dhw.pending is None


@pytest.mark.asyncio
async def test_ack_timeout_latches_and_does_not_retry():
    r,h=setup();h.services.respond=False
    await tick(r)
    r.dhw.pending['issued']-=1000
    await tick(r)
    assert r.dhw.fault and not r.dhw.pending
    count=len(h.services.calls)
    await tick(r)
    assert len(h.services.calls)==count


@pytest.mark.asyncio
async def test_service_failure_preserves_intent():
    r,h=setup();h.services.fail=True
    # Notification double also raises when fail=True; suppress only notification.
    async def no_notify(message): pass
    r.notify=no_notify
    await tick(r)
    assert r.dhw.fault and r.dhw.owned_target==60
    assert r.store.data['dhw']['owned_target']==60


@pytest.mark.asyncio
async def test_external_setpoint_respected():
    r,h=setup();await tick(r);await tick(r)
    updates(h,'water_heater.boiler',temperature=55)
    await tick(r)
    assert r.dhw.manual_hold and r.dhw.owned_target is None
    assert len(h.services.calls)==1


@pytest.mark.asyncio
async def test_pause_releases_to_base_not_turn_off():
    r,h=setup();await tick(r);await tick(r)
    r.mode='paused'
    await tick(r)
    assert h.services.calls[-1][2]['temperature']==50
    await tick(r)
    assert r.dhw.owned_target is None and not r.dhw.pending


@pytest.mark.asyncio
async def test_disable_preserves_base_not_main_power():
    r,h=setup();await tick(r);await tick(r)
    r.dhw.auto_enabled=False
    await tick(r);await tick(r)
    assert r.dhw.owned_target is None
    assert all(c[1]=='set_temperature' for c in h.services.calls)


@pytest.mark.asyncio
async def test_disallow_observe_until_control_released():
    r,h=setup();await tick(r);await tick(r)
    with pytest.raises(HomeAssistantError): await r.set_mode('observe')


@pytest.mark.asyncio
async def test_runtime_serializes_boiler_and_other_load_commands():
    r,h=setup(config={'night_enabled':False,'hygiene_schedule_enabled':False})
    h.states.set('sensor.grid',-5000,{'unit_of_measurement':'W'})
    r.device_modes['a']='auto'
    await r.tick()
    calls=[c for c in h.services.calls if c[0]!='persistent_notification']
    assert len(calls)==1 and calls[0][0]=='water_heater'


@pytest.mark.asyncio
async def test_pending_other_command_delays_boiler_write():
    r,h=setup()
    await tick(r,allow=False)
    assert not h.services.calls and r.dhw.policy.result.target_c==60


@pytest.mark.asyncio
async def test_restart_requires_review_no_replay():
    r,h=setup();await tick(r)
    data=r.dhw.snapshot()
    other=DHWManager(r);other.restore(data);r.dhw=other;r.mode='observe'
    await tick(r)
    assert other.needs_review and len(h.services.calls)==1
    with pytest.raises(HomeAssistantError): await r.set_mode('solar')


@pytest.mark.asyncio
async def test_review_only_while_not_solar():
    r,h=setup()
    with pytest.raises(HomeAssistantError): await r.dhw.review()


@pytest.mark.asyncio
async def test_review_does_not_command():
    r,h=setup(config={'hygiene_schedule_enabled':False});r.mode='paused';r.dhw.manual_hold=True
    await r.dhw.review()
    assert not r.dhw.manual_hold and not h.services.calls


@pytest.mark.asyncio
async def test_manual_takeover_allows_disconnected_removal_without_calls():
    r,h=setup();r.mode='paused';r.dhw.owned_target=60
    h.states.set('water_heater.boiler','unavailable')
    await r.dhw.takeover()
    assert not r.dhw.busy and not r.dhw.auto_enabled and not h.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize('attrs',[{'max_temp':55},{'temperature_unit':'°F'},{'supported_features':0},{'target_temp_step':4}])
async def test_incompatible_target_not_written(attrs):
    r,h=setup();updates(h,'water_heater.boiler',**attrs)
    await tick(r)
    assert not h.services.calls


@pytest.mark.asyncio
async def test_wallbox_power_not_added_to_export():
    r,h=setup();r.wallbox_settings.update({'enabled':True,'power_entity':'sensor.ev'})
    h.states.set('sensor.ev',5000,{'unit_of_measurement':'W'})
    await tick(r,grid=0)
    assert r.dhw.reading.export_w==0 and r.dhw.policy.result.target_c==50


@pytest.mark.asyncio
async def test_battery_export_not_solar_surplus():
    r,h=setup()
    await tick(r,grid=-4000,discharge=2500)
    assert r.dhw.reading.export_w==1500 and r.dhw.policy.result.target_c==50


@pytest.mark.asyncio
async def test_own_meter_compensates_only_owned_high():
    r,h=setup(config={'power_entity':'sensor.boiler_power'})
    await tick(r);await tick(r)
    h.states.set('sensor.boiler_power',3500,{'unit_of_measurement':'W'})
    await tick(r,grid=-500)
    assert r.dhw.policy.result.target_c==60 and r.dhw.reading.before_boiler_w==4000


@pytest.mark.asyncio
async def test_own_meter_must_not_be_grid_or_other_load():
    r,h=setup(config={'power_entity':'sensor.grid'})
    assert not r.dhw.exclusive_meter()
    r.dhw.config['power_entity']='sensor.load'
    r.configs['a']['power_entity']='sensor.load'
    assert not r.dhw.exclusive_meter()


@pytest.mark.asyncio
async def test_other_device_cannot_reuse_boiler_meter():
    r,h=setup(config={'power_entity':'sensor.boiler_power'})
    r.configs['a']['power_entity']='sensor.boiler_power'
    assert not r._dedicated_meter('a')


@pytest.mark.asyncio
async def test_duplicate_control_rejected_runtime():
    r,h=setup();r.configs['a']['number_entity']='water_heater.boiler'
    await tick(r)
    assert not h.services.calls


@pytest.mark.asyncio
async def test_tunable_validation_and_persistence():
    r,h=setup();r.mode='observe'
    await r.dhw.set_number('pv_threshold_w',1500)
    assert r.dhw.settings['pv_threshold_w']==1500
    other=DHWManager(r);other.restore(r.dhw.snapshot())
    assert other.settings['pv_threshold_w']==1500
    with pytest.raises(HomeAssistantError): await r.dhw.set_number('minimum_c',55)


@pytest.mark.asyncio
async def test_changed_config_revision_drops_old_tunables():
    r,h=setup();r.mode='observe'
    await r.dhw.set_number('pv_threshold_w',1500)
    old=r.dhw.snapshot()
    r.entry.options['dhw']['config_revision']='new'
    other=DHWManager(r);other.restore(old)
    assert other.settings['pv_threshold_w']==1000


@pytest.mark.asyncio
async def test_learning_cannot_mutate_temperature_rules():
    r,h=setup();before=dict(r.dhw.settings)
    r.learning.successes=100
    r.learning.enabled=False
    await tick(r)
    assert r.dhw.settings == before


@pytest.mark.asyncio
async def test_old_unchanged_target_valid_with_fresh_actual_temperature():
    from datetime import timedelta
    r,h=setup(kind="number")
    obj=h.states.get("number.boiler")
    obj.last_updated = obj.last_reported = datetime.now().astimezone()-timedelta(days=2)
    assert r.dhw._temperature() == 44
    assert r.dhw._target()[0] == 50
    assert await tick(r) is True
    assert h.services.calls[-1][2]["value"] == 60


@pytest.mark.asyncio
async def test_multiple_panasonic_manual_signals_are_respected():
    r,h=setup(config={'manual_entity':'','manual_entities':['select.powerful','switch.force_dhw']})
    h.states.set('select.powerful','off')
    h.states.set('switch.force_dhw','on')
    await tick(r)
    assert not h.services.calls and r.dhw.policy.result.target_c is None
    h.states.set('switch.force_dhw','off')
    h.states.set('select.powerful','on-60m')
    await tick(r)
    assert not h.services.calls and r.dhw.policy.result.target_c is None


@pytest.mark.parametrize("features", [None,"invalid",float("nan")])
def test_invalid_features_do_not_raise_or_send(features):
    r,h=setup()
    updates(h,"water_heater.boiler",supported_features=features)
    assert r.dhw.check_target(60)
    assert not h.services.calls


@pytest.mark.asyncio
async def test_beta36_migration_persists_runtime_50_46_as_single_dhw_truth():
    r,h=setup(config={"enabled":False,"safety_confirmed":False,"normal_c":49.0,"minimum_c":43.0})
    stored={
        "config_revision":r.dhw.config["config_revision"],
        "target_entity":r.dhw.config["target_entity"],
        "enabled":True,
        "tunables":{"normal_c":50.0,"minimum_c":46.0},
        "pending":None,"owned_target":None,"needs_review":False,
        "manual_hold":False,"fault":"",
    }
    r.dhw.restore(stored)
    changed=await r.dhw.migrate_beta36(stored)
    assert changed
    saved=r.entry.options["dhw"]
    assert saved["enabled"] is True
    assert saved["safety_confirmed"] is True
    assert saved["normal_c"]==50.0 and saved["minimum_c"]==46.0
    assert saved["tank_differential_c"]==-5.0
    assert saved["solar_c"]==50.0 and saved["surplus_c"]==60.0
    assert saved["cooling_cap_c"]==50.0 and saved["hygiene_target_c"]==62.0
    assert r.dhw.settings==r.dhw.config
    view=r.dhw.overview()
    assert view["configuration_source"]=="config_entry.options.dhw"
    assert view["enabled"] and view["safety_confirmed"]
