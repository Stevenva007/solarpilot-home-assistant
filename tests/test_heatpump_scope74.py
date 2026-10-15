"""Circuit inactivity and incomplete metering never certify whole-HP OFF."""
from copy import deepcopy
import time

import pytest

from test_heatpump_inactivity_scope69 import OperationStatus, typed_poll
from test_heatpump_task67 import automatic_monitor
from test_heatpump_ui65 import (assert_unknown_operation_is_hidden, business_tile,
    heatpump_panel, metered_sample, parsed)
from test_native_tank_action66 import DeviceDirection, TankCoordinator
from test_sg_observations64 import observed


def global_off(**changes):
    result = {'function': None, 'inactive': True, 'inactive_action': 'off',
        'inactive_scope': 'global', 'verified_global_off': True, 'conflict': False,
        'source': 'aquarea_poll', 'observed_at': time.time(), 'stale_s': 120}
    result.update({key: value() if callable(value) else value for key, value in changes.items()})
    return result


def operation_idle(stamp=None):
    return {'state': 'idle', 'label': 'Panasonic meldt rust', 'evidence': 'native_action',
            'observed_at': time.time() if stamp is None else stamp, 'stale_s': 120}


def assert_no_whole_hp_idle_label(root):
    tasks = [node for node in heatpump_panel(root).walk() if 'data-heatpump-task' in node.attributes]
    assert all('Niet actief' not in node.text() for node in tasks)


def monitored_scope(monkeypatch, *, main="unavailable", tank=OperationStatus.ON,
                    direction=DeviceDirection.IDLE):
    now = time.time()
    env, runtime, hass = automatic_monitor(monkeypatch)
    env.clock[0] = now
    coordinator = TankCoordinator()
    env.entries['native'].runtime_data = {'pump': coordinator}
    config = {**runtime.panasonic.settings, 'zone_entities': env.sources['zone_entities'],
              'tank_target_entity': 'number.hp_tank_target'}
    runtime.panasonic.update_config(config)
    for entity in [env.sources['tank_entity'], *env.sources['zone_entities'],
                   env.sources['direction_entity'], env.sources['defrost_entity']]:
        obj = hass.states.get(entity)
        env.state(entity, obj.state, dict(obj.attributes), stamp=now - 1)
    tank_state = 'heating' if direction == DeviceDirection.WATER else 'on'
    env.state(env.sources['tank_entity'], tank_state, {'operation_mode': tank_state,
              'current_temperature': 49, 'temperature': 50, 'temperature_unit': '°C'}, stamp=now - 1)
    env.state(env.sources['direction_entity'], direction.name, stamp=now - 1)
    env.state('number.hp_tank_target', 50, {'unit_of_measurement': '°C'}, stamp=now - 1)
    env.state('sensor.hp_supply_one', main, {'unit_of_measurement': 'W'}, stamp=now - 1)
    env.state('sensor.hp_supply_two', 0, {'unit_of_measurement': 'W'}, stamp=now - 1)
    runtime.panasonic.overview()  # Only subscribe to the read-only provider.
    typed_poll(coordinator, tank=tank, direction=direction)
    return runtime, hass, coordinator


@pytest.mark.parametrize('view', ['board', 'comfort'])
def test_fresh_zone_off_tank_on_idle_and_invalid_main_feed_remain_unknown(monkeypatch, view):
    runtime, hass, coordinator = monitored_scope(monkeypatch)
    before = deepcopy(runtime.panasonic.settings), deepcopy(runtime.sg_boost.snapshot())
    overview = runtime.panasonic.overview()
    assert all(row['action'] == 'off' for row in overview['zones'])
    assert overview['native_task']['inactive_scope'] == 'unknown'
    assert overview['native_task']['verified_global_off'] is False
    assert overview['power_activity']['complete'] is False
    assert overview['power_activity']['active'] is False
    assert overview['operation']['state'] == 'unknown'
    data = metered_sample(0, complete=False)
    data['panasonic'] = overview
    _, root = parsed(data, view)
    assert_unknown_operation_is_hidden(root)
    assert_no_whole_hp_idle_label(root)
    assert (runtime.panasonic.settings, runtime.sg_boost.snapshot()) == before
    assert not hass.services.calls and not coordinator.api_calls


def test_raw_typed_whole_device_off_is_retained_but_unverified_provider_is_not_display_stop_proof(monkeypatch):
    runtime, hass, coordinator = monitored_scope(monkeypatch, tank=OperationStatus.OFF)
    overview = runtime.panasonic.overview()
    assert overview['native_task']['verified_global_off'] is True
    assert overview['operation']['state'] == 'idle'
    assert overview['operation']['observed_at'] == overview['native_task']['observed_at']
    assert overview['source_contract']['status'] == 'unknown'
    assert overview['source_contract']['native_device_registered'] is True
    assert overview['operation_display']['function'] is None
    assert overview['operation_display']['active'] is None
    data = metered_sample(0, complete=False)
    data['panasonic'] = overview
    _, root = parsed(data)
    assert_unknown_operation_is_hidden(root)
    assert_no_whole_hp_idle_label(root)
    assert not hass.services.calls and not coordinator.api_calls


def test_raw_space_off_tank_route_and_electrical_activity_do_not_bypass_unverified_provider_contract(monkeypatch):
    runtime, hass, coordinator = monitored_scope(monkeypatch, main=2170, direction=DeviceDirection.WATER)
    overview = runtime.panasonic.overview()
    assert overview['native_task']['inactive_scope'] == 'space_circuit'
    assert overview['operation']['state'] == 'unknown'
    assert overview['power_activity']['function'] == 'tapwater_heating'
    assert overview['source_contract']['status'] == 'unknown'
    assert overview['operation_display']['function'] is None
    assert overview['operation_display']['active'] is True
    data = metered_sample(2170)
    data['panasonic'] = overview
    _, root = parsed(data)
    tile = business_tile(root, 'data-heatpump-task')
    assert tile.attributes['data-heatpump-task'] == 'activity'
    assert 'taak onbekend' in tile.text()
    assert 'Niet actief' not in tile.text()
    assert not hass.services.calls and not coordinator.api_calls


def test_known_source_contract_qualifies_dhw_ui_without_rewriting_raw_space_off():
    from custom_components.solar_pilot.display_operation import classify_display_operation
    from test_display_operation83 import contract_snapshot, NOW
    p = contract_snapshot(route='WATER', tank=True, main=2170)
    # This current UI fixture carries the loaded semantic proof; legacy history
    # fixtures intentionally keep their original closed version-bound evidence.
    p["source_contract"]["compatibility"] = {"schema": 1, "contract": "aquarea_special_status_action_v1",
        "verified": True, "basis": "loaded_source", "fingerprint": "c"*64}
    p['native_task'].update(inactive_scope='space_circuit', verified_global_off=False, independent_tank_on=True)
    delta = time.time()-NOW
    def shift_reports(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.endswith('observed_at') and isinstance(child, (int, float)):
                    value[key] = child+delta
                else:
                    shift_reports(child)
        elif isinstance(value, list):
            for child in value:
                shift_reports(child)
    shift_reports(p)
    original = deepcopy(p['native_task'])
    p['operation_display'] = classify_display_operation(p)
    assert p['native_task'] == original
    assert p['operation_display']['function'] == 'tapwater_heating'
    assert p['operation_display']['tier'] == 'derived'
    data = metered_sample(2170)
    data['panasonic'] = p
    _, root = parsed(data)
    tile = business_tile(root, 'data-heatpump-task')
    assert tile.attributes['data-heatpump-task'] == 'inferred' and 'Boiler opwarmen' in tile.text()
    p['source_contract']['pump']['state'] = 'off'
    p['operation_display'] = classify_display_operation(p)
    assert p['native_task'] == original and p['operation_display']['function'] is None
    _, root = parsed(data)
    assert 'taak onbekend' in business_tile(root, 'data-heatpump-task').text()


@pytest.mark.parametrize('change', [
    {'verified_global_off': False}, {'verified_global_off': 1}, {'inactive': 1},
    {'inactive_scope': 'unknown'}, {'inactive_scope': 'space_circuit'},
    {'inactive_action': 'idle'}, {'source': 'native_hvac_action'}, {'conflict': True},
    {'independent_tank_on': True}, {'independent_tank_on': 1}, {'independent_tank_on': 'true'},
    {'conflict': 1}, {'function': 'tapwater_heating'},
    {'observed_at': None}, {'observed_at': True},
    {'observed_at': lambda: time.time() - 121}, {'observed_at': lambda: time.time() + 60},
    {'stale_s': None}, {'stale_s': True}, {'stale_s': 600, 'observed_at': lambda: time.time() - 121},
])
def test_backend_and_frontend_reject_unverified_malformed_or_expired_global_off(change):
    runtime, hass = observed()
    proof = global_off(**change)
    assert runtime.panasonic._operation(None, None, [], None, None, proof)['state'] == 'unknown'
    data = metered_sample(0, complete=False)
    data['panasonic'].update(native_task=proof, operation=operation_idle())
    _, root = parsed(data)
    assert_unknown_operation_is_hidden(root)
    assert_no_whole_hp_idle_label(root)
    assert not hass.services.calls


def test_explicit_null_source_limit_cannot_certify_global_off_in_ui():
    data = metered_sample(0, complete=False)
    data['panasonic'].update(source_stale_s=None, native_task=global_off(), operation=operation_idle())
    _, root = parsed(data)
    assert_unknown_operation_is_hidden(root)
    assert_no_whole_hp_idle_label(root)


def test_missing_freshness_fields_keep_the_bounded_legacy_default():
    runtime, hass = observed()
    proof = global_off()
    proof.pop('stale_s')
    assert runtime.panasonic._operation(None, None, [], None, None, proof)['state'] == 'idle'
    data = metered_sample(0, complete=False)
    data['panasonic'].pop('source_stale_s')
    data['panasonic'].update(native_task=proof, operation=operation_idle())
    _, root = parsed(data)
    assert 'Niet actief' in business_tile(root, 'data-heatpump-task').text()
    assert not hass.services.calls


@pytest.mark.parametrize('watts,label', [(0, 'Geen elektrisch verbruik'), (58, 'Basisverbruik')])
def test_complete_fresh_low_power_is_electrical_evidence_without_native_whole_off(watts, label):
    data = metered_sample(watts, roles=('main', 'heater'))
    data['panasonic'].update(operation=operation_idle(),
        native_task=global_off(verified_global_off=False, inactive_scope='unknown'))
    _, root = parsed(data)
    assert label in business_tile(root, 'data-heatpump-task').text()
    assert_no_whole_hp_idle_label(root)


def test_confirmed_zero_hz_is_specific_compressor_status_not_whole_hp_off():
    data = metered_sample(0, complete=False)
    data['panasonic'].update(operation={**operation_idle(), 'evidence': 'compressor_frequency',
        'label': 'Compressor staat stil'}, compressor_frequency_hz=0)
    _, root = parsed(data)
    assert 'Compressor staat stil' in business_tile(root, 'data-heatpump-task').text()
    assert_no_whole_hp_idle_label(root)


@pytest.mark.parametrize('case', ['restored', 'old_meter'])
def test_restore_or_stale_complete_meter_cannot_establish_new_inactivity(case):
    data = metered_sample(0, roles=('main', 'heater'))
    if case == 'restored':
        data['restored'] = True
        data['panasonic'].update(native_task=global_off(), operation=operation_idle())
    else:
        old = time.time() - 121
        for supply in data['panasonic']['power_activity']['supplies']:
            supply['observed_at'] = old
        data['panasonic']['power_activity']['observed_at'] = old
        data['panasonic']['power_observed_at'] = old
    _, root = parsed(data)
    assert_unknown_operation_is_hidden(root)
    assert_no_whole_hp_idle_label(root)

