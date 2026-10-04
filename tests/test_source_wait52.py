"""Distinguish live source guards from command faults without changing actuation."""
import time

import pytest
from homeassistant.exceptions import HomeAssistantError

from test_runtime import build


def owned_load(*, kind="switch", device=None):
    runtime, hass = build(kind=kind, power=True, settings={"stale_s": 120},
                         device={"name": "Ontvochtiger", "min_on_s": 1800,
                                 "min_off_s": 1800, **(device or {})})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    state = runtime.states["a"]
    state.owned = state.on = state.observed_once = True
    state.last_on = time.monotonic()
    state.target_w = 1380 if kind == "number" else 1000
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.load", state.target_w, {"unit_of_measurement": "W"})
    return runtime, hass


def physical_calls(hass):
    return [call for call in hass.services.calls if call[0] != "persistent_notification"]


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["missing", "unknown", "unavailable", "restored", "old", "wrong_unit", "invalid"])
async def test_owned_meter_waits_then_recovers_without_reset_or_command(source):
    runtime, hass = owned_load()
    if source == "missing":
        del hass.states.data["sensor.load"]
    else:
        hass.states.set("sensor.load", {"unknown": "unknown", "unavailable": "unavailable",
                                       "invalid": "nan"}.get(source, 1000),
                        {"unit_of_measurement": "kWh" if source == "wrong_unit" else "W",
                         **({"restored": True} if source == "restored" else {})},
                        age=180 if source == "old" else 0)
    await runtime.tick()
    assert runtime.problem_kind == "source_wait"
    assert runtime.analysis.fast[-1]["problem_kind"] == "source_wait"
    assert "Ontvochtiger" in runtime.problem and "Vermogensmeting onbetrouwbaar" in runtime.problem
    assert "Opdrachtfout" not in runtime.problem
    assert not runtime.faults and runtime.pending is None
    assert runtime.mode == "solar" and runtime.states["a"].owned
    assert runtime.states["a"].on and not physical_calls(hass)

    hass.states.set("sensor.load", 1000, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.problem_kind == "" and runtime.problem == ""
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert runtime.mode == "solar" and not physical_calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["missing", "unknown", "unavailable", "restored"])
async def test_owned_control_status_waits_and_is_not_treated_as_a_failed_command(source):
    runtime, hass = owned_load()
    if source == "missing":
        del hass.states.data["switch.load"]
    else:
        hass.states.set("switch.load", "on" if source == "restored" else source,
                        {"restored": True} if source == "restored" else {})
    await runtime.tick()
    assert runtime.problem_kind == "source_wait" and "toestelstatus" in runtime.problem
    assert runtime.states["a"].owned and not runtime.states["a"].available
    assert not runtime.faults and not physical_calls(hass)

    hass.states.set("switch.load", "on")
    await runtime.tick()
    assert runtime.problem == "" and runtime.problem_kind == ""
    assert runtime.states["a"].owned and not physical_calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["Geen opdrachtbevestiging: handmatige controle nodig",
                                   "Opdrachtfout: HomeAssistantError; controleer het toestel"])
async def test_real_command_fault_keeps_manual_review_even_when_meter_recovers(fault):
    runtime, hass = owned_load()
    runtime.faults["a"] = fault
    hass.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.problem_kind == "command_fault"
    assert runtime.problem == "Opdrachtfout: handmatige controle nodig"
    hass.states.set("sensor.load", 1000, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.faults["a"] == fault and runtime.problem_kind == "command_fault"
    with pytest.raises(HomeAssistantError, match="schakel eerst veilig uit"):
        await runtime.reset()
    assert runtime.faults["a"] == fault and not physical_calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["Eenheid van vermogensregelaar is gewijzigd",
                                   "Bereik van vermogensregelaar is gewijzigd"])
async def test_number_configuration_fault_requires_fixing_sources_without_reset(fault):
    runtime, hass = owned_load(kind="number", device={"control_unit": "A"})
    # Keep normal allocation at its existing setting after source recovery;
    # the warning correction itself is not an instruction to raise power.
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    attrs = {"min": 6, "max": 16, "step": 1, "unit_of_measurement": "A"}
    if fault.startswith("Eenheid"):
        attrs["unit_of_measurement"] = "W"
    else:
        attrs["max"] = 10
    hass.states.set("number.amps", 6, attrs)
    await runtime.tick()
    assert runtime.problem_kind == "source_configuration" and fault in runtime.problem
    assert not runtime.faults and not physical_calls(hass)
    hass.states.set("number.amps", 6, {"min": 6, "max": 16, "step": 1, "unit_of_measurement": "A"})
    await runtime.tick()
    assert runtime.problem_kind == "" and not runtime.problem
    assert not physical_calls(hass)


@pytest.mark.asyncio
async def test_direct_reset_during_source_wait_does_not_claim_an_on_device_is_verified_off():
    runtime, hass = owned_load()
    hass.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
    await runtime.tick()
    saved_count, logs = len(runtime.store.saves), list(runtime.logs)
    with pytest.raises(HomeAssistantError, match="Wacht automatisch"):
        await runtime.reset()
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert not runtime.faults and list(runtime.logs) == logs
    assert len(runtime.store.saves) == saved_count and not physical_calls(hass)


@pytest.mark.asyncio
async def test_protected_cycle_is_not_stopped_by_missing_meter_or_source_reset():
    runtime, hass = owned_load(device={"non_interruptible": True})
    hass.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
    for _ in range(3):
        await runtime.tick()
    assert runtime.problem_kind == "source_wait"
    with pytest.raises(HomeAssistantError, match="Wacht automatisch"):
        await runtime.reset()
    assert runtime.states["a"].on and runtime.states["a"].owned
    assert not physical_calls(hass)


@pytest.mark.asyncio
async def test_restart_wait_still_has_priority_over_transient_sources():
    runtime, hass = owned_load()
    runtime.store.data = {"mode": "solar", "device_modes": {"a": "auto"},
                          "leases": {"a": {"name": "Ontvochtiger", "watts": 1000}}}
    hass.states.set("switch.load", "unavailable")
    await runtime.start()
    assert runtime.problem_kind == "restart_wait" and runtime.restart_recovery_pending
    assert runtime.mode == "observe" and not physical_calls(hass)


@pytest.mark.asyncio
async def test_unowned_unavailable_source_does_not_become_a_global_command_fault():
    runtime, hass = owned_load()
    runtime.states["a"].owned = False
    hass.states.set("switch.load", "unavailable")
    hass.states.set("sensor.load", "unavailable")
    await runtime.tick()
    assert runtime.problem_kind == "" and runtime.problem == ""
    assert not runtime.faults and not physical_calls(hass)
