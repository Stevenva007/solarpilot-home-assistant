"""Ordinary targets coexist with an internally managed native weekly cycle."""
from datetime import datetime
import time
from zoneinfo import ZoneInfo

import pytest

from test_dhw_runtime import setup, updates


TZ = ZoneInfo("Europe/Brussels")


async def monday_tick(runtime, hour=12, minute=0, *, grid=-3000):
    return await runtime.dhw.tick(time.monotonic(), grid, True, 0,
                                  local_now=datetime(2026, 10, 5, hour, minute, tzinfo=TZ))


@pytest.mark.asyncio
@pytest.mark.parametrize("hour,minute", [(11, 45), (12, 0), (12, 15), (14, 59), (15, 0)])
async def test_scheduled_cycle_with_unchanged_ordinary_target_allows60(hour, minute):
    runtime, hass = setup(config={"hygiene_schedule_enabled": True})
    updates(hass, "water_heater.boiler", current_temperature=50)
    hass.states.set("sensor.water", 50, {"unit_of_measurement": "°C"})

    assert await monday_tick(runtime, hour, minute)

    assert hass.services.calls == [("water_heater", "set_temperature", {
        "entity_id": "water_heater.boiler", "temperature": 60.0})]
    view = runtime.dhw.overview()
    assert view["execution"]["state"] == "requested"
    assert view["execution"]["proposed_target_c"] == 60
    assert not runtime.dhw.reading.protected
    assert "protection" not in view["execution"]["blocking_gates"]
    assert view["execution"]["heating_evidence"]["reported_heating"] is None
    assert view["hygiene_schedule"]["window_active"]
    assert view["hygiene_schedule"]["context_only"]
    assert view["hygiene_schedule"]["blocks_target_writes"] is False
    assert runtime.dhw.settings["hygiene_start"] == "12:00:00"
    assert runtime.dhw.settings["hygiene_target_c"] == 62
    # The controller touched neither a native cycle setting nor an on/off mode.
    assert hass.states.get("binary_sensor.hygiene").state == "off"
    assert hass.states.get("switch.powerful").state == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_calendar_information_does_not_change_surplus_or_ordinary_target_policy(enabled):
    runtime, hass = setup(config={"hygiene_schedule_enabled": enabled})
    updates(hass, "water_heater.boiler", temperature=49)

    assert await monday_tick(runtime, grid=-2999)

    assert hass.services.calls[-1][2]["temperature"] == 50
    assert not runtime.dhw.reading.protected
    assert runtime.dhw.policy.result.target_c == 50


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["hygiene", "unknown_hygiene", "powerful", "unknown_powerful",
                                  "native_high", "native_off", "native_boost"])
async def test_calendar_does_not_weaken_actual_manufacturer_or_manual_guards(guard):
    runtime, hass = setup(config={"hygiene_schedule_enabled": True})
    if guard == "hygiene":
        hass.states.set("binary_sensor.hygiene", "on")
    elif guard == "unknown_hygiene":
        hass.states.set("binary_sensor.hygiene", "unavailable")
    elif guard == "powerful":
        hass.states.set("switch.powerful", "on")
    elif guard == "unknown_powerful":
        hass.states.set("switch.powerful", "unavailable")
    elif guard == "native_high":
        updates(hass, "water_heater.boiler", temperature=62)
    elif guard == "native_off":
        obj = hass.states.get("water_heater.boiler")
        hass.states.set("water_heater.boiler", "off", obj.attributes)
    else:
        updates(hass, "water_heater.boiler", preset_mode="powerful")

    assert not await monday_tick(runtime)

    assert not hass.services.calls
    assert runtime.dhw.execution["code"] == "protection"
    assert runtime.dhw.reading.protected
    assert runtime.dhw.policy.result.target_c is None


@pytest.mark.asyncio
async def test_schedule_keeps_stability_confirmation_instead_of_making_new_cycle_ready():
    runtime, hass = setup(config={"hygiene_schedule_enabled": True, "rise_delay_s": 60})

    assert not await monday_tick(runtime)

    assert runtime.dhw.execution["code"] == "stability"
    assert runtime.dhw.policy.result.remaining_s == 60
    assert not runtime.dhw.reading.protected
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_schedule_does_not_override_actual_active_room_climate():
    runtime, hass = setup(config={"hygiene_schedule_enabled": True})
    hass.states.set("climate.home", "auto", {"hvac_action": "heating"})

    assert not await monday_tick(runtime)

    assert runtime.dhw.execution["code"] == "space_climate"
    assert not runtime.dhw.reading.protected
    assert runtime.dhw.policy.result.target_c == 50
    assert not hass.services.calls
