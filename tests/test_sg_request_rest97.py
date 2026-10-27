"""Request-only rest replacement; fictional relay and independent source clocks."""
from copy import copy, deepcopy

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_general_sg_policy64 import general_fixture, observe
from test_sg_controller62 import Store


BINDING = "a" * 64
SOURCE = (("fictional-grid", "import-positive", "fictional-pv"), ("a", "b", "c"))


async def ended_request(*, expiry=False):
    manager, adapter, clock, runtime, row = general_fixture(
        expected_power_w=3200, threshold_w=3000, cooling_protection_confirmed=True)
    status = adapter.status
    adapter.binding = BINDING
    adapter.status = lambda: {**status(), "binding_identity": adapter.binding}
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert manager.owned and manager._session_provenance["control_identity"] == manager._control_identity()
    row.update(context="heatpump_unknown", context_reliable=False, context_stamp=None,
        context_signature=None, cooling_possible=True, power_w=None, power_kind="unknown",
        power_stamp=None, compressor_running=None, compressor_frequency_hz=None)
    if expiry:
        clock.advance(adapter.expiry-clock())
        await residual(manager, clock, row)
    else:
        await manager._release("Aanhoudende netafname; extra SG-aanvraag vrijgegeven")
    assert manager.completion_hold and manager._hold_reason == "response_unknown"
    assert manager._request_rest_policy == "request" and not manager.owned
    return manager, adapter, clock, runtime, row


async def residual(manager, clock, row, *, watts=4000, stamp=None, identity=SOURCE, **changes):
    arguments = dict(surplus_w=watts, real_surplus_w=watts, grid_import_w=0,
        grid_import_stamp=clock(), data_fresh=True, phase_allowed=True,
        solar_stamp=clock() if stamp is None else stamp, native_observation=deepcopy(row),
        start_source_identity=identity)
    arguments.update(changes)
    return await manager.tick(**arguments)


async def collect(manager, clock, row, seconds=300, **kwargs):
    for _ in range(seconds // 60):
        clock.advance(60)
        await residual(manager, clock, row, **kwargs)


async def partial(manager, clock, row):
    clock.advance(1)
    await residual(manager, clock, row)
    await collect(manager, clock, row, 240)
    assert manager.completion_hold and manager._general_candidate is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("expiry", [False, True])
async def test_known_ended_request_collects_during_rest_then_requires_full_ordinary_start(expiry):
    manager, adapter, clock, _runtime, row = await ended_request(expiry=expiry)
    old_end = deepcopy(manager._last_session)
    old_origin = deepcopy(manager._hold_origin)
    calls = list(adapter.calls)
    await partial(manager, clock, row)
    wait = manager.overview()["rearm_wait"]
    assert wait["request_rest_replaceable"] and wait["request_rest_remaining_s"] > 600
    assert "Na rust" not in wait["current_condition"]
    await collect(manager, clock, row, 60)
    assert not manager.completion_hold and not manager.owned
    assert manager._rest_until == clock() and manager._rest_until_wall == clock()
    assert 590 < manager._last_rearm["request_rest_replaced_s"] < 610
    assert manager.overview()["start_remaining_s"] == 120
    assert manager._last_session == old_end and old_origin["ended_at"] == old_end["ended_at"]
    assert adapter.calls == calls
    await collect(manager, clock, row, 60)
    assert adapter.calls == calls
    await collect(manager, clock, row, 60)
    assert manager.owned and adapter.calls == calls + [("on", 300)]
    assert row["power_w"] is None and row["context_reliable"] is False


@pytest.mark.asyncio
async def test_changed_native_context_cannot_switch_the_early_residual_proof_lane():
    manager, adapter, clock, _runtime, row = await ended_request()
    clock.advance(1)
    await residual(manager, clock, row)
    row.update(context="space_heating", context_reliable=True, context_signature="changed:heat")
    for _ in range(5):
        clock.advance(60)
        row["context_stamp"] = clock()
        await residual(manager, clock, row)
    assert not manager.completion_hold and not manager.owned
    assert manager._last_rearm["kind"] == "fresh_residual_surplus"
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("block", ["read", "backoff", "external_on", "binding", "setup"])
async def test_final_contact_must_be_live_unchanged_confirmed_off(block):
    manager, adapter, clock, _runtime, row = await ended_request()
    await partial(manager, clock, row)
    deadline = manager._rest_until
    calls = list(adapter.calls)
    if block == "read":
        adapter.online = False
    elif block == "backoff":
        manager._next_read = clock()+100
    elif block == "external_on":
        adapter.on = True
        adapter.start, adapter.duration, adapter.expiry = clock(), 300, clock()+300
    elif block == "binding":
        adapter.binding = "b"*64
    elif block == "setup":
        adapter.configured = False
    await collect(manager, clock, row, 60)
    if block == "external_on":
        assert manager.external_control_overview()["active"]
    else:
        assert manager.completion_hold
    assert manager._general_candidate is None
    assert manager._rest_until == deadline and adapter.calls == calls
    assert not manager.owned


@pytest.mark.asyncio
async def test_read_failure_resets_proof_and_recovery_requires_a_new_complete_window():
    manager, adapter, clock, _runtime, row = await ended_request()
    await partial(manager, clock, row)
    adapter.online = False
    await collect(manager, clock, row, 60)
    adapter.online = True
    clock.advance(60)
    await residual(manager, clock, row)
    assert manager._general_candidate["first_seen"] == clock()
    await collect(manager, clock, row, 240)
    assert manager.completion_hold
    await collect(manager, clock, row, 60)
    assert not manager.completion_hold and not manager.owned


@pytest.mark.asyncio
async def test_solar_report_that_expires_during_contact_read_cannot_finish_proof():
    manager, adapter, clock, _runtime, row = await ended_request()
    await partial(manager, clock, row)
    get_status = adapter.get_status

    async def delayed():
        clock.advance(2)
        return await get_status()

    adapter.get_status = delayed
    clock.advance(60)
    await residual(manager, clock, row, stamp=clock()-119)
    assert manager.completion_hold and manager._general_candidate is None
    assert manager._rest_until > clock()


@pytest.mark.asyncio
@pytest.mark.parametrize("break_kind", ["phase", "priority", "limit", "source", "gap", "credit"])
async def test_interrupted_or_replaced_original_residual_evidence_restarts_the_window(break_kind):
    manager, adapter, clock, _runtime, row = await ended_request()
    await partial(manager, clock, row)
    changes = {"phase": {"phase_allowed": False}, "priority": {"priority_allowed": False},
        "limit": {"hard_limit": True}, "source": {"identity": ("other",)},
        "gap": {"data_fresh": False}, "credit": {"watts": 0, "surplus_w": 8000}}[break_kind]
    await collect(manager, clock, row, 60, **changes)
    assert manager.completion_hold and not manager.owned
    clock.advance(1)
    await residual(manager, clock, row)
    await collect(manager, clock, row, 240)
    assert manager.completion_hold
    await collect(manager, clock, row, 60)
    assert not manager.completion_hold and adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_repeated_original_report_cannot_finish_early_confirmation():
    manager, adapter, clock, _runtime, row = await ended_request()
    await partial(manager, clock, row)
    prior_report = clock()
    await collect(manager, clock, row, 60, stamp=prior_report)
    assert manager.completion_hold and not manager.owned
    clock.advance(1)
    await residual(manager, clock, row)
    assert not manager.completion_hold and len(adapter.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["native_completed", "no_uptake", "session_limit", "profile_changed"])
async def test_other_completion_holds_keep_their_original_rest(reason):
    manager, adapter, clock, _runtime, row = await ended_request()
    manager._hold_reason = reason
    clock.advance(1)
    await residual(manager, clock, row)
    await collect(manager, clock, row)
    assert manager.completion_hold and manager._rest_until > clock()
    assert manager._general_candidate is None and len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_deliberate_later_rest_cannot_borrow_an_earlier_automatic_end():
    manager, adapter, clock, _runtime, row = await ended_request()
    await partial(manager, clock, row)
    manager._begin_rest()
    assert manager._request_rest_policy == "protected"
    await collect(manager, clock, row, 60)
    assert manager.completion_hold and manager._general_candidate is None and len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_lost_off_ack_and_later_confirmed_off_keep_uncertain_request_rest_protected():
    manager, adapter, clock, _runtime, row = await ended_request()
    # Start another real bounded request first, then lose its OFF ACK after the
    # fictional relay physically applied OFF. Later recovery grants no shortcut.
    clock.advance(manager.settings["rest_s"])
    await residual(manager, clock, row)
    await collect(manager, clock, row, 300)
    await collect(manager, clock, row, 120)
    assert manager.owned
    original_off = adapter.set_off

    async def applied_without_ack():
        await original_off()
        raise RuntimeError("fictional acknowledgement missing")

    adapter.set_off = applied_without_ack
    await manager._release("Aanhoudende netafname; extra SG-aanvraag vrijgegeven")
    assert manager._request_rest_policy == "protected" and manager.fault_code == "off_failed"
    clock.advance(1)
    await residual(manager, clock, row)
    assert not manager.fault and manager._request_rest_policy == "protected"
    await collect(manager, clock, row)
    assert manager.completion_hold and manager._general_candidate is None
    assert manager._rest_until > clock() and not manager.owned


@pytest.mark.asyncio
async def test_reload_preserves_original_identity_but_discards_partial_proof_and_keeps_new_start_delay():
    manager, adapter, clock, runtime, row = await ended_request()
    clock.advance(1)
    await residual(manager, clock, row)
    await collect(manager, clock, row, 120)
    stored = deepcopy(manager.snapshot())
    other = copy(runtime)
    other.store = Store()
    restored = SGBoostManager(other, adapter=adapter, clock=clock)
    other.sg_boost = restored
    other._snapshot = lambda: {"sg_boost": restored.snapshot()}
    restored.restore(stored)
    assert restored._general_candidate is None
    assert restored._hold_origin == manager._hold_origin
    clock.advance(1)
    await residual(restored, clock, row)
    await collect(restored, clock, row, 240)
    assert restored.completion_hold
    await collect(restored, clock, row, 60)
    assert not restored.completion_hold and restored.overview()["start_remaining_s"] == 120
    # A second reload cannot recover the just-collected ordinary start delay.
    saved = deepcopy(restored.snapshot())
    again = SGBoostManager(other, adapter=adapter, clock=clock)
    other.sg_boost = again
    other._snapshot = lambda: {"sg_boost": again.snapshot()}
    again.restore(saved)
    await residual(again, clock, row)
    assert again.overview()["start_remaining_s"] == 120
    assert again._rest_until <= clock() and again._rest_until_wall == saved["rest_until_wall"]
    await collect(again, clock, row, 120)
    assert again.owned and adapter.calls == [("on", 300), ("off", None), ("on", 300)]


@pytest.mark.asyncio
async def test_command_control_identity_comes_from_frozen_pre_ack_settings():
    manager, adapter, clock, _runtime, row = general_fixture()
    original_identity = manager._control_identity()
    original_on = adapter.set_on

    async def changed_during_ack(lease_s=300):
        result = await original_on(lease_s)
        manager.settings["activity_entity"] = "sensor.fictional_changed_during_ack"
        return result

    adapter.set_on = changed_during_ack
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    evidence = manager._session_provenance or manager._last_session["session_provenance"]
    assert evidence["control_identity"] == original_identity
    assert evidence["control_identity"] != manager._control_identity()
