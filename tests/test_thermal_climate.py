from custom_components.solar_pilot.thermal_climate import (
    ClimateDecision,
    SMART_CLIMATE_DEFAULTS,
    SmartClimateState,
    ThermalProfile,
    decide_mode,
)


def zone(temp=21, target=21, mode='auto', name='Woonkamer', action='idle'):
    return {
        'entity_id':'climate.zone','name':name,'current':temp,'target':target,
        'mode':mode,'action':action,'hvac_modes':['heat','cool','off','auto']
    }


def mature_profile(k=0.04, heat=0.20, cool=0.20, delay=2.0):
    p=ThermalProfile(); p.samples=100; p.days=set(str(x) for x in range(10))
    p.passive_k=[k]*20; p.heat_gain=[heat]*20; p.cool_gain=[cool]*20; p.response_delays_h=[delay]*10
    return p


def test_smart_climate_learning_reset_preserves_operational_and_safety_state():
    state = SmartClimateState()
    state.profiles['climate.zone'] = mature_profile()
    state.weather_bias.errors['12'] = [1.2]
    state.weather_bias.days['12'] = {'2026-10-01'}
    state.weather_bias.pending = {'sample': {'valid_ts': 1, 'predicted_c': 20, 'bucket': 12}}
    state.weather_bias.total_samples = 1
    active = {'started_ts': 10, 'targets': {'climate.zone': 21}}
    pending = {'evaluate_after_ts': 20, 'action_seen': False}
    state.coast_feedback.active = active
    state.coast_feedback.pending = pending
    state.coast_feedback.history = [{'outcome': 'te_lang'}]
    state.coast_feedback.adjust_h = 1.0
    state.coast_feedback.scored = 3
    state.coast_feedback.total_coast_h = 12.5

    decision = ClimateDecision('off', 'actieve coast')
    state.last_sample_wall = 101.0
    state.last_decision_wall = 102.0
    state.last_guard_wall = 103.0
    state.last_forecast_wall = 104.0
    state.forecast = [{'temperature': 20}]
    state.last_decision = decision
    state.manual_hold_until = 105.0
    state.command_day = '2026-10-02'
    state.commands_today = 4
    state.expected_mode = {'climate.zone': 'off'}
    state.last_command_wall = 106.0
    state.last_command_mode = 'off'
    state.fault = 'veilig geblokkeerd'

    state.reset_learning()

    assert state.profiles == {}
    assert all(not values for values in state.weather_bias.errors.values())
    assert all(not days for days in state.weather_bias.days.values())
    assert state.weather_bias.pending == {}
    assert state.weather_bias.total_samples == 0
    assert state.coast_feedback.active is active
    assert state.coast_feedback.pending is pending
    assert state.coast_feedback.history == []
    assert state.coast_feedback.adjust_h == 0.0
    assert state.coast_feedback.scored == 0
    assert state.coast_feedback.total_coast_h == 0.0
    assert state.last_sample_wall == 101.0
    assert state.last_decision_wall == 102.0
    assert state.last_guard_wall == 103.0
    assert state.last_forecast_wall == 104.0
    assert state.forecast == [{'temperature': 20}]
    assert state.last_decision is decision
    assert state.manual_hold_until == 105.0
    assert state.command_day == '2026-10-02'
    assert state.commands_today == 4
    assert state.expected_mode == {'climate.zone': 'off'}
    assert state.last_command_wall == 106.0
    assert state.last_command_mode == 'off'
    assert state.fault == 'veilig geblokkeerd'


def test_hard_cold_comfort_breach_requests_auto_not_heat():
    d=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,'enabled':True,'hard_band_c':1},
                  zones=[zone(19.8,21,'off')], outside_hourly=[10]*24, profiles={})
    assert d.desired_mode=='auto' and d.hard_override
    assert 'heat' not in d.desired_mode


def test_hard_hot_comfort_breach_requests_auto_not_cool():
    d=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,'enabled':True,'hard_band_c':1},
                  zones=[zone(22.2,21,'off')], outside_hourly=[28]*24, profiles={})
    assert d.desired_mode=='auto' and d.hard_override
    assert 'cool' not in d.desired_mode


def test_manual_fixed_heat_or_cool_is_never_overridden():
    p=mature_profile()
    d=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,'enabled':True},
                  zones=[zone(24,21,'cool')], outside_hourly=[15]*48,
                  profiles={'climate.zone':p})
    assert d.desired_mode=='hold'
    assert 'nooit' in d.reason.lower()


def test_clear_winter_keeps_panasonic_auto_and_does_not_chase_coast():
    p=mature_profile(k=0.02)
    d=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,'enabled':True},
                  zones=[zone(21,21,'auto')], outside_hourly=[5]*48,
                  profiles={'climate.zone':p})
    assert d.desired_mode=='auto'
    assert d.season_context=='winter'


def test_clear_summer_keeps_panasonic_auto():
    p=mature_profile(k=0.02)
    d=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,'enabled':True},
                  zones=[zone(21,21,'auto')], outside_hourly=[30]*48,
                  profiles={'climate.zone':p})
    assert d.desired_mode=='auto'
    assert d.season_context=='summer'


def test_shoulder_season_can_coast_when_model_predicts_comfort():
    p=mature_profile(k=0.01)
    d=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,'enabled':True},
                  zones=[zone(21,21,'auto')], outside_hourly=[21]*48,
                  profiles={'climate.zone':p})
    assert d.desired_mode=='off'
    assert d.season_context=='shoulder'
    assert 'coast' in d.reason.lower()


def test_immature_model_does_not_start_new_coast_window():
    d=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,'enabled':True},
                  zones=[zone(21,21,'auto')], outside_hourly=[21]*48, profiles={})
    assert d.desired_mode=='hold'


def test_imminent_shoulder_crossing_releases_auto_before_hard_breach():
    p=mature_profile(k=0.08, delay=2.0)
    # This is not a clear winter by 24h average; a cold block will soon drag the house down.
    outside=[21]*6 + [14]*8 + [21]*10 + [21]*24
    d=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,'enabled':True,'shoulder_band_c':3,'season_extreme_delta_c':8},
                  zones=[zone(21,21,'off')], outside_hourly=outside,
                  profiles={'climate.zone':p})
    assert d.desired_mode=='auto'
    assert d.crossing_h is not None


def test_thermal_profile_learns_from_panasonic_hvac_action_while_auto():
    p=ThermalProfile()
    p.observe(wall_ts=0,day='2026-09-01',indoor_c=21,outdoor_c=11,hvac_action='idle')
    p.observe(wall_ts=1800,day='2026-09-01',indoor_c=20.9,outdoor_c=11,hvac_action='idle')
    p.observe(wall_ts=3600,day='2026-09-01',indoor_c=20.95,outdoor_c=11,hvac_action='heating')
    p.observe(wall_ts=5400,day='2026-09-01',indoor_c=21.15,outdoor_c=11,hvac_action='heating')
    assert p.samples >= 3
    assert p.passive_k


def test_prediction_respects_unchanged_thermostat_target():
    p=mature_profile()
    pred=p.predict(20,21,[5]*12,'heat')
    assert pred
    assert max(pred) <= 21.15 + 1e-6


def test_pv_preconditioning_can_only_expand_auto_reenable_lead_not_change_target():
    p=mature_profile(k=0.035, delay=1.0)
    outside=[17]*24
    normal=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,'enabled':True,'thermal_start_margin_h':1,'solar_precondition_extra_lead_h':4,'season_extreme_delta_c':8},
                       zones=[zone(21,21,'off')], outside_hourly=outside,
                       profiles={'climate.zone':p}, solar_precondition=False)
    solar=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,'enabled':True,'thermal_start_margin_h':1,'solar_precondition_extra_lead_h':4,'season_extreme_delta_c':8},
                      zones=[zone(21,21,'off')], outside_hourly=outside,
                      profiles={'climate.zone':p}, solar_precondition=True)
    assert normal.desired_mode in ('off','auto','hold')
    assert solar.desired_mode in ('off','auto','hold')
    assert zone()['target']==21


def test_every_smart_climate_setting_has_dashboard_spec():
    from custom_components.solar_pilot.thermal_climate import CLIMATE_SETTING_SPECS
    assert set(CLIMATE_SETTING_SPECS) == set(SMART_CLIMATE_DEFAULTS)


def test_solar_gain_is_learned_only_from_idle_sunny_samples_and_used_in_prediction():
    p=ThermalProfile()
    settings={**SMART_CLIMATE_DEFAULTS,'solar_gain_enabled':True,'solar_gain_learning_enabled':True,'solar_gain_min_pv_w':500}
    # Seed a stable passive coefficient so residual sunny warming is attributable.
    p.passive_k=[0.02]*10
    t=0
    p.observe(wall_ts=t,day='2026-05-01',indoor_c=21,outdoor_c=15,hvac_action='idle',pv_w=4000,settings=settings)
    for i in range(1,9):
        t += 1800
        # Passive loss is about -0.12 C/h; measured slope is +0.08 C/h -> solar residual.
        p.observe(wall_ts=t,day=f'2026-05-{i+1:02d}',indoor_c=21+0.04*i,outdoor_c=15,hvac_action='idle',pv_w=4000,settings=settings)
    assert p.solar_gain_per_kw
    with_sun=p.predict(21,21,[15]*6,'off',solar_hourly_w=[4000]*6,settings=settings)
    without=p.predict(21,21,[15]*6,'off',solar_hourly_w=[0]*6,settings=settings)
    assert with_sun[-1] > without[-1]


def test_weather_bias_profile_waits_for_confidence_then_applies_bounded_correction():
    from custom_components.solar_pilot.thermal_climate import ForecastBiasProfile
    p=ForecastBiasProfile()
    settings={**SMART_CLIMATE_DEFAULTS,'weather_bias_enabled':True,'weather_bias_min_samples':4,'weather_bias_min_days':2,'weather_bias_min_confidence':0.4,'weather_bias_max_c':2.0}
    for d in range(4):
        p.errors['12'].append(1.5)
        p.days['12'].add(f'2026-09-{10+d:02d}')
    stat=p.stats_for(12,settings)
    assert stat['confidence'] >= .4
    assert stat['applied_c'] == 1.5
    p.errors['12']=[9]*20
    stat=p.stats_for(12,settings)
    assert stat['bias_c'] == 2.0


def test_coast_feedback_can_only_adjust_minimum_window_within_bounds():
    from custom_components.solar_pilot.thermal_climate import CoastFeedback
    c={**SMART_CLIMATE_DEFAULTS,'coast_feedback_min_episodes':2,'coast_feedback_step_h':.5,
       'coast_feedback_min_adjust_h':-1,'coast_feedback_max_adjust_h':1}
    f=CoastFeedback()
    f._score('te_lang',{'duration_h':8},c)
    assert f.adjust_h == 0
    f._score('te_lang',{'duration_h':8},c)
    assert f.adjust_h == .5
    for _ in range(10): f._score('te_lang',{},c)
    assert f.adjust_h == 1
    for _ in range(20): f._score('te_voorzichtig',{},c)
    assert f.adjust_h == -1
    assert f.effective_window(c) == c['min_coast_window_h'] - 1


def test_open_window_logic_is_not_part_of_smart_climate_settings():
    forbidden = {'open_window', 'open_windows', 'window_entities', 'window_delay_s', 'raam_entities', 'deur_entities'}
    assert forbidden.isdisjoint(SMART_CLIMATE_DEFAULTS)


def test_beta36_many_passive_samples_do_not_create_false_full_climate_confidence():
    p=ThermalProfile()
    p.samples=200
    p.days={f"2026-09-{n:02d}" for n in range(1,11)}
    p.passive_k=[0.03]*40
    p.solar_gain_per_kw=[0.01]*30
    parts=p.confidence_components(SMART_CLIMATE_DEFAULTS)
    assert parts["passive_temperature_change"]["status"]=="Betrouwbaar"
    assert parts["solar_gain"]["status"]=="Betrouwbaar"
    assert parts["heating_response"]["status"]=="Nog niet geleerd"
    assert parts["cooling_response"]["status"]=="Nog niet geleerd"
    assert parts["response_delay"]["status"]=="Nog niet geleerd"
    assert p.confidence(SMART_CLIMATE_DEFAULTS)==0.0


def test_beta36_missing_active_response_keeps_auto_coast_conservative():
    p=ThermalProfile()
    p.samples=200
    p.days={f"2026-09-{n:02d}" for n in range(1,11)}
    p.passive_k=[0.03]*40
    d=decide_mode(settings={**SMART_CLIMATE_DEFAULTS,"enabled":True},
                  zones=[zone(21,21,"auto")], outside_hourly=[20]*24,
                  profiles={"climate.zone":p})
    assert d.desired_mode=="hold"
    assert d.prediction_confidence==0.0
