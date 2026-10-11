"""Completed-reset presentation preserves all existing SG report guards."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_general_sg_policy64 import ended, observe


async def confirmed_reset(kind):
    manager, adapter, clock, runtime, row = await ended()
    clock.advance(900)
    if kind == "native":
        row.update(context="normal", context_signature="off:idle")
    surplus = 0 if kind == "solar" else 4000
    await observe(manager, clock, row, surplus=surplus)
    assert manager.overview()["reassessment_kind"] == kind + "_reset"
    clock.advance(300)
    await observe(manager, clock, row, surplus=surplus)
    assert manager._general_reference[kind + "_reset_stamp"] == clock()
    return manager, adapter, clock, runtime, row, surplus


def assert_waiting_for_new_evidence(manager):
    progress = manager.overview()
    assert progress["reassessment_state"] == "waiting_new_evidence"
    assert progress["reassessment_kind"] is None
    assert progress["reassessment_remaining_s"] is None
    assert progress["reassessment_valid_until"] is None
    assert progress["reassessment_reports"] == 0
    assert not progress["reassessment_final_report_required"]
    assert manager.completion_hold and not manager.owned


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["solar", "native"])
async def test_completed_reset_does_not_display_another_wait_but_keeps_rolling_markers_and_saves(kind):
    manager, adapter, clock, runtime, row, surplus = await confirmed_reset(kind)
    first_marker = manager._general_reference[kind + "_reset_stamp"]
    first_saves = len(runtime.store.saves)
    calls = list(adapter.calls)
    clock.advance(5)
    await observe(manager, clock, row, surplus=surplus)
    assert manager._general_reset_candidate["kind"] == kind
    assert manager._general_reset_candidate["reports"] == 1
    assert_waiting_for_new_evidence(manager)
    # Read-only progress never latches/clears evidence, sends or saves.
    evidence = deepcopy((manager._general_reference, manager._general_reset_candidate))
    reads, saves = adapter.reads, len(runtime.store.saves)
    for _ in range(3):
        assert_waiting_for_new_evidence(manager)
    assert (manager._general_reference, manager._general_reset_candidate) == evidence
    assert (adapter.reads, len(runtime.store.saves), adapter.calls) == (reads, saves, calls)
    clock.advance(300)
    await observe(manager, clock, row, surplus=surplus)
    assert manager._general_reference[kind + "_reset_stamp"] == first_marker + 305
    assert len(runtime.store.saves) == first_saves + 1  # Existing control bookkeeping preserved.
    assert adapter.calls == calls
    clock.advance(5)
    await observe(manager, clock, row, surplus=surplus)
    assert_waiting_for_new_evidence(manager)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["solar", "native"])
async def test_first_reset_still_counts_down_and_needs_a_real_new_final_report(kind):
    manager, adapter, clock, _runtime, row = await ended()
    clock.advance(900)
    if kind == "native":
        row.update(context="normal", context_signature="off:idle")
    surplus = 0 if kind == "solar" else 4000
    stamp = clock()
    await observe(manager, clock, row, surplus=surplus, solar_stamp=stamp)
    assert manager.overview()["reassessment_remaining_s"] == 300
    clock.advance(270)
    await observe(manager, clock, row, surplus=surplus)
    clock.advance(30)
    progress = manager.overview()
    assert progress["reassessment_remaining_s"] == 0 and progress["reassessment_final_report_required"]
    assert manager._general_reference[kind + "_reset_stamp"] is None
    await observe(manager, clock, row, surplus=surplus, refresh=False, solar_stamp=stamp if kind == "solar" else True)
    # An old solar stamp or repeated native stamp supplies no final report.
    assert manager._general_reference[kind + "_reset_stamp"] is None
    assert manager.completion_hold and adapter.calls == [("on", 300), ("off", None)]
    await observe(manager, clock, row, surplus=surplus)
    # Missing/old solar proof clears its candidate; native repeated proof does
    # not. Either way no ON is authorized by confirming a reset itself.
    if kind == "solar":
        clock.advance(300)
        await observe(manager, clock, row, surplus=surplus)
    assert manager._general_reference[kind + "_reset_stamp"] == clock()
    assert_waiting_for_new_evidence(manager)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["solar", "native"])
async def test_new_active_episode_after_hidden_repeat_keeps_300_second_proof_and_120_second_start(kind):
    manager, adapter, clock, _runtime, row, surplus = await confirmed_reset(kind)
    clock.advance(5)
    await observe(manager, clock, row, surplus=surplus)
    assert_waiting_for_new_evidence(manager)
    if kind == "native":
        row.update(context="space_heating", context_signature="heat:idle")
    clock.advance(5)
    await observe(manager, clock, row, surplus=4000)
    expected = "new_solar_period" if kind == "solar" else "fresh_native_context"
    progress = manager.overview()
    assert progress["reassessment_kind"] == expected
    assert progress["reassessment_remaining_s"] == 300
    assert progress["reassessment_valid_until"] == clock() + 120
    clock.advance(270)
    await observe(manager, clock, row, surplus=4000)
    clock.advance(30)
    assert manager.overview()["reassessment_remaining_s"] == 0
    assert manager.completion_hold and not manager.owned
    await observe(manager, clock, row, surplus=4000)
    assert not manager.completion_hold and manager.overview()["start_remaining_s"] == 120
    clock.advance(120)
    await observe(manager, clock, row, surplus=4000)
    assert manager.owned and adapter.calls == [("on", 300), ("off", None), ("on", 300)]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["solar", "native"])
async def test_restore_keeps_completed_reset_and_never_restores_partial_candidate_or_on_authority(kind):
    previous, adapter, clock, runtime, row, surplus = await confirmed_reset(kind)
    clock.advance(5)
    await observe(previous, clock, row, surplus=surplus)
    assert previous._general_reset_candidate is not None
    saved = previous.snapshot()
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = manager
    manager.restore(saved)
    marker = manager._general_reference[kind + "_reset_stamp"]
    assert marker is not None and manager._general_reset_candidate is None
    assert manager._general_candidate is None and not manager.owned and not manager.desired_on
    await observe(manager, clock, row, surplus=surplus)
    assert manager._general_reset_candidate is not None
    assert_waiting_for_new_evidence(manager)
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_already_confirmed_low_solar_does_not_fall_through_to_normal_native_reset():
    manager, adapter, clock, _runtime, row, surplus = await confirmed_reset("solar")
    row.update(context="normal", context_signature="off:idle")
    clock.advance(5)
    await observe(manager, clock, row, surplus=surplus)
    assert manager._general_reset_candidate["kind"] == "solar"
    assert manager._general_reference["native_reset_stamp"] is None
    assert_waiting_for_new_evidence(manager)
    clock.advance(300)
    await observe(manager, clock, row, surplus=surplus)
    assert manager._general_reference["native_reset_stamp"] is None
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_new_completion_still_requires_its_own_first_reset():
    manager, adapter, clock, _runtime, row, _surplus = await confirmed_reset("solar")
    clock.advance(1)
    await observe(manager, clock, row)
    clock.advance(300)
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert manager.owned
    clock.advance(60)
    await observe(manager, clock, row, physical_evidence={"verified": True, "no_uptake": True})
    assert manager._general_reference["solar_reset_stamp"] is None
    clock.advance(1)
    await observe(manager, clock, row, surplus=0)
    assert manager.overview()["reassessment_kind"] == "solar_reset"
    assert manager.overview()["reassessment_remaining_s"] == 300
    assert adapter.calls == [("on", 300), ("off", None)] * 2


@pytest.mark.asyncio
async def test_native_reader_rebase_clears_its_confirmed_marker_and_requires_new_real_reset():
    manager, adapter, clock, _runtime, row, surplus = await confirmed_reset("native")
    manager.update_config({**manager.settings, "activity_entity": "sensor.fictional_new_activity"})
    assert manager._general_reference["native_reset_stamp"] is None
    assert manager._general_reference["native_rebase"]
    clock.advance(1)
    await observe(manager, clock, row, surplus=surplus)
    assert manager._general_reset_candidate is None  # Fresh new reader establishes baseline only.
    clock.advance(1)
    await observe(manager, clock, row, surplus=surplus)
    assert manager.overview()["reassessment_kind"] == "native_reset"
    assert manager.overview()["reassessment_remaining_s"] == 300
    assert adapter.calls == [("on", 300), ("off", None)]
