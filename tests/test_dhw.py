"""Boiler policy tests; fictional measurements, no physical hardware."""
from datetime import datetime
import pytest
from custom_components.solar_pilot.dhw import (
    DHW_DEFAULTS, DHWPolicy, DHWReading, cooling_state, night_active,
    validate_settings, effective_base_target, hygiene_schedule_active,
)


def make(**settings):
    return DHWPolicy({**DHW_DEFAULTS, "rise_delay_s": 0, "fall_delay_s": 0,
                      "cooling_clear_s": 0, **settings})


def evaluate(p=None, now=100, hour=12, temp=44, actual=49, pv=0, export=0,
             grid=0, cooling=False, before=None, holding=False, protected=False,
             date=(2026, 9, 22)):
    # Tuesday by default: avoids the configured Monday 12:00 factory hygiene window.
    p = p or make()
    r = DHWReading(temp, actual, pv, export, before, grid, cooling, protected, "Hygiëne actief")
    return p.update(now, datetime(*date, hour, 0), r, holding)


BASE = effective_base_target(DHW_DEFAULTS)


@pytest.mark.parametrize('pv,export,hour,cooling,target',[
    (0,0,2,False,49),(800,0,12,False,49),(999,0,12,False,49),
    (1000,0,12,False,50),(1600,0,12,True,50),(5000,3500,12,False,50),
    (5000,3500.1,12,False,60),(6000,5000,12,True,50),
    (6000,5000,12,None,50),(6000,5000,2,False,49),
    (0,0,12,True,49),(0,0,2,True,49),
    (None,None,12,False,49),(2000,None,12,False,50),
])
def test_requested_matrix(pv,export,hour,cooling,target):
    assert evaluate(pv=pv,export=export,hour=hour,cooling=cooling).target_c == target


def test_minimum_semantics_accounts_for_physical_deadband():
    assert BASE == 49
    assert BASE + DHW_DEFAULTS["tank_differential_c"] == 44
    assert DHW_DEFAULTS["minimum_c"] == 43


def test_solar_rule_is_production_not_export_and_may_import():
    assert evaluate(pv=1000,grid=2500).target_c == 50


def test_below_minimum_forces_minimum_regime_but_not_high_goal():
    d=evaluate(temp=41, hour=2)
    assert d.target_c == 49 and d.low_temperature and d.night


def test_no_cooling_does_not_mean_forced_60():
    assert evaluate(pv=4000,export=2000).target_c == 50


def test_rise_must_be_continuous():
    p=make(rise_delay_s=60)
    assert evaluate(p,now=0,pv=2000).target_c == 49
    assert evaluate(p,now=20,pv=2000).target_c == 49
    assert evaluate(p,now=30,pv=0).target_c == 49
    assert evaluate(p,now=40,pv=2000).remaining_s == 60
    for t in (60,80): evaluate(p,now=t,pv=2000)
    assert evaluate(p,now=100,pv=2000).target_c == 50


def test_gap_does_not_count_as_sunshine():
    p=make(rise_delay_s=60)
    evaluate(p,now=0,pv=2000)
    assert evaluate(p,now=100,pv=2000).target_c == 49


def test_night_and_cooling_bypass_long_solar_fall_delay():
    p=make(fall_delay_s=1000)
    assert evaluate(p,pv=5000,export=4000).target_c == 60
    assert evaluate(p,now=105,pv=5000,export=4000,cooling=True).target_c == 50
    assert evaluate(p,now=110,hour=2,pv=5000,export=4000).target_c == 49


def test_cooling_clear_hold():
    p=make(cooling_clear_s=60)
    evaluate(p,now=0,pv=5000,export=4000,cooling=True)
    for t in (20,40):
        assert evaluate(p,now=t,pv=5000,export=4000).target_c == 50
    assert evaluate(p,now=60,pv=5000,export=4000).target_c == 60


def test_unknown_cooling_also_extends_hold():
    p=make(cooling_clear_s=60)
    evaluate(p,now=0,pv=5000,export=4000,cooling=None)
    for t in (20,40): evaluate(p,now=t,pv=5000,export=4000)
    assert evaluate(p,now=60,pv=5000,export=4000).target_c == 60


def test_hygiene_has_no_target_even_at_night_or_with_cooling():
    d=evaluate(pv=5000,export=4000,hour=2,cooling=True,protected=True)
    assert d.target_c is None and d.stage == 'protected'


def test_factory_hygiene_guard_matches_monday_schedule_and_wraps_safely():
    c={**DHW_DEFAULTS,"hygiene_guard_before_s":900,"hygiene_guard_after_s":10800}
    assert hygiene_schedule_active(c, datetime(2026,9,21,11,45))
    assert hygiene_schedule_active(c, datetime(2026,9,21,14,59))
    assert not hygiene_schedule_active(c, datetime(2026,9,21,15,1))
    assert not hygiene_schedule_active(c, datetime(2026,9,22,12,0))


@pytest.mark.parametrize('temp,actual',[(None,49),(44,None),(None,None)])
def test_missing_temperature_or_target_no_request(temp,actual):
    assert evaluate(temp=temp,actual=actual,pv=5000,export=4000).target_c is None


def test_before_boiler_cannot_start_high_stage():
    assert evaluate(pv=5000,export=0,before=5000,holding=True).target_c == 50


def test_compensation_only_holds_existing_owned_high():
    p=make()
    assert evaluate(p,pv=5000,export=4000).target_c == 60
    assert evaluate(p,now=105,pv=5000,export=500,before=4000,holding=True).target_c == 60
    assert evaluate(p,now=110,pv=5000,export=500,before=4000,holding=False).target_c == 50


def test_excess_import_cancels_high_even_with_compensation():
    p=make()
    evaluate(p,pv=5000,export=4000)
    assert evaluate(p,now=105,pv=5000,export=0,before=4000,holding=True,grid=500).target_c == 50


def test_compensation_can_be_disabled():
    p=make(compensate_own_power=False)
    evaluate(p,pv=5000,export=4000)
    assert evaluate(p,now=105,pv=5000,export=500,before=4000,holding=True).target_c == 50


def test_pv_hysteresis_only_after_entering_solar_stage():
    p=make()
    assert evaluate(p,pv=950).target_c == 49
    assert evaluate(p,now=105,pv=1000).target_c == 50
    assert evaluate(p,now=110,pv=950).target_c == 50
    assert evaluate(p,now=115,pv=899).target_c == 49


def test_capacity_guard_delays_optional_50_but_never_minimum_recovery():
    p=make()
    r=DHWReading(46,49,2000,0,None,1500,False,False,"",500)
    d=p.update(100,datetime(2026,9,22,12),r)
    assert d.target_c==49 and d.capacity_block
    p=make()
    r=DHWReading(42,49,2000,0,None,1500,False,False,"",500)
    d=p.update(100,datetime(2026,9,22,12),r)
    assert d.target_c==50 and d.low_temperature and not d.capacity_block


@pytest.mark.parametrize('state,attrs,result',[
    ('cool',{'hvac_action':'cooling'},True),
    ('cool',{'hvac_action':'idle'},False),
    ('cool',{},True),('auto',{},None),
    ('auto',{'hvac_action':'cooling'},True),
    ('off',{},False),('heat',{},False),('unavailable',{},None),
    ('on',{},True),('unknown',{},None),
])
def test_cooling_detection(state,attrs,result):
    assert cooling_state(state,attrs) is result


def test_mode_detection_blocks_idle_cool_mode():
    assert cooling_state('cool',{'hvac_action':'idle'},'mode') is True


@pytest.mark.parametrize('hour,expected',[(0,True),(5,True),(6,False),(22,False),(23,True)])
def test_night_boundaries(hour,expected):
    assert night_active(DHW_DEFAULTS,datetime(2026,9,22,hour)) is expected


def test_custom_day_window_and_disabled():
    c={**DHW_DEFAULTS,'night_start':'09:00','night_end':'17:00'}
    assert night_active(c,datetime(2026,9,22,10))
    assert not night_active(c,datetime(2026,9,22,23))
    c['night_enabled']=False
    assert not night_active(c,datetime(2026,9,22,10))


@pytest.mark.parametrize('patch',[
 {'minimum_c':55},{'tank_differential_c':-12,'minimum_c':55},
 {'cooling_cap_c':40},{'surplus_c':45},{'minimum_c':float('nan')},
 {'solar_c':50.3},{'night_start':'24:00'},{'night_end':'23:00'},
 {'night_start':'23:00:15'},{'pv_hysteresis_w':2000},
 {'surplus_hysteresis_w':4000}, {'cooling_detection':'invented'},
 {'hygiene_weekdays':'7'}, {'hygiene_target_c':50},
])
def test_invalid_settings_rejected(patch):
    assert validate_settings({**DHW_DEFAULTS,**patch})


def test_all_requested_values_adjustable():
    c={**DHW_DEFAULTS,'minimum_c':42,'tank_differential_c':-5,'minimum_buffer_c':1,
       'solar_c':52,'surplus_c':58,'cooling_cap_c':51,
       'pv_threshold_w':1200,'surplus_threshold_w':4000,'rise_delay_s':0,'fall_delay_s':0,'cooling_clear_s':0}
    p=make(**c)
    assert effective_base_target(p.settings)==48
    assert evaluate(p,pv=1200,export=0,cooling=True).target_c == 51


def test_reported_cooling_overrides_contradictory_off_mode():
    assert cooling_state("off", {"hvac_action": "cooling"}) is True


@pytest.mark.parametrize("key,value", [("rise_delay_s",float("nan")),("ack_timeout_s",0),
    ("fall_delay_s",-1),("cooling_clear_s",9999),("stale_s",2),
    ("max_surplus_import_w",float("inf")),("pv_hysteresis_w",-5),
    ("surplus_hysteresis_w",float("nan")),("hygiene_guard_after_s",20)])
def test_invalid_timing_and_hysteresis_fail_closed(key,value):
    assert key in validate_settings({**DHW_DEFAULTS,key:value})
