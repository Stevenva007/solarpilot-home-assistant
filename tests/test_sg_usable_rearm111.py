"""New bounded SG requests from a proven current pool, never invented export."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_sg_request_rest97 import SOURCE, ended_request
from test_sg_live_solar_adversarial111 import ended_site, live_site, site_step, started_site
from test_sg_transfer_integration108 import report, sources


async def usable(manager, clock, row, *, pool=4000, raw=39, source_stamp=None,
                 report_stamp=None, identity=SOURCE, observation=None, **changes):
    value = {"valid": True, "watts": pool,
        "stamp": clock() if source_stamp is None else source_stamp,
        "report_stamp": clock() if report_stamp is None else report_stamp,
        "source_identity": identity} if observation is None else observation
    args = dict(surplus_w=pool, real_surplus_w=raw, grid_import_w=0,
        grid_import_stamp=clock(), solar_stamp=clock(), data_fresh=True,
        phase_allowed=True, native_observation=deepcopy(row),
        start_source_identity=SOURCE, usable_solar_observation=value)
    args.update(changes)
    return await manager.tick(**args)


async def window(manager, clock, row, seconds=120, **kwargs):
    for _ in range(seconds//30):
        clock.advance(30)
        await usable(manager, clock, row, **kwargs)


@pytest.mark.asyncio
async def test_current_pool_has_one_start_window_and_preserves_the_true_export():
    manager, adapter, clock, _, row = await ended_request()
    old = deepcopy(manager._last_session)
    clock.advance(1)
    await usable(manager, clock, row)
    view = manager.overview()
    assert view["real_residual_surplus_w"] == 39
    assert view["usable_solar_w"] == 4000
    assert view["usable_reassessment_available"]
    assert view["reassessment_kind"] == "fresh_usable_solar"
    assert view["reassessment_required_s"] == view["reassessment_remaining_s"] == 120
    assert not manager.owned
    await window(manager, clock, row, 90)
    assert manager.completion_hold and not manager.owned
    assert manager.overview()["reassessment_remaining_s"] == 30
    clock.advance(30)
    await usable(manager, clock, row)
    assert manager.owned and adapter.on and not manager.completion_hold
    assert adapter.calls[-1] == ("on", 300)
    assert manager._last_rearm["kind"] == "fresh_usable_solar"
    assert manager._session_started == clock()
    assert manager._lease_deadline <= clock()+300
    assert manager._last_session == old
    assert manager._solar_observation["watts"] == 39


@pytest.mark.asyncio
async def test_slow_ev_reports_keep_original_freshness_without_a_second_ev_window():
    manager, _, clock, _, row = await ended_request()
    end = clock()
    clock.advance(1)
    original_ev_stamp = end-29
    await usable(manager, clock, row, source_stamp=original_ev_stamp)
    for elapsed in (30, 60):
        clock.advance(30)
        await usable(manager, clock, row, source_stamp=original_ev_stamp)
        assert manager._usable_solar_observation["stamp"] == original_ev_stamp
        assert manager.completion_hold
    clock.advance(30)
    next_ev_stamp = clock()
    await usable(manager, clock, row, source_stamp=next_ev_stamp)
    clock.advance(30)
    await usable(manager, clock, row, source_stamp=next_ev_stamp)
    assert manager.owned and manager._session_started == end+121


@pytest.mark.asyncio
async def test_elapsed_time_without_a_new_p1_report_cannot_finish_confirmation():
    manager, _, clock, _, row = await ended_request()
    clock.advance(1)
    stamp = clock()
    await usable(manager, clock, row, source_stamp=stamp, report_stamp=stamp)
    await window(manager, clock, row, source_stamp=stamp, report_stamp=stamp)
    assert manager.completion_hold and manager._usable_candidate["reports"] == 1
    clock.advance(1)
    await usable(manager, clock, row)
    assert manager.owned


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["missing", "false", "watts_bool", "watts_nan", "watts_inf", "watts_string",
    "watts_negative", "stamp_bool", "stamp_future", "stamp_stale", "report_missing", "report_bool",
    "report_before_source", "identity_empty", "identity_none", "different_pool"])
async def test_unusable_pool_never_becomes_a_zero_or_new_request(change):
    manager, adapter, clock, _, row = await ended_request()
    clock.advance(1)
    value = {"valid": True, "watts": 4000, "stamp": clock(), "report_stamp": clock(),
             "source_identity": SOURCE}
    if change == "missing":
        value = {}
    elif change == "false":
        value["valid"] = False
    elif change.startswith("watts_"):
        value["watts"] = {"watts_bool": True, "watts_nan": float("nan"), "watts_inf": float("inf"),
            "watts_string": "4000", "watts_negative": -1}[change]
    elif change.startswith("stamp_"):
        value["stamp"] = {"stamp_bool": True, "stamp_future": clock()+6, "stamp_stale": clock()-121}[change]
    elif change.startswith("report_"):
        value["report_stamp"] = {"report_missing": None, "report_bool": True,
                                  "report_before_source": clock()-1}[change]
    elif change.startswith("identity_"):
        value["source_identity"] = () if change == "identity_empty" else None
    else:
        value["watts"] = 5000
    await usable(manager, clock, row, observation=value)
    assert manager._usable_solar_observation is None
    assert manager._usable_candidate is None and manager.completion_hold and not manager.owned
    assert len(adapter.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("stop", ["native_completed", "no_uptake", "profile_changed"])
async def test_current_solar_does_not_override_verified_physical_completion(stop):
    manager, adapter, clock, _, row = await ended_request()
    manager._hold_reason = stop
    clock.advance(1000)
    await usable(manager, clock, row)
    await window(manager, clock, row)
    assert manager.completion_hold and not manager.owned and len(adapter.calls) == 2
    assert manager._usable_candidate is None


@pytest.mark.asyncio
async def test_legacy_beta110_session_limit_with_full_provenance_can_replace_request_rest(monkeypatch):
    site = await ended_site(monkeypatch)
    runtime, hass, previous, adapter, clock = site
    assert previous._hold_reason == "session_limit"
    saved = previous.snapshot()
    saved["request_rest_policy"] = "protected"
    saved.pop("request_rest_schema")
    saved.pop("legacy_session_limit_rest")
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = manager
    manager.restore(saved)
    updated = (runtime, hass, manager, adapter, clock)
    await site_step(updated, advance=1)
    assert manager._legacy_session_limit_rest and manager._request_rest_proven()
    for _ in range(4):
        await site_step(updated, advance=30)
    assert manager.owned and not manager.completion_hold
    assert manager._last_rearm["request_rest_replaced_s"] > 700


@pytest.mark.asyncio
async def test_first_automatic_start_rechecks_a_source_rebound_during_its_storage(monkeypatch):
    site = live_site(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    await site_step(site)
    original = runtime.store.async_save
    rebound = False

    async def replaced_source(data):
        nonlocal rebound
        await original(data)
        if manager._usable_rearm_proof is not None and not rebound:
            rebound = True
            report(hass, clock, "sensor.rebound_pv", 4890, {"unit_of_measurement": "W"})
            runtime.settings["pv_entity"] = "sensor.rebound_pv"

    monkeypatch.setattr(runtime.store, "async_save", replaced_source)
    for _ in range(4):
        await site_step(site, advance=30)
    assert rebound and not manager.owned and adapter.calls == []
    assert manager._stable_since is None and manager._usable_rearm_proof is None
    for _ in range(5):
        clock.advance(30)
        report(hass, clock, "sensor.rebound_pv", 4890, {"unit_of_measurement": "W"})
        await site_step(site)
    assert manager.owned and len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_initial_pool_below_total_can_still_use_its_configured_start_threshold(monkeypatch):
    site = live_site(monkeypatch, grid=0, pv=3200, hp=0, ev=2800)
    runtime, hass, manager, adapter, clock = site
    await site_step(site, grid=0, pv=3200, hp=0, ev=2800)
    for _ in range(4):
        await site_step(site, advance=30, grid=0, pv=3200, hp=0, ev=2800)
    assert runtime.sg_usable_solar_observation()["watts"] == 2650
    assert manager.owned and adapter.calls == [("on", 300)]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_continuous_overview_uses_current_proof_after_the_original_maximum(monkeypatch):
    site = await started_site(monkeypatch, maximum=300)
    runtime, hass, manager, adapter, clock = site
    origin, command = manager._session_started, manager._session_provenance["command_identity"]
    for _ in range(20):
        await site_step(site, advance=30)
    view = manager.overview()
    assert clock()-origin > 300 and view["continuous_solar"]
    assert view["remaining_s"] is None
    assert clock() < view["continuous_solar_valid_until"] <= clock()+manager.settings["stale_s"]
    assert view["minimum_valid_until"] > clock()
    assert view["cloud_valid_until"] > clock()
    checkpoint = manager.snapshot()["session_checkpoint"]
    assert checkpoint["continuous_solar"] is True
    assert checkpoint["started_at"] == origin
    assert checkpoint["session_provenance"]["command_identity"] == command
    assert all(command == "on" and lease <= 300 for command, lease in adapter.calls)


@pytest.mark.asyncio
async def test_explicit_manual_request_keeps_its_original_hard_maximum_with_current_solar(monkeypatch):
    site = live_site(monkeypatch, maximum=300)
    runtime, hass, manager, adapter, clock = site
    await manager.start()
    await manager.set_manual_control("on", 1800)
    await site_step(site)
    assert manager.owned and manager._session_provenance["request_mode"] == "manual_on"
    origin = manager._session_started
    for _ in range(9):
        await site_step(site, advance=30)
        assert not manager.overview()["continuous_solar"]
    await site_step(site, advance=30)
    assert clock()-origin == 300 and not manager.owned and not adapter.on
    assert manager.completion_hold and manager._hold_reason == "session_limit"
    assert adapter.calls == [("on", 300-manager.settings["ack_timeout_s"])]  # Native expiry needs no new ON.


@pytest.mark.asyncio
async def test_first_deficit_during_renewal_storage_is_saved_before_any_new_lease(monkeypatch):
    site = await started_site(monkeypatch, maximum=300)
    runtime, hass, manager, adapter, clock = site
    for _ in range(20):
        await site_step(site, advance=30)
    before, original_expiry = list(adapter.calls), manager._lease_expiry
    save = runtime.store.async_save
    changed = False

    async def cloudy_after_save(data):
        nonlocal changed
        await save(data)
        if manager._in_flight and manager.owned and not changed:
            changed = True
            sources(runtime, hass, clock, grid=100, pv=0, hp=0, ev=0)

    monkeypatch.setattr(runtime.store, "async_save", cloudy_after_save)
    await site_step(site, advance=60)
    assert changed and manager.owned and manager.desired_on and adapter.on
    assert adapter.calls == before and manager._lease_expiry == original_expiry
    assert manager._joint_solar_deficit is not None and not manager._joint_solar_needs_save
    deadline = manager._joint_solar_deficit["deadline"]
    saved = manager.snapshot()
    assert saved["session_checkpoint"]["joint_solar_deficit"]["deadline"] == deadline
    await site_step(site, advance=30, grid=100, pv=0, hp=0, ev=0)
    assert manager.owned and manager._lease_expiry <= deadline
    assert manager._joint_solar_deficit["deadline"] == deadline
    assert all(command == "on" for command, _ in adapter.calls)


def test_p1_novelty_keeps_its_original_timestamp_with_a_slower_battery_report(monkeypatch):
    runtime, hass, _, _, clock = live_site(monkeypatch)
    runtime.settings["battery_power_entity"] = "sensor.fixture_battery"
    report(hass, clock, "sensor.fixture_battery", 0, {"unit_of_measurement": "W"}, age=90)
    observation = runtime.sg_usable_solar_observation()
    assert observation["valid"]
    assert observation["stamp"] == clock()-90
    assert observation["report_stamp"] == clock()


@pytest.mark.asyncio
async def test_real_automatic_solar_starts_and_continues_with_a_short_manual_scope_maximum(monkeypatch):
    site = await started_site(monkeypatch, maximum=300)
    runtime, hass, manager, adapter, clock = site
    origin = manager._session_started
    assert adapter.calls == [("on", manager.settings["lease_s"])]
    for _ in range(20):
        await site_step(site, advance=30)
        assert manager.owned and manager._session_started == origin
        assert manager.overview()["continuous_solar"]
    assert clock()-origin > 300
    assert all(command == "on" and lease == 300 for command, lease in adapter.calls)
    assert manager._last_session is None and not hass.services.calls
