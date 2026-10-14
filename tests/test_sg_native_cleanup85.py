"""Native hook cleanup at shortened lease and interrupted dispatch boundaries.

The transport is the actual ShellyLeaseAdapter class. Fictional lease status
isolates bookkeeping; these checks do not certify real device behaviour.
"""
import asyncio

import pytest

from custom_components.solar_pilot.sg_transport import ShellyLeaseAdapter
from test_sg_controller62 import boosted


async def native_fixture():
    manager, device, clock, runtime = await boosted(max_session_s=600)
    adapter = ShellyLeaseAdapter(runtime.hass, manager.settings["entity_id"])
    runtime.sg_dispatch_allowed = lambda *, renewal=False, automatic=False: True
    manager._adapter = adapter
    manager._injected_adapter = False
    attempted = []

    async def forbidden_rpc(*args, **kwargs):
        attempted.append((args, kwargs))
        raise AssertionError("A shortened pre-dispatch window must not reach RPC")

    adapter._rpc = forbidden_rpc
    return manager, device, clock, runtime, adapter, attempted


def final_window(manager, device, clock):
    # Before storage: 119 s fit before the cap and the old lease is live for
    # 114 s. Storage advances 60 s: only 59 s remain for a replacement lease.
    origin = clock()-461
    manager._session_started = manager._minimum_started = origin
    manager._last_renewed = clock()-60
    manager._session_finishing = False
    manager.owned = manager.desired_on = manager.relay_on = manager.relay_confirmed = True
    device.on = True
    device.start, device.duration, device.expiry = origin+275, 300, origin+575
    manager._lease_expiry = device.expiry
    manager._lease_deadline = device.expiry
    manager._relay_observed_at = clock()
    manager._relay_valid_until = device.expiry


@pytest.mark.asyncio
@pytest.mark.parametrize("existing", [None, "independent_hook"])
async def test_post_storage_final_window_keeps_uninstalled_native_hooks_on_repeated_attempts(existing):
    manager, device, clock, runtime, adapter, attempted = await native_fixture()
    hook = (lambda: False) if existing is not None else None
    adapter.before_on = hook
    status_hook = lambda _raw: False
    adapter.before_on_status = status_hook
    save = runtime.store.async_save
    slow = [True]

    async def slow_storage(data):
        await save(data)
        if slow[0]:
            slow[0] = False
            clock.advance(60)

    runtime.store.async_save = slow_storage
    for _ in range(2):
        final_window(manager, device, clock)
        slow[0] = True
        assert await manager._issue_on(renewal=True) is False
        assert hasattr(adapter, "before_on") and adapter.before_on is hook
        assert adapter.before_on_status is status_hook
        assert not manager._in_flight and manager.owned and manager.desired_on
        assert manager._session_finishing
        assert manager._lease_deadline <= manager._session_started+600
    assert not attempted and device.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_short_manual_deadline_after_storage_keeps_native_hooks_without_rpc():
    manager, device, clock, runtime, adapter, attempted = await native_fixture()
    manager.owned = manager.desired_on = False
    manager._session_started = manager._minimum_started = None
    manager._manual_control = {"mode": "on", "duration_s": 1800,
                               "expires_at": clock()+100}
    manager._manual_deadline = clock()+100
    save = runtime.store.async_save
    slow = [True]

    async def slow_storage(data):
        await save(data)
        if slow[0]:
            slow[0] = False
            clock.advance(30)

    runtime.store.async_save = slow_storage
    assert await manager._issue_on() is False  # 70 - 20 ACK = 50 s < 60 s.
    assert adapter.before_on is None and adapter.before_on_status is None
    assert not manager._in_flight and not manager._possibly_owned
    assert not attempted


@pytest.mark.asyncio
@pytest.mark.parametrize("interruption", ["storage_error", "storage_cancel", "final_window_save_cancel"])
async def test_uninstalled_native_hooks_survive_storage_failure_or_cancellation(interruption):
    manager, device, clock, runtime, adapter, attempted = await native_fixture()
    final_window(manager, device, clock)
    save = runtime.store.async_save
    saves = [0]
    # _release is a separate existing safe withdrawal route. Avoid device RPC
    # in this cleanup-only assertion while retaining its invocation evidence.
    releases = []

    async def release(reason, **kwargs):
        releases.append(reason)
        manager.desired_on = False

    manager._release = release

    async def interrupted_storage(data):
        saves[0] += 1
        if interruption == "storage_error" and saves[0] == 1:
            raise OSError("fictional storage failure")
        if interruption == "storage_cancel" and saves[0] == 1:
            raise asyncio.CancelledError
        if interruption == "final_window_save_cancel" and saves[0] == 1:
            clock.advance(60)
        elif interruption == "final_window_save_cancel" and saves[0] == 2:
            raise asyncio.CancelledError
        await save(data)

    runtime.store.async_save = interrupted_storage
    if interruption == "storage_error":
        assert await manager._issue_on(renewal=True) is False
    else:
        with pytest.raises(asyncio.CancelledError):
            await manager._issue_on(renewal=True)
    assert adapter.before_on is None and adapter.before_on_status is None
    assert not manager._in_flight and not manager.desired_on
    assert not attempted and releases


@pytest.mark.asyncio
@pytest.mark.parametrize("replace_hook", [False, True])
async def test_late_cancellation_removes_only_this_dispatch_callback(replace_hook):
    manager, device, clock, _runtime, adapter, attempted = await native_fixture()
    clock.advance(60)
    entered = asyncio.Event()
    release_calls = []

    async def release(reason, **kwargs):
        release_calls.append(reason)
        manager.desired_on = False

    manager._release = release

    async def awaiting_transport(*, lease_s):
        # Mirror the real adapter's required callback protocol. No physical RPC
        # occurs in this interrupted synthetic preflight.
        assert adapter.before_on_status(device.status()) is True
        assert adapter.before_on() is True
        entered.set()
        await asyncio.Event().wait()

    adapter.set_on = awaiting_transport
    task = asyncio.create_task(manager._issue_on(renewal=True))
    await entered.wait()
    replacement = lambda: False
    replacement_status = lambda _raw: False
    if replace_hook:
        adapter.before_on = replacement
        adapter.before_on_status = replacement_status
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert adapter.before_on is (replacement if replace_hook else None)
    assert adapter.before_on_status is (replacement_status if replace_hook else None)
    assert hasattr(adapter, "before_on")
    assert not manager._in_flight and not manager.desired_on
    assert not attempted and release_calls
