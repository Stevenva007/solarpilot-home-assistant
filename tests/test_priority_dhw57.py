"""One central allocation, stable hypothetical OFF, then real DHW/P1 proof."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace as NS
import time

import pytest

from custom_components.solar_pilot.dhw import DHWDecision
from custom_components.solar_pilot.priority_board import EXTRA, EXTRA_MIGRATION, WALLBOX
from test_dhw_runtime import setup, tick
from test_priority_board35 import multiple, activate


@pytest.mark.asyncio
async def test_beta57_migration_prioritises_extra_once_and_preserves_all_rights():
    r, h = multiple()
    r.dhw.config['target_entity'] = 'water_heater.test'
    activate(r, ['device:a', WALLBOX, 'device:second_consumer', EXTRA],
             {'device:a': True, 'device:second_consumer': False})
    old_devices = deepcopy(r.entry.options['devices'])
    assert await r.priority_board.migrate_beta57()
    assert r.priority_board.order() == [WALLBOX, EXTRA, 'device:a', 'device:second_consumer']
    assert r.priority_board.permissions() == {'device:a': True, 'device:second_consumer': False}
    assert not r.priority_board.effective_config('a')['_priority_board_before_wallbox']
    assert r.entry.options['devices'] == old_devices and not h.services.calls
    order = ['device:a', WALLBOX, EXTRA, 'device:second_consumer']
    await r.priority_board.save(r.priority_board.revision(), order, r.priority_board.permissions(), True)
    assert r.priority_board.saved[EXTRA_MIGRATION] == 57
    assert not await r.priority_board.migrate_beta57()
    assert r.priority_board.order() == order


@pytest.mark.asyncio
async def test_all_dishwashers_stay_before_extra_even_without_ev_preference():
    r, _ = multiple()
    r.dhw.config['target_entity'] = 'water_heater.test'
    r.configs['second_consumer'].update(kind='dishwasher', dishwasher_priority_enabled=False)
    await r.priority_board.migrate_beta57()
    assert r.priority_board.order().index('device:second_consumer') < r.priority_board.order().index(EXTRA)
    assert any(rule['before'] == 'device:second_consumer' for rule in r.priority_board.constraints())


def reclaim_context(delay=0, grid=-2700, watts=300):
    r, h = setup(config={'rise_delay_s': delay})
    r.configs['a'].update(power_entity='sensor.load', nominal_w=300,
                           min_on_s=0, min_off_s=0, start_delay_s=0)
    r.entry.options['priority_board'] = {'schema': 2, 'order': [WALLBOX, EXTRA, 'device:a'],
        'wallbox_power': {'device:a': False}, EXTRA_MIGRATION: 57}
    h.states.set('switch.load', 'on')
    h.states.set('sensor.load', watts, {'unit_of_measurement': 'W'})
    h.states.set('sensor.grid', grid, {'unit_of_measurement': 'W'})
    state = r.states['a']
    state.on = state.owned = state.enabled = state.available = True
    state.target_w = state.measured_w = watts
    state.last_on = -1e12
    r.device_modes['a'] = 'auto'
    r.grid_w = r.filtered = grid
    r.dhw.read(grid, True, 0, datetime(2026, 10, 6, 12))
    r.dhw._execution_local_now = datetime(2026, 10, 6, 12)
    return r, h


def sample(h, grid=-2700):
    h.states.set('sensor.grid', grid, {'unit_of_measurement': 'W'})


def propose(r, now=100):
    return r.priority_board.extra_reclaim_action(now, datetime(2026, 10, 6, 12))


def test_exact3000_is_hypothesis_only_and_requires_new_p1():
    r, h = reclaim_context()
    reading, policy, model = deepcopy(r.dhw.reading), deepcopy(r.dhw.policy.__dict__), deepcopy(r.dhw.comfort.snapshot())
    states = deepcopy(r.states)
    assert propose(r) is None
    assert propose(r, 101) is None  # same P1 cannot authorise a reduction
    sample(h)
    action = propose(r, 102)
    assert action and action.id == 'a' and action.watts == 0
    assert action.reason.startswith('Zonnestroom vrijmaken voor extra warm water')
    assert r.dhw.reading == reading and r.dhw.policy.__dict__ == policy
    assert r.dhw.comfort.snapshot() == model and r.states == states
    assert not h.services.calls and not r.dhw.pending
    assert r.dhw.reading.export_w == 2700


@pytest.mark.parametrize('grid,watts', [(-2699, 300), (-2000, 999), (-3000, 300)])
def test_insufficient_or_already_fitting_sun_does_not_pause(grid, watts):
    r, h = reclaim_context(grid=grid, watts=watts)
    assert propose(r) is None
    sample(h, grid)
    assert propose(r, 101) is None


@pytest.mark.parametrize('problem', ['unowned', 'off', 'unavailable', 'fault', 'minimum_runtime',
    'non_interruptible', 'dishwasher', 'manual', 'boost', 'deadline', 'urgent', 'planner',
    'estimated', 'stale_meter', 'restored_control', 'no_pv', 'battery', 'cooling', 'space_busy',
    'unknown_cooling', 'hygiene', 'manual_boiler', 'target_capability', 'raise_interval', 'capacity'])
def test_protected_or_unreliable_conditions_never_reclaim(problem):
    r, h = reclaim_context()
    s, cfg = r.states['a'], r.configs['a']
    if problem == 'unowned': s.owned = False
    elif problem == 'off': s.on = False
    elif problem == 'unavailable': s.available = False
    elif problem == 'fault': s.fault = 'offline'
    elif problem == 'minimum_runtime': s.last_on = 99; cfg['min_on_s'] = 600
    elif problem == 'non_interruptible': cfg['non_interruptible'] = True
    elif problem == 'dishwasher': cfg['kind'] = 'dishwasher'
    elif problem == 'manual': s.manual_until = 500
    elif problem == 'boost': s.boost_until = 500
    elif problem == 'deadline': s.deadline_force = True
    elif problem == 'urgent': s.deadline_urgent = True
    elif problem == 'planner': s.planner_grid_force = True
    elif problem == 'estimated': h.states.set('sensor.load', 300, {'unit_of_measurement': 'W', 'estimated': True})
    elif problem == 'stale_meter': h.states.set('sensor.load', 300, {'unit_of_measurement': 'W'}, age=1000)
    elif problem == 'restored_control': h.states.set('switch.load', 'on', {'restored': True})
    elif problem == 'no_pv': h.states.set('sensor.pv', 'unavailable', {'unit_of_measurement': 'W'})
    elif problem == 'battery':
        r.settings.update(battery_mode='separate', battery_power_entity='sensor.battery')
        h.states.set('sensor.battery', 300, {'unit_of_measurement': 'W'})
    elif problem == 'cooling': h.states.set('climate.home', 'cool', {'hvac_action': 'cooling'})
    elif problem == 'space_busy': h.states.set('climate.home', 'heat', {'hvac_action': 'heating'})
    elif problem == 'unknown_cooling': h.states.set('climate.home', 'unavailable')
    elif problem == 'hygiene': h.states.set('binary_sensor.hygiene', 'on')
    elif problem == 'manual_boiler': h.states.set('switch.powerful', 'on')
    elif problem == 'target_capability': h.states.get('water_heater.boiler').attributes['max_temp'] = 55
    elif problem == 'raise_interval': r.dhw.last_command_wall = time.time()
    elif problem == 'capacity':
        r.capacity_settings['enabled'] = True
        r.capacity = replace(r.capacity, enabled=True, optional_headroom_w=100)
    assert propose(r) is None
    sample(h)
    assert propose(r, 102) is None
    assert not h.services.calls


def test_full_stability_and_repeated_samples_and_gap_recovery():
    r, h = reclaim_context(delay=60)
    assert propose(r, 100) is None
    for now in (120, 140, 159):
        sample(h)
        assert propose(r, now) is None
    sample(h)
    assert propose(r, 160).watts == 0
    assert set(r.priority_board.extra_start_blocks(160)) == set()  # only running device
    r.states['a'].on = False
    assert set(r.priority_board.extra_start_blocks(160)) == {'a'}
    r.states['a'].on = True
    sample(h)
    assert propose(r, 200) is None  # >30s gap discards previous stability


def test_dip_discards_prospective_timer_and_actual_dhw_timer_is_untouched():
    r, h = reclaim_context(delay=30)
    assert propose(r, 100) is None
    sample(h, -2200)
    r.grid_w = r.filtered = -2200
    assert propose(r, 120) is None
    sample(h)
    r.grid_w = r.filtered = -2700
    assert propose(r, 125) is None
    sample(h)
    assert propose(r, 150) is None
    sample(h)
    assert propose(r, 155)
    assert r.dhw.policy.candidate_since is None


def test_postoff_window_reserves_raw_sun_while_filter_catches_up():
    r, h = reclaim_context(delay=60)
    action = NS(watts=0, reason='Zonnestroom vrijmaken voor extra warm water: pauze')
    r.priority_board.extra_reclaim_sent(action, 100)
    r.states['a'].on = r.states['a'].owned = False
    h.states.set('switch.load', 'off')
    h.states.set('sensor.load', 0, {'unit_of_measurement': 'W'})
    sample(h, -3000)
    r.grid_w = -3000
    r.filtered = -2700
    r.dhw.read(-3000, True, 0, datetime(2026, 10, 6, 12))
    r.dhw.policy.result = DHWDecision(target_c=50, stage='solar')
    assert set(r.priority_board.extra_start_blocks(110)) == {'a'}
    assert not r.priority_board.extra_start_blocks(1000)  # bounded, not an eternal lock
    sample(h, -2000)
    r.grid_w = -2000
    assert not r.priority_board.extra_start_blocks(120)


@pytest.mark.asyncio
async def test_absent_dhw_does_not_reorder_existing_consumers_or_ev_rights():
    r, h = multiple()
    activate(r, ['device:a', WALLBOX, 'device:second_consumer', EXTRA])
    old = deepcopy(r.entry.options)
    assert not await r.priority_board.migrate_beta57()
    assert r.entry.options == old and EXTRA_MIGRATION not in r.priority_board.saved
    assert r.priority_board.effective_config('a')['_priority_board_before_wallbox']
    assert not h.services.calls


def test_ready_nonpreferred_dishwasher_keeps_first_fitting_window():
    from test_dishwasher import setup as wash_setup
    from test_dishwasher_priority32 import boiler
    from custom_components.solar_pilot.dishwasher import read
    r, h, cfg = wash_setup(dishwasher_priority_enabled=False)
    boiler(r, h)
    r.mode = 'solar'
    r.settings['pv_entity'] = 'sensor.pv'
    h.states.set('sensor.pv', 9000, {'unit_of_measurement': 'W'})
    r.pv_w = 9000
    r.grid_w = r.filtered = -4000
    r.states['a'].enabled = r.states['a'].available = True
    r.entry.options['priority_board'] = {'schema': 2, 'order': ['device:a', WALLBOX, EXTRA],
        'wallbox_power': {'device:a': False}, EXTRA_MIGRATION: 57}
    r.dishwasher.arm(cfg, read(h, cfg), time.time())
    r.states['a'].cycle_armed = True
    reading = r.dhw.read(-4000, True, 0, datetime(2026, 10, 6, 12))
    r.priority_board.guard_extra(reading, time.monotonic())
    assert not reading.luxury_allowed
    assert 'vóór extra boilerwarmte' in reading.luxury_reason
    assert not h.services.calls
    # An unprepared or offline programme is not a live solar start claimant.
    r.dishwasher.tickets['a']['armed'] = False
    reading = r.dhw.read(-4000, True, 0, datetime(2026, 10, 6, 12))
    r.priority_board.guard_extra(reading, time.monotonic())
    assert reading.luxury_allowed


def test_shared_hp_draw_reduces_prospective_import_commitment_once():
    r, h = reclaim_context(grid=-2800, watts=300)
    r.dhw.config['power_entity'] = 'sensor.boiler_power'
    r.dhw.settings['power_entity'] = 'sensor.boiler_power'
    h.states.set('sensor.boiler_power', 1000, {'unit_of_measurement': 'W'})
    r.settings['max_import_w'] = 0
    assert propose(r) is None
    sample(h, -2800)
    assert propose(r, 102)  # incremental 2200, not another whole 3200
    h.states.set('sensor.boiler_power', 1000, {'unit_of_measurement': 'W', 'estimated': True})
    assert propose(r, 103) is None  # unknown draw reserves full 3200 again


def test_safe_freed_watts_may_help_total_peak_limit_but_not_an_unknown_phase():
    r, h = reclaim_context(grid=-2900, watts=400)
    r.capacity_settings['enabled'] = True
    r.capacity = replace(r.capacity, enabled=True, valid=True, allowed_grid_w=0,
                         optional_headroom_w=2900)
    assert propose(r) is None
    sample(h, -2900)
    assert propose(r, 102)  # projected -3300 + 3200 fits, current -2900 +3200 doesn't
    r.phase_settings.update(enabled=True, control_starts=True)
    r.phase = replace(r.phase, enabled=True, valid=True, headroom_w=1000)
    assert propose(r, 103) is None  # ordinary meter alone doesn't prove its phase


def test_new_nonpreferred_dishwasher_after57_keeps_protected_position():
    r, _ = multiple()
    activate(r, [WALLBOX, EXTRA, 'device:a', 'device:second_consumer'])
    r.priority_board.saved[EXTRA_MIGRATION] = 57
    r.configs['new_wash'] = {**r.configs['a'], 'id': 'new_wash', 'kind': 'dishwasher',
                              'dishwasher_priority_enabled': False}
    order = r.priority_board.order()
    assert order.index(WALLBOX) < order.index('device:new_wash') < order.index(EXTRA)
    r.priority_board.validate(r.priority_board.revision(), order, r.priority_board.permissions(), True)
