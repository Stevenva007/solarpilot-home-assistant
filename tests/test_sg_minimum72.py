"""Minimum duration for an extra SG request, never compressor authority."""
from copy import deepcopy

import pytest

from test_sg_controller62 import boosted, fixture, tick


async def advance(manager, clock, seconds, *, imported=1000):
    for _ in range(int(seconds // 60)):
        clock.advance(60)
        await tick(manager, surplus=0, imported=imported)
    if seconds % 60:
        clock.advance(seconds % 60)
        await tick(manager, surplus=0, imported=imported)


@pytest.mark.asyncio
async def test_default_minimum_bridges_soft_import_with_short_renewed_leases_until_twenty_minutes():
    manager, adapter, clock, _ = await boosted()
    assert manager.settings["min_session_s"] == 1200
    minimum_start = clock()
    await tick(manager, surplus=0, imported=1000)
    await advance(manager, clock, 1140)
    assert manager.owned and adapter.on and manager.minimum_hold_active
    assert manager._minimum_started == minimum_start  # Renewals never reset it.
    assert len(adapter.calls) == 20
    assert all(call == ("on", 300) for call in adapter.calls)
    row = manager.overview()
    assert row["minimum_remaining_s"] == 60 and row["minimum_import_hold"]
    assert row["min_session_s"] == row["effective_min_session_s"] == 1200
    assert not row["minimum_limited_by_max"]
    assert "Minimumduur SG-aanvraag" in row["reason"]
    clock.advance(60)
    await tick(manager, surplus=0, imported=1000)
    assert not manager.owned and not adapter.on
    assert adapter.calls[-1] == ("off", None)
    assert manager._last_session["duration_s"] == 1200
    assert manager._last_session["reason"] == "Aanhoudende netafname; extra SG-aanvraag vrijgegeven"
    assert manager.overview()["minimum_remaining_s"] is None


@pytest.mark.asyncio
async def test_existing_sixty_second_import_window_is_not_restarted_at_minimum_end():
    manager, adapter, clock, _ = await boosted(min_session_s=1200, import_threshold_w=300, stop_delay_s=60)
    await advance(manager, clock, 1140, imported=0)
    clock.advance(50)
    await tick(manager, imported=1000)
    clock.advance(10)
    await tick(manager, imported=1000)
    assert manager.owned and not manager.minimum_hold_active
    calls = list(adapter.calls)
    assert manager.overview()["minimum_remaining_s"] == 0
    clock.advance(49)
    await tick(manager, imported=1000)
    assert manager.owned and adapter.calls == calls  # The last renewal remains bounded during grace.
    clock.advance(1)
    await tick(manager, imported=1000)
    assert adapter.calls == calls + [("off", None)]


@pytest.mark.asyncio
async def test_import_recovery_resets_continuous_stop_evidence_during_minimum():
    manager, adapter, clock, _ = await boosted(min_session_s=180, import_threshold_w=300, stop_delay_s=60)
    await tick(manager, imported=1000)
    await advance(manager, clock, 120)
    assert manager.owned
    await tick(manager, imported=300)  # Exact legacy import boundary is recovery.
    assert manager._import_since is None
    clock.advance(60)
    await tick(manager, imported=1000)
    assert manager.owned and not manager.minimum_hold_active
    clock.advance(60)
    await tick(manager, imported=1000)
    assert adapter.calls[-1] == ("off", None) and not manager.owned


@pytest.mark.asyncio
async def test_explicit_zero_keeps_original_soft_import_stop():
    manager, adapter, clock, _ = await boosted(min_session_s=0, import_threshold_w=300, stop_delay_s=60)
    assert not manager.minimum_hold_active
    await tick(manager, imported=1000)
    clock.advance(60)
    await tick(manager, imported=1000)
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["data", "phase", "priority", "hard_limit", "native_completed", "no_uptake", "fault", "manual", "paused", "observe", "disabled", "close"])
async def test_minimum_never_delays_existing_early_release_guards(guard):
    manager, adapter, clock, runtime = await boosted()
    assert manager.minimum_hold_active
    clock.advance(1)
    kwargs = {}
    if guard == "data":
        await manager.tick(surplus_w=0, data_fresh=False, phase_allowed=True, grid_import_w=1000)
    elif guard == "phase":
        await manager.tick(surplus_w=0, data_fresh=True, phase_allowed=False, grid_import_w=1000)
    elif guard in {"priority", "hard_limit"}:
        kwargs["priority_allowed" if guard == "priority" else "hard_limit"] = guard != "priority"
        await tick(manager, imported=1000, **kwargs)
    elif guard in {"native_completed", "no_uptake"}:
        await tick(manager, imported=1000, physical_evidence={"verified": True,
                   "completed" if guard == "native_completed" else "no_uptake": True})
    elif guard == "fault":
        manager._fault("fixture_fault", "Fictional actuator fault")
        await tick(manager, imported=1000)
    elif guard == "manual":
        manager.manual_hold = True
        await tick(manager, imported=1000)
    elif guard in {"paused", "observe"}:
        runtime.mode = guard
        await tick(manager, imported=1000)
    elif guard == "disabled":
        await manager.set_enabled(False)
    else:
        await manager.close()
    assert adapter.calls == [("on", 300), ("off", None)]
    assert not manager.owned and not manager.minimum_hold_active
    assert manager._minimum_started is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timer_frozen", "offline"])
async def test_minimum_cannot_replace_a_missing_or_unconfirmed_renewal_proof(failure):
    manager, adapter, clock, _ = await boosted()
    if failure == "timer_frozen":
        adapter.timer_frozen = True
    else:
        adapter.online = False
    clock.advance(60)
    await tick(manager, imported=1000)
    assert not manager.desired_on and not manager.minimum_hold_active
    assert manager.fault
    # Local expiry remains bounded even when OFF cannot be confirmed.
    clock.advance(300)
    assert adapter.status()["output"] is False


@pytest.mark.asyncio
async def test_read_only_minimum_countdown_expires_at_original_contact_proof_without_side_effects():
    manager, adapter, clock, runtime = await boosted()
    start = clock()
    snapshot = deepcopy(manager.snapshot())
    calls, reads, saves = list(adapter.calls), adapter.reads, len(runtime.store.saves)
    clock.advance(90)
    for _ in range(3):
        row = manager.overview()
        assert row["minimum_remaining_s"] == 1110
        assert row["minimum_valid_until"] == start + 120
        assert row["observed_at"] == start + 90
        assert row["minimum_active"]
    assert manager.snapshot() == snapshot
    assert (adapter.calls, adapter.reads, len(runtime.store.saves)) == (calls, reads, saves)
    clock.advance(30.01)
    row = manager.overview()
    assert row["minimum_remaining_s"] is None and row["minimum_valid_until"] is None
    assert not row["minimum_active"]


@pytest.mark.asyncio
async def test_before_confirmed_on_no_minimum_counter_or_import_authority_exists():
    manager, adapter, _, _ = fixture()
    await tick(manager)
    row = manager.overview()
    assert row["min_session_s"] == row["effective_min_session_s"] == 1200
    assert row["minimum_remaining_s"] is None and row["minimum_valid_until"] is None
    assert not row["minimum_active"] and not row["minimum_import_hold"]
    assert not adapter.calls


@pytest.mark.asyncio
async def test_lower_existing_maximum_is_preserved_and_reported_as_minimum_limit():
    manager, _, _, _ = await boosted(min_session_s=1200, max_session_s=600)
    row = manager.overview()
    assert manager.settings["max_session_s"] == 600
    assert row["min_session_s"] == 1200 and row["effective_min_session_s"] == 600
    assert row["minimum_remaining_s"] == 600 and row["minimum_limited_by_max"]
