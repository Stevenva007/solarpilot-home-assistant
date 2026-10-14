"""Source-bound operation display, support and contact history; fictional only."""
from copy import deepcopy
from datetime import timedelta
import json

import pytest

from custom_components.solar_pilot.heatpump_history import HeatpumpHistory
from test_heatpump_history70 import BASE, observe, sg, source
from test_heatpump_history81 import tank_source


def test_derived_boiler_task_survives_main_to_heater_switch_with_separate_support():
    model = HeatpumpHistory()
    for seconds, main, heater in ((0, 1600, 0), (5, 40, 2760), (10, 50, 2750)):
        at = BASE+timedelta(seconds=seconds)
        observe(model, at, p=tank_source(at, task="tapwater_heating", tier="derived", watts=main+heater, main=main, heater=heater))
    detail = model.detail(None, at)
    assert detail["task_totals"] == [{"task": "tapwater_heating", "label": "Boiler opwarmen", "tier": "derived", "on_s": 10}]
    assert len(detail["task_sessions"]) == 1
    assert detail["support_totals"][0]["on_s"] == 5
    assert detail["support_sessions"][0]["duration_s"] == 5


def test_partial_main_and_explicit_tank_idle_allow_display_heating_not_total_energy():
    model = HeatpumpHistory()
    for seconds in (0, 5):
        at = BASE+timedelta(seconds=seconds)
        p = tank_source(at, tier="derived", watts=1800, main=1800)
        p.update(power_complete=False, power_w=None)
        p["power_supply2_valid"] = False
        p["power_activity"].update(complete=False, state="partial")
        p["power_activity"]["supplies"][1].update(valid=False, watts=None)
        p["display_tank"].update(available=True, observed_at=at.timestamp(), mode="idle", action="idle")
        observe(model, at, p=p)
    detail = model.detail(None, at)
    assert detail["task_totals"][0]["task"] == "space_heating"
    assert detail["task_totals"][0]["tier"] == "derived"
    assert detail["energy_kwh"] is None and detail["energy_known_s"] == 0


def test_partial_heater_proves_support_but_no_primary_thermal_task_or_total_energy():
    model = HeatpumpHistory()
    for seconds in (0, 5):
        at = BASE+timedelta(seconds=seconds)
        p = source(at, task=None, watts=2800, main=40, heater=2760)
        p.update(power_complete=False, power_w=None, power_supply1_valid=False)
        p["power_activity"].update(complete=False, state="partial")
        p["power_activity"]["supplies"][0].update(valid=False, watts=None)
        observe(model, at, p=p)
    detail = model.detail(None, at)
    assert detail["task_totals"][0]["task"] == "heatpump_unknown"
    assert detail["support_totals"][0]["on_s"] == 5
    assert detail["energy_kwh"] is None


@pytest.mark.parametrize("invalid", ["old", "negative", "role_missing", "not_valid", "boolean"])
def test_support_requires_fresh_valid_explicit_heater_feed(invalid):
    model = HeatpumpHistory()
    for seconds in (0, 5):
        at = BASE+timedelta(seconds=seconds)
        p = source(at, task="tapwater_heating", main=40, heater=2760, watts=2800)
        row = p["power_activity"]["supplies"][1]
        if invalid == "old":
            row["observed_at"] -= 121
        elif invalid == "negative":
            row["watts"] = -10
        elif invalid == "role_missing":
            row["role"] = "unknown"
        elif invalid == "not_valid":
            row["valid"] = False
        else:
            row["watts"] = True
        observe(model, at, p=p)
    detail = model.detail(None, at)
    assert detail["support_sessions"] == [] and detail["support_totals"] == []
    assert detail["support_coverage"]["known_s"] == 0


def test_restore_does_not_reclassify_legacy_support_or_backfill_new_support_lane():
    old = HeatpumpHistory()
    # This is a synthetic stored record with the old task semantics, separate
    # from a beta.82 observation. No watts or selected programme rewrite it.
    for seconds in (0, 5):
        at = BASE+timedelta(seconds=seconds)
        old._ensure(at)
        old.tasks.observe("electrical_support:derived", old._config("Elektrische ondersteuning"), True, at)
    saved = old.snapshot()
    saved.pop("support")
    saved.pop("sg_contact_evidence")
    retained = deepcopy(saved["tasks"]["devices"]["electrical_support:derived"])
    restored = HeatpumpHistory()
    restored.restore(saved, BASE+timedelta(seconds=10))
    detail = restored.detail(None, BASE+timedelta(seconds=10))
    assert detail["task_totals"] == [{"task": "electrical_support", "label": "Elektrische ondersteuning", "tier": "derived", "on_s": 5}]
    assert detail["support_sessions"] == [] and detail["support_totals"] == []
    assert restored.tasks.devices["electrical_support:derived"]["days"] == retained["days"]
    assert detail["task_sessions"][0]["duration_s"] == 5


def test_contact_overlay_distinguishes_observed_on_off_and_unknown_without_request_substitution():
    model = HeatpumpHistory()
    for seconds, contact in ((0, False), (5, True), (10, True), (15, False), (20, False)):
        at = BASE+timedelta(seconds=seconds)
        observe(model, at, s=sg(at, request=True, contact=contact))
    detail = model.detail(None, at)
    overlay = detail["sg_contact_overlay"]
    observed = [row for row in overlay["segments"] if row["state"] != "unknown"]
    assert [row["state"] for row in observed] == ["off", "on", "off"]
    assert overlay["known_s"] == 20 and overlay["on_s"] == 10
    assert overlay["state"] == "off" and overlay["reported_at"] == at.timestamp()
    assert detail["sg"]["request"]["on_s"] == 20
    assert detail["sg"]["contact"]["on_s"] == 10
    assert overlay["unknown_s"] > 0
    assert overlay["segments"][0]["state"] == "unknown"
    assert "synthetic" not in json.dumps(overlay)


def test_contact_lease_deadline_and_unknown_source_do_not_extend_current_on():
    model = HeatpumpHistory()
    for seconds in (0, 5):
        at = BASE+timedelta(seconds=seconds)
        s = sg(at, contact=True)
        s["relay_valid_until"] = BASE.timestamp()+7
        observe(model, at, s=s)
    detail = model.detail(None, BASE+timedelta(seconds=8))
    assert detail["sg_contact_overlay"]["state"] == "unknown"
    assert detail["sg_contact_overlay"]["on_s"] == 5
    assert detail["sg_contact_overlay"]["segments"][-1]["state"] == "unknown"
    assert detail["sg"]["contact"]["sessions"][0]["ongoing"] is False


def test_contact_gap_restore_and_rebind_never_create_off_or_bridge_known_intervals():
    model = HeatpumpHistory()
    for seconds in (0, 5, 100, 105):
        at = BASE+timedelta(seconds=seconds)
        observe(model, at, s=sg(at, contact=True))
    detail = model.detail(None, at)
    overlay = detail["sg_contact_overlay"]
    assert overlay["known_s"] == 10 and overlay["on_s"] == 10
    assert any(row["state"] == "unknown" and row["duration_s"] == 95 for row in overlay["segments"])
    restored = HeatpumpHistory()
    restored.restore(model.snapshot(), BASE+timedelta(seconds=110))
    assert restored.detail(None, BASE+timedelta(seconds=110))["sg_contact_overlay"]["state"] == "unknown"
    observe(restored, BASE+timedelta(seconds=110), s=sg(BASE+timedelta(seconds=110), contact=True))
    assert restored.detail(None, BASE+timedelta(seconds=110))["sg_contact_overlay"]["on_s"] == 10
    observe(restored, BASE+timedelta(seconds=115), s=sg(BASE+timedelta(seconds=115), contact=True), binding="changed")
    assert restored.detail(None, BASE+timedelta(seconds=115))["sg_contact_overlay"]["on_s"] == 10


def test_legacy_contact_on_retained_but_off_aggregate_not_spread_over_day():
    model = HeatpumpHistory()
    for seconds, contact in ((0, False), (5, True), (10, False), (15, False)):
        at = BASE+timedelta(seconds=seconds)
        observe(model, at, s=sg(at, contact=contact))
    saved = model.snapshot()
    saved.pop("sg_contact_evidence")
    restored = HeatpumpHistory()
    restored.restore(saved, BASE+timedelta(seconds=20))
    detail = restored.detail(None, BASE+timedelta(seconds=20))
    assert detail["sg"]["contact"]["known_s"] == 15
    assert detail["sg_contact_overlay"]["known_s"] == detail["sg_contact_overlay"]["on_s"] == 5
    assert not any(row["state"] == "off" for row in detail["sg_contact_overlay"]["segments"])


def test_tank_summary_keeps_independent_original_times_and_nulls_only_stale_field():
    model = HeatpumpHistory()
    p = tank_source(BASE, temperature=49, target=50)
    p["display_tank"].update(temperature_stamp=BASE.timestamp()-115, target_stamp=BASE.timestamp()-10)
    observe(model, BASE, p=p)
    detail = model.detail(None, BASE+timedelta(seconds=10))["tank_temperature"]
    live = detail["current"]
    assert live["current"] is True
    assert live["temperature_c"] is None and live["temperature_reported_at"] == BASE.timestamp()-115
    assert live["ordinary_target_c"] == 50 and live["ordinary_target_reported_at"] == BASE.timestamp()-10
    assert detail["points"][0]["temperature_c"] == 49
    assert detail["points"][0]["temperature_reported_at"] == BASE.timestamp()-115
    assert detail["ordinary_target_only"] is True
    expired = model.detail(None, BASE+timedelta(seconds=31))["tank_temperature"]["current"]
    assert expired["current"] is False and expired["ordinary_target_c"] is None


def test_restored_tank_reading_is_historical_and_never_live_without_observation():
    model = HeatpumpHistory()
    observe(model, BASE, p=tank_source(BASE))
    saved = model.snapshot()
    restored = HeatpumpHistory()
    restored.restore(saved, BASE+timedelta(seconds=5))
    result = restored.detail(None, BASE+timedelta(seconds=5))["tank_temperature"]
    assert result["current"]["temperature_c"] is None and result["current"]["current"] is False
    assert result["points"][0]["temperature_c"] == 57
    assert result["points"][0]["temperature_reported_at"] == BASE.timestamp()-4
    assert result["points"][0]["continuous_from_previous"] is False


@pytest.mark.parametrize("corrupt", ["boolean_stamp", "invalid_on", "overlap", "beyond_expiry", "private_keys"])
def test_contact_store_validation_is_closed_and_never_restores_live_anchor(corrupt):
    model = HeatpumpHistory()
    for seconds in (0, 5, 10):
        at = BASE+timedelta(seconds=seconds)
        observe(model, at, s=sg(at, contact=True))
    saved = model.snapshot()
    row = saved["sg_contact_evidence"]["spans"][0]
    if corrupt == "boolean_stamp":
        row["reported_at"] = True
    elif corrupt == "invalid_on":
        row["on"] = 1
    elif corrupt == "overlap":
        duplicate = deepcopy(row)
        duplicate.update(start=BASE.timestamp()+1)
        saved["sg_contact_evidence"]["spans"].append(duplicate)
    elif corrupt == "beyond_expiry":
        row["valid_until"] = row["end"]-1
    else:
        row["entity_id"] = "sensor.synthetic_private"
    if corrupt == "private_keys":
        restored = HeatpumpHistory()
        restored.restore(saved, BASE+timedelta(seconds=15))
        overlay = restored.detail(None, BASE+timedelta(seconds=15))["sg_contact_overlay"]
        assert overlay["state"] == "unknown" and "synthetic_private" not in json.dumps(overlay)
    else:
        with pytest.raises(ValueError):
            HeatpumpHistory().restore(saved, BASE+timedelta(seconds=15))


def test_contact_equal_state_coalescing_never_renews_first_original_deadline():
    model = HeatpumpHistory()
    for seconds in range(0, 136, 5):
        at = BASE+timedelta(seconds=seconds)
        observe(model, at, s=sg(at, contact=False))
    spans = model.snapshot()["sg_contact_evidence"]["spans"]
    assert len(spans) == 2
    assert spans[0]["reported_at"] == BASE.timestamp()
    assert spans[0]["end"] == spans[0]["valid_until"] == BASE.timestamp()+120
    assert spans[1]["start"] == BASE.timestamp()+120
    assert spans[1]["reported_at"] == BASE.timestamp()+120
    restored = HeatpumpHistory()
    restored.restore(model.snapshot(), BASE+timedelta(seconds=140))
    result = restored.detail(None, BASE+timedelta(seconds=140))["sg_contact_overlay"]
    assert result["known_s"] == 135 and result["on_s"] == 0
    assert result["state"] == "unknown"


def test_contact_evidence_bound_is_explicit_and_does_not_fabricate_old_off(monkeypatch):
    from custom_components.solar_pilot import heatpump_history_evidence
    monkeypatch.setattr(heatpump_history_evidence, "MAX_POINTS", 2)
    model = HeatpumpHistory()
    for seconds in range(0, 31, 5):
        at = BASE+timedelta(seconds=seconds)
        observe(model, at, s=sg(at, contact=seconds%10 == 0))
    assert len(model.contact_evidence.spans) == 2
    overlay = model.detail(None, at)["sg_contact_overlay"]
    assert overlay["segments_truncated"] is True
    assert sum(row["duration_s"] for row in overlay["segments"] if row["state"] == "off") == 5
    assert any(row["state"] == "unknown" for row in overlay["segments"])


def test_contact_timeline_splits_true_25_hour_local_day_at_original_utc_boundaries():
    from datetime import datetime, timezone
    model = HeatpumpHistory()
    start = datetime(2026, 10, 25, 0, 59, 50, tzinfo=timezone.utc)
    for seconds in (0, 10, 20):
        at = start+timedelta(seconds=seconds)
        observe(model, at, s=sg(at, contact=True))
    detail = model.detail("2026-10-25", at)
    overlay = detail["sg_contact_overlay"]
    assert detail["day_seconds"] == 90000 and overlay["on_s"] == 20
    on = [row for row in overlay["segments"] if row["state"] == "on"]
    assert sum(row["width_pct"] for row in on) == pytest.approx(100*20/90000, abs=.00001)
    assert on[0]["segment_start"] == "2026-10-25T00:59:50+00:00"
    assert on[-1]["segment_end"] == "2026-10-25T01:00:10+00:00"


def test_temperature_points_are_selected_by_capture_day_without_backfilling_other_days():
    model = HeatpumpHistory()
    before = BASE.replace(hour=21, minute=59, second=55)
    observe(model, before, p=tank_source(before, temperature=49))
    after = before+timedelta(seconds=10)
    observe(model, after, p=tank_source(after, temperature=50))
    previous = model.detail("2026-10-11", after)["tank_temperature"]
    current = model.detail("2026-10-12", after)["tank_temperature"]
    assert [point["temperature_c"] for point in previous["points"]] == [49]
    assert [point["temperature_c"] for point in current["points"]] == [50]
    assert previous["current"]["temperature_c"] == 50  # Explicit separate live view, UI scopes it to today.
    assert previous["points"][0]["temperature_reported_at"] == before.timestamp()-4


@pytest.mark.parametrize("problem", ["duplicate", "boolean_number", "nonmatching_value", "nonmatching_stamp", "malformed"])
def test_contradictory_typed_split_evidence_cannot_prove_total_zero_energy(problem):
    model = HeatpumpHistory()
    for seconds in (0, 5):
        at = BASE+timedelta(seconds=seconds)
        p = source(at, watts=0, task=None)
        rows = p["power_activity"]["supplies"]
        if problem == "duplicate":
            rows[1]["number"] = 1
        elif problem == "boolean_number":
            rows[0]["number"] = True
        elif problem == "nonmatching_value":
            rows[0]["watts"] = 1
        elif problem == "nonmatching_stamp":
            rows[0]["observed_at"] -= 1
        else:
            p["power_activity"]["supplies"] = {}
        observe(model, at, p=p)
    detail = model.detail(None, at)
    assert detail["energy_kwh"] is None and detail["energy_known_s"] == 0
    assert detail["electrical_activity"]["on_s"] is None


def test_missing_second_assigned_heater_cannot_prove_support_off_with_one_actual_zero():
    from custom_components.solar_pilot.display_operation import classify_display_operation
    model = HeatpumpHistory()
    at = BASE
    p = source(at, task=None, watts=0)
    p["power_activity"]["supplies"][0].update(role="heater", valid=False, watts=None)
    p["power_activity"]["supplies"][1].update(role="heater", watts=0)
    evidence = classify_display_operation(p, now_wall=at.timestamp())
    assert evidence["support"]["active"] is None and evidence["support"]["watts"] is None
    assert model._support(p, at.timestamp(), evidence) == (None, None)
    for seconds in (0, 5):
        at = BASE+timedelta(seconds=seconds)
        observe(model, at, p=p)
    detail = model.detail(None, at)
    assert detail["support_coverage"]["known_s"] == 0
    assert detail["support_totals"] == []


def test_display_and_history_support_share_the_same_role_source_contract():
    from custom_components.solar_pilot.display_operation import classify_display_operation
    at = BASE
    p = source(at, task="tapwater_heating", main=40, heater=2760, watts=2800)
    evidence = classify_display_operation(p, now_wall=at.timestamp())
    assert HeatpumpHistory._support(p, at.timestamp(), evidence) == (evidence["support"]["active"], evidence["support"]["valid_until"])
    assert HeatpumpHistory._state(p, at.timestamp(), 2800)[0:2] == (True, ("tapwater_heating", "confirmed"))
