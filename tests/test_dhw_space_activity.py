"""Panasonic reported-task guard; no real Home Assistant or actuator calls."""
from datetime import datetime, timezone
from types import SimpleNamespace as NS
import time

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot.dhw import (
    DHW_DEFAULTS,
    normalized_settings,
    validate_settings,
)
from custom_components.solar_pilot.heatpump_learning import (
    CONTEXT_HEATING,
    CONTEXT_NORMAL,
    CONTEXT_UNKNOWN,
    classify_heatpump,
)
from custom_components.solar_pilot.private_bundle import private_group_suggestions
from test_dhw_runtime import setup, tick, updates
from test_learning_hub30 import metered


def bind_direction(config=None):
    return setup(config={
        "space_activity_entity": "sensor.task_direction",
        "space_activity_active_states": "PUMP",
        "space_activity_inactive_states": "IDLE;WATER",
        **(config or {}),
    })


def platforms(monkeypatch, values):
    registry = NS(async_get=lambda entity_id: (
        NS(platform=values[entity_id]) if entity_id in values else None
    ))
    monkeypatch.setattr(er, "async_get", lambda _hass: registry)


@pytest.mark.asyncio
async def test_reported_pump_is_advisory_when_aquarea_reports_fresh_idle(monkeypatch):
    runtime, hass = bind_direction()
    hass.states.set("sensor.task_direction", "PUMP")
    hass.states.set("sensor.unrelated_pump_status", "On")
    platforms(monkeypatch, {"climate.home": "aquarea"})

    busy, reason = runtime.dhw._space_activity()
    assert busy is True and "ruimtebedrijf" in reason
    assert "compressorvermogen" in reason
    assert runtime.dhw._cooling() is False

    await tick(runtime)
    assert not runtime.dhw.policy.result.cooling_block
    assert runtime.dhw.policy.result.target_c == 60
    assert hass.services.calls[-1][2]["temperature"] == 60


@pytest.mark.asyncio
@pytest.mark.parametrize("reported", ["IDLE", "WATER", "water"])
async def test_explicit_idle_or_water_allows_surplus_without_using_pump_status(reported):
    runtime, hass = bind_direction()
    hass.states.set("sensor.task_direction", reported)
    # A separate native pump can also run for WATER; it is deliberately not a
    # space-operation source and must not be guessed by name or state.
    hass.states.set("sensor.unrelated_pump_status", "On")

    assert runtime.dhw._space_activity() == (False, "")
    assert runtime.dhw._cooling() is False
    overview = runtime.dhw.overview()["space_activity_source"]
    assert overview["reported_state"].casefold() == reported.casefold()
    assert overview["space_busy"] is False and "compressoractiviteit" in overview["evidence"]
    await tick(runtime)
    assert hass.services.calls[-1][2]["temperature"] == 60


@pytest.mark.asyncio
@pytest.mark.parametrize("reported,attrs,age", [
    ("PUMP", {}, 301),
    ("PUMP", {"restored": True}, 0),
    ("unavailable", {}, 0),
    ("MYSTERY", {}, 0),
])
async def test_unreliable_task_and_missing_climate_action_block_fail_closed(reported, attrs, age):
    runtime, hass = bind_direction()
    hass.states.set("sensor.task_direction", reported, attrs, age=age)
    hass.states.set("climate.home", "unavailable")

    busy, reason = runtime.dhw._space_activity()
    assert busy is None and "wacht" in reason
    await tick(runtime)
    assert runtime.dhw.policy.result.target_c == 50
    assert runtime.dhw.policy.result.cooling_block
    assert not hass.services.calls


@pytest.mark.parametrize("adapter_domain", ["panasonic_cc", "aquarea"])
@pytest.mark.parametrize("mode", ["auto", "heat_cool"])
def test_registered_panasonic_auto_idle_is_unknown_without_direction(
        monkeypatch, mode, adapter_domain):
    runtime, hass = setup()
    hass.states.set("climate.home", mode, {"hvac_action": "idle"})
    platforms(monkeypatch, {"climate.home": adapter_domain})

    assert runtime.dhw._space_activity()[0] is None
    assert runtime.dhw._cooling() is (None if adapter_domain == "panasonic_cc" else False)
    assert runtime.dhw._space_raise_guard()[0] is (None if adapter_domain == "panasonic_cc" else False)
    runtime.smart_climate.settings["zone_entities"] = ["climate.home"]
    context, _reason = classify_heatpump(runtime, datetime(2026, 9, 22, 12))
    assert context == CONTEXT_UNKNOWN


def test_aquarea_config_entry_keeps_learning_conservative_but_trusts_native_idle(monkeypatch):
    runtime, hass = setup()
    hass.states.set("climate.home", "auto", {"hvac_action": "idle"})
    registry = NS(async_get=lambda entity_id: (
        NS(platform="forwarded_climate", config_entry_id="aquarea-entry")
        if entity_id == "climate.home" else None))
    monkeypatch.setattr(er, "async_get", lambda _hass: registry)
    hass.config_entries = NS(async_get_entry=lambda entry_id: (
        NS(domain="aquarea") if entry_id == "aquarea-entry" else None))

    assert runtime.dhw._space_activity()[0] is None
    assert runtime.dhw._cooling() is False
    assert runtime.dhw._space_raise_guard() == (False, "")


@pytest.mark.parametrize("mode,action,cooling,busy", [
    ("auto", "heating", False, True),
    ("auto", "cooling", True, True),
    ("off", "off", False, False),
])
def test_aquarea_exact_action_is_not_overwritten_by_domain_fallback(
        monkeypatch, mode, action, cooling, busy):
    runtime, hass = setup()
    hass.states.set("climate.home", mode, {"hvac_action": action})
    platforms(monkeypatch, {"climate.home": "aquarea"})

    assert runtime.dhw._cooling() is cooling
    assert runtime.dhw._space_activity()[0] is busy


def test_other_adapter_idle_and_explicit_panasonic_off_keep_existing_idle_semantics(monkeypatch):
    runtime, hass = setup()
    runtime.smart_climate.settings["zone_entities"] = ["climate.home"]
    hass.states.set("climate.home", "heat_cool", {"hvac_action": "idle"})
    platforms(monkeypatch, {"climate.home": "other_climate"})
    assert runtime.dhw._space_activity() == (False, "")
    assert runtime.dhw._cooling() is False
    assert classify_heatpump(runtime, datetime(2026, 9, 22, 12))[0] == CONTEXT_NORMAL

    hass.states.set("climate.home", "off", {"hvac_action": "off"})
    platforms(monkeypatch, {"climate.home": "panasonic_cc"})
    assert runtime.dhw._space_activity() == (False, "")


@pytest.mark.parametrize("reported", ["PUMP", "WATER"])
def test_reported_pump_or_water_is_not_learned_as_normal_household_load(reported):
    runtime, hass = metered()
    runtime.entry.options["dhw"] = {
        **DHW_DEFAULTS,
        "space_activity_entity": "sensor.task_direction",
    }
    # Rebuild only the read-only DHW adapter against the test config.
    from custom_components.solar_pilot.dhw_runtime import DHWManager
    runtime.dhw = DHWManager(runtime)
    runtime.smart_climate.settings.update(enabled=True, zone_entities=["climate.zone"])
    hass.states.set("climate.zone", "heat_cool", {"hvac_action": "idle"})
    hass.states.set("sensor.task_direction", reported)

    sample = runtime.learning_hub.observe(datetime.now(timezone.utc), time.monotonic())
    assert sample["valid"] and sample["context"] == CONTEXT_UNKNOWN
    assert runtime.unified_planner.base_load.accepted == 0
    assert next(iter(runtime.learning_hub.days.values()))["heatpump_heatpump_unknown"] == 1


def test_explicit_action_still_classifies_before_generic_pump_direction():
    runtime, hass = bind_direction()
    runtime.smart_climate.settings["zone_entities"] = ["climate.home"]
    hass.states.set("climate.home", "heat_cool", {"hvac_action": "heating"})
    hass.states.set("sensor.task_direction", "PUMP")
    assert classify_heatpump(runtime, datetime(2026, 9, 22, 12))[0] == CONTEXT_HEATING


@pytest.mark.asyncio
@pytest.mark.parametrize("reported", ["PUMP", "MYSTERY"])
async def test_owned_sixty_falls_directly_when_legacy_direction_is_not_safe(reported, monkeypatch):
    runtime, hass = bind_direction({"fall_delay_s": 120})
    hass.states.set("sensor.task_direction", reported)
    hass.states.set("climate.home", "auto", {"hvac_action": "idle"})
    platforms(monkeypatch, {"climate.home": "panasonic_cc"})
    updates(hass, "water_heater.boiler", temperature=60)
    runtime.dhw.owned_target = 60
    runtime.dhw.policy.current = 60

    await tick(runtime)
    assert runtime.dhw.reading.cooling is None
    assert runtime.dhw.policy.result.cooling_block
    assert runtime.dhw.policy.result.target_c == 50
    assert runtime.dhw.policy.result.remaining_s == 0
    assert hass.services.calls[-1][2]["temperature"] == 50


@pytest.mark.asyncio
async def test_owned_sixty_may_remain_for_fresh_water_direction_but_real_cooling_wins():
    runtime, hass = bind_direction({"fall_delay_s": 120})
    hass.states.set("sensor.task_direction", "WATER")
    updates(hass, "water_heater.boiler", temperature=60)
    runtime.dhw.owned_target = 60
    runtime.dhw.policy.current = 60

    await tick(runtime)
    assert runtime.dhw.reading.cooling is False
    assert runtime.dhw.policy.result.target_c == 60
    assert not hass.services.calls

    hass.states.set("climate.home", "heat_cool", {"hvac_action": "cooling"})
    await tick(runtime)
    assert runtime.dhw.reading.cooling is True
    assert runtime.dhw.policy.result.target_c == 50
    assert hass.services.calls[-1][2]["temperature"] == 50


def test_state_lists_must_be_nonempty_and_disjoint():
    configured = {
        **DHW_DEFAULTS,
        "space_activity_entity": "sensor.task_direction",
        "space_activity_active_states": "PUMP; shared",
        "space_activity_inactive_states": "IDLE;SHARED",
    }
    errors = validate_settings(configured)
    assert errors["space_activity_active_states"] == "dhw_space_activity_states"
    assert errors["space_activity_inactive_states"] == "dhw_space_activity_states"

    corrupt = {
        **DHW_DEFAULTS,
        "space_activity_entity": "sensor.task_direction",
        "space_activity_active_states": {"unexpected": "PUMP"},
    }
    assert validate_settings(corrupt)["space_activity_active_states"] == "dhw_space_activity_states"
    runtime, hass = bind_direction({"space_activity_active_states": {"unexpected": "PUMP"}})
    hass.states.set("sensor.task_direction", "PUMP")
    assert runtime.dhw._space_activity()[0] is None
    assert runtime.dhw._cooling() is None

def test_defaults_and_private_import_support_all_three_explicit_fields():
    settings = normalized_settings()
    assert settings["space_activity_entity"] == ""
    assert settings["space_activity_active_states"] == "PUMP"
    assert settings["space_activity_inactive_states"] == "IDLE;WATER"
    runtime, hass = setup()
    hass.states.set("sensor.task_direction", "IDLE")
    bundle = {"format": "solarpilot-private-bundle-v1", "profile": {"suggestions": {"dhw": {
        "space_activity_entity": "sensor.task_direction",
        "space_activity_active_states": "PUMP",
        "space_activity_inactive_states": "IDLE;WATER",
    }}}}
    values = private_group_suggestions(hass, "dhw", bundle)
    assert values == {
        "space_activity_entity": "sensor.task_direction",
        "space_activity_active_states": "PUMP",
        "space_activity_inactive_states": "IDLE;WATER",
    }
    bundle["profile"]["suggestions"]["dhw"]["space_activity_active_states"] = {"bad": "PUMP"}
    assert "space_activity_active_states" not in private_group_suggestions(hass, "dhw", bundle)
