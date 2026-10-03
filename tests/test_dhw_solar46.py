"""DHW solar-buffer regressions, with HA state/service doubles only."""
from datetime import datetime
from types import SimpleNamespace as NS

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot.dhw import DHWPolicy, DHWReading
from test_dhw_runtime import setup, tick, updates


def platforms(monkeypatch, values):
    registry = NS(async_get=lambda entity_id: (
        NS(platform=values[entity_id]) if entity_id in values else None
    ))
    monkeypatch.setattr(er, "async_get", lambda _hass: registry)


def idle_aquarea(monkeypatch, *, task="PUMP", mode="auto", action="idle", config=None):
    runtime, hass = setup(config={
        "space_activity_entity": "sensor.task_direction",
        **(config or {}),
    })
    platforms(monkeypatch, {"climate.home": "aquarea"})
    hass.states.set("climate.home", mode, {"hvac_action": action})
    hass.states.set("sensor.task_direction", task)
    return runtime, hass


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "heat_cool"])
@pytest.mark.parametrize("action", ["idle", "off"])
async def test_fresh_aquarea_idle_action_allows_sixty_despite_generic_pump_task(
        monkeypatch, mode, action):
    runtime, hass = idle_aquarea(monkeypatch, mode=mode, action=action)

    # Keep the generic task useful to learning, without treating it as evidence
    # of current heating or cooling when fresh climate actions say idle.
    advisory_busy, _reason, _relevant, source = runtime.dhw.space_activity_status()
    assert advisory_busy is True and source["state"] == "PUMP"

    await tick(runtime)

    assert runtime.dhw.reading.cooling is False
    assert runtime.dhw.reading.space_climate_busy is False
    assert not runtime.dhw.policy.result.cooling_block
    assert runtime.dhw.policy.result.target_c == 60
    assert hass.services.calls == [
        ("water_heater", "set_temperature", {
            "entity_id": "water_heater.boiler", "temperature": 60,
        }),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("task,attrs,age", [
    ("MYSTERY", {}, 0),
    ("unavailable", {}, 0),
    ("PUMP", {}, 301),
    ("PUMP", {"restored": True}, 0),
])
async def test_fresh_aquarea_action_has_priority_over_unreliable_advisory_task(
        monkeypatch, task, attrs, age):
    runtime, hass = idle_aquarea(monkeypatch)
    hass.states.set("sensor.task_direction", task, attrs, age=age)

    assert runtime.dhw.space_activity_status()[0] is None
    await tick(runtime)

    assert runtime.dhw.reading.cooling is False
    assert runtime.dhw.reading.space_climate_busy is False
    assert runtime.dhw.policy.result.target_c == 60
    assert hass.services.calls[-1][2]["temperature"] == 60


@pytest.mark.asyncio
async def test_aquarea_config_entry_domain_uses_fresh_action_without_task_source(monkeypatch):
    runtime, hass = setup()
    hass.states.set("climate.home", "auto", {"hvac_action": "idle"})
    registry = NS(async_get=lambda entity_id: (
        NS(platform="forwarded_climate", config_entry_id="aquarea-entry")
        if entity_id == "climate.home" else None
    ))
    monkeypatch.setattr(er, "async_get", lambda _hass: registry)
    hass.config_entries = NS(async_get_entry=lambda entry_id: (
        NS(domain="aquarea") if entry_id == "aquarea-entry" else None
    ))

    await tick(runtime)

    assert runtime.dhw.reading.cooling is False
    assert runtime.dhw.reading.space_climate_busy is False
    assert hass.services.calls[-1][2]["temperature"] == 60


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter", [None, "other_climate", "panasonic_cc"])
@pytest.mark.parametrize("task", ["PUMP", "MYSTERY"])
async def test_unverified_idle_adapter_keeps_configured_task_guard(monkeypatch, adapter, task):
    runtime, hass = setup(config={"space_activity_entity": "sensor.task_direction"})
    platforms(monkeypatch, {"climate.home": adapter} if adapter else {})
    hass.states.set("climate.home", "auto", {"hvac_action": "idle"})
    hass.states.set("sensor.task_direction", task)

    await tick(runtime)

    assert runtime.dhw.reading.cooling is None
    assert runtime.dhw.reading.space_climate_busy is not False
    assert runtime.dhw.policy.result.target_c == 50
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("other_adapter", [None, "other_climate"])
async def test_mixed_aquarea_and_unverified_auto_idle_keeps_task_guard(
        monkeypatch, other_adapter):
    runtime, hass = idle_aquarea(monkeypatch)
    registry_values = {"climate.home": "aquarea"}
    if other_adapter:
        registry_values["climate.salon"] = other_adapter
    platforms(monkeypatch, registry_values)
    hass.states.set("climate.salon", "auto", {"hvac_action": "idle"})

    await tick(runtime)

    assert runtime.dhw.reading.cooling is None
    assert runtime.dhw.reading.space_climate_busy is not False
    assert runtime.dhw.policy.result.target_c == 50
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_screenshot_surplus_still_allows_sixty_after_house_reserve(monkeypatch):
    runtime, hass = idle_aquarea(monkeypatch)
    runtime.pv_w = 6710
    runtime.settings["reserve_w"] = 150
    hass.states.set("sensor.pv", 6710, {"unit_of_measurement": "W"})
    hass.states.set("sensor.water", 48, {"unit_of_measurement": "°C"})

    # Screenshot: 5.77 kW injection leaves 5.62 kW after the house reserve.
    # Even this conservative available amount clears the existing start rule.
    free_surplus = 5770 - runtime.settings["reserve_w"]
    assert free_surplus == 5620
    assert free_surplus > runtime.dhw.settings["surplus_threshold_w"]
    await tick(runtime, grid=-free_surplus)

    assert runtime.dhw.reading.export_w == 5620
    assert runtime.dhw.policy.result.target_c == 60
    assert hass.services.calls[-1][2]["temperature"] == 60


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ["PUMP", "WATER", "MYSTERY"])
@pytest.mark.parametrize("action", ["heating", "preheating", "defrosting"])
async def test_real_space_heating_keeps_priority_over_optional_buffer(
        monkeypatch, task, action):
    runtime, hass = idle_aquarea(monkeypatch, task=task, action=action)

    await tick(runtime)

    assert runtime.dhw.reading.cooling is False
    assert runtime.dhw.reading.space_climate_busy is True
    assert not runtime.dhw.policy.result.cooling_block
    assert runtime.dhw.policy.result.target_c == 50
    assert runtime.dhw.policy.result.stage == "space_priority"
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ["PUMP", "WATER", "IDLE", "MYSTERY"])
async def test_real_cooling_wins_every_advisory_task_and_releases_owned_sixty(
        monkeypatch, task):
    runtime, hass = idle_aquarea(monkeypatch, task=task, action="cooling", config={
        "fall_delay_s": 120,
    })
    updates(hass, "water_heater.boiler", temperature=60)
    runtime.dhw.owned_target = 60
    runtime.dhw.policy.current = 60

    await tick(runtime)

    assert runtime.dhw.reading.cooling is True
    assert runtime.dhw.policy.result.cooling_block
    assert runtime.dhw.policy.result.target_c == 50
    assert runtime.dhw.policy.result.remaining_s == 0
    assert hass.services.calls[-1][2]["temperature"] == 50


@pytest.mark.asyncio
@pytest.mark.parametrize("state,attrs,age", [
    ("unavailable", {}, 0),
    ("auto", {}, 0),
    ("auto", {"hvac_action": "idle"}, 301),
    ("auto", {"hvac_action": "idle", "restored": True}, 0),
])
async def test_unreliable_climate_cannot_use_task_to_allow_sixty(
        monkeypatch, state, attrs, age):
    runtime, hass = idle_aquarea(monkeypatch, task="WATER")
    hass.states.set("climate.home", state, attrs, age=age)

    await tick(runtime)

    assert runtime.dhw.reading.cooling is None
    assert runtime.dhw.reading.space_climate_busy is not False
    assert runtime.dhw.policy.result.cooling_block
    assert runtime.dhw.policy.result.target_c == 50
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_missing_climate_cannot_use_water_task_to_allow_sixty(monkeypatch):
    runtime, hass = idle_aquarea(monkeypatch, task="WATER")
    del hass.states.data["climate.home"]

    await tick(runtime)

    assert runtime.dhw.reading.cooling is None
    assert runtime.dhw.policy.result.target_c == 50
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_legacy_panasonic_auto_idle_blindspot_remains_fail_closed(monkeypatch):
    runtime, hass = setup()
    platforms(monkeypatch, {"climate.home": "panasonic_cc"})
    hass.states.set("climate.home", "auto", {"hvac_action": "idle"})

    await tick(runtime)

    assert runtime.dhw.reading.cooling is None
    assert runtime.dhw.policy.result.target_c == 50
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_unknown_climate_does_not_invent_cooling_or_delay_recovery(monkeypatch):
    runtime, hass = idle_aquarea(monkeypatch, config={"cooling_clear_s": 1800})
    hass.states.set("climate.home", "unavailable")

    await tick(runtime)

    assert runtime.dhw.reading.cooling is None
    assert runtime.dhw.policy.result.cooling_block
    assert runtime.dhw.policy.last_cooling is None
    assert runtime.dhw._cooling_wall is None
    assert runtime.dhw.snapshot()["cooling_wall"] is None

    hass.states.set("climate.home", "auto", {"hvac_action": "idle"})
    await tick(runtime)

    assert not runtime.dhw.policy.result.cooling_block
    assert runtime.dhw.policy.result.target_c == 60
    assert runtime.dhw.policy.last_cooling is None
    assert hass.services.calls[-1][2]["temperature"] == 60


@pytest.mark.asyncio
async def test_real_cooling_hold_survives_water_task_and_dhw_heating(monkeypatch):
    runtime, hass = idle_aquarea(monkeypatch, action="cooling", config={
        "cooling_clear_s": 1800,
    })
    await tick(runtime)
    cooling_wall = runtime.dhw._cooling_wall
    assert cooling_wall is not None
    assert runtime.dhw.policy.last_cooling is not None

    hass.states.set("sensor.task_direction", "WATER")
    hass.states.set("climate.home", "auto", {"hvac_action": "idle"})
    updates(hass, "water_heater.boiler", hvac_action="heating")
    await tick(runtime)

    assert runtime.dhw.reading.cooling is False
    assert runtime.dhw.policy.result.cooling_block
    assert runtime.dhw.policy.result.target_c == 50
    assert runtime.dhw._cooling_wall >= cooling_wall
    assert not hass.services.calls


def test_unknown_policy_reading_does_not_refresh_a_real_cooling_timestamp():
    runtime, _hass = setup(config={"cooling_clear_s": 1800})
    policy = DHWPolicy(runtime.dhw.settings)
    reading = DHWReading(temperature_c=48, actual_target_c=50, pv_w=6710,
                         export_w=5620, grid_w=-5620, cooling=True,
                         space_climate_busy=False)
    local_now = datetime(2026, 9, 22, 12)
    policy.update(100, local_now, reading)
    assert policy.last_cooling == 100

    reading.cooling = None
    policy.update(1900, local_now, reading)
    assert policy.last_cooling == 100
    assert policy.result.cooling_block

    reading.cooling = False
    policy.update(1901, local_now, reading)
    assert not policy.result.cooling_block
    assert policy.result.target_c == 60
