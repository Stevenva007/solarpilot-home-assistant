"""Forecast evidence integration: per-time counts, seasons and missing coverage."""
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json

import pytest

from test_runtime import build

BRUSSELS = ZoneInfo('Europe/Brussels')
NOW = datetime(2026, 10, 25, 10, tzinfo=BRUSSELS)


def profile():
    runtime, hass = build()
    forecast = runtime.pv_forecast
    forecast._last_local_now = NOW
    forecast.position = lambda dt: (None, None)
    forecast.source.valid = True
    forecast.source.raw_at = lambda stamp, current: 3000
    for hour, value in [(15, .8), (16, .6), (17, .9)]:
        for minute in range(0, 60, 15):
            dt = NOW.replace(hour=hour, minute=minute)
            key = forecast.model._keys(dt, None, None)[0]
            forecast.model.bins[key] = {'days': {
                (NOW.date()-timedelta(days=i)).isoformat(): [value] for i in range(1, 9)},
                'factor': value, 'updated_day': (NOW.date()-timedelta(days=1)).isoformat()}
    return forecast


def test_afternoon_diagnostics_show_each_quarter_factor_without_mutating_model():
    forecast = profile()
    before = deepcopy(forecast.model.snapshot())
    data = forecast.diagnostics()['quarter_profile']
    assert data['day'] == '2026-10-25'
    assert len(data['quarters']) == 12
    assert [r['factor'] for r in data['quarters']] == [.8]*4 + [.6]*4 + [.9]*4
    assert [r['corrected_w'] for r in data['quarters']] == [2400]*4 + [1800]*4 + [2700]*4
    assert all(r['calibration']['days'] == 8 for r in data['quarters'])
    assert all('key' not in r['calibration'] for r in data['quarters'])
    assert all(r['time'].endswith('+01:00') for r in data['quarters'])
    assert forecast.model.snapshot() == before
    json.dumps(data, allow_nan=False)


def test_missing_native_curve_does_not_become_known_zero_or_fictitious_correction():
    forecast = profile()
    forecast.source.raw_at = lambda stamp, current: None
    data = forecast.quarter_profile()
    assert all(r['raw_w'] is None and r['corrected_w'] is None for r in data['quarters'])
    assert data['quarters'][4]['factor'] == .6


def test_no_snapshot_has_no_invented_diagnostic_day():
    runtime, _ = build()
    data = runtime.pv_forecast.quarter_profile()
    assert data['day'] is None and data['quarters'] == []


def test_explicit_calibration_optout_keeps_all_projection_factors_one():
    forecast = profile()
    forecast.settings['calibration_enabled'] = False
    assert all(r['factor'] == 1 and not r['calibration']['applied']
               for r in forecast.quarter_profile()['quarters'])


def test_horizon_exposes_specific_evidence_and_does_not_confuse_total_days(monkeypatch):
    from test_pv_forecast33 import source_fixture
    runtime, hass, entries, now = source_fixture(monkeypatch)
    runtime.pv_forecast.update(now)
    horizon = runtime.pv_forecast.cached['horizon']
    assert len(horizon) == 4
    assert all('calibration' in r and 'minimum_days_required' in r['calibration'] for r in horizon)
    assert all('key' not in r['calibration'] for r in horizon)
    assert 'calibration' in runtime.pv_forecast.cached
    assert not hass.services.calls
