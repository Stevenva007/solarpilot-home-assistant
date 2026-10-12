"""Adversarial recurring-edge evidence: no fabricated days or unsafe learning."""
from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot.pv_calibration import (
    EDGE_MAX_DAYS, PVCalibration,
)
from custom_components.solar_pilot.pv_forecast_source import PV_FORECAST_DEFAULTS


LOCAL = ZoneInfo("Europe/Brussels")
START = datetime(2026, 6, 1, 16, 0, tzinfo=LOCAL)
BINDING = "independent-test-source"


def model(**settings):
    return PVCalibration({**PV_FORECAST_DEFAULTS, **settings})


def edge_quarter(m, dt, *, split=7, before=1., after=.4,
                 invalid_minute=None, fault=None, binding=BINDING):
    """Fifteen one-minute independently stamped samples, then close the quarter."""
    m.started = dt.timestamp() - 1000
    for minute in range(16):
        now = dt + timedelta(minutes=minute)
        actual = 4000 * (before if minute < split else after)
        meter_stamp = now.timestamp()
        if minute == invalid_minute:
            if fault == "clipping":
                actual = 9970
            elif fault == "outlier":
                actual = 0
            elif fault == "stale":
                meter_stamp -= 300
            elif fault == "nan":
                actual = float("nan")
        m.observe(now=now, actual_w=actual, raw_w=4000,
                  meter_stamp=meter_stamp, azimuth=250, elevation=35,
                  binding=binding)
    return m.history[-1]


def record(**kw):
    return {"direction": "drop", "offset_s": 390.,
            "before": 1., "after": .4, "value": .68,
            "samples": 15, "span_s": 840., "max_gap_s": 60., **kw}


def snapshot_with_records(records, *, binding=BINDING):
    return {"version": 1, "binding": binding,
            "edge_evidence": {"2:clock:64": {"days": records}}}


@pytest.mark.parametrize("field", ["offset_s", "before", "after", "value"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True])
def test_nonfinite_or_boolean_candidate_values_cannot_become_evidence(field, bad):
    m = model()
    m.restore(snapshot_with_records({"2026-06-01": record(**{field: bad})}))
    assert not m.edge_evidence
    json.dumps(m.snapshot(), allow_nan=False)


@pytest.mark.parametrize("value", [.15, 1.6])
def test_restored_energy_ratio_must_fit_the_measured_plateaus(value):
    m = model()
    m.restore(snapshot_with_records({"2026-06-01": record(value=value)}))
    assert not m.edge_evidence


@pytest.mark.parametrize("proof", [
    {"samples": 11}, {"samples": 21}, {"samples": True},
    {"span_s": 659}, {"span_s": float("nan")},
    {"max_gap_s": 121}, {"max_gap_s": float("inf")},
])
def test_incomplete_or_nonfinite_persisted_coverage_proof_cannot_seed_evidence(proof):
    m = model()
    m.restore(snapshot_with_records({"2026-06-01": record(**proof)}))
    assert not m.edge_evidence


@pytest.mark.parametrize("binding", [None, "", 123])
def test_unbound_restored_candidates_cannot_transfer_to_an_arbitrary_source(binding):
    m = model()
    days = {(START + timedelta(days=i)).date().isoformat(): record() for i in range(5)}
    m.restore(snapshot_with_records(days, binding=binding))
    assert not m.edge_evidence
    row = edge_quarter(m, START + timedelta(days=5))
    assert not row["accepted"]
    assert m.factor(START + timedelta(days=6), 250, 35)[0] == 1.


def test_source_change_clears_candidates_and_factors_together():
    m = model()
    for day in range(8):
        edge_quarter(m, START + timedelta(days=day))
    assert m.factor(START + timedelta(days=8), 250, 35)[0] < 1.
    edge_quarter(m, START + timedelta(days=8), binding="replacement-source")
    assert m.counts["source_changed"] == 1
    assert not m.bins
    assert all(len(entry["days"]) == 1 for entry in m.edge_evidence.values())
    assert m.factor(START + timedelta(days=9), 250, 35)[0] == 1.


def test_repeated_same_day_after_restart_never_manufactures_distinct_days():
    m = model()
    for _ in range(12):
        edge_quarter(m, START)
        saved = json.loads(json.dumps(m.snapshot(), allow_nan=False))
        m = model()
        m.restore(saved)
    assert all(len(entry["days"]) == 1 for entry in m.edge_evidence.values())
    assert not m.bins
    assert m.factor(START, 250, 35)[0] == 1.


@pytest.mark.parametrize("preset,minimum", [("normal", 5), ("slow", 7)])
def test_preset_minimum_days_is_not_bypassed_by_edge_evidence(preset, minimum):
    m = model(learning_preset=preset)
    for day in range(minimum - 1):
        assert not edge_quarter(m, START + timedelta(days=day))["accepted"]
    assert not m.bins
    assert edge_quarter(m, START + timedelta(days=minimum - 1))["accepted"]


def test_explicit_larger_minimum_days_is_respected():
    m = model(minimum_days=8)
    for day in range(7):
        assert not edge_quarter(m, START + timedelta(days=day))["accepted"]
    assert not m.bins
    assert edge_quarter(m, START + timedelta(days=7))["accepted"]


def test_cloud_steps_at_inconsistent_times_do_not_learn():
    m = model()
    for day, split in enumerate([4, 7, 10, 5, 8]):
        row = edge_quarter(m, START + timedelta(days=day), split=split)
        assert not row["accepted"]
    assert row["edge_candidate_state"] == "inconsistent"
    assert not m.bins


def test_alternating_drop_and_recovery_never_share_a_shadow_profile():
    m = model()
    for day in range(6):
        pair = (1., .4) if day % 2 == 0 else (.4, 1.)
        row = edge_quarter(m, START + timedelta(days=day), before=pair[0], after=pair[1])
        assert not row["accepted"]
    assert row["edge_candidate_state"] == "inconsistent"
    assert not m.bins


def test_large_day_to_day_magnitude_changes_remain_untrusted():
    m = model()
    for day, after in enumerate([.35, .45, .6, .7, .35, .6]):
        row = edge_quarter(m, START + timedelta(days=day), after=after)
        assert not row["accepted"]
    assert row["edge_candidate_state"] == "inconsistent"
    assert not m.bins


@pytest.mark.parametrize("fault", ["clipping", "outlier", "stale", "nan"])
def test_any_bad_sample_disqualifies_the_entire_edge_quarter(fault):
    m = model()
    for day in range(8):
        row = edge_quarter(m, START + timedelta(days=day), invalid_minute=3, fault=fault)
        assert not row["accepted"]
    assert not m.edge_evidence
    assert not m.bins


def test_cloud_drop_followed_by_recovery_in_one_quarter_is_not_a_single_edge():
    m = model()
    for day in range(8):
        dt = START + timedelta(days=day)
        m.started = dt.timestamp() - 1000
        for minute in range(16):
            now = dt + timedelta(minutes=minute)
            ratio = .4 if 4 <= minute < 8 else 1.
            m.observe(now=now, actual_w=4000 * ratio, raw_w=4000,
                      meter_stamp=now.timestamp(), azimuth=250, elevation=35,
                      binding=BINDING)
        assert not m.history[-1]["accepted"]
    assert not m.edge_evidence
    assert not m.bins


def test_incomplete_edge_quarters_cannot_seed_repeated_evidence():
    m = model()
    for day in range(8):
        dt = START + timedelta(days=day)
        m.started = dt.timestamp() - 1000
        for minute in [0, 1, 2, 3, 6, 7, 8, 9, 12, 13, 14, 15]:
            now = dt + timedelta(minutes=minute)
            m.observe(now=now, actual_w=4000 if minute < 7 else 1600,
                      raw_w=4000, meter_stamp=now.timestamp(), azimuth=250,
                      elevation=35, binding=BINDING)
        assert not m.history[-1]["accepted"]
    assert not m.edge_evidence


@pytest.mark.parametrize("seconds", [
    [minute * 60 for minute in range(15) if minute not in (4, 5)],
    [index * 55 for index in range(12)],
    [150 + index * 60 for index in range(12)],
])
def test_sample_count_alone_does_not_replace_span_gap_and_boundary_coverage(seconds):
    m = model()
    for day in range(6):
        dt = START + timedelta(days=day)
        m.started = dt.timestamp() - 1000
        for index, second in enumerate(seconds):
            now = dt + timedelta(seconds=second)
            m.observe(now=now, actual_w=4000 if index < 6 else 1600,
                      raw_w=4000, meter_stamp=now.timestamp(),
                      azimuth=250, elevation=35, binding=BINDING)
        end = dt + timedelta(minutes=15)
        m.observe(now=end, actual_w=1600, raw_w=4000,
                  meter_stamp=end.timestamp(), azimuth=250, elevation=35,
                  binding=BINDING)
        assert not m.history[-1]["accepted"]
    assert not m.edge_evidence


def test_edge_factor_steps_once_per_date_and_never_replays_an_older_date():
    m = model()
    previous = 1.
    for day in range(10):
        dt = START + timedelta(days=day)
        edge_quarter(m, dt)
        factor = m.factor(dt, 250, 35)[0]
        assert abs(factor - previous) <= .05 + 1e-9
        previous = factor
    saved = json.loads(json.dumps(m.snapshot(), allow_nan=False))
    replay = model()
    replay.restore(saved)
    edge_quarter(replay, START + timedelta(days=8))
    assert replay.factor(START + timedelta(days=9), 250, 35)[0] == pytest.approx(previous)


def test_deep_recurring_shadow_stops_at_the_existing_factor_floor():
    m = model()
    for day in range(24):
        edge_quarter(m, START + timedelta(days=day), before=.4, after=.15)
    assert m.factor(START + timedelta(days=24), 250, 35)[0] == pytest.approx(.35)


def test_persisted_candidate_date_must_match_its_season_key():
    m = model()
    m.restore(snapshot_with_records({"2026-12-01": record()}))
    assert not m.edge_evidence


@pytest.mark.parametrize("before,after,expected", [(1., .4, 9.9 / 15), (.4, 1., 11.1 / 15)])
def test_transition_factor_uses_elapsed_energy_instead_of_one_plateau_median(before, after, expected):
    m = model()
    for day in range(14):
        edge_quarter(m, START + timedelta(days=day), before=before, after=after)
    factor = m.factor(START + timedelta(days=14), 250, 35)[0]
    assert factor == pytest.approx(expected)
    # The switch is halfway between minutes 6 and 7. The last plateau extends
    # from minute 14 to the quarter boundary, so the durations are 6.5/8.5 min.
    # This intermediate correction belongs to the transition quarter, rather
    # than treating its entire duration as either the lit or shaded plateau.
    assert min(before, after) < factor < max(before, after)
    assert "global" not in m.bins


def test_edge_evidence_is_seasonal_and_does_not_create_global_correction():
    m = model()
    for day in range(8):
        edge_quarter(m, START + timedelta(days=day))
    assert m.factor(START + timedelta(days=8), 250, 35)[0] < 1.
    assert m.factor(START.replace(month=12), 250, 35)[0] == 1.
    assert "global" not in m.bins
    m.settings["shadow_enabled"] = False
    assert m.factor(START + timedelta(days=8), 250, 35)[0] == 1.


def test_future_dates_and_date_time_aliases_never_count_as_current_evidence():
    m = model()
    days = {(START + timedelta(days=i + 10)).date().isoformat(): record() for i in range(6)}
    days.update({f"2026-06-01T0{i}:00:00": record() for i in range(6)})
    m.restore(snapshot_with_records(days))
    details = m.factor_details(START)
    assert details["edge_candidate_days"] == 0
    assert details["factor"] == 1.


def test_restored_candidates_are_bounded_and_whitelisted():
    m = model()
    days = {(START + timedelta(days=i)).date().isoformat(): record() for i in range(100)}
    payload = snapshot_with_records(days)
    payload["edge_evidence"].update({"global": {"days": days},
                                      "SECRET-LOCATION": {"days": days}})
    payload["edge_evidence"]["2:clock:64"]["days"]["2026-07-31"] = {
        **record(), "latitude": 51., "api_key": "MUST_NOT_SURVIVE"}
    m.restore(payload)
    saved = m.snapshot()
    assert all(len(entry["days"]) <= EDGE_MAX_DAYS for entry in saved["edge_evidence"].values())
    assert "global" not in saved["edge_evidence"]
    assert "SECRET-LOCATION" not in saved["edge_evidence"]
    assert "MUST_NOT_SURVIVE" not in json.dumps(saved, allow_nan=False)
    assert "latitude" not in json.dumps(saved, allow_nan=False)
