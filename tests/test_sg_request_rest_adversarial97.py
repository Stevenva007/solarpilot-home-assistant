"""Independent request-rest probes; fictional relay and original source reports."""
from copy import copy, deepcopy
from types import MethodType, SimpleNamespace

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_general_sg_policy64 import general_fixture, observe
from test_sg_controller62 import Store, tick


def _dispatch(self, **_kwargs):
    self._sg_dispatch_rejection = {"fictional": "current gate was evaluated"}
    if self.current_dispatch == "error":
        raise RuntimeError("fictional gate unavailable")
    return self.current_dispatch


async def _ended_automatic():
    manager, adapter, clock, runtime, row = general_fixture(cooling_protection_confirmed=True)
    original_status = adapter.status
    adapter.status = lambda: {**original_status(), "binding_identity": "a" * 64}
    runtime.current_dispatch = True
    runtime.sg_dispatch_allowed = MethodType(_dispatch, runtime)
    runtime.entry.runtime_data = runtime
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert manager.owned
    await manager._release("Fictional interrupted automatic request")
    assert manager.completion_hold and manager._hold_reason == "response_unknown"
    row.update(context="heatpump_unknown", context_reliable=False, context_stamp=None,
               context_signature=None, cooling_possible=True, power_w=None,
               power_kind="unknown", power_stamp=None)
    return manager, adapter, clock, runtime, row


async def _residual(manager, clock, row):
    return await tick(manager, surplus=4000, real_surplus_w=4000, solar_stamp=clock(),
                      native_observation=deepcopy(row),
                      start_source_identity=("fictional-P1", "fictional-PV"))


async def _almost_confirmed(manager, clock, row):
    clock.advance(1)
    await _residual(manager, clock, row)
    for _ in range(4):
        clock.advance(60)
        await _residual(manager, clock, row)
    assert manager.completion_hold and manager._general_candidate is not None


async def _new_window(manager, clock, row):
    clock.advance(1)
    await _residual(manager, clock, row)
    for _ in range(5):
        clock.advance(60)
        await _residual(manager, clock, row)


def _restored(manager, adapter, clock, runtime, saved):
    other = copy(runtime)
    other.entry = SimpleNamespace(options=deepcopy(runtime.entry.options))
    other.entry.runtime_data = other
    other.store = Store()
    other.sg_dispatch_allowed = MethodType(_dispatch, other)
    restored = SGBoostManager(other, adapter=adapter, clock=clock)
    other.sg_boost = restored
    other._snapshot = lambda: {"sg_boost": restored.snapshot()}
    restored.restore(saved)
    return restored


@pytest.mark.asyncio
@pytest.mark.parametrize("decision", [False, "error"])
async def test_final_live_gate_changed_during_read_cannot_consume_rest_or_reuse_old_window(decision):
    manager, adapter, clock, runtime, row = await _ended_automatic()
    await _almost_confirmed(manager, clock, row)
    deadline, wall_deadline = manager._rest_until, manager._rest_until_wall
    original_read = adapter.get_status
    diagnostic = {"fictional": "original diagnostic"}
    runtime._sg_dispatch_rejection = diagnostic

    async def changed_during_read():
        raw = await original_read()
        runtime.current_dispatch = decision
        return raw

    adapter.get_status = changed_during_read
    clock.advance(60)
    await _residual(manager, clock, row)
    assert manager.completion_hold and manager._general_candidate is None
    assert (manager._rest_until, manager._rest_until_wall) == (deadline, wall_deadline)
    assert not manager.owned and adapter.calls == [("on", 300), ("off", None)]
    assert runtime._sg_dispatch_rejection is diagnostic

    adapter.get_status = original_read
    runtime.current_dispatch = True
    clock.advance(1)
    await _residual(manager, clock, row)
    for _ in range(4):
        clock.advance(60)
        await _residual(manager, clock, row)
    assert manager.completion_hold and manager._rest_until == deadline
    clock.advance(60)
    await _residual(manager, clock, row)
    assert not manager.completion_hold and not manager.owned
    assert manager.overview()["start_remaining_s"] == manager.settings["start_delay_s"]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["closed", "detached"])
async def test_runtime_authority_lost_during_contact_read_keeps_original_rest(change):
    manager, adapter, clock, runtime, row = await _ended_automatic()
    await _almost_confirmed(manager, clock, row)
    deadline, wall_deadline = manager._rest_until, manager._rest_until_wall
    original_read = adapter.get_status

    async def revoked_during_read():
        raw = await original_read()
        if change == "closed":
            runtime._closed = True
        else:
            runtime.entry.runtime_data = object()
        return raw

    adapter.get_status = revoked_during_read
    clock.advance(60)
    await _residual(manager, clock, row)
    assert manager.completion_hold and manager._general_candidate is None
    assert (manager._rest_until, manager._rest_until_wall) == (deadline, wall_deadline)
    assert not manager.owned and adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_native_source_change_with_identical_numeric_policy_cannot_replace_rest():
    manager, adapter, clock, runtime, row = await _ended_automatic()
    original_policy = deepcopy(manager._last_session["session_provenance"]["policy"])
    original_control = manager._last_session["session_provenance"]["control_identity"]
    deadline, wall_deadline = manager._rest_until, manager._rest_until_wall
    manager.update_config({**manager.settings, "activity_entity": "sensor.fictional_other_activity"})
    assert original_policy["profile"] == manager.settings["profile"]
    assert all(manager.settings[key] == value for key, value in original_policy.items()
               if key in manager.settings)
    assert manager._control_identity() != original_control
    await _new_window(manager, clock, row)
    assert manager.completion_hold and manager._general_candidate is None
    assert (manager._rest_until, manager._rest_until_wall) == (deadline, wall_deadline)
    assert not manager.owned and adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("identity", ["missing", None, True, "b" * 63, "z" * 64, "b" * 65])
async def test_legacy_or_invalid_original_control_identity_is_not_reconstructed_on_restart(identity):
    manager, adapter, clock, runtime, row = await _ended_automatic()
    saved = manager.snapshot()
    for provenance in (saved["hold_origin"]["session_provenance"],
                       saved["last_session"]["session_provenance"]):
        if identity == "missing":
            provenance.pop("control_identity")
        else:
            provenance["control_identity"] = identity
    original = deepcopy(saved)
    restored = _restored(manager, adapter, clock, runtime, saved)
    await _new_window(restored, clock, row)
    assert saved == original
    assert restored.completion_hold and restored._general_candidate is None
    assert restored._last_session == original["last_session"]
    assert restored._rest_until_wall == original["rest_until_wall"]
    assert restored._rest_until > clock() and not restored.owned
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("marker", ["missing", None, True, "unknown", {}, "protected"])
async def test_absent_invalid_or_protected_rest_origin_cannot_borrow_known_session_provenance(marker):
    manager, adapter, clock, runtime, row = await _ended_automatic()
    saved = manager.snapshot()
    if marker == "missing":
        saved.pop("request_rest_policy")
    else:
        saved["request_rest_policy"] = marker
    restored = _restored(manager, adapter, clock, runtime, saved)
    await _new_window(restored, clock, row)
    assert restored.completion_hold and restored._general_candidate is None
    assert restored._rest_until_wall == saved["rest_until_wall"]
    assert restored._rest_until > clock() and not restored.owned
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("binding", ["a" * 65, "z" * 64, True, {}])
async def test_malformed_original_binding_is_never_trimmed_into_current_contact_proof(binding):
    manager, adapter, clock, runtime, row = await _ended_automatic()
    saved = manager.snapshot()
    for provenance in (saved["hold_origin"]["session_provenance"],
                       saved["last_session"]["session_provenance"]):
        provenance["binding_identity"] = binding
    restored = _restored(manager, adapter, clock, runtime, saved)
    await _new_window(restored, clock, row)
    assert restored.completion_hold and restored._general_candidate is None
    assert restored._rest_until_wall == saved["rest_until_wall"]
    assert restored._rest_until > clock() and not restored.owned
    assert adapter.calls == [("on", 300), ("off", None)]
