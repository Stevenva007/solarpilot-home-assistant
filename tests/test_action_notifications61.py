"""Action-required HA messages; real reporter with HA API doubles only."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.action_notifications import ActionRequiredNotifications
from test_runtime import build


def setup():
    runtime, hass = build()
    notices = ActionRequiredNotifications(runtime)
    runtime.action_notifications = notices
    return runtime, hass, notices


def calls(hass):
    return [call for call in hass.services.calls if call[0] == "persistent_notification"]


@pytest.mark.asyncio
async def test_new_clean_install_does_not_write_or_dismiss_anything():
    runtime, hass, notices = setup()
    for _ in range(3):
        await notices.sync()
    assert not hass.services.calls
    assert notices.snapshot() == {"schema": 1, "active": False, "signature": ""}


@pytest.mark.asyncio
@pytest.mark.parametrize("cause", ["", "user", "legacy", "removal"])
async def test_normal_pause_and_source_waits_are_not_manual_faults(cause):
    runtime, hass, notices = setup()
    runtime.pause_cause = cause
    runtime.problem = "Wacht op ontbrekende toestelgegevens"
    runtime.problem_kind = "source_wait"
    runtime.states["a"].available = False
    runtime.states["a"].fault = "Vermogensmeting onbetrouwbaar"
    runtime.sg_boost.reason = "Wacht op betrouwbare huidige zonnegegevens"
    await notices.sync()
    assert not hass.services.calls






@pytest.mark.asyncio
async def test_all_durable_controller_faults_are_collated_once_and_deterministically():
    runtime, hass, notices = setup()
    runtime.faults["a"] = "Geen opdrachtbevestiging"
    runtime.reclaim_blocks["a"] = "Geen opdrachtbevestiging"
    runtime.sg_boost.fault = "SG-contact niet bevestigd"
    runtime.sg_boost.fault_code = "ack_failed"
    runtime.battery_fleet.configs["b"] = {"name": "Testbatterij"}
    runtime.battery_fleet.state.faults["b"] = "Batterijopdracht niet bevestigd"
    await notices.sync()
    message = calls(hass)[0][2]["message"]
    assert message.count("Geen opdrachtbevestiging") == 1
    assert "Testtoestel" in message and "Toestellen" in message
    assert "SG-contact niet bevestigd" in message and "Warmtepomp — Panasonic-regeling" in message
    assert "Testbatterij" in message and "SolarPilot → Batterij" in message
    assert message == notices.message()
    assert all(call[0] == "persistent_notification" for call in hass.services.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("cause,fragment", [
    ("internal_fault", "Instellingen → Systeem → Logboeken"),
    ("command_fault", "Regeling blijft gepauzeerd na een opdrachtfout"),
])
async def test_actual_fault_pause_explains_what_the_user_must_do(cause, fragment):
    runtime, hass, notices = setup()
    runtime.pause_cause = cause
    await notices.sync()
    message = calls(hass)[0][2]["message"]
    assert fragment in message
    assert "Automatisch regelen" in message


@pytest.mark.asyncio
async def test_typed_hard_source_configuration_notifies_but_retryable_source_wait_does_not():
    runtime, hass, notices = setup()
    runtime.problem_kind = "source_configuration"
    runtime.problem = "Testtoestel: vermogensmeter is niet exclusief voor dit toestel"
    await notices.sync()
    message = calls(hass)[0][2]["message"]
    assert "Toestellen beheren" in message and "exclusieve vermogensmeter" in message
    assert "Controle afronden herstelt deze koppeling niet" in message
    runtime.problem_kind = "source_wait"
    runtime.problem = "Wacht op nieuwe betrouwbare vermogensrapportage"
    await notices.sync()
    assert [call[1] for call in calls(hass)] == ["create", "dismiss"]


@pytest.mark.asyncio
async def test_actual_legacy_regulator_conflict_notifies_and_resolves_without_switching_it():
    runtime, hass, notices = setup()
    hass.states.set("switch.pv_excess_control_control_enabled", "on")
    await notices.sync()
    message = calls(hass)[0][2]["message"]
    assert "Dubbele regeling actief" in message and "PV Excess Control hoofdregeling" in message
    assert "Kies welke regeling" in message and "oude regeling" in message
    assert hass.states.get("switch.pv_excess_control_control_enabled").state == "on"
    hass.states.set("switch.pv_excess_control_control_enabled", "off")
    await notices.sync()
    assert [call[1] for call in calls(hass)] == ["create", "dismiss"]
    assert all(call[0] == "persistent_notification" for call in hass.services.calls)


@pytest.mark.asyncio
async def test_unchanged_notice_does_not_spam_and_changed_fault_updates_same_id():
    runtime, hass, notices = setup()
    runtime.faults["a"] = "Controle nodig"
    for _ in range(20):
        await notices.sync()
    assert len(calls(hass)) == 1
    runtime.faults["a"] = "Andere controle nodig"
    await notices.sync()
    assert len(calls(hass)) == 2
    assert calls(hass)[0][2]["notification_id"] == calls(hass)[1][2]["notification_id"]
    assert "Andere controle nodig" in calls(hass)[1][2]["message"]


@pytest.mark.asyncio
async def test_all_faults_resolved_dismisses_once_without_affecting_other_notice_ids():
    runtime, hass, notices = setup()
    runtime.faults["a"] = "Controle nodig"
    await notices.sync()
    runtime.faults.clear()
    await notices.sync()
    await notices.sync()
    assert [call[1] for call in calls(hass)] == ["create", "dismiss"]
    assert calls(hass)[1][2] == {"notification_id": "solar_pilot_test_action_required"}
    assert notices.snapshot() == {"schema": 1, "active": False, "signature": ""}


@pytest.mark.asyncio
async def test_failed_create_is_retried_and_not_acknowledged_until_success(caplog):
    runtime, hass, notices = setup()
    runtime.faults["a"] = "Controle nodig"
    hass.services.fail = True
    await notices.sync()
    await notices.sync()
    assert not notices.snapshot()["active"]
    assert len(calls(hass)) == 2
    assert len([record for record in caplog.records if "controlebericht" in record.message]) == 1
    hass.services.fail = False
    await notices.sync()
    await notices.sync()
    assert notices.snapshot()["active"]
    assert len(calls(hass)) == 3


@pytest.mark.asyncio
async def test_missing_notification_service_is_retried_when_registered():
    runtime, hass, notices = setup()
    runtime.faults["a"] = "Controle nodig"
    hass.services.has_service = lambda *_args: False
    await notices.sync()
    assert not notices.snapshot()["active"] and not calls(hass)
    hass.services.has_service = lambda *_args: True
    await notices.sync()
    assert notices.snapshot()["active"] and len(calls(hass)) == 1


@pytest.mark.asyncio
async def test_failed_dismiss_keeps_receipt_and_retries():
    runtime, hass, notices = setup()
    runtime.faults["a"] = "Controle nodig"
    await notices.sync()
    prior = notices.snapshot()
    runtime.faults.clear()
    hass.services.fail = True
    await notices.sync()
    assert notices.snapshot() == prior
    hass.services.fail = False
    await notices.sync()
    await notices.sync()
    assert [call[1] for call in calls(hass)] == ["create", "dismiss", "dismiss"]


@pytest.mark.asyncio
async def test_restored_delivery_resynchronizes_once_and_dismisses_resolved_notice_after_restart():
    runtime, hass, notices = setup()
    runtime.faults["a"] = "Controle nodig"
    await notices.sync()
    receipt = deepcopy(notices.snapshot())
    assert "Controle nodig" not in str(receipt)
    restored = ActionRequiredNotifications(runtime)
    restored.restore(receipt)
    await restored.sync()
    await restored.sync()
    assert len(calls(hass)) == 2
    assert calls(hass)[0][2]["notification_id"] == calls(hass)[1][2]["notification_id"]
    runtime.faults.clear()
    await restored.sync()
    assert [call[1] for call in calls(hass)] == ["create", "create", "dismiss"]


@pytest.mark.asyncio
async def test_receipt_save_failure_does_not_resend_accepted_notice_and_retries_save(monkeypatch):
    runtime, hass, notices = setup()
    runtime.faults["a"] = "Controle nodig"
    actual_save = runtime.store.async_delay_save
    attempts = []

    def fail_once(callback, delay):
        attempts.append(delay)
        if len(attempts) == 1:
            raise RuntimeError("Opslag tijdelijk niet bereikbaar")
        actual_save(callback, delay)

    monkeypatch.setattr(runtime.store, "async_delay_save", fail_once)
    await notices.sync()
    assert notices.snapshot()["active"] and len(calls(hass)) == 1
    await notices.sync()
    await notices.sync()
    assert len(calls(hass)) == 1 and attempts == [1, 1]


@pytest.mark.parametrize("raw", [
    None, [], {}, {"schema": True, "active": True, "signature": "a" * 64},
    {"schema": 2, "active": True, "signature": "a" * 64},
    {"schema": 1, "active": 1, "signature": "a" * 64},
    {"schema": 1, "active": True, "signature": "bad"},
    {"schema": 1, "active": False, "signature": "a" * 64},
    {"schema": 1, "active": True, "signature": "A" * 64},
])
def test_invalid_receipt_cannot_hide_current_faults(raw):
    _runtime, _hass, notices = setup()
    notices.restore(raw)
    assert notices.snapshot() == {"schema": 1, "active": False, "signature": ""}


def test_notification_bounds_external_labels_and_faults_and_neutralizes_markdown():
    runtime, hass, notices = setup()
    runtime.configs["a"]["name"] = "![image](https://invalid.example/image)\n# " + "x" * 200
    runtime.faults["a"] = "[link](https://invalid.example)\n" + "y" * 1000
    for index in range(40):
        runtime.configs[f"load_{index:02}"] = {"name": f"Toestel {index}"}
        runtime.faults[f"load_{index:02}"] = "z" * 1000
    message = notices.message()
    assert "![image](" not in message and "[link](" not in message
    assert "y" * 221 not in message and "z" * 221 not in message
    assert "Nog 9 controles" in message
    assert len(message) < 18000


@pytest.mark.asyncio
async def test_bad_reporter_data_or_service_error_never_crashes_control_path():
    runtime, hass, notices = setup()
    runtime.faults = object()
    await notices.sync()
    assert not calls(hass)
    runtime.faults = {"a": "Controle nodig"}
    await notices.sync()
    assert len(calls(hass)) == 1


@pytest.mark.asyncio
async def test_real_runtime_cycle_creates_fault_notice_then_dismisses_when_fixed():
    runtime, hass = build()
    runtime.faults["a"] = "Testopdracht niet bevestigd"
    await runtime.tick()
    receipt = runtime._snapshot()["action_notifications"]
    assert receipt["active"] and len(receipt["signature"]) == 64
    assert calls(hass)[0][2]["notification_id"] == "solar_pilot_test_action_required"
    runtime.faults.clear()
    await runtime.tick()
    assert [call[1] for call in calls(hass)] == ["create", "dismiss"]
    assert not runtime._snapshot()["action_notifications"]["active"]


@pytest.mark.asyncio
async def test_real_runtime_start_restores_receipt_and_removes_resolved_notice():
    previous, previous_hass = build()
    previous.faults["a"] = "Testopdracht niet bevestigd"
    await previous.tick()
    saved = deepcopy(previous._snapshot())
    saved["faults"] = {}
    runtime, hass = build()
    runtime.entry.options["_beta37_activation_profile"] = 1
    runtime.store.data = saved
    await runtime.start()
    notices = [call for call in calls(hass) if call[2]["notification_id"] == "solar_pilot_test_action_required"]
    assert [call[1] for call in notices] == ["dismiss"]
    assert not runtime._snapshot()["action_notifications"]["active"]
    await runtime.close()


@pytest.mark.asyncio
async def test_real_runtime_internal_exception_notifies_without_notification_failure_hiding_it(monkeypatch):
    runtime, hass = build()

    async def controller_error():
        raise RuntimeError("Testinterne fout")

    monkeypatch.setattr(runtime, "_tick", controller_error)
    hass.services.fail = True
    await runtime.tick()
    assert runtime.mode == "paused" and runtime.pause_cause == "internal_fault"
    assert not runtime.action_notifications.snapshot()["active"]
    hass.services.fail = False
    await runtime.tick()
    assert runtime.pause_cause == "internal_fault"
    assert runtime.action_notifications.snapshot()["active"]
    assert calls(hass)[-1][2]["title"] == "SolarPilot: controle nodig"
