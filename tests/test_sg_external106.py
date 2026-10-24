"""External ON takeover with fictional clocks, relays and measurements."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_sg_controller62 import fixture, tick
from test_sg_transport62 import native, writes


async def external(**settings):
    manager, adapter, clock, runtime = fixture(**settings)
    adapter.on = True
    await manager.start()
    return manager, adapter, clock, runtime


@pytest.mark.asyncio
async def test_observation_keeps_contact_and_does_not_restart_countdown():
    manager, adapter, clock, _ = await external()
    deadline = manager.external_control_overview()["expires_at"]
    for _ in range(9):
        clock.advance(99)
        await tick(manager)
    view = manager.overview()
    assert view["state"] == "external_on" and view["owner"] == "external"
    assert view["external_control"]["remaining_s"] == 9
    assert view["external_control"]["expires_at"] == deadline
    assert adapter.on and not adapter.calls and not manager.manual_hold


@pytest.mark.asyncio
async def test_exact_deadline_continues_with_short_timer_without_off_pulse():
    manager, adapter, clock, _ = await external()
    origin = clock()
    clock.advance(900)
    await tick(manager)
    assert adapter.on and manager.owned and manager.desired_on
    assert adapter.calls == [("on", 300)]
    assert manager._session_started == origin
    assert manager._minimum_started == origin
    assert not manager.external_control_overview()["active"]


@pytest.mark.asyncio
async def test_manual_period_cannot_become_an_automatic_night_boost():
    manager, adapter, clock, _ = await external()
    clock.advance(900)
    await tick(manager, surplus=0, imported=0)
    assert not adapter.on and adapter.calls == [("off", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("condition", ["import", "data", "priority", "phase"])
async def test_due_external_contact_is_released_when_automatic_conditions_fail(condition):
    manager, adapter, clock, runtime = await external()
    clock.advance(900)
    kwargs = {"surplus_w": 0, "grid_import_w": 0, "data_fresh": True, "phase_allowed": True}
    if condition == "import":
        kwargs["grid_import_w"] = 601
    elif condition == "data":
        kwargs["data_fresh"] = False
    elif condition == "phase":
        kwargs["phase_allowed"] = False
    elif condition == "priority":
        kwargs["priority_allowed"] = False
    await manager.tick(**kwargs, grid_import_stamp=clock())
    assert adapter.calls == [("off", None)] and not adapter.on
    assert not manager.external_control_overview()["active"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["observe", "paused"])
async def test_read_only_or_pause_does_not_take_control_of_external_on(mode):
    manager, adapter, clock, runtime = await external()
    deadline = manager.external_control_overview()["expires_at"]
    runtime.mode = mode
    clock.advance(901)
    await tick(manager, imported=900)
    assert adapter.on and not adapter.calls
    assert manager.external_control_overview()["expires_at"] == deadline
    runtime.mode = "solar"
    await tick(manager, imported=900)
    assert adapter.calls == [("off", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("elapsed", [300, 899, 901, 1800])
async def test_restart_preserves_original_absolute_deadline(elapsed):
    manager, adapter, clock, runtime = await external()
    stored = deepcopy(manager.snapshot())
    deadline = manager.external_control_overview()["expires_at"]
    clock.advance(elapsed)
    fresh = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = fresh
    fresh.restore(stored)
    await fresh.start()
    assert fresh.external_control_overview()["expires_at"] == deadline
    assert fresh.external_control_overview()["remaining_s"] == max(0, 900-elapsed)
    await tick(fresh)
    assert bool(adapter.calls) == (elapsed >= 900)


@pytest.mark.asyncio
async def test_manual_off_cancels_external_takeover_and_prevents_automatic_restart():
    manager, adapter, clock, _ = await external()
    clock.advance(400)
    adapter.on = False
    await tick(manager)
    clock.advance(1000)
    await tick(manager)
    assert not adapter.calls and manager.manual_hold
    assert not manager.external_control_overview()["active"]


@pytest.mark.asyncio
async def test_missing_contact_at_deadline_defers_without_extending_it():
    manager, adapter, clock, _ = await external()
    deadline = manager.external_control_overview()["expires_at"]
    clock.advance(900)
    adapter.online = False
    await tick(manager)
    assert not adapter.calls
    assert manager.external_control_overview()["expires_at"] == deadline
    adapter.online = True
    clock.advance(31)
    await tick(manager)
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_explicit_manual_on_can_name_external_on_without_resume_error():
    manager, adapter, clock, _ = await external()
    await manager.set_manual_control("on", 1800)
    await tick(manager, surplus=0)
    assert manager.manual_mode == "on" and manager.owned and adapter.on
    assert not manager.external_control_overview()["active"]
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_takeover_timer_cannot_outlive_original_session_ceiling():
    manager, adapter, clock, _ = await external(max_session_s=1000)
    clock.advance(900)
    await tick(manager)
    assert adapter.on and manager.owned
    assert adapter.calls == [("on", 80)]
    assert adapter.expiry <= manager._session_started+1000


@pytest.mark.asyncio
async def test_later_physical_off_during_takeover_preflight_is_never_replayed(native):
    manager, _adapter, clock, _runtime = fixture()
    manager._adapter = native.adapter
    native.device.output = True
    await manager.start()
    assert manager.external_control_overview()["active"]
    clock.advance(900)
    native.device.clock += 900
    original = native.adapter.set_on

    async def later_off(lease_s):
        native.device.output = False
        native.device.started = native.device.duration = None
        return await original(lease_s)

    native.adapter.set_on = later_off
    await tick(manager)
    assert writes(native) == []
    assert manager.manual_hold and not manager.owned and not manager.desired_on
