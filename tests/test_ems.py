from datetime import datetime
import pytest
from types import SimpleNamespace
from custom_components.solar_pilot.ems import CAPACITY_DEFAULTS, capacity_decision, quarter_elapsed_s
from test_runtime import build
from homeassistant.exceptions import HomeAssistantError


def cfg(**kw):
    return {**CAPACITY_DEFAULTS, "enabled": True, **kw}


def test_quarter_elapsed_uses_local_tariff_quarters():
    assert quarter_elapsed_s(datetime(2026,9,22,10,0,0)) == 0
    assert quarter_elapsed_s(datetime(2026,9,22,10,7,30)) == 450
    assert quarter_elapsed_s(datetime(2026,9,22,10,14,59)) == 899
    assert quarter_elapsed_s(datetime(2026,9,22,10,15,0)) == 0


def test_capacity_formula_limits_remaining_quarter_import():
    d=capacity_decision(datetime(2026,9,22,10,7,30),3000,3000,2500,
                        cfg(target_peak_w=3500, margin_w=100, adaptive_to_month_peak=False))
    assert d.valid and d.allowed_grid_w == pytest.approx(3800)
    assert d.optional_headroom_w == pytest.approx(1300)


def test_capacity_adapts_to_already_incurred_month_peak():
    d=capacity_decision(datetime(2026,9,22,10,7,30),4000,5549,2500,
                        cfg(target_peak_w=3500, margin_w=100, adaptive_to_month_peak=True))
    assert d.effective_target_w == 5549
    assert d.allowed_grid_w > 5000


def test_capacity_can_keep_fixed_lower_target_when_user_disables_adaptation():
    d=capacity_decision(datetime(2026,9,22,10,7,30),4000,5549,2500,
                        cfg(target_peak_w=3500, margin_w=100, adaptive_to_month_peak=False))
    assert d.effective_target_w == 3500
    assert d.allowed_grid_w < 3000


def test_capacity_early_quarter_is_conservative_not_overfitted():
    d=capacity_decision(datetime(2026,9,22,10,0,30),100,3000,2800,
                        cfg(target_peak_w=3500, margin_w=100, minimum_elapsed_s=60))
    assert d.allowed_grid_w is None
    assert d.optional_headroom_w == 600


def test_capacity_missing_data_fails_closed_for_optional_grid_load():
    d=capacity_decision(datetime(2026,9,22,10,8),None,3000,2000,cfg())
    assert not d.valid and d.optional_headroom_w == 0


@pytest.mark.asyncio
async def test_legacy_controller_blocks_solar_mode_until_disabled():
    r,h=build()
    h.states.set('switch.pv_excess_control_control_enabled','on')
    with pytest.raises(HomeAssistantError):
        await r.set_mode('solar')
    h.states.set('switch.pv_excess_control_control_enabled','off')
    await r.set_mode('solar')
    assert r.mode=='solar'




def test_economy_and_forecast_overview_is_advisory_and_keeps_real_price_spread():
    r,h=build()
    h.states.set('input_number.buy',0.30,{'unit_of_measurement':'EUR/kWh'})
    h.states.set('input_number.sell',0.03,{'unit_of_measurement':'EUR/kWh'})
    h.states.set('sensor.this_hour',1.0,{'unit_of_measurement':'kWh'})
    h.states.set('sensor.next_hour',2.0,{'unit_of_measurement':'kWh'})
    r.economy_settings.update({'enabled':True,'import_price_entity':'input_number.buy','export_price_entity':'input_number.sell'})
    r.forecast_settings.update({'enabled':True,'current_hour_entity':'sensor.this_hour','next_hour_entity':'sensor.next_hour','stale_s':7200})
    o=r.ems_overview()
    assert o['economy']['self_use_value_eur_kwh'] == pytest.approx(0.27)
    assert not any('volgend uur' in x for x in o['advice'])  # oude losse één-uurregel is verwijderd

from custom_components.solar_pilot.ems import (
    PHASE_DEFAULTS, PLANNER_DEFAULTS, accounting_step, phase_decision, planner_decision,
)


def test_capacity_respects_optional_billing_floor():
    d=capacity_decision(datetime(2026,9,22,10,7,30),1000,1000,500,
                        cfg(target_peak_w=1500, billing_floor_w=2500,
                            respect_billing_floor=True, adaptive_to_month_peak=False, margin_w=100))
    assert d.effective_target_w == 2500
    d2=capacity_decision(datetime(2026,9,22,10,7,30),1000,1000,500,
                         cfg(target_peak_w=1500, billing_floor_w=2500,
                             respect_billing_floor=False, adaptive_to_month_peak=False, margin_w=100))
    assert d2.effective_target_w == 1500


def test_phase_monitor_is_advisory_by_default():
    d=phase_decision((5000, 1000, 1000), {**PHASE_DEFAULTS, 'enabled':True, 'limit_w':5500,
                                          'margin_w':300, 'start_headroom_w':500})
    assert d.valid and d.headroom_w == pytest.approx(200)
    assert not d.block_increase and not d.release_flexible


def test_phase_control_can_block_start_and_shed_only_when_explicit():
    base={**PHASE_DEFAULTS, 'enabled':True, 'limit_w':5500, 'margin_w':300,
          'start_headroom_w':500, 'control_starts':True, 'shed_on_overlimit':True}
    d=phase_decision((5000,1000,1000),base)
    assert d.block_increase and not d.release_flexible
    d=phase_decision((5700,1000,1000),base)
    assert d.block_increase and d.release_flexible


def test_phase_missing_data_fails_closed_only_if_control_enabled():
    d=phase_decision((None,1000,1000), {**PHASE_DEFAULTS,'enabled':True,'control_starts':True})
    assert not d.valid and d.block_increase


def test_planner_defers_opted_in_start_for_clearly_better_solar_hour():
    d=planner_decision(settings={**PLANNER_DEFAULTS,'enabled':True,'forecast_gain_kwh':0.5},
        deferrable=True,current_hour_kwh=0.4,next_hour_kwh=1.2,remaining_today_kwh=5,
        required_energy_kwh=1,deadline_s=7200)
    assert d.hold_start and 'uitgesteld' in d.reason


def test_planner_never_defers_urgent_or_running_load():
    args=dict(settings=PLANNER_DEFAULTS,deferrable=True,current_hour_kwh=0.2,next_hour_kwh=2,
              remaining_today_kwh=5,required_energy_kwh=1,deadline_s=7200)
    assert not planner_decision(**args, urgent=True).hold_start
    assert not planner_decision(**args, already_on=True).hold_start


def test_planner_stops_deferral_after_max_wait_or_near_deadline():
    c={**PLANNER_DEFAULTS,'max_deferral_s':1800,'deadline_guard_s':600}
    args=dict(settings=c,deferrable=True,current_hour_kwh=0.2,next_hour_kwh=2,
              remaining_today_kwh=5,required_energy_kwh=1)
    assert not planner_decision(**args, hold_elapsed_s=1800, deadline_s=7200).hold_start
    assert not planner_decision(**args, hold_elapsed_s=0, deadline_s=2000).hold_start


def test_cheap_grid_permission_needs_price_device_permission_and_shortfall():
    c={**PLANNER_DEFAULTS,'early_grid_enabled':True,'cheap_grid_limit_eur_kwh':0.15,
       'early_grid_requires_forecast_shortfall':True}
    d=planner_decision(settings=c,deferrable=False,cheap_grid_allowed=True,
        remaining_today_kwh=0.2,required_energy_kwh=1,import_price_eur_kwh=0.10)
    assert d.allow_early_grid
    assert not planner_decision(settings=c,deferrable=False,cheap_grid_allowed=False,
        remaining_today_kwh=0.2,required_energy_kwh=1,import_price_eur_kwh=0.10).allow_early_grid
    assert not planner_decision(settings=c,deferrable=False,cheap_grid_allowed=True,
        remaining_today_kwh=3,required_energy_kwh=1,import_price_eur_kwh=0.10).allow_early_grid


def test_daily_accounting_resets_on_new_day_and_is_conservative():
    s=accounting_step({},day='2026-09-21',dt_s=60,grid_w=-1000,pv_w=4000,managed_w=2000,
                      battery_discharge_w=0,import_price_eur_kwh=.30,export_price_eur_kwh=.03)
    assert s['site_export_kwh'] == pytest.approx(1/60)
    assert s['pv_kwh'] == pytest.approx(4/60)
    assert s['managed_solar_kwh'] == pytest.approx(2/60)
    assert s['estimated_value_eur'] == pytest.approx(.009)
    s2=accounting_step(s,day='2026-09-22',dt_s=60,grid_w=1000,pv_w=0,managed_w=500,
                       import_price_eur_kwh=.30,export_price_eur_kwh=.03)
    assert s2['date']=='2026-09-22' and s2['site_export_kwh']==0

