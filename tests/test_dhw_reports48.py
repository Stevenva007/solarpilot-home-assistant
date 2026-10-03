"""A cached report cannot authorize or confirm a physical boiler command."""
import pytest
from homeassistant.exceptions import HomeAssistantError

from test_dhw_runtime import setup, tick, updates


@pytest.mark.asyncio
@pytest.mark.parametrize("entity", [
    "water_heater.boiler", "sensor.water", "binary_sensor.hygiene", "switch.powerful",
])
async def test_restored_source_blocks_writes_until_live_report_recovers(entity):
    runtime, hass = setup()
    updates(hass, entity, restored=True)

    await tick(runtime)

    assert not hass.services.calls
    assert runtime.dhw.pending is None
    assert runtime.dhw.owned_target is None
    assert not runtime.dhw.fault and not runtime.dhw.manual_hold

    updates(hass, entity, restored=False)
    await tick(runtime)

    assert hass.services.calls == [("water_heater", "set_temperature", {
        "entity_id": "water_heater.boiler", "temperature": 60.0,
    })]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["water_heater", "climate"])
@pytest.mark.parametrize("age", [10000, -30])
async def test_native_target_requires_recent_report_even_with_fresh_separate_tank(kind, age):
    runtime, hass = setup(kind)
    entity = f"{kind}.boiler"
    original = hass.states.get(entity)
    hass.states.set(entity, original.state, original.attributes, age=age)

    await tick(runtime)

    assert runtime.dhw.reading.temperature_c == 44
    assert runtime.dhw.reading.actual_target_c is None
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["number", "input_number"])
async def test_unchanged_live_numeric_helper_and_guards_remain_valid(kind):
    runtime, hass = setup(kind)
    for entity in (f"{kind}.boiler", "binary_sensor.hygiene", "switch.powerful"):
        original = hass.states.get(entity)
        hass.states.set(entity, original.state, original.attributes, age=10000)

    await tick(runtime)

    assert hass.services.calls == [(kind, "set_value", {
        "entity_id": f"{kind}.boiler", "value": 60.0,
    })]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["water_heater", "climate", "number", "input_number"])
async def test_restored_matching_target_cannot_confirm_pending_command(kind):
    runtime, hass = setup(kind)
    hass.services.respond = False
    await tick(runtime)
    assert runtime.dhw.pending
    entity = f"{kind}.boiler"
    original = hass.states.get(entity)
    if kind in ("number", "input_number"):
        hass.states.set(entity, 60, {**original.attributes, "restored": True})
    else:
        updates(hass, entity, temperature=60, restored=True)

    await tick(runtime)

    assert runtime.dhw.pending
    assert runtime.dhw.last_success is None
    assert len(hass.services.calls) == 1

    updates(hass, entity, restored=False)
    await tick(runtime)

    assert runtime.dhw.pending is None
    assert runtime.dhw.last_success["confirmation"] == "ha_state"
    assert len(hass.services.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["water_heater", "climate", "number", "input_number"])
@pytest.mark.parametrize("age", [10000, -30])
async def test_stale_or_future_target_report_cannot_confirm_pending_command(kind, age):
    runtime, hass = setup(kind)
    hass.services.respond = False
    await tick(runtime)
    entity = f"{kind}.boiler"
    original = hass.states.get(entity)
    attrs = dict(original.attributes)
    if kind in ("number", "input_number"):
        state = 60
    else:
        state = original.state
        attrs["temperature"] = 60
    hass.states.set(entity, state, attrs, age=age)

    await tick(runtime)

    assert runtime.dhw.pending
    assert runtime.dhw.last_success is None
    assert len(hass.services.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "invalid", "NaN", float("nan"), "inf", float("inf"), 10 ** 400, True, False])
async def test_invalid_number_api_value_returns_home_assistant_error_without_mutation(value):
    runtime, hass = setup()
    original = runtime.dhw.snapshot()

    with pytest.raises(HomeAssistantError, match="eindig getal"):
        await runtime.dhw.set_number("normal_c", value)

    assert runtime.dhw.snapshot() == original
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["target", "tank"])
@pytest.mark.parametrize("value", [True, False])
async def test_native_boolean_temperatures_cannot_authorize_boiler_command(source, value):
    runtime, hass = setup()
    if source == "target":
        updates(hass, "water_heater.boiler", temperature=value)
    else:
        runtime.dhw.config["temperature_entity"] = ""
        updates(hass, "water_heater.boiler", current_temperature=value)

    await tick(runtime)

    assert not hass.services.calls
    assert runtime.dhw.pending is None
    assert runtime.dhw.owned_target is None


@pytest.mark.asyncio
async def test_number_api_accepts_finite_numeric_string_without_physical_write_in_observe():
    runtime, hass = setup()
    runtime.mode = "observe"

    await runtime.dhw.set_number("normal_c", "50")

    assert runtime.dhw.settings["normal_c"] == 50.0
    assert isinstance(runtime.dhw.settings["normal_c"], float)
    assert runtime.entry.options["dhw"]["normal_c"] == 50.0
    assert not hass.services.calls
