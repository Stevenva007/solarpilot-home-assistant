"""Runtime forecast coverage, clock boundaries and atomic planner inputs.

HA doubles verify source evidence and elapsed time; no physical HA actuation.
"""
from copy import deepcopy
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from homeassistant.exceptions import HomeAssistantError

from test_runtime import build
from test_price_sources_beta48 import pricing
from test_thermal_runtime import setup_climate
from test_thermal_runtime_beta48 import clock, forecast

UTC = timezone.utc
BRUSSELS = ZoneInfo("Europe/Brussels")
NOW = datetime(2026, 10, 4, 22, 37, tzinfo=UTC)


def legacy(*, horizon=6):
    runtime, hass = build()
    runtime.planner_settings.update(horizon_h=horizon, slot_min=15)
    runtime.forecast_settings.update(enabled=True)
    return runtime, hass


def energy(runtime, hass, key, value, unit="kWh"):
    entity = "sensor.legacy_" + key
    runtime.forecast_settings[key + "_entity"] = entity
    hass.states.set(entity, value, {"unit_of_measurement": unit})


def test_missing_modern_and_legacy_forecasts_stay_unknown():
    runtime, hass = legacy()
    runtime.pv_forecast.hourly = lambda now, hours: [None] * hours
    assert runtime._planner_pv_hourly(NOW) == [None] * 6
    assert not hass.services.calls


def test_covered_modern_zero_and_power_preserved_without_filling_missing_tail():
    runtime, hass = legacy()
    calls = []
    def hourly(start, hours):
        calls.append((start, hours))
        return [0, 1500, None]
    runtime.pv_forecast.hourly = hourly
    assert runtime._planner_pv_hourly(NOW) == [0, 1500, None, None, None, None]
    assert calls == [(NOW.replace(minute=30), 6)]


def test_independent_legacy_current_and_next_energy_only_fill_their_hours():
    runtime, hass = legacy()
    energy(runtime, hass, "current_hour", 500, "Wh")
    energy(runtime, hass, "next_hour", 1.2)
    assert runtime._legacy_planner_pv_hourly(NOW) == [500, 1200, None, None, None, None]


@pytest.mark.parametrize("bad", ["unknown", "unavailable", float("nan"), float("inf"), -1])
def test_invalid_legacy_energy_never_becomes_known_zero(bad):
    runtime, hass = legacy()
    energy(runtime, hass, "current_hour", bad)
    assert runtime._legacy_planner_pv_hourly(NOW)[0] is None


def test_known_zero_day_energy_needs_no_learned_solar_shape():
    runtime, hass = legacy()
    energy(runtime, hass, "remaining_today", 0)
    energy(runtime, hass, "tomorrow", 0)
    assert runtime._legacy_planner_pv_hourly(NOW) == [0] * 6


@pytest.mark.parametrize("profile", [{}, {"22": 1}, {str(h): 0 for h in range(24)}])
def test_positive_daily_energy_without_complete_valid_shape_stays_unknown(profile):
    runtime, hass = legacy()
    runtime.historical_seed["pv_profile"] = {"median_normalized_pct_by_hour": profile}
    energy(runtime, hass, "remaining_today", 2)
    energy(runtime, hass, "tomorrow", 24)
    assert runtime._legacy_planner_pv_hourly(NOW) == [None] * 6


@pytest.mark.parametrize("profile", [None, [], "invalid"])
def test_malformed_historical_pv_profile_is_unknown_without_stopping_runtime(profile):
    runtime, hass = legacy()
    runtime.historical_seed["pv_profile"] = profile
    energy(runtime, hass, "remaining_today", 2)
    energy(runtime, hass, "tomorrow", 24)
    assert runtime._legacy_planner_pv_hourly(NOW) == [None] * 6


def test_short_tomorrow_horizon_does_not_spend_the_entire_daily_forecast():
    runtime, hass = legacy()
    runtime.historical_seed["pv_profile"] = {
        "median_normalized_pct_by_hour": {str(h): 1 for h in range(24)}}
    energy(runtime, hass, "remaining_today", 2)
    energy(runtime, hass, "tomorrow", 24)
    result = runtime._legacy_planner_pv_hourly(NOW.replace(minute=0))
    assert result == pytest.approx([1000] * 6)
    assert sum(result[2:]) / 1000 == 4  # Four hours, not tomorrow's full 24 kWh.


@pytest.mark.parametrize("day,hours", [(datetime(2026, 3, 29, tzinfo=BRUSSELS), 23),
                                      (datetime(2026, 10, 25, tzinfo=BRUSSELS), 25)])
def test_legacy_daily_shape_accounts_for_actual_dst_day_length(day, hours):
    runtime, hass = legacy(horizon=36)
    runtime.historical_seed["pv_profile"] = {
        "median_normalized_pct_by_hour": {str(h): 1 for h in range(24)}}
    energy(runtime, hass, "remaining_today", hours)
    result = runtime._legacy_planner_pv_hourly(day)
    assert result[:hours] == pytest.approx([1000] * hours)
    assert result[hours:] == [None] * (36 - hours)


@pytest.mark.parametrize("day,hours", [(datetime(2026, 3, 29, tzinfo=BRUSSELS), 23),
                                      (datetime(2026, 10, 25, tzinfo=BRUSSELS), 25)])
def test_timestamp_prices_use_elapsed_time_and_distinguish_repeated_hour(day, hours):
    runtime, hass = pricing()
    runtime.planner_settings["slot_min"] = 60
    rows = [{"start": datetime.fromtimestamp(day.timestamp() + h*3600, BRUSSELS).isoformat(),
             "price": h/100} for h in range(hours)]
    hass.states.set("sensor.dynamic_import", .4, {"prices": rows})
    result, _ = runtime._planner_prices(hours, day)
    assert result == pytest.approx([h/100 for h in range(hours)])


@pytest.mark.parametrize("day,hours", [(datetime(2026, 3, 29, tzinfo=BRUSSELS), 23),
                                      (datetime(2026, 10, 25, tzinfo=BRUSSELS), 25)])
def test_day_price_arrays_with_actual_dst_length_preserve_all_slots(day, hours):
    runtime, hass = pricing()
    runtime.planner_settings["slot_min"] = 60
    hass.states.set("sensor.dynamic_import", .4, {"today": [h/100 for h in range(hours)]})
    result, _ = runtime._planner_prices(hours, day)
    assert result == pytest.approx([h/100 for h in range(hours)])


@pytest.mark.parametrize("key", ["today", "prices"])
def test_ambiguous_24_hour_array_on_25_hour_day_uses_fixed_fallback(key):
    runtime, hass = pricing()
    runtime.planner_settings["slot_min"] = 60
    hass.states.set("sensor.dynamic_import", .4, {key: [.01]*24})
    result, _ = runtime._planner_prices(25, datetime(2026, 10, 25, tzinfo=BRUSSELS))
    assert result == pytest.approx([.30]*25)


def test_generic_partial_prices_do_not_repeat_last_cheap_hour():
    runtime, hass = pricing()
    runtime.planner_settings["slot_min"] = 15
    hass.states.set("sensor.dynamic_import", .4, {"prices": [.01, .02]})
    result, _ = runtime._planner_prices(16, NOW)
    assert result == pytest.approx([.01]*4 + [.02]*4 + [.30]*8)


@pytest.mark.parametrize("row", [False, True, 10**1000, {"price": 10**1000},
                                 {"price": False}, {"price": None}])
def test_malformed_price_values_are_unknown_not_free_or_runtime_errors(row):
    runtime, hass = pricing()
    assert runtime._price_value(row) is None
    hass.states.set("sensor.dynamic_import", .4, {"prices": [row, row]})
    result, _ = runtime._planner_prices(8, NOW)
    assert result == pytest.approx([.30]*8)


def test_oversized_dynamic_price_timestamp_is_ignored_safely():
    runtime, hass = pricing()
    row = {"start": 10**1000, "price": .01}
    assert runtime._price_timestamp(row, UTC) is None
    hass.states.set("sensor.dynamic_import", .4, {"prices": [row]})
    result, _ = runtime._planner_prices(8, NOW)
    assert result == pytest.approx([.30]*8)


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), "NaN", "inf", None, [], {}, True, 10**1000])
async def test_invalid_numeric_planner_setting_is_atomic(bad):
    runtime, hass = build()
    settings = deepcopy(runtime.planner_settings)
    options = deepcopy(runtime.entry.options)
    plan = object()
    runtime.unified_plan = runtime.unified_planner.plan = plan
    runtime.unified_planner.last_plan_wall = 123
    with pytest.raises(HomeAssistantError):
        await runtime.async_set_planner_setting("horizon_h", bad)
    assert runtime.planner_settings == settings
    assert runtime.entry.options == options
    assert runtime.unified_plan is plan and runtime.unified_planner.plan is plan
    assert runtime.unified_planner.last_plan_wall == 123
    assert not runtime.logs and not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [False, 0, "false", "OFF", "0", " uit "])
async def test_false_planner_boolean_strings_really_disable(value):
    runtime, hass = build()
    assert await runtime.async_set_planner_setting("enabled", value) is False
    assert runtime.planner_settings["enabled"] is False
    assert runtime.entry.options["planner"]["enabled"] is False
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["maybe", "", None, [], {}, 2, float("nan")])
async def test_invalid_planner_boolean_keeps_current_value(bad):
    runtime, hass = build()
    before = deepcopy(runtime.planner_settings)
    with pytest.raises(HomeAssistantError):
        await runtime.async_set_planner_setting("enabled", bad)
    assert runtime.planner_settings == before
    assert not runtime.logs and not hass.services.calls


@pytest.mark.asyncio
async def test_missing_thermal_solar_source_and_cached_model_do_not_forge_zero(monkeypatch):
    runtime, hass = setup_climate(control=True)
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    await runtime.smart_climate._refresh_forecast()
    runtime.pv_forecast.hourly = lambda now, hours: [None]*hours
    runtime.local_pv.overview = lambda: {"confidence": 1, "corrected_power_w": 0,
                                       "corrected_next_hour_kwh": 0}
    result = runtime.smart_climate._solar_hourly(datetime.fromtimestamp(wall[0], BRUSSELS), 48)
    assert result == [None]*48
    overview = runtime.smart_climate.overview()["solar_gain"]
    assert overview["next_24h_kwh_proxy"] is None
    assert overview["peak_w_proxy"] is None
    assert overview["covered_hours"] == 0


@pytest.mark.asyncio
async def test_thermal_proxy_keeps_modern_zero_and_gap_distinct(monkeypatch):
    runtime, hass = setup_climate(control=True)
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    await runtime.smart_climate._refresh_forecast()
    anchor = runtime.smart_climate.state.forecast[0]["valid_ts"]
    def hourly(now, hours):
        return [0 if now.timestamp() == anchor else None]*hours
    runtime.pv_forecast.hourly = hourly
    result = runtime.smart_climate._solar_hourly(datetime.fromtimestamp(wall[0], BRUSSELS), 48)
    assert result == [0] + [None]*47
    assert runtime.smart_climate.overview()["solar_gain"]["next_24h_kwh_proxy"] is None
