"""Boiler cooldown retains completed live stability, without unissued hysteresis."""
from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import time

import pytest
from custom_components.solar_pilot import runtime as runtime_module, dhw_runtime
from test_dhw_runtime import setup


@pytest.fixture
def boiler(monkeypatch):
    elapsed = [0.0]
    wall_start = datetime(2026, 9, 22, 13, tzinfo=timezone.utc).timestamp()
    monkeypatch.setattr(time, 'time', lambda: wall_start + elapsed[0])
    control_clock = SimpleNamespace(time=time.time, monotonic=lambda: 1000 + elapsed[0])
    monkeypatch.setattr(runtime_module, 'time', control_clock)
    monkeypatch.setattr(dhw_runtime, 'time', control_clock)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromtimestamp(wall_start + elapsed[0], tz or timezone.utc)
    monkeypatch.setattr(runtime_module, 'datetime', Clock)
    runtime, hass = setup(config={'rise_delay_s':60, 'optional_raise_interval_s':1800,
                                 'hygiene_schedule_enabled':False, 'cooling_clear_s':0})
    def set_state(entity, value, attrs=None, age=0, reported_age=None):
        previous = hass.states.get(entity)
        attrs = previous.attributes if attrs is None and previous else attrs or {}
        stamp = datetime.fromtimestamp(time.time() - age, timezone.utc)
        report = datetime.fromtimestamp(time.time() - (age if reported_age is None else reported_age), timezone.utc)
        hass.states.data[entity] = SimpleNamespace(state=str(value), attributes=dict(attrs),
                                                 last_updated=stamp, last_reported=report)
    monkeypatch.setattr(hass.states, 'set', set_state)
    for entity, state in list(hass.states.data.items()):
        set_state(entity, state.state, state.attributes)
    hass.states.set('water_heater.boiler', 'heat_pump', {**hass.states.get('water_heater.boiler').attributes,
                                                       'temperature':50, 'current_temperature':50})
    hass.states.set('sensor.water', 50)
    hass.states.set('climate.home', 'off', {'hvac_action':'off'})
    hass.states.set('climate.salon', 'off', {'hvac_action':'off'})
    runtime.dhw.last_command_wall = time.time()  # Last ANY target write, including normal50.
    runtime.settings['settle_s'] = 0
    return runtime, hass, elapsed


async def report(boiler, seconds, *, pv=6080, grid=-5260, cooling=False, full_runtime=False, allow=True):
    runtime, hass, elapsed = boiler
    elapsed[0] = seconds
    for entity, state in list(hass.states.data.items()):
        hass.states.set(entity, state.state, state.attributes)
    hass.states.set('sensor.pv', pv)
    hass.states.set('sensor.grid', grid)
    hass.states.set('climate.home', 'cool' if cooling else 'off', {'hvac_action':'cooling' if cooling else 'off'})
    runtime.pv_w = None if pv == 'unavailable' else pv
    if full_runtime:
        await runtime.tick()
        assert runtime.mode == 'solar', runtime.problem
    else:
        await runtime.dhw.tick(runtime_module.time.monotonic(), grid, True, 0, allow,
                               datetime.fromtimestamp(time.time(), ZoneInfo('Europe/Brussels')))
    return runtime.dhw


def writes(hass):
    return [call for call in hass.services.calls if call[1] == 'set_temperature']


@pytest.mark.asyncio
@pytest.mark.parametrize('full_runtime', [False, True])
async def test_continuous_five_second_samples_finish_stability_once_then_wait_for_any_write_interval(boiler, full_runtime):
    runtime, hass, elapsed = boiler
    for seconds in range(0, 1800, 5):
        manager = await report(boiler, seconds, full_runtime=full_runtime)
        expected = max(0, 60 - seconds)
        assert manager.policy.result.remaining_s == expected, (seconds, manager.status)
        assert not writes(hass)
        if seconds >= 60:
            assert manager.policy.current is None  # No unexecuted target grants hysteresis.
            assert manager.policy.candidate == 60
            assert manager.policy.candidate_since == 1000
            assert manager.overview()['optional_raise_remaining_s'] == 1800 - seconds
    manager = await report(boiler, 1800, full_runtime=full_runtime)
    assert manager.policy.result.remaining_s == 0
    assert manager.pending and manager.pending['target'] == 60
    assert [call[2]['temperature'] for call in writes(hass)] == [60]
    assert manager.overview()['optional_raise_remaining_s'] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('loss', ['pv_missing', 'surplus', 'cooling', 'sample_gap'])
async def test_real_solar_loss_cooling_or_sampling_gap_requires_new_full_stability(boiler, loss):
    runtime, hass, elapsed = boiler
    for seconds in range(0, 70, 5): await report(boiler, seconds)
    assert runtime.dhw.policy.result.remaining_s == 0
    if loss == 'sample_gap':
        manager = await report(boiler, 105)
        assert manager.policy.result.remaining_s == 60
        origin = 105
    else:
        manager = await report(boiler, 70, pv='unavailable' if loss == 'pv_missing' else 6080,
                               grid=-3300 if loss == 'surplus' else -5260, cooling=loss == 'cooling')
        assert manager.policy.candidate is None and manager.policy.result.target_c == 50
        manager = await report(boiler, 75)
        assert manager.policy.result.remaining_s == 60
        origin = 75
    for seconds in range(origin + 5, origin + 60, 5):
        manager = await report(boiler, seconds)
        assert manager.policy.result.remaining_s == origin + 60 - seconds
    manager = await report(boiler, origin + 60)
    assert manager.policy.result.remaining_s == 0 and manager.policy.current is None
    assert not writes(hass)


@pytest.mark.asyncio
async def test_completed_but_throttled_sixty_does_not_authorize_unissued_fiftyfive_pv_hysteresis(boiler):
    runtime, hass, elapsed = boiler
    runtime.dhw.settings['solar_c'] = 55
    for seconds in range(0, 70, 5): await report(boiler, seconds)
    assert runtime.dhw.policy.current is None and runtime.dhw.policy.candidate == 60
    manager = await report(boiler, 70, pv=950, grid=-3300)
    assert manager.policy.result.target_c == 50 and manager.policy.candidate is None
    assert not writes(hass)


@pytest.mark.asyncio
async def test_other_pending_command_delays_dispatch_without_restarting_completed_stability(boiler):
    runtime, hass, elapsed = boiler
    runtime.dhw.last_command_wall = time.time() - 1800
    for seconds in range(0, 70, 5): await report(boiler, seconds, allow=False)
    assert runtime.dhw.policy.result.remaining_s == 0 and not writes(hass)
    assert 'andere regelopdracht' in runtime.dhw.status
    manager = await report(boiler, 70, allow=True)
    assert manager.pending and manager.pending['target'] == 60
    assert len(writes(hass)) == 1


@pytest.mark.asyncio
async def test_serialized_sixty_proposal_issued_and_confirmed_retains_real_owned_surplus_hold_band(boiler):
    runtime, hass, elapsed = boiler
    runtime.dhw.last_command_wall = time.time() - 1800
    for seconds in range(0, 70, 5): await report(boiler, seconds, allow=False)
    assert runtime.dhw.policy.current is None and not writes(hass)
    manager = await report(boiler, 70, allow=True)
    assert manager.policy.current == 60 and manager.pending
    manager = await report(boiler, 75)
    assert not manager.pending and manager.owned_target == 60 and manager.policy.current == 60
    manager = await report(boiler, 80, grid=-3300)
    assert manager.policy.result.target_c == 60 and manager.policy.current == 60
    assert [call[2]['temperature'] for call in writes(hass)] == [60]


@pytest.mark.asyncio
async def test_safety_denied_mature_fiftyfive_proposal_grants_no_pv_hold_after_permission(boiler):
    runtime, hass, elapsed = boiler
    runtime.dhw.settings.update(solar_c=55, safety_confirmed=False, optional_raise_interval_s=0)
    for seconds in range(0, 70, 5): await report(boiler, seconds, pv=2000, grid=0)
    assert runtime.dhw.policy.current is None and runtime.dhw.policy.candidate == 55
    assert not writes(hass)
    runtime.dhw.settings['safety_confirmed'] = True
    manager = await report(boiler, 70, pv=950, grid=100)
    assert manager.policy.result.target_c == 50 and not writes(hass)


@pytest.mark.asyncio
async def test_already_issued_sixty_pending_delayed_native_report_preserves_later_confirmed_hold(boiler, monkeypatch):
    runtime, hass, elapsed = boiler
    manager = runtime.dhw
    manager.last_command_wall = time.time() - 1800
    monkeypatch.setattr(manager, '_ack_poll_min_s', lambda: 10)
    hass.services.respond = False
    for seconds in range(0, 65, 5): await report(boiler, seconds, allow=False)
    await report(boiler, 65)
    assert manager.pending and manager.policy.current == 60
    await report(boiler, 70)
    assert manager.pending and manager.policy.current == 60  # Issued target is not an unissued proposal.
    attrs = dict(hass.states.get('water_heater.boiler').attributes)
    attrs['temperature'] = 60
    hass.states.set('water_heater.boiler', 'heat_pump', attrs)
    await report(boiler, 73)
    assert manager.pending and manager.policy.current == 60  # Early cloud echo cannot ACK.
    await report(boiler, 75)
    assert not manager.pending and manager.owned_target == 60 and manager.policy.current == 60
    await report(boiler, 80, grid=-3300)
    assert manager.policy.result.target_c == 60 and manager.policy.current == 60
    assert [call[2]['temperature'] for call in writes(hass)] == [60]


@pytest.mark.asyncio
async def test_normal_fifty_write_keeps_the_existing_any_write_interval_anchor(boiler):
    runtime, hass, elapsed = boiler
    attrs = dict(hass.states.get('water_heater.boiler').attributes)
    attrs['temperature'] = 49
    hass.states.set('water_heater.boiler', 'heat_pump', attrs)
    manager = await report(boiler, 0, pv=0, grid=100)
    assert manager.pending and manager.pending['target'] == 50
    written_wall = manager.last_command_wall
    await report(boiler, 5, pv=0, grid=100)
    assert not manager.pending and manager.owned_target == 50
    for seconds in range(10, 75, 5): await report(boiler, seconds)
    assert manager.policy.result.remaining_s == 0
    assert manager.last_command_wall == written_wall
    assert manager.overview()['optional_raise_remaining_s'] == 1730
    assert [call[2]['temperature'] for call in writes(hass)] == [50]
