"""Recovery preserves current admission, protected one-shot commands and faults."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import time

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.device_retry import DeviceRetry, ambiguous_transport
from test_runtime import build
from test_dishwasher import setup as dishwasher_setup
from test_dishwasher_runtime import arm as arm_dishwasher


def physical(hass):
    return [call for call in hass.services.calls if call[0] != "persistent_notification"]


def due(runtime):
    runtime.device_retry.records["a"]["next_check_wall"] = time.time() - 1


def post_send(hass, entity, state, issued, attrs=None):
    hass.states.set(entity, state, attrs or {})
    obj = hass.states.get(entity)
    obj.last_reported = obj.last_updated = datetime.fromtimestamp(
        max(time.time(), issued + 0.001), timezone.utc)


@pytest.mark.parametrize("name", ["ServiceValidationError", "Unauthorized", "ConfigEntryAuthFailed"])
def test_explicit_actionable_ha_error_types_are_never_classified_as_transport(name):
    error_type = type(name, (HomeAssistantError,), {})
    assert not ambiguous_transport(error_type("actionable"))


@pytest.mark.parametrize("error", [HomeAssistantError("native service unavailable"), TimeoutError()])
def test_external_transport_failure_is_ambiguous_not_proof_of_off(error):
    assert ambiguous_transport(error)


@pytest.mark.asyncio
async def test_missing_native_service_is_known_unsent_and_retries_only_after_interval():
    runtime, hass = build()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    native = hass.services.has_service
    hass.services.has_service = lambda domain, action: False if domain == "switch" else native(domain, action)
    await runtime.tick()
    assert not physical(hass)
    assert not runtime.faults and runtime.device_retry.waiting("a")
    assert not runtime.states["a"].owned
    assert "a" not in runtime.store.data["leases"]
    view = runtime.overview()[0]["availability_retry"]
    assert view["active"] and view["state"] == "source_wait"
    assert 0 < view["remaining_s"] <= 300
    await runtime.tick()
    assert not physical(hass)
    hass.services.has_service = native
    await runtime.tick()
    assert not physical(hass)  # Native availability does not bypass backoff.
    due(runtime)
    await runtime.tick()
    assert [call[:2] for call in physical(hass)] == [("switch", "turn_on")]


@pytest.mark.asyncio
async def test_ack_timeout_waits_without_error_and_preserves_live_intent():
    runtime, hass = build()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.services.respond = False
    await runtime.tick()
    assert runtime.pending
    runtime.pending["issued"] -= 1000
    await runtime.tick()
    assert runtime.pending is None
    assert runtime.device_retry.waiting("a") and not runtime.faults
    assert runtime.states["a"].owned
    assert runtime.store.data["leases"]["a"]["watts"] > 0
    assert runtime.overview()[0]["availability_retry"]["state"] == "command_wait"
    assert not [call for call in hass.services.calls if call[0] == "persistent_notification"]


@pytest.mark.asyncio
async def test_partial_number_write_does_not_become_known_unsent_when_enable_service_disappears():
    runtime, hass = build(kind="number")
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.services.has_service = lambda domain, action: domain != "switch"
    await runtime.tick()
    assert [call[:2] for call in physical(hass)] == [("number", "set_value")]
    assert runtime.device_retry.command_waiting("a")
    assert runtime.store.data["leases"]["a"]["watts"] >= 1380
    assert not runtime.faults
    await runtime.tick()
    assert len(physical(hass)) == 1


@pytest.mark.asyncio
async def test_unavailable_meter_is_neutral_but_wrong_unit_remains_actionable():
    runtime, hass = build(power=True)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.overview()[0]["availability_retry"]["active"]
    assert runtime.states["a"].fault == ""
    assert not physical(hass)
    hass.states.set("sensor.load", 1, {"unit_of_measurement": "kWh"})
    await runtime.tick()
    assert not runtime.overview()[0]["availability_retry"]["active"]
    assert runtime.states["a"].fault
    assert not physical(hass)


@pytest.mark.asyncio
async def test_dishwasher_uncertain_start_is_checked_repeatedly_without_second_start():
    runtime, hass, cfg = dishwasher_setup()
    hass.services.fail = True
    await arm_dishwasher(runtime)
    hass.services.fail = False
    assert runtime.device_retry.command_waiting("a")
    assert runtime.dishwasher.tickets["a"]["attempted"]
    assert not runtime.faults
    issued = runtime.device_retry.records["a"]["issued_wall"]
    for _ in range(3):
        due(runtime)
        post_send(hass, "sensor.dw_phase", "Idle", issued)
        await runtime.tick()
        assert runtime.device_retry.command_waiting("a")
        assert runtime.dishwasher.tickets["a"]["attempted"]
        assert len(physical(hass)) == 1
    due(runtime)
    post_send(hass, "sensor.dw_phase", "Washing", issued)
    await runtime.tick()
    assert not runtime.device_retry.waiting("a")
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert len(physical(hass)) == 1
    assert not runtime.dishwasher.tickets["a"]["armed"]


@pytest.mark.asyncio
async def test_unknown_dishwasher_restart_does_not_block_selecting_global_automatic():
    runtime, hass, cfg = dishwasher_setup()
    await arm_dishwasher(runtime)
    saved = runtime._snapshot()
    saved["mode"] = "observe"
    saved["restart_requested_mode"] = None
    restarted, restored_hass, restored_cfg = dishwasher_setup()
    restored_hass.states.set("sensor.dw_connection", "Disconnected")
    restarted.store.data = saved
    await restarted.start()
    try:
        assert restarted.device_retry.command_waiting("a")
        assert not restarted.restart_blocking
        await restarted.set_mode("solar")
        assert restarted.mode == "solar"
        assert not physical(restored_hass)
        assert restarted.isolated_reserve_w == 0
        assert restarted.store.data["dishwasher"]["tickets"]["a"]["attempted"]
    finally:
        await restarted.close()


@pytest.mark.parametrize("payload", [None, [], {"schema": 2}, {"schema": 1, "records": []},
    {"schema": 1, "records": {"a": {"state": "command_wait", "issued_wall": float("nan")}}}])
def test_invalid_wait_journal_cannot_clear_or_replay_anything(payload):
    runtime, hass = build()
    runtime.faults["a"] = "Ongeldige configuratie"
    runtime.device_retry.restore(payload)
    assert not runtime.device_retry.waiting("a")
    assert runtime.faults["a"] == "Ongeldige configuratie"
    assert not physical(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("lease_w", [0, 1000])
@pytest.mark.parametrize("remembered_mode_key", [False, True])
async def test_legacy_failed_command_already_on_resumes_without_off_reset_or_duplicate_on(lease_w, remembered_mode_key):
    runtime, hass = build(device={"nominal_w": 1000, "min_on_s": 600})
    hass.states.set("switch.load", "on")
    runtime.store.data = {
        "mode": "observe", "device_modes": {"a": "auto"},
        "leases": {"a": {"watts": lease_w, "name": "Testtoestel"}},
        "faults": {"a": "Opdrachtfout: HomeAssistantError; controleer het toestel"},
    }
    if remembered_mode_key:
        runtime.store.data["restart_requested_mode"] = None
    await runtime.start()
    try:
        assert runtime.mode == "observe"
        assert runtime.device_retry.command_waiting("a")
        assert not runtime.faults
        await runtime.set_mode("solar")
        assert runtime.mode == "solar"
        assert not physical(hass)
        issued = runtime.device_retry.records["a"]["issued_wall"]
        post_send(hass, "switch.load", "on", issued)
        due(runtime)
        await runtime.tick()
        assert not runtime.device_retry.waiting("a")
        assert runtime.states["a"].owned and runtime.states["a"].on
        assert not physical(hass)  # No OFF prerequisite and no duplicate ON.
        hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
        await runtime.tick()
        assert not physical(hass)  # The fresh minimum run remains protected.
        runtime.states["a"].last_on -= 601
        await runtime.tick()
        assert [call[:2] for call in physical(hass)] == [("switch", "turn_off")]
    finally:
        await runtime.close()


def test_wrapped_explicit_authorization_error_remains_actionable():
    unauthorized = type("Unauthorized", (HomeAssistantError,), {})
    wrapped = HomeAssistantError("native integration wrapped its cause")
    wrapped.__cause__ = unauthorized("authorization failed")
    assert not ambiguous_transport(wrapped)


@pytest.mark.asyncio
async def test_explicit_manual_takeover_removes_retry_permission_and_never_readopts():
    runtime, hass = build()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.services.fail = True
    await runtime.tick()
    hass.services.fail = False
    assert runtime.device_retry.command_waiting("a")
    issued = runtime.device_retry.records["a"]["issued_wall"]
    runtime.mode = "paused"
    post_send(hass, "switch.load", "on", issued)
    await runtime.takeover("a")
    assert not runtime.device_retry.waiting("a")
    assert not runtime.states["a"].owned
    await runtime.set_mode("solar")
    assert not runtime.states["a"].owned
    assert runtime.device_modes["a"] == "disabled"
    assert len(physical(hass)) == 1


@pytest.mark.asyncio
async def test_explicit_verified_off_reset_removes_retry_record():
    runtime, hass = build()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.services.fail = True
    await runtime.tick()
    hass.services.fail = False
    runtime.mode = "paused"
    hass.states.set("switch.load", "off")
    await runtime.reset()
    assert not runtime.device_retry.waiting("a")
    assert not runtime.states["a"].owned
    assert len(physical(hass)) == 1


@pytest.mark.asyncio
async def test_removed_device_retry_record_is_pruned_without_global_internal_fault():
    runtime, hass = build()
    runtime.device_retry.begin("a", 1000, time.time())
    runtime.configs.pop("a")
    runtime.states.pop("a")
    await runtime.device_retry.tick(time.monotonic())
    assert not runtime.device_retry.waiting("a")
    assert not runtime.faults


@pytest.mark.asyncio
async def test_dishwasher_missing_start_service_restores_unconsumed_ticket():
    runtime, hass, cfg = dishwasher_setup()
    native = hass.services.has_service
    hass.services.has_service = lambda domain, action: False if (domain, action) == ("button", "press") else native(domain, action)
    await arm_dishwasher(runtime)
    assert not physical(hass)
    assert not runtime.faults
    assert runtime.device_retry.waiting("a")
    ticket = runtime.dishwasher.tickets["a"]
    assert isinstance(ticket, dict)
    assert ticket["armed"] and not ticket.get("attempted")
    assert not runtime.states["a"].owned
    await runtime.tick()
    assert not physical(hass)
    hass.services.has_service = native
    due(runtime)
    await runtime.tick()
    assert [call[:2] for call in physical(hass)] == [("button", "press")]
    assert runtime.dishwasher.tickets["a"]["attempted"]


@pytest.mark.asyncio
async def test_old_transport_message_without_lease_never_takes_over_external_on():
    runtime, hass = build()
    hass.states.set("switch.load", "on")
    runtime.store.data = {
        "mode": "observe", "device_modes": {"a": "auto"}, "leases": {},
        "faults": {"a": "Opdrachtfout: HomeAssistantError; controleer het toestel"},
    }
    await runtime.start()
    try:
        await runtime.set_mode("solar")
        assert not runtime.states["a"].owned
        assert runtime.states["a"].on
        assert not physical(hass)
        assert not runtime.faults
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_external_dishwasher_losing_connection_does_not_keep_a_cached_peak():
    from test_cycle_reserve_audit89 import runtime_with_running_cycle

    runtime, hass = runtime_with_running_cycle()
    runtime.mode = "observe"
    await runtime.tick()
    assert runtime._dishwasher_unmetered_reserve == 2000
    assert runtime.states["fictional_cycle"].on
    assert not runtime.states["fictional_cycle"].owned
    hass.states.set("sensor.dw_connection", "Disconnected")
    await runtime.tick()
    assert not runtime.states["fictional_cycle"].available
    assert runtime.states["fictional_cycle"].on  # Unknown does not mean OFF.
    assert runtime._dishwasher_unmetered_reserve == 0
    assert not physical(hass)


@pytest.mark.asyncio
async def test_dispatch_uses_actual_surplus_when_external_cycle_goes_offline_during_journal(monkeypatch):
    from test_cycle_reserve_audit89 import runtime_with_running_cycle

    runtime, hass = runtime_with_running_cycle()
    runtime.settings["max_import_w"] = 0
    hass.states.set("sensor.grid", -4000, {"unit_of_measurement": "W"})
    saved = runtime.store.async_save
    changed = False

    async def become_unavailable(data):
        nonlocal changed
        await saved(data)
        if changed or "a" not in data.get("leases", {}):
            return
        changed = True
        hass.states.set("sensor.dw_connection", "Disconnected")
        hass.states.set("sensor.grid", -900, {"unit_of_measurement": "W"})

    monkeypatch.setattr(runtime.store, "async_save", become_unavailable)
    await runtime.tick()
    assert changed
    assert [call[:2] for call in physical(hass)] == [("switch", "turn_on")]
    assert runtime.pending and runtime.states["a"].owned
