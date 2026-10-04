"""Missing PV is missing evidence, not a measured dark interval or forecast."""
from copy import deepcopy
import math

import pytest

from custom_components.solar_pilot.thermal_climate import (
    SMART_CLIMATE_DEFAULTS, ThermalProfile, decide_mode,
)
from test_thermal_climate_confidence_beta48 import profile, zone
from test_thermal_runtime import setup_climate


SETTINGS = {**SMART_CLIMATE_DEFAULTS, "enabled": True}
UNKNOWN_PV = [None, "unavailable", math.nan, math.inf, True]


def learning_snapshot(p):
    return {key: value for key, value in p.snapshot().items() if key != "last"}


@pytest.mark.parametrize("action,temperature", [("idle", 20.9), ("heating", 21.1), ("cooling", 20.8)])
@pytest.mark.parametrize("bad_pv", UNKNOWN_PV)
def test_unknown_current_pv_does_not_learn_or_increase_any_confidence(action, temperature, bad_pv):
    p = profile(heating=True, cooling=True, delay=True, solar=True)
    p.observe(wall_ts=0, day="2026-10-01", indoor_c=21, outdoor_c=14,
              hvac_action=action, pv_w=0)
    before = deepcopy(learning_snapshot(p))
    confidence = deepcopy(p.confidence_components(SETTINGS))

    accepted = p.observe(wall_ts=900, day="2026-10-02", indoor_c=temperature,
                         outdoor_c=14, hvac_action=action, pv_w=bad_pv)

    assert not accepted
    assert learning_snapshot(p) == before
    assert p.confidence_components(SETTINGS) == confidence
    assert p.last["pv_w"] is None


def test_one_missing_pv_endpoint_invalidates_the_interval_then_known_reports_resume():
    p = ThermalProfile()
    p.observe(wall_ts=0, day="2026-10-01", indoor_c=21, outdoor_c=11,
              hvac_action="idle", pv_w=None)
    assert not p.observe(wall_ts=900, day="2026-10-01", indoor_c=20.95, outdoor_c=11,
                         hvac_action="idle", pv_w=0)
    assert p.samples == 0 and not p.passive_k and not p.days
    assert p.observe(wall_ts=1800, day="2026-10-01", indoor_c=20.90, outdoor_c=11,
                     hvac_action="idle", pv_w=0)
    assert p.samples == 1 and len(p.passive_k) == 1


def test_pv_outage_does_not_bridge_an_unobserved_interval_or_delay_response():
    p = ThermalProfile()
    p.observe(wall_ts=0, day="2026-10-01", indoor_c=21, outdoor_c=14,
              hvac_action="idle", pv_w=0)
    p.observe(wall_ts=900, day="2026-10-01", indoor_c=21, outdoor_c=14,
              hvac_action="heating", pv_w=0)
    assert p.action_started
    before = deepcopy(learning_snapshot(p))
    assert not p.observe(wall_ts=1800, day="2026-10-01", indoor_c=21.3, outdoor_c=14,
                         hvac_action="heating", pv_w=None)
    assert not p.action_started
    assert learning_snapshot(p) == before
    assert not p.observe(wall_ts=2700, day="2026-10-01", indoor_c=21.5, outdoor_c=14,
                         hvac_action="heating", pv_w=0)
    assert not p.response_delays_h


@pytest.mark.parametrize("saved_pv", [{}, {"pv_w": None}, {"pv_w": "unknown"}, {"pv_w": math.nan}])
def test_restore_retains_valid_history_but_unknown_last_pv_is_not_restored_as_zero(saved_pv):
    original = profile(heating=True, delay=True, solar=True)
    data = original.snapshot()
    data["last"] = {"t": 0, "indoor": 21, "outdoor": 14, "action": "idle", **saved_pv}
    p = ThermalProfile()
    p.restore(data)
    assert p.samples == 633
    assert learning_snapshot(p) == learning_snapshot(original)
    assert p.last["pv_w"] is None
    assert not p.observe(wall_ts=900, day="2026-10-01", indoor_c=20.95, outdoor_c=14,
                         hvac_action="idle", pv_w=0)
    assert p.samples == 633


def test_explicit_disabled_solar_model_can_learn_without_a_pv_source():
    p = ThermalProfile(solar_gain_per_kw=[.05] * 20)
    settings = {**SETTINGS, "solar_gain_enabled": False}
    p.observe(wall_ts=0, day="2026-10-01", indoor_c=21, outdoor_c=14,
              hvac_action="heating", pv_w=None, settings=settings)
    assert p.observe(wall_ts=900, day="2026-10-01", indoor_c=21.1, outdoor_c=14,
                     hvac_action="heating", pv_w=None, settings=settings)
    assert p.samples == 1 and p.heat_gain
    # Disabling the selected solar model also removes its learned correction.
    q = ThermalProfile(solar_gain_per_kw=[.05] * 20)
    q.observe(wall_ts=0, day="2026-10-01", indoor_c=21, outdoor_c=14,
              hvac_action="heating", pv_w=4000, settings=settings)
    q.observe(wall_ts=900, day="2026-10-01", indoor_c=21.1, outdoor_c=14,
              hvac_action="heating", pv_w=4000, settings=settings)
    assert q.heat_gain == pytest.approx(p.heat_gain)


@pytest.mark.parametrize("solar", [None, [], [0.] * 3, [0.] * 47 + [None], [0.] * 47 + [math.nan]])
@pytest.mark.parametrize("mode,expected", [("auto", "hold"), ("off", "auto")])
def test_enabled_solar_model_requires_a_known_coast_forecast_and_keeps_learned_history(solar, mode, expected):
    p = profile(heating=True, cooling=True, delay=True, solar=True)
    before = deepcopy(p.snapshot())
    decision = decide_mode(settings=SETTINGS, zones=[zone(mode=mode)], outside_hourly=[21.] * 48,
                           profiles={"climate.zone": p}, solar_hourly_w=solar)
    assert decision.desired_mode == expected and not decision.control_ready
    assert "solar_forecast" in decision.required_components
    assert "solar_forecast" in decision.missing_components
    assert "PV-uurverwachting" in decision.block_reason
    assert p.snapshot() == before and p.samples == 633


@pytest.mark.parametrize("solar", [[0.] * 48, [1000.] * 48])
def test_valid_dark_and_sunny_forecasts_remain_eligible_for_a_new_coast(solar):
    decision = decide_mode(settings=SETTINGS, zones=[zone()], outside_hourly=[21.] * 48,
                           profiles={"climate.zone": profile(solar=True)}, solar_hourly_w=solar)
    assert decision.desired_mode == "off" and decision.control_ready
    assert "solar_forecast" not in decision.missing_components


def test_explicit_disabled_solar_model_still_coasts_without_pv_forecast():
    decision = decide_mode(settings={**SETTINGS, "solar_gain_enabled": False}, zones=[zone()],
                           outside_hourly=[21.] * 48, profiles={"climate.zone": profile()}, solar_hourly_w=None)
    assert decision.desired_mode == "off" and decision.control_ready
    assert "solar_forecast" not in decision.required_components


def test_pv_must_cover_the_whole_evaluated_temperature_horizon_not_only_first_coast_hours():
    p = profile(solar=True)
    incomplete = decide_mode(settings=SETTINGS, zones=[zone()], outside_hourly=[21.] * 48,
                             profiles={"climate.zone": p}, solar_hourly_w=[0.] * 8)
    assert incomplete.desired_mode == "hold" and not incomplete.control_ready
    assert "solar_forecast" in incomplete.missing_components
    complete = decide_mode(settings=SETTINGS, zones=[zone()], outside_hourly=[21.] * 8,
                           profiles={"climate.zone": p}, solar_hourly_w=[0.] * 8)
    assert complete.desired_mode == "off" and complete.control_ready
    assert complete.evaluated_forecast_h == 8
    assert complete.readiness_by_zone["climate.zone"]["forecast_hours"] == 8
    assert "komende 8 uur" in complete.reason


@pytest.mark.asyncio
@pytest.mark.parametrize("owned_off", [False, True])
async def test_runtime_without_pv_forecast_cannot_start_coast_but_releases_only_its_owned_off(owned_off):
    runtime, hass = setup_climate(control=True, mode="off" if owned_off else "auto")
    runtime.mode = "solar"
    manager = runtime.smart_climate
    for entity in ("climate.home", "climate.salon"):
        manager.state.profiles[entity] = profile(heating=True, cooling=True, delay=True, solar=True)
    if owned_off:
        manager.state.expected_mode["climate.home"] = "off"
        manager.manual_off.add("climate.salon")

    await runtime.tick()

    decision = manager.state.last_decision
    assert not decision.control_ready
    assert "solar_forecast" in decision.missing_components
    assert all(p.samples == 633 for p in manager.state.profiles.values())
    climate_calls = [call for call in hass.services.calls if call[0] == "climate"]
    assert climate_calls == ([
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ] if owned_off else [])
    if owned_off:
        assert hass.states.get("climate.salon").state == "off"
