"""Scoped coast evidence uses observations needed by the actual forecast."""
from copy import deepcopy
import math

import pytest

from custom_components.solar_pilot import thermal_climate as model
from custom_components.solar_pilot.thermal_climate import (
    SMART_CLIMATE_DEFAULTS, SmartClimateState, ThermalProfile, decide_mode,
)


SETTINGS = {**SMART_CLIMATE_DEFAULTS, "enabled": True}


def profile(*, heating=False, cooling=False, delay=False, solar=False):
    p = ThermalProfile(samples=633, days={f"2026-09-{day:02d}" for day in range(1, 8)})
    p.passive_k = [.04] * 40
    p.heat_gain = [.2] * 20 if heating else []
    p.cool_gain = [.2] * 20 if cooling else []
    p.response_delays_h = [2.] * 10 if delay else []
    p.solar_gain_per_kw = [.005] * 20 if solar else []
    return p


def zone(*, entity_id="climate.zone", current=21., target=21., mode="auto"):
    return {"entity_id": entity_id, "name": entity_id, "current": current,
            "target": target, "mode": mode, "action": "idle"}


def decide(p, outside=None, *, mode="auto", solar=None, settings=None):
    # These component-isolation cases model a known dark PV forecast by default.
    # Missing PV-source behavior has separate explicit regressions.
    solar = [0.] * 48 if solar is None else solar
    return decide_mode(settings={**SETTINGS, **(settings or {})}, zones=[zone(mode=mode)],
                       outside_hourly=[21.] * 48 if outside is None else outside,
                       profiles={"climate.zone": p}, solar_hourly_w=solar)


def cold_later():
    return [21.] * 20 + [19.] * 28


def hot_later():
    return [21.] * 20 + [23.] * 28


@pytest.mark.parametrize("field", ["indoor_c", "outdoor_c"])
def test_boolean_temperature_is_neither_a_measurement_nor_a_learning_sample(field):
    p = profile()
    p.observe(wall_ts=1000, day="2026-10-01", indoor_c=21, outdoor_c=14, hvac_action="idle", pv_w=0)
    before = deepcopy(p.snapshot())
    args = {"wall_ts": 1900, "day": "2026-10-01", "indoor_c": 21,
            "outdoor_c": 14, "hvac_action": "idle", "pv_w": 0, field: True}
    assert model.finite(True) is None and model.finite(False) is None
    assert not p.observe(**args)
    assert p.snapshot() == before


def test_633_passive_observations_are_real_forecast_evidence_without_a_fake_complete_model():
    p = profile()
    assert p.confidence(SETTINGS) == 0  # The compatibility complete-model score.
    d = decide(p)
    assert d.desired_mode == "off" and d.control_ready
    assert d.forecast_confidence == d.prediction_confidence == .98
    assert d.required_components == ["passive_temperature_change"]
    assert not d.missing_components and not d.block_reason
    assert not p.heat_gain and not p.cool_gain and not p.response_delays_h


def test_total_sample_count_does_not_replace_any_observed_passive_evidence():
    p = profile()
    p.passive_k = []
    d = decide(p)
    assert d.desired_mode == "hold" and not d.control_ready
    assert d.forecast_confidence == 0
    assert d.missing_components == ["passive_temperature_change"]


def test_component_minimum_counts_are_enforced_even_when_the_percentage_exceeds_the_threshold():
    p = profile()
    p.passive_k = [.04] * 11
    assert p.readiness(SETTINGS)["confidence"] > SETTINGS["model_confidence_min"]
    assert not p.readiness(SETTINGS)["control_ready"]
    p.passive_k.append(.04)
    assert p.readiness(SETTINGS)["control_ready"]


def test_lowering_a_confidence_threshold_cannot_replace_missing_practice_observations():
    d = decide(profile(), cold_later(), settings={"model_confidence_min": 0})
    assert not d.control_ready and d.desired_mode == "hold"
    assert "heating_response" in d.missing_components


@pytest.mark.parametrize("direction,outside", [("heating", cold_later()), ("cooling", hot_later())])
def test_only_forecast_relevant_active_direction_is_needed(direction, outside):
    p = profile(heating=direction == "heating", cooling=direction == "cooling", delay=True)
    d = decide(p, outside)
    assert d.desired_mode == "off" and d.control_ready
    assert d.comfort_direction == direction
    assert d.prediction_confidence == .98
    assert d.required_components == ["passive_temperature_change", f"{direction}_response", "response_delay"]
    assert not d.missing_components
    opposite = "cooling" if direction == "heating" else "heating"
    assert f"{opposite}_response" not in d.required_components
    assert p.confidence(SETTINGS) == 0


@pytest.mark.parametrize("mode,desired", [("auto", "hold"), ("off", "auto")])
def test_missing_needed_heating_response_cannot_start_or_keep_an_unverified_coast(mode, desired):
    p = profile(cooling=True)
    d = decide(p, cold_later(), mode=mode)
    assert d.desired_mode == desired and not d.control_ready
    assert d.forecast_confidence == .98 and d.prediction_confidence == 0
    assert d.missing_components == ["heating_response", "response_delay"]
    assert "cooling_response" not in d.required_components
    assert "verwarmingsreactie" in d.block_reason


def test_each_zone_uses_its_own_relevant_direction_before_combining_a_mixed_forecast():
    zones = [zone(entity_id="climate.high", current=22, target=22),
             zone(entity_id="climate.low", current=20, target=20)]
    profiles = {"climate.high": profile(heating=True, delay=True),
                "climate.low": profile(cooling=True, delay=True)}
    d = decide_mode(settings=SETTINGS, zones=zones, outside_hourly=[21.] * 48,
                    profiles=profiles, solar_hourly_w=[0.] * 48)
    assert d.desired_mode == "auto" and not d.control_ready
    assert d.prediction_confidence == .98 and not d.missing_components
    assert d.readiness_by_zone["climate.high"]["directions"] == ["heating"]
    assert d.readiness_by_zone["climate.low"]["directions"] == ["cooling"]
    assert all(row["control_ready"] for row in d.readiness_by_zone.values())
    assert "Gemengde" in d.block_reason


def test_mixed_weather_does_not_hide_a_missing_cooling_response():
    outside = [19.] * 18 + [25.] * 30
    d = decide(profile(heating=True, delay=True), outside)
    assert d.desired_mode == "hold" and not d.control_ready
    assert "cooling_response" in d.missing_components
    assert "heating_response" not in d.missing_components


def test_positive_solar_proxy_cannot_be_silently_ignored_to_authorise_off():
    d = decide(profile(), solar=[1000.] * 48)
    assert d.desired_mode == "hold" and not d.control_ready
    assert d.missing_components == ["solar_gain"]
    assert not d.solar_gain_used
    assert d.readiness_by_zone["climate.zone"]["solar_required"]


def test_learned_solar_component_qualifies_only_when_the_forecast_uses_it():
    p = profile(solar=True)
    sunny = decide(p, solar=[1000.] * 48)
    assert sunny.desired_mode == "off" and sunny.control_ready and sunny.solar_gain_used
    assert sunny.required_components == ["passive_temperature_change", "solar_gain"]
    dark = decide(p, solar=[0.] * 48)
    assert dark.required_components == ["passive_temperature_change"]
    assert not dark.solar_gain_used


def test_explicit_disabled_solar_learning_preserves_the_selected_model_scope():
    d = decide(profile(), solar=[1000.] * 48, settings={"solar_gain_enabled": False})
    assert d.desired_mode == "off" and d.control_ready
    assert "solar_gain" not in d.required_components


@pytest.mark.parametrize("outside", [[], [21.] * 3, [21.] * 47 + [None], [21.] * 47 + [math.nan]])
@pytest.mark.parametrize("mode,desired", [("auto", "hold"), ("off", "auto")])
def test_missing_short_or_invalid_forecast_never_starts_a_coast(outside, mode, desired):
    d = decide(profile(), outside, mode=mode)
    assert d.desired_mode == desired and not d.control_ready
    assert "hourly_forecast" in d.missing_components
    assert "uurvoorspelling" in d.block_reason


@pytest.mark.parametrize("component", ["heating_response", "response_delay"])
def test_provisional_counts_do_not_qualify_coefficient_fallbacks_as_learned_control(component):
    p = profile(heating=True, delay=True)
    if component == "heating_response":
        p.heat_gain = [.2] * 4
    else:
        p.response_delays_h = [2.] * 3
    d = decide(p, cold_later())
    assert d.prediction_confidence >= SETTINGS["model_confidence_min"]
    assert not d.control_ready and d.desired_mode == "hold"
    assert d.missing_components == [component]


def test_component_progress_names_the_needed_sample_count_and_shared_delay_provenance():
    parts = profile().confidence_components(SETTINGS)
    assert parts["passive_temperature_change"]["required_samples"] == 12
    assert parts["heating_response"]["required_samples"] == 6
    assert parts["cooling_response"]["required_samples"] == 6
    assert parts["response_delay"]["required_samples"] == 4
    assert parts["response_delay"]["evidence_scope"] == "shared_heating_or_cooling"


@pytest.mark.parametrize("outside,label", [([14.] * 48, "wintercontext"), ([28.] * 48, "zomercontext")])
def test_season_context_never_claims_an_actual_heat_or_cool_request(outside, label):
    d = decide(profile(), outside)
    assert d.desired_mode == "auto" and not d.control_ready
    assert label in d.reason
    assert "geen actuele warmte- of koelvraag" in d.reason
    assert "handmatige OFF-zones blijven uit" in d.reason
    assert "coast is voor deze" in d.block_reason


def test_scoped_readiness_and_decisions_do_not_rewrite_existing_learning_journals():
    p = profile(heating=True, delay=True, solar=True)
    before = deepcopy(p.snapshot())
    p.readiness(SETTINGS, directions=["heating"], use_solar=True)
    decide(p, cold_later())
    assert p.snapshot() == before
    restored = ThermalProfile()
    restored.restore(before)
    assert restored.snapshot() == before


@pytest.mark.parametrize("saved,expected", [(1_001_800., 1_001_800.),
                                          (2_000_000., 1_021_600.),
                                          (999_999., 0.), (None, 0.),
                                          (math.nan, 0.), (math.inf, 0.), ("invalid", 0.)])
def test_restart_preserves_valid_wall_clock_manual_hold_and_bounds_invalid_journals(monkeypatch, saved, expected):
    monkeypatch.setattr(model.time, "time", lambda: 1_000_000.)
    state = SmartClimateState()
    state.restore({"manual_hold_until": saved}, settings={"manual_hold_h": 6})
    assert state.manual_hold_until == expected


def test_an_actual_stable_heating_action_does_not_fabricate_a_measured_response_delay():
    p = profile()
    p.observe(wall_ts=0, day="2026-10-01", indoor_c=21, outdoor_c=14, hvac_action="idle", pv_w=0)
    for sample in range(1, 10):
        p.observe(wall_ts=sample * 900, day="2026-10-01", indoor_c=21,
                  outdoor_c=14, hvac_action="heating", pv_w=0)
    assert len(p.heat_gain) >= 6
    assert not p.response_delays_h
    assert "response_delay" in p.readiness(SETTINGS, directions=["heating"])["missing_components"]
