from custom_components.solar_pilot.battery_analysis import BatteryOpportunitySimulator


def seed():
    return {"source":{"homewizard_start":"2026-05-01","homewizard_end":"2026-09-20"},"grid":{"period_days":143},"battery_upper_bound":{"scenarios":[{"capacity_kwh":10,"power_kw":5,"avoided_import_kwh":1262,"used_export_kwh":1402}]}}


def test_seed_scenario_is_exposed_as_historical():
    b=BatteryOpportunitySimulator({"capacities_kwh":[10],"powers_kw":[5]},seed())
    row=b.overview()["scenarios"][0]
    assert row["historical_avoided_import_kwh"]==1262 and row["avoided_import_kwh"]==1262


def test_live_export_then_import_is_shifted():
    b=BatteryOpportunitySimulator({"capacities_kwh":[10],"powers_kw":[5],"seed_enabled":False,"max_dt_s":1000}, {})
    b.step(900,-4000); b.step(900,4000)
    row=b.overview()["scenarios"][0]
    assert row["live_used_export_kwh"]>0 and row["live_avoided_import_kwh"]>0


def test_battery_analysis_does_not_create_control_action():
    b=BatteryOpportunitySimulator({"capacities_kwh":[5],"powers_kw":[3]},seed())
    o=b.overview(); assert o["advisory_only"] is True and "scenarios" in o


def test_reserve_reduces_usable_virtual_energy():
    a=BatteryOpportunitySimulator({"capacities_kwh":[10],"powers_kw":[10],"seed_enabled":False,"reserve_pct":0,"max_dt_s":4000},{})
    r=BatteryOpportunitySimulator({"capacities_kwh":[10],"powers_kw":[10],"seed_enabled":False,"reserve_pct":50,"max_dt_s":4000},{})
    for b in (a,r): b.step(3600,-10000); b.step(3600,10000)
    assert a.overview()["scenarios"][0]["live_avoided_import_kwh"] > r.overview()["scenarios"][0]["live_avoided_import_kwh"]
