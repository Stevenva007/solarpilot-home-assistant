"""Real soft-import policy with fictional measured P1 and local SG leases."""
from copy import deepcopy
import asyncio
import time

import pytest

from test_sg_budget_priority62 import configured
from test_sg_controller62 import boosted, fixture, tick


@pytest.mark.asyncio
async def test_explicit_cloud_policy_is_separate_from_solar_episode_hysteresis():
    manager, adapter, clock, _ = await boosted(min_session_s=0)
    assert manager.settings["import_threshold_w"] == 600
    assert manager.settings["stop_delay_s"] == 300
    assert manager.settings["hysteresis_w"] == 300
    for _ in range(6):
        clock.advance(60)
        await tick(manager, surplus=0, imported=600)
        assert manager.owned and manager._import_since is None
    assert adapter.calls == [("on", 300)] * 7
    row = manager.overview()
    assert not row["cloud_active"] and row["cloud_remaining_s"] is None
    assert row["cloud_valid_until"] == clock() + 120


@pytest.mark.asyncio
async def test_continuous_import_above_six_hundred_stops_after_five_minutes_with_renewals():
    manager, adapter, clock, _ = await boosted(min_session_s=0)
    await tick(manager, surplus=0, imported=600.1)
    began = manager._import_since
    for seconds in (60, 60, 60, 60, 59):
        clock.advance(seconds)
        await tick(manager, surplus=0, imported=600.1)
        assert manager.owned and manager._import_since == began
    row = manager.overview()
    assert row["cloud_active"] and row["cloud_import_hold"] and row["cloud_remaining_s"] == 1
    assert adapter.calls == [("on", 300)] * 5
    clock.advance(1)
    await tick(manager, surplus=0, imported=600.1)
    assert not manager.owned and adapter.calls[-1] == ("off", None)
    assert manager._last_session["duration_s"] == 300
    assert manager._last_session["reason"] == "Aanhoudende netafname; extra SG-aanvraag vrijgegeven"
    assert manager.overview()["cloud_valid_until"] is None


@pytest.mark.asyncio
async def test_exact_threshold_recovery_resets_the_whole_continuous_import_window():
    manager, adapter, clock, _ = await boosted(min_session_s=0)
    await tick(manager, imported=1000)
    for _ in range(4):
        clock.advance(60)
        await tick(manager, imported=1000)
    clock.advance(59)
    await tick(manager, imported=600)
    assert manager._import_since is None and not manager.cloud_hold_active
    clock.advance(1)
    await tick(manager, imported=1000)
    restarted = manager._import_since
    assert manager.overview()["cloud_remaining_s"] == 300
    for _ in range(4):
        clock.advance(60)
        await tick(manager, imported=1000)
    clock.advance(59)
    await tick(manager, imported=1000)
    assert manager.owned and manager._import_since == restarted
    clock.advance(1)
    await tick(manager, imported=1000)
    assert not manager.owned and adapter.calls[-1] == ("off", None)


@pytest.mark.asyncio
async def test_cloud_zero_during_minimum_reports_overlap_without_restarting_either_timer():
    manager, adapter, clock, _ = await boosted()
    minimum = manager._minimum_started
    await tick(manager, imported=1000)
    cloud = manager._import_since
    for _ in range(5):
        clock.advance(60)
        await tick(manager, imported=1000)
    row = manager.overview()
    assert row["cloud_active"] and row["cloud_import_hold"]
    assert row["cloud_remaining_s"] == 0 and row["minimum_remaining_s"] == 900
    assert not manager.cloud_hold_active and manager.minimum_hold_active
    assert manager._minimum_started == minimum and manager._import_since == cloud
    assert adapter.calls == [("on", 300)] * 6


@pytest.mark.asyncio
async def test_cloud_overview_does_not_read_save_mutate_or_refresh_the_old_p1_report():
    manager, adapter, clock, runtime = await boosted(min_session_s=0)
    await tick(manager, imported=1000, grid_import_stamp=clock() - 90)
    state = deepcopy(manager.__dict__)
    state.pop("_lock")
    calls, reads, saves = list(adapter.calls), adapter.reads, len(runtime.store.saves)
    for _ in range(3):
        row = manager.overview()
        assert row["cloud_remaining_s"] == 300 and row["cloud_valid_until"] == clock() + 30
    after = dict(manager.__dict__)
    after.pop("_lock")
    # Evidence and counters are compared directly; runtime/adapter have their
    # own mutable identities and are independently checked for side effects.
    for name in ("_import_since", "_import_policy", "_import_observation", "_minimum_started", "_lease_deadline"):
        assert after[name] == state[name]
    assert (adapter.calls, adapter.reads, len(runtime.store.saves)) == (calls, reads, saves)
    clock.advance(30)
    row = manager.overview()
    assert not row["cloud_active"] and not row["cloud_import_hold"]
    assert row["cloud_remaining_s"] is None and row["cloud_valid_until"] is None
    assert not manager.cloud_hold_active


@pytest.mark.asyncio
@pytest.mark.parametrize("stamp_delta", [None, -120, -121, 5.01])
async def test_missing_stale_or_future_original_p1_proof_releases_even_during_minimum(stamp_delta):
    manager, adapter, clock, _ = await boosted()
    stamp = None if stamp_delta is None else clock() + stamp_delta
    await tick(manager, imported=1000, grid_import_stamp=stamp)
    assert adapter.calls == [("on", 300), ("off", None)]
    assert not manager.owned and not manager.minimum_hold_active and not manager.cloud_hold_active


@pytest.mark.asyncio
@pytest.mark.parametrize("key,value", [
    ("import_threshold_w", None), ("import_threshold_w", "invalid"),
    ("import_threshold_w", float("nan")), ("import_threshold_w", True),
    ("import_threshold_w", -1), ("import_threshold_w", 20001),
    ("stop_delay_s", None), ("stop_delay_s", "invalid"),
    ("stop_delay_s", float("nan")), ("stop_delay_s", True),
    ("stop_delay_s", 0), ("stop_delay_s", 901),
])
async def test_invalid_stored_import_policy_blocks_without_throwing_or_retaining_owned_on(key, value):
    manager, adapter, clock, _ = await boosted()
    manager.settings[key] = value  # Imported bad options remain visible, never repaired silently.
    row = manager.overview()
    assert row["cloud_remaining_s"] is None and row["cloud_valid_until"] is None
    assert not row["cloud_import_hold"] and not manager.minimum_hold_active
    assert not manager.soft_import_renewal_allowed(grid_import_w=1000, grid_import_stamp=clock())
    await tick(manager, imported=1000)
    assert manager.state == "blocked" and not manager.owned
    assert "SG-instellingen vragen controle" in manager.reason
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_before_confirmed_on_and_after_restore_no_cloud_authority_or_progress_exists():
    manager, adapter, _, _ = fixture()
    await tick(manager, imported=1000)
    row = manager.overview()
    assert not row["cloud_active"] and not row["cloud_import_hold"]
    assert row["cloud_remaining_s"] is None and row["cloud_valid_until"] is None
    assert not adapter.calls
    manager.restore({"schema": 1, "relay_entity": manager.settings["entity_id"], "owned": True})
    assert manager._import_since is None and manager._import_observation is None
    assert not manager.cloud_hold_active


@pytest.mark.asyncio
async def test_valid_numeric_string_import_options_keep_the_same_measured_policy():
    manager, adapter, clock, _ = await boosted(min_session_s=0, import_threshold_w="600", stop_delay_s="300")
    await tick(manager, imported=900)
    clock.advance(60)
    await tick(manager, imported=900)
    assert manager.cloud_hold_active and manager.overview()["cloud_remaining_s"] == 240
    assert adapter.calls == [("on", 300), ("on", 300)]


@pytest.mark.parametrize("sign,value,expected", [
    ("import_positive", 750, 750), ("import_positive", -750, 0),
    ("export_positive", -750, 750), ("export_positive", 750, 0),
])
def test_p1_proof_uses_actual_signed_report_independent_of_old_pv_or_existing_hp(sign, value, expected):
    runtime, hass = configured(export=0)
    runtime.settings["grid_sign"] = sign
    hass.states.set("sensor.grid", value, {"unit_of_measurement": "W"})
    hass.states.set("sensor.public_pv", 8000, {"unit_of_measurement": "W"}, age=110)
    hass.states.set("sensor.public_hp", 2500, {"unit_of_measurement": "W"}, age=100)
    source = runtime._sg_import_observation()
    assert source["watts"] == expected
    assert source["stamp"] == hass.states.get("sensor.grid").last_reported.timestamp()
    assert source["source"] == (sign, "sensor.grid", None)


def test_separate_import_export_p1_proof_requires_both_original_current_reports():
    runtime, hass = configured(export=0)
    runtime.settings.update(grid_sign="separate", export_entity="sensor.synthetic_export")
    hass.states.set("sensor.grid", 1000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.synthetic_export", 100, {"unit_of_measurement": "W"}, age=90)
    source = runtime._sg_import_observation()
    assert source["watts"] == 900
    assert source["stamp"] == hass.states.get("sensor.synthetic_export").last_reported.timestamp()
    assert source["source"] == ("separate", "sensor.grid", "sensor.synthetic_export")
    hass.states.set("sensor.synthetic_export", 100, {"unit_of_measurement": "W"}, age=121)
    assert runtime._sg_import_observation() is None


@pytest.mark.parametrize("attributes", [
    {"unit_of_measurement": "W", "estimated": True},
    {"unit_of_measurement": "W", "is_estimated": True},
    {"unit_of_measurement": "W", "restored": True},
    {"unit_of_measurement": "kWh"},
])
def test_unusable_p1_cannot_supply_a_cloud_proof(attributes):
    runtime, hass = configured(export=0)
    hass.states.set("sensor.grid", 900, attributes)
    assert runtime._sg_import_observation() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("guard,current", [
    ("fixed", 500), ("fixed", 501), ("quarter", 600), ("quarter", 601),
])
async def test_actual_p1_changed_during_handover_await_keeps_hard_import_ceilings(guard, current):
    runtime, hass = configured(export=4500)
    manager, adapter, _clock, _ = await boosted()
    manager._wall_clock = time.time  # The HA state doubles report actual wall times.
    runtime.sg_boost = manager
    runtime.states["a"].owned = runtime.states["a"].enabled = False
    runtime.device_modes["a"] = "manual"
    limit = 500 if guard == "fixed" else 600
    if guard == "quarter":
        runtime.settings["max_import_w"] = 3500
        runtime.capacity_settings.update(enabled=True, target_peak_w=600, margin_w=0,
            respect_billing_floor=False, adaptive_to_month_peak=False, minimum_elapsed_s=0,
            average_demand_entity="sensor.synthetic_average", monthly_peak_entity="sensor.synthetic_peak")
        hass.states.set("sensor.synthetic_average", 600, {"unit_of_measurement": "W"})
        hass.states.set("sensor.synthetic_peak", 600, {"unit_of_measurement": "W"})

    async def changed_after_original_p1_capture(*_args):
        await asyncio.sleep(0)
        hass.states.set("sensor.grid", current, {"unit_of_measurement": "W"})

    runtime._advance_handover = changed_after_original_p1_capture
    await runtime._tick()
    if current > limit:
        assert not manager.owned and adapter.calls[-1] == ("off", None)
        assert ("Netgrens overschreden" if guard == "fixed" else "Kwartierbudget overschreden") in manager.reason
        assert f"{current} W" in manager.reason
    else:
        assert manager.owned and adapter.calls == [("on", 300)]
        assert manager._import_observation["watts"] == current
        assert manager._import_observation["stamp"] == hass.states.get("sensor.grid").last_reported.timestamp()
        assert manager._import_since is None  # Recovery is the current paired P1 value.
    assert not hass.services.calls
