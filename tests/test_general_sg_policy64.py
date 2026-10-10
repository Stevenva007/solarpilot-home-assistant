"""General SG policy with fictional read-only native data and local leases."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_sg_controller62 import fixture, tick, tank_observation


def general_fixture(**config):
    manager, adapter, clock, runtime = fixture(profile="general", profile_confirmed=True, **config)
    row = {"context": "space_heating", "context_reliable": True,
           "context_signature": "heat:idle", "context_stamp": clock(),
           "cooling_possible": False, "compressor_running": False,
           "frequency_hz": 0, "power_w": 0, "power_kind": "measured",
           "power_stamp": clock(),
           "sg_status": "unknown", "sg_status_confirmed": False}
    runtime.panasonic.overview = lambda: deepcopy(row)
    return manager, adapter, clock, runtime, row


async def observe(manager, clock, row, *, surplus=4000, refresh=True, solar_stamp=True, **kwargs):
    if refresh:
        row["context_stamp"] = clock()
        row["power_stamp"] = clock()
    stamp = clock() if solar_stamp is True else None if solar_stamp is False else solar_stamp
    return await tick(manager, surplus=surplus, native_observation=deepcopy(row),
                      solar_stamp=stamp, **kwargs)


async def started(**config):
    manager, adapter, clock, runtime, row = general_fixture(**config)
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert manager.owned and adapter.calls == [("on", 300)]
    return manager, adapter, clock, runtime, row


async def ended(**config):
    manager, adapter, clock, runtime, row = await started(**config)
    clock.advance(60)
    await observe(manager, clock, row, physical_evidence={"verified": True, "no_uptake": True})
    assert manager.completion_hold and adapter.calls[-1] == ("off", None)
    return manager, adapter, clock, runtime, row


@pytest.mark.asyncio
async def test_general_stable_tank_and_new_native_context_reassesses_without_tank_decline():
    manager, adapter, clock, _, row = await ended(tank_temperature_entity="sensor.fictional_tank")
    manager._need_reference = {"schema": 1, "entity_id": "sensor.fictional_tank",
        "temperature_c": 60, "stamp": clock(), "ended_at": clock()}
    clock.advance(900)
    row["context_signature"] = "heat:heating"
    await observe(manager, clock, row, tank_observation=tank_observation(manager, clock, 60))
    clock.advance(300)
    await observe(manager, clock, row, tank_observation=tank_observation(manager, clock, 60))
    assert not manager.completion_hold and manager._last_rearm["kind"] == "fresh_native_context"
    assert not manager.owned
    clock.advance(120)
    await observe(manager, clock, row)
    assert adapter.calls == [("on", 300), ("off", None), ("on", 300)]


@pytest.mark.asyncio
async def test_constant_sun_same_native_reports_rest_reload_and_restart_ready_do_not_retrigger():
    previous, adapter, clock, runtime, row = await ended()
    saved = previous.snapshot()
    for _ in range(3):
        clock.advance(2000)
        await observe(previous, clock, row, physical_evidence={"verified": True, "restart_ready": True})
    assert previous.completion_hold and len(adapter.calls) == 2
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    manager.restore(saved)
    for _ in range(3):
        clock.advance(2000)
        await observe(manager, clock, row)
    assert manager.completion_hold and len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_new_solar_episode_needs_real_low_and_high_reports_then_full_start_delay():
    manager, adapter, clock, runtime, row = await ended()
    clock.advance(900)
    await observe(manager, clock, row, surplus=0)
    clock.advance(300)
    await observe(manager, clock, row, surplus=0)
    assert manager._general_reference["solar_reset_stamp"] == clock()
    # The confirmed reset is persisted; restoring it grants no new ON.
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    manager.restore(runtime.store.saves[-1]["sg_boost"])
    clock.advance(1)
    await observe(manager, clock, row)
    clock.advance(299)
    await observe(manager, clock, row)
    assert manager.completion_hold
    clock.advance(1)
    await observe(manager, clock, row)
    assert not manager.completion_hold and not manager.owned
    clock.advance(120)
    await observe(manager, clock, row)
    assert len(adapter.calls) == 3 and manager._last_rearm["kind"] == "new_solar_period"


@pytest.mark.asyncio
async def test_repeated_reports_and_small_surplus_dip_are_not_a_new_solar_episode():
    manager, adapter, clock, _, row = await ended()
    clock.advance(900)
    await observe(manager, clock, row, surplus=2999)
    clock.advance(300)
    await observe(manager, clock, row, surplus=2999)
    clock.advance(300)
    await observe(manager, clock, row)
    assert manager.completion_hold
    stamp = clock()
    await observe(manager, clock, row, surplus=0, solar_stamp=stamp)
    clock.advance(300)
    await observe(manager, clock, row, surplus=0, solar_stamp=stamp)
    assert manager._general_reference["solar_reset_stamp"] is None
    assert len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_native_idle_then_new_same_active_episode_is_meaningful_but_unavailable_is_not():
    manager, adapter, clock, _, row = await ended()
    clock.advance(900)
    row["context_reliable"] = False
    await observe(manager, clock, row)
    clock.advance(300)
    row["context_reliable"] = True
    await observe(manager, clock, row)
    assert manager.completion_hold
    row.update(context="normal", context_signature="off:idle")
    await observe(manager, clock, row)
    clock.advance(300)
    await observe(manager, clock, row)
    row.update(context="space_heating", context_signature="heat:idle")
    clock.advance(1)
    await observe(manager, clock, row)
    clock.advance(300)
    await observe(manager, clock, row)
    assert not manager.completion_hold and len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_new_context_repeated_or_stale_sample_cannot_complete_confirmation_window():
    manager, adapter, clock, _, row = await ended()
    clock.advance(900)
    row["context_signature"] = "heat:heating"
    await observe(manager, clock, row)
    clock.advance(300)
    await observe(manager, clock, row, refresh=False)
    assert manager.completion_hold and len(adapter.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("changes", [
    {"context": "space_cooling", "cooling_possible": True},
    {"context": "space_heating", "cooling_possible": True},
    {"context": "heatpump_unknown", "context_reliable": False, "cooling_possible": True},
    {"context_reliable": False, "cooling_possible": False},
])
async def test_general_cooling_or_auto_unknown_requires_separate_protection(changes):
    manager, adapter, clock, _, row = general_fixture()
    row.update(changes)
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert not adapter.calls and "beveiliging" in manager.reason


@pytest.mark.asyncio
async def test_confirmed_condensation_protection_allows_native_cooling_without_setting_writes():
    manager, adapter, clock, _, row = general_fixture(cooling_protection_confirmed=True)
    row.update(context="space_cooling", context_signature="cool:cooling", cooling_possible=True)
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert adapter.calls == [("on", 300)]
    assert manager.settings["cooling_protection_confirmed"] is True


@pytest.mark.asyncio
async def test_cooling_guard_is_rechecked_at_actual_on_boundary_and_on_renewal():
    manager, adapter, clock, runtime, row = general_fixture()
    await observe(manager, clock, row)
    clock.advance(120)
    original_save = runtime.store.async_save

    async def changed_context(data):
        await original_save(data)
        if manager._in_flight:
            row["cooling_possible"] = True

    runtime.store.async_save = changed_context
    await observe(manager, clock, row)
    assert not adapter.calls
    row["cooling_possible"] = False
    runtime.store.async_save = original_save
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert manager.owned
    row["cooling_possible"] = True
    clock.advance(60)
    await observe(manager, clock, row)
    assert adapter.calls[-1] == ("off", None) and not manager.owned


@pytest.mark.asyncio
async def test_profile_change_converts_only_old_tank_hold_and_preserves_true_holds():
    manager, adapter, clock, runtime = fixture(tank_temperature_entity="sensor.fictional_tank")
    manager.completion_hold = manager.manual_hold = True
    manager._need_reference = {"schema": 1, "entity_id": "sensor.fictional_tank",
        "temperature_c": 60, "stamp": clock(), "ended_at": clock()}
    manager._fault("lease_failed", "Fictional safety hold")
    manager.update_config({**manager.settings, "profile": "general", "profile_confirmed": True})
    assert manager.manual_hold and manager.fault_code == "lease_failed" and manager.completion_hold
    assert manager._hold_provenance["need_reference"]["temperature_c"] == 60
    saved = manager.snapshot()
    other = SGBoostManager(runtime, adapter=adapter, clock=clock)
    other.settings = deepcopy(manager.settings)
    other.restore(saved)
    assert other._hold_provenance == manager._hold_provenance and other.manual_hold
    assert "tank" not in other._completion_reason().casefold()


@pytest.mark.asyncio
async def test_general_conversion_of_legacy_hold_requires_fresh_context_and_is_idempotent():
    manager, adapter, clock, runtime, row = general_fixture()
    manager.restore({"schema": 1, "relay_entity": manager.settings["entity_id"],
                     "completion_hold": True})
    provenance = deepcopy(manager._hold_provenance)
    await observe(manager, clock, row)
    clock.advance(300)
    await observe(manager, clock, row)
    assert manager.completion_hold  # First same-time report is not after conversion.
    clock.advance(300)
    await observe(manager, clock, row)
    assert not manager.completion_hold and not adapter.calls
    manager.restore(manager.snapshot())
    assert manager._hold_provenance == provenance


@pytest.mark.asyncio
async def test_scope_change_during_owned_session_releases_before_new_evaluation():
    manager, adapter, clock, _, row = await started()
    manager.update_config({**manager.settings, "profile": "dhw_only", "profile_confirmed": False})
    assert not manager.desired_on
    await observe(manager, clock, row)
    assert adapter.calls[-1] == ("off", None) and not manager.owned
    assert manager.state == "rest"


@pytest.mark.asyncio
async def test_low_consumption_twenty_minutes_logs_once_without_off_on_or_native_writes():
    manager, adapter, clock, runtime, row = await started()
    row["power_w"] = 64
    for _ in range(25):
        clock.advance(60)
        await observe(manager, clock, row)
    messages = [note for note in runtime.notes if "extra warmteopname nog niet aangetoond" in note]
    assert len(messages) == 1 and manager.owned and not manager.fault
    assert all(command == "on" for command, _ in adapter.calls)


@pytest.mark.asyncio
async def test_one_low_reading_after_twenty_minutes_is_not_sustained_low_power():
    manager, _, clock, runtime, row = await started()
    row["power_w"] = 1800
    for _ in range(22):
        clock.advance(60)
        await observe(manager, clock, row)
    row["power_w"] = 64
    await observe(manager, clock, row)
    assert not any("extra warmteopname nog niet aangetoond" in note for note in runtime.notes)


@pytest.mark.asyncio
async def test_read_binding_change_is_not_new_native_business_context():
    manager, adapter, clock, _, row = await ended()
    manager.update_config({**manager.settings, "zone_entities": ["climate.fictional_new_reader"]})
    clock.advance(900)
    row["context_signature"] = "new-reader:heat:idle"
    await observe(manager, clock, row)
    clock.advance(300)
    await observe(manager, clock, row)
    assert manager.completion_hold and len(adapter.calls) == 2
    row["context_signature"] = "new-reader:heat:heating"
    clock.advance(1)
    await observe(manager, clock, row)
    clock.advance(300)
    await observe(manager, clock, row)
    assert not manager.completion_hold and len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_lease_finishing_at_session_limit_persists_hold_before_reload():
    manager, adapter, clock, runtime, row = await started(max_session_s=300)
    clock.advance(301)
    await observe(manager, clock, row)
    saved = runtime.store.saves[-1]["sg_boost"]
    assert saved["completion_hold"] and saved["hold_reason"] == "session_limit"
    other = SGBoostManager(runtime, adapter=adapter, clock=clock)
    other.restore(saved)
    clock.advance(2000)
    await observe(other, clock, row)
    clock.advance(2000)
    await observe(other, clock, row)
    assert other.completion_hold and len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_skipped_final_ticks_cannot_bypass_general_session_limit():
    manager, adapter, clock, _, row = await started(max_session_s=600)
    assert not manager._session_finishing
    clock.advance(601)
    await observe(manager, clock, row)
    assert manager.completion_hold and manager._hold_reason == "session_limit"
    clock.advance(900)
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_premature_general_lease_expiry_needs_new_real_evidence():
    manager, adapter, clock, _, row = await started()
    clock.advance(301)
    await observe(manager, clock, row)
    assert manager.completion_hold and manager._hold_reason == "response_unknown"
    clock.advance(900)
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_reload_of_active_general_request_releases_and_does_not_restart_from_rest_only():
    previous, adapter, clock, runtime, row = await started()
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    manager.restore(previous.snapshot())
    await manager.start()
    assert manager.completion_hold and manager._hold_reason == "response_unknown"
    clock.advance(900)
    await observe(manager, clock, row)
    clock.advance(300)
    await observe(manager, clock, row)
    assert adapter.calls == [("on", 300), ("off", None)]
    await manager.resume_automation()
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert adapter.calls[-1] == ("on", 300)


@pytest.mark.asyncio
async def test_soft_source_release_general_has_policy_hold_separate_from_source_fault():
    manager, adapter, clock, _, row = await started()
    await manager.tick(surplus_w=4000, grid_import_w=0, data_fresh=False,
        phase_allowed=True, native_observation=row, solar_stamp=clock())
    assert manager.completion_hold and not manager.fault
    clock.advance(2000)
    await observe(manager, clock, row)
    clock.advance(300)
    await observe(manager, clock, row)
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_restored_timestamp_shapes_are_normalized_without_crashing_or_granting_on():
    manager, adapter, clock, _, row = general_fixture()
    manager.restore({"schema": 1, "relay_entity": manager.settings["entity_id"],
        "completion_hold": True, "general_reference": {"schema": 1,
            "ended_at": str(clock()-1), "signature": "same-native",
            "native_stamp": str(clock()-1), "solar_stamp": str(clock()-1),
            "solar_reset_stamp": {"malformed": True}}})
    await observe(manager, clock, row)
    assert manager.completion_hold and not adapter.calls
    assert manager._general_reference["ended_at"] == clock()-1
    assert manager._general_reference["solar_reset_stamp"] is None


@pytest.mark.asyncio
async def test_legacy_tank_reference_numeric_strings_remain_readable_and_do_not_grant_on():
    manager, adapter, clock, _ = fixture(tank_temperature_entity="sensor.fictional_tank")
    manager.restore({"schema": 1, "relay_entity": manager.settings["entity_id"],
        "completion_hold": True, "need_reference": {"schema": 1,
            "entity_id": "sensor.fictional_tank", "temperature_c": "55",
            "stamp": str(clock()-1), "ended_at": str(clock()-1)}})
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    assert manager.completion_hold and not adapter.calls
    assert manager._need_reference["temperature_c"] == 55


@pytest.mark.asyncio
async def test_manual_contact_on_does_not_invent_timer_confirmation():
    manager, adapter, _, _, _ = general_fixture()
    adapter.on = True
    await manager.start()
    view = manager.overview()
    assert view["owner"] == "manual" and view["lease_confirmed"] is False
    assert not adapter.calls


@pytest.mark.asyncio
async def test_frequency_or_compressor_operation_never_claims_sg_causality():
    manager, _, clock, _, row = await started()
    row.update(compressor_running=True, frequency_hz=31, power_w=1300)
    await observe(manager, clock, row)
    assert manager.panasonic_confirmed is None
    row.update(sg_status="active", sg_status_confirmed=True)
    await observe(manager, clock, row)
    assert manager.panasonic_confirmed is True
