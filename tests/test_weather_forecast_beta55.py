"""Hourly weather availability and successful-fetch cache lifecycle.

Synthetic HA service/state doubles only; no installation export or hardware.
"""
from datetime import datetime, timezone

import pytest
from homeassistant.exceptions import HomeAssistantError

from test_thermal_runtime import setup_climate
from test_thermal_runtime_beta48 import clock, forecast, report


def weather_calls(hass):
    return [call for call in hass.services.calls if call[0] == "weather"]


def setup_weather(monkeypatch):
    runtime, hass = setup_climate()
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    forecast(hass, wall[0])
    return hass, manager, wall


def invalid_weather(hass, manager, invalid):
    obj = hass.states.get("weather.home")
    if invalid == "missing":
        del hass.states.data["weather.home"]
    elif invalid in ("unknown", "unavailable", ""):
        report(hass, "weather.home", mode=invalid or " ")
        if not invalid:
            hass.states.get("weather.home").state = ""
    elif invalid == "restored":
        report(hass, "weather.home", restored=True)
    elif invalid == "future":
        hass.states.set("weather.home", obj.state, obj.attributes, age=-1)
    elif invalid == "missing_stamp":
        obj.last_reported = obj.last_updated = None
    elif invalid == "invalid_stamp":
        obj.last_reported = obj.last_updated = "invalid"
    elif invalid == "wrong_unit":
        report(hass, "weather.home", temperature_unit="°F")
    elif invalid == "binding":
        hass.states.set("weather.other", "cloudy", {"temperature": 21, "temperature_unit": "°C"})
        manager.settings["weather_entity"] = "weather.other"


INVALID_SOURCE = ["missing", "unknown", "unavailable", "", "restored", "future",
                  "missing_stamp", "invalid_stamp", "wrong_unit"]


@pytest.mark.asyncio
async def test_hourly_provider_cache_survives_current_temperature_heartbeat_expiry(monkeypatch):
    hass, manager, wall = setup_weather(monkeypatch)
    # Fetch at :28 while the hourly provider's current report dates from :22.
    wall[0] = (wall[0] // 3600) * 3600 + 28 * 60
    hass.states.set("weather.home", "cloudy", {"temperature": 21, "temperature_unit": "°C"}, age=360)
    forecast(hass, wall[0])
    await manager._refresh_forecast()
    fetched = manager.state.last_forecast_wall
    assert manager.forecast_cache_valid()

    wall[0] += 30 * 60  # :58: room heartbeat policy has now expired.
    manager.settings["outside_temp_entity"] = None
    assert manager._outside() is None
    await manager._refresh_forecast()
    assert manager.forecast_cache_valid()
    assert len(manager._outside_hourly()) == 48
    assert manager._planned_sources_unchanged({"_planning_weather_used": True}, "off", None)
    assert manager.state.last_forecast_wall == fetched
    assert len(weather_calls(hass)) == 1

    wall[0] += 24 * 60  # Next :22: fresh conditions do not force a refetch.
    report(hass, "weather.home")
    await manager._refresh_forecast()
    assert len(weather_calls(hass)) == 1
    assert manager._outside_hourly()

    wall[0] += 6 * 60  # Next :28: ordinary hourly forecast refresh.
    forecast(hass, wall[0])
    await manager._refresh_forecast()
    assert len(weather_calls(hass)) == 2
    assert manager.state.last_forecast_wall == wall[0]
    wall[0] += 30 * 60
    await manager._refresh_forecast()
    assert manager._outside() is None
    assert len(manager._outside_hourly()) == 48
    assert not manager.last_forecast_error


@pytest.mark.asyncio
async def test_old_current_report_can_fetch_forecast_but_selected_outside_stays_strict(monkeypatch):
    hass, manager, wall = setup_weather(monkeypatch)
    obj = hass.states.get("weather.home")
    hass.states.set("weather.home", obj.state, obj.attributes, age=3700)
    await manager._refresh_forecast()
    assert manager.forecast_cache_valid()
    assert manager._outside_hourly() == [21.] * 48
    outdoor = hass.states.get("sensor.outdoor")
    hass.states.set("sensor.outdoor", outdoor.state, outdoor.attributes, age=1801)
    assert manager._outside() is None  # Selected physical source cannot fall back.


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", INVALID_SOURCE)
async def test_invalid_weather_never_fetches_even_with_old_heartbeat_policy_removed(monkeypatch, invalid):
    hass, manager, _ = setup_weather(monkeypatch)
    invalid_weather(hass, manager, invalid)
    await manager._refresh_forecast()
    assert not weather_calls(hass)
    assert manager.state.forecast == []
    assert manager.state.last_forecast_wall == 0
    assert not manager.forecast_cache_valid()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [*INVALID_SOURCE, "binding"])
async def test_all_forecast_consumers_reject_invalid_source_before_next_refresh(monkeypatch, invalid):
    hass, manager, _ = setup_weather(monkeypatch)
    await manager._refresh_forecast()
    invalid_weather(hass, manager, invalid)
    assert not manager.forecast_cache_valid()
    assert manager._current_forecast_rows(24) == []
    assert manager._outside_hourly() == []
    assert not manager._planned_sources_unchanged({"_planning_weather_used": True}, "off", None)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [*INVALID_SOURCE, "binding"])
async def test_source_and_binding_are_revalidated_after_weather_service_await(monkeypatch, invalid):
    hass, manager, _ = setup_weather(monkeypatch)
    original_call = hass.services.async_call

    async def changed_source(domain, action, *args, **kwargs):
        result = await original_call(domain, action, *args, **kwargs)
        invalid_weather(hass, manager, invalid)
        return result

    hass.services.async_call = changed_source
    await manager._refresh_forecast()
    assert len(weather_calls(hass)) == 1
    assert manager.state.forecast == []
    assert manager.state.last_forecast_wall == 0
    assert not manager.state.weather_bias.pending
    assert not manager.forecast_cache_valid()


@pytest.mark.asyncio
async def test_recovered_empty_cache_fetches_immediately_after_recent_success(monkeypatch):
    hass, manager, wall = setup_weather(monkeypatch)
    await manager._refresh_forecast()
    wall[0] += 10
    report(hass, "weather.home", mode="unavailable")
    await manager._refresh_forecast()
    assert manager.state.forecast == []
    report(hass, "weather.home", mode="cloudy")
    await manager._refresh_forecast()
    assert len(weather_calls(hass)) == 2
    assert manager.state.last_forecast_wall == wall[0]
    assert manager.forecast_cache_valid()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["exception", "empty", "past", "far_future", "malformed"])
async def test_failed_initial_refresh_retries_after_one_minute_without_success_stamp(monkeypatch, failure):
    hass, manager, wall = setup_weather(monkeypatch)
    good_rows = list(hass.services.forecast)
    original_call = hass.services.async_call
    fail = [True]

    async def failed_response(domain, action, *args, **kwargs):
        response = await original_call(domain, action, *args, **kwargs)
        if not fail[0]:
            return response
        if failure == "exception":
            raise HomeAssistantError("synthetic weather outage")
        if failure == "past":
            forecast(hass, wall[0] - 72 * 3600)
            rows = hass.services.forecast
        elif failure == "far_future":
            forecast(hass, wall[0] + 72 * 3600)
            rows = hass.services.forecast
        else:
            rows = [] if failure == "empty" else [None, {"datetime": "bad", "temperature": 21}]
        return {manager.settings["weather_entity"]: {"forecast": rows}}

    hass.services.async_call = failed_response
    await manager._refresh_forecast()
    assert manager.state.last_forecast_wall == 0
    assert manager.state.forecast == []
    assert manager.last_forecast_error
    assert not manager.state.weather_bias.pending
    wall[0] += 59
    await manager._refresh_forecast()
    assert len(weather_calls(hass)) == 1
    wall[0] += 1
    fail[0] = False
    hass.services.forecast = good_rows
    await manager._refresh_forecast()
    assert len(weather_calls(hass)) == 2
    assert manager.state.last_forecast_wall == wall[0]
    assert manager.forecast_cache_valid()
    assert not manager.last_forecast_error


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["exception", "empty", "past"])
async def test_repeated_failed_refresh_does_not_extend_old_successful_cache(monkeypatch, failure):
    hass, manager, wall = setup_weather(monkeypatch)
    await manager._refresh_forecast()
    fetched = wall[0]
    original_call = hass.services.async_call

    async def failed_response(domain, action, *args, **kwargs):
        await original_call(domain, action, *args, **kwargs)
        if failure == "exception":
            raise HomeAssistantError("synthetic weather outage")
        rows = []
        if failure == "past":
            rows = [{"datetime": datetime.fromtimestamp(fetched - 3600, timezone.utc).isoformat(),
                     "temperature": 21}]
        return {manager.settings["weather_entity"]: {"forecast": rows}}

    hass.services.async_call = failed_response
    for age in (3600, 3660, 7200):
        wall[0] = fetched + age
        await manager._refresh_forecast()
        assert manager.state.last_forecast_wall == fetched
        assert manager.forecast_cache_valid()
        assert manager._outside_hourly()
    wall[0] = fetched + 7201
    assert not manager.forecast_cache_valid()
    assert manager._current_forecast_rows(24) == []
    await manager._refresh_forecast()
    assert manager.state.forecast == []
    assert manager.state.last_forecast_wall == fetched
    assert len(weather_calls(hass)) == 4  # Last failed attempt still respects 60s retry.


@pytest.mark.asyncio
@pytest.mark.parametrize("refresh_s,limit", [(900, 1800), (3600, 7200), (21600, 43200)])
async def test_success_cache_age_has_existing_dhw_bound(monkeypatch, refresh_s, limit):
    hass, manager, wall = setup_weather(monkeypatch)
    manager.settings["forecast_refresh_s"] = refresh_s
    await manager._refresh_forecast()
    fetched = wall[0]
    wall[0] = fetched + limit
    assert manager.forecast_cache_valid()
    wall[0] += 1
    assert not manager.forecast_cache_valid()
    assert manager._outside_hourly() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("stamp", [0, None, float("nan"), float("inf"), "bad", "future"])
async def test_invalid_success_timestamp_never_exposes_cached_future_hours(monkeypatch, stamp):
    hass, manager, wall = setup_weather(monkeypatch)
    await manager._refresh_forecast()
    manager.state.last_forecast_wall = wall[0] + 1 if stamp == "future" else stamp
    assert not manager.forecast_cache_valid()
    assert manager._outside_hourly() == []


@pytest.mark.asyncio
async def test_past_prefix_cannot_crowd_upcoming_hours_out_of_cache_cap(monkeypatch):
    hass, manager, wall = setup_weather(monkeypatch)
    future_rows = list(hass.services.forecast)
    past_rows = [{"datetime": datetime.fromtimestamp(wall[0] - (hour + 2) * 3600,
                                                     timezone.utc).isoformat(),
                  "temperature": 21} for hour in range(150)]
    hass.services.forecast = past_rows + future_rows
    await manager._refresh_forecast()
    assert manager.forecast_cache_valid()
    assert manager._outside_hourly() == [21.] * 48
    assert len(manager.state.forecast) == 48


@pytest.mark.asyncio
async def test_live_binding_change_resets_failed_retry_window_and_rejects_old_cache(monkeypatch):
    hass, manager, wall = setup_weather(monkeypatch)
    original_call = hass.services.async_call

    async def fail_response(domain, action, *args, **kwargs):
        await original_call(domain, action, *args, **kwargs)
        raise HomeAssistantError("synthetic weather outage")

    hass.services.async_call = fail_response
    await manager._refresh_forecast()
    wall[0] += 1
    hass.states.set("weather.other", "cloudy", {"temperature": 21, "temperature_unit": "°C"})
    manager.apply_settings({**manager.settings, "weather_entity": "weather.other"})
    hass.services.async_call = original_call
    await manager._refresh_forecast()
    assert len(weather_calls(hass)) == 2
    assert weather_calls(hass)[-1][2]["target"] == {"entity_id": "weather.other"}
    assert manager.forecast_cache_valid()
