"""Software-only SG leases and state transitions, with a deterministic device.

These tests do not certify Shelly firmware, wiring or a Panasonic SG mapping.
"""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.sg_boost import SGBoostManager
from custom_components.solar_pilot.sg_config import SG_DEFAULTS


class Clock:
    def __init__(self):
        self.value = 1_800_000_000.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class Store:
    def __init__(self):
        self.saves = []

    async def async_save(self, data):
        self.saves.append(deepcopy(data))


class Adapter:
    """A locally expiring relay; loss of HA does not stop its device clock."""
    def __init__(self, clock):
        self.clock = clock
        self.on = False
        self.start = None
        self.duration = None
        self.expiry = None
        self.online = True
        self.configured = True
        self.calls = []
        self.reads = 0
        self.timer_missing = False
        self.timer_frozen = False
        self.no_expiry = False
        self.off_bad = False
        self.delayed = None
        self.fingerprint = {"device_id": "fictional-relay", "firmware_id": "fixture-v1", "component": "switch:0"}

    def status(self):
        if self.on and self.expiry is not None and self.clock() >= self.expiry and not self.no_expiry:
            self.on = False
            self.start = self.duration = self.expiry = None
        return {"output": self.on, "timer_started_at": self.start,
                "timer_duration": self.duration, "expires_at": self.expiry,
                "lease_remaining_s": None if self.expiry is None else max(0, self.expiry - self.clock()),
                "setup_valid": self.configured, "fingerprint": deepcopy(self.fingerprint)}

    async def get_status(self):
        self.reads += 1
        if not self.online:
            raise RuntimeError("transport unavailable")
        return self.status()

    async def set_on(self, lease_s=300):
        self.calls.append(("on", lease_s))
        if not self.online:
            raise RuntimeError("transport unavailable")
        if self.delayed is not None:
            await self.delayed.wait()
        self.on = True
        if not self.timer_missing and not (self.timer_frozen and self.expiry is not None):
            self.start, self.duration = self.clock(), lease_s
            self.expiry = self.start + lease_s
        return self.status()

    async def set_off(self):
        self.calls.append(("off", None))
        if not self.online:
            raise RuntimeError("transport unavailable")
        if not self.off_bad:
            self.on = False
            self.start = self.duration = self.expiry = None
        return self.status()


def fixture(*, enabled=True, mode="solar", **config):
    clock = Clock()
    settings = {**SG_DEFAULTS, "entity_id": "switch.sg_fixture", "enabled": enabled,
                "commissioning_confirmed": True, "watchdog_confirmed": True, **config}
    runtime = SimpleNamespace(entry=SimpleNamespace(options={"sg_boost": settings}),
                              mode=mode, hass=SimpleNamespace(), store=Store(), notes=[],
                              last_issued=0, last_issued_wall=0)
    runtime.note = runtime.notes.append
    runtime.panasonic = SimpleNamespace(overview=lambda: {"temperature_c": 49, "target_c": 50,
                                                         "power_w": 2500, "power_kind": "measured",
                                                         "power_scope": "supply2"})
    runtime.entity_id = lambda domain, suffix: f"{domain}.fixture_{suffix}"
    adapter = Adapter(clock)
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = manager
    runtime._snapshot = lambda: {"sg_boost": manager.snapshot()}
    return manager, adapter, clock, runtime


async def tick(manager, *, surplus=4000, imported=0, **kwargs):
    return await manager.tick(surplus_w=surplus, grid_import_w=imported, data_fresh=True,
                              phase_allowed=True, **kwargs)


async def boosted(**kwargs):
    manager, adapter, clock, runtime = fixture(**kwargs)
    await tick(manager)
    clock.advance(manager.settings["start_delay_s"])
    await tick(manager)
    assert manager.owned and manager.desired_on
    assert adapter.calls == [("on", manager.settings["lease_s"])]
    return manager, adapter, clock, runtime


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["observe", "paused", "unknown"])
async def test_global_mode_cannot_start_sg(mode):
    manager, adapter, clock, _ = fixture(mode=mode)
    await tick(manager)
    clock.advance(10000)
    await tick(manager)
    assert not adapter.calls and not manager.desired_on


@pytest.mark.asyncio
@pytest.mark.parametrize("config", [{"enabled": False}, {"commissioning_confirmed": False},
                                   {"watchdog_confirmed": False}, {"entity_id": ""},
                                   {"entity_id": "climate.fake"}, {"renew_s": 299}])
async def test_missing_enable_or_confirmations_cannot_create_authority(config):
    manager, adapter, clock, _ = fixture(**config)
    await tick(manager)
    clock.advance(10000)
    await tick(manager)
    assert not adapter.calls


@pytest.mark.asyncio
async def test_start_requires_continuous_real_surplus_not_forecast_or_native_power():
    manager, adapter, clock, _ = fixture()
    await tick(manager, surplus=4000)
    clock.advance(119)
    await tick(manager, surplus=2999, predicted_surplus_w=99999, native_hp_power_w=8000)
    clock.advance(120)
    await tick(manager, surplus=4000)
    assert not adapter.calls
    clock.advance(119)
    await tick(manager, surplus=4000)
    assert not adapter.calls
    clock.advance(1)
    await tick(manager, surplus=4000)
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_boost_consuming_export_does_not_trigger_false_stop():
    manager, adapter, clock, _ = await boosted()
    for _ in range(5):
        clock.advance(60)
        await tick(manager, surplus=0, imported=0)
    assert manager.owned and manager.desired_on
    assert all(command == "on" for command, _ in adapter.calls)
    assert len(adapter.calls) == 6


@pytest.mark.asyncio
async def test_stop_import_is_delayed_and_resets_when_cloud_passes():
    manager, adapter, clock, _ = await boosted()
    await tick(manager, imported=1000)
    clock.advance(59)
    await tick(manager, imported=1000)
    assert manager.owned
    await tick(manager, imported=299)
    clock.advance(61)
    await tick(manager, imported=1000)
    assert manager.owned
    clock.advance(60)
    await tick(manager, imported=1000)
    assert not manager.owned and adapter.calls[-1] == ("off", None)
    assert manager.state == "rest"


@pytest.mark.asyncio
@pytest.mark.parametrize("gate", ["data_fresh", "phase_allowed", "priority_allowed", "hard_limit"])
async def test_hard_guard_releases_contact_immediately(gate):
    manager, adapter, _, _ = await boosted()
    values = {"surplus_w": 4000, "grid_import_w": 0, "data_fresh": True, "phase_allowed": True}
    values[gate] = gate == "hard_limit"
    await manager.tick(**values)
    assert adapter.calls[-1] == ("off", None)
    assert not manager.desired_on and manager.relay_on is False


@pytest.mark.asyncio
@pytest.mark.parametrize("surplus, imported", [(None, 0), (float("nan"), 0), (-1, 0),
                                                (4000, None), (4000, -1), (True, 0)])
async def test_invalid_numeric_input_cannot_start(surplus, imported):
    manager, adapter, clock, _ = fixture()
    await tick(manager, surplus=surplus, imported=imported)
    clock.advance(1000)
    await tick(manager, surplus=surplus, imported=imported)
    assert not adapter.calls


@pytest.mark.asyncio
async def test_rest_requires_new_stability_period_after_release():
    manager, adapter, clock, runtime = await boosted()
    runtime.mode = "paused"
    await tick(manager)
    runtime.mode = "solar"
    clock.advance(899)
    await tick(manager)
    assert manager.state == "rest"
    clock.advance(1)
    await tick(manager)
    assert len(adapter.calls) == 2
    clock.advance(119)
    await tick(manager)
    assert len(adapter.calls) == 2
    clock.advance(1)
    await tick(manager)
    assert adapter.calls[-1] == ("on", 300)


@pytest.mark.asyncio
async def test_max_duration_stops_and_does_not_repeat_unknown_completed_session():
    manager, adapter, clock, _ = await boosted(max_session_s=300)
    for _ in range(4):
        clock.advance(60)
        await tick(manager)
    clock.advance(60)
    await tick(manager)
    assert not manager.owned and manager.completion_hold
    count = len(adapter.calls)
    clock.advance(10000)
    await tick(manager)
    clock.advance(10000)
    await tick(manager)
    assert len(adapter.calls) == count
    await tick(manager, physical_evidence={"verified": True, "restart_ready": True})
    clock.advance(120)
    await tick(manager)
    assert adapter.calls[-1] == ("on", 300)


@pytest.mark.asyncio
@pytest.mark.parametrize("evidence", [{"completed": True}, {"no_uptake": True},
                                     {"verified": False, "completed": True},
                                     {"temperature_c": 60}, {"target_c": 50}])
async def test_unknown_or_temperature_alone_is_not_completion_proof(evidence):
    manager, adapter, _, _ = await boosted()
    await tick(manager, physical_evidence=evidence)
    assert manager.owned and len(adapter.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["completed", "no_uptake"])
async def test_explicit_verified_completion_stops_and_waits_for_new_need(key):
    manager, adapter, clock, _ = await boosted()
    await tick(manager, physical_evidence={"verified": True, key: True})
    assert manager.completion_hold and adapter.calls[-1] == ("off", None)
    clock.advance(10000)
    await tick(manager)
    assert len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_timer_renewal_advances_without_off_on_cycle():
    manager, adapter, clock, runtime = await boosted()
    expiry, last_action = manager._lease_expiry, runtime.last_issued_wall
    clock.advance(60)
    await tick(manager)
    assert manager._lease_expiry == expiry + 60
    assert adapter.calls == [("on", 300), ("on", 300)]
    assert manager.renewed_this_tick and not manager.sent_this_tick
    assert runtime.last_issued_wall == last_action


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timer_missing", "timer_frozen"])
async def test_missing_or_unrenewed_local_timer_blocks_and_releases(failure):
    if failure == "timer_frozen":
        manager, adapter, clock, _ = await boosted()
        adapter.timer_frozen = True
        clock.advance(60)
    else:
        manager, adapter, clock, _ = fixture()
        adapter.timer_missing = True
        await tick(manager)
        clock.advance(120)
    await tick(manager)
    assert manager.fault_code == "on_failed"
    assert adapter.calls[-1] == ("off", None)
    count = len(adapter.calls)
    clock.advance(10000)
    await tick(manager)
    assert len(adapter.calls) == count


@pytest.mark.asyncio
async def test_local_lease_expires_without_ha_and_new_decision_is_required():
    manager, adapter, clock, _ = await boosted()
    # No tick/renewal while Home Assistant is absent.
    clock.advance(301)
    assert adapter.status()["output"] is False
    await tick(manager)
    assert not manager.manual_hold and not manager.desired_on
    assert manager.state == "rest" and len(adapter.calls) == 1
    clock.advance(900)
    await tick(manager)
    assert len(adapter.calls) == 1
    clock.advance(120)
    await tick(manager)
    assert len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_early_manual_off_is_respected_until_explicit_resume():
    manager, adapter, clock, _ = await boosted()
    adapter.on = False
    adapter.start = adapter.duration = adapter.expiry = None
    clock.advance(10)
    await tick(manager)
    assert manager.manual_hold and not manager.owned
    clock.advance(10000)
    await tick(manager)
    assert len(adapter.calls) == 1
    await manager.resume_automation()
    await tick(manager)
    clock.advance(120)
    await tick(manager)
    assert adapter.calls[-1] == ("on", 300)


@pytest.mark.asyncio
async def test_external_manual_on_without_journal_is_not_switched_off():
    manager, adapter, clock, _ = fixture()
    adapter.on = True
    await manager.start()
    assert manager.manual_hold and manager.relay_on is True
    await manager.set_enabled(False)
    await manager.close()
    assert not adapter.calls


@pytest.mark.asyncio
async def test_external_timer_change_releases_ownership_but_respects_contact():
    manager, adapter, clock, _ = await boosted()
    adapter.expiry += 600
    clock.advance(10)
    await tick(manager)
    assert manager.manual_hold and not manager.owned and adapter.on
    assert len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_restart_releases_owned_request_but_never_replays_it():
    previous, adapter, clock, runtime = await boosted()
    journal = previous.snapshot()
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = manager
    runtime._snapshot = lambda: {"sg_boost": manager.snapshot()}
    manager.restore(journal)
    assert len(adapter.calls) == 1 and not manager.desired_on
    await manager.start()
    assert adapter.calls == [("on", 300), ("off", None)]
    await tick(manager)
    assert manager.state == "rest"


@pytest.mark.asyncio
async def test_restart_with_different_live_manual_timer_does_not_release_it():
    previous, adapter, clock, runtime = await boosted()
    journal = previous.snapshot()
    adapter.expiry += 600
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    manager.restore(journal)
    await manager.start()
    assert manager.manual_hold and adapter.on and len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_restore_never_enables_disabled_config_or_carries_other_relay_ownership():
    manager, adapter, _, _ = fixture(enabled=False)
    manager.restore({"schema": 1, "relay_entity": "switch.different", "owned": True, "enabled": True,
                     "manual_hold": True, "completion_hold": True})
    await manager.start()
    assert not manager.auto_enabled and not manager._restart_release and not manager.manual_hold
    assert not adapter.calls


@pytest.mark.asyncio
async def test_unreachable_contact_is_unknown_and_writes_are_bounded():
    manager, adapter, clock, _ = await boosted()
    adapter.online = False
    await tick(manager)
    assert manager.relay_on is None and not manager.relay_confirmed
    count = len(adapter.calls)
    reads = adapter.reads
    for _ in range(10):
        clock.advance(1)
        await tick(manager)
    assert len(adapter.calls) == count and adapter.reads == reads
    assert not manager.desired_on
    assert manager.fault and count == 2  # One OFF attempt, then the local timer.
    clock.advance(301)
    assert adapter.status()["output"] is False
    assert not manager.busy and manager.relay_on is None


@pytest.mark.asyncio
async def test_off_failure_waits_for_real_off_not_fiction_or_command_retries():
    manager, adapter, clock, runtime = await boosted()
    adapter.off_bad = True
    runtime.mode = "paused"
    await tick(manager)
    assert manager.relay_on is None and manager.fault_code == "off_failed"
    count = len(adapter.calls)
    await tick(manager)
    assert len(adapter.calls) == count
    clock.advance(301)
    await tick(manager)
    assert manager.relay_on is False and manager.relay_confirmed and not manager.fault


@pytest.mark.asyncio
async def test_late_on_after_disable_is_released_without_new_permission():
    manager, adapter, clock, _ = fixture()
    await tick(manager)
    clock.advance(120)
    adapter.delayed = asyncio.Event()
    pending = asyncio.create_task(tick(manager))
    for _ in range(3):
        await asyncio.sleep(0)
    disable = asyncio.create_task(manager.set_enabled(False))
    await asyncio.sleep(0)
    adapter.delayed.set()
    await pending
    await disable
    assert adapter.calls == [("on", 300), ("off", None)]
    assert not manager.auto_enabled and not manager.desired_on and manager.relay_on is False


@pytest.mark.asyncio
async def test_close_with_pending_on_releases_and_cannot_restart():
    manager, adapter, clock, _ = fixture()
    await tick(manager)
    clock.advance(120)
    adapter.delayed = asyncio.Event()
    pending = asyncio.create_task(tick(manager))
    for _ in range(3):
        await asyncio.sleep(0)
    close = asyncio.create_task(manager.close())
    await asyncio.sleep(0)
    adapter.delayed.set()
    await pending
    await close
    assert not adapter.on and not manager.busy
    clock.advance(10000)
    await tick(manager)
    assert adapter.calls == [("on", 300), ("off", None)]


@pytest.mark.asyncio
async def test_unchanged_tank_setpoint_is_not_an_sg_ack_or_fault():
    manager, _, clock, _ = await boosted()
    clock.advance(60)
    await tick(manager)
    row = manager.overview()
    assert row["target_c"] == 50 and not row["fault"]
    assert row["panasonic_confirmed"] is None
    assert "niet afzonderlijk bevestigd" in row["reason"]
    assert row["power_w"] == 2500 and row["power_scope"] == "supply2"


@pytest.mark.asyncio
async def test_only_verified_sg_status_confirms_panasonic_not_heat_or_relay():
    manager, _, _, _ = await boosted()
    await tick(manager, physical_evidence={"sg_active": True})
    assert manager.panasonic_confirmed is None
    await tick(manager, physical_evidence={"verified": True, "sg_active": True})
    assert manager.panasonic_confirmed is True


@pytest.mark.asyncio
async def test_unsafe_changed_local_setup_stops_owned_sg():
    manager, adapter, _, _ = await boosted()
    adapter.configured = False
    await tick(manager)
    assert manager.fault_code == "setup_invalid"
    assert adapter.calls[-1] == ("off", None)


@pytest.mark.asyncio
async def test_no_lease_does_not_fake_off_or_confirm_physical_reaction():
    manager, adapter, _, _ = fixture()
    adapter.online = False
    await manager.start()
    row = manager.overview()
    assert row["relay_on"] is None and not row["relay_confirmed"]
    assert row["panasonic_confirmed"] is None


def test_binding_change_cannot_detach_an_owned_lease():
    manager, _, _, _ = fixture()
    manager.owned = True
    with pytest.raises(HomeAssistantError):
        manager.update_config({**manager.settings, "entity_id": "switch.other"})
    assert manager.settings["entity_id"] == "switch.sg_fixture"


@pytest.mark.asyncio
async def test_waiting_does_not_request_notification_but_transport_fault_does():
    manager, adapter, _, _ = fixture()
    await tick(manager, surplus=0)
    assert not manager.action_required and not manager.overview()["action_required"]
    adapter.online = False
    await tick(manager)
    assert manager.action_required


@pytest.mark.asyncio
async def test_firmware_change_releases_and_revokes_old_commissioning():
    manager, adapter, _, _ = await boosted()
    assert manager.snapshot()["commissioned_fingerprint"] == adapter.fingerprint
    adapter.fingerprint["firmware_id"] = "fixture-v2"
    await tick(manager)
    assert adapter.calls[-1] == ("off", None)
    assert manager.fault_code == "firmware_changed"
    assert not manager.settings["watchdog_confirmed"]
    assert not manager.settings["commissioning_confirmed"]
    with pytest.raises(HomeAssistantError):
        await manager.resume_automation()
    with pytest.raises(HomeAssistantError):
        await manager.set_enabled(True)


@pytest.mark.asyncio
async def test_restart_does_not_reuse_firmware_attestation_for_new_version():
    prior, adapter, clock, runtime = await boosted()
    saved = prior.snapshot()
    adapter.fingerprint["firmware_id"] = "fixture-v2"
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    manager.restore(saved)
    await manager.start()
    assert manager.fault_code == "firmware_changed"
    assert not manager.settings["watchdog_confirmed"]
    assert adapter.calls[-1] == ("off", None)
    clock.advance(10000)
    await tick(manager)
    assert len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_explicit_new_commissioning_can_accept_changed_firmware_after_release():
    manager, adapter, clock, _ = await boosted()
    adapter.fingerprint["firmware_id"] = "fixture-v2"
    await tick(manager)
    manager.update_config({**manager.settings, "commissioning_confirmed": True, "watchdog_confirmed": True})
    assert not manager.fault
    assert manager.snapshot()["commissioned_fingerprint"] == adapter.fingerprint
    clock.advance(900)
    await tick(manager)
    clock.advance(120)
    await tick(manager)
    assert manager.owned and adapter.calls[-1] == ("on", 300)


@pytest.mark.asyncio
async def test_rejected_renewal_still_releases_previous_owned_contact():
    manager, adapter, clock, _ = await boosted()

    class Rejected(Exception):
        command_attempted = False

    async def reject(lease_s):
        raise Rejected("configuration no longer safe")

    adapter.set_on = reject
    clock.advance(60)
    await tick(manager)
    assert adapter.calls == [("on", 300), ("off", None)]
    assert not manager.owned and manager.fault_code == "on_failed"


@pytest.mark.asyncio
async def test_storage_failure_prevents_on_without_claiming_command_was_sent():
    manager, adapter, clock, runtime = fixture()
    await tick(manager)
    clock.advance(120)

    async def broken_save(_data):
        raise RuntimeError("private storage unavailable")

    runtime.store.async_save = broken_save
    # The error may still reach the integration for reporting, but an actuator
    # must never be changed when ownership intent could not be stored.
    with pytest.raises(RuntimeError):
        await tick(manager)
    assert adapter.calls == []
    assert not manager._possibly_owned and not manager.desired_on
    assert runtime.last_issued_wall == 0


def test_snapshot_is_stable_without_mutating_rest_or_other_evidence():
    manager, _, clock, _ = fixture()
    initial = manager.snapshot()
    clock.advance(300)
    assert manager.snapshot() == initial
    manager._begin_rest()
    resting = manager.snapshot()
    clock.advance(50)
    assert manager.snapshot() == resting


@pytest.mark.asyncio
async def test_setup_abort_close_does_not_replace_unrestored_private_store():
    manager, adapter, _, runtime = fixture(entity_id="", enabled=False)
    saved = {"device_history": {"fixture": "preserve"}, "analysis": {"observations": [1, 2]}}
    await runtime.store.async_save(saved)
    await manager.close(persist=False)
    assert runtime.store.saves == [saved] and not adapter.calls


@pytest.mark.asyncio
async def test_abort_no_persist_still_withdraws_an_own_leased_request():
    manager, adapter, _, runtime = await boosted()
    saved = deepcopy(runtime.store.saves)
    await manager.close(persist=False)
    assert adapter.calls[-1] == ("off", None)
    assert not manager.owned and not manager.desired_on
    assert runtime.store.saves == saved


@pytest.mark.asyncio
async def test_pause_during_journal_save_prevents_any_on_call():
    manager, adapter, clock, runtime = fixture()
    await tick(manager)
    clock.advance(120)
    original_save = runtime.store.async_save

    async def change_mode_while_saving(data):
        await original_save(data)
        runtime.mode = "paused"

    runtime.store.async_save = change_mode_while_saving
    await tick(manager)
    assert not adapter.calls and not manager.desired_on
    assert manager.relay_on is False and manager.relay_confirmed
    assert runtime.last_issued_wall == 0
    assert not manager.fault


@pytest.mark.asyncio
async def test_disable_during_journal_save_prevents_any_on_call():
    manager, adapter, clock, runtime = fixture()
    await tick(manager)
    clock.advance(120)
    original_save = runtime.store.async_save

    async def disable_while_saving(data):
        await original_save(data)
        manager.update_config({**manager.settings, "enabled": False})

    runtime.store.async_save = disable_while_saving
    await tick(manager)
    assert not adapter.calls and not manager.desired_on
    assert runtime.last_issued_wall == 0
    assert not manager.fault


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["phase", "surplus", "priority"])
async def test_final_transport_callback_rejects_changed_live_budget(kind):
    manager, adapter, clock, runtime = fixture()
    permitted = [True]
    runtime.sg_dispatch_allowed = lambda renewal: permitted[0]
    adapter.before_on = None

    class DispatchChanged(Exception):
        code = "dispatch_changed"
        command_attempted = False

    async def preflight_changes(lease_s):
        # Mirrors actual asynchronous native read/check preflight. The callback
        # runs after those reads and immediately before the hypothetical Set.
        await asyncio.sleep(0)
        permitted[0] = False
        if adapter.before_on() is not True:
            raise DispatchChanged(kind)
        raise AssertionError("Obsolete admission must never reach Switch.Set")

    adapter.set_on = preflight_changes
    await tick(manager)
    clock.advance(120)
    await tick(manager)
    assert not adapter.calls and not manager.desired_on
    assert manager.relay_on is False and manager.relay_confirmed
    assert runtime.last_issued_wall == 0 and not manager.fault
    assert adapter.before_on is None


@pytest.mark.asyncio
async def test_policy_rejected_renewal_withdraws_old_request_without_new_on():
    manager, adapter, clock, runtime = await boosted()
    runtime.sg_dispatch_allowed = lambda renewal: True
    adapter.before_on = None

    class DispatchChanged(Exception):
        code = "dispatch_changed"
        command_attempted = False

    async def deny_after_preflight(lease_s):
        runtime.mode = "paused"
        assert adapter.before_on() is False
        raise DispatchChanged()

    adapter.set_on = deny_after_preflight
    clock.advance(60)
    await tick(manager)
    assert adapter.calls == [("on", 300), ("off", None)]
    assert not manager.owned and not manager.fault


@pytest.mark.asyncio
async def test_first_local_lease_never_exceeds_short_configured_session():
    manager, adapter, clock, _ = fixture(lease_s=600, max_session_s=300)
    await tick(manager)
    clock.advance(120)
    await tick(manager)
    assert manager.owned and adapter.calls == [("on", 300)]
    start = manager._session_started
    assert manager._lease_deadline <= start + manager.settings["max_session_s"]
    clock.advance(301)
    assert adapter.status()["output"] is False  # HA absent, device still expires.


@pytest.mark.asyncio
async def test_renewed_local_permission_cannot_outlive_session_when_ha_disappears():
    manager, adapter, clock, _ = await boosted(max_session_s=300)
    start = manager._session_started
    clock.advance(60)
    await tick(manager)
    assert adapter.calls == [("on", 300)]  # Existing timer already ends at the session ceiling.
    assert manager._lease_deadline <= start + 300
    # Stop evaluating after this renewal; its local lease still ends within the
    # session ceiling rather than defaulting to a further full five minutes.
    clock.advance(241)
    assert adapter.status()["output"] is False


@pytest.mark.asyncio
async def test_final_shorter_renewal_advances_timer_without_exceeding_session_ceiling():
    manager, adapter, clock, _ = await boosted(max_session_s=600)
    start = manager._session_started
    for _ in range(5):
        clock.advance(60)
        await tick(manager)
    assert adapter.calls[-1] == ("on", 280)
    assert manager._lease_deadline == start + 580
    count = len(adapter.calls)
    clock.advance(60)
    await tick(manager)
    assert len(adapter.calls) == count and manager._session_finishing
    journal = manager.snapshot()
    assert journal["session_finishing"] is True
    clock.advance(221)
    assert adapter.status()["output"] is False
    await tick(manager)
    assert manager.completion_hold and not manager.owned


@pytest.mark.asyncio
async def test_restart_final_session_window_requires_new_need_or_explicit_resume():
    previous, adapter, clock, runtime = await boosted(max_session_s=300)
    saved = previous.snapshot()
    assert saved["session_finishing"] is True
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    manager.restore(saved)
    await manager.start()
    assert manager.completion_hold and adapter.calls[-1] == ("off", None)
    count = len(adapter.calls)
    clock.advance(10000)
    await tick(manager)
    assert len(adapter.calls) == count


@pytest.mark.asyncio
async def test_native_runtime_keyword_only_dispatch_gate_is_called_correctly():
    manager, adapter, clock, runtime = fixture()
    checks = []

    def native_gate(*, renewal=False):
        checks.append(renewal)
        return True

    runtime.sg_dispatch_allowed = native_gate
    await tick(manager)
    clock.advance(120)
    await tick(manager)
    assert manager.owned and adapter.calls == [("on", 300)]
    assert checks == [False, False]


def tank_observation(manager, clock, temperature, *, stamp=None, entity_id=None):
    return {"entity_id": entity_id or manager.settings["tank_temperature_entity"],
            "temperature_c": temperature, "stamp": clock() if stamp is None else stamp}


async def finished_with_tank_reference():
    manager, adapter, clock, runtime = await boosted(max_session_s=300,
        tank_temperature_entity="sensor.tank_fixture")
    clock.advance(301)
    await tick(manager, tank_observation=tank_observation(manager, clock, 55))
    assert manager.completion_hold and manager._need_reference["temperature_c"] == 55
    assert not manager.owned and not adapter.on
    return manager, adapter, clock, runtime


@pytest.mark.asyncio
async def test_real_tank_decline_after_rest_rearms_automatically_with_new_full_start_delay():
    manager, adapter, clock, _ = await finished_with_tank_reference()
    clock.advance(900)
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    assert manager.completion_hold
    clock.advance(300)
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    assert not manager.completion_hold and manager._last_rearm["drop_c"] == 2
    assert len(adapter.calls) == 1 and not manager.desired_on
    clock.advance(119)
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    assert len(adapter.calls) == 1
    clock.advance(1)
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    assert adapter.calls == [("on", 300), ("on", 300)] and manager.owned


@pytest.mark.asyncio
async def test_status_polling_cannot_replace_real_tank_heartbeats_for_rearm():
    manager, adapter, clock, _ = await finished_with_tank_reference()
    clock.advance(900)
    observation = tank_observation(manager, clock, 52)
    await tick(manager, tank_observation=observation)
    for _ in range(7):
        clock.advance(50)
        await tick(manager, tank_observation=observation)
    assert manager.completion_hold and len(adapter.calls) == 1
    # The old temperature report is stale. A new report restarts the full local
    # observation window rather than inheriting elapsed relay polls.
    await tick(manager, tank_observation=tank_observation(manager, clock, 52))
    assert manager.completion_hold


@pytest.mark.asyncio
async def test_local_five_minute_confirmation_cannot_be_shortcut_by_report_timestamps():
    manager, _, clock, _ = await finished_with_tank_reference()
    clock.advance(900)
    await tick(manager, tank_observation=tank_observation(manager, clock, 52))
    clock.advance(299)
    await tick(manager, tank_observation=tank_observation(manager, clock, 52, stamp=clock()+5))
    assert manager.completion_hold
    clock.advance(1)
    await tick(manager, tank_observation=tank_observation(manager, clock, 52, stamp=clock()+5))
    assert not manager.completion_hold


@pytest.mark.asyncio
async def test_small_decline_or_rising_temperature_does_not_prove_new_storage():
    manager, adapter, clock, _ = await finished_with_tank_reference()
    clock.advance(900)
    for temperature in (55, 54, 53.1, 56):
        await tick(manager, tank_observation=tank_observation(manager, clock, temperature))
        clock.advance(400)
    assert manager.completion_hold and len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_temperature_rebound_resets_decline_confirmation_window():
    manager, _, clock, _ = await finished_with_tank_reference()
    clock.advance(900)
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    clock.advance(299)
    await tick(manager, tank_observation=tank_observation(manager, clock, 54))
    clock.advance(1)
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    assert manager.completion_hold
    clock.advance(300)
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    assert not manager.completion_hold


@pytest.mark.asyncio
async def test_reference_is_exact_session_end_reading_and_not_invented_afterwards():
    manager, adapter, clock, _ = await boosted(max_session_s=300,
        tank_temperature_entity="sensor.tank_fixture")
    clock.advance(301)
    await tick(manager)  # No reliable end observation available.
    assert manager.completion_hold and manager._need_reference is None
    clock.advance(900)
    await tick(manager, tank_observation=tank_observation(manager, clock, 55))
    clock.advance(400)
    await tick(manager, tank_observation=tank_observation(manager, clock, 50))
    assert manager.completion_hold and manager._need_reference is None
    assert len(adapter.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["none", "nan", "boolean", "range", "source", "stale", "future"])
async def test_bad_end_observation_never_grants_automatic_rearm(bad):
    manager, adapter, clock, _ = await boosted(max_session_s=300,
        tank_temperature_entity="sensor.tank_fixture")
    clock.advance(301)
    observation = tank_observation(manager, clock, 55)
    if bad == "none":
        observation["temperature_c"] = None
    elif bad == "nan":
        observation["temperature_c"] = float("nan")
    elif bad == "boolean":
        observation["temperature_c"] = True
    elif bad == "range":
        observation["temperature_c"] = 150
    elif bad == "source":
        observation["entity_id"] = "sensor.other_fixture"
    elif bad == "stale":
        observation["stamp"] -= 121
    elif bad == "future":
        observation["stamp"] += 6
    await tick(manager, tank_observation=observation)
    assert manager._need_reference is None and manager.completion_hold
    clock.advance(2000)
    await tick(manager, tank_observation=tank_observation(manager, clock, 50))
    assert len(adapter.calls) == 1 and manager.completion_hold


@pytest.mark.asyncio
async def test_tank_source_change_requires_explicit_resume_instead_of_reusing_reference():
    manager, adapter, clock, _ = await finished_with_tank_reference()
    manager.update_config({**manager.settings, "tank_temperature_entity": "sensor.new_tank_fixture"})
    clock.advance(900)
    await tick(manager, tank_observation=tank_observation(manager, clock, 50))
    clock.advance(400)
    await tick(manager, tank_observation=tank_observation(manager, clock, 50))
    assert manager.completion_hold and manager._tank_source_changed and len(adapter.calls) == 1
    await manager.resume_automation()
    assert not manager.completion_hold and not manager._tank_source_changed
    assert manager._need_reference is None


@pytest.mark.asyncio
async def test_private_reference_survives_reload_but_confirmation_requires_new_reports():
    prior, adapter, clock, runtime = await finished_with_tank_reference()
    clock.advance(900)
    await tick(prior, tank_observation=tank_observation(prior, clock, 53))
    clock.advance(299)
    saved = prior.snapshot()
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    manager.restore(saved)
    assert manager._need_reference == prior._need_reference and manager._need_candidate is None
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    clock.advance(1)
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    assert manager.completion_hold
    clock.advance(299)
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    assert not manager.completion_hold


@pytest.mark.asyncio
async def test_proven_new_storage_does_not_override_bad_solar_or_electrical_inputs():
    manager, adapter, clock, _ = await finished_with_tank_reference()
    clock.advance(900)
    await tick(manager, tank_observation=tank_observation(manager, clock, 53))
    clock.advance(300)
    await manager.tick(surplus_w=4000, grid_import_w=0, data_fresh=False, phase_allowed=False,
                       tank_observation=tank_observation(manager, clock, 53))
    assert not manager.completion_hold and not manager.desired_on
    assert len(adapter.calls) == 1
    clock.advance(120)
    await tick(manager, surplus=0, tank_observation=tank_observation(manager, clock, 53))
    assert len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_imported_duplicate_disabled_ordinary_binding_cannot_start_sg():
    manager, adapter, clock, runtime = fixture()
    runtime.configs = {"duplicate": {"id": "duplicate", "enabled": False,
                                     "control_entity": manager.settings["entity_id"]},
                       "healthy": {"id": "healthy", "enabled": True,
                                   "control_entity": "switch.healthy_fixture"}}
    runtime.faults = {}
    previous = deepcopy(runtime.configs)
    await tick(manager)
    clock.advance(120)
    await tick(manager)
    assert adapter.calls == [] and manager.state == "blocked"
    assert "één eigenaar" in manager.reason
    assert runtime.mode == "solar" and runtime.faults == {} and runtime.configs == previous


@pytest.mark.asyncio
async def test_imported_duplicate_disabled_battery_binding_cannot_start_sg():
    manager, adapter, clock, runtime = fixture()
    runtime.configs = {"healthy": {"id": "healthy", "enabled": True,
                                   "control_entity": "switch.healthy_fixture"}}
    runtime.battery_fleet = SimpleNamespace(configs={"battery": {"id": "battery",
        "enabled": False, "control_enabled": False, "number_entity": manager.settings["entity_id"]}})
    runtime.faults = {}
    previous = deepcopy(runtime.configs)
    await tick(manager)
    clock.advance(120)
    await tick(manager)
    assert adapter.calls == [] and manager.state == "blocked"
    assert "één eigenaar" in manager.reason
    assert runtime.mode == "solar" and runtime.faults == {} and runtime.configs == previous


@pytest.mark.asyncio
async def test_rearm_requires_a_real_new_report_at_end_of_confirmation_window():
    manager, adapter, clock, _ = await finished_with_tank_reference()
    clock.advance(900)
    await tick(manager, tank_observation=tank_observation(manager, clock, 52))
    clock.advance(250)
    second = tank_observation(manager, clock, 52)
    await tick(manager, tank_observation=second)
    clock.advance(50)
    await tick(manager, tank_observation=second)
    assert manager.completion_hold and len(adapter.calls) == 1
    clock.advance(1)
    await tick(manager, tank_observation=tank_observation(manager, clock, 52))
    assert not manager.completion_hold


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", ["ordinary", "battery"])
async def test_enable_rejects_duplicate_owner_before_live_settings_or_persistence(owner):
    manager, adapter, _, runtime = fixture(enabled=False)
    duplicate = {"enabled": False, "control_entity": manager.settings["entity_id"]}
    if owner == "ordinary":
        runtime.configs = {"duplicate": duplicate}
    else:
        runtime.battery_fleet = SimpleNamespace(configs={"duplicate": duplicate})
    called = []
    runtime.set_sg_enabled = called.append
    previous = deepcopy(manager.settings)
    with pytest.raises(HomeAssistantError, match="één eigenaar"):
        await manager.set_enabled(True)
    assert manager.settings == previous and manager.config is manager.settings
    assert called == [] and adapter.calls == [] and runtime.mode == "solar"


@pytest.mark.asyncio
async def test_rejected_enable_persistence_restores_live_policy_without_actuation():
    manager, adapter, clock, runtime = fixture(enabled=False)
    previous = deepcopy(manager.settings)
    entry_options = deepcopy(runtime.entry.options)

    async def reject_enable(enabled):
        assert enabled is True
        await asyncio.sleep(0)
        raise HomeAssistantError("Actuator authority rejected by runtime")

    runtime.set_sg_enabled = reject_enable
    with pytest.raises(HomeAssistantError, match="authority rejected"):
        await manager.set_enabled(True)
    assert manager.settings == previous and manager.config is manager.settings
    assert runtime.entry.options == entry_options and runtime.mode == "solar"
    await tick(manager)
    clock.advance(120)
    await tick(manager)
    assert adapter.calls == [] and not manager.auto_enabled and not manager.desired_on


@pytest.mark.asyncio
async def test_failed_disable_persistence_still_withdraws_contact_and_prevents_renewal():
    manager, adapter, clock, runtime = await boosted()

    async def reject_disable(enabled):
        assert enabled is False
        await asyncio.sleep(0)
        raise HomeAssistantError("Preference could not be saved")

    runtime.set_sg_enabled = reject_disable
    with pytest.raises(HomeAssistantError, match="could not be saved"):
        await manager.set_enabled(False)
    assert manager.settings["enabled"] is False and manager.config is manager.settings
    assert adapter.calls == [("on", 300), ("off", None)]
    assert not manager.owned and not manager.desired_on and adapter.on is False
    assert runtime.mode == "solar"
    clock.advance(1200)
    await tick(manager)
    assert adapter.calls == [("on", 300), ("off", None)]
