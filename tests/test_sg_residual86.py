"""Fresh residual solar retries unknown SG response without fictitious HP watts.

Sources and actuators are fictional. A permitted contact is no proof of extra
heat uptake, compressor operation or physical device commissioning.
"""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_general_sg_policy64 import observe, started
from test_sg_budget_priority62 import configured


async def unknown_hold(**settings):
    manager, adapter, clock, runtime, row = await started(**settings)
    await manager._release("Fictional routine policy withdrawal")
    assert manager.completion_hold and manager._hold_reason == "response_unknown"
    row.update(power_w=None, power_kind="unknown", power_stamp=None)
    clock.advance(manager.settings["rest_s"])
    return manager, adapter, clock, runtime, row


async def qualify(manager, clock, row, **kwargs):
    await observe(manager, clock, row, **kwargs)
    for _ in range(5):
        clock.advance(60)
        await observe(manager, clock, row, **kwargs)


@pytest.mark.asyncio
async def test_unknown_response_retries_from_real_residual_then_full_start_delay():
    manager, adapter, clock, runtime, row = await unknown_hold(expected_power_w=3200)
    await qualify(manager, clock, row, surplus=3200, real_surplus_w=3200)
    assert not manager.completion_hold and manager._last_rearm["kind"] == "fresh_residual_surplus"
    assert not manager.owned and adapter.calls == [("on", 300), ("off", None)]
    assert manager.overview()["start_remaining_s"] == manager.settings["start_delay_s"]
    assert row["power_w"] is None and row["power_kind"] == "unknown"
    clock.advance(manager.settings["start_delay_s"]-1)
    await observe(manager, clock, row, surplus=3200, real_surplus_w=3200)
    assert not manager.owned
    clock.advance(1)
    await observe(manager, clock, row, surplus=3200, real_surplus_w=3200)
    assert manager.owned and adapter.calls[-1] == ("on", 300)
    assert any("warmtepomprespons blijft onbekend" in message for message in runtime.notes)


@pytest.mark.asyncio
@pytest.mark.parametrize("optional_power", [None, -4580, float("nan"), 0, 2500])
async def test_optional_hp_power_neither_qualifies_nor_blocks_real_residual(optional_power):
    manager, adapter, clock, _runtime, row = await unknown_hold(expected_power_w=3200)
    row.update(power_w=optional_power, power_kind="measured" if optional_power is not None else "unknown")
    await qualify(manager, clock, row, surplus=3200, real_surplus_w=3200)
    assert not manager.completion_hold and manager._last_rearm["kind"] == "fresh_residual_surplus"
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("residual", [0, 2999, 3199, None, -1, True, float("nan")])
async def test_hp_credit_and_large_eligible_budget_do_not_replace_actual_residual(residual):
    manager, adapter, clock, _runtime, row = await unknown_hold(expected_power_w=3200)
    await qualify(manager, clock, row, surplus=9999, real_surplus_w=residual)
    assert manager.completion_hold and manager._general_candidate is None
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_expired_unobserved_interval_does_not_count_as_five_minutes_solar():
    manager, _adapter, clock, _runtime, row = await unknown_hold()
    await observe(manager, clock, row)
    first = manager._general_candidate["first_seen"]
    clock.advance(301)
    await observe(manager, clock, row)
    assert manager.completion_hold
    assert manager._general_candidate["first_seen"] > first
    assert manager._general_candidate["reports"] == 1


@pytest.mark.asyncio
async def test_progress_is_read_only_and_expires_with_original_residual_report():
    manager, adapter, clock, runtime, row = await unknown_hold()
    await observe(manager, clock, row, real_surplus_w=4000)
    before = deepcopy(manager._general_candidate)
    calls, reads, saves = list(adapter.calls), adapter.reads, len(runtime.store.saves)
    progress = manager.overview()
    assert progress["reassessment_kind"] == "fresh_residual_surplus"
    assert progress["reassessment_state"] == "confirming_fresh_residual_surplus"
    assert progress["reassessment_remaining_s"] == 300
    assert progress["real_residual_surplus_w"] == 4000
    assert progress["residual_reassessment_threshold_w"] == 3200
    clock.advance(121)
    progress = manager.overview()
    assert progress["reassessment_remaining_s"] is None
    assert progress["real_residual_surplus_w"] is None
    assert manager._general_candidate == before
    assert (adapter.calls, adapter.reads, len(runtime.store.saves)) == (calls, reads, saves)


@pytest.mark.asyncio
async def test_restart_preserves_hold_and_rest_but_requires_new_residual_window():
    manager, adapter, clock, runtime, row = await unknown_hold()
    await observe(manager, clock, row)
    clock.advance(60)
    await observe(manager, clock, row)
    saved = manager.snapshot()
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    runtime._snapshot = lambda: {"sg_boost": restored.snapshot()}
    restored.restore(saved)
    assert restored.completion_hold and restored._general_candidate is None
    await observe(restored, clock, row)
    assert restored._general_candidate["first_seen"] == clock()
    assert restored._general_candidate["reports"] == 1


@pytest.mark.asyncio
async def test_hard_guard_changing_during_final_ownership_save_still_prevents_on():
    manager, adapter, clock, runtime, row = await unknown_hold()
    await qualify(manager, clock, row)
    gate = [True]
    runtime.sg_dispatch_allowed = lambda *, renewal=False: gate[0]
    save = runtime.store.async_save

    async def live_limit_changes(data):
        await save(data)
        if manager._in_flight:
            gate[0] = False

    runtime.store.async_save = live_limit_changes
    clock.advance(manager.settings["start_delay_s"])
    await observe(manager, clock, row)
    assert not manager.owned and not manager.desired_on
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.parametrize("optional_power", ["unavailable", -4580, float("nan")])
def test_actual_p1_pv_budget_remains_valid_without_optional_hp_total(optional_power):
    runtime, hass = configured(export=3500)
    runtime.entry.runtime_data = runtime
    hass.states.set("sensor.public_hp", optional_power, {"unit_of_measurement": "W"})
    budget = sg_solar_budget(runtime)
    assert budget["valid"] and budget["available_w"] == 3350
    assert budget["hp_power_w"] == (0 if optional_power == -4580 else None)
    assert budget["hp_solar_w"] == 0
    assert budget["eligible_w"] == budget["available_w"]
    assert runtime.sg_dispatch_allowed() is True
    # No measured HP total does not shrink the extra 3200 W estimate.
    hass.states.set("sensor.grid", 0, {"unit_of_measurement": "W"})
    assert runtime.sg_dispatch_allowed(ignore_solar=True) is False
