from custom_components.solar_pilot.battery_fleet import (
    BatteryReading, aggregate, recommend, BATTERY_FLEET_DEFAULTS
)


def r(i, soc, power=0, controllable=True, cap=10, charge=5000, discharge=5000):
    return BatteryReading(i, i, True, soc, power, cap, 5, 15, 95, charge, discharge, controllable, 'three_phase')


def test_aggregate_multiple_batteries_capacity_weighted_soc_and_power():
    a=aggregate([r('a',20,1000,cap=5), r('b',80,-500,cap=15)])
    assert a['capacity_kwh']==20
    assert a['soc_pct']==65
    assert a['power_w']==500
    assert a['discharge_w']==1000 and a['charge_w']==500


def test_recommend_charges_only_from_residual_export_by_default():
    d=recommend({**BATTERY_FLEET_DEFAULTS,'enabled':True,'charge_reserve_w':200}, [r('a',40)], -2200)
    assert d.valid and d.total_target_w==-2000
    assert d.allocations['a']==-2000


def test_recommend_discharges_on_import_but_keeps_reserve_margin():
    d=recommend({**BATTERY_FLEET_DEFAULTS,'enabled':True,'discharge_reserve_w':150}, [r('a',80)], 2150)
    assert d.total_target_w==2000


def test_low_soc_battery_is_not_discharged():
    d=recommend({**BATTERY_FLEET_DEFAULTS,'enabled':True}, [r('a',14)], 3000)
    assert d.total_target_w==0


def test_charge_balancing_prefers_low_soc_battery():
    d=recommend({**BATTERY_FLEET_DEFAULTS,'enabled':True,'charge_reserve_w':0},
                [r('low',20,charge=2000), r('high',80,charge=2000)], -3000)
    assert d.allocations['low']==-2000
    assert d.allocations['high']==-1000


def test_capacity_budget_can_request_more_discharge():
    d=recommend({**BATTERY_FLEET_DEFAULTS,'enabled':True,'discharge_reserve_w':2000,'strategy':'hybrid'}, [r('a',80)], 4000, 2500)
    assert d.total_target_w>=1500


def test_read_only_battery_still_gets_useful_advisory_target_without_control_allocation():
    x=r('a',50,controllable=False)
    d=recommend({**BATTERY_FLEET_DEFAULTS,'enabled':True,'charge_reserve_w':0}, [x], -1800)
    assert d.total_target_w == -1800
    assert d.allocations['a'] == -1800
    assert d.control_allocations['a'] == 0


def test_mixed_fleet_control_allocation_uses_only_explicitly_controllable_batteries():
    ro=r('readonly',20,controllable=False,charge=5000)
    ctl=r('control',40,controllable=True,charge=5000)
    d=recommend({**BATTERY_FLEET_DEFAULTS,'enabled':True,'charge_reserve_w':0}, [ro,ctl], -3000)
    assert d.total_target_w == -3000
    assert d.control_allocations['readonly'] == 0
    assert d.control_allocations['control'] == -3000
