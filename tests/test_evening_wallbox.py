"""Bounded evening reserve may use confirmed autonomous solar EV power only."""
from copy import deepcopy
from types import SimpleNamespace
import time

import pytest

from test_dhw_comfort27 import at, wb_context
from test_dhw_runtime import setup
from test_priority_board35 import multiple
from custom_components.solar_pilot.priority_board import EXTRA


@pytest.mark.parametrize('change', [
    {'confirmed': False}, {'mode': 'manual'}, {'mode': 'unknown'}, {'mode': 'stopped'},
    {'valid': False}, {'connected': False}, {'connected': None}, {'demand': False},
    {'demand': None}, {'age': 121}, {'age': float('inf')}, {'age': -6},
    {'stamp': 0}, {'power': 0}, {'power': float('nan')}, {'power': -4000},
])
def test_evening_cannot_borrow_unconfirmed_stale_manual_or_idle_ev_power(change):
    r, h = setup(config={'evening_enabled': True, 'hygiene_schedule_enabled': False})
    wb_context(r, **{'power': 4000, 'status': 'Charging', **change})
    r.pv_w = 6000
    h.states.set('sensor.water', 49, {'unit_of_measurement': '°C'})
    rd = r.dhw.read(-100, True, 0, at(16))
    r.dhw._prepare_comfort(at(16), rd)
    assert rd.export_w == 100 and rd.comfort_stage != 'evening'
    assert not h.services.calls


@pytest.mark.parametrize('grid,valid,discharge,pv', [
    (None, False, 0, 6000), (-100, False, 0, 6000), (-100, True, 4000, 6000),
    (-100, True, 0, None), (-100, True, 0, 900), (2000, True, 0, 4000),
])
def test_evening_ev_credit_never_replaces_real_site_solar_or_battery_measurement(grid, valid, discharge, pv):
    r, h = setup(config={'evening_enabled': True, 'hygiene_schedule_enabled': False})
    wb_context(r, power=4000, status='Charging')
    r.pv_w = pv
    h.states.set('sensor.water', 49, {'unit_of_measurement': '°C'})
    rd = r.dhw.read(grid, valid, discharge, at(16))
    r.dhw._prepare_comfort(at(16), rd)
    assert rd.comfort_stage != 'evening'
    assert not h.services.calls


@pytest.mark.asyncio
async def test_confirmed_solar_ev_allows_only_bounded_evening_setpoint_not_ev_or_heat_mode_commands():
    r, h = setup(config={'evening_enabled': True, 'hygiene_schedule_enabled': False})
    wb_context(r, power=4000, status='Charging')
    r.pv_w = 6000
    h.states.set('sensor.water', 49, {'unit_of_measurement': '°C'})
    sent = await r.dhw.tick(time.monotonic(), -100, True, 0, True, at(16))
    assert sent and r.dhw.policy.result.stage == 'evening'
    assert r.dhw.reading.export_w == 100
    assert [(domain, action) for domain, action, _ in h.services.calls] == [('water_heater', 'set_temperature')]
    assert 50 < h.services.calls[0][2]['temperature'] <= 55
    assert 'auto minder laden' in r.dhw.policy.result.reason


@pytest.mark.parametrize('guard', ['cooling', 'hygiene', 'space_heating', 'capacity'])
@pytest.mark.asyncio
async def test_evening_ev_permission_does_not_bypass_existing_guards(guard):
    r, h = setup(config={'evening_enabled': True, 'hygiene_schedule_enabled': False})
    wb_context(r, power=4000, status='Charging')
    r.pv_w = 6000
    h.states.set('sensor.water', 49, {'unit_of_measurement': '°C'})
    if guard == 'cooling':
        h.states.set('climate.salon', 'cool', {'hvac_action': 'cooling'})
    elif guard == 'space_heating':
        h.states.set('climate.salon', 'heat', {'hvac_action': 'heating'})
    elif guard == 'hygiene':
        h.states.set('binary_sensor.hygiene', 'on')
    else:
        r.capacity = SimpleNamespace(enabled=True, optional_headroom_w=500)
        r.capacity_settings['respect_optional_dhw'] = True
    await r.dhw.tick(time.monotonic(), -100, True, 0, True, at(16))
    assert not [call for call in h.services.calls if call[2].get('temperature', 0) > 50]
    if guard == 'hygiene':
        assert not h.services.calls
    assert r.dhw.reading.export_w == 100


def test_evening_reserve_has_explicit_fixed_wallbox_permission_without_enabling_other_installations():
    r, h = multiple()
    before = deepcopy(r.entry.options)
    row = next(x for x in r.priority_board.protected_rows() if x['id'] == 'dhw_evening')
    assert not row['active']
    assert row['name'] == 'Avondvoorraad warm water (maximaal 55 °C)'
    assert row['power_label'] == 'Wallbox-vermogen: ja, bij bevestigd zonneladen'
    assert 'geen laadcommando' in row['reason'] and 'koeling' in row['reason']
    assert r.entry.options == before and not h.services.calls


def test_enabled_evening_reserve_exposes_existing_permission_and_actual_ceiling():
    r, h = setup(config={'evening_enabled': True, 'evening_cap_c': 54})
    row = next(x for x in r.priority_board.protected_rows() if x['id'] == 'dhw_evening')
    assert row['active'] and '54 °C' in row['name']
    extra = next(x for x in r.priority_board.overview()['rows'] if x['id'] == EXTRA)
    assert extra['power_label'] == 'Wallbox-vermogen: nee · alleen echt vrij overschot'
    assert not h.services.calls
