"""Recurring transitions must earn seasonal evidence before PV correction."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot.pv_calibration import PVCalibration
from custom_components.solar_pilot.pv_forecast_source import PV_FORECAST_DEFAULTS

NOW = datetime(2026, 6, 20, 16, 0, tzinfo=ZoneInfo("Europe/Brussels"))
AZ, EL = 240, 35


def model(**settings):
    return PVCalibration({**PV_FORECAST_DEFAULTS, **settings})


def quarter(m, dt, before=1.0, after=0.4, split=7, binding="source-a",
            ratios=None, dirty=None, raw=3000.0, az=AZ, el=EL):
    m.started = dt.timestamp() - 1000
    ratios = ratios or [before] * split + [after] * (15 - split)
    for minute in range(16):
        at = dt + timedelta(minutes=minute)
        actual = raw * ratios[min(minute, 14)]
        stamp = at.timestamp()
        if dirty == "stale" and minute == 4:
            stamp -= 1000
        if dirty == "missing" and minute == 4:
            actual = None
        if dirty == "clipping" and minute == 4:
            actual = 9900
        if dirty == "outlier" and minute == 4:
            actual = 100
        m.observe(now=at, actual_w=actual, raw_w=raw, meter_stamp=stamp,
                  azimuth=az, elevation=el, binding=binding)
    return m.history[-1]


@pytest.mark.parametrize("before,after,direction,target", [(1, 0.4, "drop", 0.66), (0.4, 1, "recovery", 0.74)])
def test_fifth_distinct_day_proves_edge_and_starts_bounded_learning(before, after, direction, target):
    m = model()
    previous_rows = []
    for day in range(5):
        row = quarter(m, NOW + timedelta(days=day), before, after)
        if day < 4:
            assert not row["accepted"] and row["edge_candidate_state"] == "pending"
            previous_rows.append(deepcopy(row))
            assert m.factor(NOW + timedelta(days=day), AZ, EL)[0] == 1
    details = m.factor_details(NOW + timedelta(days=4), AZ, EL)
    assert row["accepted"] and details["factor"] == pytest.approx(0.95)
    assert details["applied"] and details["profile_kind"] == "sun"
    assert details["edge"]["status"] == "trusted"
    assert details["edge"]["candidate_days"] == 5
    assert details["edge"]["direction"] == direction
    assert m.edge_evidence[m._keys(NOW, AZ, EL)[0]]["days"][NOW.date().isoformat()]["value"] == pytest.approx(target)
    assert [row for row in m.history if row.get("edge_candidate") and not row["accepted"]] == previous_rows
    assert "global" not in m.bins


def test_stable_step_is_not_a_permanent_sixteen_hour_rule():
    m = model()
    for day in range(5):
        quarter(m, NOW + timedelta(days=day))
    assert m.factor(NOW + timedelta(days=4), AZ, EL)[0] < 1
    # Neither a different clock quarter nor a different sun position inherits it.
    other = NOW + timedelta(days=4, hours=2)
    assert m.factor(other, 290, 15)[0] == 1
    assert m.factor(NOW.replace(month=12), AZ, EL)[0] == 1


def test_details_show_three_real_profile_days_without_enabling_correction():
    m = model()
    for day in range(3):
        quarter(m, NOW + timedelta(days=day), before=0.8, after=0.8)
    details = m.factor_details(NOW + timedelta(days=2), AZ, EL)
    assert details["days"] == 3 and details["minimum_days_required"] == 5
    assert details["confidence"] == pytest.approx(0.25)
    assert not details["eligible"] and details["validated_days"] == 0
    assert details["factor"] == 1 and not details["applied"]
    assert "onvoldoende" in details["reason"]
    assert m.factor(NOW + timedelta(days=2), AZ, EL)[:3] == (1, 0, 0)


def test_details_prefer_real_clock_evidence_when_geometry_has_none():
    m = model()
    for day in range(3):
        quarter(m, NOW + timedelta(days=day), before=0.8, after=0.8, az=150, el=50)
    details = m.factor_details(NOW + timedelta(days=2), AZ, EL)
    assert details["days"] == 3 and details["profile_kind"] == "clock"
    assert details["fallback_used"] and not details["eligible"]


def test_three_geometry_days_do_not_block_a_valid_clock_profile():
    m = model()
    for day in range(5):
        quarter(m, NOW + timedelta(days=day), before=0.8, after=0.8,
                az=AZ if day<3 else 150, el=EL if day<3 else 50)
    details = m.factor_details(NOW + timedelta(days=4), AZ, EL)
    assert details["days"] == details["validated_days"] == 5
    assert details["profile_kind"] == "clock" and details["eligible"]
    assert details["factor"] == pytest.approx(0.95)


def test_many_edges_same_day_cannot_supply_five_days():
    m = model()
    for interval in range(8):
        quarter(m, NOW + timedelta(minutes=30 * interval))
    assert all(len(entry["days"]) == 1 for entry in m.edge_evidence.values())
    assert not m.bins
    assert m.factor(NOW, AZ, EL)[0] == 1


@pytest.mark.parametrize("ratios", [
    [1 if minute % 2 else 0.4 for minute in range(15)],
    [1 - minute * 0.04 for minute in range(15)],
    [1] * 5 + [0.4] * 5 + [1] * 5,
])
def test_alternating_clouds_ramps_and_multiple_steps_remain_rejected(ratios):
    m = model()
    for day in range(7):
        row = quarter(m, NOW + timedelta(days=day), ratios=ratios)
        assert not row["accepted"]
    assert not m.edge_evidence and not m.bins


def test_inconsistent_edge_time_cannot_become_a_shadow_pattern():
    m = model()
    for day, split in enumerate([4, 8, 5, 9, 4, 8]):
        row = quarter(m, NOW + timedelta(days=day), split=split)
    assert row["edge_candidate_state"] == "inconsistent"
    assert not m.bins
    assert m.factor_details(NOW + timedelta(days=5), AZ, EL)["edge"]["status"] == "inconsistent"


@pytest.mark.parametrize("dirty", ["stale", "missing", "clipping", "outlier"])
def test_dirty_quarter_cannot_contribute_edge_proof(dirty):
    m = model()
    for day in range(7):
        row = quarter(m, NOW + timedelta(days=day), dirty=dirty)
        assert not row["accepted"]
    assert not m.edge_evidence and not m.bins


@pytest.mark.parametrize("policy", ["calibration_enabled", "shadow_enabled"])
def test_policy_off_does_not_collect_or_apply_new_edges(policy):
    m = model(**{policy: False})
    for day in range(7):
        row = quarter(m, NOW + timedelta(days=day))
        assert not row["accepted"]
    assert not m.edge_evidence
    assert m.factor(NOW + timedelta(days=6), AZ, EL)[0] == 1


def test_v1_restore_preserves_legacy_bins_and_is_idempotent_with_edges():
    m = model()
    legacy = {"version": 1, "binding": "source-a", "bins": {
        "2:sun:24:7": {"days": {"2026-06-01": [0.8]}, "factor": 0.95, "updated_day": "2026-06-01"}},
        "history": [], "counts": {"accepted": 1}, "revision": 1}
    m.restore(legacy)
    assert m.bins == legacy["bins"] and not m.edge_evidence
    for day in range(5):
        quarter(m, NOW + timedelta(days=day))
    saved = json.loads(json.dumps(m.snapshot(), allow_nan=False))
    rest = model()
    rest.restore(saved)
    first = rest.snapshot()
    rest.restore(first)
    assert rest.snapshot() == first
    assert rest.factor_details(NOW + timedelta(days=4), AZ, EL) == m.factor_details(NOW + timedelta(days=4), AZ, EL)


def test_rebinding_clears_candidates_and_legacy_factors_together():
    m = model()
    for day in range(5):
        quarter(m, NOW + timedelta(days=day))
    assert m.edge_evidence and m.bins
    quarter(m, NOW + timedelta(days=5), binding="source-b")
    assert all(len(entry["days"]) == 1 for entry in m.edge_evidence.values())
    assert not m.bins and m.counts["source_changed"] == 1


def test_trusted_quarter_fallback_requires_stronger_specific_evidence():
    m = model()
    geometry = m._keys(NOW, AZ, EL)[0]
    m.bins[geometry] = {"factor": 0.7, "updated_day": "2026-06-05",
        "days": {f"2026-06-0{day}": [value] for day, value in enumerate([1, 0.2, 0.9, 0.2, 0.8], 1)}}
    for day in range(6):
        # Each measurement is in another geometry bin, but the same local quarter.
        quarter(m, NOW + timedelta(days=day), az=150 + day * 10, el=50)
    details = m.factor_details(NOW + timedelta(days=5), AZ, EL)
    assert details["applied"] and details["fallback_used"]
    assert details["profile_kind"] == "clock"
    assert "sterker bewijs" in details["source"]
    assert details["edge"]["status"] == "trusted"


def test_ordinary_clock_model_does_not_bypass_noisy_geometry():
    m = model()
    geometry, clock = m._keys(NOW, AZ, EL)
    m.bins[geometry] = {"factor": 0.7, "days": {f"2026-06-0{day}": [value] for day, value in enumerate([1, 0.2, 0.9, 0.2, 0.8], 1)}}
    m.bins[clock] = {"factor": 0.8, "days": {f"2026-06-{day:02d}": [0.8] for day in range(1, 10)}}
    details = m.factor_details(NOW, AZ, EL)
    assert details["factor"] == 1 and not details["applied"]
    assert details["profile_kind"] == "sun" and not details["fallback_used"]


def test_historical_date_rerun_cannot_step_a_factor_twice_after_restore():
    m = model()
    for day in range(6):
        quarter(m, NOW + timedelta(days=day))
    restored = model()
    restored.restore(m.snapshot())
    key = m._keys(NOW, AZ, EL)[0]
    before = restored.bins[key]["factor"]
    quarter(restored, NOW + timedelta(days=4))
    assert restored.bins[key]["factor"] == before
