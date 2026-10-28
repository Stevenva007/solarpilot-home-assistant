"""Independent SG solar-pool and final-dispatch regressions with fictitious meters."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from custom_components.solar_pilot import heatpump_budget, runtime as runtime_module
from custom_components.solar_pilot.sg_boost import SGBoostManager
from custom_components.solar_pilot.sg_transport import ShellyLeaseError
from test_sg_transfer_integration108 import environment, report, sources
from test_sg_transport62 import native, writes


def live_site(monkeypatch, *, grid=-39, pv=4890, hp=2590, ev=1510, maximum=3600):
    runtime, hass, manager, adapter, clock = environment(monkeypatch, min_session_s=0)
    config = {**manager.settings, "profile": "general", "profile_confirmed": True,
        "cooling_protection_confirmed": True, "expected_power_w": 3000,
        "threshold_w": 2500, "start_delay_s": 120, "max_session_s": maximum,
        "rest_s": 900, "min_session_s": 0}
    runtime.entry.options["sg_boost"] = deepcopy(config)
    manager.update_config(config)
    runtime.panasonic.update_config(config)
    # Actual transport binds a fixed physical output. The deterministic adapter
    # needs the same explicit evidence for ended-request reassessment rights.
    original = adapter.status
    adapter.status = lambda: {**original(), "binding_identity": "a"*64}
    runtime.entry.options["priority_board"]["order"] = ["wallbox", "dhw_extra", "device:a"]
    sources(runtime, hass, clock, grid=grid, pv=pv, hp=hp, ev=ev)
    return runtime, hass, manager, adapter, clock


async def site_step(site, *, advance=0, grid=-39, pv=4890, hp=2590, ev=1510):
    runtime, hass, manager, adapter, clock = site
    clock.advance(advance)
    sources(runtime, hass, clock, grid=grid, pv=pv, hp=hp, ev=ev)
    await runtime._tick()
    return manager


async def started_site(monkeypatch, *, maximum=3600):
    site = live_site(monkeypatch, maximum=maximum)
    await site_step(site)
    for _ in range(5):
        await site_step(site, advance=30)
        if site[2].owned:
            break
    assert site[2].owned and site[3].on
    return site


async def ended_site(monkeypatch):
    """Restore the real bounded-OFF journal an installed beta.110 could leave."""
    site = live_site(monkeypatch, maximum=300)
    runtime, hass, manager, adapter, clock = site
    await site_step(site)
    for _ in range(30):
        await site_step(site, advance=30)
        if manager.owned and clock()-manager._session_started >= 300:
            break
    assert manager.owned
    # Reproduce the old controller's physical bounded stop, keeping its actual
    # provenance and confirmed OFF. New beta.111 must not cause this stop itself.
    manager._session_provenance["release"] = "1.0.0-beta.110"
    manager.completion_hold = True
    manager._hold_reason = "session_limit"
    manager._capture_need_reference()
    await manager._release("Begrensde SG-sessieduur bereikt", rest=True, policy_hold=False)
    saved = manager.snapshot()
    saved.pop("request_rest_schema", None)
    saved.pop("legacy_session_limit_rest", None)
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    restored.restore(saved)
    manager = restored
    assert manager.completion_hold and not manager.owned and adapter.on is False
    assert manager._hold_reason == "session_limit"
    return runtime, hass, manager, adapter, clock


def test_current_hp_and_ev_pool_qualifies_without_physical_export(monkeypatch):
    runtime, hass, _, _, _ = live_site(monkeypatch)
    budget = sg_solar_budget(runtime)
    assert budget["valid"] and budget["available_w"] == 0
    assert budget["hp_power_w"] == 2590
    assert budget["ev_solar_w"] == 1510
    assert budget["eligible_w"] == 3989
    assert runtime.priority_board.sg_before_wallbox()
    assert not hass.services.calls


def test_large_current_ev_is_not_capped_before_import_is_paid(monkeypatch):
    runtime, hass, _, _, _ = live_site(monkeypatch, grid=1500, pv=5500, hp=0, ev=5150)
    budget = sg_solar_budget(runtime)
    assert budget["available_w"] == 0
    assert budget["ev_solar_w"] == 5150
    assert budget["eligible_w"] == 3500  # 5150 - 1500 actual import - 150 margin.
    assert not hass.services.calls


def test_fixed_sg_pair_does_not_reorder_ordinary_appliances_or_saved_user_rows(monkeypatch):
    runtime, hass, _, _, clock = live_site(monkeypatch)
    board = deepcopy(runtime.entry.options["priority_board"])
    policy = runtime.wallbox_priority
    journal = policy._empty()
    journal["targets"]["dhw_extra"] = {"option": "until_auto", "created_at": clock()-1,
        "expires_at": None, "binding": "old-sg-choice"}
    journal["targets"]["device:a"] = {"option": "until_auto", "created_at": clock()-1,
        "expires_at": None, "binding": policy.eligible()["device:a"]}
    policy.restore(journal, wall=clock())
    assert not policy.active("dhw_extra") and policy.active("device:a")
    assert runtime.priority_board.sg_before_wallbox()
    assert runtime.priority_board.effective_config("a")["_priority_board_before_wallbox"] is False
    assert sg_solar_budget(runtime)["ev_solar_w"] == 1510
    assert runtime.entry.options["priority_board"] == board
    assert not hass.services.calls


@pytest.mark.parametrize("issue", ["manual", "stopped", "stale", "future", "missing", "incoherent"])
def test_unproven_ev_cannot_rearm_from_its_remembered_charging_watts(monkeypatch, issue):
    runtime, hass, _, _, clock = live_site(monkeypatch)
    if issue == "manual":
        report(hass, clock, "sensor.fixture_session", "Manueel laden")
    elif issue == "stopped":
        report(hass, clock, "sensor.fixture_session", "Laden gestopt")
    elif issue in ("stale", "future"):
        report(hass, clock, "sensor.public_ev_power", 1510, {"unit_of_measurement": "W"},
               age=121 if issue == "stale" else -6)
    elif issue == "missing":
        report(hass, clock, "sensor.public_ev_power", "unavailable", {"unit_of_measurement": "W"})
    else:
        report(hass, clock, "sensor.public_ev_power", 7000, {"unit_of_measurement": "W"})
    budget = sg_solar_budget(runtime)
    assert budget["ev_solar_w"] == 0
    assert budget["eligible_w"] == 2479 < 3000
    assert budget["available_w"] == 0
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["phase", "quarter", "fault", "battery", "site", "ev", "binding"])
async def test_fresh_pool_does_not_override_a_changed_final_native_preflight(monkeypatch, native, change):
    runtime, hass, _, _, clock = live_site(monkeypatch)
    assert runtime.sg_dispatch_allowed(automatic=True)
    native.adapter.before_on = lambda: runtime.sg_dispatch_allowed(automatic=True)
    native.device.pause_read = asyncio.Event()
    native.device.release_read = asyncio.Event()
    pending = asyncio.create_task(native.adapter.set_on(300))
    await asyncio.wait_for(native.device.pause_read.wait(), timeout=2)
    if change == "phase":
        runtime.phase_settings.update(enabled=True, control_starts=True, limit_w=4000,
            phase_1_entity="sensor.fictional_phase1", phase_2_entity="sensor.fictional_phase2",
            phase_3_entity="sensor.fictional_phase3")
        for n in (1, 2, 3):
            report(hass, clock, f"sensor.fictional_phase{n}", 3900, {"unit_of_measurement": "W"})
    elif change == "quarter":
        runtime.capacity_settings.update(enabled=True, average_demand_entity="sensor.fictional_quarter")
        report(hass, clock, "sensor.fictional_quarter", "unavailable", {"unit_of_measurement": "W"})
    elif change == "fault":
        runtime.faults["a"] = "Fictional unresolved command"
    elif change == "battery":
        runtime.settings["battery_power_entity"] = "sensor.fictional_battery"
        report(hass, clock, "sensor.fictional_battery", 100, {"unit_of_measurement": "W"})
    elif change == "site":
        runtime.settings["grid_entity"] = "sensor.fictional_missing_grid"
    elif change == "ev":
        report(hass, clock, "sensor.fixture_session", "Manueel laden")
    else:
        native.entry.config_entry_id = "fictional-replaced-binding"
    native.device.release_read.set()
    with pytest.raises(ShellyLeaseError):
        await pending
    assert writes(native) == [] and not hass.services.calls


@pytest.mark.asyncio
async def test_three_hours_of_current_solar_keeps_one_original_request_without_off_cycles(monkeypatch):
    site = live_site(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    origin = command = sequence = None
    await site_step(site)
    # Current solar may retain the same request beyond the historical hourly
    # maximum. Every actual renewal still needs its short local lease.
    for _ in range((3*3600+600)//30):
        await site_step(site, advance=30)
        budget = sg_solar_budget(runtime)
        assert budget["available_w"] == 0 and budget["eligible_w"] == 3989
        if origin is None and manager.owned:
            origin = manager._session_started
            command = manager._session_provenance["command_identity"]
            sequence = manager._session
        if origin is not None:
            assert manager.owned and manager.desired_on and adapter.on
            assert manager._session_started == origin and manager._session == sequence
            assert manager._session_provenance["command_identity"] == command
            assert clock() < manager._lease_deadline <= clock()+300
    assert clock()-origin > 3*3600
    assert len(adapter.calls) > 100 and all(command == "on" for command, _ in adapter.calls)
    assert not manager.manual_hold and not manager.fault
    assert manager._last_session is None
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_rebinding_a_valid_source_during_rearm_storage_requires_a_whole_new_window(monkeypatch):
    site = await ended_site(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    before = list(adapter.calls)
    original_save = runtime.store.async_save
    changed = False

    async def rebound_after_save(data):
        nonlocal changed
        await original_save(data)
        if not changed and manager._usable_rearm_proof is not None and not manager.owned:
            changed = True
            report(hass, clock, "sensor.fictional_rebound_pv", 4890, {"unit_of_measurement": "W"})
            runtime.settings["pv_entity"] = "sensor.fictional_rebound_pv"

    monkeypatch.setattr(runtime.store, "async_save", rebound_after_save)
    for _ in range(5):
        await site_step(site, advance=30)
    assert changed and not manager.owned and adapter.calls == before
    assert manager._usable_rearm_proof is None
    # The rebound source remains fully valid; only the completed window was
    # revoked. A new complete normal start window can qualify it again.
    for _ in range(5):
        clock.advance(30)
        sources(runtime, hass, clock, grid=-39, pv=4890, hp=2590, ev=1510)
        report(hass, clock, "sensor.fictional_rebound_pv", 4890, {"unit_of_measurement": "W"})
        await runtime._tick()
    assert manager.owned and len(adapter.calls) == len(before)+1
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_restart_drops_partial_rearm_progress_and_does_not_create_on_proof(monkeypatch):
    site = await ended_site(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    await site_step(site, advance=30)
    await site_step(site, advance=30)
    assert manager._usable_candidate is not None
    before = list(adapter.calls)
    saved = manager.snapshot()
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    restored.restore(saved)
    assert restored._usable_candidate is None and restored._usable_rearm_proof is None
    restored_site = (runtime, hass, restored, adapter, clock)
    await site_step(restored_site, advance=30)
    await site_step(restored_site, advance=90)
    assert not restored.owned and adapter.calls == before
    # A ninety-second observation gap cannot finish a two-minute proof.
    for _ in range(4):
        await site_step(restored_site, advance=30)
    assert restored.owned and len(adapter.calls) == len(before)+1


@pytest.mark.asyncio
async def test_wall_clock_rollback_discards_partial_rearm_evidence(monkeypatch):
    site = await ended_site(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    await site_step(site, advance=30)
    await site_step(site, advance=30)
    assert manager._usable_candidate is not None
    before = list(adapter.calls)
    wall = manager._wall_clock
    manager._wall_clock = lambda: clock()-10
    await site_step(site, advance=30)
    assert manager._usable_candidate is None and not manager.owned
    assert adapter.calls == before
    manager._wall_clock = wall
    for _ in range(4):
        await site_step(site, advance=30)
    assert not manager.owned and adapter.calls == before
    await site_step(site, advance=30)
    assert manager.owned and len(adapter.calls) == len(before)+1


@pytest.mark.asyncio
async def test_changed_policy_cannot_replace_old_rest_but_can_start_after_rest_and_new_proof(monkeypatch):
    site = await ended_site(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    old_policy = manager._last_session["policy_hash"]
    rest_deadline = manager._rest_until
    old_calls = list(adapter.calls)
    config = {**manager.settings, "threshold_w": 2600}
    runtime.entry.options["sg_boost"] = deepcopy(config)
    manager.update_config(config)
    runtime.panasonic.update_config(config)
    while clock()+30 < rest_deadline:
        await site_step(site, advance=30)
        assert manager.completion_hold and not manager.owned
        assert adapter.calls == old_calls
    await site_step(site, advance=rest_deadline-clock())
    assert not manager.owned
    for _ in range(5):
        await site_step(site, advance=30)
    assert manager.owned and manager._session_provenance["policy_hash"] != old_policy
    assert clock() <= rest_deadline+manager.settings["start_delay_s"]+30
    assert len(adapter.calls) == len(old_calls)+1 and not hass.services.calls


@pytest.mark.asyncio
async def test_night_stops_after_bounded_solar_deficit_even_below_raw_import_cloud_threshold(monkeypatch):
    site = await started_site(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    original = manager._session_started
    await site_step(site, grid=100, pv=0, hp=0, ev=0)
    for _ in range(9):
        await site_step(site, advance=30, grid=100, pv=0, hp=0, ev=0)
        assert manager.owned and manager._session_started == original
    await site_step(site, advance=29, grid=100, pv=0, hp=0, ev=0)
    assert manager.owned
    await site_step(site, advance=1, grid=100, pv=0, hp=0, ev=0)
    assert not manager.owned and not adapter.on
    assert manager._import_since is None or manager._import_observation["watts"] == 100
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_unknown_site_source_cannot_renew_a_long_running_request(monkeypatch):
    site = await started_site(monkeypatch, maximum=300)
    runtime, hass, manager, adapter, clock = site
    for _ in range(20):
        await site_step(site, advance=30)
    assert manager.owned and clock()-manager._session_started > 300
    calls = list(adapter.calls)
    clock.advance(60)
    sources(runtime, hass, clock, grid=-39, pv=4890, hp=2590, ev=1510)
    report(hass, clock, "sensor.public_pv", "unavailable", {"unit_of_measurement": "W"})
    await runtime._tick()
    assert not any(command == "on" for command, _ in adapter.calls[len(calls):])
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("current_pool", [True, False])
async def test_restart_beyond_old_maximum_requires_current_pool_before_adopting_same_live_lease(monkeypatch, current_pool):
    site = await started_site(monkeypatch, maximum=300)
    runtime, hass, manager, adapter, clock = site
    for _ in range(20):
        await site_step(site, advance=30)
    assert manager.owned and clock()-manager._session_started > 300
    original, expiry = manager._session_started, manager._lease_expiry
    saved = manager.snapshot()
    assert saved["session_checkpoint"] is not None
    calls = list(adapter.calls)
    clock.advance(15)
    sources(runtime, hass, clock, grid=-39, pv=4890, hp=2590 if current_pool else 0,
            ev=1510 if current_pool else 0)
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    restored.restore(saved)
    assert not restored.owned and not restored.desired_on
    await restored.start()
    await runtime._tick()
    if current_pool:
        assert restored.owned and restored._session_started == original
        assert restored._lease_expiry == expiry and adapter.calls == calls
    else:
        assert not restored.owned
        assert not any(command == "on" for command, _ in adapter.calls[len(calls):])
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_restart_during_solar_deficit_cannot_purchase_a_new_cloud_window(monkeypatch):
    site = await started_site(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    began = clock()
    deadline = began+manager.settings["stop_delay_s"]
    await site_step(site, grid=100, pv=0, hp=0, ev=0)
    for _ in range(4):
        await site_step(site, advance=30, grid=100, pv=0, hp=0, ev=0)
    saved = manager.snapshot()
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    restored.restore(saved)
    restored_site = (runtime, hass, restored, adapter, clock)
    for _ in range(7):
        before = len(adapter.calls)
        await site_step(restored_site, advance=30, grid=100, pv=0, hp=0, ev=0)
        if any(command == "on" for command, _ in adapter.calls[before:]):
            assert restored._lease_expiry <= deadline
    assert clock() > deadline and not restored.owned and not adapter.on
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_live_wall_rollback_and_backdated_low_pool_reports_do_not_extend_deficit(monkeypatch):
    site = await started_site(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    began = clock()
    deadline = began+manager.settings["stop_delay_s"]
    await site_step(site, grid=100, pv=0, hp=0, ev=0)
    await site_step(site, advance=60, grid=100, pv=0, hp=0, ev=0)
    shifted_wall = lambda: clock()-90
    manager._wall_clock = shifted_wall
    shifted_time = SimpleNamespace(time=shifted_wall, monotonic=clock)
    monkeypatch.setattr(runtime_module, "time", shifted_time)
    monkeypatch.setattr(heatpump_budget, "time", shifted_time)
    for _ in range(9):
        clock.advance(30)
        sources(runtime, hass, shifted_wall, grid=100, pv=0, hp=0, ev=0)
        before = len(adapter.calls)
        await runtime._tick()
        if any(command == "on" for command, _ in adapter.calls[before:]):
            assert manager._lease_expiry <= deadline
    assert clock() > deadline and not manager.owned and not adapter.on
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_replayed_sunny_reports_cannot_erase_a_later_low_pool_deadline(monkeypatch):
    site = await started_site(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    sunny_stamp = clock()
    await site_step(site, advance=10, grid=100, pv=0, hp=0, ev=0)
    clock.advance(60)
    # Still within source-age limits, but older than the observed deficit.
    sources(runtime, hass, lambda: sunny_stamp, grid=-39, pv=4890, hp=2590, ev=1510)
    before = len(adapter.calls)
    await runtime._tick()
    assert not any(command == "on" for command, _ in adapter.calls[before:])
    assert not manager.owned or manager._joint_solar_deficit is not None
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_first_deficit_during_native_renewal_preflight_is_saved_before_any_later_on(monkeypatch, native):
    runtime, hass, manager, _, clock = live_site(monkeypatch)
    manager._adapter = native.adapter
    # The native protocol fixture intentionally has no UI entity registry.
    runtime.entity_id = lambda *_args, **_kwargs: ""
    # Exercise the production Shelly callback protocol from the first ON.
    for i in range(5):
        if i:
            clock.advance(30)
        sources(runtime, hass, clock, grid=-39, pv=4890, hp=2590, ev=1510)
        native.device.clock = clock()
        await runtime._tick()
    assert manager.owned and native.device.output
    initial_writes = writes(native)
    expiry = manager._lease_expiry
    paused, release = asyncio.Event(), asyncio.Event()
    original_rpc = native.device.call_rpc

    async def pause_final_read(method, params=None, timeout=None):
        if method == "Switch.GetStatus" and manager._in_flight and not paused.is_set():
            paused.set()
            await release.wait()
        return await original_rpc(method, params=params, timeout=timeout)

    native.device.call_rpc = pause_final_read
    clock.advance(60)
    sources(runtime, hass, clock, grid=-39, pv=4890, hp=2590, ev=1510)
    native.device.clock = clock()
    pending = asyncio.create_task(runtime._tick())
    await asyncio.wait_for(paused.wait(), timeout=2)
    sources(runtime, hass, clock, grid=100, pv=0, hp=0, ev=0)
    release.set()
    await pending
    assert writes(native) == initial_writes
    assert manager.owned and manager.desired_on and manager._lease_expiry == expiry
    checkpoint = runtime.store.data["sg_boost"]["session_checkpoint"]
    deficit = checkpoint["joint_solar_deficit"]
    assert deficit["started_at"] == clock()
    deadline = deficit["deadline"]
    clock.advance(30)
    native.device.clock = clock()
    sources(runtime, hass, clock, grid=100, pv=0, hp=0, ev=0)
    await runtime._tick()
    assert manager.owned and manager._lease_expiry <= deadline
    assert all(params["on"] is True for _, params in writes(native))
    assert not hass.services.calls and not native.hass.services.calls
