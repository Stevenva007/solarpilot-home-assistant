"""Optional source outages never become a global verified-OFF prerequisite.

All fixtures are synthetic. These tests exercise runtime and shipped card code,
not physical appliances or a live Home Assistant installation.
"""
from copy import deepcopy
from datetime import datetime, timezone
import time

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.engine import State
from test_runtime import build
from test_dishwasher import setup as dishwasher_setup
from test_source_wait_ui52 import render_alerts
from test_device_retry_audit90 import failed_start, fresh


def physical(hass):
    return [call for call in hass.services.calls if call[0] != 'persistent_notification']


def unavailable_site(*, owned=False, recovery=False):
    runtime, hass, _cfg = dishwasher_setup()
    runtime.mode = 'paused'
    runtime.device_modes['a'] = 'auto'
    runtime.states['a'].owned = owned
    runtime.states['a'].target_w = 2000 if owned else 0
    if recovery:
        runtime.recovery['a'] = {'name': 'Offline appliance', 'watts': 2000}
    hass.states.set('sensor.dw_connection', 'Disconnected')
    hass.states.set('sensor.dw_remote', 'Disabled')
    runtime.wallbox_settings.update(enabled=True, power_entity='sensor.ev_power',
        status_entity='sensor.ev_status', mode_entity='select.ev_mode')
    runtime.wallbox_guard = runtime._make_wallbox_guard()
    runtime.sg_wallbox_guard = runtime._make_sg_wallbox_guard()
    hass.states.set('sensor.ev_power', 'unavailable', {'unit_of_measurement': 'W'})
    hass.states.set('sensor.ev_status', 'Ready')
    hass.states.set('select.ev_mode', 'full_solar')
    peer, _ = build(device={'nominal_w': 300})
    runtime.configs['b'] = {**peer.configs['a'], 'id': 'b', 'name': 'Healthy load',
                            'control_entity': 'switch.healthy'}
    runtime.consumer_history.configs['b'] = runtime.configs['b']
    runtime.states['b'] = State(last_off=time.monotonic()-1000)
    runtime.device_modes['b'] = 'auto'
    hass.states.set('switch.healthy', 'off')
    return runtime, hass


@pytest.mark.asyncio
@pytest.mark.parametrize(('owned', 'recovery'), [(False, False), (True, False), (True, True)])
async def test_stale_reset_is_noop_for_offline_dishwasher_and_preserves_lease(owned, recovery):
    runtime, hass = unavailable_site(owned=owned, recovery=recovery)
    await runtime.tick()
    record = deepcopy(runtime.device_retry.records['a'])
    leases = deepcopy(runtime.recovery)
    tickets = deepcopy(runtime.dishwasher.tickets)
    logs = list(runtime.logs)
    saves = len(runtime.store.saves)
    for _ in range(3):
        await runtime.reset()
    assert runtime.device_retry.records['a'] == record
    assert runtime.recovery == leases
    assert runtime.dishwasher.tickets == tickets
    assert runtime.states['a'].owned == owned
    assert not runtime.states['a'].available
    assert not runtime.restart_blocking
    assert runtime.mode == 'paused'
    assert len(runtime.store.saves) == saves and list(runtime.logs) == logs
    assert not physical(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize(('owned', 'recovery'), [(False, False), (True, False), (True, True)])
async def test_offline_dishwasher_and_wallbox_do_not_block_healthy_residual_solar(owned, recovery):
    runtime, hass = unavailable_site(owned=owned, recovery=recovery)
    runtime.mode = 'solar'
    await runtime.tick()
    assert physical(hass) == [('switch', 'turn_on', {'entity_id': 'switch.healthy'})]
    assert runtime.device_retry.waiting('a')
    assert not runtime.restart_blocking
    assert runtime.wallbox_guard.result.max_increase_w is None
    assert not runtime.wallbox_guard.result.block_increase
    assert runtime.isolated_reserve_w == 0
    assert runtime.wallbox_overview()['reclaimable_w'] == 0
    assert not runtime.faults


@pytest.mark.asyncio
@pytest.mark.parametrize('grid', [0, 700])
async def test_optional_outages_never_invent_solar_or_bypass_import_limits(grid):
    runtime, hass = unavailable_site()
    runtime.mode = 'solar'
    hass.states.set('sensor.grid', grid, {'unit_of_measurement': 'W'})
    await runtime.tick()
    assert not physical(hass)
    assert runtime.result.targets.get('b', 0) == 0
    assert not runtime.restart_blocking


@pytest.mark.asyncio
@pytest.mark.parametrize('recovery', [False, True])
async def test_review_of_real_off_fault_does_not_wait_for_or_erase_unrelated_offline_appliance(recovery):
    runtime, hass = unavailable_site(owned=True, recovery=recovery)
    await runtime.tick()
    runtime.faults['b'] = 'Maximale looptijd bereikt: controleer en wis de melding'
    runtime.states['b'].fault = runtime.faults['b']
    record = deepcopy(runtime.device_retry.records['a'])
    lease = deepcopy(runtime.recovery)
    await runtime.reset()
    assert 'b' not in runtime.faults
    assert runtime.device_retry.records['a'] == record
    assert runtime.recovery == lease
    assert runtime.states['a'].owned and not runtime.states['a'].available
    assert not physical(hass)
    assert 'a' in runtime.store.data['device_retry']['records']


@pytest.mark.asyncio
@pytest.mark.parametrize('report', ['before_command', 'restored'])
async def test_reset_cannot_erase_uncertain_command_using_old_or_restored_off(monkeypatch, report):
    runtime, hass, clock = await failed_start(monkeypatch)
    runtime.mode = 'paused'
    item = deepcopy(runtime.device_retry.records['a'])
    if report == 'before_command':
        fresh(hass, 'switch.load', 'off', clock)
        stamp = datetime.fromtimestamp(item['issued_wall']-10, timezone.utc)
        hass.states.get('switch.load').last_reported = stamp
        hass.states.get('switch.load').last_updated = stamp
    else:
        fresh(hass, 'switch.load', 'off', clock, {'restored': True})
    with pytest.raises(HomeAssistantError, match='schakel eerst veilig uit'):
        await runtime.reset()
    assert runtime.device_retry.records['a'] == item
    assert runtime.states['a'].owned
    assert len(physical(hass)) == 1


@pytest.mark.asyncio
async def test_battery_pending_is_not_consumed_by_an_unrelated_review():
    runtime, hass = unavailable_site()
    runtime.battery_fleet.state.pending = {'id': 'synthetic-battery', 'command': 'uncertain'}
    pending = deepcopy(runtime.battery_fleet.state.pending)
    with pytest.raises(HomeAssistantError, match='lopende opdracht'):
        await runtime.reset()
    assert runtime.battery_fleet.state.pending == pending
    assert not physical(hass)


@pytest.mark.asyncio
async def test_wallbox_wait_is_typed_and_disappears_after_real_source_recovery():
    runtime, hass = unavailable_site()
    await runtime.tick()
    assert runtime.problem_kind == 'wallbox_wait'
    assert 'Wallbox' in runtime.problem
    assert not [c for c in hass.services.calls if c[:2] == ('persistent_notification', 'create')]
    hass.states.set('sensor.ev_power', 0, {'unit_of_measurement': 'W'})
    await runtime.tick()
    assert runtime.problem_kind == '' and runtime.problem == ''
    assert runtime.device_retry.waiting('a')
    assert not physical(hass)


def test_wallbox_wait_has_no_fault_color_or_reset_button_and_explains_peer_independence():
    _, notice = render_alerts({'mode': 'solar', 'problem_kind': 'wallbox_wait',
        'problem': 'Wallbox-laadvermogen ontbreekt', 'reset_entity': 'button.reset'})
    assert notice.notices == [['notice']]
    assert 'Wallbox tijdelijk niet bereikbaar' in notice.text
    assert 'Dit blokkeert andere toestellen niet' in notice.text
    assert 'onbekend laadvermogen wordt niet als vrij vermogen gerekend' in notice.text
    assert 'reset' not in notice.actions


def test_wallbox_configuration_remains_visible_without_a_useless_off_reset():
    _, notice = render_alerts({'mode': 'solar', 'problem_kind': 'wallbox_configuration',
        'problem': 'Dubbele koppeling', 'reset_entity': 'button.reset'})
    assert 'Wallboxkoppeling controleren' in notice.text
    assert 'reset' not in notice.actions
    assert notice.notices == [['notice', 'warn']]
