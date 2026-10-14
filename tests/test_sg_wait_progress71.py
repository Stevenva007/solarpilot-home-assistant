"""Read-only SG evidence countdowns; fictional observations and local leases."""
from copy import deepcopy

import pytest

from test_general_sg_policy64 import ended, general_fixture, observe


async def solar_candidate():
    manager, adapter, clock, runtime, row = await ended()
    clock.advance(900)
    await observe(manager, clock, row, surplus=0)
    clock.advance(300)
    await observe(manager, clock, row, surplus=0)
    assert manager._general_reference["solar_reset_stamp"] == clock()
    clock.advance(1)
    await observe(manager, clock, row)
    return manager, adapter, clock, runtime, row


@pytest.mark.asyncio
async def test_new_solar_confirmation_then_start_delay_remains_read_only():
    manager, adapter, clock, runtime, row = await solar_candidate()
    progress = manager.overview()
    assert progress["reassessment_state"] == "confirming_new_solar_period"
    assert progress["reassessment_kind"] == "new_solar_period"
    assert progress["reassessment_remaining_s"] == progress["reassessment_required_s"] == 300
    assert progress["reassessment_reports"] == 1
    assert progress["reassessment_source_current"]
    assert progress["reassessment_valid_until"] == clock() + 120
    assert progress["start_remaining_s"] is None
    clock.advance(270)
    await observe(manager, clock, row)
    clock.advance(29.2)
    assert manager.overview()["reassessment_remaining_s"] == 1
    clock.advance(.8)
    before = deepcopy((manager._general_reference, manager._general_candidate, manager._general_reset_candidate))
    saves, reads, calls = len(runtime.store.saves), adapter.reads, list(adapter.calls)
    for _ in range(3):
        progress = manager.overview()
        assert progress["reassessment_remaining_s"] == 0
        assert progress["reassessment_final_report_required"]
        assert progress["reassessment_reports"] == 2
        assert manager.completion_hold and not manager.owned
    assert before == (manager._general_reference, manager._general_candidate, manager._general_reset_candidate)
    assert (len(runtime.store.saves), adapter.reads, adapter.calls) == (saves, reads, calls)
    # The actual new report, not overview or elapsed time, clears the hold.
    await observe(manager, clock, row)
    progress = manager.overview()
    assert not manager.completion_hold and not manager.owned
    assert progress["reassessment_state"] is None
    assert progress["start_remaining_s"] == 120
    assert progress["start_required_s"] == 120
    assert progress["start_valid_until"] == clock() + 120
    clock.advance(119.2)
    assert manager.overview()["start_remaining_s"] == 1
    clock.advance(.8)
    assert manager.overview()["start_remaining_s"] == 0
    assert adapter.calls == [("on", 300), ("off", None)]
    await observe(manager, clock, row)
    assert adapter.calls == [("on", 300), ("off", None), ("on", 300)]
    assert manager.overview()["start_remaining_s"] is None


@pytest.mark.asyncio
async def test_stale_candidate_hides_countdown_without_clearing_stored_evidence():
    manager, adapter, clock, runtime, _ = await solar_candidate()
    candidate = deepcopy(manager._general_candidate)
    saves, reads = len(runtime.store.saves), adapter.reads
    clock.advance(121)
    progress = manager.overview()
    assert progress["reassessment_state"] == "waiting_new_evidence"
    assert progress["reassessment_kind"] is None
    assert progress["reassessment_remaining_s"] is None
    assert progress["reassessment_valid_until"] is None
    assert not progress["reassessment_source_current"]
    assert not progress["reassessment_final_report_required"]
    assert manager._general_candidate == candidate
    assert (len(runtime.store.saves), adapter.reads) == (saves, reads)


@pytest.mark.asyncio
async def test_fresh_but_unqualified_observation_cannot_keep_old_candidate_countdown():
    manager, _, _, _, _ = await solar_candidate()
    manager._solar_observation["watts"] = 1000
    progress = manager.overview()
    assert progress["reassessment_state"] == "waiting_new_evidence"
    assert progress["reassessment_remaining_s"] is None
    assert progress["reassessment_source_current"]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["solar", "native"])
async def test_reset_confirmation_is_separate_from_confirming_new_episode(kind):
    manager, adapter, clock, _, row = await ended()
    clock.advance(1)
    if kind == "native":
        row.update(context="normal", context_signature="off:idle")
    await observe(manager, clock, row, surplus=0 if kind == "solar" else 4000)
    progress = manager.overview()
    assert progress["reassessment_state"] == "confirming_" + kind + "_reset"
    assert progress["reassessment_kind"] == kind + "_reset"
    assert progress["reassessment_remaining_s"] == 300
    assert progress["reassessment_reports"] == 1
    assert progress["start_remaining_s"] is None
    clock.advance(300)
    await observe(manager, clock, row, surplus=0 if kind == "solar" else 4000)
    assert manager._general_reference[kind + "_reset_stamp"] == clock()
    assert manager.overview()["reassessment_state"] == "waiting_new_evidence"
    assert manager.completion_hold and adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_changed_native_context_countdown_requires_same_current_signature():
    manager, _, clock, _, row = await ended()
    clock.advance(900)
    row["context_signature"] = "heat:heating"
    await observe(manager, clock, row)
    progress = manager.overview()
    assert progress["reassessment_kind"] == "fresh_native_context"
    assert progress["reassessment_remaining_s"] == 300
    assert progress["reassessment_source_current"]
    # A read does not transform an old candidate into a changed signature.
    manager._native_observation["context_signature"] = "heat:different"
    progress = manager.overview()
    assert progress["reassessment_state"] == "waiting_new_evidence"
    assert progress["reassessment_remaining_s"] is None
    assert "signature" not in progress


@pytest.mark.asyncio
@pytest.mark.parametrize("condition", ["low_solar", "phase_blocked", "priority_blocked", "stale", "manual", "closed", "observe"])
async def test_ordinary_start_countdown_only_describes_current_valid_start_window(condition):
    manager, adapter, clock, runtime, row = general_fixture()
    await observe(manager, clock, row)
    assert manager.overview()["start_remaining_s"] == 120
    if condition == "low_solar":
        await observe(manager, clock, row, surplus=100)
    elif condition == "phase_blocked":
        await manager.tick(surplus_w=4000, data_fresh=True, phase_allowed=False,
                           native_observation=row, solar_stamp=clock())
    elif condition == "priority_blocked":
        await observe(manager, clock, row, priority_allowed=False)
    elif condition == "stale":
        clock.advance(121)
    elif condition == "manual":
        manager.manual_hold = True
    elif condition == "closed":
        manager._closed = True
    else:
        runtime.mode = "observe"
    progress = manager.overview()
    if condition == "low_solar":
        assert progress["start_remaining_s"] == 120
        assert progress["start_cloud_active"] is True
        assert progress["start_cloud_kind"] == "cloud"
        assert progress["start_cloud_remaining_s"] == 300
    else:
        assert progress["start_remaining_s"] is None
    assert not adapter.calls


@pytest.mark.asyncio
async def test_dhw_hold_and_fresh_manager_do_not_advertise_general_reassessment():
    manager, _, clock, _, row = general_fixture()
    assert manager.overview()["reassessment_required_s"] is None
    manager.completion_hold = True
    manager.settings["profile"] = "dhw_only"
    await observe(manager, clock, row)
    progress = manager.overview()
    assert progress["reassessment_state"] is None
    assert progress["reassessment_required_s"] is None
    assert progress["start_remaining_s"] is None


@pytest.mark.asyncio
async def test_valid_until_tracks_original_report_instead_of_fresh_overview_time():
    manager, _, clock, _, _ = await solar_candidate()
    actual_stamp = manager._solar_observation["stamp"]
    clock.advance(90)
    progress = manager.overview()
    assert progress["observed_at"] == clock()
    assert progress["reassessment_valid_until"] == actual_stamp + 120
    assert progress["reassessment_valid_until"] - progress["observed_at"] == 30
    clock.advance(30)
    assert manager.overview()["reassessment_remaining_s"] == 180  # stale_s is inclusive.
    clock.advance(.01)
    assert manager.overview()["reassessment_remaining_s"] is None


@pytest.mark.asyncio
async def test_future_solar_stamp_outside_existing_clock_skew_is_not_current_progress():
    manager, _, clock, _, _ = await solar_candidate()
    manager._solar_observation["stamp"] = clock() + 5
    assert manager.overview()["reassessment_remaining_s"] == 300
    manager._solar_observation["stamp"] = clock() + 5.01
    progress = manager.overview()
    assert progress["reassessment_remaining_s"] is None
    assert progress["reassessment_valid_until"] is None


@pytest.mark.asyncio
async def test_start_validity_respects_earlier_native_cooling_guard_report_expiry():
    manager, _, clock, _, row = general_fixture(start_delay_s=75)
    row["context_stamp"] = clock() - 90
    await observe(manager, clock, row, refresh=False)
    progress = manager.overview()
    assert progress["start_remaining_s"] == progress["start_required_s"] == 75
    assert progress["start_valid_until"] == clock() + 30
    clock.advance(30.01)
    assert manager.overview()["start_remaining_s"] is None
