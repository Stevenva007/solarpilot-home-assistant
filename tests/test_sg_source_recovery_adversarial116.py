"""Independent boundary probes: source recovery cannot replay timed requests.

Only the SG relay request is modelled; no compressor operation is inferred.
"""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_sg_controller62 import fixture
from test_sg_source_recovery116 import observation, step, stopped
from test_sg_transport62 import native, writes  # noqa: F401 - native RPC fixture


async def native_stopped(native):
    _unused, _adapter, clock, runtime = fixture(entity_id="switch.public_sg",
        start_delay_s=120, rest_s=900)
    runtime.hass = native.hass
    manager = SGBoostManager(runtime, adapter=native.adapter, clock=clock)
    runtime.sg_boost = manager
    runtime._snapshot = lambda: {"sg_boost": manager.snapshot()}
    await manager.start()
    await manager.set_manual_control("on", 3600)
    await step(manager)
    assert manager.owned and native.device.output
    await step(manager, fresh=False, advance=5)
    assert not manager.owned and not native.device.output
    await step(manager, advance=900)
    await step(manager, advance=60)
    return manager, clock, runtime


@pytest.mark.asyncio
async def test_external_on_during_native_preflight_cannot_borrow_recovery_off_proof(native):
    manager, clock, runtime = await native_stopped(native)
    original = native.device.call_rpc
    intervened = False

    async def external_change(method, params=None, timeout=None):
        nonlocal intervened
        if method == "Switch.GetStatus" and native.adapter.before_on_status is not None:
            intervened = True
            native.device.output = True
        return await original(method, params=params, timeout=timeout)

    native.device.call_rpc = external_change
    await step(manager, advance=60)
    assert intervened and native.device.output  # The external contact is untouched.
    assert not manager.owned and not manager.desired_on
    assert manager._source_recovery is not None
    assert [params["on"] for _, params in writes(native)] == [True, False]
    assert native.adapter.before_on is None and native.adapter.before_on_status is None
    assert not native.hass.services.calls
    # Seeing an external ON also invalidates the completed OFF/source window.
    # A subsequent external OFF cannot let the next tick reuse that old proof.
    native.device.call_rpc = original
    native.device.output = False
    await step(manager, advance=1)
    assert not native.device.output
    await step(manager, advance=60)
    assert not native.device.output
    await step(manager, advance=60)
    assert native.device.output and manager.owned


@pytest.mark.asyncio
async def test_expiry_while_recovery_intent_is_saved_never_gets_a_new_lease():
    manager, adapter, clock, runtime, expiry = await stopped(duration=1800)
    await step(manager, advance=900)
    await step(manager, advance=60)
    original = runtime.store.async_save

    async def delayed_save(data):
        await original(data)
        clock.advance(max(0, expiry-clock())+1)

    runtime.store.async_save = delayed_save
    await step(manager, advance=60)
    assert not adapter.on and not manager.owned
    assert [name for name, _ in adapter.calls] == ["on", "off"]
    assert manager._source_recovery is not None
    # Cleanup may choose auto; any surviving stored choice keeps its old end.
    assert manager._manual_control is None or manager._manual_control["expires_at"] == expiry


@pytest.mark.asyncio
@pytest.mark.parametrize("corrupt", [
    {"schema": 1, "stopped_at": 1_900_000_000, "control_identity": "wrong"},
    {"schema": 1, "stopped_at": -1},
    {"schema": True, "stopped_at": 1_800_000_005},
    ["source-stop"], "source-stop", 1,
])
async def test_recognizable_damaged_recovery_needs_new_live_source_proof(corrupt):
    manager, adapter, clock, runtime, expiry = await stopped()
    snapshot = manager.snapshot()
    snapshot["source_recovery"] = deepcopy(corrupt)
    replacement = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = replacement
    runtime._snapshot = lambda: {"sg_boost": replacement.snapshot()}
    replacement.restore(snapshot)
    assert replacement._source_recovery is not None
    assert replacement._source_recovery_candidate is None
    await step(replacement)
    assert not adapter.on
    assert replacement._manual_control["expires_at"] == expiry


@pytest.mark.asyncio
@pytest.mark.parametrize("evidence", [None, {
    "schema": 1, "code": "site_source", "evaluated_at": 1_800_000_005,
    "renewal": True,
}])
async def test_beta115_upgrade_cannot_replay_a_stopped_manual_choice(evidence):
    manager, adapter, clock, runtime, expiry = await stopped()
    snapshot = manager.snapshot()
    snapshot.pop("source_recovery")
    snapshot["last_session"]["stop_evidence"] = evidence
    clock.advance(901)  # The durable protected rest has already expired.
    replacement = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = replacement
    runtime._snapshot = lambda: {"sg_boost": replacement.snapshot()}
    replacement.restore(snapshot)
    assert replacement._source_recovery is not None
    assert replacement._restart_resume is None
    await step(replacement)
    assert not adapter.on
    await step(replacement, advance=60)
    assert not adapter.on
    await step(replacement, advance=60)
    assert adapter.on
    assert replacement._manual_control["expires_at"] == expiry


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [None, {}, {"p1": True, "site": 1_800_000_000, "pv": 1_800_000_000}])
async def test_missing_or_malformed_original_source_clocks_never_complete_recovery(invalid):
    manager, adapter, clock, runtime, _ = await stopped()
    await step(manager, advance=900)
    await step(manager, advance=60)
    clock.advance(60)
    current = observation(clock)
    current["source_reports"] = invalid
    runtime.sg_usable_solar_observation = lambda: deepcopy(current)
    await manager.tick(surplus_w=0, real_surplus_w=0, data_fresh=True,
        phase_allowed=True, grid_import_w=0, solar_stamp=clock(),
        grid_import_stamp=clock(), grid_import_source="fictional-grid",
        start_source_identity="fictional-inputs", usable_solar_observation=current)
    assert not adapter.on and manager._source_recovery is not None
    assert [name for name, _ in adapter.calls] == ["on", "off"]
