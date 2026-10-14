"""Independent native-adapter callback lifecycle probes with fictional RPC."""
import asyncio

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_sg_controller62 import fixture
from test_sg_transport62 import native, writes


def native_manager(native):
    _unused, _adapter, clock, runtime = fixture(entity_id="switch.public_sg", min_session_s=0)
    runtime.hass = native.hass
    manager = SGBoostManager(runtime, adapter=native.adapter, clock=clock)
    runtime.sg_boost = manager
    runtime._snapshot = lambda: {"sg_boost": manager.snapshot()}
    return manager, clock, runtime


async def narrow_after_save(manager, clock, runtime):
    await manager.set_manual_control("on", 1800)
    clock.advance(1700)
    original = runtime.store.async_save
    first = True

    async def slow_intent_save(data):
        nonlocal first
        await original(data)
        if first:
            first = False
            clock.advance(30)

    runtime.store.async_save = slow_intent_save
    try:
        assert await manager._issue_on() is False
    finally:
        runtime.store.async_save = original


@pytest.mark.asyncio
async def test_native_empty_callback_attributes_survive_two_preflight_early_returns(native):
    manager, clock, runtime = native_manager(native)
    await manager.start()
    for _ in range(2):
        await narrow_after_save(manager, clock, runtime)
        assert hasattr(native.adapter, "before_on")
        assert native.adapter.before_on is None
        assert native.adapter.before_on_status is None
        assert native.adapter.before_off_status is None
        assert not manager._in_flight and not manager.desired_on
    assert writes(native) == []


@pytest.mark.asyncio
async def test_uninstalled_existing_callback_is_not_cleared_by_early_return(native):
    manager, clock, runtime = native_manager(native)
    await manager.start()
    original_on = lambda: False
    original_status = lambda _raw: False
    native.adapter.before_on = original_on
    native.adapter.before_on_status = original_status
    await narrow_after_save(manager, clock, runtime)
    assert native.adapter.before_on is original_on
    assert native.adapter.before_on_status is original_status
    assert writes(native) == []


@pytest.mark.asyncio
async def test_initial_storage_failure_leaves_native_callback_protocol_intact(native):
    manager, _clock, runtime = native_manager(native)
    await manager.start()

    async def unavailable_store(_data):
        raise RuntimeError("fictional store outage")

    runtime.store.async_save = unavailable_store
    with pytest.raises(RuntimeError):
        await manager._issue_on()
    assert native.adapter.before_on is None
    assert native.adapter.before_on_status is None
    assert native.adapter.before_off_status is None
    assert writes(native) == []


@pytest.mark.asyncio
async def test_cancelled_initial_storage_does_not_delete_or_install_native_hooks(native):
    manager, _clock, runtime = native_manager(native)
    await manager.start()
    started, resume = asyncio.Event(), asyncio.Event()
    original = runtime.store.async_save

    async def waiting_store(data):
        if not started.is_set():
            started.set()
            await resume.wait()
        await original(data)

    runtime.store.async_save = waiting_store
    task = asyncio.create_task(manager._issue_on())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert native.adapter.before_on is None
    assert native.adapter.before_on_status is None
    assert native.adapter.before_off_status is None
    assert writes(native) == []


@pytest.mark.asyncio
async def test_success_after_early_return_still_rechecks_native_final_dispatch_guard(native):
    manager, clock, runtime = native_manager(native)
    await manager.start()
    await narrow_after_save(manager, clock, runtime)
    await manager.set_manual_control("on", 1800)
    allowed = [True]
    runtime.sg_dispatch_allowed = lambda *, renewal=False: allowed[0]
    original = native.device.call_rpc

    async def change_during_native_preflight(method, params=None, timeout=None):
        answer = await original(method, params=params, timeout=timeout)
        if method == "Switch.GetStatus":
            allowed[0] = False
        return answer

    native.device.call_rpc = change_during_native_preflight
    assert await manager._issue_on() is False
    assert not manager.owned and not manager.desired_on
    assert writes(native) == []
    assert native.adapter.before_on is None
    assert native.adapter.before_on_status is None
    native.device.call_rpc = original
    allowed[0] = True
    assert await manager._issue_on() is True
    assert manager.owned and native.device.output
    assert writes(native) == [("Switch.Set", {"id": 0, "on": True, "toggle_after": 300})]
    assert native.adapter.before_on is None
    assert native.adapter.before_on_status is None


@pytest.mark.asyncio
async def test_callback_replaced_during_rpc_is_not_removed_by_our_cleanup(native):
    manager, _clock, _runtime = native_manager(native)
    await manager.start()
    replacement = lambda: False
    original = native.device.call_rpc

    async def replace_during_command(method, params=None, timeout=None):
        answer = await original(method, params=params, timeout=timeout)
        if method == "Switch.Set":
            native.adapter.before_on = replacement
        return answer

    native.device.call_rpc = replace_during_command
    assert await manager._issue_on() is True
    assert native.adapter.before_on is replacement
    assert native.adapter.before_on_status is None
    assert manager.owned and native.device.output
