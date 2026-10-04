"""Native battery reports, durable intent and fail-closed release regressions."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import time

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from custom_components.solar_pilot.battery_fleet import BatteryFleetState
from test_battery_runtime import setup_battery


@pytest.fixture
def battery(monkeypatch):
    wall = [float(int(time.time()))]
    monkeypatch.setattr(time, 'time', lambda: wall[0])
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    def set_state(entity, value, attrs=None, age=0, reported_age=None):
        previous = hass.states.get(entity)
        attrs = previous.attributes if attrs is None and previous else attrs or {}
        stamp = datetime.fromtimestamp(wall[0] - age, timezone.utc)
        report = datetime.fromtimestamp(wall[0] - (age if reported_age is None else reported_age), timezone.utc)
        hass.states.data[entity] = SimpleNamespace(state=str(value), attributes=dict(attrs),
                                                 last_updated=stamp, last_reported=report)
    monkeypatch.setattr(hass.states, 'set', set_state)
    for entity, state in list(hass.states.data.items()):
        set_state(entity, state.state, state.attributes)
    return runtime, hass, wall


async def command(battery, target=-1800):
    runtime, hass, wall = battery
    assert await runtime.battery_fleet._send('bat1', target)
    return runtime.battery_fleet


async def ack(battery, target=-1800):
    runtime, hass, wall = battery
    wall[0] += 1
    hass.states.set('sensor.bat_power', target, {'unit_of_measurement':'W'})
    await runtime.battery_fleet.tick(grid_w=0, allow_command=False)
    assert not runtime.battery_fleet.busy


@pytest.mark.asyncio
@pytest.mark.parametrize('report', ['cached', 'same_stamp', 'restored', 'future', 'stale', 'bad_unit'])
async def test_pending_command_requires_later_native_power_and_matching_native_target(battery, report):
    runtime, hass, wall = battery
    manager = await command(battery)
    attrs = {'unit_of_measurement': 'W'}
    age = 20 if report == 'cached' else 0
    if report == 'restored': attrs['restored'] = True
    if report == 'bad_unit': attrs['unit_of_measurement'] = 'kWh'
    if report == 'future': age = -30
    if report == 'stale': age = 121
    if report not in ('cached', 'same_stamp'): wall[0] += 1
    hass.states.set('sensor.bat_power', -1800, attrs, age=age)
    await manager.tick(grid_w=0, allow_command=True)
    assert manager.busy and len(hass.services.calls) == 1
    await ack(battery)
    assert runtime.store.data['battery_fleet']['expected_numbers'] == {
        'bat1': {'entity_id': 'number.bat_setpoint', 'target_w': -1800}}


@pytest.mark.asyncio
async def test_matching_later_power_does_not_confirm_wrong_native_target(battery):
    runtime, hass, wall = battery
    manager = await command(battery)
    wall[0] += 1
    hass.states.set('sensor.bat_power', -1800)
    hass.states.set('number.bat_setpoint', 0)
    await manager.tick(grid_w=0, allow_command=True)
    assert manager.busy and len(hass.services.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('value,attrs,age', [
    (60, {'unit_of_measurement':'%'}, 121), (60, {'unit_of_measurement':'%', 'restored':True}, 0),
    (60, {'unit_of_measurement':'%'}, -30), (60, {'unit_of_measurement':'kWh'}, 0),
    ('unknown', {'unit_of_measurement':'%'}, 0), ('nan', {'unit_of_measurement':'%'}, 0),
    ('inf', {'unit_of_measurement':'%'}, 0), (-1, {'unit_of_measurement':'%'}, 0),
    (101, {'unit_of_measurement':'%'}, 0), (True, {'unit_of_measurement':'%'}, 0),
])
async def test_invalid_soc_never_authorizes_battery_control(battery, value, attrs, age):
    runtime, hass, wall = battery
    hass.states.set('sensor.bat_soc', value, attrs, age=age)
    await runtime.battery_fleet.tick(grid_w=2000, allow_command=True)
    assert not runtime.battery_fleet.read()[0].valid
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_static_soc_helper_and_input_number_power_adapter_keep_native_units_and_domain(battery):
    runtime, hass, wall = battery
    cfg = runtime.battery_fleet.configs['bat1']
    cfg.update(soc_entity='input_number.soc', number_entity='input_number.target', number_sign='charge_positive')
    hass.states.set('input_number.soc', 60, {'unit_of_measurement':'%'}, age=10000)
    hass.states.set('input_number.target', 0, {'unit_of_measurement':'kW', 'min':-5, 'max':5, 'step':.1}, age=10000)
    assert runtime.battery_fleet.read()[0].valid
    assert await runtime.battery_fleet._send('bat1', -1850)
    domain, action, data = hass.services.calls[-1]
    assert (domain, action, data['entity_id']) == ('input_number', 'set_value', 'input_number.target')
    assert data['value'] == pytest.approx(1.8)
    assert runtime.battery_fleet.state.pending['target_w'] == pytest.approx(-1800)


@pytest.mark.asyncio
async def test_command_intent_is_durable_before_physical_call_and_failure_never_retries(battery):
    runtime, hass, wall = battery
    def before_call(domain, action, data):
        saved = runtime.store.data['battery_fleet']['pending']
        assert saved['target_w'] == -1800 and saved['entity_id'] == 'number.bat_setpoint'
    hass.services.on_call = before_call
    hass.services.fail = True
    manager = await command(battery)
    assert not manager.busy and 'bat1' in manager.state.faults
    assert runtime.store.data['battery_fleet']['faults'] == manager.state.faults
    wall[0] += 200
    hass.states.set('sensor.bat_soc', 60)
    hass.states.set('sensor.bat_power', -1800)
    hass.states.set('sensor.grid', -1800)
    manager.state.last_command_mono = None
    for _ in range(3):
        await manager.tick(grid_w=-1800, allow_command=True)
        await manager.prepare_for_removal()
    assert len(hass.services.calls) == 1 and manager.removal_blocked()


@pytest.mark.asyncio
async def test_restore_pending_requires_review_even_when_restart_interval_has_elapsed(battery):
    runtime, hass, wall = battery
    manager = runtime.battery_fleet
    manager.restore({'pending':{'id':'bat1', 'target_w':1900}, 'faults':{}})
    manager.state.last_command_mono = None
    await manager.tick(grid_w=2000, allow_command=True)
    assert 'restart' in manager.state.faults and not hass.services.calls


@pytest.mark.asyncio
async def test_external_native_target_change_is_preserved_and_latched_before_sibling_allocation(battery):
    runtime, hass, wall = battery
    manager = await command(battery)
    await ack(battery)
    second = deepcopy(manager.configs['bat1'])
    second.update(id='bat2', power_entity='sensor.second_power', number_entity='number.second_target')
    manager.configs['bat2'] = second
    wall[0] += 1
    hass.states.set('number.bat_setpoint', 0)
    hass.states.set('sensor.bat_power', 1900)
    hass.states.set('sensor.second_power', 0, {'unit_of_measurement':'W'})
    hass.states.set('number.second_target', 0, {'unit_of_measurement':'W','min':-5000,'max':5000,'step':50})
    hass.states.set('sensor.grid', 100)
    manager.state.last_command_mono = None
    await manager.tick(grid_w=100, allow_command=True)
    assert 'bat1' in manager.state.faults and not manager.state.expected_numbers
    assert manager.recommendation.control_allocations == {'bat1':0, 'bat2':0}
    assert len(hass.services.calls) == 1 and hass.states.get('number.bat_setpoint').state == '0'


@pytest.mark.asyncio
async def test_measured_power_modulation_alone_does_not_claim_manual_change(battery):
    runtime, hass, wall = battery
    manager = await command(battery)
    await ack(battery)
    wall[0] += 1
    hass.states.set('sensor.bat_power', -100)
    await manager.tick(grid_w=0, allow_command=False)
    assert not manager.state.faults and 'bat1' in manager.state.expected_numbers
    saved = manager.snapshot()
    manager.restore(saved)
    assert manager.state.expected_numbers == saved['expected_numbers']


@pytest.mark.asyncio
async def test_removal_requires_zero_native_target_and_later_zero_power_report(battery):
    runtime, hass, wall = battery
    manager = runtime.battery_fleet
    hass.states.set('number.bat_setpoint', -1800)
    assert manager.removal_blocked()
    assert await manager.prepare_for_removal()
    assert hass.services.calls[-1][2]['value'] == 0
    await manager.tick(grid_w=0, allow_command=False)
    assert manager.busy  # unchanged zero power pre-dates neutral command
    await ack(battery, 0)
    await manager.prepare_for_removal()
    assert not manager.removal_blocked() and not manager.settings['control_enabled']
    assert not manager.state.expected_numbers


@pytest.mark.asyncio
@pytest.mark.parametrize('source', ['power', 'target'])
async def test_unknown_controlled_state_never_reports_removal_ready(battery, source):
    runtime, hass, wall = battery
    hass.states.set('sensor.bat_power' if source == 'power' else 'number.bat_setpoint', 'unavailable')
    manager = runtime.battery_fleet
    assert not await manager.prepare_for_removal()
    assert manager.removal_blocked() and manager.settings['control_enabled']
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_neutral_timeout_never_replays_but_known_manual_neutral_can_finish_release(battery):
    runtime, hass, wall = battery
    manager = runtime.battery_fleet
    hass.states.set('number.bat_setpoint', -1800)
    hass.states.set('sensor.bat_power', -1800)
    assert await manager.prepare_for_removal()
    wall[0] += 121
    hass.states.set('sensor.bat_power', -1800)
    await manager.tick(grid_w=0, allow_command=False)
    assert not manager.busy and 'bat1' in manager.state.faults
    for _ in range(3): assert not await manager.prepare_for_removal()
    assert len(hass.services.calls) == 1 and manager.removal_blocked()
    hass.states.set('sensor.bat_power', 0)
    assert not await manager.prepare_for_removal()
    assert not manager.removal_blocked() and len(hass.services.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('target,script', [(-1800,'script.charge'), (1800,'script.discharge'), (0,'script.idle')])
async def test_selected_script_on_wallbox_device_is_rejected(battery, monkeypatch, target, script):
    runtime, hass, wall = battery
    manager = runtime.battery_fleet
    manager.configs['bat1'].update(control_kind='scripts', charge_script='script.charge',
                                  discharge_script='script.discharge', idle_script='script.idle')
    runtime.wallbox_settings.update(enabled=True, power_entity='sensor.ev_power')
    registry = SimpleNamespace(async_get=lambda entity: SimpleNamespace(device_id='wallbox')
                               if entity in (script, 'sensor.ev_power') else None)
    monkeypatch.setattr(er, 'async_get', lambda h: registry)
    with pytest.raises(HomeAssistantError, match='Wallbox'):
        await manager._send('bat1', target)
    assert not hass.services.calls and not manager.busy


@pytest.mark.asyncio
@pytest.mark.parametrize('target', [None, True, float('nan'), float('inf'), 10**1000])
async def test_nonfinite_numeric_target_is_rejected_before_journal_or_service(battery, target):
    runtime, hass, wall = battery
    with pytest.raises(HomeAssistantError, match='eindig'):
        await runtime.battery_fleet._send('bat1', target)
    assert not hass.services.calls and not runtime.battery_fleet.busy


def test_malformed_fault_snapshot_and_even_empty_pending_fail_closed():
    state = BatteryFleetState()
    state.restore({'faults':[], 'pending':{}})
    assert 'restart' in state.faults and state.pending is None


@pytest.mark.asyncio
async def test_native_actuator_bounds_cap_planner_and_do_not_repeat_clipped_target(battery):
    runtime, hass, wall = battery
    manager = runtime.battery_fleet
    hass.states.set('number.bat_setpoint', 0, {'unit_of_measurement':'W', 'min':-1000, 'max':2000, 'step':50})
    assert await manager.tick(grid_w=5000, allow_command=True)
    assert manager.state.pending['target_w'] == 2000
    await ack(battery, 2000)
    wall[0] += 1
    hass.states.set('sensor.grid', 3000)
    manager.state.last_command_mono = None
    assert not await manager.tick(grid_w=3000, allow_command=True)
    assert manager.recommendation.control_allocations['bat1'] == 2000
    assert len(hass.services.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('attrs', [
    {'unit_of_measurement':'W','min':0,'max':5000,'step':0},
    {'unit_of_measurement':'W','min':0,'max':float('inf'),'step':50},
    {'unit_of_measurement':'W','min':5000,'max':0,'step':50},
])
async def test_invalid_actuator_bounds_leave_profile_readonly_without_command(battery, attrs):
    runtime, hass, wall = battery
    hass.states.set('number.bat_setpoint', 0, attrs)
    await runtime.battery_fleet.tick(grid_w=5000, allow_command=True)
    reading = runtime.battery_fleet.read()[0]
    assert reading.valid and not reading.controllable
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_pause_releases_only_acked_numeric_ownership_then_relinquishes_neutral(battery):
    runtime, hass, wall = battery
    manager = await command(battery)
    assert not await manager.release_owned_targets()  # pending is reconciliation-only
    await ack(battery)
    assert await manager.release_owned_targets()
    assert manager.state.pending['target_w'] == 0
    assert len(hass.services.calls) == 2
    await ack(battery, 0)
    assert not await manager.release_owned_targets()
    assert not manager.state.expected_numbers
    assert not runtime.store.data['battery_fleet']['expected_numbers']


@pytest.mark.asyncio
@pytest.mark.parametrize('case', ['unowned', 'manual', 'unknown', 'fault', 'script'])
async def test_pause_never_neutralizes_unowned_manual_unknown_faulted_or_script_targets(battery, case):
    runtime, hass, wall = battery
    manager = runtime.battery_fleet
    if case != 'unowned':
        manager.state.expected_numbers['bat1'] = {'entity_id':'number.bat_setpoint','target_w':-1800}
    hass.states.set('number.bat_setpoint', -1800)
    hass.states.set('sensor.bat_power', -1800)
    if case == 'manual': hass.states.set('number.bat_setpoint', -1000)
    if case == 'unknown': hass.states.set('sensor.bat_power', 'unavailable')
    if case == 'fault': manager.state.faults['bat1'] = 'manual review'
    if case == 'script': manager.configs['bat1']['control_kind'] = 'scripts'
    assert not await manager.release_owned_targets()
    assert not hass.services.calls
    if case == 'manual': assert 'bat1' in manager.state.faults and not manager.state.expected_numbers


@pytest.mark.parametrize('expected', [[], {'bat1':None}, {'bat1':{'entity_id':'number.bat_setpoint','target_w':'invalid'}}])
def test_corrupt_ownership_journal_requires_review_instead_of_losing_provenance(expected):
    state = BatteryFleetState()
    state.restore({'expected_numbers':expected})
    assert 'restart' in state.faults


@pytest.mark.asyncio
async def test_native_nonzero_target_is_released_before_sibling_increase_even_when_power_is_quiet(battery):
    runtime, hass, wall = battery
    manager = runtime.battery_fleet
    second = deepcopy(manager.configs['bat1'])
    second.update(id='bat2', power_entity='sensor.second_power', number_entity='number.second_target')
    manager.configs['bat2'] = second
    hass.states.set('sensor.bat_soc', 80)
    hass.states.set('sensor.second_power', 0, {'unit_of_measurement':'W'})
    hass.states.set('number.second_target', 200, {'unit_of_measurement':'W','min':-5000,'max':5000,'step':50})
    assert await manager.tick(grid_w=1900, allow_command=True)
    assert hass.services.calls[0][2]['entity_id'] == 'number.second_target'
    assert manager.state.pending['target_w'] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('minimum,maximum,step', [(1,5000,50), (-1,5000,50)])
async def test_numeric_actuator_without_exact_neutral_is_readonly_and_removal_waits(battery, minimum, maximum, step):
    runtime, hass, wall = battery
    manager = runtime.battery_fleet
    hass.states.set('number.bat_setpoint', 1, {'unit_of_measurement':'W','min':minimum,'max':maximum,'step':step})
    await manager.tick(grid_w=5000, allow_command=True)
    assert not manager.read()[0].controllable and not hass.services.calls
    assert not await manager.prepare_for_removal()
    assert manager.removal_blocked()


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['target', 'global_permission', 'profile_permission', 'exclusive_permission',
                                    'binding', 'unit', 'bounds', 'restored'])
async def test_durable_intent_wait_rechecks_native_target_binding_and_permissions_before_write(battery, change, monkeypatch):
    runtime, hass, wall = battery
    manager = runtime.battery_fleet
    save = runtime.store.async_save
    changed = False
    async def change_during_save(data):
        nonlocal changed
        await save(data)
        if changed or data['battery_fleet']['pending'] is None:
            return
        changed = True
        cfg = manager.configs['bat1']
        if change == 'target': hass.states.set('number.bat_setpoint', -1000)
        elif change == 'global_permission': manager.settings['control_enabled'] = False
        elif change == 'profile_permission': cfg['control_enabled'] = False
        elif change == 'exclusive_permission': cfg['exclusive_control_confirmed'] = False
        elif change == 'binding': cfg['number_entity'] = 'number.other'
        else:
            attrs = dict(hass.states.get('number.bat_setpoint').attributes)
            if change == 'unit': attrs['unit_of_measurement'] = 'kW'
            if change == 'bounds': attrs['max'] = 1000
            if change == 'restored': attrs['restored'] = True
            hass.states.set('number.bat_setpoint', 0, attrs)
    monkeypatch.setattr(runtime.store, 'async_save', change_during_save)
    assert not await manager._send('bat1', -1800)
    assert changed and not hass.services.calls and not manager.busy
    assert 'bat1' in manager.state.faults
    assert runtime.store.data['battery_fleet']['pending'] is None
    assert runtime.store.data['battery_fleet']['faults'] == manager.state.faults
    if change == 'target': assert hass.states.get('number.bat_setpoint').state == '-1000'
