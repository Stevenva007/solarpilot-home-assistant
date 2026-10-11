"""Independent reset presentation checks; fictional reports and local contact.

Rolling controller evidence remains unchanged. Repeated overviews must never
grant demand, rewrite a marker, save ownership, or touch the SG contact.
"""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_general_sg_policy64 import ended, observe


async def reset_confirmed(kind="solar"):
    manager, adapter, clock, runtime, row = await ended()
    clock.advance(1)
    if kind == "native":
        row.update(context="normal", context_signature="off:idle")
    surplus = 0 if kind == "solar" else 4000
    await observe(manager, clock, row, surplus=surplus)
    assert manager.overview()["reassessment_state"] == "confirming_" + kind + "_reset"
    clock.advance(300)
    await observe(manager, clock, row, surplus=surplus)
    assert manager._general_reference[kind + "_reset_stamp"] == clock()
    assert manager.completion_hold and not manager.owned
    return manager, adapter, clock, runtime, row


def proof(manager, adapter, runtime):
    return deepcopy((manager.snapshot(), manager._general_reference,
                     manager._general_candidate, manager._general_reset_candidate,
                     runtime.store.saves, adapter.calls, adapter.reads))


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["solar", "native"])
async def test_completed_reset_hides_repeated_countdown_but_preserves_rolling_controller(kind):
    manager, adapter, clock, runtime, row = await reset_confirmed(kind)
    first_marker = manager._general_reference[kind + "_reset_stamp"]
    initial_saves = len(runtime.store.saves)
    for _ in range(18):
        clock.advance(60)
        await observe(manager, clock, row, surplus=0 if kind == "solar" else 4000)
        before = proof(manager, adapter, runtime)
        for _ in range(3):
            progress = manager.overview()
            assert progress["reassessment_state"] == "waiting_new_evidence"
            assert progress["reassessment_kind"] is None
            assert progress["reassessment_remaining_s"] is None
            assert progress["reassessment_valid_until"] is None
            assert progress["reassessment_reports"] == 0
            assert not progress["reassessment_final_report_required"]
        assert proof(manager, adapter, runtime) == before
    # The release contract deliberately keeps controller checkpoints intact.
    assert manager._general_reference[kind + "_reset_stamp"] > first_marker
    assert len(runtime.store.saves) > initial_saves
    assert manager.completion_hold and not manager.owned
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_latest_rolling_reset_still_rejects_backdated_high_after_first_confirmed_reset():
    manager, adapter, clock, _runtime, row = await reset_confirmed()
    first_marker = manager._general_reference["solar_reset_stamp"]
    for _ in range(6):
        clock.advance(60)
        await observe(manager, clock, row, surplus=0)
    latest = manager._general_reference["solar_reset_stamp"]
    assert latest > first_marker
    clock.advance(10)
    backdated = latest - 50  # Fresh (<120s), but predates latest reset proof.
    assert backdated > first_marker
    await observe(manager, clock, row, surplus=4000, solar_stamp=backdated)
    assert manager._general_candidate is None
    assert manager.completion_hold and not manager.owned
    assert manager.overview()["reassessment_remaining_s"] is None
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_confirmed_low_solar_keeps_priority_without_creating_native_reset_fallback():
    manager, adapter, clock, runtime, row = await reset_confirmed()
    row.update(context="normal", context_signature="off:idle")
    for _ in range(6):
        clock.advance(60)
        await observe(manager, clock, row, surplus=0)
        candidate = manager._general_reset_candidate
        assert candidate is None or candidate["kind"] == "solar"
        assert manager._general_reference["native_reset_stamp"] is None
        before = proof(manager, adapter, runtime)
        assert manager.overview()["reassessment_state"] == "waiting_new_evidence"
        assert proof(manager, adapter, runtime) == before
    assert manager.completion_hold and adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["solar", "native"])
async def test_restored_confirmed_reset_stays_hidden_without_creating_on_or_overview_writes(kind):
    previous, adapter, clock, runtime, row = await reset_confirmed(kind)
    saved = previous.snapshot()
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = manager
    runtime._snapshot = lambda: {"sg_boost": manager.snapshot()}
    manager.restore(saved)
    await manager.start()
    marker = manager._general_reference[kind + "_reset_stamp"]
    clock.advance(1)
    await observe(manager, clock, row, surplus=0 if kind == "solar" else 4000)
    assert manager._general_reset_candidate["kind"] == kind
    before = proof(manager, adapter, runtime)
    assert manager.overview()["reassessment_state"] == "waiting_new_evidence"
    assert proof(manager, adapter, runtime) == before
    assert manager._general_reference[kind + "_reset_stamp"] == marker
    assert manager.completion_hold and not manager.owned
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_native_reader_rebase_invalidates_only_native_reset_and_requires_new_real_proof():
    manager, adapter, clock, runtime, row = await reset_confirmed("native")
    manager.update_config({**manager.settings, "zone_entities": ["climate.other_fixture_reader"]})
    assert manager._general_reference["native_reset_stamp"] is None
    clock.advance(1)
    row["context_signature"] = "new-reader:off:idle"
    await observe(manager, clock, row, surplus=4000)
    assert manager._general_reference["native_rebase"] is False
    assert manager._general_reset_candidate is None
    assert manager.overview()["reassessment_state"] == "waiting_new_evidence"
    clock.advance(1)
    await observe(manager, clock, row, surplus=4000)
    before = proof(manager, adapter, runtime)
    progress = manager.overview()
    assert progress["reassessment_state"] == "confirming_native_reset"
    assert progress["reassessment_remaining_s"] == 300
    assert proof(manager, adapter, runtime) == before
    assert manager.completion_hold and not manager.owned


@pytest.mark.asyncio
async def test_confirmed_reset_does_not_erase_rest_or_new_episode_and_start_guards():
    manager, adapter, clock, _runtime, row = await reset_confirmed()
    clock.advance(1)
    await observe(manager, clock, row)
    assert clock() < manager._rest_until
    assert manager._general_candidate is None
    assert manager.overview()["reassessment_state"] == "waiting_new_evidence"
    clock.advance(manager._rest_until - clock())
    await observe(manager, clock, row, hard_limit=True)
    assert manager.overview()["reassessment_state"] == "confirming_new_solar_period"
    clock.advance(300)
    await observe(manager, clock, row, hard_limit=True)
    assert not manager.completion_hold and not manager.owned
    assert manager._stable_since is None
    assert adapter.calls == [("on", 300), ("off", None)]
    clock.advance(1)
    await observe(manager, clock, row)
    assert manager.overview()["start_remaining_s"] == 120
    clock.advance(119)
    await observe(manager, clock, row)
    assert not manager.owned
    clock.advance(1)
    await observe(manager, clock, row)
    assert adapter.calls == [("on", 300), ("off", None), ("on", 300)]


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_marker", [None, True, "unavailable"])
async def test_invalid_reset_marker_cannot_hide_a_real_first_confirmation(invalid_marker):
    manager, _adapter, clock, _runtime, row = await ended()
    manager._general_reference["solar_reset_stamp"] = invalid_marker
    clock.advance(1)
    await observe(manager, clock, row, surplus=0)
    progress = manager.overview()
    assert progress["reassessment_state"] == "confirming_solar_reset"
    assert progress["reassessment_remaining_s"] == 300
    assert manager.completion_hold


@pytest.mark.asyncio
async def test_no_new_report_and_stale_sources_do_not_invent_a_confirmed_reset():
    manager, adapter, clock, runtime, row = await ended()
    clock.advance(1)
    original = clock()
    await observe(manager, clock, row, surplus=0)
    clock.advance(300)
    await observe(manager, clock, row, surplus=0, refresh=False, solar_stamp=original)
    assert manager._general_reference["solar_reset_stamp"] is None
    assert manager._general_reference["native_reset_stamp"] is None
    before = proof(manager, adapter, runtime)
    progress = manager.overview()
    assert progress["reassessment_state"] == "waiting_new_evidence"
    assert not progress["reassessment_source_current"]
    assert proof(manager, adapter, runtime) == before
    assert manager.completion_hold and adapter.calls == [("on", 300), ("off", None)]
