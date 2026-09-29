"""PV contract tests against actual modules and explicit HA doubles; no network."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from zoneinfo import ZoneInfo
import json
import pytest
from custom_components.solar_pilot.pv_forecast_source import (
    PV_FORECAST_DEFAULTS, ForecastSolarSource, PowerSeries, finite, stamp, ENTITY_ROLES)
from custom_components.solar_pilot.pv_calibration import PVCalibration, solar_position
from custom_components.solar_pilot.pv_forecast import PVForecast, PV_SENSOR_DEFINITIONS
from test_runtime import build

UTC=timezone.utc
NOW=datetime(2026,9,15,12,tzinfo=UTC)

def settings(**kw):return {**PV_FORECAST_DEFAULTS,**kw}

@pytest.mark.parametrize('value',[None,True,False,'unknown','unavailable','nan','inf','-inf',{},[]])
def test_bad_numbers_are_unknown_not_zero(value):assert finite(value) is None

@pytest.mark.parametrize('value',[None,'garbage','2026-09-29T12:00:00',''])
def test_naive_or_invalid_timestamps_are_rejected(value):assert stamp(value) is None

@pytest.mark.parametrize('unit,value,result',[('W',2345,2345),('kW',2.345,2345),('Wh',2,None),('A',25,None)])
def test_power_units(unit,value,result):
    r,h=build();h.states.set('sensor.forecast',value,{'unit_of_measurement':unit})
    source=ForecastSolarSource(h,settings(now_entity='sensor.forecast'))
    source.refresh(datetime.now(UTC).timestamp())
    assert source.scalars['now_entity']==result
    assert not h.services.calls

@pytest.mark.parametrize('unit,value,result',[('Wh',2500,2.5),('kWh',2.5,2.5),('W',2500,None),('A',25,None)])
def test_energy_units(unit,value,result):
    r,h=build();h.states.set('sensor.energy',value,{'unit_of_measurement':unit})
    s=ForecastSolarSource(h,settings(remaining_entity='sensor.energy'));s.refresh(datetime.now(UTC).timestamp())
    assert s.scalars['remaining_entity']==result

@pytest.mark.parametrize('age',[7300,-600])
def test_old_or_future_sensor_not_valid(age):
    r,h=build();h.states.set('sensor.forecast',2500,{'unit_of_measurement':'W'},age=age)
    s=ForecastSolarSource(h,settings(now_entity='sensor.forecast'));s.refresh(datetime.now(UTC).timestamp())
    assert not s.valid and s.raw_at(NOW.timestamp(),NOW.timestamp()) is None


def source_fixture(monkeypatch,entries_count=1,custom_name='sensor.renamed_by_user'):
    r,h=build(settings={'pv_entity':'sensor.pv'})
    now=datetime.now(UTC);t=now.timestamp()
    h.states.set(custom_name,3000,{'unit_of_measurement':'W'})
    h.states.set('sensor.pv',2200,{'unit_of_measurement':'W'})
    entries=[NS(entry_id=f'fs{i}',domain='forecast_solar',title=f'Installation {i}',disabled_by=None,
        data={},options={'inverter_size':10000,'damping_morning':0,'damping_evening':0,'api_key':'NEVER_EXPORT'},
        subentries={'plane':NS(data={'modules_power':13800,'declination':25,'azimuth':180,'latitude':1,'secret':'secret'})},
        runtime_data=NS(last_update_success=True,data=NS(watts={now+timedelta(hours=x):max(0,3000-x*500) for x in range(-1,7)}))) for i in range(entries_count)]
    h.config_entries=NS(async_entries=lambda domain: entries if domain=='forecast_solar' else [],
        async_get_entry=lambda i:next((e for e in entries if e.entry_id==i),None))
    from homeassistant.helpers import entity_registry as er
    ents={custom_name:NS(entity_id=custom_name,config_entry_id='fs0',unique_id='fs0_power_production_now',disabled_by=None)}
    monkeypatch.setattr(er,'async_get',lambda _:NS(entities=ents))
    return r,h,entries,now


def test_auto_discovery_uses_registry_not_entity_name(monkeypatch):
    r,h,entries,now=source_fixture(monkeypatch)
    s=ForecastSolarSource(h,settings());s.refresh(now.timestamp())
    assert s.valid and s.refs['now_entity']=='sensor.renamed_by_user'
    assert s.entry_id=='fs0' and s.raw_at(now.timestamp()+2*3600,now.timestamp())==2000
    assert 'NEVER_EXPORT' not in json.dumps(s.metadata) and 'latitude' not in json.dumps(s.metadata)
    assert not h.services.calls


def test_ambiguous_auto_discovery_does_not_mix_installations(monkeypatch):
    r,h,entries,now=source_fixture(monkeypatch,2)
    s=ForecastSolarSource(h,settings());s.refresh(now.timestamp())
    assert not s.valid and not s.refs and len(s.candidates)==2 and 'Meerdere' in s.warning
    s.refresh(now.timestamp()+60);assert 'Meerdere' in s.warning


def test_explicit_entry_resolves_ambiguity(monkeypatch):
    r,h,e,now=source_fixture(monkeypatch,2)
    s=ForecastSolarSource(h,settings(forecast_entry_id='fs0'));s.refresh(now.timestamp());assert s.valid


def test_disabled_source_keeps_auto_off(monkeypatch):
    r,h,e,now=source_fixture(monkeypatch)
    s=ForecastSolarSource(h,settings(enabled=False));s.refresh(now.timestamp())
    assert not s.valid and not s.series.points


def test_adapter_absent_scalar_forecasts_still_work(monkeypatch):
    r,h,e,now=source_fixture(monkeypatch);e[0].runtime_data=None
    s=ForecastSolarSource(h,settings());s.refresh(now.timestamp())
    assert s.valid and s.raw_at(now.timestamp(),now.timestamp())==3000
    assert s.raw_at(now.timestamp()+7200,now.timestamp()) is None


def test_failed_coordinator_never_exposes_stale_curve(monkeypatch):
    r,h,e,now=source_fixture(monkeypatch);e[0].runtime_data.last_update_success=False
    s=ForecastSolarSource(h,settings());s.refresh(now.timestamp());assert not s.series.points
    assert s.valid # still fresh scalar data, no guessed future


def test_stale_equal_coordinator_not_rejuvenated(monkeypatch):
    r,h,e,now=source_fixture(monkeypatch)
    s=ForecastSolarSource(h,settings());s.refresh(now.timestamp())
    obj=h.states.get('sensor.renamed_by_user');obj.last_reported=now+timedelta(hours=3)
    s.refresh(now.timestamp()+3*3600)
    assert s.valid and not s.series.points and 'cache te oud' in s.warning


def test_new_equal_data_object_is_real_update(monkeypatch):
    r,h,e,now=source_fixture(monkeypatch);s=ForecastSolarSource(h,settings());s.refresh(now.timestamp())
    obj=h.states.get('sensor.renamed_by_user');obj.last_reported=now+timedelta(hours=3)
    e[0].runtime_data.data=deepcopy(e[0].runtime_data.data)
    s.refresh(now.timestamp()+3*3600);assert s.series.points


def test_series_linear_integral_no_outside_extrapolation():
    s=PowerSeries([(0,0),(3600,2000),(7200,0)])
    assert s.at(1800)==1000 and s.energy(0,7200)==2
    assert s.at(-1) is None and s.energy(0,7201) is None
    assert s.energy(0,7200,lambda t,w:w*.8)==pytest.approx(1.6)


def test_series_gaps_are_not_free_energy_or_sun():
    s=PowerSeries([(0,1000),(14400,1000)]);assert s.energy(0,14400) is None
    night=PowerSeries([(0,0),(36000,0)]);assert night.energy(0,36000)==0


def test_series_rejects_nonfinite_and_bounds_size():
    s=PowerSeries([(0,'nan'),(1,-1),(2,True),(3,1e10),(4,1000)])
    assert s.points==[(4,1000)]
    assert len(PowerSeries([(i,1) for i in range(9999)]).points)==2048

@pytest.mark.parametrize('day,hours',[(datetime(2026,3,29,tzinfo=ZoneInfo('Europe/Brussels')),23),
    (datetime(2026,10,25,tzinfo=ZoneInfo('Europe/Brussels')),25)])
def test_dst_integrates_elapsed_not_assumed_24_hours(day,hours):
    end=day+timedelta(days=1)
    s=PowerSeries([(day.timestamp()+i*3600,1000) for i in range(hours+1)])
    assert s.energy(day.timestamp(),end.timestamp())==hours


def quarter(model,dt,actual=2400,raw=3000,**kw):
    model.started=dt.timestamp()-1000
    for i in range(16):
        now=dt+timedelta(minutes=i)
        a=actual[i] if isinstance(actual,list) else actual
        model.observe(now=now,actual_w=a,raw_w=raw,meter_stamp=now.timestamp(),azimuth=190,elevation=35,**kw)
    return model.history[-1]


def test_single_day_never_applies_shadow():
    m=PVCalibration(settings());quarter(m,NOW)
    assert m.counts['accepted']==1 and m.factor(NOW,190,35)[0]==1


def test_distinct_days_gradual_correction_and_persistence():
    m=PVCalibration(settings())
    for i in range(9):quarter(m,NOW+timedelta(days=i))
    factor,conf,days,_=m.factor(NOW+timedelta(days=9),190,35)
    assert .75 <= factor <= .8+1e-9 and conf>=.7 and days==9
    saved=json.loads(json.dumps(m.snapshot(),allow_nan=False));rest=PVCalibration(settings());rest.restore(saved)
    assert rest.factor(NOW+timedelta(days=9),190,35)==m.factor(NOW+timedelta(days=9),190,35)
    assert rest.started is None and rest.window is None # no restored half-window


def test_same_day_repeats_cannot_fabricate_distinct_days():
    m=PVCalibration(settings())
    for i in range(24):quarter(m,NOW+timedelta(minutes=15*i))
    assert m.summary()['days']==1 and m.factor(NOW,190,35)[0]==1

@pytest.mark.parametrize('actual,raw,why',[(9970,10000,'clipping'),(4000,10000,'clipping'),(11200,9000,'outlier'),
    (0,3000,'outlier'),(100,200,'Te weinig zon'),(None,3000,'ongeldige'),(2000,None,'ongeldige')])
def test_training_rejection_reasons(actual,raw,why):
    m=PVCalibration(settings());row=quarter(m,NOW,actual,raw)
    assert not row['accepted'] and why in row['reason'] and not m.bins


def test_rapid_clouds_not_shadow():
    m=PVCalibration(settings());row=quarter(m,NOW,[2500 if i%2 else 1300 for i in range(16)])
    assert not row['accepted'] and 'bewolking' in row['reason']


def test_incomplete_quarter_rejected():
    m=PVCalibration(settings());m.started=NOW.timestamp()-1000
    for minute in (0,4,8,12,16):
        t=NOW+timedelta(minutes=minute);m.observe(now=t,actual_w=2000,raw_w=3000,meter_stamp=t.timestamp())
    assert not m.history[-1]['accepted'] and 'dekking' in m.history[-1]['reason']


def test_restart_warmup_prevents_learning():
    m=PVCalibration(settings())
    for i in range(16):
        t=NOW+timedelta(minutes=i);m.observe(now=t,actual_w=2000,raw_w=3000,meter_stamp=t.timestamp())
    assert 'Opstart' in m.history[-1]['reason']


def test_frozen_and_stale_measurements_not_counted():
    m=PVCalibration(settings());m.started=NOW.timestamp()-1000
    for i in range(16):
        t=NOW+timedelta(minutes=i);m.observe(now=t,actual_w=2000,raw_w=3000,meter_stamp=NOW.timestamp())
    assert not m.history[-1]['accepted'] and 'verse' in m.history[-1]['reason']


def test_no_16_hour_magic_shadow_and_distinct_sun_positions():
    m=PVCalibration(settings())
    for i in range(8):quarter(m,NOW+timedelta(days=i))
    dt=NOW+timedelta(days=8,hours=4)
    assert m.factor(dt,250,20)[0]==1
    assert m.factor(dt,190,35)[0]<1 # same geometry, not same clock


def test_seasons_separate_and_previous_year_not_reused():
    m=PVCalibration(settings())
    for i in range(8):quarter(m,NOW+timedelta(days=i))
    assert m.factor(NOW.replace(month=12),190,35)[0]==1
    assert m.factor(NOW.replace(year=2027),190,35)[0]==1


def test_source_binding_change_clears_incompatible_factors():
    m=PVCalibration(settings())
    for i in range(8):quarter(m,NOW+timedelta(days=i),binding='old')
    quarter(m,NOW+timedelta(days=8),binding='new')
    assert m.counts['source_changed']==1 and m.factor(NOW+timedelta(days=9),190,35)[0]==1

@pytest.mark.parametrize('preset,maximum', [('slow',.025),('normal',.05),('responsive',.075)])
def test_presets_limit_daily_change(preset,maximum):
    m=PVCalibration(settings(learning_preset=preset));prev=1.
    for i in range(12):
        dt=NOW+timedelta(days=i);quarter(m,dt)
        factor=m.factor(dt,190,35)[0];assert abs(factor-prev)<=maximum+1e-8;prev=factor


def test_disable_shadow_retains_global_calibration():
    m=PVCalibration(settings(shadow_enabled=False))
    for i in range(8):quarter(m,NOW+timedelta(days=i))
    assert m.factor(NOW+timedelta(days=8),250,20)[0]<1
    m.settings['calibration_enabled']=False;assert m.factor(NOW,190,35)[0]==1


def test_history_bounded_in_time_and_restore_corrupt_data():
    m=PVCalibration(settings(history_days=2))
    for i in range(8):quarter(m,NOW+timedelta(days=i))
    assert all(datetime.fromisoformat(x["time"]).timestamp() >= datetime.fromisoformat(m.history[-1]["time"]).timestamp()-2*86400 for x in m.history)
    m.restore({'version':1,'bins':{'x':{'days':{'bad':[1],'2026-09-19':[True,'nan',.8]},'factor':float('inf')}},
      'history':[{'time':'2026-09-29T12:00:00+00:00','actual_w':float('nan'),'raw_w':3,'corrected_w':1}, {'time':'bad'}, {'time':'2026-09-01'}],
      'counts':{'accepted':'bad','rejected':2},'revision':'bad'})
    assert len(m.history)==1 and m.history[0]['actual_w'] is None
    json.dumps(m.snapshot(),allow_nan=False);m.summary()

@pytest.mark.parametrize('data',[None,[],{'version':99},{'version':1,'bins':[],'history':{},'counts':[]},{'version':1,'bins':{'x':{'days':[]}}}])
def test_missing_or_future_storage_never_crashes(data):
    m=PVCalibration(settings());m.restore(data);m.summary();json.dumps(m.snapshot(),allow_nan=False)


def test_solar_geometry_bounds_and_invalid_location():
    az,el=solar_position(datetime(2026,6,21,12,tzinfo=UTC),51,4)
    assert 170<az<205 and 55<el<65
    assert solar_position(NOW,None,None)==(None,None)
    assert solar_position(NOW,100,4)==(None,None)


def test_runtime_cache_does_not_poll_or_write_every_tick(monkeypatch):
    r,h,e,now=source_fixture(monkeypatch);h.config=NS(latitude=51,longitude=4,time_zone='Europe/Brussels')
    m=PVForecast(r);calls=[];original=m.source.refresh
    m.source.refresh=lambda t:(calls.append(t),original(t))[1]
    m.update(now)
    for i in range(1,12):m.update(now+timedelta(seconds=i*5))
    assert len(calls)==1 and not h.services.calls and m.cached['available']
    assert m.cached['horizon'][2]['raw_w']==2000
    assert m.cached['native_raw_now_w']==3000


def test_runtime_stale_source_graceful_fallback_no_actuator(monkeypatch):
    r,h,e,now=source_fixture(monkeypatch);m=PVForecast(r);m.update(now)
    h.states.get('sensor.renamed_by_user').state='unavailable';m.update(now+timedelta(minutes=1))
    assert not m.cached['available'] and all(v is None for v in m.hourly(now,4))
    assert not h.services.calls


def test_optional_analysis_exception_never_crashes_control(monkeypatch):
    r,h=build();m=PVForecast(r)
    def fail(*a):raise RuntimeError('private credentials must not leak')
    m.source.refresh=fail;m.update(datetime.now(UTC))
    assert not m.cached['available'] and m.cached['error']=='RuntimeError'
    assert 'private credentials' not in json.dumps(m.cached)


def test_old_optouts_and_explicit_sources_migrate():
    r,h=build();r.entry.options.update(forecast={'enabled':False,'remaining_today_entity':'sensor.my_forecast'},local_pv={'enabled':False})
    m=PVForecast(r)
    assert not m.settings['enabled'] and not m.settings['calibration_enabled']
    assert m.settings['remaining_entity']=='sensor.my_forecast'


def test_sensors_unknown_not_zero_and_not_energy_counters():
    import ast
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/"custom_components/solar_pilot/sensor.py"
    tree=ast.parse(path.read_text(encoding="utf-8"))
    class Base:
        def __init__(self,runtime,*args):self.runtime=runtime
    class Entity:pass
    ns={"SolarEntity":Base,"SensorEntity":Entity,"SensorDeviceClass":NS(POWER="power",ENERGY="energy")}
    exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="PVForecastSensor"],type_ignores=[]),str(path),"exec"),ns)
    PVForecastSensor=ns["PVForecastSensor"]
    r,h=build()
    for suffix,definition in PV_SENSOR_DEFINITIONS.items():
        s=PVForecastSensor(r,suffix,definition)
        assert s.native_value is None and s._attr_state_class is None
    r.pv_forecast.cached={'available':True,'confidence':.75,'horizon':[{'raw_w':1234,'corrected_w':1000}]}
    assert PVForecastSensor(r,'pvf_confidence',PV_SENSOR_DEFINITIONS['pvf_confidence']).native_value==75
    assert PVForecastSensor(r,'pvf_raw_3h',PV_SENSOR_DEFINITIONS['pvf_raw_3h']).native_value is None


def test_forecast_cannot_create_current_free_power(monkeypatch):
    r,h,e,now=source_fixture(monkeypatch);r.pv_forecast.update(now)
    before=r._site_data();r.pv_forecast.cached['horizon'][0]['corrected_w']=999999
    after=r._site_data();assert before[:4]==after[:4]
    assert not h.services.calls
