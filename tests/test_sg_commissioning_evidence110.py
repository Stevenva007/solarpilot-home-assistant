"""Firmware is advisory; fictional live device/timer checks still control SG."""
from copy import deepcopy
import json

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.sg_boost import COMMISSIONING_CHANGE_REASON, SGBoostManager
from custom_components.solar_pilot.sg_transport import ShellyLeaseError
from test_sg_controller62 import boosted, fixture, tick
from test_sg_transport62 import native, writes


async def changed_relay():
    manager, adapter, clock, runtime = fixture()
    adapter.fingerprint["version"] = "2.0.1"
    await manager.start()
    clock.advance(30)
    adapter.fingerprint.update(version="2.1.0", firmware_id="fixture-build-v2")
    await manager._read(force=True)
    return manager, adapter, clock, runtime


def legacy_fault(manager):
    saved = manager.snapshot()
    saved["commissioned_fingerprint"] = deepcopy(saved["fingerprint_change"]["commissioned_fingerprint"])
    saved["fault_code"] = "firmware_changed"
    saved.pop("fingerprint_change")
    saved.pop("observed_fingerprint")
    saved["firmware_recovery_pending"] = False
    manager.settings["commissioning_confirmed"] = False
    manager.settings["watchdog_confirmed"] = False
    manager._persist_settings()
    return saved


def restarted(runtime, adapter, clock, saved):
    manager = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = manager
    runtime._snapshot = lambda: {"sg_boost": manager.snapshot()}
    manager.restore(saved)
    return manager


@pytest.mark.asyncio
async def test_firmware_only_allows_start_without_manual_reconfirmation():
    manager, adapter, clock, _ = await changed_relay()
    assert not manager.fault and manager.settings["commissioning_confirmed"] and manager.settings["watchdog_confirmed"]
    await tick(manager)
    clock.advance(manager.settings["start_delay_s"])
    await tick(manager)
    assert manager.owned and manager.desired_on and adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_change_is_saved_as_advisory_while_relay_stays_off():
    manager, adapter, clock, runtime = await changed_relay()
    saved = runtime.store.saves[-1]["sg_boost"]
    assert saved["fault_code"] == ""
    assert saved["fingerprint_change"]["detected_at"] == clock()
    assert saved["fingerprint_change"]["commissioned_fingerprint"]["version"] == "2.0.1"
    assert saved["observed_fingerprint"] == adapter.fingerprint
    assert saved["commissioned_fingerprint"] == adapter.fingerprint
    assert saved == manager.snapshot() and adapter.calls == []


@pytest.mark.asyncio
async def test_summary_contains_field_names_and_versions_without_device_identifiers():
    manager, _, clock, _ = await changed_relay()
    view = manager.overview()["commissioning_diagnostic"]
    assert not view["active"] and view["read_only"] and view["evidence_available"]
    assert view["firmware_only"] and view["verification"] == "verified" and view["automatic"]
    assert view["detected_at"] == clock()
    assert view["changed_fields"] == ["firmware_id", "version"]
    assert view["previous_version"] == "2.0.1" and view["observed_version"] == "2.1.0"
    assert view["current_observed_version"] == "2.1.0"
    summary = json.dumps(view)
    for private in ("fictional-relay", "fixture-model", "fixture-app", "fixture-build-v2", "fixture-v1"):
        assert private not in summary


@pytest.mark.asyncio
async def test_repeat_reads_and_display_do_not_move_the_first_detection_time():
    manager, adapter, clock, runtime = await changed_relay()
    original = deepcopy(manager.snapshot()["fingerprint_change"])
    saved_count = len(runtime.store.saves)
    for _ in range(3):
        clock.advance(60)
        await manager._read(force=True)
        manager.overview()
    assert manager.snapshot()["fingerprint_change"] == original
    assert len(runtime.store.saves) == saved_count and adapter.calls == []


@pytest.mark.asyncio
async def test_later_version_preserves_original_mismatch_and_records_latest_observation():
    manager, adapter, clock, runtime = await changed_relay()
    original = deepcopy(manager.snapshot()["fingerprint_change"])
    clock.advance(60)
    adapter.fingerprint.update(version="2.2.0", firmware_id="fixture-build-v3")
    await manager._read(force=True)
    assert manager.snapshot()["fingerprint_change"] == original
    assert runtime.store.saves[-1]["sg_boost"]["observed_fingerprint"] == adapter.fingerprint
    diag = manager.overview()["commissioning_diagnostic"]
    assert diag["observed_version"] == "2.1.0" and diag["current_observed_version"] == "2.2.0"
    assert not manager.fault


@pytest.mark.asyncio
async def test_firmware_rollback_and_app_label_change_are_also_advisory():
    manager, adapter, clock, _ = await changed_relay()
    original = deepcopy(manager.snapshot()["fingerprint_change"])
    clock.advance(60)
    adapter.fingerprint = deepcopy(original["commissioned_fingerprint"])
    adapter.fingerprint["app"] = "fixture-new-app-label"
    await manager._read(force=True)
    assert manager.snapshot()["fingerprint_change"] == original
    assert manager.settings["commissioning_confirmed"] and not manager.fault and adapter.calls == []


@pytest.mark.asyncio
async def test_restart_preserves_advisory_and_requires_a_current_read_before_verified():
    prior, adapter, clock, runtime = await changed_relay()
    saved = prior.snapshot()
    clock.advance(600)
    manager = restarted(runtime, adapter, clock, saved)
    assert manager.overview()["commissioning_diagnostic"]["verification"] == "pending"
    await manager.start()
    assert manager.overview()["commissioning_diagnostic"]["verification"] == "verified"
    assert manager.snapshot()["fingerprint_change"] == saved["fingerprint_change"]
    assert not manager.owned and not manager.desired_on and adapter.calls == []


@pytest.mark.asyncio
async def test_legacy_firmware_fault_repairs_only_after_fresh_same_hardware_read():
    prior, adapter, clock, runtime = await changed_relay()
    manager = restarted(runtime, adapter, clock, legacy_fault(prior))
    assert manager.fault_code == "firmware_changed" and not manager.settings["watchdog_confirmed"]
    await manager.start()
    diag = manager.overview()["commissioning_diagnostic"]
    assert not manager.fault and manager.settings["commissioning_confirmed"] and manager.settings["watchdog_confirmed"]
    assert diag["evidence_available"] and diag["detected_at"] is None and diag["automatic"]
    assert not manager.owned and not manager.desired_on and adapter.calls == []


@pytest.mark.asyncio
async def test_legacy_firmware_fault_with_unavailable_read_never_grants_permissions():
    prior, adapter, clock, runtime = await changed_relay()
    manager = restarted(runtime, adapter, clock, legacy_fault(prior))
    adapter.online = False
    await manager.start()
    assert not manager.settings["watchdog_confirmed"] and not manager.settings["commissioning_confirmed"]
    assert manager.overview()["commissioning_diagnostic"]["verification"] == "pending"
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_legacy_recovery_waits_for_actual_setup_then_heals_without_manual_confirmation():
    prior, adapter, clock, runtime = await changed_relay()
    manager = restarted(runtime, adapter, clock, legacy_fault(prior))
    adapter.configured = False
    await manager.start()
    assert manager.fault_code == "setup_invalid" and not manager.settings["watchdog_confirmed"]
    pending = manager.snapshot()
    manager = restarted(runtime, adapter, clock, pending)
    adapter.configured = True
    await manager.start()
    assert not manager.fault and manager.settings["watchdog_confirmed"]
    assert not manager.owned and adapter.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("detected", [True, float("nan"), float("inf"), -1, 1_900_000_000.0, "private-id"])
async def test_invalid_stored_detection_time_cannot_become_historical_proof(detected):
    prior, adapter, clock, runtime = await changed_relay()
    saved = prior.snapshot()
    saved["fingerprint_change"]["detected_at"] = detected
    manager = restarted(runtime, adapter, clock, saved)
    diag = manager.overview()["commissioning_diagnostic"]
    assert not diag["evidence_available"] and diag["detected_at"] is None
    assert not manager.owned


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["private-relay-id", "<script>2.1</script>", "1"*1000+".0", True, None])
async def test_unexpected_version_metadata_is_not_exposed_or_a_new_blocker(version):
    manager, adapter, clock, _ = await changed_relay()
    clock.advance(30)
    adapter.fingerprint["version"] = version
    await manager._read(force=True)
    assert manager.overview()["commissioning_diagnostic"]["current_observed_version"] is None
    assert not manager.fault and manager.settings["watchdog_confirmed"]


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("device_id", "different-fixture"), ("model", "other-model"),
    ("gen", 3), ("profile", "cover"), ("component", "switch:1")])
async def test_actual_hardware_or_role_change_remains_a_specific_actionable_block(field, value):
    manager, adapter, _, _ = await changed_relay()
    adapter.fingerprint[field] = value
    await tick(manager)
    assert manager.fault_code == "commissioning_changed"
    assert manager.overview()["reason"] == COMMISSIONING_CHANGE_REASON
    assert not manager.settings["commissioning_confirmed"] and not manager.settings["watchdog_confirmed"]
    with pytest.raises(HomeAssistantError):
        await manager.resume_automation()
    assert not manager.owned and adapter.calls == []


@pytest.mark.asyncio
async def test_no_legacy_fault_means_user_withdrawn_confirmation_stays_withdrawn():
    manager, adapter, _, _ = await changed_relay()
    manager.settings["watchdog_confirmed"] = False
    manager._persist_settings()
    adapter.fingerprint["firmware_id"] = "fixture-build-v3"
    await manager._read(force=True)
    assert not manager.fault and not manager.settings["watchdog_confirmed"] and adapter.calls == []


@pytest.mark.asyncio
async def test_hardware_change_then_firmware_change_cannot_automatically_accept_new_hardware():
    manager, adapter, _, _ = await changed_relay()
    adapter.fingerprint["device_id"] = "different-fixture"
    await manager._read(force=True)
    adapter.fingerprint["firmware_id"] = "fixture-build-v3"
    await manager._read(force=True)
    assert manager.fault_code == "commissioning_changed"
    assert not manager.settings["watchdog_confirmed"] and adapter.calls == []


@pytest.mark.asyncio
async def test_changed_binding_is_not_a_firmware_exception_and_explicit_confirmation_can_rebind():
    manager, adapter, _, _ = fixture()
    original_status = adapter.status
    binding = ["a"*64]
    adapter.status = lambda: {**original_status(), "binding_identity": binding[0]}
    await manager.start()
    binding[0] = "b"*64
    adapter.fingerprint["version"] = "2.0.0"
    await manager._read(force=True)
    assert manager.fault_code == "commissioning_changed"
    assert not manager.settings["watchdog_confirmed"]
    manager.update_config({**manager.settings, "commissioning_confirmed": True, "watchdog_confirmed": True})
    await manager._read(force=True)
    assert not manager.fault and manager._commissioned_binding_identity == binding[0]
    assert manager.settings["watchdog_confirmed"] and adapter.calls == []


@pytest.mark.asyncio
async def test_legacy_firmware_fault_cannot_heal_when_physical_hardware_changed():
    prior, adapter, clock, runtime = await changed_relay()
    saved = legacy_fault(prior)
    adapter.fingerprint["device_id"] = "different-fixture"
    manager = restarted(runtime, adapter, clock, saved)
    await manager.start()
    assert manager.fault_code == "commissioning_changed"
    assert not manager.settings["commissioning_confirmed"] and not manager.settings["watchdog_confirmed"]
    assert not manager.owned and adapter.calls == []


@pytest.mark.asyncio
async def test_external_on_deadline_is_preserved_without_owner_or_pulse():
    manager, adapter, clock, _ = fixture()
    adapter.on = True
    await manager.start()
    original = deepcopy(manager._external_control)
    deadline = manager._external_deadline
    clock.advance(30)
    adapter.fingerprint["firmware_id"] = "fixture-new-firmware"
    await tick(manager)
    assert manager._external_control["created_at"] == original["created_at"]
    assert manager._external_control["expires_at"] == original["expires_at"]
    assert manager._external_deadline == deadline
    assert manager._external_control["fingerprint"] == adapter.fingerprint
    assert not manager.owned and not manager.manual_hold and adapter.calls == []


@pytest.mark.asyncio
async def test_manual_on_choice_keeps_original_deadline_during_firmware_update():
    manager, adapter, clock, _ = fixture()
    await manager.set_manual_control("on", 1800)
    await tick(manager)
    origin, deadline = manager._session_started, manager._manual_deadline
    calls = list(adapter.calls)
    original = deepcopy(manager._manual_control)
    clock.advance(30)
    adapter.fingerprint["firmware_id"] = "fixture-new-firmware"
    await tick(manager)
    assert manager.manual_mode == "on" and manager._manual_deadline == deadline
    assert manager._manual_control["expires_at"] == original["expires_at"]
    assert manager._session_started == origin and manager.owned and not manager.fault
    assert adapter.calls == calls


@pytest.mark.asyncio
async def test_saved_active_checkpoint_can_keep_same_live_timer_after_firmware_update():
    prior, adapter, clock, runtime = await boosted()
    saved = prior.snapshot()
    calls = list(adapter.calls)
    expiry = prior._lease_expiry
    clock.advance(30)
    adapter.fingerprint["firmware_id"] = "fixture-new-firmware"
    manager = restarted(runtime, adapter, clock, saved)
    await manager.start()
    assert manager._restart_resume["fingerprint"] == adapter.fingerprint
    await tick(manager)
    assert manager.owned and manager.desired_on and manager._lease_expiry == expiry
    assert adapter.calls == calls


@pytest.mark.asyncio
async def test_firmware_metadata_does_not_replace_actual_local_timer_proof():
    manager, adapter, _, _ = await boosted()
    adapter.fingerprint["firmware_id"] = "fixture-new-firmware"
    adapter.expiry = adapter.start = adapter.duration = None
    await tick(manager)
    assert not manager.owned and manager.fault_code == "lease_invalid"
    assert adapter.calls[-1] == ("off", None)


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("ver", None), ("fw_id", ""), ("app", None)])
async def test_missing_firmware_labels_do_not_disable_actual_supported_output(native, field, value):
    native.device.info[field] = value
    status = await native.adapter.get_status()
    assert status["setup_valid"] and status["fingerprint"][{"ver": "version", "fw_id": "firmware_id", "app": "app"}[field]] is None
    assert (await native.adapter.set_on(300))["lease_proven"]


@pytest.mark.asyncio
async def test_real_configuration_error_is_still_checked_after_upgrade(native):
    await native.adapter.get_status()
    native.device.info.update(ver="2.2.0", fw_id="fixture-build-v3", app="fixture-app-v3")
    native.device.config["auto_on"] = True
    assert not (await native.adapter.get_status())["setup_valid"]
    with pytest.raises(ShellyLeaseError):
        await native.adapter.set_on(300)
    assert writes(native) == []


async def active_with_boot_proof(**settings):
    manager, adapter, clock, runtime = fixture(**settings)
    device_boot = [clock()-10_000]
    original_status = adapter.status
    adapter.status = lambda: {**original_status(), "device_unixtime": clock(),
                              "device_uptime_s": clock()-device_boot[0]}
    await tick(manager)
    clock.advance(manager.settings["start_delay_s"])
    await tick(manager)
    assert manager.owned
    return manager, adapter, clock, runtime, device_boot


def reboot_relay(adapter, clock, device_boot):
    device_boot[0] = clock()-5
    adapter.fingerprint.update(version="3.0.0", firmware_id="fixture-reboot-build")
    adapter.on = False
    adapter.start = adapter.duration = adapter.expiry = None


@pytest.mark.asyncio
async def test_proven_firmware_reboot_off_waits_for_fresh_solar_without_manual_hold():
    manager, adapter, clock, _, device_boot = await active_with_boot_proof(profile="general", profile_confirmed=True,
                                                                        cooling_protection_confirmed=True)
    origin, minimum = manager._session_started, manager._minimum_started
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    assert not manager.owned and not manager.desired_on and not manager.manual_hold
    assert not manager.completion_hold and not manager.fault
    # General automatic solar operation no longer inherits a one-hour cap.
    # This real physical OFF ends the old episode; a new request still needs
    # fresh stability and a new proven bounded local lease.
    assert manager._firmware_reboot is None
    assert manager._last_session["duration_s"] == 30
    assert len(adapter.calls) == 1 and manager.state == "waiting_surplus"
    clock.advance(manager.settings["start_delay_s"]-1)
    await tick(manager)
    assert len(adapter.calls) == 1
    clock.advance(1)
    await tick(manager)
    assert manager.owned and manager._session_started == clock() > origin
    assert manager._minimum_started >= manager._session_started > minimum
    assert manager._firmware_reboot is None and len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_reboot_recovery_never_restarts_the_original_maximum_session():
    manager, adapter, clock, _, device_boot = await active_with_boot_proof(max_session_s=300, min_session_s=0)
    origin = manager._session_started
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    deadline = manager._firmware_reboot["deadline"]
    assert deadline == origin+300
    clock.advance(manager.settings["start_delay_s"])
    await tick(manager)
    assert manager.owned and manager._session_started == origin
    assert adapter.calls[-1] == ("on", 130)
    assert manager._lease_deadline <= deadline


@pytest.mark.asyncio
async def test_waiting_past_original_maximum_keeps_completed_session_protection():
    manager, adapter, clock, _, device_boot = await active_with_boot_proof(max_session_s=300, min_session_s=0)
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager, surplus=0)
    clock.advance(271)
    await tick(manager)
    assert manager._firmware_reboot["state"] == "expired"
    assert manager.completion_hold and manager._hold_reason == "session_limit"
    assert not manager.owned and len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_manual_on_reboot_needs_new_stability_without_extending_manual_expiry():
    manager, adapter, clock, _, device_boot = await active_with_boot_proof()
    await manager.set_manual_control("on", 1800)
    original = deepcopy(manager._manual_control)
    manual_deadline = manager._manual_deadline
    origin = manager._session_started
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    calls = list(adapter.calls)
    assert not manager.owned and manager.manual_mode == "on" and not manager.manual_hold
    assert manager._manual_deadline == manual_deadline
    clock.advance(manager.settings["start_delay_s"])
    await tick(manager)
    assert manager.owned and len(adapter.calls) == len(calls)+1
    assert manager._manual_control["expires_at"] == original["expires_at"]
    assert manager._manual_deadline == manual_deadline and manager._session_started == origin


@pytest.mark.asyncio
async def test_waiting_reboot_record_restores_as_evidence_without_new_ownership_or_time():
    manager, adapter, clock, runtime, device_boot = await active_with_boot_proof()
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    saved = manager.snapshot()
    clock.advance(30)
    restored = restarted(runtime, adapter, clock, saved)
    await restored.start()
    assert not restored.owned and not restored.desired_on
    assert all(restored._firmware_reboot[key] == saved["firmware_reboot"][key] for key in ("started_at", "minimum_started_at", "deadline", "detected_at"))
    assert restored._firmware_reboot["remaining_cap_s"] <= saved["firmware_reboot"]["remaining_cap_s"]
    await tick(restored)
    assert not restored.owned and len(adapter.calls) == 1
    clock.advance(restored.settings["start_delay_s"])
    await tick(restored)
    assert restored.owned and restored._session_started == saved["firmware_reboot"]["started_at"]


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["uptime", "clock", "previous", "stale", "clock_back", "clock_jump", "ha_back",
                                     "no_reset", "no_firmware", "expired", "binding", "setup"])
async def test_unproven_firmware_off_keeps_manual_off_protection(missing):
    manager, adapter, clock, _, device_boot = await active_with_boot_proof()
    original_status = adapter.status
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    if missing == "previous":
        manager._boot_observation = None
    elif missing == "stale":
        clock.advance(manager.settings["stale_s"]+1)
    elif missing == "ha_back":
        clock.advance(-60)
        manager._next_read = 0
    elif missing == "no_reset":
        device_boot[0] = clock()-10_000
    elif missing == "no_firmware":
        adapter.fingerprint = deepcopy(manager._commissioned_fingerprint)
    elif missing == "expired":
        clock.advance(301)
    elif missing == "setup":
        adapter.configured = False
    else:
        change = {"uptime": {"device_uptime_s": None}, "clock": {"device_unixtime": None},
                  "clock_back": {"device_unixtime": manager._boot_observation["clock"]-1},
                  "clock_jump": {"device_unixtime": clock()+100}, "binding": {"binding_identity": "b"*64}}[missing]
        adapter.status = lambda: {**original_status(), **change}
    await tick(manager)
    assert manager._firmware_reboot is None
    assert not manager.owned and len(adapter.calls) == 1
    assert manager.manual_hold or manager.fault or missing == "expired"


@pytest.mark.asyncio
async def test_external_contact_firmware_reboot_does_not_grant_owned_recovery():
    manager, adapter, clock, _ = fixture()
    device_boot = [clock()-10_000]
    original_status = adapter.status
    adapter.status = lambda: {**original_status(), "device_unixtime": clock(), "device_uptime_s": clock()-device_boot[0]}
    adapter.on = True
    await manager.start()
    await tick(manager)
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    assert manager._firmware_reboot is None and manager.manual_hold
    assert not manager.owned and adapter.calls == []


@pytest.mark.asyncio
async def test_reboot_during_an_ordinary_completed_session_cannot_remove_completion_hold():
    manager, adapter, clock, _, device_boot = await active_with_boot_proof()
    manager.completion_hold = True
    manager._hold_reason = "session_limit"
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    assert manager._firmware_reboot is None and manager.completion_hold
    assert not manager.owned and len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_live_wall_clock_rollback_cannot_move_recovery_session_or_maximum():
    manager, adapter, clock, _, device_boot = await active_with_boot_proof(max_session_s=300, min_session_s=0)
    origin, minimum = manager._session_started, manager._minimum_started
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    deadline = manager._firmware_reboot_deadline()
    manager._wall_clock = lambda: clock()-100
    clock.advance(120)
    await manager._issue_on()
    assert manager.owned and manager._session_started == origin and manager._minimum_started == minimum
    assert manager._lease_deadline <= deadline and adapter.calls[-1] == ("on", 130)


@pytest.mark.asyncio
async def test_saved_remaining_cap_keeps_original_elapsed_minimum_and_maximum_after_restore():
    manager, adapter, clock, runtime, device_boot = await active_with_boot_proof(max_session_s=300, min_session_s=0)
    origin, minimum = manager._session_started, manager._minimum_started
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    deadline = manager._firmware_reboot_deadline()
    clock.advance(120)
    manager._wall_clock = lambda: clock()-100
    saved = manager.snapshot()
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    restored._wall_clock = manager._wall_clock
    restored.restore(saved)
    assert restored._firmware_reboot_anchor == {"origin": origin, "minimum": minimum, "deadline": deadline}
    assert not restored.owned


@pytest.mark.asyncio
async def test_snapshot_wall_highwater_and_remaining_cap_cannot_move_backwards():
    manager, adapter, clock, _, device_boot = await active_with_boot_proof()
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    clock.advance(20)
    first = manager.snapshot()["firmware_reboot"]
    manager._wall_clock = lambda: clock()-10
    clock.advance(5)
    second = manager.snapshot()["firmware_reboot"]
    assert second["observed_at"] == first["observed_at"]
    assert second["remaining_cap_s"] < first["remaining_cap_s"]


@pytest.mark.asyncio
@pytest.mark.parametrize("section,key,value", [
    ("boot_observation", "observed_at", "123"), ("boot_observation", "clock", True),
    ("boot_observation", "uptime", float("nan")), ("boot_observation", "uptime", 10**400),
    ("firmware_reboot", "state", {}), ("firmware_reboot", "started_at", "123"),
    ("firmware_reboot", "deadline", float("inf")), ("firmware_reboot", "remaining_cap_s", True),
])
async def test_corrupt_recovery_or_boot_journal_is_rejected_without_crash_or_new_on(section, key, value):
    manager, adapter, clock, runtime, device_boot = await active_with_boot_proof()
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    saved = manager.snapshot()
    saved[section][key] = value
    restored = restarted(runtime, adapter, clock, saved)
    if section == "firmware_reboot":
        assert restored._firmware_reboot_invalid
        clock.advance(restored.settings["start_delay_s"])
        await tick(restored)
        assert not restored._on_permission_current(restored._generation)
        assert "herstelgegevens" in restored.reason and not restored.owned
    else:
        assert restored._boot_observation is None and not restored.owned
    assert len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_restore_before_saved_wall_highwater_enters_targeted_hold_and_can_be_explicitly_resumed():
    manager, adapter, clock, runtime, device_boot = await active_with_boot_proof()
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    clock.advance(30)
    saved = manager.snapshot()
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    restored._wall_clock = lambda: clock()-10
    restored.restore(saved)
    assert restored._firmware_reboot_invalid and not restored.owned
    await restored.start()
    await restored.resume_automation()
    assert not restored._firmware_reboot_invalid and restored._firmware_reboot is None
    assert not restored.owned and len(adapter.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("uptime,expected", [(500, 500.0), (None, None), ("500", None), (True, None),
                                           (float("nan"), None), (-1, None), (10**400, None)])
async def test_native_sys_uptime_is_optional_strictly_numeric_boot_evidence(native, uptime, expected):
    original_rpc = native.device.call_rpc
    async def with_uptime(method, params=None, timeout=None):
        result = await original_rpc(method, params=params, timeout=timeout)
        return {**result, "uptime": uptime} if method == "Sys.GetStatus" else result
    native.device.call_rpc = with_uptime
    status = await native.adapter.get_status()
    assert status["device_uptime_s"] == expected and status["setup_valid"]
    assert writes(native) == []


@pytest.mark.asyncio
async def test_completed_recovered_episode_does_not_cap_a_later_genuine_sg_session():
    manager, adapter, clock, _, device_boot = await active_with_boot_proof(max_session_s=300, min_session_s=0)
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await tick(manager)
    clock.advance(manager.settings["start_delay_s"])
    await tick(manager)
    assert manager.owned and manager._firmware_reboot["state"] == "resumed"
    await manager._release("Fictionele oude aanvraag afgerond", rest=False, policy_hold=False)
    assert manager._firmware_reboot is None and manager._firmware_reboot_anchor is None
    clock.advance(400)
    await tick(manager)
    clock.advance(manager.settings["start_delay_s"])
    await tick(manager)
    origin = manager._session_started
    assert manager.owned and manager._firmware_reboot_deadline() is None
    clock.advance(1)
    await tick(manager)
    assert manager.owned and manager._session_started == origin


@pytest.mark.asyncio
async def test_first_durable_reboot_read_commits_old_lease_end_and_bounded_wait_atomically():
    manager, adapter, clock, runtime, device_boot = await active_with_boot_proof()
    clock.advance(30)
    reboot_relay(adapter, clock, device_boot)
    await manager._read(force=True)
    saved = runtime.store.saves[-1]["sg_boost"]
    assert not saved["owned"] and saved["session_checkpoint"] is None
    assert saved["firmware_reboot"]["state"] == "waiting" and not saved["manual_hold"]
    restored = restarted(runtime, adapter, clock, saved)
    await restored.start()
    assert not restored.owned and not restored.manual_hold
    assert restored._firmware_reboot["deadline"] == saved["firmware_reboot"]["deadline"]
