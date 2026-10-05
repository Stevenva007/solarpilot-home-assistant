"""Demand-led room control never invents thermal mass or forecast evidence."""
from copy import deepcopy
import math
import time

import pytest

from custom_components.solar_pilot.thermal_climate import (
    CLIMATE_SETTING_SPECS, SMART_CLIMATE_DEFAULTS, ThermalProfile, decide_mode, decide_zone,
)


SETTINGS = {**SMART_CLIMATE_DEFAULTS, "enabled": True, "solar_gain_enabled": False}
DAYS = {f"2026-10-{day:02d}" for day in range(1, 6)}


def room(current=21., *, target=21., mode="off", action="off"):
    return {"entity_id": "climate.room", "name": "Room", "current": current,
            "target": target, "mode": mode, "action": action,
            "hvac_modes": ["auto", "off", "heat", "cool"]}


def trained(*, k=.02, heat=.8, cool=.8, delay=2., solar=.01):
    p = ThermalProfile(passive_k=[k] * 24, heat_gain=[heat] * 12, cool_gain=[cool] * 12,
                       heating_delays_h=[delay] * 5, cooling_delays_h=[delay] * 5,
                       response_delays_h=[delay] * 10, solar_gain_per_kw=[solar] * 24,
                       samples=300, days=set(DAYS))
    p.component_days = {key: set(DAYS) for key in p.directional_evidence(SETTINGS)}
    p.validation_errors = {key: [.01] * 12 for key in ("passive", "heating", "cooling")}
    p.validation_horizons = {key: [.25] * 12 for key in ("passive", "heating", "cooling")}
    return p


def decide(current=21., *, outside=14.5, forecast=None, profile=None, settings=None,
           mode="off", action="off", solar=None):
    return decide_zone(settings={**SETTINGS, **(settings or {})},
                       zone=room(current, mode=mode, action=action),
                       outside_hourly=[outside] * 48 if forecast is None else forecast,
                       profile=ThermalProfile() if profile is None else profile,
                       outside_c=outside, solar_hourly_w=solar)


@pytest.mark.parametrize("current,outside,desired,direction,urgent", [
    (21., 14.5, "off", "", False),
    (22., 14.5, "off", "", False),
    (23., 14.5, "off", "", False),
    (19., 30., "off", "", False),
    (20.4, 14.5, "auto", "heating", False),
    (19.9, 14.5, "auto", "heating", True),
    (21.6, 30., "auto", "cooling", False),
    (23., 40., "auto", "cooling", True),
])
def test_measured_demand_works_during_learning_and_is_directional(current, outside, desired, direction, urgent):
    d = decide(current, outside=outside)
    assert d.stage == "reactive" and d.desired_mode == desired
    assert d.comfort_direction == direction and d.urgent_auto is urgent
    assert d.comfort_required is (desired == "auto")
    assert d.prediction_confidence == 0


@pytest.mark.parametrize("mode,desired", [("auto", "auto"), ("off", "off")])
@pytest.mark.parametrize("current,outside,direction", [(20.7, 14., "heating"), (21.3, 30., "cooling")])
def test_existing_auto_request_has_hysteresis_until_native_target(mode, desired, current, outside, direction):
    d = decide(current, outside=outside, mode=mode, action="idle")
    assert d.desired_mode == desired
    if desired == "auto":
        assert d.comfort_direction == direction


@pytest.mark.parametrize("mode", ["heat", "cool", "dry", "unknown"])
def test_fixed_or_unknown_native_mode_is_not_written(mode):
    assert decide(19., mode=mode).desired_mode == "hold"


def test_reactive_rising_passive_temperature_can_establish_cooling_need_in_cool_weather():
    p = ThermalProfile(last={"outdoor": 14.5, "indoor": 23., "t": time.time(),
                             "action": "off", "passive_slope_c_h": .2})
    d = decide(23., outside=14.5, profile=p)
    assert d.desired_mode == "auto" and d.comfort_direction == "cooling"
    # A heater-induced slope cannot count as natural overheating evidence.
    d = decide(23., outside=14.5, profile=p, action="heating")
    assert d.desired_mode == "off"


def test_an_observed_restoring_trend_does_not_request_opposing_heat():
    p = ThermalProfile(last={"outdoor": 30., "indoor": 19., "t": time.time(),
                             "action": "off", "passive_slope_c_h": .2})
    assert decide(19., outside=30., profile=p).desired_mode == "off"


@pytest.mark.parametrize("current,actual,direction", [(19.3, 5., "heating"), (23., 40., "cooling")])
def test_a_neutral_near_forecast_does_not_hide_actual_directional_comfort_need(current, actual, direction):
    d = decide(current, outside=actual, forecast=[21.] * 48)
    assert d.desired_mode == "auto" and d.urgent_auto
    assert d.comfort_direction == direction


@pytest.mark.parametrize("current,outside,trend", [(19., 5., .2), (23., 40., -.2)])
def test_observed_passive_recovery_avoids_opposing_auto_request(current, outside, trend):
    p = ThermalProfile(last={"outdoor": outside, "indoor": current, "t": time.time(),
                             "action": "off", "passive_slope_c_h": trend})
    assert decide(current, outside=outside, profile=p).desired_mode == "off"


def test_capacity_changes_future_start_and_infeasible_cooling_is_explicit():
    forecast = [21.] * 24 + [40.] * 24
    weak = decide(outside=21., forecast=forecast, profile=trained(cool=.025))
    strong = decide(outside=21., forecast=forecast, profile=trained(cool=.8))
    assert weak.stage == strong.stage == "predictive"
    assert weak.crossing_h == strong.crossing_h == 26
    assert weak.desired_mode == "auto" and weak.urgent_auto
    assert weak.restart_after_h == 0 and weak.forecast_feasible is False
    assert strong.desired_mode == "off" and strong.restart_after_h > 0
    assert strong.forecast_feasible is True
    assert "garandeert geen actieve" in weak.block_reason


def test_measured_zero_capacity_is_not_clamped_into_fictitious_cooling():
    d = decide(outside=21., forecast=[21.] * 24 + [40.] * 24, profile=trained(cool=0))
    assert d.forecast_feasible is False and d.desired_mode == "auto"


def test_auto_availability_cannot_precharge_a_room_already_at_native_target():
    # Forty hours of measured *room* delay is permitted; the planner must not
    # pretend AUTO at a satisfied target starts forty hours of active cooling.
    d = decide(outside=21., forecast=[21.] * 24 + [40.] * 24, profile=trained(delay=40.))
    assert d.desired_mode == "auto" and not d.forecast_feasible
    assert "AUTO garandeert" in d.block_reason


def test_a_comfortable_insulated_room_can_stay_off_even_in_winter():
    p = trained(k=.0001)
    d = decide(outside=14.5, profile=p)
    assert d.stage == "predictive" and d.desired_mode == "off"
    assert d.predicted_min_c > 20.95
    legacy = decide_mode(settings=SETTINGS, zones=[room(mode="auto")], outside_hourly=[14.5] * 48,
                         profiles={"climate.room": p})
    assert legacy.desired_mode == "auto"  # Opt-out behavior remains available.


def test_old_shared_heating_delay_never_qualifies_new_precooling():
    p = trained()
    p.cooling_delays_h = []
    assert p.response_delays_h and p.heating_delays_h
    d = decide(outside=21., forecast=[21.] * 24 + [40.] * 24, profile=p)
    assert d.stage == "reactive" and "cooling_delay" in d.missing_components
    assert d.desired_mode == "off"  # Only current measured demand is controlled.


def test_missing_irrelevant_cooling_evidence_does_not_block_heating_forecast():
    p = trained()
    p.cool_gain = []
    p.cooling_delays_h = []
    p.validation_errors.pop("cooling")
    d = decide(outside=21., forecast=[21.] * 24 + [2.] * 24, profile=p)
    assert d.stage == "predictive" and d.comfort_direction == "heating"
    assert not d.missing_components


def test_generic_learning_days_do_not_invent_direction_specific_day_coverage():
    p = trained()
    p.component_days["cooling_response"] = {"2026-10-01"}
    d = decide(outside=21., forecast=[21.] * 24 + [40.] * 24, profile=p)
    assert d.stage == "reactive" and "cooling_response" in d.missing_components
    assert p.directional_evidence(SETTINGS)["cooling_response"]["days"] == 1


def test_inconsistent_coefficients_do_not_get_predictive_control_from_counts_alone():
    p = trained()
    p.passive_k = [.04, .001, .2, .004, .1, .01] * 20
    assert p.confidence_components(SETTINGS)["passive_temperature_change"]["confidence"] == .98
    assert not p.directional_evidence(SETTINGS)["passive_temperature_change"]["consistent"]
    d = decide(outside=21., forecast=[21.] * 48, profile=p)
    assert d.stage == "reactive" and "passive_temperature_change" in d.missing_components


@pytest.mark.parametrize("errors", [[], [.3] * 12, [.01] * 11])
def test_unvalidated_or_inaccurate_response_cannot_authorise_predictive_start(errors):
    p = trained()
    p.validation_errors["cooling"] = errors
    d = decide(outside=21., forecast=[21.] * 24 + [40.] * 24, profile=p)
    assert d.stage == "reactive" and "cooling_validation" in d.missing_components


@pytest.mark.parametrize("length,stage", [(0, "reactive"), (5, "reactive"), (16, "predictive"), (48, "predictive")])
def test_pv_tail_sets_actual_common_thermal_forecast_scope(length, stage):
    d = decide(outside=21., profile=trained(), settings={"solar_gain_enabled": True}, solar=[0.] * length)
    assert d.stage == stage and d.evaluated_forecast_h == length
    if length < 8:
        assert "solar_forecast" in d.missing_components
        assert d.predicted_min_c is None and d.predicted_max_c is None
    else:
        assert f"{length} uur" in d.reason


@pytest.mark.parametrize("bad", [None, math.nan, math.inf, True, -1])
def test_an_internal_unknown_pv_interval_stops_the_common_horizon(bad):
    d = decide(outside=21., profile=trained(), settings={"solar_gain_enabled": True},
               solar=[0.] * 5 + [bad] + [0.] * 42)
    assert d.stage == "reactive" and d.evaluated_forecast_h == 5
    assert d.predicted_min_c is None


@pytest.mark.parametrize("bad", [None, math.nan, math.inf, True])
def test_an_internal_unknown_weather_interval_cannot_be_skipped(bad):
    d = decide(outside=21., profile=trained(), forecast=[21.] * 5 + [bad] + [40.] * 42)
    assert d.stage == "reactive" and d.evaluated_forecast_h == 5
    assert "hourly_forecast" in d.missing_components and d.predicted_max_c is None


def test_sun_gain_needs_its_own_days_before_qualifying_a_sunny_pause():
    p = trained()
    p.component_days.pop("solar_gain")
    d = decide(outside=21., profile=p, settings={"solar_gain_enabled": True}, solar=[500.] * 48)
    assert d.stage == "reactive" and "solar_gain" in d.missing_components


def test_new_default_controls_and_specs_are_complete():
    assert SMART_CLIMATE_DEFAULTS["automatic_zone_control"] is True
    for key in ("automatic_min_run_h", "automatic_min_off_h"):
        assert SMART_CLIMATE_DEFAULTS[key] == 1
        assert CLIMATE_SETTING_SPECS[key]["min"] == .25
        assert CLIMATE_SETTING_SPECS[key]["max"] == 12
    assert set(CLIMATE_SETTING_SPECS) == set(SMART_CLIMATE_DEFAULTS)


def observe(p, stamp, indoor, action="idle", *, outside=11., pv=0.):
    return p.observe(wall_ts=stamp, day="2026-10-01", indoor_c=indoor,
                     outdoor_c=outside, hvac_action=action, pv_w=pv)


@pytest.mark.parametrize("before,after", [("idle", "heating"), ("heating", "idle"),
                                         ("cooling", "idle"), ("heating", "cooling")])
def test_action_transitions_do_not_attribute_a_mixed_interval_to_a_coefficient(before, after):
    p = ThermalProfile()
    observe(p, 0, 21., before)
    observe(p, 900, 20.9, after)
    assert not p.passive_k and not p.heat_gain and not p.cool_gain
    assert not p.component_days


def test_stable_passive_and_heating_intervals_still_learn_with_real_day_provenance():
    p = ThermalProfile()
    observe(p, 0, 21.)
    observe(p, 900, 20.95)
    observe(p, 1800, 20.95, "heating")
    observe(p, 2700, 21.05, "heating")
    assert p.passive_k and p.heat_gain
    assert p.component_days["passive_temperature_change"] == {"2026-10-01"}
    assert p.component_days["heating_response"] == {"2026-10-01"}


@pytest.mark.parametrize("action,final,field", [("heating", 21.2, "heating_delays_h"),
                                             ("cooling", 20.8, "cooling_delays_h")])
def test_response_delay_keeps_actual_direction_separate(action, final, field):
    p = ThermalProfile()
    observe(p, 0, 21.)
    observe(p, 900, 21., action)
    observe(p, 1800, final, action)
    assert getattr(p, field) == [.25]
    assert p.component_days[f"{action}_delay"] == {"2026-10-01"}
    opposite = "cooling_delays_h" if action == "heating" else "heating_delays_h"
    assert not getattr(p, opposite)


def test_a_gap_discards_an_incomplete_response_instead_of_bridging_unknown_time():
    p = ThermalProfile()
    observe(p, 0, 21.)
    observe(p, 900, 21., "heating")
    assert p.action_started
    assert not observe(p, 8100, 21., "heating")
    observe(p, 9000, 21.2, "heating")
    assert not p.response_delays_h and not p.heating_delays_h


def test_unknown_temperature_invalidates_only_the_unobserved_interval():
    p = trained()
    observe(p, 0, 21.)
    learned = {k: v for k, v in p.snapshot().items() if k != "last"}
    assert not observe(p, 900, None)
    assert p.last is None and p.action_started is None
    assert {k: v for k, v in p.snapshot().items() if k != "last"} == learned
    assert not observe(p, 1800, 20.8)


def test_prediction_validation_is_from_next_observation_before_learning_and_is_not_48h_accuracy():
    p = trained(k=.02)
    p.validation_errors = {}
    p.validation_horizons = {}
    observe(p, 0, 21.)
    observe(p, 900, 20.95)
    report = p.validation_summary()["passive"]
    assert report["samples"] == 1
    assert report["mean_absolute_error_c"] == 0
    assert report["max_horizon_h"] == .25
    assert not report["ready"] and "geen bewijs" in report["note"]


def test_new_provenance_and_validation_survive_restore_without_relabelling_old_shared_delay():
    original = trained(delay=40.)
    saved = deepcopy(original.snapshot())
    restored = ThermalProfile()
    restored.restore(saved)
    # Legacy shared delay is bounded to12h; directional actual room observations
    # remain40h and do not become a proven separate building-mass state.
    assert restored.cooling_delays_h == restored.heating_delays_h == [40.] * 5
    assert restored.component_days == original.component_days
    assert restored.validation_summary() == original.validation_summary()
    restored.restore({"passive_k": [.02] * 20, "heat_gain": [.2] * 20,
                      "response_delays_h": [2.] * 10, "days": sorted(DAYS)})
    assert restored.response_delays_h and not restored.cooling_delays_h
    assert not restored.component_days and not restored.validation_errors


@pytest.mark.parametrize("bad", [None, [], "bad", 42, True])
def test_malformed_new_maps_do_not_crash_or_create_predictive_evidence(bad):
    p = ThermalProfile()
    p.restore({"component_days": bad, "validation_errors": bad,
               "validation_horizons": bad, "heating_delays_h": bad, "cooling_delays_h": bad})
    assert not p.component_days and not p.heating_delays_h and not p.cooling_delays_h
    assert not p.predictive_readiness(SETTINGS)["control_ready"]
