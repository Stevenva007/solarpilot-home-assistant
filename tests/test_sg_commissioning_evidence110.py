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
