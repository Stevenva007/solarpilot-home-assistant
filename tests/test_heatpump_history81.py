"""Read-only native context and electrical segments using fictional sources."""
from copy import deepcopy
from datetime import timedelta
import json

import pytest

from custom_components.solar_pilot.heatpump_history import HeatpumpHistory
from custom_components.solar_pilot.heatpump_history_evidence import MAX_POINTS, number
from test_heatpump_history70 import BASE, source, observe


def tank_source(at, *, temperature=57, target=50, **kwargs):
    result = source(at, **kwargs)
    result["display_tank"] = {"entity_id": "water_heater.synthetic_tank", "temperature_c": temperature,
        "temperature_stamp": at.timestamp()-4, "target_c": target, "target_stamp": at.timestamp()-7}
    return result


def test_context_retains_original_times_and_unknown_hygiene_target_result():
    model = HeatpumpHistory()
    p = tank_source(BASE, task="tapwater_heating", tier="derived", main=40, heater=2760, watts=2800)
    before = deepcopy(p)
    observe(model, BASE, p=p)
    data = model.detail(None, BASE)
    point = data["native_evidence"]["points"][0]
    assert point["captured_at"] == BASE.timestamp()
    assert point["tank"] == {"temperature_c": 57, "temperature_reported_at": BASE.timestamp()-4,
        "ordinary_target_c": 50, "ordinary_target_reported_at": BASE.timestamp()-7}
    assert point["native"]["confirmed"] is False and point["native"]["function"] is None
    assert point["effective_target"] == {"temperature_c": None, "reported_at": None, "status": "unknown"}
    assert point["completion"] == {"state": "unknown", "reported_at": None}
    assert point["supplies"][0]["watts"] == 40 and point["supplies"][1]["watts"] == 2760
    assert p == before and "synthetic_tank" not in json.dumps(data)


def test_fresh_invalid_negative_feed_is_unknown_and_real_zero_retained():
    model = HeatpumpHistory()
    p = tank_source(BASE)
    p.update(power_supply1_w=-7, power_supply1_valid=False, power_complete=False,
             power_supply2_w=0, power_supply2_valid=True)
    observe(model, BASE, p=p)
    point = model.detail(None, BASE)["native_evidence"]["points"][0]
    assert point["supplies"][0]["watts"] is None and point["supplies"][0]["fresh"] is True
    assert point["supplies"][1]["watts"] == 0 and point["supplies"][1]["valid"] is True
    assert model.detail(None, BASE)["electrical_activity"]["on_s"] is None


def test_native_start_requires_coherent_original_global_off_transition():
    model = HeatpumpHistory()
    for seconds in (0, 5, 10):
        at = BASE+timedelta(seconds=seconds)
        p = tank_source(at, watts=0, task=None)
        p["native_task"].update(inactive_scope="global", inactive_action="off", verified_global_off=True)
        observe(model, at, p=p)
    observe(model, BASE+timedelta(seconds=15), p=tank_source(BASE+timedelta(seconds=15)))
    points = model.detail(None, BASE+timedelta(seconds=15))["native_evidence"]["points"]
    assert len(points) == 3  # The actual preceding unchanged OFF is retained.
    assert points[-1]["native"]["start_observed"] is True
    assert points[-2]["captured_at"] == (BASE+timedelta(seconds=10)).timestamp()
    restored = HeatpumpHistory()
    restored.restore(model.snapshot(), BASE+timedelta(seconds=20))
    assert restored.detail(None, BASE+timedelta(seconds=20))["native_evidence"]["points"][-1]["native"]["start_observed"] is True


@pytest.mark.parametrize("break_kind", ["gap", "pause", "binding", "space_scope", "same_report", "reversed_report", "independent_tank", "scoped_source"])
def test_gap_reload_rebind_scoped_idle_or_reused_report_cannot_prove_start(break_kind):
    model = HeatpumpHistory()
    p = tank_source(BASE, watts=0, task=None)
    p["native_task"].update(inactive_scope="global", inactive_action="off", verified_global_off=True)
    if break_kind == "space_scope":
        p["native_task"].update(inactive_scope="space_circuit")
    if break_kind == "independent_tank":
        p["native_task"]["independent_tank_on"] = True
    if break_kind == "scoped_source":
        p["native_task"]["source"] = "native_hvac_action"
    observe(model, BASE, p=p)
    if break_kind == "pause":
        model.pause_recording()
    at = BASE+timedelta(seconds=60 if break_kind == "gap" else 5)
    active = tank_source(at)
    if break_kind in ("same_report", "reversed_report"):
        active["native_task"]["observed_at"] = BASE.timestamp()-(1 if break_kind == "reversed_report" else 0)
    observe(model, at, p=active, binding="replacement" if break_kind == "binding" else "same")
    assert model.detail(None, at)["native_evidence"]["points"][-1]["native"]["start_observed"] is False


def test_electrical_segments_never_replace_native_intervals_or_raw_counts():
    model = HeatpumpHistory()
    for seconds, watts in ((0, 0), (5, 1700), (10, 0), (15, 1600), (25, 0)):
        observe(model, BASE+timedelta(seconds=seconds), watts=watts, task="space_heating")
    data = model.detail(None, BASE+timedelta(seconds=25))
    assert data["on_s"] == 25 and data["starts"] == data["stops"] == 0  # Native activity remained on.
    electrical = data["electrical_activity"]
    assert electrical["on_s"] == 15 and electrical["starts"] == electrical["stops"] == 2
    assert [s["duration_s"] for s in electrical["sessions"]] == [5, 10]
    assert all(s["short_observed_period"] for s in electrical["sessions"])
    assert all(s["start_confirmed"] and s["stop_confirmed"] for s in electrical["sessions"])


def test_electrical_gap_is_not_a_stop_or_joined_short_period():
    model = HeatpumpHistory()
    observe(model, BASE, watts=1600, task=None)
    observe(model, BASE+timedelta(seconds=5), watts=1600, task=None)
    observe(model, BASE+timedelta(seconds=100), watts=1600, task=None)
    observe(model, BASE+timedelta(seconds=105), watts=0, task=None)
    electrical = model.detail(None, BASE+timedelta(seconds=105))["electrical_activity"]
    assert electrical["on_s"] == 10 and len(electrical["sessions"]) == 2
    assert electrical["starts"] == 0 and electrical["stops"] == 1
    assert electrical["sessions"][0]["stop_confirmed"] is False


def test_legacy_store_preserves_totals_without_backfilled_new_evidence():
    model = HeatpumpHistory()
    observe(model, BASE)
    observe(model, BASE+timedelta(seconds=5))
    saved = model.snapshot()
    saved.pop("electrical")
    saved.pop("native_evidence")
    other = HeatpumpHistory()
    other.restore(saved, BASE+timedelta(seconds=10))
    data = other.detail(None, BASE+timedelta(seconds=10))
    assert data["on_s"] == 5 and data["energy_known_s"] == 5
    assert data["native_evidence"]["points"] == [] and data["electrical_activity"]["on_s"] is None


@pytest.mark.parametrize("corrupt", ["native_flags", "native_time", "start", "tank_time", "supply_time", "huge", "boolean"])
def test_contradictory_retained_proof_cannot_become_native_confirmation(corrupt):
    model = HeatpumpHistory()
    observe(model, BASE, p=tank_source(BASE))
    saved = model.snapshot()
    point = saved["native_evidence"]["points"][0]
    if corrupt == "native_flags":
        point["native"]["function"] = None
    elif corrupt == "native_time":
        point["native"]["reported_at"] = None
    elif corrupt == "start":
        point["native"]["start_observed"] = True
    elif corrupt == "tank_time":
        point["tank"]["temperature_reported_at"] = BASE.timestamp()-1000
    elif corrupt == "supply_time":
        point["supplies"][0]["reported_at"] = BASE.timestamp()-1000
    elif corrupt == "huge":
        point["supplies"][0]["watts"] = 10**10000
    else:
        point["native"]["reported_at"] = True
    with pytest.raises(ValueError):
        HeatpumpHistory().restore(saved, BASE+timedelta(seconds=10))


def test_unknown_stored_keys_are_never_returned_by_public_proof():
    model = HeatpumpHistory()
    observe(model, BASE, p=tank_source(BASE))
    saved = model.snapshot()
    point = saved["native_evidence"]["points"][0]
    point.update(private_entity="sensor.synthetic_secret")
    point["native"]["entity_id"] = "sensor.synthetic_secret"
    point["effective_target"] = {"temperature_c": 62, "status": "confirmed"}
    point["completion"] = {"state": "succeeded"}
    other = HeatpumpHistory()
    other.restore(saved, BASE+timedelta(seconds=10))
    data = other.detail(None, BASE+timedelta(seconds=10))["native_evidence"]
    assert "synthetic_secret" not in json.dumps(data)
    assert data["points"][0]["effective_target"]["temperature_c"] is None
    assert data["points"][0]["completion"]["state"] == "unknown"


def test_context_retention_is_bounded_and_reports_truncation(monkeypatch):
    from custom_components.solar_pilot import heatpump_history_evidence
    monkeypatch.setattr(heatpump_history_evidence, "MAX_POINTS", 4)
    model = HeatpumpHistory()
    point = tank_source(BASE)
    for n in range(8):
        at = BASE+timedelta(seconds=n*5)
        observe(model, at, p=tank_source(at, temperature=50+n%2))
    data = model.detail(None, at)["native_evidence"]
    assert len(model.native_evidence.points) == 4
    assert data["points_truncated"] is True
    assert number(10**10000) is None


def test_future_source_times_are_invalid_evidence_and_roundtrip_without_fake_zero():
    model = HeatpumpHistory()
    p = tank_source(BASE)
    p["native_task"]["observed_at"] = BASE.timestamp()+1000
    p["display_tank"]["temperature_stamp"] = BASE.timestamp()+1000
    p["power_supply1_observed_at"] = BASE.timestamp()+1000
    observe(model, BASE, p=p)
    other = HeatpumpHistory()
    other.restore(model.snapshot(), BASE+timedelta(seconds=5))
    point = other.detail(None, BASE+timedelta(seconds=5))["native_evidence"]["points"][0]
    assert point["native"]["confirmed"] is False
    assert point["tank"]["temperature_c"] is None and point["supplies"][0]["watts"] is None


def test_bounded_retention_drops_orphan_native_start_and_roundtrips(monkeypatch):
    from custom_components.solar_pilot import heatpump_history_evidence
    monkeypatch.setattr(heatpump_history_evidence, "MAX_POINTS", 1)
    model = HeatpumpHistory()
    p = tank_source(BASE, watts=0, task=None)
    p["native_task"].update(inactive_scope="global", inactive_action="off", verified_global_off=True)
    observe(model, BASE, p=p)
    observe(model, BASE+timedelta(seconds=5))
    assert model.native_evidence.points == []
    assert model.native_evidence.trimmed_before == (BASE+timedelta(seconds=5)).timestamp()
    restored = HeatpumpHistory()
    restored.restore(model.snapshot(), BASE+timedelta(seconds=10))
    observe(restored, BASE+timedelta(seconds=10))
    assert restored.native_evidence.points[0]["native"]["start_observed"] is False


def test_calendar_pruning_cannot_leave_unrestorable_native_start():
    model = HeatpumpHistory()
    before = BASE.replace(hour=21, minute=59, second=55)  # 23:59:55 HA local.
    p = tank_source(before, watts=0, task=None)
    p["native_task"].update(inactive_scope="global", inactive_action="off", verified_global_off=True)
    observe(model, before, p=p)
    at = before+timedelta(seconds=5)
    observe(model, at)
    assert model.native_evidence.points[-1]["native"]["start_observed"] is True
    later = at+timedelta(days=29, hours=2)  # Cross local midnight after DST change.
    model.native_evidence.prune(later.timestamp())
    assert model.native_evidence.points == []  # The preceding day expired.
    restored = HeatpumpHistory()
    restored.restore(model.snapshot(), later)
    assert restored.native_evidence.points == []
