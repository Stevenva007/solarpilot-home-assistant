"""Action-required HA messages; real reporter with HA API doubles only."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.action_notifications import ActionRequiredNotifications
from custom_components.solar_pilot import action_notifications
from custom_components.solar_pilot.dhw_runtime import LEGACY_ACK_FAULT
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
    runtime.smart_climate.state.fault = "Actuele buitentemperatuur ontbreekt of is te oud"
    runtime.dhw.restart_recovery = {"reason": "Wacht op doelrapportage"}
    runtime.dhw.recovery_budget = {"next_attempt_wall": 9999999999}
    await notices.sync()
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_unknown_boiler_fault_has_distinct_id_and_real_recovery_location():
    runtime, hass, notices = setup()
    runtime.dhw.fault = "Opgeslagen boileropdracht ongeldig; controle nodig"
    await notices.sync()
    domain, service, payload = calls(hass)[0]
    assert (domain, service) == ("persistent_notification", "create")
    assert payload["notification_id"] == "solar_pilot_test_action_required"
    assert payload["title"] == "SolarPilot: controle nodig"
    assert "Sanitair warm water" in payload["message"]
    assert "Boilercontrole afronden" in payload["message"]
    assert "Opgeslagen boileropdracht ongeldig" in payload["message"]
    assert notices.snapshot()["active"]


@pytest.mark.asyncio
async def test_exact_known_automatic_boiler_recovery_is_quiet_but_stale_recovery_cannot_hide_fault():
    runtime, hass, notices = setup()
    runtime.dhw.fault = LEGACY_ACK_FAULT
    runtime.dhw.automatic_recovery = {"fault": LEGACY_ACK_FAULT, "state": "waiting_reports"}
    await notices.sync()
    assert not calls(hass)
    runtime.dhw.fault = "Onbekende boilerfout; controle nodig"
    await notices.sync()
    assert len(calls(hass)) == 1
    assert "Onbekende boilerfout" in calls(hass)[0][2]["message"]


@pytest.mark.asyncio
async def test_manual_guard_cannot_be_hidden_by_an_old_matching_automatic_recovery():
    runtime, hass, notices = setup()
    runtime.dhw.fault = LEGACY_ACK_FAULT
    runtime.dhw.automatic_recovery = {"fault": LEGACY_ACK_FAULT}
    runtime.dhw.manual_hold = True
    runtime.dhw.auto_enabled = True
    await notices.sync()
    assert len(calls(hass)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("manual_hold,enabled,protected,review,expected", [
    (True, False, False, False, False),  # Explicit disabled/manual takeover.
    (True, True, False, False, True),   # Unexpected target change while owning.
    (True, True, "Hygiëneprogramma actief", False, False),
    (False, True, False, True, True),
    (False, True, "Hygiëneprogramma actief", True, False),
])
async def test_boiler_manual_review_and_deliberate_native_choices(manual_hold, enabled, protected, review, expected):
    runtime, hass, notices = setup()
    runtime.dhw.manual_hold = manual_hold
    runtime.dhw.auto_enabled = enabled
    runtime.dhw.reading = SimpleNamespace(protected=protected)
    runtime.dhw.needs_review = review
    runtime.dhw.status = "Boilertoestand vraagt controle"
    await notices.sync()
    assert bool(calls(hass)) == expected


@pytest.mark.asyncio
async def test_native_hygiene_does_not_hide_a_separate_unknown_command_fault():
    runtime, hass, notices = setup()
    runtime.dhw.reading = SimpleNamespace(protected="Hygiëneprogramma actief")
    runtime.dhw.fault = "Onbekende opgeslagen opdracht"
    await notices.sync()
    assert "Onbekende opgeslagen opdracht" in calls(hass)[0][2]["message"]


@pytest.mark.asyncio
async def test_all_durable_controller_faults_are_collated_once_and_deterministically():
    runtime, hass, notices = setup()
    runtime.faults["a"] = "Geen opdrachtbevestiging"
    runtime.reclaim_blocks["a"] = "Geen opdrachtbevestiging"
    hass.states.set("climate.zone", "off", {"friendly_name": "Testzone"})
    runtime.smart_climate.command_faults["climate.zone"] = "Klimaatopdracht niet bevestigd"
    runtime.battery_fleet.configs["b"] = {"name": "Testbatterij"}
    runtime.battery_fleet.state.faults["b"] = "Batterijopdracht niet bevestigd"
    await notices.sync()
    message = calls(hass)[0][2]["message"]
    assert message.count("Geen opdrachtbevestiging") == 1
    assert "Testtoestel" in message and "Toestellen" in message
    assert "Testzone" in message and "Ruimteklimaat" in message
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
async def test_restored_delivery_suppresses_duplicate_and_dismisses_resolved_notice_after_restart():
    runtime, hass, notices = setup()
    runtime.faults["a"] = "Controle nodig"
    await notices.sync()
    receipt = deepcopy(notices.snapshot())
    assert "Controle nodig" not in str(receipt)
    restored = ActionRequiredNotifications(runtime)
    restored.restore(receipt)
    await restored.sync()
    assert len(calls(hass)) == 1
    runtime.faults.clear()
    await restored.sync()
    assert [call[1] for call in calls(hass)] == ["create", "dismiss"]


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
        runtime.smart_climate.command_faults[f"climate.zone_{index:02}"] = "z" * 1000
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
async def test_real_runtime_keeps_known_automatic_boiler_reconciliation_quiet():
    runtime, hass = build()
    runtime.dhw.fault = LEGACY_ACK_FAULT
    runtime.dhw.automatic_recovery = runtime.dhw._new_recovery(None, LEGACY_ACK_FAULT)
    await runtime.tick()
    assert runtime.pause_cause != "internal_fault"
    assert not calls(hass)
    assert not runtime.action_notifications.snapshot()["active"]


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


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["waiting_sources", "waiting_reports", "waiting_external_target"])
async def test_long_automatic_boiler_wait_notifies_once_without_changing_recovery_and_dismisses_when_resolved(monkeypatch, state):
    runtime, hass, notices = setup()
    wall = [10000.0]
    monkeypatch.setattr(action_notifications, "time", SimpleNamespace(time=lambda: wall[0]))
    runtime.dhw.fault = LEGACY_ACK_FAULT
    runtime.dhw.automatic_recovery = {"fault": LEGACY_ACK_FAULT, "state": state, "failed_wall": 10000.0}
    before = deepcopy(runtime.dhw.automatic_recovery)
    wall[0] += 899
    await notices.sync()
    assert not calls(hass)
    wall[0] += 1
    await notices.sync()
    assert len(calls(hass)) == 1
    message = calls(hass)[0][2]["message"]
    assert "minstens 15 minuten" in message and "doeltemperatuur" in message
    assert "verbinding" in message and "Sanitair warm water" in message
    assert "automatische controle blijft doorlopen; geen reset nodig" in message
    assert "Boilercontrole afronden" not in message
    assert runtime.dhw.fault == LEGACY_ACK_FAULT and runtime.dhw.automatic_recovery == before
    for _ in range(10):
        wall[0] += 60
        await notices.sync()
    assert len(calls(hass)) == 1
    runtime.dhw.fault = ""
    runtime.dhw.automatic_recovery = None
    await notices.sync()
    assert [call[1] for call in calls(hass)] == ["create", "dismiss"]
    assert all(call[0] == "persistent_notification" for call in hass.services.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["checking_reports", "waiting_protection", "backoff", ""])
async def test_long_automatic_protection_verification_or_backoff_does_not_request_a_user_check(monkeypatch, state):
    runtime, hass, notices = setup()
    monkeypatch.setattr(action_notifications, "time", SimpleNamespace(time=lambda: 20000.0))
    runtime.dhw.fault = LEGACY_ACK_FAULT
    runtime.dhw.automatic_recovery = {"fault": LEGACY_ACK_FAULT, "state": state, "failed_wall": 10000.0}
    await notices.sync()
    assert not calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("failed_wall", [None, True, False, "bad", float("nan"), float("inf"), -1, 0, 20001])
async def test_invalid_automatic_wait_timestamp_does_not_fabricate_a_duration_or_notice(monkeypatch, failed_wall):
    runtime, hass, notices = setup()
    monkeypatch.setattr(action_notifications, "time", SimpleNamespace(time=lambda: 20000.0))
    runtime.dhw.fault = LEGACY_ACK_FAULT
    runtime.dhw.automatic_recovery = {"fault": LEGACY_ACK_FAULT, "state": "waiting_sources", "failed_wall": failed_wall}
    await notices.sync()
    assert not calls(hass)


@pytest.mark.asyncio
async def test_connection_wait_notice_disappears_when_new_reports_enter_verification(monkeypatch):
    runtime, hass, notices = setup()
    monkeypatch.setattr(action_notifications, "time", SimpleNamespace(time=lambda: 20000.0))
    runtime.dhw.fault = LEGACY_ACK_FAULT
    runtime.dhw.automatic_recovery = {"fault": LEGACY_ACK_FAULT, "state": "waiting_sources", "failed_wall": 10000.0}
    await notices.sync()
    runtime.dhw.automatic_recovery["state"] = "checking_reports"
    await notices.sync()
    assert runtime.dhw.fault == LEGACY_ACK_FAULT
    assert [call[1] for call in calls(hass)] == ["create", "dismiss"]
