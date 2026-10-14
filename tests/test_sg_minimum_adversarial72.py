"""Adversarial minimum-SG checks with fictional clocks, meters and contacts.

These cases exercise confirmed authority and the real final runtime gate.
They do not establish a physical Panasonic or Shelly commissioning result.
"""
from copy import deepcopy
import time

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_electrical_limits69 import protected_ev
from test_sg_budget_priority62 import configured
from test_sg_controller62 import boosted, fixture, tick


def live_dispatch(manager, *, imported=400):
    """Use actual SolarRuntime policy, independently of controller doubles."""
    # The synthetic session clock is monotonic; these HA meter doubles report
    # actual wall times. Align contact proof with that distinct wall clock.
    shift = time.time() - manager._wall_clock()
    if manager._relay_observed_at is not None:
        manager._relay_observed_at += shift
    if manager._relay_valid_until is not None:
        manager._relay_valid_until += shift
    if manager._import_observation is not None:
        manager._import_observation["stamp"] += shift
    manager._wall_clock = time.time
    live, hass = configured(export=0, reserve=0)
    live.sg_boost = manager
    hass.states.set("sensor.grid", imported, {"unit_of_measurement": "W"})
    manager.runtime.sg_dispatch_allowed = live.sg_dispatch_allowed
    return live, hass


async def advance_import(manager, clock, target):
    """Observe often enough that the local contact lease cannot expire."""
    while clock() < target:
        clock.advance(min(60, target - clock()))
        await tick(manager, surplus=0, imported=400)


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [
    "ownership", "desired", "confirmed_contact", "on_contact",
    "lease_deadline", "relay_deadline", "fresh_contact",
])
async def test_import_exception_requires_current_owned_on_and_live_lease(missing):
    manager, _adapter, clock, _runtime = await boosted(min_session_s=1200, import_threshold_w=300, stop_delay_s=60)
    live, _hass = live_dispatch(manager)
    assert live.sg_dispatch_allowed(renewal=True)
    if missing == "ownership":
        manager.owned = False
        manager._possibly_owned = True  # A write intent is not confirmed ON.
    elif missing == "desired":
        manager.desired_on = False
    elif missing == "confirmed_contact":
        manager.relay_confirmed = False
    elif missing == "on_contact":
        manager.relay_on = False
    elif missing == "lease_deadline":
        manager._lease_deadline = clock()
    elif missing == "relay_deadline":
        manager._relay_valid_until = manager._wall_clock()
    else:
        manager._relay_observed_at = manager._wall_clock() - manager.settings["stale_s"] - 1
    assert not manager.minimum_hold_active
    assert not live.sg_dispatch_allowed(renewal=True)


@pytest.mark.asyncio
async def test_renewal_flag_never_grants_an_initial_on_during_import():
    manager, adapter, _clock, _runtime = fixture(min_session_s=1200, import_threshold_w=300, stop_delay_s=60)
    live_dispatch(manager)
    await manager.start()
    await manager._issue_on(renewal=True)
    assert not adapter.calls
    assert not manager.owned and not manager.desired_on


@pytest.mark.asyncio
@pytest.mark.parametrize("hard_guard", [
    "fixed_import", "committed_load", "stale_grid", "stale_pv",
    "battery_discharge", "missing_phases", "missing_quarter", "protected_ev",
    "pause", "restart", "runtime_fault", "pending_command", "removal",
])
async def test_minimum_import_permission_never_bypasses_final_live_hard_guards(hard_guard):
    manager, _adapter, _clock, _runtime = await boosted(min_session_s=1200, import_threshold_w=300, stop_delay_s=60)
    live, hass = live_dispatch(manager)
    assert manager.minimum_hold_active and live.sg_dispatch_allowed(renewal=True)
    if hard_guard == "fixed_import":
        hass.states.set("sensor.grid", 501, {"unit_of_measurement": "W"})
    elif hard_guard == "committed_load":
        live.states["a"].target_w += 101
    elif hard_guard in ("stale_grid", "stale_pv"):
        entity = "sensor.grid" if hard_guard == "stale_grid" else "sensor.public_pv"
        obj = hass.states.get(entity)
        hass.states.set(entity, obj.state, obj.attributes, age=121)
    elif hard_guard == "battery_discharge":
        live.settings.update(battery_power_entity="sensor.fixture_battery",
                             battery_sign="discharge_positive")
        hass.states.set("sensor.fixture_battery", 51, {"unit_of_measurement": "W"})
    elif hard_guard == "missing_phases":
        live.phase_settings.update(enabled=True, control_starts=True)
    elif hard_guard == "missing_quarter":
        live.capacity_settings.update(enabled=True)
    elif hard_guard == "protected_ev":
        protected_ev(live, hass)
    elif hard_guard == "pause":
        live.mode = "paused"
    elif hard_guard == "restart":
        live.recovery["a"] = {"fictional": True}
        live.faults["a"] = "Fictional unresolved command"
    elif hard_guard == "runtime_fault":
        live.faults["a"] = "Fictional runtime fault"
    elif hard_guard == "pending_command":
        live.pending = {"fictional": True}
    else:
        live.removal_requested = True
    assert not live.sg_dispatch_allowed(renewal=True)
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_final_transport_gate_rechecks_minimum_after_async_preflight():
    manager, adapter, clock, _runtime = await boosted(min_session_s=1200, import_threshold_w=300, stop_delay_s=60)
    live, _hass = live_dispatch(manager)
    confirmed = clock()
    await advance_import(manager, clock, confirmed + 1199)
    assert manager.minimum_hold_active and live.sg_dispatch_allowed(renewal=True)
    calls = list(adapter.calls)
    adapter.before_on = None

    class DispatchChanged(Exception):
        code = "dispatch_changed"
        command_attempted = False

    async def preflight_crosses_minimum(lease_s):
        clock.advance(2)
        assert not manager.minimum_hold_active
        if adapter.before_on() is not True:
            raise DispatchChanged()
        raise AssertionError("Expired minimum must not reach the contact write")

    adapter.set_on = preflight_crosses_minimum
    await manager._issue_on(renewal=True)
    assert adapter.calls == calls + [("off", None)]
    assert not manager.owned and not manager.desired_on and not manager.fault


@pytest.mark.asyncio
async def test_minimum_begins_after_on_readback_while_maximum_keeps_write_clock():
    manager, adapter, clock, _runtime = fixture(
        min_session_s=1200, import_threshold_w=300, stop_delay_s=60, max_session_s=3600, start_delay_s=30)
    original_on = adapter.set_on
    first = True
    adapter.before_on = None
    issued = []

    async def delayed_first_readback(lease_s):
        nonlocal first
        if first:
            first = False
            clock.advance(5)  # Native asynchronous preflight.
            assert adapter.before_on() is True
            issued.append(clock())
            await original_on(lease_s=lease_s)
            clock.advance(10)  # Contact ON exists before ACK/readback returns.
            return adapter.status()
        assert adapter.before_on() is True
        return await original_on(lease_s=lease_s)

    adapter.set_on = delayed_first_readback
    await tick(manager)
    clock.advance(30)
    await tick(manager)
    confirmed = clock()
    assert manager.owned and manager._session_started == issued[0]
    assert manager._lease_deadline == issued[0] + 300
    live_dispatch(manager)
    await advance_import(manager, clock, confirmed + 1199)
    assert manager.owned and manager.minimum_hold_active
    clock.advance(1)
    await tick(manager, surplus=0, imported=400)
    assert not manager.owned and adapter.calls[-1] == ("off", None)
    assert manager._last_session["duration_s"] == 1210


@pytest.mark.asyncio
async def test_shorter_hard_session_cap_is_not_extended_by_confirmed_minimum():
    manager, adapter, clock, _runtime = fixture(
        min_session_s=1200, import_threshold_w=300, stop_delay_s=60, max_session_s=300, lease_s=600)
    await tick(manager)
    clock.advance(manager.settings["start_delay_s"])
    await tick(manager)
    assert manager.owned and manager.desired_on
    started = manager._session_started
    lease = 300 - manager.settings["ack_timeout_s"]
    assert adapter.calls == [("on", lease)]
    await advance_import(manager, clock, started + lease - 1)
    assert manager.owned
    assert manager._lease_deadline <= started + 300
    clock.advance(started + 300 - clock())
    await tick(manager, surplus=0, imported=400)
    assert not manager.owned and not manager.minimum_hold_active
    assert not adapter.on
    assert all(lease <= 300 for command, lease in adapter.calls if command == "on")


@pytest.mark.asyncio
@pytest.mark.parametrize("receipt_delay_s", [5, 19.9])
async def test_initial_on_receipt_delay_cannot_extend_local_lease_past_hard_maximum(receipt_delay_s):
    manager, adapter, clock, _runtime = fixture(
        min_session_s=1200, import_threshold_w=300, stop_delay_s=60, max_session_s=300, lease_s=600)
    original_on = adapter.set_on
    adapter.before_on = None
    issued = []

    async def delayed_server_receipt(lease_s):
        assert adapter.before_on() is True
        issued.append(clock())
        clock.advance(receipt_delay_s)  # Server starts its timer after dispatch.
        return await original_on(lease_s=lease_s)

    adapter.set_on = delayed_server_receipt
    await tick(manager)
    clock.advance(manager.settings["start_delay_s"])
    await tick(manager)
    assert manager.owned and manager._session_started == issued[0]
    assert manager._lease_deadline <= issued[0] + 300
    assert manager._effective_minimum_s() <= 300 - receipt_delay_s
    # HA does nothing after confirmation. Local expiry still respects hardmax.
    clock.advance(issued[0] + 300 - clock() + 0.01)
    assert adapter.status()["output"] is False


@pytest.mark.asyncio
async def test_slow_ownership_save_cannot_move_renewed_lease_past_hard_session_limit():
    manager, adapter, clock, runtime = await boosted(
        min_session_s=1200, import_threshold_w=300, stop_delay_s=60, max_session_s=600)
    started = manager._session_started
    for _ in range(4):
        clock.advance(60)
        await tick(manager)
    clock.advance(60)
    original_save = runtime.store.async_save
    delayed = False

    async def slow_first_save(data):
        nonlocal delayed
        if not delayed:
            delayed = True
            clock.advance(25)  # Persistence is outside the bounded relay ACK.
        await original_save(data)

    runtime.store.async_save = slow_first_save
    await tick(manager, surplus=0, imported=400)
    assert manager._lease_deadline is None or manager._lease_deadline <= started + 600
    # No further HA execution. The local permission must still end on time.
    clock.advance(started + 600 - clock() + 0.01)
    assert adapter.status()["output"] is False


@pytest.mark.asyncio
async def test_restart_preserves_evidence_but_never_restores_minimum_authority():
    previous, adapter, clock, runtime = await boosted(min_session_s=1200, import_threshold_w=300, stop_delay_s=60)
    saved = deepcopy(previous.snapshot())
    saved.pop("session_checkpoint")  # Beta.83 had no fresh continuity proof.
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = manager
    runtime._snapshot = lambda: {"sg_boost": manager.snapshot()}
    manager.restore(saved)
    assert not manager.minimum_hold_active
    assert not manager.owned and not manager.desired_on
    await manager.start()
    assert adapter.calls == [("on", 300), ("off", None)]
    await tick(manager, surplus=0, imported=400)
    assert not manager.minimum_hold_active and not manager.owned
    assert adapter.calls == [("on", 300), ("off", None)]
