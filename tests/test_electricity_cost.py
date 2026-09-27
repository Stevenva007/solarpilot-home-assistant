from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest
from custom_components.solar_pilot.electricity_cost import DailyElectricityCost
from custom_components.solar_pilot.unified_planner import UnifiedPlanner
TZ=ZoneInfo('Europe/Brussels')
T=datetime(2026,9,27,12,tzinfo=TZ)

def add(ledger,t,grid=1000,pv=0,ip=.30,ep=.03,storage=False):
    return ledger.update(now=t,grid_w=grid,pv_w=pv,import_price=ip,export_price=ep,storage_present=storage)

def test_import_is_costed_without_double_subtracting_self_used_solar():
    l=DailyElectricityCost()
    add(l,T,grid=1000,pv=2000)
    x=add(l,T+timedelta(seconds=120),grid=1000,pv=2000)
    assert x['net_cost_eur']==pytest.approx(.01)
    assert x['pv_avoided_cost_eur']==pytest.approx(.02)
    assert x['direct_pv_kwh']==pytest.approx(2000*120/3_600_000,abs=1e-6)

def test_export_produces_negative_net_cost():
    l=DailyElectricityCost();add(l,T,grid=-1500,pv=3000)
    x=add(l,T+timedelta(seconds=120),grid=-1500,pv=3000)
    assert x['import_cost_eur']==0 and x['export_revenue_eur']==pytest.approx(.0015)
    assert x['net_cost_eur']==pytest.approx(-.0015)
    assert x['direct_pv_kwh']==.05

def test_direction_crossing_never_nets_import_and_export_before_pricing():
    l=DailyElectricityCost();add(l,T,grid=1200,pv=2000)
    x=add(l,T+timedelta(seconds=120),grid=-1200,pv=2000)
    assert x['import_kwh']==x['export_kwh']==.01
    assert x['net_cost_eur']==pytest.approx(.0027)

def test_tariff_change_does_not_reprice_the_previous_period():
    l=DailyElectricityCost();add(l,T,ip=.3)
    add(l,T+timedelta(seconds=60),ip=.5)
    x=add(l,T+timedelta(seconds=120),ip=.5)
    assert x['import_cost_eur']==pytest.approx((.3+.5)/60,abs=1e-6)

def test_negative_prices_remain_negative_not_clamped():
    l=DailyElectricityCost();add(l,T,ip=-.1)
    x=add(l,T+timedelta(seconds=120),ip=-.1)
    assert x['net_cost_eur']==pytest.approx(-.1/30,abs=1e-6)

def test_negative_export_tariff_is_cost_not_credit():
    l=DailyElectricityCost();add(l,T,grid=-1000,ep=-.1)
    x=add(l,T+timedelta(seconds=120),grid=-1000,ep=-.1)
    assert x['net_cost_eur']>0 and x['export_revenue_eur']<0

def test_midnight_does_not_copy_yesterday_into_today():
    l=DailyElectricityCost();t=T.replace(hour=23,minute=59,second=30)
    add(l,t);x=add(l,t+timedelta(seconds=60))
    assert x['date']=='2026-09-28' and x['coverage_s']==30
    assert x['net_cost_eur']==pytest.approx(.0025)

def test_missing_data_and_large_gaps_are_not_free_energy():
    l=DailyElectricityCost();add(l,T)
    x=add(l,T+timedelta(hours=1))
    assert x['net_cost_eur'] is None and x['partial']
    add(l,T+timedelta(hours=1,seconds=30),grid=None)
    x=add(l,T+timedelta(hours=1,seconds=60))
    assert x['net_cost_eur'] is None

def test_restore_preserves_day_totals_without_interpolating_offline_gap():
    l=DailyElectricityCost();add(l,T);x=add(l,T+timedelta(seconds=120))
    fresh=DailyElectricityCost();fresh.restore(l.snapshot())
    y=add(fresh,T+timedelta(hours=3))
    assert x['net_cost_eur']==y['net_cost_eur'] and y['coverage_s']==120

def test_upgrade_keeps_existing_totals_as_explicit_price_estimate():
    l=DailyElectricityCost();l.seed_legacy({'date':T.date().isoformat(),'samples_s':3600,
        'site_import_kwh':10,'site_export_kwh':6,'pv_kwh':11,'pv_self_used_kwh':5},T,.3,.03)
    x=add(l,T)
    assert x['net_cost_eur']==2.82 and x['pv_avoided_cost_eur']==1.5
    assert x['legacy_price_estimate'] and x['partial']

def test_battery_prevents_claiming_direct_solar_without_proven_attribution():
    l=DailyElectricityCost();add(l,T,grid=1000,pv=3000,storage=True)
    x=add(l,T+timedelta(seconds=120),grid=1000,pv=3000,storage=True)
    assert x['net_cost_eur']==.01
    assert x['direct_pv_kwh'] is None and x['pv_avoided_cost_eur'] is None

def test_no_pv_sensor_still_costs_grid_without_fake_solar_zero():
    l=DailyElectricityCost();add(l,T,pv=None);x=add(l,T+timedelta(seconds=120),pv=None)
    assert x['net_cost_eur']==.01 and x['direct_pv_kwh'] is None

def test_disabled_economy_gives_unknown_cost_not_free_electricity():
    l=DailyElectricityCost();add(l,T,ip=None,ep=None)
    x=add(l,T+timedelta(seconds=120),ip=None,ep=None)
    assert x['import_kwh']>0 and x['net_cost_eur'] is None

def test_horizon_cost_breakdown_matches_existing_net_forecast():
    p=UnifiedPlanner({'horizon_h':6,'slot_min':15,'base_load_learning':False})
    x=p.build(local_now=T,pv_hourly_w=[4000,3000,2000,0,0,0],import_prices=[.30]*24,export_prices=[.03]*24,devices=[])
    d=x.overview()['cost_breakdown']
    assert d['import_cost_eur']-d['export_revenue_eur']==pytest.approx(x.predicted_cost_eur,abs=1e-5)
    assert x.predicted_export_kwh>0 and d['export_revenue_eur']>0

@pytest.mark.parametrize('day', [(2026,3,29),(2026,10,25)])
def test_coverage_uses_elapsed_seconds_on_dst_days(day):
    t=datetime(*day,12,tzinfo=TZ);l=DailyElectricityCost()
    add(l,t);x=add(l,t+timedelta(seconds=120))
    assert x['coverage_s']==120 and x['partial']
