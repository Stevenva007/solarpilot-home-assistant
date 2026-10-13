"""Diagnostic transport stages cannot alter SG operations or permit retries."""
import asyncio
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_transport import ShellyLeaseError
from test_sg_controller62 import boosted, fixture, tick


@pytest.mark.asyncio
@pytest.mark.parametrize("error,phase,category,attempted,applied", [
    (TimeoutError(), "failed", "timeout", None, None),
    (ShellyLeaseError("write_uncertain", "fixture transport", command_attempted=True),
        "send_uncertain", "write_uncertain", True, None),
    (ShellyLeaseError("invalid_response", "fixture reply", command_attempted=True, command_applied=True),
        "accepted_readback_unconfirmed", "invalid_response", True, True),
    (ShellyLeaseError("unavailable", "fixture preflight"), "not_sent", "unavailable", False, None),
    (ValueError("off_not_confirmed"), "failed", "contact_unconfirmed", None, None),
])
async def test_off_controller_closure_transport_failure_and_later_contact_confirmation_are_separate(
        error, phase, category, attempted, applied):
    manager, adapter, clock, runtime = await boosted()
    assert manager.overview()["transport_evidence"]["operation"] == "on"
    before_options = deepcopy(runtime.entry.options)
    clock.advance(20)
    attempted_calls = []
    async def fail_off():
        attempted_calls.append("off")
        raise error
    adapter.set_off = fail_off
    await manager._release("SG-voorwaarden gewijzigd; eigen aanvraag vrijgegeven")
    assert manager._last_session["ended_at"] == clock()
    assert manager.relay_on is None and not manager.relay_confirmed
    evidence = manager._last_session["transport"]
    assert evidence == {"operation": "off", "phase": phase, "category": category,
                        "observed_at": clock(), "command_attempted": attempted, "command_applied": applied}
    assert runtime.entry.options == before_options
    # A genuinely new OFF readback is new evidence, without a replayed OFF.
    adapter.on = False
    clock.advance(5)
    raw = await manager._read(force=True)
    manager._observe_contact(raw)
    assert manager.relay_on is False and manager.relay_confirmed
    assert manager.overview()["transport_evidence"]["operation"] == "read"
    assert manager.overview()["transport_evidence"]["phase"] == "confirmed"
    assert manager._last_session["transport"] == evidence
    assert attempted_calls == ["off"]
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_cancelled_off_is_recorded_then_original_cancellation_is_preserved():
    manager, adapter, clock, runtime = await boosted()
    async def cancel_off():
        raise asyncio.CancelledError()
    adapter.set_off = cancel_off
    with pytest.raises(asyncio.CancelledError):
        await manager._release("Eigen SG-aanvraag vrijgegeven voor afsluiten")
    assert manager._last_session["transport"]["category"] == "cancelled"
    assert manager._last_session["transport"]["command_attempted"] is None
    assert manager.relay_on is None


@pytest.mark.asyncio
async def test_diagnostic_failure_does_not_change_native_start_or_off(monkeypatch):
    manager, adapter, clock, runtime = fixture()
    def broken(*args, **kwargs):
        raise ValueError("fixture diagnostic failure")
    monkeypatch.setattr(manager, "_capture_transport_evidence", broken)
    await tick(manager)
    clock.advance(manager.settings["start_delay_s"])
    await tick(manager)
    assert manager.owned and manager.desired_on and adapter.calls == [("on", 300)]
    await manager._release("Eigen SG-aanvraag vrijgegeven voor afsluiten")
    assert not manager.owned and manager.relay_on is False
    assert adapter.calls == [("on", 300), ("off", None)]
    assert manager._last_session["transport"] is None


def test_malformed_errors_and_failing_telemetry_clock_do_not_escape_or_leak(monkeypatch):
    manager, _, _, _ = fixture()
    manager._record_transport("off", error=ValueError({"private_fixture_payload": "secret"}))
    assert manager.overview()["transport_evidence"]["category"] == "unknown"
    assert "private_fixture_payload" not in str(manager.overview()["transport_evidence"])
    monkeypatch.setattr(manager, "_wall_clock", lambda: (_ for _ in ()).throw(ValueError("fixture clock")))
    manager._record_transport("read")
    manager._transport_confirmed("read")
    assert manager._transport_evidence is None


@pytest.mark.asyncio
async def test_known_off_without_off_transport_does_not_borrow_prior_on_evidence():
    manager, adapter, clock, _ = await boosted()
    # Existing ownership logic has already seen OFF. A controller closure may
    # record its reason, but no OFF operation was actually witnessed here.
    manager.owned = manager._possibly_owned = False
    await manager._release("SG-voorwaarden gewijzigd; eigen aanvraag vrijgegeven")
    assert manager._last_session["transport"] is None
    assert adapter.calls == [("on", 300)]
