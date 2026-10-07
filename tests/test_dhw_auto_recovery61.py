"""Automatic boiler recovery observes new evidence, never replays a command."""
from copy import deepcopy
from datetime import datetime, timezone

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.dhw_runtime import DHWManager, LEGACY_ACK_FAULT
from test_dhw_failure61 import failure_runtime, elapsed_tick, physical_calls, report, send


def advance(wall, mono, seconds):
    wall[0] += seconds
    mono[0] += seconds


def fresh(runtime, hass, wall, target=50, grid=-4000):
    """A new real-shaped HA report for all configured meter/guard inputs."""
    report(runtime, hass, wall, target)
    hass.states.get("sensor.grid").state = str(grid)
    stamp = datetime.fromtimestamp(wall[0], timezone.utc)
    for obj in hass.states.data.values():
        obj.last_updated = obj.last_reported = stamp


async def failed(monkeypatch, *, target=60, release=False, previous_owned=None):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    if previous_owned is not None:
        fresh(runtime, hass, wall, previous_owned)
        runtime.dhw.owned_target = previous_owned
        runtime.dhw.reading.actual_target_c = previous_owned
    await runtime.dhw._send(mono[0], target, release, "Test doelopdracht")
    advance(wall, mono, 181)
    fresh(runtime, hass, wall, previous_owned if previous_owned is not None else 50)
    await elapsed_tick(runtime, wall, mono, 0)
    assert runtime.dhw.fault and runtime.dhw.automatic_recovery
    return runtime, hass, wall, mono


async def mismatch_reports(runtime, hass, wall, mono, target=50):
    advance(wall, mono, 1)
    fresh(runtime, hass, wall, target)
    await elapsed_tick(runtime, wall, mono, 0)
    advance(wall, mono, 60)
    fresh(runtime, hass, wall, target)
    await elapsed_tick(runtime, wall, mono, 0)


@pytest.mark.asyncio
async def test_late_ack_finishes_once_without_new_call_or_action_clock(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    action_clock = runtime.last_issued_wall
    advance(wall, mono, 1)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert not runtime.dhw.fault and runtime.dhw.owned_target == 60
    assert runtime.dhw.last_success["confirmation"] == "automatic_late_ha_state"
    assert runtime.dhw.failed_command["review_kind"] == "automatic_late_ack"
    assert runtime.dhw.automatic_recovered_this_tick and runtime.dhw.recovery_barrier
    assert runtime.dhw.blocks_increase and runtime.last_issued_wall == action_clock
    assert runtime.dhw.recovery_budget is None and len(physical_calls(hass)) == 1
    await elapsed_tick(runtime, wall, mono, 0)
    assert runtime.dhw.recovery_barrier and len(physical_calls(hass)) == 1
    advance(wall, mono, 1)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert not runtime.dhw.recovery_barrier and not runtime.dhw.automatic_recovered_this_tick
    assert len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_matching_release_ack_drops_ownership_without_resending(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch, target=50, release=True, previous_owned=60)
    runtime.mode = "paused"
    advance(wall, mono, 1)
    fresh(runtime, hass, wall, 50)
    await elapsed_tick(runtime, wall, mono, 0)
    assert not runtime.dhw.fault and runtime.dhw.owned_target is None
    assert runtime.dhw.last_success["target_c"] == 50 and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_two_distinct_ordinary_reports_resolve_without_write_then_use_normal_policy(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    await mismatch_reports(runtime, hass, wall, mono)
    assert not runtime.dhw.fault and runtime.dhw.owned_target is None
    assert runtime.dhw.failed_command["review_kind"] == "automatic_observed_target"
    assert runtime.dhw.last_success is None and len(physical_calls(hass)) == 1
    assert runtime.dhw.recovery_budget["failure_streak"] == 1
    advance(wall, mono, 1)
    fresh(runtime, hass, wall)
    await elapsed_tick(runtime, wall, mono, 0)
    assert not runtime.dhw.recovery_barrier and len(physical_calls(hass)) == 1
    # Existing 1800 s optional-raise interval remains stronger than 300 s retry backoff.
    advance(wall, mono, 2000)
    fresh(runtime, hass, wall)
    await elapsed_tick(runtime, wall, mono, 0)
    assert len(physical_calls(hass)) == 2 and runtime.dhw.pending["target"] == 60
    assert runtime.dhw.pending["issued_wall"] == wall[0]


@pytest.mark.asyncio
async def test_same_report_aging_cannot_be_second_evidence(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    advance(wall, mono, 1)
    fresh(runtime, hass, wall)
    await elapsed_tick(runtime, wall, mono, 0)
    await elapsed_tick(runtime, wall, mono, 90)
    assert runtime.dhw.fault and runtime.dhw.automatic_recovery
    assert len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_target_change_resets_agreement_window(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch, target=55)
    advance(wall, mono, 1)
    fresh(runtime, hass, wall, 50)
    await elapsed_tick(runtime, wall, mono, 0)
    advance(wall, mono, 60)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert runtime.dhw.fault and runtime.dhw.automatic_recovery["candidate_target_c"] == 60
    advance(wall, mono, 60)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert not runtime.dhw.fault and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["restored", "stale", "target_unavailable", "temperature_unavailable", "wrong_unit",
                                "hygiene", "powerful", "native_off", "high_target", "guard_unknown", "future"])
async def test_invalid_or_protected_sources_reset_recovery_evidence(monkeypatch, bad):
    runtime, hass, wall, mono = await failed(monkeypatch)
    advance(wall, mono, 1)
    fresh(runtime, hass, wall)
    await elapsed_tick(runtime, wall, mono, 0)
    advance(wall, mono, 60)
    fresh(runtime, hass, wall)
    target = hass.states.get("water_heater.boiler")
    if bad == "restored":
        target.attributes["restored"] = True
    elif bad == "stale":
        target.last_reported = datetime.fromtimestamp(wall[0] - 500, timezone.utc)
    elif bad == "target_unavailable":
        target.state = "unavailable"
    elif bad == "temperature_unavailable":
        hass.states.get("sensor.water").state = "unavailable"
    elif bad == "wrong_unit":
        target.attributes["temperature_unit"] = "°F"
    elif bad == "hygiene":
        hass.states.get("binary_sensor.hygiene").state = "on"
    elif bad == "powerful":
        hass.states.get("switch.powerful").state = "on"
    elif bad == "native_off":
        target.state = "off"
    elif bad == "high_target":
        target.attributes["temperature"] = 62
    elif bad == "guard_unknown":
        hass.states.get("binary_sensor.hygiene").state = "unknown"
    else:
        target.last_reported = datetime.fromtimestamp(wall[0] + 6, timezone.utc)
    await elapsed_tick(runtime, wall, mono, 0)
    assert runtime.dhw.fault and "first_report_wall" not in runtime.dhw.automatic_recovery
    assert len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_small_future_report_cannot_shortcut_local_sixty_seconds(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    advance(wall, mono, 1)
    fresh(runtime, hass, wall)
    await elapsed_tick(runtime, wall, mono, 0)
    advance(wall, mono, 55)
    fresh(runtime, hass, wall)
    report(runtime, hass, wall, 50, offset=5)
    await elapsed_tick(runtime, wall, mono, 0)
    assert runtime.dhw.fault and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_arbitrary_intermediate_target_does_not_grant_automatic_control(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    await mismatch_reports(runtime, hass, wall, mono, 54)
    assert runtime.dhw.fault and runtime.dhw.automatic_recovery["state"] == "waiting_external_target"
    assert len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_failed_release_preserves_only_previous_confirmed_matching_ownership(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch, target=50, release=True, previous_owned=60)
    runtime.mode = "paused"
    await mismatch_reports(runtime, hass, wall, mono, 60)
    assert not runtime.dhw.fault and runtime.dhw.owned_target == 60
    assert len(physical_calls(hass)) == 1
    advance(wall, mono, 1)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert len(physical_calls(hass)) == 1
    advance(wall, mono, 300)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert len(physical_calls(hass)) == 2 and runtime.dhw.pending["release"]
    assert runtime.dhw.pending["target"] == 50


@pytest.mark.asyncio
async def test_restart_keeps_budget_but_drops_report_progress_and_requires_this_run_reports(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    advance(wall, mono, 1)
    fresh(runtime, hass, wall)
    await elapsed_tick(runtime, wall, mono, 0)
    snapshot = deepcopy(runtime.dhw.snapshot())
    advance(wall, mono, 60)
    runtime.dhw = DHWManager(runtime)
    runtime.dhw.restore(snapshot)
    assert runtime.dhw.recovery_budget == snapshot["recovery_budget"]
    assert "first_report_wall" not in runtime.dhw.automatic_recovery
    assert runtime.dhw.busy and runtime.dhw.owned_target is None and runtime.dhw.pending is None
    await elapsed_tick(runtime, wall, mono, 0)
    assert runtime.dhw.fault and len(physical_calls(hass)) == 1
    await mismatch_reports(runtime, hass, wall, mono)
    assert not runtime.dhw.fault and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("damage", [None, {"failure_streak": True}, {"next_attempt_wall": -1}, {"failure_streak": 0}])
async def test_missing_or_damaged_budget_cannot_shorten_restored_cooldown(monkeypatch, damage):
    runtime, hass, wall, mono = await failed(monkeypatch)
    snapshot = runtime.dhw.snapshot()
    if damage is None:
        snapshot.pop("recovery_budget")
    else:
        snapshot["recovery_budget"].update(damage)
    runtime.dhw = DHWManager(runtime)
    runtime.dhw.restore(snapshot)
    assert runtime.dhw.recovery_budget["failure_streak"] == 3
    assert runtime.dhw._recovery_remaining() == 3600
    assert len(physical_calls(hass)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["manual_hold", "unknown_fault", "different_binding", "invalid_journal"])
async def test_unrelated_authority_never_becomes_automatic_recovery(monkeypatch, guard):
    runtime, hass, wall, mono = await failed(monkeypatch)
    snapshot = runtime.dhw.snapshot()
    if guard == "manual_hold":
        snapshot["manual_hold"] = True
    elif guard == "unknown_fault":
        snapshot["fault"] = "Onbekende ernstige fout"
    elif guard == "different_binding":
        snapshot["target_entity"] = "water_heater.other"
    else:
        snapshot["automatic_recovery"]["issued_wall"] = True
    runtime.dhw = DHWManager(runtime)
    runtime.dhw.restore(snapshot)
    await mismatch_reports(runtime, hass, wall, mono)
    assert runtime.dhw.fault and not runtime.dhw.automatic_recovery
    assert len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_exact_legacy_timeout_auto_checks_without_inventing_an_old_requested_target(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    runtime.dhw.restore({"target_entity": "water_heater.boiler", "config_revision": runtime.dhw.config["config_revision"],
                         "fault": LEGACY_ACK_FAULT, "needs_review": True, "owned_target": 60})
    assert runtime.dhw.automatic_recovery["requested_target_c"] is None
    assert runtime.dhw.failed_command is None and not runtime.dhw.needs_review
    await mismatch_reports(runtime, hass, wall, mono)
    assert not runtime.dhw.fault and not physical_calls(hass)


@pytest.mark.asyncio
async def test_manual_takeover_cancels_automatic_recovery_but_retains_history(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    runtime.mode = "paused"
    await runtime.dhw.takeover()
    assert runtime.dhw.manual_hold and not runtime.dhw.auto_enabled
    assert runtime.dhw.automatic_recovery is None
    assert not runtime.dhw.overview()["automatic_recovery_pending"]
    assert runtime.dhw.failed_command["review_kind"] == "manual" and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_repeated_failure_budget_is_bounded_and_persisted(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    first = deepcopy(runtime.dhw.recovery_budget)
    assert first["next_attempt_wall"] - first["last_failure_wall"] == 300
    advance(wall, mono, 2000)
    runtime.dhw._record_recovery_failure()
    second = runtime.dhw.recovery_budget
    assert second["failure_streak"] == 2
    assert second["next_attempt_wall"] >= runtime.dhw.last_command_wall + 3600
    advance(wall, mono, 2000)
    runtime.dhw._record_recovery_failure()
    third = runtime.dhw.recovery_budget
    assert third["failure_streak"] == 3 and third["next_attempt_wall"] - third["last_failure_wall"] == 3600
    for _ in range(5):
        runtime.dhw._record_recovery_failure()
    assert runtime.dhw._recovery_remaining() == 3600 and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_current_import_prevents_new_optional_raise_after_automatic_recovery(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    await mismatch_reports(runtime, hass, wall, mono)
    advance(wall, mono, 2000)
    fresh(runtime, hass, wall, grid=4000)
    await runtime.dhw.tick(mono[0], 4000, True, 0, True, datetime(2026, 10, 7, 14))
    assert not runtime.dhw.pending and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_target_change_while_saving_new_recovery_attempt_cancels_unsent_intent(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    await mismatch_reports(runtime, hass, wall, mono)
    advance(wall, mono, 2000)
    fresh(runtime, hass, wall)
    original_save = runtime.store.async_save
    async def changed_during_save(data):
        await original_save(data)
        if runtime.dhw.pending:
            report(runtime, hass, wall, 55)
    monkeypatch.setattr(runtime.store, "async_save", changed_during_save)
    await elapsed_tick(runtime, wall, mono, 0)
    assert not runtime.dhw.pending and len(physical_calls(hass)) == 1
    assert not runtime.dhw.fault


@pytest.mark.asyncio
async def test_service_error_subclass_is_a_known_new_failure_and_has_no_action_notification(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    class NativeServiceFailure(HomeAssistantError):
        pass
    original_call = hass.services.async_call
    async def failing_actuator(domain, action, data, blocking=False):
        if domain == "water_heater":
            hass.services.calls.append((domain, action, data))
            raise NativeServiceFailure("unknown result")
        await original_call(domain, action, data, blocking)
    monkeypatch.setattr(hass.services, "async_call", failing_actuator)
    await send(runtime, mono)
    assert runtime.dhw.failed_command["code"] == "service_error"
    assert runtime.dhw.automatic_recovery and not runtime.dhw.overview()["review_required"]
    assert all(call[0] != "persistent_notification" for call in hass.services.calls)
    advance(wall, mono, 20)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert not runtime.dhw.fault and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_a_new_unrelated_fault_revokes_automatic_recovery(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    runtime.dhw.fault = "Nieuwe onbekende fout"
    advance(wall, mono, 1)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert runtime.dhw.fault == "Nieuwe onbekende fout" and runtime.dhw.automatic_recovery is None
    assert runtime.dhw.overview()["review_required"] and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_second_failed_release_waits_a_full_hour_between_new_attempts(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch, target=50, release=True, previous_owned=60)
    runtime.mode = "paused"
    await mismatch_reports(runtime, hass, wall, mono, 60)
    advance(wall, mono, 300)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert len(physical_calls(hass)) == 2
    second_issued = runtime.dhw.pending["issued_wall"]
    advance(wall, mono, 181)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert runtime.dhw.recovery_budget["failure_streak"] == 2
    await mismatch_reports(runtime, hass, wall, mono, 60)
    advance(wall, mono, 901)
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert len(physical_calls(hass)) == 2 and wall[0] < second_issued + 3600
    advance(wall, mono, second_issued + 3601 - wall[0])
    fresh(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert len(physical_calls(hass)) == 3 and runtime.dhw.pending["target"] == 50
