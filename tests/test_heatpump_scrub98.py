"""Historical cursor data uses recorded meter evidence, never current values."""
from copy import deepcopy
from datetime import timedelta
import json

import pytest

from custom_components.solar_pilot.heatpump_history import HeatpumpHistory
from test_heatpump_history70 import BASE, observe, source


def point(model, when=BASE):
    return model.detail(None, when)["native_evidence"]["points"][-1]


@pytest.mark.parametrize("watts", [0, 1800, 100000])
def test_new_comparison_point_retains_validated_total_and_original_meter_times(watts):
    model = HeatpumpHistory()
    p = source(BASE, watts=watts)
    before = deepcopy(p)
    observe(model, BASE, p=p)
    expected = {"schema": 1, "total_w": watts, "reported_at": BASE.timestamp(),
        "valid_until": BASE.timestamp()+120, "stale_s": 120,
        "source_scope": "split", "complete": True, "kind": "measured"}
    assert point(model)["power"] == expected and p == before
    later = BASE+timedelta(days=1)
    restored = HeatpumpHistory()
    restored.restore(model.snapshot(), later)
    assert restored.detail(BASE.date().isoformat(), later)["native_evidence"]["points"][0]["power"] == expected


def test_full_total_meter_does_not_need_fictional_split_supplies():
    model = HeatpumpHistory()
    p = {"power_kind": "measured", "power_scope": "total", "power_complete": True,
        "power_w": 2345, "power_observed_at": BASE.timestamp()-17, "source_stale_s": 120}
    observe(model, BASE, p=p)
    power = point(model)["power"]
    assert power["total_w"] == 2345 and power["source_scope"] == "total"
    assert power["reported_at"] == BASE.timestamp()-17
    assert power["valid_until"] == BASE.timestamp()+103
    restored = HeatpumpHistory()
    restored.restore(model.snapshot(), BASE+timedelta(seconds=5))
    assert point(restored, BASE+timedelta(seconds=5))["power"] == power


def test_split_total_keeps_the_oldest_actual_contributing_report_and_expiry():
    model = HeatpumpHistory()
    p = source(BASE)
    p["power_observed_at"] = BASE.timestamp()-10
    for n, age in ((1, 20), (2, 40)):
        p[f"power_supply{n}_observed_at"] = BASE.timestamp()-age
        p["power_activity"]["supplies"][n-1]["observed_at"] = BASE.timestamp()-age
    observe(model, BASE, p=p)
    power = point(model)["power"]
    assert power["total_w"] == 1800 and power["complete"]
    assert power["reported_at"] == BASE.timestamp()-40
    assert power["valid_until"] == BASE.timestamp()+80
    restored = HeatpumpHistory()
    restored.restore(model.snapshot(), BASE+timedelta(seconds=5))
    assert point(restored, BASE+timedelta(seconds=5))["power"] == power


@pytest.mark.parametrize("invalid", ["partial", "estimate", "old_total", "old_feed", "missing_feed", "inconsistent_sum", "boolean", "nan", "negative"])
def test_unusable_full_meter_cannot_become_historical_total(invalid):
    model = HeatpumpHistory()
    p = source(BASE)
    if invalid == "partial":
        p["power_complete"] = False
    elif invalid == "estimate":
        p["power_kind"] = "estimated"
    elif invalid == "old_total":
        p["power_observed_at"] = BASE.timestamp()-121
    elif invalid == "old_feed":
        p["power_supply1_observed_at"] = BASE.timestamp()-121
    elif invalid == "missing_feed":
        p["power_supply2_valid"] = False
    elif invalid == "inconsistent_sum":
        p["power_supply1_w"] = 1700
    else:
        p["power_w"] = {"boolean": True, "nan": float("nan"), "negative": -1}[invalid]
    observe(model, BASE, p=p)
    power = point(model)["power"]
    assert power["total_w"] is None and power["valid_until"] is None
    assert power["complete"] is False
    restored = HeatpumpHistory()
    restored.restore(model.snapshot(), BASE+timedelta(seconds=5))
    assert point(restored, BASE+timedelta(seconds=5))["power"] == power


def test_watt_changes_do_not_expand_existing_comparison_point_rhythm_or_rewrite_previous_values():
    model = HeatpumpHistory()
    for seconds in range(0, 301, 5):
        observe(model, BASE+timedelta(seconds=seconds), watts=1800+seconds)
    points = model.detail(None, BASE+timedelta(seconds=300))["native_evidence"]["points"]
    assert [row["captured_at"] for row in points] == [BASE.timestamp(), BASE.timestamp()+300]
    assert [row["power"]["total_w"] for row in points] == [1800, 2100]
    assert model.detail(None, BASE+timedelta(seconds=300))["energy_known_s"] == 300


def test_legacy_missing_power_is_never_filled_from_later_measurement_or_day_energy():
    model = HeatpumpHistory()
    observe(model, BASE)
    observe(model, BASE+timedelta(seconds=10))
    saved = model.snapshot()
    for row in saved["native_evidence"]["points"]:
        row.pop("power")
    old = deepcopy(saved)
    restored = HeatpumpHistory()
    restored.restore(saved, BASE+timedelta(seconds=20))
    observe(restored, BASE+timedelta(seconds=20), watts=4200)
    points = restored.detail(None, BASE+timedelta(seconds=20))["native_evidence"]["points"]
    assert "power" not in points[0] and points[-1]["power"]["total_w"] == 4200
    assert saved == old and restored.detail(None, BASE+timedelta(seconds=20))["energy_kwh"] == .005


@pytest.mark.parametrize("boundary", ["gap", "pause", "binding", "restore"])
def test_source_boundaries_keep_separate_actual_power_samples_without_continuity(boundary):
    model = HeatpumpHistory()
    observe(model, BASE, watts=1800)
    after = BASE+timedelta(seconds=60 if boundary == "gap" else 5)
    if boundary == "pause":
        model.pause_recording()
    elif boundary == "restore":
        restored = HeatpumpHistory()
        restored.restore(model.snapshot(), after)
        model = restored
    observe(model, after, watts=2400, binding="replacement" if boundary == "binding" else "same")
    points = model.detail(None, after)["native_evidence"]["points"]
    assert [row["power"]["total_w"] for row in points] == [1800, 2400]
    assert points[-1]["continuity"] is False
    assert model.detail(None, after)["energy_known_s"] == 0


def test_day_bounds_are_numeric_utc_seconds_even_for_a_day_without_observations():
    model = HeatpumpHistory()
    observe(model, BASE)
    day = (BASE-timedelta(days=1)).date().isoformat()
    data = model.detail(day, BASE)
    assert (data["day_start"], data["day_end"]) == model.lanes._bounds(day)
    assert type(data["day_start"]) in (int, float) and type(data["day_end"]) in (int, float)
    assert data["day_end"]-data["day_start"] == data["day_seconds"] == 86400
    assert data["native_evidence"]["points"] == [] and data["energy_kwh"] is None


def test_restored_power_whitelist_does_not_disclose_source_identities_or_labels():
    model = HeatpumpHistory()
    observe(model, BASE)
    saved = model.snapshot()
    saved["native_evidence"]["points"][0]["power"].update(
        entity_id="sensor.fictional_private_meter", label="fictional-private-label")
    restored = HeatpumpHistory()
    restored.restore(saved, BASE+timedelta(seconds=5))
    payload = json.dumps(restored.detail(None, BASE+timedelta(seconds=5)))
    assert "fictional_private_meter" not in payload and "fictional-private-label" not in payload
