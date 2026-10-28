"""Independent cloud-buffer races with fictional real-report evidence.

Source timestamps represent actual P1 reports, never rendering or forecasting.
These checks do not establish physical Shelly or Panasonic commissioning.
"""
from copy import deepcopy
import time

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_electrical_limits69 import protected_ev
from test_sg_budget_priority62 import configured
from test_sg_controller62 import boosted, fixture


SOURCE = ("sensor.fictional_p1", "import_positive", "")
CURRENT = object()


async def report(manager, clock, *, imported=900, stamp=CURRENT, source=SOURCE,
                 data_fresh=True, **context):
    stamp = clock() if stamp is CURRENT else stamp
    return await manager.tick(
        surplus_w=0, real_surplus_w=0, grid_import_w=imported,
        grid_import_stamp=stamp, grid_import_source=source,
        solar_stamp=clock(), data_fresh=data_fresh, phase_allowed=True,
        **context)


async def advance_reports(manager, clock, target, *, imported=900):
    while clock() < target:
        clock.advance(min(60, target - clock()))
        await report(manager, clock, imported=imported)


async def active_cloud(*, min_session_s=0):
    manager, adapter, clock, runtime = await boosted(
        import_threshold_w=600, stop_delay_s=300, min_session_s=min_session_s)
    await report(manager, clock)
    assert manager.cloud_hold_active
    return manager, adapter, clock, runtime


@pytest.mark.asyncio
async def test_cloud_start_at_minute_eighteen_stops_at_twenty_three_without_timer_restart():
    manager, adapter, clock, _runtime = await boosted(
        import_threshold_w=600, stop_delay_s=300, min_session_s=1200)
    started = clock()
    await advance_reports(manager, clock, started + 1080, imported=0)
    await report(manager, clock)
    onset = manager._import_since
    await advance_reports(manager, clock, started + 1379)
    assert manager.owned and adapter.on and manager._import_since == onset
    assert not manager.minimum_hold_active and manager.cloud_hold_active
    clock.advance(1)
    await report(manager, clock)
    assert not manager.owned and adapter.calls[-1] == ("off", None)
    assert manager._last_session["duration_s"] == 1380


@pytest.mark.asyncio
async def test_cloud_pending_longer_than_five_minutes_releases_at_minimum_end():
    manager, adapter, clock, _runtime = await boosted(
        import_threshold_w=600, stop_delay_s=300, min_session_s=1200)
    started = clock()
    await advance_reports(manager, clock, started + 600, imported=0)
    await report(manager, clock)
    onset = manager._import_since
    await advance_reports(manager, clock, started + 1199)
    assert manager.owned and manager._import_since == onset
    assert manager.minimum_hold_active and not manager.cloud_hold_active
    clock.advance(1)
    await report(manager, clock)
    assert not manager.owned and adapter.calls[-1] == ("off", None)
    assert manager._last_session["duration_s"] == 1200


@pytest.mark.asyncio
async def test_post_minimum_cloud_renews_past_old_four_minute_five_second_expiry():
    manager, adapter, clock, _runtime = await boosted(
        import_threshold_w=600, stop_delay_s=300, min_session_s=1200)
    await advance_reports(manager, clock, clock() + 1200, imported=0)
    clock.advance(55)
    onset = clock()
    original_deadline = manager._lease_deadline
    assert original_deadline - onset == 245
    await report(manager, clock)
    await advance_reports(manager, clock, onset + 245)
    assert manager.owned and adapter.on
    assert manager._lease_deadline > original_deadline
    await advance_reports(manager, clock, onset + 299)
    assert manager.owned and manager._import_since == onset
    clock.advance(1)
    await report(manager, clock)
    assert not manager.owned and adapter.calls[-1] == ("off", None)


@pytest.mark.asyncio
async def test_exact_six_hundred_watt_recovery_resets_candidate_and_new_cloud_gets_full_grace():
    manager, adapter, clock, _runtime = await active_cloud()
    first = manager._import_since
    await advance_reports(manager, clock, clock() + 200)
    await report(manager, clock, imported=600)
    assert manager._import_since is None and not manager.cloud_hold_active
    clock.advance(1)
    await report(manager, clock, imported=601)
    second = manager._import_since
    assert second > first
    await advance_reports(manager, clock, second + 299, imported=601)
    assert manager.owned and manager._import_since == second
    clock.advance(1)
    await report(manager, clock, imported=601)
    assert not manager.owned and adapter.calls[-1] == ("off", None)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["backdated", "binding"])
async def test_unreliable_p1_cannot_restart_owned_cloud_without_measured_recovery(change):
    manager, adapter, clock, _runtime = await active_cloud()
    onset = manager._import_since
    await advance_reports(manager, clock, onset + 299)
    stamp, source = clock(), SOURCE
    if change == "backdated":
        stamp -= 1  # Still fresh, but older than the last genuine P1 report.
    else:
        source = ("sensor.other_fictional_p1", "import_positive", "")
    await report(manager, clock, stamp=stamp, source=source)
    # Unreliable evidence may force a safe release, but cannot buy another
    # five minutes of sustained import in the same confirmed request.
    assert not manager.owned or manager._import_since == onset
    clock.advance(1)
    await report(manager, clock, stamp=stamp, source=source)
    assert not manager.owned and adapter.calls[-1] == ("off", None)


@pytest.mark.asyncio
async def test_expired_original_p1_followed_by_fresh_report_cannot_buy_a_new_buffer():
    manager, adapter, clock, _runtime = await active_cloud()
    onset = manager._import_since
    clock.advance(121)  # Original P1 expired; the 300s local relay is still ON.
    await report(manager, clock)
    assert not manager.owned or manager._import_since == onset
    await advance_reports(manager, clock, onset + 300)
    assert not manager.owned and adapter.calls[-1] == ("off", None)


@pytest.mark.asyncio
async def test_repeated_current_original_report_keeps_original_candidate_start():
    manager, _adapter, clock, _runtime = await active_cloud()
    onset, original_stamp = manager._import_since, clock()
    clock.advance(60)
    await report(manager, clock, stamp=original_stamp)
    assert manager.owned and manager._import_since == onset
    assert manager.cloud_hold_active


async def live_cloud_dispatch():
    """A real SolarRuntime gate with independent monotonic and HA wall clocks."""
    manager, adapter, clock, runtime = await boosted(
        import_threshold_w=600, stop_delay_s=300, min_session_s=0)
    shift = time.time() - manager._wall_clock()
    manager._relay_observed_at += shift
    manager._relay_valid_until += shift
    manager._wall_clock = time.time
    live, hass = configured(export=0, reserve=0)
    live.settings["max_import_w"] = 3500
    live.sg_boost = manager
    hass.states.set("sensor.grid", 900, {"unit_of_measurement": "W"})
    original_p1 = live._sg_import_observation()
    manager._observe_import(original_p1["watts"], original_p1["stamp"],
                            original_p1["source"], clock())
    runtime.sg_dispatch_allowed = live.sg_dispatch_allowed
    assert manager.cloud_hold_active and not manager.minimum_hold_active
    assert live.sg_dispatch_allowed(renewal=True)
    return manager, adapter, clock, runtime, live, hass


@pytest.mark.asyncio
@pytest.mark.parametrize("hard_guard", [
    "fixed_import", "actual_load", "stale_grid", "stale_pv",
    "battery_discharge", "missing_phases", "missing_quarter", "protected_ev",
    "pause", "restart", "runtime_fault", "pending_command", "removal",
])
async def test_cloud_after_minimum_cannot_bypass_live_physical_or_runtime_guards(hard_guard):
    manager, _adapter, _clock, _runtime, live, hass = await live_cloud_dispatch()
    if hard_guard == "fixed_import":
        hass.states.set("sensor.grid", 3501, {"unit_of_measurement": "W"})
    elif hard_guard == "actual_load":
        live.states["a"].target_w += 2601
        # The future thermostat target alone spends no current export.
        assert live.sg_dispatch_allowed(renewal=True)
        hass.states.set("sensor.grid", 3501, {"unit_of_measurement": "W"})
    elif hard_guard in ("stale_grid", "stale_pv"):
        entity = "sensor.grid" if hard_guard == "stale_grid" else "sensor.public_pv"
        obj = hass.states.get(entity)
        hass.states.set(entity, obj.state, obj.attributes, age=121)
    elif hard_guard == "battery_discharge":
        live.settings.update(battery_power_entity="sensor.fixture_battery",
                             battery_sign="discharge_positive")
        hass.states.set("sensor.fixture_battery", 51, {"unit_of_measurement": "W"})
    elif hard_guard == "missing_phases":
        live.phase_settings.update(enabled=True, control_starts=True)
    elif hard_guard == "missing_quarter":
        live.capacity_settings.update(enabled=True)
    elif hard_guard == "protected_ev":
        protected_ev(live, hass)
        # SG can retain confirmed solar EV watts during the cloud hold, while
        # actual P1 above the fixed import ceiling still blocks the renewal.
        assert live.sg_dispatch_allowed(renewal=True)
        hass.states.set("sensor.grid", 3501, {"unit_of_measurement": "W"})
    elif hard_guard == "pause":
        live.mode = "paused"
    elif hard_guard == "restart":
        live.recovery["a"] = {"fictional": True}
        live.faults["a"] = "Fictional unresolved command"
    elif hard_guard == "runtime_fault":
        live.faults["a"] = "Fictional runtime fault"
    elif hard_guard == "pending_command":
        live.pending = {"fictional": True}
    else:
        live.removal_requested = True
    assert not live.sg_dispatch_allowed(renewal=True)
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_measured_recovery_uses_actual_p1_even_when_conservative_filter_stays_above_threshold():
    manager, _adapter, clock, _runtime, live, hass = await live_cloud_dispatch()
    live.filtered = 900  # Still conservatively counted by the physical budget.
    hass.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    p1 = live._sg_import_observation()
    manager._observe_import(p1["watts"], p1["stamp"], p1["source"], clock())
    assert manager._import_since is None and not manager.cloud_hold_active
    assert live.sg_dispatch_allowed(renewal=True)
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("exit_reason", [
    "data", "priority", "hard_limit", "native_complete", "native_no_uptake",
    "manual", "local_off", "watchdog", "pause", "fault",
])
async def test_cloud_candidate_cannot_postpone_hard_native_manual_or_local_off(exit_reason):
    manager, adapter, clock, runtime = await active_cloud()
    context = {}
    data_fresh = exit_reason != "data"
    if exit_reason == "priority":
        context["priority_allowed"] = False
    elif exit_reason == "hard_limit":
        context["hard_limit"] = True
    elif exit_reason.startswith("native_"):
        context["physical_evidence"] = {"verified": True,
            "completed" if exit_reason == "native_complete" else "no_uptake": True}
    elif exit_reason == "manual":
        manager.manual_hold = True
    elif exit_reason == "local_off":
        adapter.on = False
    elif exit_reason == "watchdog":
        manager.settings["watchdog_confirmed"] = False
    elif exit_reason == "pause":
        runtime.mode = "paused"
    elif exit_reason == "fault":
        manager._fault("lease_failed", "Fictional local timer fault")
    await report(manager, clock, data_fresh=data_fresh, **context)
    assert not manager.owned and not manager.desired_on
    assert not manager.cloud_hold_active
    assert len([call for call in adapter.calls if call[0] == "on"]) == 1


@pytest.mark.asyncio
async def test_cloud_renewal_slow_save_and_receipt_keep_original_hard_session_ceiling():
    manager, adapter, clock, runtime = await boosted(
        import_threshold_w=600, stop_delay_s=300, min_session_s=0,
        max_session_s=600)
    started = manager._session_started
    await advance_reports(manager, clock, started + 240, imported=0)
    clock.advance(60)
    original_save, original_on = runtime.store.async_save, adapter.set_on
    delayed = False
    adapter.before_on = None

    async def delayed_storage(data):
        nonlocal delayed
        if not delayed:
            delayed = True
            clock.advance(25)
        await original_save(data)

    async def delayed_receipt(lease_s):
        assert adapter.before_on() is True
        clock.advance(5)
        return await original_on(lease_s=lease_s)

    runtime.store.async_save, adapter.set_on = delayed_storage, delayed_receipt
    await report(manager, clock)
    assert manager.owned and manager.cloud_hold_active
    assert manager._import_since == started + 300
    assert manager._lease_deadline <= started + 600
    clock.advance(started + 600 - clock() + .01)
    assert adapter.status()["output"] is False
    await report(manager, clock)
    assert not manager.owned and not manager.cloud_hold_active


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [
    "ownership", "desired", "confirmed_contact", "on_contact",
    "lease_deadline", "relay_deadline", "fresh_contact",
])
async def test_cloud_renewal_needs_current_confirmed_owned_on_and_unexpired_lease(missing):
    manager, adapter, clock, _runtime = await active_cloud()
    if missing == "ownership":
        manager.owned = False
        manager._possibly_owned = True
    elif missing == "desired":
        manager.desired_on = False
    elif missing == "confirmed_contact":
        manager.relay_confirmed = False
    elif missing == "on_contact":
        manager.relay_on = False
    elif missing == "lease_deadline":
        manager._lease_deadline = clock()
    elif missing == "relay_deadline":
        manager._relay_valid_until = clock()
    else:
        manager._relay_observed_at = clock() - manager.settings["stale_s"] - 1
    assert not manager.cloud_hold_active
    assert not manager.soft_import_renewal_allowed(
        grid_import_w=900, grid_import_stamp=clock(), grid_import_source=SOURCE)
    calls = list(adapter.calls)
    await manager._issue_on(renewal=True)
    assert adapter.calls == calls


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_report", ["missing", "old", "future", "binding", "backdated"])
async def test_final_cloud_helper_rejects_unproven_or_different_original_p1_report(bad_report):
    manager, _adapter, clock, _runtime = await active_cloud()
    stamp, source = clock(), SOURCE
    if bad_report == "missing":
        stamp = None
    elif bad_report == "old":
        stamp -= manager.settings["stale_s"] + 1
    elif bad_report == "future":
        stamp += 5.01
    elif bad_report == "binding":
        source = ("sensor.other_fictional_p1", "import_positive", "")
    else:
        stamp -= 1
    assert not manager.soft_import_renewal_allowed(
        grid_import_w=900, grid_import_stamp=stamp, grid_import_source=source)


@pytest.mark.asyncio
@pytest.mark.parametrize("stamp", [None, "unavailable", True])
async def test_missing_original_p1_during_minimum_never_crashes_or_grants_cloud(stamp):
    manager, adapter, clock, _runtime = await boosted(
        import_threshold_w=600, stop_delay_s=300, min_session_s=1200)
    await report(manager, clock, stamp=stamp)
    assert not manager.cloud_hold_active
    assert not manager.soft_import_renewal_allowed(
        grid_import_w=900, grid_import_stamp=stamp, grid_import_source=SOURCE)
    # Missing required source evidence cannot be converted into a relay ON.
    assert len([call for call in adapter.calls if call[0] == "on"]) == 1


@pytest.mark.asyncio
async def test_renewal_and_cached_cloud_state_never_grant_an_initial_on():
    manager, adapter, clock, _runtime = fixture(
        import_threshold_w=600, stop_delay_s=300, min_session_s=1200)
    await manager.start()
    manager._observe_import(900, clock(), SOURCE, clock())
    assert not manager.cloud_hold_active and not manager.minimum_hold_active
    assert not manager.soft_import_renewal_allowed(
        grid_import_w=900, grid_import_stamp=clock(), grid_import_source=SOURCE)
    await manager._issue_on(renewal=True)
    assert not adapter.calls and not manager.desired_on


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["grace_expired", "p1_expired", "new_policy", "new_binding",
                                    "lease_expired", "relay_expired", "disabled"])
async def test_final_callback_rejects_cloud_evidence_changed_during_async_preflight(change):
    manager, adapter, clock, runtime = await active_cloud()
    if change == "grace_expired":
        await advance_reports(manager, clock, clock() + 299)
    elif change == "p1_expired":
        clock.advance(119)
        await manager._read(force=True)  # Current relay; original P1 is aged.
    else:
        clock.advance(60)
        await report(manager, clock)
        # The normal tick renewed at sixty seconds. Move beyond that exact
        # deadline so this independent renewal genuinely enters preflight.
        clock.advance(1)
        await report(manager, clock)
    old_stamp = clock() - 119 if change == "p1_expired" else clock()
    live = {"stamp": old_stamp, "source": SOURCE}
    runtime.sg_dispatch_allowed = lambda renewal=False: renewal and manager.soft_import_renewal_allowed(
        grid_import_w=900, grid_import_stamp=live["stamp"], grid_import_source=live["source"])
    assert runtime.sg_dispatch_allowed(renewal=True)
    calls = list(adapter.calls)
    adapter.before_on = None

    class DispatchChanged(Exception):
        code = "dispatch_changed"
        command_attempted = False

    async def changed_preflight(lease_s):
        if change in ("grace_expired", "p1_expired"):
            clock.advance(2)
        elif change == "new_policy":
            manager.update_config({**manager.settings, "stop_delay_s": 600})
        elif change == "new_binding":
            live["source"] = ("sensor.other_fictional_p1", "import_positive", "")
        elif change == "lease_expired":
            manager._lease_deadline = clock()
        elif change == "relay_expired":
            manager._relay_valid_until = clock()
        else:
            manager.settings["enabled"] = False
        if adapter.before_on() is not True:
            raise DispatchChanged()
        raise AssertionError("Changed cloud proof must never reach the contact write")

    adapter.set_on = changed_preflight
    await manager._issue_on(renewal=True)
    assert adapter.calls == calls + [("off", None)]
    assert not manager.owned and not manager.desired_on and not manager.fault


@pytest.mark.asyncio
async def test_restore_never_resumes_the_previous_cloud_candidate_or_renewal_right():
    previous, adapter, clock, runtime = await active_cloud(min_session_s=1200)
    saved = deepcopy(previous.snapshot())
    saved.pop("session_checkpoint")  # Legacy journals remain release-only.
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = manager
    runtime._snapshot = lambda: {"sg_boost": manager.snapshot()}
    manager.restore(saved)
    assert manager._import_since is None and not manager.cloud_hold_active
    await manager.start()
    assert adapter.calls == [("on", 300), ("off", None)]
    assert not manager.soft_import_renewal_allowed(
        grid_import_w=900, grid_import_stamp=clock(), grid_import_source=SOURCE)
