"""Restart reconciliation against HA doubles, never real actuator services."""
from copy import deepcopy
import time

import pytest

from test_runtime import build
from test_dishwasher import setup as dishwasher_setup


def actuator_calls(hass):
    return [call for call in hass.services.calls if call[0] != "persistent_notification"]


def saved_lease(runtime, *, mode="solar", watts=1000, **extra):
    return {
        "mode": mode,
        "device_modes": {"a": "auto"},
        "leases": {"a": {"watts": watts, "name": runtime.configs["a"]["name"]}},
        **extra,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("late_state", ["on", "off"])
async def test_late_switch_state_reconciles_read_only_and_resumes_saved_solar(late_state):
    runtime, hass = build(device={"min_on_s": 600})
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "unavailable")
    runtime.store.data = saved_lease(runtime)

    await runtime.start()
    assert runtime.mode == "solar" and "a" in runtime.recovery
    assert not actuator_calls(hass)

    hass.states.set("switch.load", late_state)
    await runtime.tick()

    assert not runtime.recovery and runtime.mode == "solar"
    assert runtime.states["a"].on is (late_state == "on")
    assert runtime.states["a"].owned is (late_state == "on")
    assert runtime.states["a"].target_w == (1000 if late_state == "on" else 0)
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_dehumidifier_may_start_again_under_normal_solar_rules_after_late_off():
    runtime, hass = build(device={"name": "Ontvochtiger", "nominal_w": 350})
    hass.states.set("switch.load", "unavailable")
    runtime.store.data = saved_lease(runtime, watts=350)
    await runtime.start()

    hass.states.set("switch.load", "off")
    await runtime.tick()
    await runtime.tick()

    assert runtime.mode == "solar" and not runtime.recovery
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert actuator_calls(hass) == [
        ("switch", "turn_on", {"entity_id": "switch.load"}),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("prior_mode", ["observe", "paused"])
async def test_explicit_prior_non_solar_mode_is_preserved_after_late_reconciliation(prior_mode):
    runtime, hass = build()
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "unavailable")
    # A saved intent marks a known previous user choice rather than a beta.46
    # temporary Observatie state caused by an interrupted restart.
    runtime.store.data = saved_lease(runtime, mode=prior_mode,
                                    restart_requested_mode=prior_mode,
                                    auto_resume_after_restart=False)
    await runtime.start()

    hass.states.set("switch.load", "off")
    await runtime.tick()

    assert not runtime.recovery and runtime.mode == prior_mode
    assert not actuator_calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("chosen_mode", ["observe", "paused"])
async def test_manual_mode_choice_cancels_automatic_solar_resume(chosen_mode):
    runtime, hass = build()
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "unavailable")
    runtime.store.data = saved_lease(runtime)
    await runtime.start()

    await runtime.set_mode(chosen_mode)
    hass.states.set("switch.load", "off")
    await runtime.tick()

    assert not runtime.recovery and runtime.mode == chosen_mode
    assert not actuator_calls(hass)

    # beta.58 distinguishes cancelling today's queued resume from choosing
    # to preserve Pause across a later restart.
    await runtime.set_auto_resume_after_restart(False)
    saved = deepcopy(runtime._snapshot())
    restarted, again_hass = build()
    again_hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    restarted.store.data = saved
    await restarted.start()
    assert restarted.mode == chosen_mode
    assert not actuator_calls(again_hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["missing", "unavailable", "restored"])
async def test_missing_or_cached_switch_never_resolves_restart_lease(source):
    runtime, hass = build()
    if source == "missing":
        del hass.states.data["switch.load"]
    elif source == "restored":
        hass.states.set("switch.load", "on", {"restored": True})
    else:
        hass.states.set("switch.load", "unavailable")
    runtime.store.data = saved_lease(runtime)

    await runtime.start()
    for _ in range(3):
        await runtime.tick()

    assert "a" in runtime.recovery
    assert runtime.mode == "solar"
    assert not runtime.states["a"].owned
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_solar_resume_intent_survives_second_restart_while_entity_is_missing():
    first, first_hass = build(device={"min_on_s": 600})
    first_hass.states.set("switch.load", "unavailable")
    first.store.data = saved_lease(first)
    await first.start()
    interrupted = deepcopy(first._snapshot())

    second, second_hass = build(device={"min_on_s": 600})
    second_hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    second_hass.states.set("switch.load", "unavailable")
    second.store.data = interrupted
    await second.start()
    assert second.mode == "solar" and "a" in second.recovery

    second_hass.states.set("switch.load", "on")
    await second.tick()

    assert second.mode == "solar" and not second.recovery
    assert second.states["a"].owned
    assert not actuator_calls(first_hass)
    assert not actuator_calls(second_hass)


@pytest.mark.asyncio
async def test_beta46_interrupted_observe_snapshot_migrates_resume_intent_once():
    runtime, hass = build()
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "unavailable")
    runtime.store.data = saved_lease(runtime, mode="observe")
    await runtime.start()

    hass.states.set("switch.load", "off")
    await runtime.tick()

    assert runtime.mode == "solar" and not runtime.recovery
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_observe_without_interrupted_lease_remains_observe():
    runtime, hass = build()
    runtime.store.data = {"mode": "observe", "device_modes": {"a": "auto"}}

    await runtime.start()

    assert runtime.mode == "observe"
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_disabled_automatic_resume_with_interrupted_lease_stays_paused():
    runtime, hass = build()
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "unavailable")
    runtime.store.data = saved_lease(runtime, mode="paused", auto_resume_after_restart=False)
    await runtime.start()

    hass.states.set("switch.load", "off")
    await runtime.tick()

    assert runtime.mode == "paused" and not runtime.recovery
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_legacy_observe_with_real_fault_does_not_infer_solar_resume():
    runtime, hass = build()
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "unavailable")
    fault = "Opdrachtfout: HomeAssistantError; controleer het toestel"
    runtime.store.data = saved_lease(runtime, mode="observe", faults={"a": fault})
    await runtime.start()

    hass.states.set("switch.load", "off")
    await runtime.tick()

    assert runtime.mode == "observe" and runtime.faults["a"] == fault
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_null_restart_intent_preserves_observe_despite_interrupted_lease():
    runtime, hass = build()
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "unavailable")
    runtime.store.data = saved_lease(runtime, mode="observe", restart_requested_mode=None)
    await runtime.start()

    hass.states.set("switch.load", "off")
    await runtime.tick()

    assert runtime.mode == "observe" and not runtime.recovery
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_current_number_setting_different_from_saved_target_is_not_replayed_or_reduced():
    runtime, hass = build(kind="number", device={"min_on_s": 600})
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "on")
    hass.states.set("number.amps", 10, {
        "min": 6, "max": 16, "step": 1, "unit_of_measurement": "A",
    })
    runtime.store.data = saved_lease(runtime, watts=1380)

    await runtime.start()

    assert runtime.mode == "solar" and not runtime.recovery
    assert runtime.states["a"].on
    assert not runtime.states["a"].owned
    assert runtime.states["a"].target_w == 0
    assert runtime.states["a"].manual_until > time.monotonic()
    assert hass.states.get("number.amps").state == "10"
    assert not actuator_calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("cached_entity", ["switch.load", "number.amps"])
async def test_restored_number_actuator_or_setting_keeps_restart_pending(cached_entity):
    runtime, hass = build(kind="number", device={"min_on_s": 600})
    hass.states.set("switch.load", "on")
    obj = hass.states.get(cached_entity)
    hass.states.set(cached_entity, obj.state, {**obj.attributes, "restored": True})
    runtime.store.data = saved_lease(runtime, watts=1380)

    await runtime.start()
    await runtime.tick()

    assert "a" in runtime.recovery and runtime.mode == "solar"
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_waiting_flag_distinguishes_automatic_status_retry_from_real_start_fault():
    waiting, waiting_hass = build()
    waiting_hass.states.set("switch.load", "unavailable")
    waiting.store.data = saved_lease(waiting)
    await waiting.start()
    assert waiting.restart_recovery_pending

    blocked, blocked_hass = attempted_dishwasher(
        fault="Opdrachtfout: HomeAssistantError; controleer het toestel")
    await blocked.start()
    assert "a" in blocked.recovery and "a" in blocked.faults
    assert not blocked.restart_recovery_pending
    assert not actuator_calls(waiting_hass)
    assert not actuator_calls(blocked_hass)


@pytest.mark.asyncio
async def test_restart_notification_is_dismissed_once_after_reliable_recovery():
    runtime, hass = build()
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "unavailable")
    runtime.store.data = saved_lease(runtime)
    await runtime.start()
    assert not [call for call in hass.services.calls if call[:2] == (
        "persistent_notification", "dismiss")]

    hass.states.set("switch.load", "off")
    for _ in range(3):
        await runtime.tick()

    dismissals = [call for call in hass.services.calls if call[:2] == (
        "persistent_notification", "dismiss")]
    assert dismissals == [
        ("persistent_notification", "dismiss", {"notification_id": "solar_pilot_test"}),
    ]
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_external_on_without_saved_lease_is_not_adopted():
    runtime, hass = build(device={"min_on_s": 600})
    hass.states.set("switch.load", "on")
    runtime.store.data = {"mode": "solar", "device_modes": {"a": "auto"}}

    await runtime.start()

    assert runtime.mode == "solar" and runtime.states["a"].on
    assert not runtime.states["a"].owned
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_latched_actuator_fault_survives_restart_and_late_known_state():
    runtime, hass = build(device={"min_on_s": 600})
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    hass.states.set("switch.load", "unavailable")
    fault = "Geen opdrachtbevestiging: handmatige controle nodig"
    runtime.store.data = saved_lease(runtime, faults={"a": fault})
    await runtime.start()

    hass.states.set("switch.load", "on")
    await runtime.tick()

    assert runtime.faults["a"] == fault
    assert runtime._snapshot()["faults"]["a"] == fault
    assert not actuator_calls(hass)


def attempted_dishwasher(*, mode="solar", fault=None):
    runtime, hass, cfg = dishwasher_setup()
    assert runtime._active(cfg) is False
    runtime.dishwasher.arm(cfg, runtime.dishwasher.readings["a"], time.time())
    runtime.dishwasher.sent(cfg, time.time())
    data = saved_lease(runtime, mode=mode, watts=2000,
                       dishwasher=runtime.dishwasher.snapshot())
    if fault:
        data["faults"] = {"a": fault}
    hass.states.set("sensor.dw_connection", "unavailable")
    runtime.store.data = data
    return runtime, hass


@pytest.mark.asyncio
@pytest.mark.parametrize("running_state", ["Running", "Washing", "Drying", "Paused"])
async def test_late_running_dishwasher_is_adopted_without_duplicate_start_or_stop(running_state):
    runtime, hass = attempted_dishwasher()
    await runtime.start()
    assert "a" in runtime.recovery
    assert runtime.dishwasher.tickets["a"]["attempted"]

    hass.states.set("sensor.dw_connection", "Connected")
    hass.states.set("sensor.dw_phase", running_state)
    await runtime.tick()
    await runtime.tick()

    assert not runtime.recovery and runtime.mode == "solar"
    assert "a" not in runtime.faults
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert not runtime.dishwasher.tickets["a"]["attempted"]
    assert runtime.dishwasher.tickets["a"]["confirmed"]
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_generated_dishwasher_restart_fault_survives_then_resolves_after_second_restart():
    first, first_hass = attempted_dishwasher()
    await first.start()
    interrupted = deepcopy(first._snapshot())

    second, second_hass, _cfg = dishwasher_setup()
    second_hass.states.set("sensor.dw_connection", "unavailable")
    second.store.data = interrupted
    await second.start()
    assert "a" in second.faults and "a" in second.recovery

    second_hass.states.set("sensor.dw_connection", "Connected")
    second_hass.states.set("sensor.dw_phase", "Running")
    await second.tick()

    assert second.mode == "solar" and not second.recovery
    assert "a" not in second.faults
    assert second.dishwasher.tickets["a"]["confirmed"]
    assert not actuator_calls(first_hass)
    assert not actuator_calls(second_hass)


@pytest.mark.asyncio
async def test_late_idle_dishwasher_does_not_replay_uncertain_start():
    runtime, hass = attempted_dishwasher()
    await runtime.start()

    hass.states.set("sensor.dw_connection", "Connected")
    hass.states.set("sensor.dw_phase", "Idle")
    for _ in range(3):
        await runtime.tick()

    assert "a" in runtime.recovery and "a" in runtime.faults
    assert runtime.dishwasher.tickets["a"]["attempted"]
    assert not runtime.dishwasher.tickets["a"]["armed"]
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_late_explicit_finished_dishwasher_resolves_without_rearming():
    runtime, hass = attempted_dishwasher()
    await runtime.start()

    hass.states.set("sensor.dw_connection", "Connected")
    hass.states.set("sensor.dw_phase", "Finished")
    await runtime.tick()

    assert not runtime.recovery and runtime.mode == "solar"
    assert "a" not in runtime.faults
    assert not runtime.states["a"].owned and not runtime.states["a"].on
    assert not runtime.dishwasher.tickets["a"]["attempted"]
    assert not runtime.dishwasher.tickets["a"]["armed"]
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_prior_pause_preserves_running_dishwasher_through_restart():
    runtime, hass, _cfg = dishwasher_setup()
    hass.states.set("sensor.dw_phase", "Running")
    runtime.store.data = saved_lease(runtime, mode="paused", watts=2000,
                                    restart_requested_mode="paused",
                                    auto_resume_after_restart=False)

    await runtime.start()
    await runtime.tick()

    assert runtime.mode == "paused" and runtime.states["a"].on
    assert not actuator_calls(hass)


@pytest.mark.asyncio
async def test_real_dishwasher_command_fault_is_not_cleared_by_running_report():
    fault = "Opdrachtfout: HomeAssistantError; controleer het toestel"
    runtime, hass = attempted_dishwasher(fault=fault)
    await runtime.start()
    hass.states.set("sensor.dw_connection", "Connected")
    hass.states.set("sensor.dw_phase", "Running")

    await runtime.tick()

    assert runtime.faults["a"] == fault
    assert not actuator_calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("boot_state", ["Finished", "Running", "unavailable"])
async def test_consumed_app_request_cannot_rearm_after_recovered_dishwasher_cycle(boot_state):
    runtime, hass, cfg = dishwasher_setup(
        dishwasher_arming_mode="app", dishwasher_remote_states="Enabled")
    assert runtime._active(cfg) is False
    runtime.dishwasher.arm(cfg, runtime.dishwasher.readings["a"], time.time())
    runtime.dishwasher.sent(cfg, time.time())
    wall = time.time()
    request = {
        "created": wall - 60, "not_before": wall - 60,
        "deadline": wall - 1, "expires": wall + 3600,
        "grid_allowed": True, "program": "Eco",
        "source_signature": runtime.dishwasher_app.signature(cfg),
    }
    # Waiting covers a crash after START but before its running callback. An
    # already-running saved cycle also must consume a stale remaining request.
    runtime.dishwasher_app.data["a"] = {
        "request": request, "remote": "Enabled",
        "cycle": {"status": "running" if boot_state == "Running" else "waiting"},
    }
    runtime.store.data = saved_lease(runtime, watts=2000,
        dishwasher=runtime.dishwasher.snapshot(),
        dishwasher_app=runtime.dishwasher_app.snapshot())
    hass.states.set("sensor.dw_phase", boot_state)

    await runtime.start()
    if boot_state == "unavailable":
        assert "a" in runtime.recovery
        hass.states.set("sensor.dw_phase", "Finished")
        await runtime.tick()
    assert not runtime.dishwasher_app.data["a"].get("request")

    hass.states.set("sensor.dw_phase", "Finished")
    await runtime.tick()
    hass.states.set("sensor.dw_phase", "Idle")
    for _ in range(3):
        await runtime.tick()

    assert not runtime.recovery
    assert not runtime.dishwasher.tickets["a"].get("armed")
    assert not runtime.dishwasher.tickets["a"].get("attempted")
    assert runtime.pending is None
    assert not actuator_calls(hass)
