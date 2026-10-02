"""Only native-reading observations, with no Home Assistant or hardware calls."""
from copy import deepcopy
from dataclasses import replace
import math

import pytest

from custom_components.solar_pilot.wallbox import Reading
from custom_components.solar_pilot.wallbox_activity import WallboxActivityHistory


T = 1000.0


def read(stamp=T, power=2000, status="Charging", **kw):
    kw.setdefault("status_stamp", stamp)
    return Reading(power_w=power, stamp=stamp, demand=True, status=status,
                   mode="full_solar", raw_mode="full_solar", valid=True, age_s=0,
                   connected=True, session_confirmed=True, **kw)


def test_power_not_configured_mode_confirms_actual_charging():
    history = WallboxActivityHistory()
    result = history.update(read(), T)
    assert result["current"]["active"] is True
    assert result["current"]["label"] == "Auto laadt"
    result = history.update(read(stamp=T+90, power=0, status="Something new"), T+90)
    assert not result["current"]["active"]
    assert result["last_stop"]["stop_confirmed"]
    assert not result["last_stop"]["cause_reported"]
    assert "exacte wacht- of stopoorzaak" in result["last_stop"]["stop_reason"]


@pytest.mark.parametrize("status,waiting", [("Waiting in queue by Eco-Smart", "solar"),
                                           ("Waiting for green energy", "solar"),
                                           ("Scheduled", "schedule"),
                                           ("Waiting for car demand", "car"),
                                           ("Waiting in queue by Power Boost", "power_boost"),
                                           ("Waiting in queue by Power Sharing", "power_sharing"),
                                           ("Paused", "paused"), ("Locked", "locked"),
                                           ("Disconnected", "connection"), ("Error", "error")])
def test_exact_native_status_explains_waiting_without_new_control(status, waiting):
    history = WallboxActivityHistory()
    report = history.update(read(power=0, status=status), T)
    assert report["current"]["waiting_for"] == waiting
    assert report["current"]["cause_reported"] is True
    assert report["read_only"] is True
    assert report["last_stop"] is None  # Observing idle at startup is not a stop event.


@pytest.mark.parametrize("status", ["Ready", "Waiting", "Unknown", "New Eco-Smart state", ""])
def test_unknown_status_and_full_solar_never_invent_solar_wait_or_full_battery(status):
    history = WallboxActivityHistory()
    report = history.update(read(power=0, status=status), T)
    current = report["current"]
    assert current["waiting_for"] == "unknown"
    assert current["cause_reported"] is False
    assert "volledig geladen" not in current["reason"]


def test_exact_paused_status_does_not_invent_manual_actor():
    history = WallboxActivityHistory()
    history.update(read(), T)
    report = history.update(read(stamp=T+90, power=0, status="Paused"), T+90)
    assert "wie of wat" in report["last_stop"]["stop_reason"]
    assert not report["last_stop"]["solar_pilot_cause_proven"]


def test_new_solar_wait_stop_is_recorded_with_native_status_and_observed_time():
    history = WallboxActivityHistory()
    history.update(read(), T)
    report = history.update(read(stamp=T+90, power=0, status="Waiting in queue by Eco-Smart"), T+95)
    event = report["last_stop"]
    assert event["observed_stop_at"] == T+95
    assert event["stop_report_at"] == T+90
    assert event["native_status"] == "Waiting in queue by Eco-Smart"
    assert event["previous_power_w"] == 2000 and event["power_w"] == 0
    assert event["stop_confirmed"] and event["cause_reported"]
    assert not event["start_confirmed"]  # First observation was already charging.


@pytest.mark.parametrize("status", ["Paused", "Waiting in queue by Eco-Smart"])
@pytest.mark.parametrize("status_stamp", [T-10, T+1])
def test_old_native_status_cannot_be_claimed_as_new_stop_cause(status, status_stamp):
    history = WallboxActivityHistory()
    history.update(read(), T)
    report = history.update(read(stamp=T+90, power=0, status=status,
                                 status_stamp=status_stamp), T+90)
    event = report["last_stop"]
    assert event["stop_confirmed"]
    assert not event["cause_reported"]
    assert event["status_report_at"] == status_stamp
    assert "niet gelijktijdig" in event["stop_reason"]
    assert "zonnestroom" not in event["stop_reason"]
    assert "gepauzeerd" not in event["stop_reason"]


def test_start_can_be_confirmed_only_after_previously_observed_not_charging():
    history = WallboxActivityHistory()
    history.update(read(power=0, status="Ready"), T)
    report = history.update(read(stamp=T+90), T+90)
    assert report["ongoing"]["start_confirmed"] is True


@pytest.mark.parametrize("change", [{"valid": False}, {"power_w": None}, {"power_w": -1},
                                    {"power_w": math.nan}, {"stamp": 0}, {"age_s": 301},
                                    {"stamp": T-301}, {"stamp": T+6}, {"age_s": None}])
def test_unavailable_or_stale_power_is_unknown_not_a_confirmed_stop(change):
    history = WallboxActivityHistory()
    history.update(read(stamp=T-90), T-90)
    report = history.update(replace(read(power=0), **change), T)
    assert not report["current"]["known"]
    assert report["current"]["power_w"] is None
    event = report["last_stop"]
    assert event["observed_stop_at"] is None
    assert not event["stop_confirmed"] and not event["cause_reported"]
    assert event["telemetry_gap"] and event["end_state"] == "unconfirmed"


def test_reconnect_after_gap_never_promotes_old_stop_to_known_reason():
    history = WallboxActivityHistory()
    history.update(read(), T)
    history.update(replace(read(stamp=T+90, power=0), valid=False), T+90)
    report = history.update(read(stamp=T+180, power=0, status="Paused"), T+180)
    assert report["current"]["waiting_for"] == "paused"
    assert not report["last_stop"]["stop_confirmed"]
    assert not report["last_stop"]["cause_reported"]
    assert report["retained_events"] == 1


def test_long_gap_with_two_individually_fresh_samples_cannot_confirm_historical_stop():
    history = WallboxActivityHistory(stale_s=300)
    history.update(read(), T)
    report = history.update(read(stamp=T+600, power=0, status="Waiting in queue by Eco-Smart"), T+600)
    assert report["current"]["known"]
    assert report["current"]["waiting_for"] == "solar"
    assert report["current"]["cause_reported"]
    assert not report["last_stop"]["stop_confirmed"]
    assert not report["last_stop"]["cause_reported"]
    assert report["last_stop"]["observed_stop_at"] is None
    assert "Te lange onderbreking" in report["last_stop"]["stop_reason"]


def test_long_gap_cannot_confirm_restart_of_a_still_charging_session():
    history = WallboxActivityHistory(stale_s=300)
    history.update(read(), T)
    report = history.update(read(stamp=T+600), T+600)
    assert report["current"]["active"]
    assert not report["last_stop"]["stop_confirmed"]
    assert report["ongoing"]["observed_start_at"] == T+600
    assert not report["ongoing"]["start_confirmed"]


def test_duplicate_or_out_of_order_power_report_does_not_create_fake_transition():
    history = WallboxActivityHistory()
    history.update(read(), T)
    report = history.update(read(power=0, status="Paused"), T+10)
    assert report["last_stop"] is None
    history.update(read(stamp=T+90, power=0, status="Paused"), T+90)
    report = history.update(read(stamp=T+90, power=0, status="Paused"), T+95)
    assert report["retained_events"] == 1


def test_grid_or_cloud_context_is_not_used_as_causal_stop_proof():
    history = WallboxActivityHistory()
    history.update(read(), T)
    report = history.update(read(stamp=T+90, power=0, status="Ready"), T+90,
                            grid_w=2000, pv_w=0, free_w=0)
    assert not report["last_stop"]["cause_reported"]
    assert not report["current"]["site_context"]["proves_stop_cause"]


def test_positive_power_with_old_waiting_status_is_still_actual_charging():
    history = WallboxActivityHistory()
    report = history.update(read(status="Waiting in queue by Eco-Smart"), T)
    assert report["current"]["active"]
    assert report["current"]["waiting_for"] == "none"
    assert report["current"]["native_status"] == "Waiting in queue by Eco-Smart"


def test_history_is_bounded_at_30_observed_endings():
    history = WallboxActivityHistory()
    for index in range(40):
        t = T + index*180
        history.update(read(stamp=t), t)
        history.update(read(stamp=t+90, power=0, status="Paused"), t+90)
    assert len(history.snapshot()["events"]) == 30
    assert history.overview()["retained_events"] == 30


def test_restore_retains_real_completed_history_but_does_not_bridge_restart():
    history = WallboxActivityHistory()
    history.update(read(), T)
    history.update(read(stamp=T+90, power=0, status="Paused"), T+90)
    history.update(read(stamp=T+180), T+180)
    restored = WallboxActivityHistory()
    restored.restore(history.snapshot())
    report = restored.update(read(stamp=T+360, power=0, status="Waiting in queue by Eco-Smart"), T+360)
    assert report["history"][1]["stop_confirmed"]
    assert not report["last_stop"]["stop_confirmed"]
    assert "herstart" in report["last_stop"]["stop_reason"]
    assert not report["last_stop"]["cause_reported"]


def test_restore_revokes_native_cause_without_same_batch_status_timestamp():
    history = WallboxActivityHistory()
    history.update(read(), T)
    history.update(read(stamp=T+90, power=0, status="Paused"), T+90)
    payload = history.snapshot()
    payload["events"][0].pop("status_report_at")
    restored = WallboxActivityHistory()
    restored.restore(payload)
    event = restored.overview()["last_stop"]
    assert event["stop_confirmed"]
    assert not event["cause_reported"]
    assert "niet gelijktijdig" in event["stop_reason"]


def test_future_restored_watermark_cannot_suppress_current_reports_indefinitely():
    restored = WallboxActivityHistory()
    restored.restore({"version": 1, "events": [], "last_report_stamp": T+10_000})
    report = restored.update(read(stamp=T, power=0, status="Ready"), T)
    assert report["current"]["known"]
    assert restored.snapshot()["last_report_stamp"] == T


@pytest.mark.parametrize("ongoing", [
    {"observed_start_at": T, "last_charging_report_at": None, "previous_power_w": 2000},
    {"observed_start_at": T, "last_charging_report_at": T, "previous_power_w": -1},
    {"observed_start_at": T, "last_charging_report_at": T-301, "previous_power_w": 2000},
    {"observed_start_at": T+1000, "last_charging_report_at": T+1000, "previous_power_w": 2000},
])
def test_invalid_or_future_restored_ongoing_never_creates_fake_gap_event(ongoing):
    restored = WallboxActivityHistory(stale_s=300)
    restored.restore({"version": 1, "events": [], "ongoing": ongoing,
                      "last_report_stamp": ongoing.get("last_charging_report_at")})
    report = restored.update(read(stamp=T, power=0, status="Ready"), T)
    assert report["last_stop"] is None
    assert report["ongoing"] is None


def test_serialization_ignores_entity_identifiers_and_unknown_extra_payloads():
    history = WallboxActivityHistory()
    history.update(read(), T)
    history.update(read(stamp=T+90, power=0, status="Paused"), T+90)
    payload = history.snapshot()
    payload["events"][0]["entity_id"] = "sensor.private_identifier"
    payload["events"][0]["solar_pilot_cause_proven"] = True
    restored = WallboxActivityHistory()
    restored.restore(payload)
    assert "entity_id" not in restored.snapshot()["events"][0]
    assert not restored.snapshot()["events"][0]["solar_pilot_cause_proven"]
    restored.restore({"version": 999, "events": payload["events"]})
    assert restored.overview()["last_stop"] is None


@pytest.mark.parametrize("change", [{"observed_start_at": -1}, {"observed_stop_at": -1},
                                    {"observed_stop_at": T-1}, {"stop_report_at": T},
                                    {"stop_report_at": T+200}, {"last_charging_report_at": -1}])
def test_restore_does_not_trust_negative_or_contradictory_stop_times(change):
    history = WallboxActivityHistory()
    history.update(read(), T)
    history.update(read(stamp=T+90, power=0, status="Paused"), T+90)
    payload = history.snapshot()
    payload["events"][0].update(change)
    restored = WallboxActivityHistory()
    restored.restore(payload)
    event = restored.overview()["last_stop"]
    assert event is None or not event["stop_confirmed"]
    assert event is None or not event["cause_reported"]


def test_overview_and_snapshot_are_independent_copies_and_no_reading_mutation():
    history = WallboxActivityHistory()
    reading = read()
    previous = deepcopy(reading)
    report = history.update(reading, T)
    report["current"]["active"] = False
    assert history.overview()["current"]["active"]
    assert reading == previous
    payload = history.snapshot()
    payload["ongoing"]["previous_power_w"] = 99999
    assert history.snapshot()["ongoing"]["previous_power_w"] == 2000


def test_disabling_monitor_does_not_claim_physical_charger_stopped():
    history = WallboxActivityHistory()
    history.update(read(), T)
    report = history.update(read(stamp=T+90), T+90, enabled=False)
    assert not report["current"]["known"]
    assert not report["last_stop"]["stop_confirmed"]
