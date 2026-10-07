"""Execute boiler recovery against real managers with explicit HA doubles."""
import copy
import time

import pytest
from homeassistant.exceptions import HomeAssistantError

from test_dhw_runtime import setup


FAULT = "Boilerdoel niet bevestigd; handmatige controle nodig"


def faulted_boiler(mode="paused"):
    runtime, hass = setup(config={"hygiene_schedule_enabled": False})
    runtime.mode = mode
    runtime.dhw.fault = runtime.dhw.status = FAULT
    return runtime, hass


def boiler_writes(hass):
    return [call for call in hass.services.calls
            if call[0] in ("water_heater", "climate", "number", "input_number")
            and call[1] in ("set_temperature", "set_value")]


@pytest.mark.asyncio
async def test_latched_boiler_fault_gets_its_own_problem_category_and_review_contract():
    runtime, hass = faulted_boiler()
    await runtime.tick()
    assert runtime.problem_kind == "dhw_review" and runtime.problem == FAULT
    review = runtime.dhw.overview()
    assert review["review_required"] is True and review["review_allowed"] is True
    assert not review["review_block_reason"]
    assert not boiler_writes(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("problem_kind", ["dhw_review", ""])
async def test_generic_reset_rejects_pure_boiler_fault_without_touching_other_journals(problem_kind):
    runtime, hass = faulted_boiler()
    runtime.problem_kind = problem_kind
    runtime.problem = FAULT
    journal = {"id": "battery_one", "target_w": -1000, "issued_wall": time.time(), "kind": "number"}
    runtime.battery_fleet.state.pending = copy.deepcopy(journal)
    with pytest.raises(HomeAssistantError) as error:
        await runtime.reset()
    assert "boiler" in str(error.value).lower()
    assert runtime.dhw.fault == FAULT
    assert runtime.battery_fleet.state.pending == journal
    assert not boiler_writes(hass)


@pytest.mark.asyncio
async def test_mixed_load_reset_clears_only_the_confirmed_off_load_and_keeps_boiler_review_required():
    runtime, hass = faulted_boiler()
    runtime.faults["a"] = "Uitschakelen niet bevestigd"
    runtime.states["a"].fault = runtime.faults["a"]
    hass.states.set("switch.load", "off")
    await runtime.reset()
    assert "a" not in runtime.faults and not runtime.states["a"].fault
    assert runtime.dhw.fault == FAULT and runtime.mode == "paused"
    assert not boiler_writes(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("block", [
    "solar", "pending", "target_missing", "temperature_missing", "temperature_wrong_unit",
    "target_stale", "target_restored", "hygiene", "powerful",
])
async def test_boiler_review_preserves_the_fault_when_existing_prerequisites_fail(block):
    runtime, hass = faulted_boiler()
    runtime.dhw.owned_target = 60
    if block == "solar":
        runtime.mode = "solar"
    elif block == "pending":
        runtime.dhw.pending = {"target_c": 60, "issued_wall": time.time()}
    elif block == "target_missing":
        hass.states.set("water_heater.boiler", "unavailable")
    elif block == "temperature_missing":
        hass.states.set("sensor.water", "unavailable", {"unit_of_measurement": "°C"})
    elif block == "temperature_wrong_unit":
        hass.states.set("sensor.water", 50, {"unit_of_measurement": "°F"})
    elif block in ("target_stale", "target_restored"):
        obj = hass.states.get("water_heater.boiler")
        hass.states.set("water_heater.boiler", obj.state,
                        {**obj.attributes, **({"restored": True} if block == "target_restored" else {})},
                        age=1200 if block == "target_stale" else 0)
    else:
        hass.states.set("binary_sensor.hygiene" if block == "hygiene" else "switch.powerful", "on")
    before = runtime.dhw.snapshot()
    with pytest.raises(HomeAssistantError):
        await runtime.dhw.review()
    assert runtime.dhw.snapshot() == before
    assert runtime.dhw.fault == FAULT and runtime.dhw.owned_target == 60
    assert not boiler_writes(hass)


@pytest.mark.asyncio
async def test_explicit_boiler_review_clears_its_fault_without_replaying_temperature_or_resuming_solar():
    runtime, hass = faulted_boiler()
    runtime.dhw.needs_review = runtime.dhw.manual_hold = True
    runtime.dhw.restart_recovery = {"reason": "Boilercontrole vereist"}
    runtime.dhw.owned_target = 60
    await runtime.dhw.review()
    assert not runtime.dhw.fault and not runtime.dhw.needs_review and not runtime.dhw.manual_hold
    assert runtime.dhw.restart_recovery is None and runtime.dhw.owned_target is None
    assert runtime.dhw.pending is None and runtime.mode == "paused"
    assert hass.states.get("water_heater.boiler").attributes["temperature"] == 50
    assert not boiler_writes(hass)


@pytest.mark.asyncio
async def test_boiler_review_does_not_clear_other_module_faults():
    runtime, hass = faulted_boiler()
    runtime.faults["a"] = "Andere schakelopdracht niet bevestigd"
    runtime.battery_fleet.state.faults["battery_one"] = "Batterijopdracht niet bevestigd"
    runtime.smart_climate.command_faults["climate.home"] = "Klimaatopdracht niet bevestigd"
    await runtime.dhw.review()
    assert not runtime.dhw.fault
    assert runtime.faults["a"] == "Andere schakelopdracht niet bevestigd"
    assert runtime.battery_fleet.state.faults["battery_one"] == "Batterijopdracht niet bevestigd"
    assert runtime.smart_climate.command_faults["climate.home"] == "Klimaatopdracht niet bevestigd"
    assert not boiler_writes(hass)
