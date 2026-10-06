"""Quarantine uncertain device sources while independently safe loads proceed."""
from copy import deepcopy
from datetime import datetime, timezone
import time

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.engine import Action
from custom_components.solar_pilot.runtime import SolarRuntime
from test_runtime import build


def paired_runtime(*, kind="switch", protected=False, power=True):
    original, hass = build(kind=kind, power=power,
        device={"name": "Onbereikbaar toestel", "non_interruptible": protected,
                "min_on_s": 600, "min_off_s": 600})
    original.entry.options["devices"].append({
        "id": "b", "name": "Beschikbaar toestel", "kind": "switch",
        "control_entity": "switch.healthy", "nominal_w": 1000,
        "start_delay_s": 0, "stop_delay_s": 0, "min_on_s": 0,
        "min_off_s": 0, "start_margin_w": 0,
    })
    hass.states.set("switch.healthy", "off")
    runtime = SolarRuntime(hass, original.entry)
    runtime.store.data = {"mode": "solar", "restart_requested_mode": None,
        "device_modes": {"a": "auto", "b": "auto"},
        "leases": {"a": {"watts": 1380 if kind == "number" else 1000,
                          "name": "Onbereikbaar toestel"}}}
    hass.states.set("switch.load", "unavailable")
    return runtime, hass


def commands(hass, entity=None):
    return [call for call in hass.services.calls
            if call[0] != "persistent_notification"
            and (entity is None or call[2].get("entity_id") == entity)]


@pytest.mark.asyncio
async def test_missing_restart_device_isolated_while_healthy_load_starts():
    runtime, hass = paired_runtime()
    await runtime.start()
    assert runtime.mode == "solar" and runtime.restart_requested_mode is None
    assert "a" in runtime.recovery and not runtime.restart_blocking
    assert runtime.source_isolated_devices["a"]["reserve_w"] == 1000
    assert runtime.result.budget_w == 2500  # P1 surplus, never synthetic owned credit.
    assert runtime.energy_estimated
    assert commands(hass) == [("switch", "turn_on", {"entity_id": "switch.healthy"})]
    assert "Tijdelijk apart gehouden" in runtime.result.reasons["a"]
    assert runtime.store.data["leases"]["a"]["watts"] == 1000
    assert not runtime.states["a"].owned and not runtime.states["a"].available
    assert runtime.analysis.fast[-1]["isolated_devices"]["a"]["reserve_w"] == 1000
    assert runtime.analysis.fast[-1]["isolated_reserve_w"] == 1000
    assert not runtime.analysis.fast[-1]["restart_blocking"]


@pytest.mark.asyncio
@pytest.mark.parametrize("grid", ["unavailable", "unknown", "stale", "wrong_unit"])
async def test_device_isolation_never_bypasses_invalid_global_p1(grid):
    runtime, hass = paired_runtime()
    hass.states.set("sensor.grid", -2500 if grid in ("stale", "wrong_unit") else grid,
                    {"unit_of_measurement": "kWh" if grid == "wrong_unit" else "W"},
                    age=999 if grid == "stale" else 0)
    await runtime.start()
    assert runtime.mode == "solar" and runtime.recovery
    assert not runtime._start_context["measurement_valid"]
    assert not commands(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("watts", [2200, 3000])
async def test_unknown_restart_consumption_is_reserved_without_phantom_surplus(watts):
    runtime, hass = paired_runtime()
    runtime.store.data["leases"]["a"]["watts"] = watts
    await runtime.start()
    assert runtime.isolated_reserve_w == watts
    assert runtime.result.budget_w == 2500
    assert not commands(hass)
    assert runtime.result.start_power["b"]["available_w"] == max(0, 2500 - watts)


@pytest.mark.asyncio
async def test_number_isolation_reserves_configured_maximum_not_old_minimum():
    runtime, hass = paired_runtime(kind="number")
    hass.states.set("sensor.load", 300, {"unit_of_measurement": "W"})
    await runtime.start()
    assert runtime.isolated_reserve_w == 16 * 230 - 300
    assert not commands(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("meter", ["unavailable", "old", "wrong_unit", "restored"])
async def test_only_fresh_dedicated_power_reduces_unknown_future_reservation(meter):
    runtime, hass = paired_runtime()
    hass.states.set("sensor.load", "unavailable" if meter == "unavailable" else 800,
                    {"unit_of_measurement": "kWh" if meter == "wrong_unit" else "W",
                     **({"restored": True} if meter == "restored" else {})},
                    age=999 if meter == "old" else 0)
    await runtime.start()
    assert runtime.isolated_reserve_w == 1000
    assert len(commands(hass, "switch.healthy")) == 1
    assert not commands(hass, "switch.load")


@pytest.mark.asyncio
async def test_valid_exclusive_live_power_is_already_inside_p1():
    runtime, hass = paired_runtime()
    hass.states.set("sensor.load", 800, {"unit_of_measurement": "W"})
    await runtime.start()
    assert runtime.isolated_reserve_w == 200
    assert runtime.result.budget_w == 2500
    assert not commands(hass, "switch.load")


@pytest.mark.asyncio
@pytest.mark.parametrize("returned", ["on", "off"])
async def test_lease_returns_without_replay_and_with_fresh_minimum_timing(returned):
    runtime, hass = paired_runtime()
    await runtime.start()
    await runtime.tick()  # Acknowledge unrelated healthy command.
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", returned)
    hass.states.set("sensor.load", 1000 if returned == "on" else 0,
                    {"unit_of_measurement": "W"})
    before = time.monotonic()
    await runtime.tick()
    state = runtime.states["a"]
    assert "a" not in runtime.recovery and not runtime.source_isolated_devices
    assert state.owned is (returned == "on") and state.on is (returned == "on")
    assert (state.last_on if returned == "on" else state.last_off) >= before
    assert not commands(hass, "switch.load")
    if returned == "on":
        await runtime.tick()
        assert not commands(hass, "switch.load")


@pytest.mark.asyncio
async def test_outage_and_requested_solar_survive_another_restart():
    first, hass = paired_runtime()
    await first.start()
    saved = deepcopy(first._snapshot())
    second, again = paired_runtime()
    again.states.set("switch.healthy", "on")
    second.store.data = saved
    await second.start()
    assert second.mode == "solar" and "a" in second.recovery
    assert second._snapshot()["leases"]["a"] == saved["leases"]["a"]
    assert not commands(again)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["observe", "paused"])
async def test_explicit_mode_while_isolated_survives_return_and_reboot(mode):
    runtime, hass = paired_runtime()
    runtime.device_modes["b"] = "disabled"
    runtime.store.data["device_modes"]["b"] = "disabled"
    await runtime.start()
    await runtime.set_mode(mode)
    await runtime.set_auto_resume_after_restart(False)
    saved = deepcopy(runtime._snapshot())
    restarted, again = paired_runtime()
    restarted.store.data = saved
    await restarted.start()
    assert restarted.mode == mode and restarted.restart_requested_mode is None
    again.states.set("switch.load", "off")
    await restarted.tick()
    assert restarted.mode == mode and not restarted.recovery
    assert not commands(again)


@pytest.mark.asyncio
async def test_true_command_fault_keeps_site_restart_hold_and_is_not_quarantined():
    runtime, hass = paired_runtime()
    runtime.store.data["faults"] = {"a": "Geen opdrachtbevestiging: handmatige controle nodig"}
    await runtime.start()
    assert runtime.restart_blocking and runtime.mode == "observe"
    assert not runtime.source_isolated_devices and not commands(hass)
    hass.states.set("switch.load", "on")
    await runtime.tick()
    assert runtime.faults and not runtime._start_context["can_increase"]
    assert not commands(hass)


@pytest.mark.asyncio
async def test_pending_command_keeps_other_start_serialized_despite_local_isolation():
    runtime, hass = paired_runtime()
    await runtime.start()
    assert runtime.pending and runtime.pending["id"] == "b"
    hass.services.respond = False
    hass.states.set("switch.healthy", "off")
    count = len(commands(hass))
    await runtime.tick()
    assert runtime.pending and not runtime._start_context["can_increase"]
    assert len(commands(hass)) == count


@pytest.mark.asyncio
async def test_live_owned_power_outage_is_local_and_cannot_stop_protected_cycle():
    runtime, hass = paired_runtime(protected=True)
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.load", 1000, {"unit_of_measurement": "W"})
    await runtime.start()
    await runtime.tick()
    hass.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
    runtime.states["a"].last_on -= 1000
    hass.states.set("switch.healthy", "off")
    runtime.states["b"].owned = False
    runtime.last_issued -= 10
    hass.states.set("sensor.grid", -2500, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert "a" in runtime.source_isolated_devices and runtime.mode == "solar"
    assert runtime.states["a"].on and runtime.states["a"].owned
    assert not commands(hass, "switch.load")
    assert commands(hass, "switch.healthy")


@pytest.mark.asyncio
async def test_unprotected_owned_bad_meter_cannot_generate_engine_stop_or_direct_command():
    runtime, hass = paired_runtime()
    runtime.store.data["device_modes"]["b"] = "disabled"
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.load", 1000, {"unit_of_measurement": "W"})
    await runtime.start()
    runtime.states["a"].last_on -= 1000
    hass.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.result.action is None
    assert runtime.managed_w == 0 and runtime.energy_estimated
    daily_before = (runtime.states["a"].daily_runtime_s, runtime.states["a"].daily_energy_kwh)
    runtime._update_daily_runtime(datetime.now(timezone.utc), 30)
    assert (runtime.states["a"].daily_runtime_s, runtime.states["a"].daily_energy_kwh) == daily_before
    await runtime._send(Action("a", 0, "synthetic phase release"), time.monotonic())
    await runtime._send(Action("a", 1000, "synthetic deadline"), time.monotonic())
    assert not commands(hass, "switch.load")
    assert runtime.states["a"].owned and runtime.states["a"].on


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["boost", "manual_start", "manual_stop"])
async def test_manual_device_commands_cannot_override_isolation(operation):
    runtime, hass = paired_runtime()
    await runtime.start()
    with pytest.raises(HomeAssistantError, match="tijdelijk apart gehouden"):
        await getattr(runtime, operation)("a")
    assert not commands(hass, "switch.load")
    assert "a" in runtime.recovery


@pytest.mark.asyncio
async def test_return_after_live_status_outage_restarts_minimum_once():
    runtime, hass = paired_runtime()
    runtime.store.data["device_modes"]["b"] = "disabled"
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.load", 1000, {"unit_of_measurement": "W"})
    await runtime.start()
    runtime.states["a"].last_on -= 1000
    hass.states.set("switch.load", "unavailable")
    await runtime.tick()
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "on")
    before = time.monotonic()
    await runtime.tick()
    renewed = runtime.states["a"].last_on
    assert renewed >= before
    await runtime.tick()
    assert runtime.states["a"].last_on == renewed
    assert not commands(hass, "switch.load")


@pytest.mark.asyncio
@pytest.mark.parametrize("use_map", [False, True])
async def test_isolated_future_load_reserves_individual_phase_room(use_map):
    runtime, hass = paired_runtime()
    runtime.configs["a"]["nominal_w"] = 300
    runtime.configs["b"].update(nominal_w=300, phase_hint="l2")
    runtime.entry.options["devices"][0]["nominal_w"] = 300
    runtime.entry.options["devices"][1].update(nominal_w=300, phase_hint="l2")
    runtime.store.data["leases"]["a"]["watts"] = 300
    runtime.phase_settings.update(enabled=True, control_starts=True,
        use_learned_device_map=use_map, learning_enabled=False,
        phase_1_entity="sensor.phase_one", phase_2_entity="sensor.phase_two",
        phase_3_entity="sensor.phase_three", limit_w=7000, margin_w=0,
        start_headroom_w=0, stale_s=120)
    for entity, watts in (("sensor.phase_one", 0), ("sensor.phase_two", 6500),
                          ("sensor.phase_three", 0)):
        hass.states.set(entity, watts, {"unit_of_measurement": "W"})
    await runtime.start()
    assert runtime.phase.valid and runtime.isolated_reserve_w == 300
    assert runtime._start_context["max_increase_w"] == (None if use_map else 200)
    if use_map:
        assert runtime._start_context["device_increase_limits"]["b"] == 200
    assert not commands(hass)


@pytest.mark.asyncio
async def test_source_loss_between_observation_and_direct_dispatch_still_isolated():
    runtime, hass = paired_runtime()
    runtime.store.data["device_modes"]["b"] = "disabled"
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.load", 1000, {"unit_of_measurement": "W"})
    await runtime.start()
    assert not runtime.source_isolated_devices
    hass.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
    assert not runtime.states["a"].fault  # The next observation has not run yet.
    await runtime._send(Action("a", 0, "dispatch after source loss"), time.monotonic())
    assert not commands(hass, "switch.load")


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["unavailable", "negative", "overlap"])
async def test_unowned_required_meter_failure_at_dispatch_prevents_physical_start(source):
    runtime, hass = build(power=True)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    runtime._observe(time.monotonic())
    assert runtime.states["a"].available and not runtime.states["a"].fault
    if source == "overlap":
        runtime.settings["pv_entity"] = "sensor.load"
    else:
        hass.states.set("sensor.load", "unavailable" if source == "unavailable" else -100,
                        {"unit_of_measurement": "W"})
    await runtime._send(Action("a", 1000, "dispatch after required meter failed"), time.monotonic())
    assert not commands(hass)
    assert not runtime.states["a"].owned and runtime.pending is None
    assert not runtime.store.saves


@pytest.mark.asyncio
async def test_unowned_number_bounds_changed_at_dispatch_prevent_setting_or_enable():
    runtime, hass = build(kind="number", device={"control_unit": "A"})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    runtime._observe(time.monotonic())
    assert runtime.states["a"].available and not runtime.states["a"].fault
    hass.states.set("number.amps", 6, {"min": 6, "max": 10, "step": 1,
                                      "unit_of_measurement": "A"})
    await runtime._send(Action("a", 16 * 230, "dispatch after regulator bounds changed"), time.monotonic())
    assert not commands(hass)
    assert not runtime.states["a"].owned and runtime.pending is None


@pytest.mark.asyncio
@pytest.mark.parametrize("native_value, start_allowed", [(0, True), (17, False)])
async def test_inactive_number_native_zero_may_start_but_out_of_native_value_cannot(native_value, start_allowed):
    runtime, hass = build(kind="number", device={"control_unit": "A"})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.set("number.amps", native_value, {"min": 0, "max": 16, "step": 1,
                                                  "unit_of_measurement": "A"})
    await runtime._send(Action("a", 6 * 230, "start within native limits"), time.monotonic())
    assert bool(commands(hass)) is start_allowed
    if start_allowed:
        assert commands(hass) == [
            ("number", "set_value", {"entity_id": "number.amps", "value": 6.0}),
            ("switch", "turn_on", {"entity_id": "switch.load"})]
    else:
        assert not runtime.states["a"].owned and runtime.pending is None
