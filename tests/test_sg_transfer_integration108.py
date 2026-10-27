"""Actual SG/runtime dispatch with a delayed, read-only fictional solar EV.

The software limit may bridge a bounded EV reaction; independent electrical
limits and original source clocks remain real inputs, never adjusted P1.
"""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from types import MappingProxyType, SimpleNamespace
import time

import pytest

from custom_components.solar_pilot import heatpump_budget, runtime as runtime_module
from custom_components.solar_pilot.sg_boost import SGBoostManager
from custom_components.solar_pilot.sg_transport import ShellyLeaseError
from test_priority106 import solar_wallbox
from test_sg_controller62 import Adapter, Clock, tick
from test_sg_transport62 import native, writes


def report(hass, clock, entity, state, attrs=None, *, age=0):
    hass.states.set(entity, state, attrs)
    obj = hass.states.get(entity)
    stamp = datetime.fromtimestamp(clock()-age, timezone.utc)
    obj.last_reported = obj.last_updated = stamp


def sources(runtime, hass, clock, *, grid=0, pv=8000, ev=4000, hp=0):
    for entity, watts in (("sensor.grid", grid), ("sensor.public_pv", pv),
                          ("sensor.public_ev_power", ev), ("sensor.public_hp", hp)):
        report(hass, clock, entity, watts, {"unit_of_measurement": "W"})
    report(hass, clock, "sensor.public_ev_status", "Charging")
    report(hass, clock, "select.public_ev_solar", "full_solar")
    report(hass, clock, "sensor.fixture_session", "Zonne-auto · laden")
    report(hass, clock, "switch.load", "off")
    report(hass, clock, "sensor.load", 0, {"unit_of_measurement": "W"})
    runtime.filtered = None


def environment(monkeypatch, *, limit=4000, min_session_s=1200, stop_delay_s=300, data_loaded=True):
    clock = Clock()
    clock.value = float(int(time.time()))
    fake_time = SimpleNamespace(time=clock, monotonic=clock)
    monkeypatch.setattr(runtime_module, "time", fake_time)
    monkeypatch.setattr(heatpump_budget, "time", fake_time)
    runtime, hass = solar_wallbox()
    runtime.last_tick = clock()
    runtime.data_loaded = data_loaded
    runtime.settings.update(settle_s=0, filter_s=0, max_import_w=limit)
    runtime.device_modes["a"] = "manual"
    state = runtime.states["a"]
    state.owned = state.on = state.enabled = False
    runtime.entry.options["sg_boost"].update(min_session_s=min_session_s, stop_delay_s=stop_delay_s)
    adapter = Adapter(clock)
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = manager
    sources(runtime, hass, clock)
    return runtime, hass, manager, adapter, clock


async def running(monkeypatch, **settings):
    runtime, hass, manager, adapter, clock = environment(monkeypatch, **settings)
    await runtime._observe_sg_wallbox_transfer()
    await tick(manager)
    clock.advance(15)
    sources(runtime, hass, clock)
    await runtime._observe_sg_wallbox_transfer()
    clock.advance(15)
    sources(runtime, hass, clock)
    await tick(manager)
    assert manager.owned and manager.desired_on and adapter.on
    assert adapter.calls == [("on", 300)]
    assert runtime.sg_wallbox_transfer.snapshot()["armed"] is True
    return runtime, hass, manager, adapter, clock


async def spike(runtime, hass, clock, *, grid=4200, **kwargs):
    sources(runtime, hass, clock, grid=grid, **kwargs)
    await runtime._tick()


@pytest.mark.asyncio
async def test_later_cloud_spike_keeps_sg_while_wallbox_reacts_and_recovers(monkeypatch):
    runtime, hass, manager, adapter, clock = await running(monkeypatch)
    # A later spike, not just the initial SG switch-on, gets its own window.
    clock.advance(20)
    await spike(runtime, hass, clock)
    first = runtime.sg_wallbox_transfer_overview()
    assert first["applicable"] is True and first["remaining_s"] == 240
    assert first["eligible_w"] == 2500
    assert runtime.grid_w == manager._import_observation["watts"] == 4200
    assert manager._import_since == clock()  # The raw 600 W cloud timer still runs.
    assert manager.minimum_hold_active and manager.owned and adapter.on
    assert all(command == "on" for command, _lease in adapter.calls)
    deadline = first["expires_at"]
    clock.advance(30)
    await spike(runtime, hass, clock, grid=0, ev=2000)
    assert manager.owned and adapter.on and manager._import_since is None
    assert runtime.sg_wallbox_transfer.overview(now=clock(), wall=clock())["expires_at"] == deadline
    clock.advance(15)
    await spike(runtime, hass, clock, grid=0, ev=2000)
    assert runtime.sg_wallbox_transfer.snapshot()["episode"] is None
    assert all(command == "on" for command, _lease in adapter.calls)
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_continuous_overload_stops_at_reaction_deadline_despite_minimum(monkeypatch):
    runtime, hass, manager, adapter, clock = await running(monkeypatch)
    clock.advance(5)
    await spike(runtime, hass, clock)
    began = manager._import_since
    deadline = runtime.sg_wallbox_transfer_overview()["expires_at"]
    for delay in (60, 60, 60, 59):
        clock.advance(delay)
        await spike(runtime, hass, clock)
        assert manager.owned and manager.minimum_hold_active
        assert manager._import_since == began
        assert runtime.sg_wallbox_transfer_overview()["expires_at"] == deadline
    clock.advance(1)
    await spike(runtime, hass, clock)
    assert not manager.owned and not adapter.on
    assert adapter.calls[-1] == ("off", None)
    assert manager._last_session["reason"].startswith("Netgrens overschreden:")
    assert manager._last_session["duration_s"] < 1200
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_overload_above_current_ev_credit_is_not_buffered(monkeypatch):
    runtime, hass, manager, adapter, clock = await running(monkeypatch)
    clock.advance(5)
    await spike(runtime, hass, clock, grid=6501)
    assert not manager.owned and not adapter.on
    assert adapter.calls[-1] == ("off", None)
    assert not runtime._sg_net_limit_allowed(6501)
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["higher_wallbox", "manual_session", "unknown_status", "stale_ev", "incoherent_ev"])
async def test_an_active_window_loses_permission_when_ev_proof_or_order_changes(monkeypatch, change):
    runtime, hass, manager, _adapter, clock = await running(monkeypatch)
    clock.advance(5)
    await spike(runtime, hass, clock)
    assert runtime.sg_dispatch_allowed(renewal=True)
    deadline = runtime.sg_wallbox_transfer_overview()["expires_at"]
    if change == "higher_wallbox":
        runtime.entry.options["priority_board"]["order"] = ["wallbox", "dhw_extra", "device:a"]
    elif change == "manual_session":
        report(hass, clock, "sensor.fixture_session", "Manueel laden")
    elif change == "unknown_status":
        report(hass, clock, "sensor.public_ev_status", "unknown")
    elif change == "stale_ev":
        report(hass, clock, "sensor.public_ev_power", 4000, {"unit_of_measurement": "W"}, age=121)
    else:
        report(hass, clock, "sensor.public_ev_power", 15000, {"unit_of_measurement": "W"})
    assert not runtime.sg_dispatch_allowed(renewal=True)
    assert runtime.sg_wallbox_transfer_overview()["expires_at"] == deadline
    assert manager._import_observation["watts"] == 4200
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["phase", "quarter", "battery"])
async def test_real_final_dispatch_keeps_independent_raw_electrical_guards(monkeypatch, guard):
    runtime, hass, _manager, _adapter, clock = await running(monkeypatch)
    clock.advance(5)
    await spike(runtime, hass, clock)
    assert runtime.sg_dispatch_allowed(renewal=True)
    if guard == "phase":
        runtime.phase_settings.update(enabled=True, control_starts=True, limit_w=4000,
            phase_1_entity="sensor.fixture_phase1", phase_2_entity="sensor.fixture_phase2",
            phase_3_entity="sensor.fixture_phase3")
        for n, watts in ((1, 4500), (2, 0), (3, 0)):
            report(hass, clock, f"sensor.fixture_phase{n}", watts, {"unit_of_measurement": "W"})
    elif guard == "quarter":
        runtime.capacity_settings.update(enabled=True, target_peak_w=4000, margin_w=0,
            respect_billing_floor=False, adaptive_to_month_peak=False, minimum_elapsed_s=0,
            average_demand_entity="sensor.fixture_average", monthly_peak_entity="sensor.fixture_peak")
        for entity in ("sensor.fixture_average", "sensor.fixture_peak"):
            report(hass, clock, entity, 4000, {"unit_of_measurement": "W"})
    else:
        runtime.settings["battery_power_entity"] = "sensor.fixture_battery"
        report(hass, clock, "sensor.fixture_battery", 300, {"unit_of_measurement": "W"})
    # The signature change itself also invalidates a transfer. Prove the
    # independent final electrical rejection, rather than relying on net denial.
    runtime._sg_net_limit_allowed = lambda *_args, **_kwargs: True
    assert not runtime.sg_dispatch_allowed(renewal=True)
    assert runtime._sg_dispatch_rejection["code"] == {
        "phase": "phase_limit", "quarter": "capacity_limit", "battery": "battery_discharge"}[guard]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_snapshot_restore_keeps_absolute_window_and_does_not_restart_it(monkeypatch):
    runtime, hass, manager, _adapter, clock = await running(monkeypatch)
    clock.advance(5)
    await spike(runtime, hass, clock)
    before = runtime.sg_wallbox_transfer_overview()
    saved = deepcopy(runtime._snapshot()["sg_wallbox_transfer"])
    assert saved == runtime.store.data["sg_wallbox_transfer"]
    clock.advance(70)
    sources(runtime, hass, clock, grid=4200)
    restored = type(runtime.sg_wallbox_transfer)()
    restored.restore(saved)
    runtime.sg_wallbox_transfer = restored
    await runtime._observe_sg_wallbox_transfer()
    view = runtime.sg_wallbox_transfer_overview()
    assert view["expires_at"] == before["expires_at"]
    assert view["remaining_s"] == 170
    assert runtime.sg_dispatch_allowed(renewal=True)
    assert manager.owned and not hass.services.calls


@pytest.mark.asyncio
async def test_restart_without_episode_cannot_buy_a_new_window_above_limit(monkeypatch):
    runtime, hass, _manager, _adapter, clock = await running(monkeypatch)
    saved = runtime._snapshot()["sg_wallbox_transfer"]
    assert saved["armed"] is True and saved["episode"] is None
    fresh = type(runtime.sg_wallbox_transfer)()
    fresh.restore(saved)
    runtime.sg_wallbox_transfer = fresh
    clock.advance(5)
    sources(runtime, hass, clock, grid=4200)
    await runtime._observe_sg_wallbox_transfer()
    assert not runtime._sg_net_limit_allowed(4200)
    assert not runtime.sg_dispatch_allowed(renewal=True)
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["deadline", "order", "source"])
async def test_native_preflight_does_not_write_on_after_transfer_permission_changes(monkeypatch, native, change):
    runtime, hass, _manager, _adapter, clock = await running(monkeypatch)
    clock.advance(5)
    await spike(runtime, hass, clock)
    assert runtime.sg_dispatch_allowed(renewal=True)
    native.adapter.before_on = lambda: runtime.sg_dispatch_allowed(renewal=True)
    native.device.pause_read = asyncio.Event()
    native.device.release_read = asyncio.Event()
    pending = asyncio.create_task(native.adapter.set_on(300))
    await asyncio.wait_for(native.device.pause_read.wait(), timeout=2)
    if change == "deadline":
        clock.advance(240)
        sources(runtime, hass, clock, grid=4200)
        # Keep the independent existing relay proof live so expiration of the
        # transfer, not merely an old contact reading, is the deciding fact.
        runtime.sg_boost._relay_observed_at = clock()
        runtime.sg_boost._relay_valid_until = clock()+120
        runtime.sg_boost._lease_deadline = clock()+300
    elif change == "order":
        runtime.entry.options["priority_board"]["order"] = ["wallbox", "dhw_extra", "device:a"]
    else:
        report(hass, clock, "sensor.public_ev_power", "unavailable", {"unit_of_measurement": "W"})
    native.device.release_read.set()
    with pytest.raises(ShellyLeaseError) as caught:
        await pending
    assert caught.value.code == "dispatch_changed" and not caught.value.command_attempted
    assert writes(native) == [] and not hass.services.calls


@pytest.mark.asyncio
async def test_new_sg_start_can_temporarily_borrow_beyond_software_import_limit(monkeypatch):
    runtime, hass, manager, adapter, clock = await running(monkeypatch, limit=2000)
    # Full 3200 W SG envelope exceeds this software cap before the EV reacts.
    # Current solar EV credit covers that difference; actual P1 stays unedited.
    clock.advance(1)
    sources(runtime, hass, clock)
    assert runtime.heat_pump_increase_allowed()[0]
    assert runtime.sg_dispatch_allowed(automatic=True)
    assert manager.owned and adapter.calls == [("on", 300)]
    assert runtime._site_data()[0] == 0
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_first_delayed_p1_report_uses_original_time_for_window(monkeypatch):
    runtime, hass, manager, _adapter, clock = await running(monkeypatch)
    clock.advance(20)
    sources(runtime, hass, clock, grid=4200)
    report(hass, clock, "sensor.grid", 4200, {"unit_of_measurement": "W"}, age=10)
    await runtime._tick()
    view = runtime.sg_wallbox_transfer_overview()
    assert view["started_at"] == clock()-10
    assert view["expires_at"] == clock()+230
    assert view["remaining_s"] == 230
    assert manager.owned and not hass.services.calls


@pytest.mark.asyncio
async def test_failure_to_persist_first_episode_grants_no_transfer_permission(monkeypatch):
    runtime, hass, _manager, adapter, clock = await running(monkeypatch)
    clock.advance(5)
    sources(runtime, hass, clock, grid=4200)
    calls = list(adapter.calls)

    async def unavailable_store(_snapshot):
        raise OSError("fictional unavailable storage")

    monkeypatch.setattr(runtime.store, "async_save", unavailable_store)
    with pytest.raises(OSError):
        await runtime._observe_sg_wallbox_transfer()
    assert not runtime._sg_net_limit_allowed(4200)
    assert adapter.calls == calls and not hass.services.calls


@pytest.mark.asyncio
async def test_policy_changed_during_episode_storage_cannot_retain_sg(monkeypatch):
    runtime, hass, manager, adapter, clock = await running(monkeypatch)
    original_save = runtime.store.async_save
    changed = False

    async def changed_while_saving(data):
        nonlocal changed
        await original_save(data)
        if data["sg_wallbox_transfer"]["episode"] is not None and not changed:
            changed = True
            runtime.entry.options["priority_board"]["order"] = ["wallbox", "dhw_extra", "device:a"]

    monkeypatch.setattr(runtime.store, "async_save", changed_while_saving)
    clock.advance(5)
    await spike(runtime, hass, clock)
    assert changed and not manager.owned and not adapter.on
    assert adapter.calls[-1] == ("off", None)
    assert runtime.sg_wallbox_transfer.snapshot()["episode"]["invalidated"] is True
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_complete_sg_checkpoint_and_transfer_restore_keep_original_deadline(monkeypatch):
    runtime, hass, manager, adapter, clock = await running(monkeypatch)
    clock.advance(5)
    await spike(runtime, hass, clock)
    saved = deepcopy(runtime._snapshot())
    deadline = runtime.sg_wallbox_transfer_overview()["expires_at"]
    began = manager._session_started
    clock.advance(70)
    sources(runtime, hass, clock, grid=4200)
    fresh_transfer = type(runtime.sg_wallbox_transfer)()
    fresh_transfer.restore(saved["sg_wallbox_transfer"])
    runtime.sg_wallbox_transfer = fresh_transfer
    fresh_manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    fresh_manager.restore(saved["sg_boost"])
    runtime.sg_boost = fresh_manager
    await fresh_manager.start()
    assert fresh_manager._restart_resume is not None
    await runtime._tick()
    assert fresh_manager.owned and adapter.on
    assert fresh_manager._session_started == began
    assert runtime.sg_wallbox_transfer_overview()["expires_at"] == deadline
    assert runtime.sg_wallbox_transfer_overview()["remaining_s"] == 170
    assert all(command == "on" for command, _lease in adapter.calls)
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_soft_cloud_timer_runs_in_parallel_and_can_stop_before_transfer_deadline(monkeypatch):
    runtime, hass, manager, adapter, clock = await running(
        monkeypatch, min_session_s=0, stop_delay_s=60)
    clock.advance(5)
    await spike(runtime, hass, clock)
    deadline = runtime.sg_wallbox_transfer_overview()["expires_at"]
    clock.advance(59)
    await spike(runtime, hass, clock)
    assert manager.owned and clock() < deadline
    clock.advance(1)
    await spike(runtime, hass, clock)
    assert not manager.owned and not adapter.on and clock() < deadline
    assert manager._last_session["reason"] == "Aanhoudende netafname; extra SG-aanvraag vrijgegeven"
    assert adapter.calls[-1] == ("off", None) and not hass.services.calls


async def external_running(monkeypatch):
    runtime, hass, manager, adapter, clock = environment(monkeypatch)
    adapter.on = True
    await manager.start()
    assert manager.external_control_overview()["active"] and not manager.owned
    await runtime._observe_sg_wallbox_transfer()
    clock.advance(15)
    sources(runtime, hass, clock)
    await runtime._observe_sg_wallbox_transfer()
    assert runtime.sg_wallbox_transfer.snapshot()["armed"] is True
    assert adapter.calls == []
    return runtime, hass, manager, adapter, clock


@pytest.mark.asyncio
async def test_observed_manual_on_survives_ev_reaction_without_taking_ownership(monkeypatch):
    runtime, hass, manager, adapter, clock = await external_running(monkeypatch)
    original_deadline = manager.external_control_overview()["expires_at"]
    clock.advance(5)
    await spike(runtime, hass, clock)
    assert runtime.sg_wallbox_transfer_overview()["applicable"]
    assert manager.external_control_overview()["expires_at"] == original_deadline
    assert not manager.owned and adapter.on and adapter.calls == []
    clock.advance(30)
    await spike(runtime, hass, clock, grid=0, ev=2000)
    assert adapter.on and not manager.owned and adapter.calls == []
    assert manager.external_control_overview()["expires_at"] == original_deadline
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["fingerprint", "binding"])
async def test_changed_external_contact_proof_cannot_keep_the_net_exception(monkeypatch, change):
    runtime, hass, manager, adapter, clock = await external_running(monkeypatch)
    clock.advance(5)
    await spike(runtime, hass, clock)
    assert runtime._sg_transfer_live() and runtime._sg_net_limit_allowed(4200)
    if change == "fingerprint":
        manager._observed_fingerprint = {"device_id": "other-fictional-relay"}
    else:
        manager._relay_binding_identity = "other-fictional-binding"
    assert not runtime._sg_transfer_live()
    assert not runtime._sg_net_limit_allowed(4200)
    assert not manager.owned and adapter.calls == []
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_external_fifteen_minute_reassessment_keeps_raw_soft_import_condition(monkeypatch):
    runtime, hass, manager, adapter, clock = await external_running(monkeypatch)
    original_deadline = manager.external_control_overview()["expires_at"]
    clock.advance(5)
    await spike(runtime, hass, clock)
    assert adapter.calls == []
    clock.advance(original_deadline-clock())
    # Sufficient eligible sun cannot erase the separate raw >600 W condition.
    await spike(runtime, hass, clock, grid=1000, hp=1600)
    assert runtime._sg_import_observation()["watts"] == 1000
    assert not adapter.on and not manager.owned
    assert adapter.calls == [("off", None)]
    assert manager.external_control_overview()["active"] is False
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_display_name_and_unrelated_immutable_metadata_do_not_cancel_real_transfer(monkeypatch):
    runtime, hass, _manager, _adapter, clock = await running(monkeypatch)
    clock.advance(5)
    await spike(runtime, hass, clock)
    before = runtime.sg_wallbox_transfer_overview()
    runtime.settings["metadata"] = MappingProxyType({"nested": MappingProxyType({"label": "fictitious"})})
    runtime.wallbox_settings["name"] = "Display name changed"
    assert runtime._sg_net_limit_allowed(4200)
    assert runtime.sg_dispatch_allowed(renewal=True)
    assert runtime.sg_wallbox_transfer_overview()["expires_at"] == before["expires_at"]
    # A real source rebinding remains a different permission identity.
    runtime.wallbox_settings["power_entity"] = "sensor.rebound_ev"
    report(hass, clock, "sensor.rebound_ev", 4000, {"unit_of_measurement": "W"})
    assert not runtime._sg_net_limit_allowed(4200)
    assert not runtime.sg_dispatch_allowed(renewal=True)
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [None, {"mode": "solar", "leases": {"previous": {"watts": 1200}}}])
async def test_preload_source_observation_cannot_overwrite_existing_journal_or_arm(monkeypatch, stored):
    runtime, hass, _manager, adapter, clock = environment(monkeypatch, data_loaded=False)
    runtime.store.data = deepcopy(stored)
    before = deepcopy(runtime.sg_wallbox_transfer.snapshot())
    await runtime._observe_sg_wallbox_transfer()
    clock.advance(20)
    sources(runtime, hass, clock)
    await runtime._observe_sg_wallbox_transfer()
    assert runtime.store.data == stored and runtime.store.saves == []
    assert runtime.sg_wallbox_transfer.snapshot() == before
    assert adapter.calls == [] and not hass.services.calls
