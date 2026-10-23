"""Synthetic meter cases: never household data or actuator calls."""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from pathlib import Path
import importlib.util
import sys
import pytest

# Pure component module; no Home Assistant install is needed for these tests.
path = Path(__file__).parents[1]/'custom_components/solar_pilot/dishwasher_meter.py'
spec = importlib.util.spec_from_file_location('sp_meter105', path)
m = importlib.util.module_from_spec(spec);sys.modules[spec.name] = m;spec.loader.exec_module(m)
START = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
CFG = {'power_entity':'sensor.test_power', 'energy_entity':'sensor.test_energy'}

class FakeStates:
    def __init__(self): self.items = {}
    def get(self, key): return self.items.get(key)
    def put(self, key, value, seconds=0, unit='W', **attrs):
        self.items[key] = SimpleNamespace(state=value, attributes={'unit_of_measurement':unit,'state_class':'total_increasing',**attrs}, last_reported=START+timedelta(seconds=seconds), last_updated=START+timedelta(seconds=seconds))

@pytest.fixture
def setup():
    h = SimpleNamespace(states=FakeStates())
    return h, m.DishwasherMeter(CFG)

def sample(h, meter, seconds, watts, *, energy=10, native=None, finished=False, **kwargs):
    h.states.put(CFG['power_entity'], watts, seconds)
    h.states.put(CFG['energy_entity'], energy, seconds, 'kWh')
    return meter.sample(h, START+timedelta(seconds=seconds), native, finished, **kwargs)

def test_manual_start_without_any_cloud(setup):
    h,t=setup
    assert sample(h,t,0,0)['active'] is False
    assert sample(h,t,5,90)['active'] is False
    result=sample(h,t,65,80)
    assert result['active'] is True and result['source']=='meter'
    assert result['programme_finished'] is False

def test_short_pulse_is_not_cycle(setup):
    h,t=setup
    sample(h,t,0,0);sample(h,t,5,1800)
    assert sample(h,t,30,0)['active'] is False

def test_unchanged_cached_report_does_not_finish_debounce(setup):
    h,t=setup
    sample(h,t,0,100)
    assert t.sample(h,START+timedelta(seconds=65))['active'] is None

def test_silent_phase_kept_then_unconfirmed_end(setup):
    h,t=setup
    sample(h,t,0,100);sample(h,t,60,100)
    for second in range(70,970,60):
        assert sample(h,t,second,0)['active'] is True
    r=sample(h,t,970,0)
    assert r['active'] is False and r['programme_finished'] is False

def test_native_paused_overrides_zero_watts(setup):
    h,t=setup
    for second in range(0,1900,60):
        assert sample(h,t,second,0,native=True)['active'] is True

def test_native_finish_closes_inferred_activity(setup):
    h,t=setup
    sample(h,t,0,100);sample(h,t,60,100)
    r=sample(h,t,70,0,native=False,finished=True)
    assert r['active'] is False and r['source']=='native'

def test_cloud_off_does_not_erase_independent_running_meter(setup):
    h,t=setup
    sample(h,t,0,100,native=False)
    assert sample(h,t,60,100,native=False)['active'] is True

@pytest.mark.parametrize('value', ['unknown','unavailable','NaN','inf','-inf',True,False,-1,None,''])
def test_invalid_power_never_becomes_zero(setup,value):
    h,t=setup
    assert sample(h,t,0,value)['power_w'] is None
    assert t.latest['active'] is None

@pytest.mark.parametrize('attr', ['restored','estimated','is_estimated'])
def test_restored_or_estimated_rejected(setup,attr):
    h,t=setup
    h.states.put(CFG['power_entity'],1000,0,**{attr:True})
    assert t.sample(h,START)['power_valid'] is False

@pytest.mark.parametrize('unit', ['kWh','Wh','A',''])
def test_wrong_power_units_rejected(setup,unit):
    h,t=setup
    h.states.put(CFG['power_entity'],1000,0,unit)
    assert t.sample(h,START)['power_valid'] is False

def test_kw_wh_conversion(setup):
    h,t=setup
    h.states.put(CFG['power_entity'],1.8,0,'kW')
    h.states.put(CFG['energy_entity'],1234,0,'Wh')
    result=t.sample(h,START)
    assert result['power_w']==1800 and result['energy_total_kwh']==pytest.approx(1.234)

def test_unknown_breaks_session_no_fictional_off(setup):
    h,t=setup
    sample(h,t,0,100);sample(h,t,60,100)
    assert sample(h,t,70,'unavailable')['active'] is None
    assert sample(h,t,90,100)['active'] is None

def test_stale_high_report_is_unknown(setup):
    h,t=setup
    sample(h,t,0,100);sample(h,t,60,100)
    assert t.sample(h,START+timedelta(seconds=181))['active'] is None

def test_gap_between_reports_restarts_debounce(setup):
    h,t=setup
    sample(h,t,0,100)
    assert sample(h,t,400,100)['active'] is None

def test_counter_delta_not_total_or_power_integral(setup):
    h,t=setup
    sample(h,t,0,2000,energy=50)
    r=sample(h,t,60,2000,energy=50.02)
    assert r['energy_today_kwh']==pytest.approx(.02)
    assert r['energy_partial'] is True
    assert t.sample(h,START+timedelta(seconds=61))['energy_today_kwh']==pytest.approx(.02)

def test_counter_reset_no_negative_or_spike(setup):
    h,t=setup
    sample(h,t,0,100,energy=50);sample(h,t,60,100,energy=.1)
    assert t.latest['energy_today_kwh'] is None
    assert sample(h,t,120,100,energy=.11)['energy_today_kwh']==pytest.approx(.01)

def test_counter_jump_rebaselines_without_inventing_consumption(setup):
    h,t=setup
    sample(h,t,0,100,energy=1)
    assert sample(h,t,60,100,energy=100)['energy_today_kwh'] is None

def test_energy_gap_not_interpolated(setup):
    h,t=setup
    sample(h,t,0,100,energy=1)
    assert sample(h,t,600,100,energy=1.1)['energy_today_kwh'] is None

def test_midnight_delta_not_split_arbitrarily(setup):
    h,t=setup
    sample(h,t,43170,100,energy=1)
    assert sample(h,t,43230,100,energy=1.01)['energy_today_kwh'] is None

def test_restart_preserves_totals_not_live_state(setup):
    h,t=setup
    sample(h,t,0,100,energy=1);sample(h,t,60,100,energy=1.01)
    other=m.DishwasherMeter(CFG)
    assert other.restore(t.snapshot()) is True
    r=sample(h,other,120,100,energy=1.02)
    assert r['energy_today_kwh']==pytest.approx(.01)
    assert r['active'] is None

def test_duplicate_meter_rejected(setup):
    h,t=setup
    r=sample(h,t,0,1500,dedicated=False)
    assert r['active'] is None and r['power_w'] is None and r['energy_total_kwh'] is None

def test_settings_validation():
    for key,value in [('dishwasher_meter_start_w',True),('dishwasher_meter_end_s',-1),('dishwasher_meter_idle_w',20),('dishwasher_meter_stale_s',float('nan'))]:
        assert m.config_errors({key:value})

def test_unknown_storage_does_not_restore():
    assert m.DishwasherMeter(CFG).restore({'version':2,'days':{}}) is False

def test_no_control_dependencies():
    text=path.read_text()
    assert 'async_call' not in text and 'button.press' not in text and 'turn_off' not in text


def test_numeric_configuration_strings_normalised():
    h=SimpleNamespace(states=FakeStates())
    t=m.DishwasherMeter({**CFG,'dishwasher_meter_start_w':'20','dishwasher_meter_idle_w':'0'})
    assert sample(h,t,0,25)['active'] is None
    assert sample(h,t,60,25)['active'] is True

def test_invalid_config_cannot_use_native_data_to_make_meter_valid(setup):
    h,_=setup
    t=m.DishwasherMeter({**CFG,'dishwasher_meter_start_w':True})
    result=sample(h,t,0,100,native=True)
    assert result['source']=='native' and result['active'] is True
    assert result['power_valid'] is False and result['energy_valid'] is False

def test_non_cumulative_energy_is_unknown(setup):
    h,t=setup
    h.states.put(CFG['power_entity'],100,0)
    h.states.put(CFG['energy_entity'],10,0,'kWh',state_class='measurement')
    assert t.sample(h,START)['energy_valid'] is False

def test_power_only_binding_has_no_fake_energy(setup):
    h,_=setup;t=m.DishwasherMeter({'power_entity':CFG['power_entity']})
    r=sample(h,t,0,0)
    assert r['energy_total_kwh'] is None and r['energy_today_kwh'] is None
