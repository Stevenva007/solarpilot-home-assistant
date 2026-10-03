"""Read-only activity/value presentation against HA doubles, never hardware."""
from datetime import datetime, timedelta, timezone
import time
import pytest
from test_runtime import build
from custom_components.solar_pilot.wallbox import Reading


@pytest.mark.parametrize('watts,demand,valid,age,expected', [
    (2750, True, True, 0, 'charging'),
    (2750, False, True, 0, 'charging'),
    (0, True, True, 0, 'waiting'),
    (0, False, True, 0, 'stopped'),
    (2750, True, False, 0, 'unknown'),
    (2750, True, True, 600, 'unknown'),
    (None, True, True, 0, 'unknown'),
])
def test_wallbox_activity_requires_actual_valid_power(watts, demand, valid, age, expected):
    runtime, hass = build()
    runtime.wallbox_settings['enabled'] = True
    runtime.wallbox_guard.reading = Reading(power_w=watts, stamp=time.time()-age,
                                           demand=demand, valid=valid, mode='manual')
    row = runtime.wallbox_overview()
    assert row['activity'] == expected
    assert row['active'] is (expected == 'charging')
    assert row['read_only'] is True
    assert not row['reclaim_allowed_now']
    assert hass.services.calls == []


@pytest.mark.parametrize('status', ['Scheduled', 'Waiting for car demand'])
def test_top_level_native_waiting_status_matches_detailed_classifier(status):
    runtime, hass = build()
    runtime.wallbox_settings['enabled'] = True
    stamp = time.time()
    reading = Reading(power_w=0, stamp=stamp, demand=False, status=status,
                      valid=True, age_s=0, status_stamp=stamp)
    runtime._observe_wallbox_activity(reading, 0, 0)
    runtime.wallbox_guard.reading = reading
    row = runtime.wallbox_overview()
    assert row['activity'] == 'waiting'
    assert row['activity_details']['current']['state'] == 'waiting'
    assert row['activity_details']['current']['label'] == 'Auto wacht'
    assert hass.services.calls == []


def test_no_request_presentation_overrides_stale_manual_session_wording():
    runtime, hass = build()
    runtime.wallbox_settings['enabled'] = True
    stamp = time.time()
    runtime.wallbox_guard.reading = Reading(
        power_w=0, stamp=stamp, demand=False, status='Waiting for car demand',
        mode='manual', valid=True, age_s=0, session_confirmed=True,
        session_reason='Manueel laden: EV-vermogen blijft gereserveerd voor de auto',
        session_value='Manueel laden · klaar', status_stamp=stamp,
    )
    row = runtime.wallbox_overview()
    assert not row['reclaim_allowed_now']
    assert row['reclaim_reason'] == 'Geen actieve Wallbox-laadvraag: geen vermogen gereserveerd'
    assert hass.services.calls == []


def test_wallbox_native_stop_history_is_read_only_durable_and_survives_resume():
    runtime, hass = build()
    runtime.wallbox_settings['enabled'] = True
    now = time.time()
    runtime._observe_wallbox_activity(Reading(power_w=2400, stamp=now-10, demand=True,
        valid=True, status='Charging', age_s=10, status_stamp=now-10), -500, 0)
    runtime._observe_wallbox_activity(Reading(power_w=0, stamp=now-1, demand=True,
        valid=True, status='Waiting in queue by Eco-Smart', age_s=1, status_stamp=now-1), 0, 0)
    details = runtime.wallbox_overview()['activity_details']
    assert details['current']['waiting_for'] == 'solar'
    assert details['last_stop']['stop_confirmed']
    assert details['last_stop']['cause_reported']
    assert 'zonnestroom' in details['last_stop']['stop_reason']
    assert not details['last_stop']['solar_pilot_cause_proven']
    snapshot = runtime._snapshot()['wallbox_activity']
    runtime._observe_wallbox_activity(Reading(power_w=2000, stamp=now, demand=True,
        valid=True, status='Charging', age_s=0), -500, 0)
    assert runtime.wallbox_overview()['activity_details']['last_stop'] == details['last_stop']
    restored, _ = build()
    restored.wallbox_activity.restore(snapshot)
    assert restored.wallbox_overview()['activity_details']['last_stop'] == details['last_stop']
    assert hass.services.calls == []


@pytest.mark.asyncio
async def test_tick_observes_native_wallbox_without_actuator_calls():
    runtime, hass = build()
    runtime.wallbox_settings.update(enabled=True, power_entity='sensor.wb_power',
        status_entity='sensor.wb_status', mode_entity='select.wb_mode')
    hass.states.set('sensor.wb_power', 2400, {'unit_of_measurement':'W'})
    hass.states.set('sensor.wb_status', 'Charging')
    hass.states.set('select.wb_mode', 'manual')
    status_obj = hass.states.get('sensor.wb_status')
    status_stamp = getattr(status_obj, 'last_reported', status_obj.last_updated).timestamp()
    await runtime.tick()
    details = runtime.wallbox_overview()['activity_details']
    assert details['current']['known'] and details['current']['active']
    assert details['current']['status_report_timestamp'] == status_stamp
    assert details['last_stop'] is None
    assert hass.services.calls == []


def _automatic_interval(runtime, *, dt=30, day=None):
    now = day or datetime.now(timezone.utc)
    runtime._record_automatic_value(now, dt, -500, True, 0, .30, .03)
    return runtime.savings_history.report(current_date=now.date().isoformat())


def test_automatic_value_counts_only_auto_owned_active_not_manual_or_boost():
    runtime, hass = build()
    runtime.mode = 'solar'
    runtime.pv_w = 3500
    runtime.device_modes['a'] = 'auto'
    state = runtime.states['a']
    state.owned = state.on = state.available = True
    state.measured_w = 2000
    report = _automatic_interval(runtime)
    assert report['today']['solar_kwh'] == pytest.approx(2000*30/3_600_000, abs=1e-6)
    assert report['today']['power_estimated']
    assert report['proven_savings_eur'] is None
    first = runtime.savings_history.snapshot()
    state.manual_forced = True
    _automatic_interval(runtime, day=datetime.now(timezone.utc)+timedelta(seconds=31))
    assert runtime.savings_history.report()['available_period']['solar_kwh'] == report['today']['solar_kwh']
    state.manual_forced = False
    state.boost_until = time.monotonic()+100
    _automatic_interval(runtime, day=datetime.now(timezone.utc)+timedelta(seconds=62))
    assert runtime.savings_history.report()['available_period']['solar_kwh'] == report['today']['solar_kwh']
    assert first['records']
    assert hass.services.calls == []


@pytest.mark.parametrize(('attrs', 'estimated'), [
    ({'estimated': True}, True),
    ({'is_estimated': True}, True),
    ({'restored': True}, True),
    ({'friendly_name': 'Toestelvermogen geschat'}, True),
    ({'friendly_name': 'Shelly toestelvermogen'}, False),
])
@pytest.mark.asyncio
async def test_estimated_meter_metadata_stays_qualified_in_runtime_and_value(attrs, estimated):
    runtime, hass = build(power=True)
    hass.states.set('switch.load', 'on')
    hass.states.set('sensor.load', 2000, {'unit_of_measurement': 'W', **attrs})
    runtime.mode = 'solar'
    runtime.device_modes['a'] = 'auto'
    state = runtime.states['a']
    state.owned = True
    state.target_w = 1000
    await runtime.tick()
    assert runtime.energy_estimated is estimated
    assert runtime.overview()[0]['estimated'] is estimated
    runtime.savings_history.records.clear()
    runtime.pv_w = 3500
    report = _automatic_interval(runtime)
    if attrs.get('restored'):
        # A restored power placeholder has no valid active interval to qualify
        # as estimated savings. Zero-watt coverage may still be recorded.
        assert report['today']['solar_kwh'] in (None, 0)
        assert report['today']['estimated_benefit_eur'] in (None, 0)
        assert not any(row.get('automatic', {}).get('managed_kwh', 0) > 0
                       for row in runtime.savings_history.records.values())
        assert hass.services.calls == [
            ('switch', 'turn_off', {'entity_id': 'switch.load'}),
        ]
    else:
        assert report['today']['power_estimated'] is estimated
        assert hass.services.calls == []


@pytest.mark.parametrize('block', ['paused', 'pending', 'recovery', 'fault', 'gap'])
def test_uncertain_or_nonautomatic_intervals_are_not_backfilled(block):
    runtime, hass = build()
    runtime.mode = 'solar'
    runtime.pv_w = 3500
    runtime.device_modes['a'] = 'auto'
    state = runtime.states['a']
    state.owned = state.on = state.available = True
    state.measured_w = 2000
    if block == 'paused': runtime.mode = 'paused'
    if block == 'pending': runtime.pending = {'id':'a'}
    if block == 'recovery': runtime.recovery = {'a':{}}
    if block == 'fault': runtime.faults = {'a':'fault'}
    report = _automatic_interval(runtime, dt=3600 if block == 'gap' else 30)
    assert report['today']['estimated_benefit_eur'] is None
    assert report['today']['solar_kwh'] is None
    assert hass.services.calls == []


def test_savings_persist_in_runtime_without_repricing_or_actuator_calls():
    runtime, hass = build()
    runtime.mode = 'solar'
    runtime.pv_w = 3500
    runtime.device_modes['a'] = 'auto'
    state = runtime.states['a']
    state.owned = state.on = state.available = True
    state.measured_w = 2000
    report = _automatic_interval(runtime)
    saved = runtime._snapshot()['savings_history']
    new, other = build()
    new.savings_history.restore(saved)
    assert new.ems_overview()['savings']['available_period'] == report['available_period']
    assert hass.services.calls == other.services.calls == []


def test_savings_today_uses_home_assistant_timezone_not_host_timezone(monkeypatch):
    from types import SimpleNamespace
    import custom_components.solar_pilot.runtime as runtime_module
    runtime, hass = build()
    hass.config = SimpleNamespace(time_zone='Europe/Brussels')
    moment = datetime(2026, 10, 1, 23, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(runtime_module, 'datetime', SimpleNamespace(now=lambda tz=None:moment.astimezone(tz)))
    assert runtime.ems_overview()['savings']['today']['date'] == '2026-10-02'
