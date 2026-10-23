"""Delayed original counter reports cannot be relabelled to the capture date."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import sys
import pytest

path = Path(__file__).parents[1] / 'custom_components/solar_pilot/dishwasher_meter.py'
spec = importlib.util.spec_from_file_location('sp_meter_midnight105', path)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

@pytest.mark.parametrize('zone', ['UTC', 'Europe/Brussels'])
def test_delayed_previous_day_reports_do_not_count_as_today(zone):
    midnight = datetime(2026, 1, 2, tzinfo=ZoneInfo(zone))
    cfg = {'power_entity': 'sensor.fixture_power', 'energy_entity': 'sensor.fixture_energy'}
    states = {}
    hass = SimpleNamespace(states=SimpleNamespace(get=states.get))
    meter = m.DishwasherMeter(cfg)
    def sample(capture_s, report_s, total):
        capture = midnight + timedelta(seconds=capture_s)
        report = midnight + timedelta(seconds=report_s)
        states[cfg['power_entity']] = SimpleNamespace(state=0,
            attributes={'unit_of_measurement': 'W'}, last_reported=capture)
        states[cfg['energy_entity']] = SimpleNamespace(state=total,
            attributes={'unit_of_measurement': 'kWh', 'state_class': 'total_increasing'},
            last_reported=report)
        return meter.sample(hass, capture)
    first = sample(10, -60, 10)
    second = sample(20, -30, 10.01)
    assert not first['energy_valid'] and not second['energy_valid']
    assert second['energy_today_kwh'] is None
    assert sample(30, 30, 10.02)['energy_today_kwh'] is None
    assert sample(90, 90, 10.03)['energy_today_kwh'] == pytest.approx(.01)
