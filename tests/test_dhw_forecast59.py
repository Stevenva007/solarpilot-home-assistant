"""A real, usable PV forecast must not crash the evening DHW path."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot import runtime as runtime_module
from test_dhw_runtime import setup


def sunny_evening_forecast():
    runtime, hass = setup(config={"evening_enabled": True, "night_enabled": False})
    runtime.settings.update(settle_s=0, filter_s=0)
    runtime.forecast_settings.update(
        enabled=True,
        current_hour_entity="sensor.forecast_current",
        next_hour_entity="sensor.forecast_next",
        remaining_today_entity="sensor.forecast_remaining",
    )
    # Exercise the independently configured legacy source fallback, with real
    # HA sensor values instead of replacing the forecast-reader methods.
    runtime.pv_forecast.settings["enabled"] = False
    for entity, value in (("sensor.forecast_current", 5),
                          ("sensor.forecast_next", 4),
                          ("sensor.forecast_remaining", 20)):
        hass.states.set(entity, value, {"unit_of_measurement": "kWh"})
    hass.states.set("sensor.grid", -4000, {"unit_of_measurement": "W"})
    runtime.grid_w, runtime.pv_w = -4000, 5000
    return runtime, hass


def test_evening_forecast_builds_real_hourly_slots_without_changing_measured_surplus():
    runtime, hass = sunny_evening_forecast()
    now = datetime(2026, 10, 6, 14, 30, tzinfo=ZoneInfo("Europe/Brussels"))
    reading = runtime.dhw.read(-4000, True, 0, now)

    runtime.dhw._prepare_comfort(now, reading)

    assert runtime.dhw._comfort_forecast_available
    assert runtime.dhw._comfort_slots[:2] == [
        (now, 4000), (now + timedelta(hours=1), 3000)]
    assert reading.export_w == 4000
    assert runtime.dhw.reading.actual_target_c == 50
    assert hass.services.calls == []


@pytest.mark.asyncio
async def test_solar_mode_selection_with_sunny_evening_forecast_stays_automatic(monkeypatch):
    runtime, hass = sunny_evening_forecast()
    fixed_now = datetime(2026, 10, 6, 14, 30, tzinfo=ZoneInfo("Europe/Brussels"))

    class AfternoonClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now.astimezone(tz) if tz is not None else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(runtime_module, "datetime", AfternoonClock)
    runtime.mode = "paused"
    runtime.pause_cause = "user"

    await runtime.set_mode("solar")

    assert runtime.mode == "solar"
    assert runtime.pause_cause == ""
    assert runtime.problem_kind != "internal_fault"
    assert runtime.dhw._comfort_forecast_available
    assert runtime.dhw.policy.result.target_c == 60
    assert ("water_heater", "set_temperature", {
        "entity_id": "water_heater.boiler", "temperature": 60}) in hass.services.calls
