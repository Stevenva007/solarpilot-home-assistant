"""Only a loaded, bound, proven semantic break creates an advisory notice."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.compatibility_notifications import CompatibilityNotifications
from test_runtime import build


def incompatible():
    return {"schema": 1, "provider_loaded": True, "native_device_registered": True,
            "compatibility_state": "incompatible", "reason_code": "provider_semantics_changed",
            "compatibility_detail": "operation_status_no_longer_special_status",
            "provider": {"integration_version": "9.8.7", "library_version": "3.2.1"}}


def compatible():
    return {"schema": 1, "provider_loaded": True, "native_device_registered": True,
            "compatibility_state": "compatible", "compatibility": {
                "schema": 1, "contract": "aquarea_special_status_action_v1", "verified": True,
                "basis": "loaded_source", "fingerprint": "a" * 64}}


def setup():
    runtime, hass = build()
    return runtime, hass, CompatibilityNotifications(runtime)


def notices(hass):
    return [call for call in hass.services.calls if call[0] == "persistent_notification"]


@pytest.mark.asyncio
async def test_normal_empty_or_compatible_install_has_no_notification_writes():
    _runtime, hass, reporter = setup()
    for value in ({}, compatible(), None):
        await reporter.sync(value)
    assert not hass.services.calls
    assert reporter.snapshot() == {"schema": 1, "active": False, "signature": ""}


@pytest.mark.asyncio
@pytest.mark.parametrize("patch", [
    {"provider_loaded": False}, {"provider_loaded": 1}, {"native_device_registered": False},
    {"native_device_registered": 1}, {"compatibility_state": "unknown"},
    {"reason_code": "provider_contract_unverified"}, {"reason_code": "provider_semantics_unavailable"},
    {"reason_code": "native_poll_not_current"}, {"reason_code": "native_source_not_current"},
    {"reason_code": "native_source_value_conflict"}, {"compatibility_detail": None},
    {"compatibility_detail": "unknown"},
])
async def test_unknown_offline_uninspectable_or_unbound_sources_never_alert(patch):
    _runtime, hass, reporter = setup()
    value = {**incompatible(), **patch}
    for _ in range(3):
        await reporter.sync(value)
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_proven_break_is_deduplicated_and_changed_provider_updates_same_notice():
    runtime, hass, reporter = setup()
    before = {"mode": runtime.mode, "faults": deepcopy(runtime.faults),
              "states": deepcopy(runtime.states), "sg": runtime.sg_boost.snapshot()}
    value = incompatible()
    for _ in range(20):
        await reporter.sync(value)
    assert len(notices(hass)) == 1
    text = notices(hass)[0][2]["message"]
    assert "9.8.7" in text and "Panasonic-statusfuncties" in text
    assert "Panasonic-comfortregeling blijft behouden" in text
    assert "geplande onderhoudscontrole" in text and "GitHub" in text
    assert "geïnstalleerd" not in text
    value["provider"]["integration_version"] = "9.8.8"
    await reporter.sync(value)
    assert len(notices(hass)) == 2
    assert {call[2]["notification_id"] for call in notices(hass)} == {reporter.notification_id}
    assert all(call[0] == "persistent_notification" for call in hass.services.calls)
    assert runtime.mode == before["mode"] and runtime.faults == before["faults"]
    assert runtime.states == before["states"] and runtime.sg_boost.snapshot() == before["sg"]


@pytest.mark.asyncio
async def test_unknown_later_state_preserves_notice_until_positive_contract_recovery():
    _runtime, hass, reporter = setup()
    await reporter.sync(incompatible())
    for value in ({}, {**incompatible(), "provider_loaded": False},
                  {**incompatible(), "reason_code": "native_source_not_current"}):
        await reporter.sync(value)
    assert [call[1] for call in notices(hass)] == ["create"]
    await reporter.sync(compatible())
    await reporter.sync(compatible())
    assert [call[1] for call in notices(hass)] == ["create", "dismiss"]
    assert notices(hass)[-1][2] == {"notification_id": reporter.notification_id}


@pytest.mark.asyncio
@pytest.mark.parametrize("patch", [
    {"schema": True}, {"schema": 2}, {"verified": 1}, {"verified": False},
    {"contract": "different"}, {"basis": "version_allowlist"},
    {"fingerprint": "bad"}, {"fingerprint": "A" * 64}, {"unexpected": "ignored"},
])
async def test_malformed_positive_proof_cannot_dismiss_existing_notice(patch):
    _runtime, hass, reporter = setup()
    await reporter.sync(incompatible())
    value = compatible()
    value["compatibility"].update(patch)
    await reporter.sync(value)
    assert [call[1] for call in notices(hass)] == ["create"]
    assert reporter.snapshot()["active"]


@pytest.mark.asyncio
async def test_delivery_failures_retry_without_controller_fault_or_log_spam(caplog):
    runtime, hass, reporter = setup()
    hass.services.fail = True
    for _ in range(3):
        await reporter.sync(incompatible())
    assert not reporter.snapshot()["active"]
    assert not runtime.faults and runtime.mode == "observe"
    assert len([row for row in caplog.records if "compatibiliteitsbericht" in row.message]) == 1
    hass.services.fail = False
    await reporter.sync(incompatible())
    await reporter.sync(incompatible())
    assert len(notices(hass)) == 4 and reporter.snapshot()["active"]
    hass.services.fail = True
    await reporter.sync(compatible())
    assert reporter.snapshot()["active"]
    hass.services.fail = False
    await reporter.sync(compatible())
    assert not reporter.snapshot()["active"]
    assert not runtime.faults and runtime.mode == "observe"


@pytest.mark.asyncio
async def test_missing_notification_service_waits_and_retries_when_available():
    _runtime, hass, reporter = setup()
    hass.services.has_service = lambda *_: False
    await reporter.sync(incompatible())
    assert not hass.services.calls
    hass.services.has_service = lambda *_: True
    await reporter.sync(incompatible())
    assert len(notices(hass)) == 1


@pytest.mark.asyncio
async def test_restored_receipt_resynchronizes_once_without_storing_provider_text():
    runtime, hass, reporter = setup()
    await reporter.sync(incompatible())
    receipt = reporter.snapshot()
    assert set(receipt) == {"schema", "active", "signature"}
    restored = CompatibilityNotifications(runtime)
    restored.restore(receipt)
    await restored.sync(incompatible())
    await restored.sync(incompatible())
    assert len(notices(hass)) == 2
    assert notices(hass)[0][2]["notification_id"] == notices(hass)[1][2]["notification_id"]
    await restored.sync(compatible())
    assert [call[1] for call in notices(hass)] == ["create", "create", "dismiss"]


@pytest.mark.asyncio
async def test_failed_receipt_save_does_not_resend_successful_notification(monkeypatch):
    runtime, hass, reporter = setup()
    save = runtime.store.async_delay_save
    attempts = []
    def fail_once(callback, delay):
        attempts.append(delay)
        if len(attempts) == 1:
            raise RuntimeError("Temporary receipt failure")
        save(callback, delay)
    monkeypatch.setattr(runtime.store, "async_delay_save", fail_once)
    await reporter.sync(incompatible())
    assert reporter.snapshot()["active"]
    await reporter.sync(incompatible())
    assert len(notices(hass)) == 1 and attempts == [1, 1]


@pytest.mark.parametrize("value", [
    None, [], {}, {"schema": True, "active": True, "signature": "a" * 64},
    {"schema": 1, "active": 1, "signature": "a" * 64},
    {"schema": 1, "active": True, "signature": "bad"},
    {"schema": 1, "active": False, "signature": "a" * 64},
])
def test_malformed_delivery_receipt_cannot_hide_new_incompatibility(value):
    _runtime, _hass, reporter = setup()
    reporter.restore(value)
    assert reporter.snapshot() == {"schema": 1, "active": False, "signature": ""}


@pytest.mark.asyncio
async def test_provider_labels_are_inert_markdown_and_bounded():
    _runtime, hass, reporter = setup()
    value = incompatible()
    value["provider"]["integration_version"] = "<img onerror=evil()> [bad](https://private) " + "x" * 1000
    await reporter.sync(value)
    text = notices(hass)[0][2]["message"]
    assert "<img" not in text and "[bad]" not in text and len(text) < 1000


@pytest.mark.asyncio
@pytest.mark.parametrize("detail", [
    "operation_status_mapping_changed",
    "action_or_status_getter_semantics_changed",
])
async def test_other_positively_inspected_contract_changes_get_one_notice(detail):
    _runtime, hass, reporter = setup()
    value = incompatible()
    value["compatibility_detail"] = detail
    for _ in range(3):
        await reporter.sync(value)
    assert [call[1] for call in notices(hass)] == ["create"]
    assert "gewijzigd of niet-herkend gegevenscontract" in notices(hass)[0][2]["message"]
    value["compatibility_state"] = "unknown"
    await reporter.sync(value)
    assert [call[1] for call in notices(hass)] == ["create"]
    await reporter.sync(compatible())
    assert [call[1] for call in notices(hass)] == ["create", "dismiss"]
