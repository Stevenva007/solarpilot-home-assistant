"""Fictitious source recovery after actual source-driven contact release.

A timed request is not permission to pulse an intermittently usable meter.
"""
import asyncio
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_sg_controller62 import fixture


def observation(clock, *, site_stamp=None, identity="fictional-inputs"):
    stamp = clock() if site_stamp is None else site_stamp
    return {"valid": True, "watts": 0, "stamp": min(stamp, clock()),
        "report_stamp": clock(), "source_identity": {"binding": identity},
        "source_reports": {"p1": clock(), "site": stamp, "pv": clock()}}


async def step(manager, *, fresh=True, advance=0, site_stamp=None, phase=True, hard=False,
               identity="fictional-inputs", surplus=0):
    manager._clock.advance(advance)
    current = observation(manager._clock, site_stamp=site_stamp, identity=identity)
    current["watts"] = surplus
    manager.runtime.sg_usable_solar_observation = lambda: deepcopy(current)
    return await manager.tick(surplus_w=surplus, real_surplus_w=surplus, data_fresh=fresh,
        phase_allowed=phase, hard_limit=hard, grid_import_w=0,
        solar_stamp=current["stamp"], grid_import_stamp=manager._clock(),
        grid_import_source="fictional-grid", start_source_identity=identity,
        usable_solar_observation=current)


async def stopped(*, duration=3600):
    manager, adapter, clock, runtime = fixture(start_delay_s=120, rest_s=900)
    await manager.set_manual_control("on", duration)
    await step(manager)
    assert manager.owned and adapter.on  # Initial deliberate ON stays immediate.
    expiry = manager._manual_control["expires_at"]
    await step(manager, fresh=False, advance=5)
    assert not manager.owned and not adapter.on
    assert manager._source_recovery is not None
    return manager, adapter, clock, runtime, expiry


@pytest.mark.asyncio
async def test_manual_source_stop_respects_rest_then_original_source_stability():
    manager, adapter, clock, _, expiry = await stopped()
    for _ in range(29):
        await step(manager, advance=30)
        assert not adapter.on
    await step(manager, advance=30)  # protected rest expires, stability starts now
    assert not adapter.on
    await step(manager, advance=60)
    assert not adapter.on
    await step(manager, advance=60)
    assert manager.owned and adapter.on, (manager.reason, manager._blocked_reasons, manager.fault_code)
    assert adapter.calls == [("on", 300), ("off", None), ("on", 300)]
    assert manager._source_recovery is None
    assert manager._manual_control["expires_at"] == expiry


@pytest.mark.asyncio
async def test_repeated_recovered_ticks_and_p1_reports_cannot_replace_new_site_report():
    manager, adapter, clock, _, _ = await stopped()
    await step(manager, advance=900)
    site_stamp = clock()
    for _ in range(4):
        await step(manager, advance=30, site_stamp=site_stamp)
    assert not adapter.on
    await step(manager, advance=1)  # all original clocks finally progress
    assert manager.owned and adapter.on


@pytest.mark.asyncio
async def test_source_flaps_after_rest_restart_full_stability_without_any_on_pulse():
    manager, adapter, clock, _, _ = await stopped()
    await step(manager, advance=900)
    for _ in range(8):
        await step(manager, advance=40)
        await step(manager, fresh=False, advance=5)
        assert not adapter.on
    await step(manager, advance=1)
    await step(manager, advance=60)
    assert not adapter.on
    await step(manager, advance=60)
    assert adapter.on
    assert len([c for c in adapter.calls if c[0] == "on"]) == 2


@pytest.mark.asyncio
async def test_restart_does_not_restore_accumulated_recovery_stability_or_extend_manual_deadline():
    manager, adapter, clock, runtime, expiry = await stopped()
    await step(manager, advance=900)
    await step(manager, advance=90)
    snapshot = manager.snapshot()
    replacement = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = replacement
    runtime._snapshot = lambda: {"sg_boost": replacement.snapshot()}
    replacement.restore(snapshot)
    assert replacement._source_recovery is not None
    assert replacement._source_recovery_candidate is None
    assert replacement._manual_control["expires_at"] == expiry
    await step(replacement, advance=30)
    assert not adapter.on
    await step(replacement, advance=60)
    assert not adapter.on
    await step(replacement, advance=60)
    assert adapter.on
    assert replacement._manual_control["expires_at"] == expiry


@pytest.mark.asyncio
async def test_original_manual_expiry_during_source_recovery_never_replays_on():
    manager, adapter, clock, _, expiry = await stopped(duration=1800)
    while clock() <= expiry + 120:
        await step(manager, fresh=False, advance=60)
    assert manager.manual_mode == "auto"
    for _ in range(5):
        await step(manager, advance=60)
    assert not adapter.on
    assert len([c for c in adapter.calls if c[0] == "on"]) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("control", ["on", "auto", "off"])
async def test_reselecting_manual_mode_cannot_clear_source_recovery(control):
    manager, adapter, clock, _, _ = await stopped()
    await manager.set_manual_control(control, None if control == "auto" else 1800)
    assert manager._source_recovery is not None
    await step(manager, advance=60)
    assert not adapter.on


@pytest.mark.asyncio
@pytest.mark.parametrize("corrupt", [False, {}, {"schema": 1, "stopped_at": True},
                                     {"schema": 1, "stopped_at": float("nan")}])
async def test_malformed_recovery_storage_cannot_erase_blocker(corrupt):
    manager, adapter, clock, runtime, _ = await stopped()
    snapshot = manager.snapshot()
    snapshot["source_recovery"] = corrupt
    replacement = SGBoostManager(runtime, adapter=adapter, clock=clock)
    replacement.restore(snapshot)
    await step(replacement)
    assert replacement._source_recovery is not None and not adapter.on


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["hard", "phase"])
async def test_recovery_does_not_bypass_hard_or_phase_gates(guard):
    manager, adapter, clock, _, _ = await stopped()
    await step(manager, advance=900)
    await step(manager, advance=60)
    await step(manager, advance=60, phase=guard != "phase", hard=guard == "hard")
    assert not adapter.on
    await step(manager, advance=1)
    assert not adapter.on  # fresh stability required after failed guard


@pytest.mark.asyncio
async def test_live_source_binding_change_during_save_revokes_completed_recovery():
    manager, adapter, clock, runtime, _ = await stopped()
    await step(manager, advance=900)
    await step(manager, advance=60)
    original_save = runtime.store.async_save
    async def rebind(data):
        await original_save(data)
        runtime.sg_usable_solar_observation = lambda: observation(clock, identity="different-inputs")
    runtime.store.async_save = rebind
    await step(manager, advance=60)
    assert not adapter.on
    assert len([c for c in adapter.calls if c[0] == "on"]) == 1
    assert manager._source_recovery is not None


@pytest.mark.asyncio
async def test_two_early_reports_followed_by_cached_reads_do_not_prove_full_recovery_window():
    manager, adapter, clock, _, _ = await stopped()
    await step(manager, advance=900)
    await step(manager, advance=1)
    cached = observation(clock)
    manager.runtime.sg_usable_solar_observation = lambda: deepcopy(cached)
    clock.advance(119)
    await manager.tick(surplus_w=0, real_surplus_w=0, data_fresh=True,
        phase_allowed=True, grid_import_w=0, solar_stamp=cached["stamp"],
        grid_import_stamp=clock(), grid_import_source="fictional-grid",
        start_source_identity="fictional-inputs", usable_solar_observation=cached)
    assert not adapter.on
    await step(manager, advance=1)
    assert adapter.on


@pytest.mark.asyncio
async def test_source_release_intent_is_persisted_before_off_and_cannot_resume_old_lease():
    manager, adapter, clock, runtime = fixture(start_delay_s=120, rest_s=900)
    await manager.set_manual_control("on", 3600)
    await step(manager)
    original_off = adapter.set_off
    release_intents = []
    async def inspected_off():
        saved = deepcopy(runtime.store.saves[-1]["sg_boost"])
        assert saved["source_recovery"] is not None
        assert saved["request_rest_policy"] == "protected"
        release_intents.append(saved)
        return await original_off()
    adapter.set_off = inspected_off
    await step(manager, fresh=False, advance=5)
    replacement = SGBoostManager(runtime, adapter=adapter, clock=clock)
    replacement.restore(release_intents[0])
    assert replacement._restart_resume is None
    assert replacement._source_recovery is not None
    await step(replacement)
    assert not adapter.on
    assert len([c for c in adapter.calls if c[0] == "on"]) == 1


@pytest.mark.asyncio
async def test_release_intent_storage_failure_never_prevents_existing_safe_off():
    manager, adapter, _, runtime = fixture(start_delay_s=120, rest_s=900)
    await manager.set_manual_control("on", 3600)
    await step(manager)
    original_save = runtime.store.async_save
    saves = 0
    async def fail_once(data):
        nonlocal saves
        saves += 1
        if saves == 1:
            raise OSError("fictional storage failure")
        await original_save(data)
    runtime.store.async_save = fail_once
    await step(manager, fresh=False, advance=5)
    assert not adapter.on and manager._source_recovery is not None
    assert runtime.store.saves[-1]["sg_boost"]["source_recovery"] is not None


@pytest.mark.asyncio
async def test_hung_release_intent_store_is_cancelled_before_existing_safe_off():
    manager, adapter, _, runtime = fixture(start_delay_s=120, rest_s=900)
    await manager.set_manual_control("on", 3600)
    await step(manager)
    manager.settings["ack_timeout_s"] = .02  # Deterministic short timeout, no physical device.
    original_save = runtime.store.async_save
    saves = 0
    cancelled = False
    async def hang_once(data):
        nonlocal saves, cancelled
        saves += 1
        if saves == 1:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled = True
                raise
        await original_save(data)
    runtime.store.async_save = hang_once
    await asyncio.wait_for(step(manager, fresh=False, advance=5), 1)
    assert cancelled and not adapter.on
    assert manager._source_recovery is not None


@pytest.mark.asyncio
async def test_cancelled_release_intent_still_attempts_off_and_preserves_cancel_if_off_fails():
    manager, adapter, _, runtime = fixture(start_delay_s=120, rest_s=900)
    await manager.set_manual_control("on", 3600)
    await step(manager)
    original_save = runtime.store.async_save
    saving = asyncio.Event()
    saves = 0
    async def interrupted_save(data):
        nonlocal saves
        saves += 1
        if saves == 1:
            saving.set()
            await asyncio.Event().wait()
        await original_save(data)
    runtime.store.async_save = interrupted_save
    adapter.off_bad = True
    release = asyncio.create_task(step(manager, fresh=False, advance=5))
    await asyncio.wait_for(saving.wait(), 1)
    release.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(release, 1)
    assert adapter.calls[-1] == ("off", None)
    assert manager.fault_code == "off_failed" and manager.relay_on is None
    assert runtime.store.saves[-1]["sg_boost"]["source_recovery"] is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("stored_rest", [None, "corrupt", 0])
async def test_source_recovery_reconstructs_minimum_protected_rest_from_stop(stored_rest):
    manager, adapter, clock, runtime, _ = await stopped()
    snapshot = manager.snapshot()
    snapshot["rest_until_wall"] = stored_rest
    replacement = SGBoostManager(runtime, adapter=adapter, clock=clock)
    replacement.restore(snapshot)
    assert replacement._rest_until-clock() >= 900
    await step(replacement)
    await step(replacement, advance=120)
    assert not adapter.on


@pytest.mark.asyncio
async def test_malformed_source_recovery_and_rest_require_new_full_protected_rest():
    manager, adapter, clock, runtime, _ = await stopped()
    snapshot = manager.snapshot()
    snapshot.update(source_recovery=False, rest_until_wall=None)
    clock.advance(100)
    replacement = SGBoostManager(runtime, adapter=adapter, clock=clock)
    replacement.restore(snapshot)
    assert replacement._rest_until-clock() >= 900
    await step(replacement)
    await step(replacement, advance=120)
    assert not adapter.on


@pytest.mark.asyncio
async def test_automatic_source_stop_also_keeps_nonreplaceable_rest():
    manager, adapter, _, runtime = fixture(start_delay_s=120, rest_s=900,
        profile="general", profile_confirmed=True, cooling_protection_confirmed=True)
    await step(manager, surplus=4000)
    await step(manager, surplus=4000, advance=120)
    assert manager.owned and adapter.on, (manager.reason, manager._blocked_reasons, manager.fault_code)
    await step(manager, fresh=False, advance=5)
    assert not adapter.on and manager._source_recovery is not None
    assert manager._request_rest_policy == "protected"
    for _ in range(14):
        await step(manager, surplus=9000, advance=60)
        assert not adapter.on
    assert manager._source_recovery_candidate is None
    assert runtime.store.saves[-1]["sg_boost"]["request_rest_policy"] == "protected"
