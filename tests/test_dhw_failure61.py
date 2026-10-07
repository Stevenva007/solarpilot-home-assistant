"""Boiler failure evidence and explicit review, using HA API doubles only."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace as NS
import time

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot import dhw_runtime
from custom_components.solar_pilot.dhw_runtime import DHWManager
from test_dhw_runtime import setup, updates


def failure_runtime(monkeypatch, *, kind="water_heater"):
    runtime, hass = setup(kind=kind)
    hass.services.respond = False
    hass.states.set("sensor.water", 50, {"unit_of_measurement": "°C"})
    wall, mono = [time.time()], [1000.0]
    actual_monotonic = time.monotonic
    started = actual_monotonic()
    monkeypatch.setattr(dhw_runtime.time, "time", lambda: wall[0])
    # Keep asyncio's short service-feedback sleeps progressing in real time.
    monkeypatch.setattr(dhw_runtime.time, "monotonic", lambda: mono[0] + actual_monotonic() - started)
    monkeypatch.setattr(er, "async_get", lambda _hass: NS(
        async_get=lambda _eid: NS(platform="aquarea"), async_get_entity_id=lambda *_args: None))
    return runtime, hass, wall, mono


def report(runtime, hass, wall, target, *, offset=0):
    eid = runtime.dhw.config["target_entity"]
    if eid.startswith(("number.", "input_number.")):
        old = hass.states.get(eid)
        hass.states.set(eid, target, old.attributes)
    else:
        updates(hass, eid, temperature=target)
    obj = hass.states.get(eid)
    obj.last_updated = obj.last_reported = datetime.fromtimestamp(wall[0] + offset, timezone.utc)


async def send(runtime, mono, *, release=False):
    await runtime.dhw._send(mono[0], 60, release, "Test zonnebuffer")


async def elapsed_tick(runtime, wall, mono, seconds):
    wall[0] += seconds
    mono[0] += seconds
    await runtime.dhw.tick(mono[0], -4000, True, 0, True, datetime(2026, 10, 7, 14))


def physical_calls(hass):
    return [call for call in hass.services.calls if call[0] in (
        "water_heater", "climate", "number", "input_number")]


@pytest.mark.asyncio
async def test_timeout_preserves_requested_and_fresh_mismatching_report_before_pending_is_cleared(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    issued = wall[0]
    wall[0] += 170
    mono[0] += 170
    report(runtime, hass, wall, 50)
    await elapsed_tick(runtime, wall, mono, 11)

    row = runtime.dhw.overview()["failed_command"]
    assert row["code"] == "target_mismatch"
    assert row["requested_target_c"] == 60 and row["reported_target_c"] == 50
    assert row["issued_wall"] == issued and row["failed_wall"] == wall[0]
    assert row["waited_s"] == 181 and row["timeout_s"] == 180
    assert row["report_age_s"] == 11 and "60 °C" in row["reason"] and "50 °C" in row["reason"]
    assert datetime.fromisoformat(row["failed_at"]).timestamp() == pytest.approx(wall[0], abs=.000001)
    assert runtime.dhw.pending is None and runtime.dhw.fault
    assert runtime.store.data["dhw"]["failed_command"] == row
    assert runtime.dhw.overview()["failed_command_active"]
    assert len(physical_calls(hass)) == 1
    await elapsed_tick(runtime, wall, mono, 1)
    assert len(physical_calls(hass)) == 1 and runtime.dhw.failed_command == row


@pytest.mark.asyncio
async def test_optimistic_echo_aging_is_a_distinct_failure_not_a_real_ack(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    report(runtime, hass, wall, 60, offset=1)
    await elapsed_tick(runtime, wall, mono, 181)
    row = runtime.dhw.failed_command
    assert row["code"] == "report_before_confirmation"
    assert row["reported_target_c"] == 60 and row["report_age_s"] == 180
    assert runtime.dhw.last_success is None and runtime.dhw.fault
    assert len(physical_calls(hass)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["missing_stamp", "stale", "unavailable", "restored", "wrong_unit"])
async def test_missing_stale_and_unavailable_feedback_have_distinct_audit_reasons(monkeypatch, bad):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    report(runtime, hass, wall, 60)
    obj = hass.states.get("water_heater.boiler")
    expected = "target_unavailable"
    if bad == "missing_stamp":
        obj.last_reported = obj.last_updated = None
        expected = "report_missing"
    elif bad == "stale":
        obj.last_reported = obj.last_updated = datetime.fromtimestamp(wall[0] - 500, timezone.utc)
        expected = "report_stale"
    elif bad == "unavailable":
        obj.state = "unavailable"
    elif bad == "restored":
        obj.attributes["restored"] = True
    else:
        obj.attributes["temperature_unit"] = "°F"
    await elapsed_tick(runtime, wall, mono, 181)
    assert runtime.dhw.failed_command["code"] == expected
    assert runtime.dhw.failed_command["reported_target_c"] is None
    assert runtime.dhw.fault and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_service_exception_is_not_mislabelled_as_feedback_timeout(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    hass.services.on_call = lambda domain, _action, _data: setattr(hass.services, "fail", domain == "water_heater")
    await send(runtime, mono)
    row = runtime.dhw.failed_command
    assert row["code"] == "service_error"
    assert row["requested_target_c"] == 60 and row["waited_s"] == pytest.approx(0, abs=.05)
    assert "resultaat is onzeker" in row["reason"]
    assert runtime.dhw.pending is None and runtime.dhw.fault
    assert len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_fresh_later_matching_report_acks_without_creating_a_failure(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    wall[0] += 20
    mono[0] += 20
    report(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert runtime.dhw.pending is None and runtime.dhw.owned_target == 60
    assert runtime.dhw.last_success["confirmation"] == "delayed_ha_state"
    assert runtime.dhw.failed_command is None and not runtime.dhw.fault
    assert len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_audit_restores_only_same_target_binding_and_never_replays_a_write(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    await elapsed_tick(runtime, wall, mono, 181)
    saved = runtime.dhw.snapshot()
    restored = DHWManager(runtime)
    restored.restore(saved)
    assert restored.failed_command == runtime.dhw.failed_command
    assert restored.pending is None and restored.fault
    assert len(physical_calls(hass)) == 1
    saved["target_entity"] = "water_heater.other"
    different = DHWManager(runtime)
    different.restore(saved)
    assert different.failed_command is None


@pytest.mark.asyncio
async def test_old_journals_without_audit_keep_their_existing_review_semantics(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    await elapsed_tick(runtime, wall, mono, 181)
    saved = runtime.dhw.snapshot()
    saved.pop("failed_command")
    restored = DHWManager(runtime)
    restored.restore(saved)
    assert restored.failed_command is None and restored.fault and restored.automatic_recovery
    assert not restored.needs_review
    assert len(physical_calls(hass)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("damage", [
    {"schema": True}, {"code": []}, {"code": "arbitrary"},
    {"target_entity": "water_heater.other"}, {"issued_wall": float("nan")},
    {"issued_wall": True}, {"issued_wall": -1}, {"failed_wall": float("inf")},
    {"failed_wall": 0}, {"waited_s": -1}, {"waited_s": float("nan")},
    {"timeout_s": 1}, {"report_age_s": float("inf")}, {"requested_target_c": True},
    {"requested_target_c": 120}, {"reported_target_c": "invalid"}, {"release": "yes"},
])
async def test_damaged_audit_row_is_discarded_without_mutating_fault_authority(monkeypatch, damage):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    await elapsed_tick(runtime, wall, mono, 181)
    saved = runtime.dhw.snapshot()
    saved["failed_command"].update(damage)
    restored = DHWManager(runtime)
    restored.restore(saved)
    assert restored.failed_command is None and restored.fault
    assert restored.pending is None and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_audit_restore_sanitizes_text_and_unknown_fields(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    await elapsed_tick(runtime, wall, mono, 181)
    saved = runtime.dhw.snapshot()
    expected = runtime.dhw.failed_command["reason"]
    saved["failed_command"].update(reason="untrusted text", issued_at="bad", failed_at="bad", credentials="ignore")
    restored = DHWManager(runtime)
    restored.restore(saved)
    assert restored.failed_command["reason"] == expected
    assert "credentials" not in restored.failed_command
    assert restored.failed_command["issued_at"] != "bad"


@pytest.mark.asyncio
async def test_review_readiness_and_actual_review_share_pause_requirement_and_preserve_history(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    await elapsed_tick(runtime, wall, mono, 181)
    row = deepcopy(runtime.dhw.failed_command)
    overview = runtime.dhw.overview()
    assert not overview["review_required"] and overview["automatic_recovery_pending"]
    assert not overview["review_allowed"]
    with pytest.raises(HomeAssistantError, match="Pauze") as error:
        await runtime.dhw.review()
    assert str(error.value) == overview["review_block_reason"]
    assert runtime.dhw.failed_command == row

    runtime.mode = "paused"
    overview = runtime.dhw.overview()
    assert overview["review_allowed"] and not overview["review_block_reason"]
    await runtime.dhw.review()
    current = runtime.dhw.overview()
    assert not current["review_required"] and not current["failed_command_active"]
    assert not runtime.dhw.fault and runtime.dhw.owned_target is None
    assert current["failed_command"]["reviewed_wall"] == wall[0]
    assert current["failed_command"]["code"] == row["code"]
    assert len(physical_calls(hass)) == 1
    restored = DHWManager(runtime)
    restored.restore(runtime.dhw.snapshot())
    assert restored.failed_command == runtime.dhw.failed_command


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["pending", "target_missing", "temperature_missing", "hygiene", "powerful", "native_off"])
async def test_readiness_cannot_bypass_existing_review_guards(monkeypatch, guard):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    runtime.mode = "paused"
    runtime.dhw.fault = "Testfout"
    if guard == "pending":
        runtime.dhw.pending = {"target": 60}
    elif guard == "target_missing":
        hass.states.set("water_heater.boiler", "unavailable")
    elif guard == "temperature_missing":
        hass.states.set("sensor.water", "unavailable")
    elif guard == "hygiene":
        hass.states.set("binary_sensor.hygiene", "on")
    elif guard == "powerful":
        hass.states.set("switch.powerful", "on")
    else:
        hass.states.get("water_heater.boiler").state = "off"
    before = runtime.dhw.snapshot()
    overview = runtime.dhw.overview()
    assert overview["review_required"] and not overview["review_allowed"]
    with pytest.raises(HomeAssistantError) as error:
        await runtime.dhw.review()
    assert str(error.value) == overview["review_block_reason"]
    assert runtime.dhw.snapshot() == before and not physical_calls(hass)


@pytest.mark.asyncio
async def test_late_matching_report_retains_failure_history_without_replaying_command(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    await elapsed_tick(runtime, wall, mono, 181)
    row = deepcopy(runtime.dhw.failed_command)
    wall[0] += 1
    mono[0] += 1
    report(runtime, hass, wall, 60)
    await elapsed_tick(runtime, wall, mono, 0)
    assert not runtime.dhw.fault and runtime.dhw.failed_command["failed_at"] == row["failed_at"]
    assert runtime.dhw.failed_command["review_kind"] == "automatic_late_ack"
    assert runtime.dhw.last_success and len(physical_calls(hass)) == 1


@pytest.mark.asyncio
async def test_reviewed_failure_stays_historical_after_a_later_confirmed_command(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    await elapsed_tick(runtime, wall, mono, 181)
    runtime.mode = "paused"
    await runtime.dhw.review()
    row = deepcopy(runtime.dhw.failed_command)
    wall[0] += 301
    mono[0] += 301
    report(runtime, hass, wall, 60)
    water = hass.states.get("sensor.water")
    water.last_updated = water.last_reported = datetime.fromtimestamp(wall[0], timezone.utc)
    runtime.dhw.reading.actual_target_c = 60
    await runtime.dhw._send(mono[0], 50, True, "Test vrijgave")
    wall[0] += 20
    mono[0] += 20
    report(runtime, hass, wall, 50)
    await elapsed_tick(runtime, wall, mono, 0)
    assert runtime.dhw.last_success and not runtime.dhw.pending
    assert runtime.dhw.failed_command == row and not runtime.dhw.overview()["failed_command_active"]
    assert len(physical_calls(hass)) == 2


@pytest.mark.asyncio
async def test_new_failure_replaces_the_single_audit_row(monkeypatch):
    runtime, hass, wall, mono = failure_runtime(monkeypatch)
    await send(runtime, mono)
    await elapsed_tick(runtime, wall, mono, 181)
    first = deepcopy(runtime.dhw.failed_command)
    runtime.mode = "paused"
    await runtime.dhw.review()
    wall[0] += 301
    mono[0] += 301
    report(runtime, hass, wall, 60)
    water = hass.states.get("sensor.water")
    water.last_updated = water.last_reported = datetime.fromtimestamp(wall[0], timezone.utc)
    runtime.dhw.reading.actual_target_c = 60
    await runtime.dhw._send(mono[0], 50, True, "Test vrijgave")
    await elapsed_tick(runtime, wall, mono, 181)
    second = runtime.dhw.failed_command
    assert second["issued_wall"] > first["issued_wall"] and second["release"]
    assert "reviewed_at" not in second and runtime.dhw.overview()["failed_command_active"]
    assert isinstance(runtime.dhw.snapshot()["failed_command"], dict)


def test_unconfigured_overview_exposes_disabled_review_without_actuator_calls():
    from test_runtime import build
    runtime, hass = build()
    overview = runtime.dhw.overview()
    assert not overview["review_allowed"] and not overview["review_required"]
    assert overview["review_block_reason"] == "Boilerbediening niet gekoppeld"
    assert overview["failed_command"] is None and not hass.services.calls
