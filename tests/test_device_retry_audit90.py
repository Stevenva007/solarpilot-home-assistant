"""Independent 300-second recovery acceptance tests using explicit HA doubles.

Runtime clocks are replaced per module rather than patching the shared time
module, so asyncio deadlines retain their real monotonic clock.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
import time

import pytest

from custom_components.solar_pilot import runtime as runtime_module
from custom_components.solar_pilot import device_retry as retry_module
from custom_components.solar_pilot.engine import Action
from test_runtime import build

class Clock:
    def __init__(self):
        self.wall = time.time()
        self.mono = time.monotonic()
    def advance(self, seconds):
        self.wall += seconds
        self.mono += seconds

def install_clock(monkeypatch):
    clock = Clock()
    replacement = SimpleNamespace(time=lambda: clock.wall, monotonic=lambda: clock.mono)
    monkeypatch.setattr(runtime_module, "time", replacement)
    monkeypatch.setattr(retry_module, "time", replacement)
    return clock

def fresh(hass, entity, state, clock, attrs=None):
    hass.states.set(entity, state, attrs or {})
    obj = hass.states.get(entity)
    obj.last_reported = obj.last_updated = datetime.fromtimestamp(clock.wall, timezone.utc)

def reports(hass, clock, *, active="off", grid=-2500):
    fresh(hass, "switch.load", active, clock)
    fresh(hass, "sensor.grid", grid, clock, {"unit_of_measurement": "W"})
    fresh(hass, "sensor.load", 0 if active == "off" else 1000,
          clock, {"unit_of_measurement": "W"})

def physical(hass):
    return [call for call in hass.services.calls if call[0] != "persistent_notification"]

async def failed_start(monkeypatch):
    clock = install_clock(monkeypatch)
    runtime, hass = build(device={"nominal_w": 1000})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    reports(hass, clock)
    hass.services.fail = True
    await runtime.tick()
    hass.services.fail = False
    assert len(physical(hass)) == 1
    assert runtime.device_retry.waiting("a")
    assert not runtime.faults
    return runtime, hass, clock

@pytest.mark.asyncio
async def test_failed_start_waits_300_seconds_without_error_notification(monkeypatch):
    runtime, hass, clock = await failed_start(monkeypatch)
    assert not [call for call in hass.services.calls if call[0] == "persistent_notification"]
    for advance in (1, 100, 198):
        clock.advance(advance)
        reports(hass, clock)
        await runtime.tick()
        assert len(physical(hass)) == 1
        assert runtime.device_retry.waiting("a")
    clock.advance(1)
    reports(hass, clock)
    await runtime.tick()
    assert not runtime.device_retry.waiting("a")
    assert len(physical(hass)) == 2
    assert physical(hass)[-1][:2] == ("switch", "turn_on")

@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["grid", "mode", "participation", "demand", "interlock"])
async def test_recovery_replans_current_conditions_and_never_replays_start(monkeypatch, changed):
    runtime, hass, clock = await failed_start(monkeypatch)
    clock.advance(300)
    reports(hass, clock, grid=500 if changed == "grid" else -2500)
    if changed == "mode":
        runtime.mode = "paused"
    elif changed == "participation":
        runtime.device_modes["a"] = "disabled"
    elif changed == "demand":
        runtime.configs["a"]["condition_entity"] = "input_boolean.demand"
        fresh(hass, "input_boolean.demand", "off", clock)
    elif changed == "interlock":
        runtime.configs["a"]["interlock_entity"] = "input_boolean.release"
        fresh(hass, "input_boolean.release", "off", clock)
    await runtime.tick()
    assert len(physical(hass)) == 1
    assert not runtime.faults

@pytest.mark.asyncio
@pytest.mark.parametrize("report", ["old", "restored", "unavailable"])
async def test_stale_or_restored_report_never_confirms_failed_start(monkeypatch, report):
    runtime, hass, clock = await failed_start(monkeypatch)
    old_state = hass.states.get("switch.load")
    clock.advance(300)
    fresh(hass, "sensor.grid", -2500, clock, {"unit_of_measurement": "W"})
    if report == "old":
        hass.states.data["switch.load"] = old_state
    else:
        fresh(hass, "switch.load", "off" if report == "restored" else "unavailable",
              clock, {"restored": True} if report == "restored" else {})
    await runtime.tick()
    assert runtime.device_retry.waiting("a")
    assert len(physical(hass)) == 1
    assert runtime.states["a"].owned
    assert runtime.isolated_reserve_w == 0
    assert runtime.store.data["leases"]["a"]["watts"] >= 1000

@pytest.mark.asyncio
async def test_successful_start_seen_after_exception_is_adopted_without_second_turn_on(monkeypatch):
    runtime, hass, clock = await failed_start(monkeypatch)
    clock.advance(300)
    reports(hass, clock, active="on")
    await runtime.tick()
    assert not runtime.device_retry.waiting("a")
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert len(physical(hass)) == 1

@pytest.mark.asyncio
async def test_failed_stop_keeps_unknown_journal_without_replaying_obsolete_off(monkeypatch):
    clock = install_clock(monkeypatch)
    runtime, hass = build(device={"nominal_w": 1000})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    state = runtime.states["a"]
    state.owned = state.on = state.observed_once = True
    state.target_w = 1000
    reports(hass, clock, active="on", grid=-2500)
    hass.services.fail = True
    await runtime._send(Action("a", 0, "Oude stopvraag"), clock.mono)
    hass.services.fail = False
    assert runtime.device_retry.waiting("a")
    clock.advance(100)
    reports(hass, clock, active="unavailable")
    await runtime.tick()
    assert runtime.isolated_reserve_w == 0
    clock.advance(200)
    reports(hass, clock, active="on", grid=-2500)
    await runtime.tick()
    assert not runtime.device_retry.waiting("a")
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert len(physical(hass)) == 1

@pytest.mark.asyncio
async def test_saved_retry_deadline_survives_restart_without_replaying_command(monkeypatch):
    runtime, hass, clock = await failed_start(monkeypatch)
    saved = runtime._snapshot()
    clock.advance(100)
    restarted, restored_hass = build(device={"nominal_w": 1000})
    restarted.store.data = saved
    reports(restored_hass, clock)
    await restarted.start()
    try:
        assert restarted.device_retry.waiting("a")
        assert not physical(restored_hass)
        clock.advance(199)
        reports(restored_hass, clock)
        await restarted.tick()
        assert not physical(restored_hass)
        clock.advance(1)
        reports(restored_hass, clock)
        await restarted.tick()
        assert len(physical(restored_hass)) == 1
        assert physical(restored_hass)[0][:2] == ("switch", "turn_on")
    finally:
        await restarted.close()

@pytest.mark.asyncio
async def test_changed_number_setting_is_left_to_current_operator(monkeypatch):
    clock = install_clock(monkeypatch)
    runtime, hass = build(kind="number", device={"control_unit": "A"})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    reports(hass, clock)
    hass.services.fail = True
    await runtime.tick()
    hass.services.fail = False
    assert runtime.device_retry.waiting("a")
    assert len(physical(hass)) == 1
    clock.advance(300)
    reports(hass, clock, active="on")
    fresh(hass, "number.amps", 9, clock,
          {"min": 6, "max": 16, "step": 1, "unit_of_measurement": "A"})
    await runtime.tick()
    assert not runtime.states["a"].owned
    assert runtime.states["a"].manual_until > clock.mono
    assert len(physical(hass)) == 1

@pytest.mark.asyncio
async def test_protected_script_does_not_rearm_after_failed_start(monkeypatch):
    clock = install_clock(monkeypatch)
    runtime, hass = build(kind="script", device={"non_interruptible": True})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    reports(hass, clock)
    hass.services.fail = True
    await runtime.tick()
    hass.services.fail = False
    assert len(physical(hass)) == 1
    assert not runtime.states["a"].cycle_armed
    clock.advance(300)
    reports(hass, clock)
    fresh(hass, "binary_sensor.running", "off", clock)
    await runtime.tick()
    assert not runtime.states["a"].cycle_armed
    assert len(physical(hass)) == 1

@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_command_fault", [False, True])
async def test_global_auto_can_be_selected_while_one_offline_load_is_quarantined(legacy_command_fault):
    from test_restart_isolation53 import paired_runtime, commands

    runtime, hass = paired_runtime()
    # Exceed the measured solar pool deliberately: an estimated offline load
    # must neither consume that pool nor create synthetic owned-power credit.
    runtime.configs["a"]["nominal_w"] = 3000
    hass.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
    runtime.store.data["mode"] = "observe"
    if legacy_command_fault:
        runtime.store.data["faults"] = {
            "a": "Opdrachtfout: HomeAssistantError; controleer het toestel"
        }
    await runtime.start()
    try:
        assert runtime.mode == "observe"
        assert not commands(hass)
        await runtime.set_mode("solar")
        assert runtime.mode == "solar"
        assert runtime.isolated_reserve_w == 0
        assert runtime.grid_w == -2500
        assert runtime._power("sensor.load")[0] is None
        assert runtime.result.start_power["b"]["available_w"] >= 1000
        assert not commands(hass, "switch.load")
        assert commands(hass, "switch.healthy") == [
            ("switch", "turn_on", {"entity_id": "switch.healthy"})
        ]
        assert not runtime.states["a"].available
        assert runtime.store.data["leases"]["a"]["watts"] >= 1000
    finally:
        await runtime.close()

@pytest.mark.asyncio
async def test_prolonged_unavailability_has_no_retry_limit_or_notification_spam(monkeypatch):
    runtime, hass, clock = await failed_start(monkeypatch)
    for _ in range(24):
        clock.advance(300)
        reports(hass, clock, active="unavailable")
        await runtime.tick()
        assert runtime.device_retry.waiting("a")
        assert not runtime.faults
        assert len(physical(hass)) == 1
        assert runtime.isolated_reserve_w == 0
        assert runtime.store.data["leases"]["a"]["watts"] >= 1000
    assert not [call for call in hass.services.calls if call[0] == "persistent_notification"]
    clock.advance(300)
    reports(hass, clock, grid=500)
    await runtime.tick()
    assert not runtime.device_retry.waiting("a")
    assert len(physical(hass)) == 1

@pytest.mark.asyncio
async def test_configuration_value_error_is_not_hidden_as_temporary_unavailability(monkeypatch):
    clock = install_clock(monkeypatch)
    runtime, hass = build(device={"nominal_w": 1000})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    reports(hass, clock)
    async def invalid_call(domain, action, data, blocking=False):
        hass.services.calls.append((domain, action, data))
        raise ValueError("Invalid configured actuator value")
    hass.services.async_call = invalid_call
    await runtime.tick()
    assert "a" in runtime.faults
    assert not runtime.device_retry.waiting("a")
    initial = len(physical(hass))
    clock.advance(300)
    reports(hass, clock)
    await runtime.tick()
    assert len(physical(hass)) == initial
    assert "a" in runtime.faults

@pytest.mark.asyncio
async def test_explicit_manual_takeover_cancels_retry_and_cannot_re_adopt_later(monkeypatch):
    runtime, hass, clock = await failed_start(monkeypatch)
    runtime.mode = "paused"
    await runtime.takeover("a")
    assert not runtime.device_retry.waiting("a")
    assert not runtime.states["a"].owned
    assert runtime.device_modes["a"] == "disabled"
    clock.advance(300)
    reports(hass, clock, active="on", grid=500)
    await runtime.tick()
    assert not runtime.states["a"].owned
    assert runtime.states["a"].on
    assert len(physical(hass)) == 1
    assert "a" not in runtime.store.data["leases"]

@pytest.mark.asyncio
async def test_orphan_legacy_fault_cannot_claim_an_external_on_device(monkeypatch):
    clock = install_clock(monkeypatch)
    runtime, hass = build(device={"nominal_w": 1000})
    reports(hass, clock, active="on", grid=500)
    runtime.store.data = {
        "mode": "observe", "device_modes": {"a": "auto"}, "leases": {},
        "faults": {"a": "Opdrachtfout: HomeAssistantError; controleer het toestel"},
    }
    await runtime.start()
    try:
        clock.advance(300)
        reports(hass, clock, active="on", grid=500)
        await runtime.tick()
        assert not runtime.states["a"].owned
        assert runtime.states["a"].on
        assert "a" not in runtime.store.data["leases"]
        assert not physical(hass)
    finally:
        await runtime.close()

@pytest.mark.asyncio
async def test_reset_of_unrelated_off_fault_cannot_clear_an_unknown_command(monkeypatch):
    from copy import deepcopy
    from homeassistant.exceptions import HomeAssistantError

    runtime, hass, clock = await failed_start(monkeypatch)
    runtime.configs["b"] = {
        **runtime.configs["a"], "id": "b", "name": "Ander testtoestel",
        "control_entity": "switch.healthy",
    }
    runtime.states["b"] = type(runtime.states["a"])()
    runtime.faults["b"] = "Ongeldige configuratie"
    fresh(hass, "switch.healthy", "off", clock)
    fresh(hass, "switch.load", "unavailable", clock)
    journal = deepcopy(runtime.device_retry.snapshot()["records"]["a"])

    with pytest.raises(HomeAssistantError, match="schakel eerst veilig uit"):
        await runtime.reset()

    assert runtime.device_retry.command_waiting("a")
    assert runtime.device_retry.snapshot()["records"]["a"] == journal
    assert runtime.faults["b"] == "Ongeldige configuratie"
    assert runtime.states["a"].owned
    assert len(physical(hass)) == 1
