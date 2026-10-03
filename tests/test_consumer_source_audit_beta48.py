"""Reject restored charger limits and contaminated controlled phase evidence."""
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.phase_learning import PhaseLearning, phase_allocation_from_hint
from test_wallbox_profile27 import setup


@pytest.mark.parametrize("source", ["current", "phases", "both"])
def test_restored_wallbox_profile_keeps_confirmed_manual_fallback(source):
    profile, hass = setup(max_current_entity="number.ev_current",
                          phases_entity="sensor.ev_phases",
                          max_current_a=16, charging_phases=1)
    hass.states.set("number.ev_current", 32,
                    {"max": 32, "restored": source in ("current", "both")})
    hass.states.set("sensor.ev_phases", 3,
                    {"restored": source in ("phases", "both")})
    result = profile.update()
    assert result["max_current_a"] == (16 if source in ("current", "both") else 32)
    assert result["phases"] == (1 if source in ("phases", "both") else 3)
    if source in ("current", "both"):
        assert result["current_source"] == "handmatig bevestigd profiel"
    if source in ("phases", "both"):
        assert result["phase_source"] == "handmatig bevestigd profiel"
    assert result["warning"]
    assert not hass.services.calls


def test_restored_wallbox_profile_recovers_on_native_report_without_write():
    profile, hass = setup(max_current_entity="number.ev_current",
                          phases_entity="sensor.ev_phases")
    for eid, value in (("number.ev_current", 16), ("sensor.ev_phases", 3)):
        hass.states.set(eid, value, {"restored": True})
    assert profile.update()["maximum_power_w"] == 5750
    for eid, value in (("number.ev_current", 16), ("sensor.ev_phases", 3)):
        hass.states.set(eid, value)
    result = profile.update()
    assert result["maximum_power_w"] == 11040
    assert result["current_source"] == "Wallbox-integratie"
    assert result["phase_source"] == "expliciete Wallbox-bron"
    assert not hass.services.calls


@pytest.mark.parametrize("stamp", [None, "invalid", SimpleNamespace(timestamp=lambda: float("nan")),
                                   SimpleNamespace(timestamp=lambda: float("inf"))])
def test_malformed_wallbox_profile_timestamp_uses_manual_fallback(stamp):
    profile, hass = setup(max_current_entity="number.ev_current", max_current_a=16)
    hass.states.set("number.ev_current", 32)
    state = hass.states.get("number.ev_current")
    state.last_reported = state.last_updated = stamp
    result = profile.update()
    assert result["max_current_a"] == 16
    assert result["current_source"] == "handmatig bevestigd profiel"
    assert not hass.services.calls


def phase_model():
    return PhaseLearning({"learning_enabled": True, "learning_min_delta_w": 200,
                          "learning_settle_s": 5, "learning_max_window_s": 60,
                          "learning_min_samples": 3})


def test_controlled_simultaneous_loads_cannot_create_trusted_two_phase_map():
    model = phase_model()
    for attempt in range(5):
        now = attempt * 100
        model.observe(now=now, day=f"day-{attempt}", phase_values=(100, 100, 100),
                      device_powers={"controlled": 0, "other": 0})
        model.begin_controlled("controlled", now, (100, 100, 100), 0)
        model.observe(now=now+6, day=f"day-{attempt}", phase_values=(1100, 600, 100),
                      device_powers={"controlled": 1000, "other": 500})
    # Before beta.48 this falsely learned L1+L2 at 98% confidence for a load
    # that only used L1. Repeated ambiguous events must never increase trust.
    profile = model.profile("controlled")
    assert profile["classification"] == "unknown"
    assert profile["samples"] == 0 and profile["confidence"] == 0
    assert model.rejected == 5 and not model.pending


def test_other_load_change_before_settle_is_not_credited_after_it_returns():
    model = phase_model()
    model.observe(now=0, day="day", phase_values=(100, 100, 100),
                  device_powers={"controlled": 0, "other": 0})
    model.begin_controlled("controlled", 0, (100, 100, 100), 0)
    model.observe(now=2, day="day", phase_values=(100, 600, 100),
                  device_powers={"controlled": 0, "other": 500})
    model.observe(now=6, day="day", phase_values=(1100, 100, 100),
                  device_powers={"controlled": 1000, "other": 0})
    assert model.profile("controlled")["samples"] == 0
    assert model.rejected == 1


@pytest.mark.parametrize("other_readings", [{"controlled": 1000},
                                          {"controlled": 1000, "other": None},
                                          {"controlled": 1000, "other": 0, "new": 500}])
def test_controlled_fingerprint_requires_other_meter_baselines(other_readings):
    model = phase_model()
    model.observe(now=0, day="day", phase_values=(100, 100, 100),
                  device_powers={"controlled": 0, "other": 0})
    model.begin_controlled("controlled", 0, (100, 100, 100), 0)
    model.observe(now=6, day="day", phase_values=(1100, 100, 100),
                  device_powers=other_readings)
    assert model.profile("controlled")["samples"] == 0
    assert model.rejected == 1


def test_isolated_controlled_load_still_learns_with_unchanged_other_meter():
    model = phase_model()
    model.observe(now=0, day="day", phase_values=(100, 200, 100),
                  device_powers={"controlled": 0, "other": 100})
    model.begin_controlled("controlled", 0, (100, 200, 100), 0)
    model.observe(now=6, day="day", phase_values=(1100, 200, 100),
                  device_powers={"controlled": 1000, "other": 100})
    assert model.profile("controlled")["classification"] == "L1"
    assert model.profile("controlled")["samples"] == 1
    assert model.accepted == 1 and model.rejected == 0


@pytest.mark.parametrize("bad_entry", [
    {"weight": "unknown"}, {"weight": float("nan")}, {"weight": 0},
    {"device_delta_w": "unknown"}, {"device_delta_w": float("inf")},
    {"shares": [1, 1, 1]}, {"shares": [1, None, 0]},
])
def test_phase_restore_skips_bad_observation_without_losing_valid_evidence(bad_entry):
    model = phase_model()
    valid = {"shares": [1, 0, 0], "weight": 1, "device_delta_w": 1000,
             "day": "day", "source": "passive"}
    model.restore({"profiles": {"controlled": {"observations": [valid, {**valid, **bad_entry}]}},
                   "accepted": 7, "rejected": 3}, ["controlled"])
    assert model.profile("controlled")["classification"] == "L1"
    assert model.profile("controlled")["samples"] == 1
    assert model.accepted == 7 and model.rejected == 3


@pytest.mark.parametrize("stored", [
    {"profiles": None}, {"profiles": []},
    {"profiles": {"controlled": {"observations": None}}},
    {"accepted": "unknown", "rejected": None},
    {"accepted": float("inf"), "rejected": float("nan")},
])
def test_phase_restore_invalid_storage_does_not_block_startup(stored):
    model = phase_model()
    model.restore(stored, ["controlled"])
    assert model.profile("controlled")["samples"] == 0
    assert model.accepted == model.rejected == 0


def test_legacy_controlled_fingerprint_is_relearned_without_losing_passive_or_manual_phase():
    model = phase_model()
    old = {"shares": [.6667, .3333, 0], "weight": 2, "device_delta_w": 1000,
           "source": "controlled", "day": "old-day"}
    passive = {"shares": [1, 0, 0], "weight": 1, "device_delta_w": 1000,
               "source": "passive", "day": "passive-day"}
    model.restore({"profiles": {"only_controlled": {"observations": [old]*5},
                                "mixed": {"observations": [old]*5 + [passive]}}},
                  ["only_controlled", "mixed"])
    assert model.profile("only_controlled")["confidence"] == 0
    assert model.profile("mixed")["samples"] == 1
    assert model.profile("mixed")["classification"] == "L1"
    assert phase_allocation_from_hint("l3", model.profile("only_controlled")) == ((0, 0, 1), "handmatig")
    # Re-saving/reloading performs the same one-time filtering and preserves
    # valid passive records; it never restores the discarded 98% false map.
    restored = phase_model()
    restored.restore(model.snapshot(), ["only_controlled", "mixed"])
    assert restored.profile("mixed") == model.profile("mixed")
    assert restored.profile("only_controlled")["confidence"] == 0


def test_new_isolated_controlled_fingerprint_survives_restart():
    model = phase_model()
    for attempt in range(5):
        now = attempt*100
        model.observe(now=now, day=f"day-{attempt}", phase_values=(100, 100, 100),
                      device_powers={"controlled": 0, "other": 100})
        model.begin_controlled("controlled", now, (100, 100, 100), 0)
        model.observe(now=now+6, day=f"day-{attempt}", phase_values=(100, 100, 1100),
                      device_powers={"controlled": 1000, "other": 100})
    profile = model.profile("controlled")
    assert profile["classification"] == "L3" and profile["confidence"] == .98
    restored = phase_model()
    restored.restore(model.snapshot(), ["controlled"])
    assert restored.profile("controlled") == profile
