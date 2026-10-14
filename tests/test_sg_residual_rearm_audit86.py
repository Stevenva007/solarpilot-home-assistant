"""Independent conservative residual rearm probes with fictional SG sources."""
from copy import deepcopy, copy

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from test_general_sg_policy64 import started
from test_sg_controller62 import Store, tick
from test_sg_budget_priority62 import configured

SOURCE_IDENTITY = (("fictional-P1", "import-positive", "fictional-PV"), ("phase-a", "phase-b", "phase-c"))


async def unknown_hold(*, reason="response_unknown", cooling=True, **settings):
    manager, adapter, clock, runtime, row = await started(
        expected_power_w=3200, threshold_w=3000,
        cooling_protection_confirmed=cooling, **settings)
    row.update(context="heatpump_unknown", context_reliable=False, context_stamp=None,
               context_signature=None, cooling_possible=True,
               power_w=None, power_kind="unknown", power_stamp=None,
               compressor_running=None, compressor_frequency_hz=None)
    await manager._release("Fictional interrupted request")
    assert manager.completion_hold and manager._hold_reason == "response_unknown"
    manager._hold_reason = reason
    return manager, adapter, clock, runtime, row


async def observe_residual(manager, clock, row, *, residual=4000, eligible=None,
                           stamp=None, identity=SOURCE_IDENTITY, **kwargs):
    return await tick(manager, surplus=residual if eligible is None else eligible,
                      real_surplus_w=residual, solar_stamp=clock() if stamp is None else stamp,
                      native_observation=deepcopy(row), start_source_identity=identity, **kwargs)


async def begin_after_rest(manager, clock, row, **kwargs):
    clock.advance(max(0, manager._rest_until-clock()))
    await observe_residual(manager, clock, row, **kwargs)


async def fresh_for(manager, clock, row, seconds, **kwargs):
    for _ in range(seconds // 60):
        clock.advance(60)
        await observe_residual(manager, clock, row, **kwargs)


@pytest.mark.asyncio
async def test_unknown_response_rearms_without_hp_power_or_native_task_then_uses_normal_start_delay():
    manager, adapter, clock, _runtime, row = await unknown_hold()
    calls = list(adapter.calls)
    await begin_after_rest(manager, clock, row)
    await fresh_for(manager, clock, row, 240)
    assert manager.completion_hold and not manager.owned
    await fresh_for(manager, clock, row, 60)
    assert not manager.completion_hold and not manager.owned
    assert manager._last_rearm["kind"] == "fresh_residual_surplus"
    assert manager.overview()["start_remaining_s"] == manager.settings["start_delay_s"]
    assert adapter.calls == calls
    await fresh_for(manager, clock, row, 120)
    assert manager.owned and manager.desired_on
    assert adapter.calls == calls + [("on", 300)]
    assert row["power_w"] is None and row["context_reliable"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("residual,eligible", [(0, 8000), (2999, 8000), (3000, 8000), (3199, 8000)])
async def test_hp_credit_or_start_threshold_alone_cannot_buy_the_full_estimated_new_request(residual, eligible):
    manager, adapter, clock, _runtime, row = await unknown_hold()
    calls = list(adapter.calls)
    await begin_after_rest(manager, clock, row, residual=residual, eligible=eligible)
    await fresh_for(manager, clock, row, 360, residual=residual, eligible=eligible)
    assert manager.completion_hold and not manager.owned
    assert adapter.calls == calls
    assert manager.overview()["residual_reassessment_threshold_w"] == 3200


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["no_uptake", "native_completed", "session_limit", "profile_changed"])
async def test_confirmed_or_bounded_completion_holds_are_not_cleared_by_same_sun_lane(reason):
    manager, adapter, clock, _runtime, row = await unknown_hold(reason=reason)
    calls = list(adapter.calls)
    await begin_after_rest(manager, clock, row)
    await fresh_for(manager, clock, row, 600)
    assert manager.completion_hold and manager._hold_reason == reason
    assert adapter.calls == calls


@pytest.mark.asyncio
async def test_five_minute_confirmation_starts_after_rest_and_never_runs_inside_rest():
    manager, adapter, clock, _runtime, row = await unknown_hold()
    calls = list(adapter.calls)
    await fresh_for(manager, clock, row, 840)
    assert manager.completion_hold and manager._general_candidate is None
    await fresh_for(manager, clock, row, 60)
    assert manager.completion_hold
    await fresh_for(manager, clock, row, 240)
    assert manager.completion_hold
    await fresh_for(manager, clock, row, 60)
    assert not manager.completion_hold and not manager.owned
    assert adapter.calls == calls


@pytest.mark.asyncio
async def test_elapsed_clock_with_repeated_final_report_cannot_clear_unknown_hold():
    manager, adapter, clock, _runtime, row = await unknown_hold()
    await begin_after_rest(manager, clock, row)
    await fresh_for(manager, clock, row, 240)
    final_old_stamp = clock()
    clock.advance(60)
    await observe_residual(manager, clock, row, stamp=final_old_stamp)
    assert manager.completion_hold and not manager.owned
    calls = list(adapter.calls)
    clock.advance(5)
    await observe_residual(manager, clock, row)
    assert not manager.completion_hold and adapter.calls == calls


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_stamp", [0, True, float("nan"), float("inf"), "invalid", "future", "stale"])
async def test_invalid_or_unusable_original_solar_report_never_qualifies_rearm(bad_stamp):
    manager, adapter, clock, _runtime, row = await unknown_hold()
    calls = list(adapter.calls)
    clock.advance(manager.settings["rest_s"])
    for _ in range(7):
        stamp = clock()+6 if bad_stamp == "future" else clock()-121 if bad_stamp == "stale" else bad_stamp
        await observe_residual(manager, clock, row, stamp=stamp)
        clock.advance(60)
    assert manager.completion_hold and not manager.owned
    assert adapter.calls == calls


@pytest.mark.asyncio
async def test_prior_solar_proof_expired_before_new_final_report_restarts_confirmation():
    manager, adapter, clock, _runtime, row = await unknown_hold()
    calls = list(adapter.calls)
    await begin_after_rest(manager, clock, row)
    clock.advance(301)
    await observe_residual(manager, clock, row)
    assert manager.completion_hold and not manager.owned
    await fresh_for(manager, clock, row, 240)
    assert manager.completion_hold
    await fresh_for(manager, clock, row, 60)
    assert not manager.completion_hold and adapter.calls == calls


@pytest.mark.asyncio
async def test_missing_measurement_inside_confirmation_cannot_purchase_elapsed_qualification():
    manager, adapter, clock, _runtime, row = await unknown_hold()
    calls = list(adapter.calls)
    await begin_after_rest(manager, clock, row)
    await fresh_for(manager, clock, row, 120)
    clock.advance(60)
    await manager.tick(surplus_w=None, real_surplus_w=None, grid_import_w=None,
                       data_fresh=False, phase_allowed=True,
                       native_observation=deepcopy(row), start_source_identity=SOURCE_IDENTITY)
    clock.advance(60)
    await observe_residual(manager, clock, row)
    await fresh_for(manager, clock, row, 60)
    assert manager.completion_hold and not manager.owned
    await fresh_for(manager, clock, row, 240)
    assert not manager.completion_hold and adapter.calls == calls


@pytest.mark.asyncio
async def test_mutated_source_identity_does_not_reuse_or_mutate_prior_candidate():
    manager, adapter, clock, _runtime, row = await unknown_hold()
    identity = {"grid": "fictional-original", "pv": "fictional-PV"}
    await begin_after_rest(manager, clock, row, identity=identity)
    await fresh_for(manager, clock, row, 120, identity=identity)
    prior_candidate = deepcopy(manager._general_candidate)
    identity["grid"] = "fictional-replacement"
    clock.advance(60)
    await observe_residual(manager, clock, row, identity=identity)
    assert manager._general_candidate != prior_candidate
    await fresh_for(manager, clock, row, 120, identity=identity)
    assert manager.completion_hold and not manager.owned
    calls = list(adapter.calls)
    await fresh_for(manager, clock, row, 180, identity=identity)
    assert not manager.completion_hold and adapter.calls == calls


@pytest.mark.asyncio
async def test_partial_rearm_candidate_is_not_restored_or_credited_across_restart():
    manager, adapter, clock, runtime, row = await unknown_hold()
    await begin_after_rest(manager, clock, row)
    await fresh_for(manager, clock, row, 240)
    saved = manager.snapshot()
    other = copy(runtime)
    other.store = Store()
    restored = SGBoostManager(other, adapter=adapter, clock=clock)
    other.sg_boost = restored
    other._snapshot = lambda: {"sg_boost": restored.snapshot()}
    restored.restore(saved)
    assert restored.completion_hold and restored._general_candidate is None
    calls = list(adapter.calls)
    clock.advance(60)
    await observe_residual(restored, clock, row)
    assert restored.completion_hold
    await fresh_for(restored, clock, row, 240)
    assert restored.completion_hold
    await fresh_for(restored, clock, row, 60)
    assert not restored.completion_hold and adapter.calls == calls


@pytest.mark.asyncio
@pytest.mark.parametrize("block", ["phase", "priority", "hard_limit", "paused", "observe", "fault", "manual_hold", "cooling"])
async def test_essential_authority_and_known_hard_blocks_are_never_overridden_by_optional_meter_fallback(block):
    manager, adapter, clock, runtime, row = await unknown_hold()
    arguments = {}
    if block == "phase":
        arguments["phase_allowed"] = False
    elif block == "priority":
        arguments["priority_allowed"] = False
    elif block == "hard_limit":
        arguments["hard_limit"] = True
    elif block in ("paused", "observe"):
        runtime.mode = block
    elif block == "fault":
        manager._fault("on_failed", "Fictional uncertain command")
    elif block == "manual_hold":
        manager.manual_hold = True
    else:
        manager.settings["cooling_protection_confirmed"] = False
    clock.advance(manager.settings["rest_s"])
    calls = list(adapter.calls)
    for _ in range(7):
        if block == "phase":
            await manager.tick(surplus_w=4000, real_surplus_w=4000, grid_import_w=0,
                               grid_import_stamp=clock(), solar_stamp=clock(), data_fresh=True,
                               phase_allowed=False, native_observation=deepcopy(row),
                               start_source_identity=SOURCE_IDENTITY)
        else:
            await observe_residual(manager, clock, row, **arguments)
        clock.advance(60)
    assert manager.completion_hold and not manager.owned
    assert adapter.calls == calls


def test_actual_p1_budget_with_missing_hp_total_keeps_zero_credit_and_full_future_envelope():
    runtime, hass = configured(export=3350, reserve=150)
    runtime.panasonic.settings.update(power_entity="", power_supply1_entity="sensor.fictional_main_absent",
        power_supply2_entity="sensor.fictional_auxiliary", split_power_confirmed=True)
    hass.states.set("sensor.fictional_auxiliary", 0, {"unit_of_measurement": "W"})
    budget = sg_solar_budget(runtime)
    assert budget["valid"] and budget["available_w"] == budget["eligible_w"] == 3200
    assert budget["hp_power_w"] is None and budget["hp_solar_w"] == 0
    assert runtime.sg_dispatch_allowed()
    # Returning known watts may qualify existing HP-solar attribution only;
    # it cannot reduce the full projected future request at the physical gate.
    hass.states.set("sensor.fictional_main_absent", 4000, {"unit_of_measurement": "W"})
    recovered = sg_solar_budget(runtime)
    assert recovered["valid"] and recovered["hp_power_w"] == 4000
    assert recovered["available_w"] == 3200 and recovered["eligible_w"] > recovered["available_w"]
    hass.states.set("sensor.grid", -2699, {"unit_of_measurement": "W"})
    assert not runtime.sg_dispatch_allowed()


@pytest.mark.asyncio
async def test_restart_retains_only_remaining_rest_before_starting_new_residual_confirmation():
    manager, adapter, clock, runtime, row = await unknown_hold()
    released_at = clock()
    clock.advance(300)
    saved = manager.snapshot()
    other = copy(runtime)
    other.store = Store()
    restored = SGBoostManager(other, adapter=adapter, clock=clock)
    other.sg_boost = restored
    other._snapshot = lambda: {"sg_boost": restored.snapshot()}
    restored.restore(saved)
    assert restored._rest_until == released_at + manager.settings["rest_s"]
    calls = list(adapter.calls)
    await fresh_for(restored, clock, row, 540)
    assert restored.completion_hold and restored._general_candidate is None
    await fresh_for(restored, clock, row, 60)
    assert restored.completion_hold
    await fresh_for(restored, clock, row, 240)
    assert restored.completion_hold
    await fresh_for(restored, clock, row, 60)
    assert not restored.completion_hold and adapter.calls == calls


@pytest.mark.asyncio
async def test_changed_expected_request_policy_requires_its_own_full_residual_proof_window():
    manager, adapter, clock, _runtime, row = await unknown_hold()
    await begin_after_rest(manager, clock, row)
    await fresh_for(manager, clock, row, 120)
    manager.update_config({**manager.settings, "expected_power_w": 3500})
    clock.advance(60)
    await observe_residual(manager, clock, row)
    await fresh_for(manager, clock, row, 120)
    assert manager.completion_hold and not manager.owned
    calls = list(adapter.calls)
    await fresh_for(manager, clock, row, 180)
    assert not manager.completion_hold and adapter.calls == calls
    assert manager.overview()["residual_reassessment_threshold_w"] == 3500
