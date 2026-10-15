"""Analysis stays readable without alerts; only existing urgent reporters notify."""
from copy import deepcopy
import time

import pytest

from custom_components.solar_pilot.learning_hub import LearningHub
from test_runtime import build


def calls(hass):
    return [call for call in hass.services.calls if call[0] == "persistent_notification"]


def legacy(runtime, **changes):
    value = {**runtime.learning_hub.snapshot(), "notification_signature": "a" * 32,
             "last_notification": time.time() - 90000}
    value.update(changes)
    runtime.learning_hub.restore(value)


@pytest.mark.asyncio
@pytest.mark.parametrize("opt_in", [False, True])
async def test_new_and_changed_findings_remain_silent_across_days(opt_in, monkeypatch):
    runtime, hass = build()
    hub = runtime.learning_hub
    hub.policy["notifications"] = opt_in
    base = time.time()
    for day in range(4):
        monkeypatch.setattr(time, "time", lambda: base + day * 90000)
        runtime.settings["grid_entity"] = f"sensor.test_grid_{day}"
        hub.refresh(force=True)
        await hub.tick()
        assert hub.summary()["analysis_needed"]
        assert hub.summary()["findings"]
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("opt_in", [False, True])
async def test_upgrade_dismisses_only_the_old_analysis_id_once_and_keeps_findings(opt_in):
    runtime, hass = build()
    hub = runtime.learning_hub
    legacy(runtime, policy={**hub.policy, "notifications": opt_in})
    before = deepcopy(hub.refresh(force=True)["questions"])
    for _ in range(5):
        await hub.tick()
    assert calls(hass) == [("persistent_notification", "dismiss", {
        "notification_id": "solar_pilot_learning_test"})]
    assert hub.refresh(force=True)["questions"] == before
    assert not hub.notification_signature and hub.last_notification == 0
    assert not runtime.faults and not runtime.problem
    assert hass.states.get("switch.load").state == "off"


@pytest.mark.asyncio
async def test_legacy_optin_without_delivery_receipt_still_cleans_up_once():
    runtime, hass = build()
    legacy(runtime, notification_signature="", last_notification=0,
           policy={**runtime.learning_hub.policy, "notifications": True})
    await runtime.learning_hub.tick()
    await runtime.learning_hub.tick()
    assert [call[1] for call in calls(hass)] == ["dismiss"]


@pytest.mark.asyncio
async def test_unavailable_notification_service_keeps_cleanup_pending():
    runtime, hass = build()
    legacy(runtime)
    hass.services.has_service = lambda *_args: False
    await runtime.learning_hub.tick()
    assert runtime.learning_hub.notification_signature and not calls(hass)
    hass.services.has_service = lambda *_args: True
    await runtime.learning_hub.tick()
    await runtime.learning_hub.tick()
    assert [call[1] for call in calls(hass)] == ["dismiss"]


@pytest.mark.asyncio
async def test_failed_cleanup_is_retried_without_pausing_or_repeated_log_spam(caplog):
    runtime, hass = build()
    legacy(runtime)
    hass.services.fail = True
    for _ in range(3):
        await runtime.learning_hub.tick()
    assert runtime.learning_hub.notification_signature
    assert not runtime.problem and not runtime.faults and runtime.mode == "observe"
    assert len([record for record in caplog.records if "analysemelding" in record.message]) == 1
    hass.services.fail = False
    await runtime.learning_hub.tick()
    await runtime.learning_hub.tick()
    assert [call[1] for call in calls(hass)] == ["dismiss"] * 4
    assert not runtime.learning_hub.notification_signature


@pytest.mark.asyncio
async def test_receipt_save_failure_does_not_repeat_an_accepted_dismissal(monkeypatch):
    runtime, hass = build()
    legacy(runtime)
    runtime.data_loaded = True
    runtime.learning_hub.refresh(force=True)
    original = runtime.store.async_delay_save
    attempts = []

    def fail_once(callback, delay):
        attempts.append(delay)
        if len(attempts) == 1:
            raise RuntimeError("Synthetic storage failure")
        original(callback, delay)

    monkeypatch.setattr(runtime.store, "async_delay_save", fail_once)
    await runtime.learning_hub.tick()
    await runtime.learning_hub.tick()
    await runtime.learning_hub.tick()
    assert [call[1] for call in calls(hass)] == ["dismiss"]
    assert attempts == [60, 60]
    restored = LearningHub(runtime)
    restored.restore(runtime.learning_hub.snapshot())
    await restored.tick()
    assert [call[1] for call in calls(hass)] == ["dismiss"]


@pytest.mark.asyncio
async def test_urgent_fault_survives_analysis_cleanup_and_dismisses_after_recovery():
    runtime, hass = build()
    legacy(runtime)
    runtime.faults["a"] = "Bevestigde toestelstoring"
    await runtime.action_notifications.sync()
    await runtime.learning_hub.tick()
    await runtime.action_notifications.sync()
    assert [(call[1], call[2]["notification_id"]) for call in calls(hass)] == [
        ("create", "solar_pilot_test_action_required"),
        ("dismiss", "solar_pilot_learning_test")]
    assert "Bevestigde toestelstoring" in calls(hass)[0][2]["message"]
    runtime.faults.clear()
    await runtime.action_notifications.sync()
    assert calls(hass)[-1] == ("persistent_notification", "dismiss", {
        "notification_id": "solar_pilot_test_action_required"})
    assert all(call[0] == "persistent_notification" for call in hass.services.calls)
