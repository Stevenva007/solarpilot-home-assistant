"""Independent timed SG and restart boundary probes with fictional contacts."""
import asyncio
from copy import deepcopy, copy

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_sg_controller62 import Store, fixture, tick


async def manual_on(*, duration=1800, **settings):
    manager, adapter, clock, runtime = fixture(min_session_s=0, **settings)
    await manager.start()
    await manager.set_manual_control("on", duration)
    await tick(manager, surplus=0)
    assert manager.owned and manager.desired_on
    assert adapter.on
    return manager, adapter, clock, runtime


def restored_manager(previous, adapter, clock, stored=None):
    runtime = copy(previous.runtime)
    runtime.store = Store()
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = manager
    runtime._snapshot = lambda: {"sg_boost": manager.snapshot()}
    manager.restore(deepcopy(stored if stored is not None else previous.snapshot()))
    return manager, runtime


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,duration", [
    ("on", True), ("on", 1800.0), ("on", "1800"), ("on", 1801),
    ("off", False), ("off", 3600.0), ("off", None), ("auto", 1800),
    ("automatic", None), (True, 1800),
])
async def test_timed_contract_rejects_non_exact_choices_without_contact_write(mode, duration):
    manager, adapter, _clock, _runtime = fixture()
    await manager.start()
    before = deepcopy(manager.snapshot())
    with pytest.raises((HomeAssistantError, ValueError)):
        await manager.set_manual_control(mode, duration)
    assert not adapter.calls
    assert manager.snapshot() == before


@pytest.mark.asyncio
@pytest.mark.parametrize("gate", ["data_fresh", "phase_allowed", "priority_allowed", "hard_limit"])
async def test_timed_on_never_buys_permission_past_current_hard_guards(gate):
    manager, adapter, clock, _runtime = await manual_on()
    clock.advance(10)
    values = {"surplus_w": 0, "grid_import_w": 0, "data_fresh": True,
              "phase_allowed": True, "grid_import_stamp": manager._wall_clock()}
    values[gate] = gate == "hard_limit"
    await manager.tick(**values)
    assert not manager.desired_on and not adapter.on
    assert adapter.calls[-1][0] == "off"


@pytest.mark.asyncio
async def test_wallclock_rollback_does_not_extend_running_override_window():
    manager, adapter, clock, _runtime = await manual_on()
    wall = [clock()]
    manager._wall_clock = lambda: wall[0]
    wall[0] -= 7200
    clock.advance(1801)
    await tick(manager, surplus=0)
    control = manager.overview()["manual_control"]
    assert control["mode"] == "auto"
    assert control["active"] is False
    assert not adapter.on


@pytest.mark.asyncio
async def test_manual_off_storage_failure_cannot_allow_prior_on_to_renew():
    manager, adapter, clock, runtime = await manual_on()
    original_save = runtime.store.async_save

    async def failed_save(_data):
        raise RuntimeError("fictional persistence failure")

    runtime.store.async_save = failed_save
    with pytest.raises(RuntimeError):
        await manager.set_manual_control("off", 1800)
    runtime.store.async_save = original_save
    before = len([call for call in adapter.calls if call[0] == "on"])
    clock.advance(60)
    await tick(manager, surplus=4000)
    assert len([call for call in adapter.calls if call[0] == "on"]) == before
    assert not manager.desired_on


@pytest.mark.asyncio
async def test_failed_manual_on_intent_save_never_grants_later_grid_on():
    manager, adapter, _clock, runtime = fixture(min_session_s=0)
    await manager.start()
    original_save = runtime.store.async_save

    async def failed_save(_data):
        raise RuntimeError("fictional persistence failure")

    runtime.store.async_save = failed_save
    with pytest.raises(RuntimeError):
        await manager.set_manual_control("on", 1800)
    runtime.store.async_save = original_save
    await tick(manager, surplus=0)
    assert not adapter.calls
    assert not manager.owned and not manager.desired_on


@pytest.mark.asyncio
async def test_restart_expired_contact_rechecks_bounded_user_intent_without_resetting_session():
    manager, adapter, clock, _runtime = await manual_on()
    stored = manager.snapshot()
    calls = list(adapter.calls)
    clock.advance(301)
    assert adapter.status()["output"] is False
    restored, _ = restored_manager(manager, adapter, clock, stored)
    await restored.start()
    await tick(restored, surplus=0)
    assert adapter.calls == calls + [("on", 300)]
    assert restored.owned and restored.desired_on
    assert restored._session_started == manager._session_started
    assert restored.overview()["manual_control"]["remaining_s"] == 1499


@pytest.mark.asyncio
async def test_restart_different_timer_is_external_even_with_matching_saved_mode():
    manager, adapter, clock, _runtime = await manual_on()
    stored = manager.snapshot()
    adapter.start = clock()
    adapter.duration = 500
    adapter.expiry = clock() + 500
    restored, _ = restored_manager(manager, adapter, clock, stored)
    calls = list(adapter.calls)
    await restored.start()
    await tick(restored, surplus=4000)
    assert adapter.on
    assert adapter.calls == calls
    assert restored.manual_hold and not restored.owned


@pytest.mark.asyncio
async def test_startup_checkpoint_does_not_erase_pending_continuity_proof():
    manager, adapter, clock, _runtime = await manual_on()
    stored = manager.snapshot()
    clock.advance(5)
    first, _ = restored_manager(manager, adapter, clock, stored)
    startup_checkpoint = first.snapshot()
    second, _ = restored_manager(first, adapter, clock, startup_checkpoint)
    calls = list(adapter.calls)
    await second.start()
    await tick(second, surplus=4000)
    assert second.owned and second.desired_on
    assert adapter.on
    assert not any(call[0] == "off" for call in adapter.calls[len(calls):])
    assert second.overview()["manual_control"]["remaining_s"] <= 1795


@pytest.mark.asyncio
@pytest.mark.parametrize("activated", [False, True])
async def test_persisted_manual_intent_cannot_follow_same_entity_to_new_registry_binding(activated):
    manager, adapter, clock, _runtime = fixture(min_session_s=0)
    native_status = adapter.status
    binding = ["fixture-registry-binding-A"]
    adapter.status = lambda: {**native_status(), "binding_identity": binding[0]}
    await manager.start()
    await manager.set_manual_control("on", 1800)
    if activated:
        await tick(manager, surplus=0)
        assert manager.owned
    stored = manager.snapshot()
    clock.advance(301)
    adapter.status()
    binding[0] = "fixture-registry-binding-B"
    restored, _ = restored_manager(manager, adapter, clock, stored)
    calls = list(adapter.calls)
    await restored.start()
    await tick(restored, surplus=0)
    assert adapter.calls == calls
    assert not restored.desired_on and not restored.owned
    assert restored.manual_mode != "on"


@pytest.mark.asyncio
async def test_explicit_off_invalidates_on_while_original_ack_is_still_pending():
    manager, adapter, _clock, _runtime = fixture(min_session_s=0)
    await manager.start()
    await manager.set_manual_control("on", 1800)
    native_on = adapter.set_on
    entered, resume = asyncio.Event(), asyncio.Event()

    async def delayed_on(lease_s):
        entered.set()
        await resume.wait()
        return await native_on(lease_s=lease_s)

    adapter.set_on = delayed_on
    on_task = asyncio.create_task(tick(manager, surplus=0))
    await entered.wait()
    off_task = asyncio.create_task(manager.set_manual_control("off", 1800))
    await asyncio.sleep(0)
    resume.set()
    await asyncio.gather(on_task, off_task)
    assert adapter.calls == [("on", 300), ("off", None)]
    assert not adapter.on and not manager.desired_on
    assert manager.manual_mode == "off"


@pytest.mark.asyncio
async def test_manual_deadline_crossed_during_final_preflight_never_writes_on():
    manager, adapter, clock, _runtime = fixture(min_session_s=0)
    await manager.start()
    await manager.set_manual_control("on", 1800)
    adapter.before_on = None

    class ChangedBeforeWrite(Exception):
        code = "dispatch_changed"
        command_attempted = False

    async def cross_deadline(lease_s):
        clock.advance(1801)
        if adapter.before_on() is not True:
            raise ChangedBeforeWrite()
        raise AssertionError("Expired intent must not reach the physical contact")

    adapter.set_on = cross_deadline
    manager.runtime.sg_dispatch_allowed = lambda *, renewal=False: manager.manual_mode == "on"
    await tick(manager, surplus=0)
    assert not adapter.calls and not adapter.on
    assert not manager.owned and not manager.desired_on


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), True, {"unexpected": "mapping"}])
async def test_invalid_effective_control_config_cannot_crash_or_restore_manual_authority(invalid):
    manager, adapter, clock, _runtime = await manual_on()
    stored = manager.snapshot()
    settings = {**manager.settings, "expected_power_w": invalid}
    manager.update_config(settings)
    # Invalid source bytes remain a visible configuration problem, not a hash
    # exception that prevents the runtime reaching its safe release path.
    checkpoint = manager.snapshot()
    assert checkpoint["manual_control"] is None
    manager.runtime.entry.options["sg_boost"] = deepcopy(manager.settings)
    restored, _ = restored_manager(manager, adapter, clock, stored)
    await restored.start()
    await tick(restored, surplus=0)
    assert not restored.owned and not restored.desired_on


async def solar_tick(manager, clock, *, surplus=4000, **kwargs):
    return await tick(manager, surplus=surplus, solar_stamp=clock(),
                      grid_import_source="fictional-P1", **kwargs)


@pytest.mark.asyncio
async def test_short_measured_cloud_keeps_wallclock_start_but_cannot_start_during_dip():
    manager, adapter, clock, _runtime = fixture(start_delay_s=120)
    await solar_tick(manager, clock)
    clock.advance(60)
    await solar_tick(manager, clock)
    clock.advance(1)
    await solar_tick(manager, clock, surplus=0)
    for _ in range(3):
        clock.advance(60)
        await solar_tick(manager, clock, surplus=0)
        assert not adapter.calls
    await solar_tick(manager, clock, surplus=4000)
    assert adapter.calls == [("on", 300)]
    assert manager.owned


@pytest.mark.asyncio
async def test_short_missing_measurement_keeps_clock_without_treating_missing_as_zero_or_on_proof():
    manager, adapter, clock, _runtime = fixture(start_delay_s=120)
    await solar_tick(manager, clock)
    clock.advance(61)
    await manager.tick(surplus_w=None, grid_import_w=None, data_fresh=False,
                       phase_allowed=True, priority_allowed=True)
    clock.advance(180)
    await manager.tick(surplus_w=None, grid_import_w=None, data_fresh=False,
                       phase_allowed=True, priority_allowed=True)
    assert not adapter.calls
    await solar_tick(manager, clock)
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["measured_dip", "missing"])
async def test_repeated_gap_reports_do_not_repurchase_five_minutes_of_start_grace(kind):
    manager, adapter, clock, _runtime = fixture(start_delay_s=120)
    await solar_tick(manager, clock)
    clock.advance(61)
    for index in range(6):
        if index:
            clock.advance(60)
        if kind == "measured_dip":
            await solar_tick(manager, clock, surplus=0)
        else:
            await manager.tick(surplus_w=None, grid_import_w=None, data_fresh=False,
                               phase_allowed=True, priority_allowed=True)
        assert not adapter.calls
    clock.advance(1)
    await solar_tick(manager, clock)
    assert not adapter.calls
    clock.advance(119)
    await solar_tick(manager, clock)
    assert not adapter.calls
    clock.advance(1)
    await solar_tick(manager, clock)
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_known_hard_block_during_measurement_gap_discards_original_start_qualification():
    manager, adapter, clock, _runtime = fixture(start_delay_s=120)
    await solar_tick(manager, clock)
    clock.advance(61)
    await manager.tick(surplus_w=None, grid_import_w=None, data_fresh=False,
                       phase_allowed=False, hard_limit=True)
    clock.advance(180)
    await solar_tick(manager, clock)
    assert not adapter.calls
    clock.advance(120)
    await solar_tick(manager, clock)
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_persisted_off_window_does_not_block_reused_entity_with_other_registered_contact():
    manager, adapter, clock, _runtime = fixture()
    native_status = adapter.status
    binding = ["fictional-off-contact-A"]
    adapter.status = lambda: {**native_status(), "binding_identity": binding[0]}
    await manager.start()
    await manager.set_manual_control("off", 1800)
    stored = manager.snapshot()
    clock.advance(5)
    binding[0] = "fictional-off-contact-B"
    restored, _ = restored_manager(manager, adapter, clock, stored)
    await restored.start()
    await solar_tick(restored, clock)
    assert restored.manual_mode == "auto"
    assert restored.overview()["manual_control"]["active"] is False
    assert not adapter.calls


@pytest.mark.asyncio
async def test_valid_restart_lease_waits_through_short_missing_sources_without_renewal_or_off_pulse():
    from test_sg_controller62 import boosted
    manager, adapter, clock, _runtime = await boosted(start_delay_s=30)
    stored = manager.snapshot()
    clock.advance(5)
    restored, _ = restored_manager(manager, adapter, clock, stored)
    before = list(adapter.calls)
    await restored.start()
    await restored.tick(surplus_w=None, grid_import_w=None, data_fresh=False,
                        phase_allowed=False, hard_limit=True,
                        start_wait_source_gap=True, start_known_hard_limit=False)
    assert adapter.on
    assert adapter.calls == before
    assert not restored.owned and not restored.desired_on
    assert restored._restart_resume is not None
    clock.advance(20)
    await solar_tick(restored, clock)
    assert restored.owned and restored.desired_on
    assert adapter.on and adapter.calls == before
    assert restored._session_started == manager._session_started


@pytest.mark.asyncio
async def test_known_hard_violation_during_restart_source_wait_still_releases_owned_contact():
    from test_sg_controller62 import boosted
    manager, adapter, clock, _runtime = await boosted(start_delay_s=30)
    stored = manager.snapshot()
    clock.advance(5)
    restored, _ = restored_manager(manager, adapter, clock, stored)
    await restored.start()
    await restored.tick(surplus_w=None, grid_import_w=None, data_fresh=False,
                        phase_allowed=False, hard_limit=True,
                        start_wait_source_gap=False, start_known_hard_limit=True)
    assert not adapter.on and adapter.calls[-1] == ("off", None)
    assert not restored.owned and not restored.desired_on


@pytest.mark.asyncio
async def test_unobserved_gap_longer_than_five_minutes_cannot_complete_start_with_two_samples():
    manager, adapter, clock, _runtime = fixture(start_delay_s=120)
    await solar_tick(manager, clock)
    clock.advance(301)
    await solar_tick(manager, clock)
    assert not adapter.calls
    clock.advance(119)
    await solar_tick(manager, clock)
    assert not adapter.calls
    clock.advance(1)
    await solar_tick(manager, clock)
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_manual_expiry_never_restarts_original_continuous_soft_import_grace():
    manager, adapter, clock, _runtime = await manual_on(duration=1800)
    start = clock()
    while clock() < start + 1500:
        clock.advance(60)
        await tick(manager, surplus=0, imported=0)
    await tick(manager, surplus=0, imported=1000, grid_import_source="fictional-continuous-P1")
    imported_since = manager._import_since
    for _ in range(5):
        clock.advance(60)
        await tick(manager, surplus=0, imported=1000, grid_import_source="fictional-continuous-P1")
    assert manager.manual_mode == "auto"
    assert imported_since == start + 1500
    assert not manager.owned and not manager.desired_on
    assert not adapter.on
    assert adapter.calls[-1][0] == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize("boundary", ["ownership_save", "transport_preflight"])
@pytest.mark.parametrize("kind", ["cloud", "measurement_gap", None])
async def test_post_await_soft_rejection_keeps_clock_only_with_current_typed_deferral(boundary, kind):
    manager, adapter, clock, runtime = fixture(start_delay_s=30)
    await solar_tick(manager, clock)
    qualified_since = manager._stable_since
    allowed = [True]
    runtime.sg_dispatch_allowed = lambda *, renewal=False: allowed[0]
    runtime.sg_start_wait_kind = lambda: kind
    original_save, original_on = runtime.store.async_save, adapter.set_on

    class ChangedBeforeWrite(Exception):
        code = "dispatch_changed"
        command_attempted = False

    if boundary == "ownership_save":
        async def changed_during_save(data):
            await original_save(data)
            if data["sg_boost"]["owned"]:
                allowed[0] = False
        runtime.store.async_save = changed_during_save
    else:
        adapter.before_on = None
        async def changed_during_preflight(lease_s):
            allowed[0] = False
            if adapter.before_on() is not True:
                raise ChangedBeforeWrite()
            raise AssertionError("Changed source/guard may not reach ON")
        adapter.set_on = changed_during_preflight
    clock.advance(30)
    await solar_tick(manager, clock)
    assert not adapter.calls and not adapter.on
    assert not manager.owned and not manager.desired_on
    assert manager._stable_since == (qualified_since if kind is not None else None)
    runtime.store.async_save = original_save
    adapter.set_on = original_on
    if boundary == "transport_preflight":
        del adapter.before_on  # Restore this fixture's no-callback protocol.
    allowed[0] = True
    clock.advance(10)
    await solar_tick(manager, clock)
    if kind is not None:
        assert adapter.calls == [("on", 300)]
    else:
        assert not adapter.calls
        clock.advance(30)
        await solar_tick(manager, clock)
        assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_same_bounded_intent_cannot_reset_hard_maximum_on_repeated_restart_after_lease_expiry():
    manager, adapter, clock, _runtime = await manual_on(duration=3600, max_session_s=300)
    stored = manager.snapshot()
    calls = list(adapter.calls)
    clock.advance(281)
    assert not adapter.status()["output"]
    first, _ = restored_manager(manager, adapter, clock, stored)
    await first.start()
    await solar_tick(first, clock, surplus=0)
    assert adapter.calls == calls
    clock.advance(20)
    second, _ = restored_manager(first, adapter, clock, first.snapshot())
    await second.start()
    await solar_tick(second, clock, surplus=0)
    assert adapter.calls == calls
    assert not second.owned and not second.desired_on and not adapter.on


@pytest.mark.asyncio
@pytest.mark.parametrize("damaged_origin", [None, True, float("nan"), "invalid"])
async def test_damaged_manual_origin_cannot_reset_valid_checkpoint_hard_ceiling(damaged_origin):
    manager, adapter, clock, _runtime = await manual_on(duration=3600, max_session_s=300)
    stored = manager.snapshot()
    stored["manual_control"]["session_started_at"] = damaged_origin
    calls = list(adapter.calls)
    clock.advance(281)
    assert not adapter.status()["output"]
    restored, _ = restored_manager(manager, adapter, clock, stored)
    await restored.start()
    await solar_tick(restored, clock, surplus=0)
    assert adapter.calls == calls
    assert not restored.owned and not restored.desired_on and not adapter.on
