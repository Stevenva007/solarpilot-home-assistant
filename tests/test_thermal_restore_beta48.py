"""Malformed thermal journals cannot stop valid sibling models from loading."""
from copy import deepcopy
import json
import math

import pytest

from custom_components.solar_pilot.thermal_climate import (
    CoastFeedback, ForecastBiasProfile, SMART_CLIMATE_DEFAULTS,
    SmartClimateState, ThermalProfile, finite,
)


def saved_profile():
    return {"passive_k": [.04] * 20, "heat_gain": [.2] * 8, "cool_gain": [],
            "solar_gain_per_kw": [.01] * 20, "response_delays_h": [2.] * 4,
            "samples": 633, "days": [f"2026-09-{day:02d}" for day in range(1, 8)],
            "last": {"t": 1000., "indoor": 21., "outdoor": 14., "action": "idle", "pv_w": 1000.}}


@pytest.mark.parametrize("invalid", [None, {}, "000000000000", 633, True])
def test_non_array_observations_do_not_crash_or_create_fake_learning(invalid):
    p = ThermalProfile()
    p.restore({"passive_k": invalid, "heat_gain": invalid,
               "cool_gain": invalid, "solar_gain_per_kw": invalid,
               "response_delays_h": invalid, "days": invalid})
    assert p.passive_k == p.heat_gain == p.cool_gain == p.solar_gain_per_kw == p.response_delays_h == []
    assert not p.days
    assert not p.readiness(SMART_CLIMATE_DEFAULTS)["control_ready"]


def test_invalid_values_only_remove_the_affected_observations_and_preserve_other_learning():
    saved = saved_profile()
    saved["passive_k"] = [.03, None, math.nan, math.inf, -1, .26, True, {}, .04]
    saved["days"].extend([None, {}, "invalid", "2026-99-99"])
    p = ThermalProfile()
    p.restore(saved)
    assert p.passive_k == [.03, .04]
    assert p.heat_gain == [.2] * 8 and p.solar_gain_per_kw == [.01] * 20
    assert p.response_delays_h == [2.] * 4
    assert len(p.days) == 7 and p.samples == 633


@pytest.mark.parametrize("value", [None, "bad", math.nan, math.inf, -1, True, {}, 3.5])
def test_malformed_learning_counters_do_not_stop_restore_or_inflate_confidence(value):
    p = ThermalProfile()
    p.restore({**saved_profile(), "samples": value})
    assert p.samples == 0
    assert p.passive_k == [.04] * 20


def test_numeric_counters_are_bounded_without_changing_normal_saved_counts():
    p = ThermalProfile()
    p.restore({**saved_profile(), "samples": "633"})
    assert p.samples == 633
    p.restore({**saved_profile(), "samples": 1e100})
    assert p.samples == 2_147_483_647
    assert finite(10 ** 10_000) is None


def test_huge_numeric_saved_fields_do_not_abort_valid_sibling_model_restore():
    huge = 10 ** 10_000
    saved = saved_profile()
    broken = {**saved, "samples": huge, "passive_k": [.03, huge, .04],
              "last": {**saved["last"], "t": huge}}
    state = SmartClimateState()
    state.restore({"profiles": {"climate.broken": broken, "climate.good": saved},
                   "weather_bias": {"total_samples": huge, "pending": [
                       {"valid_ts": huge, "predicted_c": 14, "bucket": 6}]},
                   "coast_feedback": {"scored": huge, "adjust_h": huge,
                                      "total_coast_h": huge},
                   "manual_hold_until": huge, "commands_today": huge},
                  ["climate.broken", "climate.good"])
    assert state.profiles["climate.good"].snapshot() == saved
    assert state.profiles["climate.broken"].passive_k == [.03, .04]
    assert state.profiles["climate.broken"].samples == 0
    assert state.profiles["climate.broken"].last is None
    assert state.weather_bias.total_samples == 0 and not state.weather_bias.pending
    assert state.coast_feedback.scored == state.coast_feedback.total_coast_h == 0
    assert state.coast_feedback.adjust_h == state.manual_hold_until == 0
    assert state.commands_today == SMART_CLIMATE_DEFAULTS["max_commands_per_day"]


@pytest.mark.parametrize("last", [{}, {"t": 1000}, {"t": 1000, "indoor": "bad", "outdoor": 14, "action": "idle"},
                                 {"t": 1000, "indoor": 21, "outdoor": 14, "action": {}},
                                 {"t": math.inf, "indoor": 21, "outdoor": 14, "action": "idle"}])
def test_invalid_previous_observation_restarts_sampling_without_a_later_key_error(last):
    p = ThermalProfile()
    p.restore({**saved_profile(), "last": last})
    assert p.last is None
    assert not p.observe(wall_ts=1900, day="2026-10-01", indoor_c=21, outdoor_c=14, hvac_action="idle")
    assert p.samples == 633


def test_valid_profile_round_trip_preserves_633_observations_and_all_coefficients():
    saved = saved_profile()
    p = ThermalProfile()
    p.restore(saved)
    assert p.snapshot() == saved


@pytest.mark.parametrize("invalid", [None, [], "bad", 42, True])
def test_malformed_weather_maps_do_not_crash_restore(invalid):
    p = ForecastBiasProfile()
    p.restore({"errors": invalid, "days": invalid, "pending": invalid, "total_samples": invalid})
    assert all(not values for values in p.errors.values())
    assert not p.pending and p.total_samples == (42 if invalid == 42 and not isinstance(invalid, bool) else 0)


def test_weather_restore_preserves_valid_horizons_and_pending_rows_despite_bad_siblings():
    p = ForecastBiasProfile()
    p.restore({"errors": {"6": None, "12": [1., math.nan, {}, 2., 99.]},
               "days": {"6": {}, "12": ["2026-09-01", "invalid"]},
               "pending": [None, {}, {"valid_ts": 7200, "predicted_c": 14, "bucket": "bad"},
                           {"valid_ts": 7200, "predicted_c": 14, "bucket": "12"},
                           {"valid_ts": 3600, "predicted_c": True, "bucket": 6},
                           {"valid_ts": 7200, "predicted_c": 14, "bucket": {}}],
               "total_samples": "633"})
    assert p.errors["6"] == [] and p.errors["12"] == [1., 2.]
    assert p.days["12"] == {"2026-09-01"}
    assert list(p.pending.values()) == [{"valid_ts": 7200., "predicted_c": 14., "bucket": 12}]
    assert p.total_samples == 633
    assert p.observe(7200, 15., "2026-10-01") == 1


@pytest.mark.parametrize("history", [None, {}, "bad", 42])
def test_malformed_coast_history_does_not_crash_restore_or_overview(history):
    p = CoastFeedback()
    p.restore({"history": history, "scored": "bad"})
    assert p.history == [] and p.scored == 0
    assert p.overview(SMART_CLIMATE_DEFAULTS)["counts"]["correct"] == 0


def test_one_unhashable_coast_outcome_does_not_destroy_other_valid_history():
    p = CoastFeedback()
    p.restore({"history": [{"outcome": "correct", "duration_h": 8},
                           {"outcome": {}}, {"outcome": []}, None,
                           {"outcome": "te_lang", "duration_h": 9}],
               "adjust_h": 1e100, "scored": "633", "total_coast_h": 1e100},
              {**SMART_CLIMATE_DEFAULTS, "coast_feedback_min_adjust_h": -1, "coast_feedback_max_adjust_h": 1})
    assert len(p.history) == 2 and p.scored == 633
    overview = p.overview(SMART_CLIMATE_DEFAULTS)
    assert overview["counts"]["correct"] == overview["counts"]["te_lang"] == 1
    assert p.adjust_h == 1 and p.total_coast_h == 2_147_483_647.
    assert p.active is None and p.pending is None


@pytest.mark.parametrize("bad_row", [
    {"outcome": "correct", "duration_h": math.inf},
    {"outcome": "correct", "ended_temps": {"climate.home": math.nan}},
    {"outcome": "correct", "duration_h": 10 ** 10_000},
])
def test_nonfinite_history_row_cannot_poison_a_valid_serializable_coast_journal(bad_row):
    valid = {"outcome": "correct", "duration_h": 8., "ended_temps": {"climate.home": 21.}}
    p = CoastFeedback()
    p.restore({"history": [valid, bad_row], "scored": 633})
    assert p.history == [valid] and p.scored == 633
    assert json.loads(json.dumps(p.snapshot(), allow_nan=False))["history"] == [valid]


@pytest.mark.parametrize("profiles", [None, [], "bad", 633])
def test_malformed_profile_collection_does_not_abort_entire_integration_restore(profiles):
    state = SmartClimateState()
    state.restore({"profiles": profiles, "weather_bias": None, "coast_feedback": None,
                   "expected_mode": None, "commands_today": "bad"})
    assert state.profiles == {} and state.expected_mode == {}
    assert state.commands_today == SMART_CLIMATE_DEFAULTS["max_commands_per_day"]


def test_bad_model_row_preserves_valid_sibling_profiles_modes_and_input_data():
    good = saved_profile()
    saved = {"profiles": {"climate.bad": None, "climate.good": good,
                          "climate.other": {**good, "samples": "bad", "passive_k": None}},
             "expected_mode": {"climate.bad": {}, "climate.good": "off", "climate.other": ["auto"]},
             "commands_today": 1}
    before = deepcopy(saved)
    state = SmartClimateState()
    state.restore(saved, ["climate.bad", "climate.good", "climate.other"])
    assert state.profiles["climate.good"].snapshot() == good
    assert state.profiles["climate.other"].heat_gain == good["heat_gain"]
    assert state.profiles["climate.other"].passive_k == []
    assert state.expected_mode == {"climate.good": "off"}
    assert state.commands_today == 1 and saved == before


def test_selected_valid_profile_after_many_unknown_rows_is_not_discarded_by_the_budget():
    profiles = {f"climate.unselected_{idx}": None for idx in range(1000)}
    profiles["climate.good"] = saved_profile()
    state = SmartClimateState()
    state.restore({"profiles": profiles}, ["climate.good"])
    assert set(state.profiles) == {"climate.good"}
    assert state.profiles["climate.good"].samples == 633


def test_saved_array_retention_is_bounded_without_losing_normal_counter_history():
    p = ThermalProfile()
    p.restore({**saved_profile(), "passive_k": [.04] * 400, "response_delays_h": [2.] * 100})
    assert len(p.passive_k) == 240 and len(p.response_delays_h) == 60
    assert p.samples == 633
