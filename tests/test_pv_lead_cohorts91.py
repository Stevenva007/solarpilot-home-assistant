"""Synthetic lead cohorts must be selected before a shared original outcome."""
from copy import deepcopy
from datetime import timedelta
import json

import pytest

from custom_components.solar_pilot.pv_forecast_evidence import (
    COHORT_SELECTION_RULE, ForecastEvidence, lead_band,
)
from test_pv_evidence81 import BINDING, CONTEXT, NOW, Source, capture

TARGET = NOW + timedelta(hours=4)


def captured_cohorts():
    evidence = ForecastEvidence()
    # First locally available forecast in each band, followed by a revision in
    # the same band. Fixtures contain no real installation entities or values.
    for minutes, watts in ((240, 3000), (225, 2900), (165, 2000),
                           (150, 1900), (45, 1000), (30, 900)):
        capture(evidence, TARGET-timedelta(minutes=minutes), Source(watts=watts))
    return evidence


def observe(evidence, at=TARGET, watts=1200, binding=BINDING, context=CONTEXT, elevation=20):
    evidence.compare(at, watts, at.timestamp(), context, binding, 10000,
                     solar_elevation=elevation, solar_reported_at=at.timestamp())


def target_rows(evidence):
    return [row for row in evidence.cohort_comparisons if row["target_at"] == TARGET.isoformat()]


def test_each_band_keeps_its_first_forecast_and_shares_one_original_measurement():
    evidence = captured_cohorts()
    selected_before = deepcopy([row for row in evidence.cohort_pending if row["target_at"] == TARGET.isoformat()])
    assert {row["lead_band"]: row["raw_w"] for row in selected_before} == {
        "3h_12h": 3000, "1h_3h": 2000, "5m_1h": 1000}
    assert all(row["selection_rule"] == COHORT_SELECTION_RULE for row in selected_before)
    observe(evidence)
    rows = target_rows(evidence)
    assert {row["lead_band"]: row["raw_w"] for row in rows} == {
        row["lead_band"]: row["raw_w"] for row in selected_before}
    assert {row["actual_reported_at"] for row in rows} == {TARGET.isoformat()}
    assert {row["actual_w"] for row in rows} == {1200}
    assert all(row["solar_context"] == rows[0]["solar_context"] for row in rows)
    assert len(evidence.comparisons) == 1 and evidence.comparisons[0]["raw_w"] == 3000
    assert not [row for row in evidence.cohort_pending if row["target_at"] == TARGET.isoformat()]
    observe(evidence, TARGET+timedelta(seconds=30), watts=1800)
    assert target_rows(evidence) == rows  # no revised actual or post-hoc fill


def test_cohort_stats_count_shared_originals_daylight_and_dependency_honestly():
    evidence = captured_cohorts(); observe(evidence)
    saved = evidence.snapshot()
    summary = evidence.summary()["lead_cohort_evidence"]
    assert summary["identity"] == ["target_at", "binding", "lead_band"]
    assert summary["samples"] == 3 and summary["unique_targets"] == summary["unique_original_reports"] == 1
    assert summary["daylight_targets"] == summary["daylight_days"] == summary["distinct_days"] == 1
    assert summary["shared_measurement_rows"] == 2 and summary["statistically_independent"] is False
    assert summary["historical_backfill"] is summary["applied"] is False
    assert {row["lead_band"]: row["mae_w"] for row in summary["by_recorded_lead"]} == {
        "3h_12h": 1200, "1h_3h": 400, "5m_1h": 400}
    assert evidence.summary()["planning_margin_comparison"]["applied"] is False
    assert evidence.snapshot() == saved  # rendering cannot create or tune proof


@pytest.mark.parametrize("ahead,expected", [(299.999, None), (300, "5m_1h"), (3599.999, "5m_1h"),
    (3600, "1h_3h"), (10799.999, "1h_3h"), (10800, "3h_12h"), (43200, "3h_12h"), (43200.001, None), (43201, None)])
def test_band_boundaries_are_fixed_before_outcomes(ahead, expected):
    assert lead_band(ahead) == expected


def test_pending_and_completed_cohorts_roundtrip_without_legacy_backfill_or_replay():
    evidence = captured_cohorts()
    pending = json.loads(json.dumps(evidence.snapshot(), allow_nan=False))
    restored = ForecastEvidence(); restored.restore(pending, now=TARGET)
    assert restored.snapshot() == pending
    capture(restored, TARGET-timedelta(minutes=15), Source(watts=1200))
    assert {row["lead_band"]:row["raw_w"] for row in restored.cohort_pending
            if row["target_at"] == TARGET.isoformat()} == {"3h_12h":3000,"1h_3h":2000,"5m_1h":1000}
    observe(restored)
    saved = json.loads(json.dumps(restored.snapshot(), allow_nan=False))
    restarted = ForecastEvidence(); restarted.restore(saved, now=TARGET)
    assert restarted.snapshot() == saved
    observe(restarted); observe(restarted, TARGET-timedelta(seconds=1))
    assert len(target_rows(restarted)) == 3
    legacy = deepcopy(saved); legacy.pop("lead_cohorts")
    restarted.restore(legacy, now=TARGET)
    assert restarted.comparisons and restarted.snapshots
    assert not restarted.cohort_comparisons and not restarted.cohort_pending
    observe(restarted, TARGET+timedelta(seconds=30))
    assert not restarted.cohort_comparisons  # old snapshots never become a new series


def test_cohorts_compare_when_legacy_already_has_target_and_never_cross_bindings():
    evidence = captured_cohorts()
    old = ForecastEvidence(); capture(old); observe(old)
    evidence.comparisons.extend(old.comparisons)
    observe(evidence)
    assert len(target_rows(evidence)) == 3 and len(evidence.comparisons) == 1
    other = captured_cohorts()
    observe(other, context="c"*64)
    observe(other, TARGET+timedelta(seconds=1), binding="d"*64)
    assert not other.cohort_comparisons


@pytest.mark.parametrize("path,bad", [
    (("captured_at",), True), (("raw_w",), float("nan")), (("corrected_w",), float("inf")),
    (("factor",), True), (("lead_band",), "5m_1h"), (("selection_rule",), "best_after_observation"),
    (("source_context", "source_reported_at"), (TARGET+timedelta(days=1)).isoformat()),
])
def test_malformed_pending_is_isolated_and_cannot_fabricate_selected_proof(path,bad):
    evidence = captured_cohorts(); saved = evidence.snapshot()
    entry = next(row for row in saved["lead_cohorts"]["pending"]
                 if row["target_at"] == TARGET.isoformat() and row["lead_band"] == "3h_12h")
    parent = entry
    for key in path[:-1]: parent = parent[key]
    parent[path[-1]] = bad
    restored = ForecastEvidence(); restored.restore(saved, now=TARGET)
    observe(restored)
    assert {row["lead_band"] for row in target_rows(restored)} == {"1h_3h", "5m_1h"}
    assert restored.snapshots and restored.comparisons
    json.dumps(restored.snapshot(), allow_nan=False)


def test_restore_recomputes_errors_and_refuses_mixed_actuals_or_late_horizon_fill():
    evidence = captured_cohorts(); observe(evidence); saved = evidence.snapshot()
    rows = saved["lead_cohorts"]["comparisons"]
    rows[0]["raw_error_w"] = float("nan")
    rows[0]["recorded_ahead_s"] = 1
    rows[1]["actual_w"] = 1500
    # Stored pending may not create another band after this target was observed.
    pending = captured_cohorts().snapshot()["lead_cohorts"]["pending"]
    saved["lead_cohorts"]["pending"] = pending
    restored = ForecastEvidence(); restored.restore(saved, now=TARGET)
    restored_rows = target_rows(restored)
    assert len(restored_rows) == 2
    assert restored_rows[0]["recorded_ahead_s"] == 14400 and restored_rows[0]["raw_error_w"] == -1800
    assert {row["actual_w"] for row in restored_rows} == {1200}
    assert not [row for row in restored.cohort_pending if row["target_at"] == TARGET.isoformat()]
    observe(restored, TARGET+timedelta(seconds=20))
    assert len(target_rows(restored)) == 2
    json.dumps(restored.snapshot(), allow_nan=False)


@pytest.mark.parametrize("extension", [{"version":99,"private": "preserve"},
    {"version":1,"selection_rule":"future_rule","private":"preserve"}])
def test_unknown_extension_stays_private_without_disabling_legacy(extension):
    evidence = captured_cohorts(); saved = evidence.snapshot(); saved["lead_cohorts"] = extension
    restored = ForecastEvidence(); restored.restore(saved, now=TARGET)
    capture(restored, TARGET-timedelta(minutes=15), Source(watts=500)); observe(restored)
    assert restored.snapshot()["lead_cohorts"] == extension
    assert restored.comparisons and not restored.cohort_comparisons
    assert "private" not in json.dumps(restored.diagnostics())
    assert restored.diagnostics()["cohort_storage_warning"]


@pytest.mark.parametrize("limit", [None, True, float("inf"), float("nan"), -1, 0])
def test_invalid_inverter_limit_creates_neither_legacy_nor_cohort_proof(limit):
    evidence = captured_cohorts()
    evidence.compare(TARGET, 1200, TARGET.timestamp(), CONTEXT, BINDING, limit)
    assert not evidence.comparisons and not evidence.cohort_comparisons


def test_pending_cap_never_evicts_first_selection_to_make_room_for_a_revision(monkeypatch):
    import custom_components.solar_pilot.pv_forecast_evidence as module
    monkeypatch.setattr(module, "MAX_COHORT_PENDING", 4)
    evidence = ForecastEvidence(); capture(evidence)
    first = deepcopy(list(evidence.cohort_pending))
    assert len(first) == 4 and evidence.cohort_capacity_reached
    capture(evidence, NOW+timedelta(minutes=15), Source(watts=1200))
    assert list(evidence.cohort_pending) == first
    saved = evidence.snapshot(); restarted = ForecastEvidence(); restarted.restore(saved, now=TARGET)
    assert restarted.snapshot() == saved
    assert restarted.summary()["lead_cohort_evidence"]["status"] == "capacity_reached"
    assert restarted.summary()["lead_cohort_evidence"]["retention_bounds"]["pending"] == 4


@pytest.mark.parametrize("field,bad", [("source_reported_at", (NOW+timedelta(minutes=10)).isoformat()),
    ("local_data_observed_at", (NOW+timedelta(minutes=10)).isoformat())])
def test_future_source_report_cannot_become_live_ahead_evidence(field,bad):
    class InvalidSource(Source):
        def evidence(self, target, now):
            return {**super().evidence(target,now), field: bad}
    evidence = ForecastEvidence(); capture(evidence, source=InvalidSource())
    assert not evidence.snapshots and not evidence.cohort_pending


@pytest.mark.parametrize("offset", [0, 60])
def test_capture_before_compare_retains_cohorts_for_late_original_meter_report(offset):
    evidence = captured_cohorts()
    reported = TARGET+timedelta(seconds=offset)
    observed = reported+timedelta(seconds=120)
    # The runtime captures first. At the maximum accepted delay/skew the target
    # is already 180s old, but its one original actual remains valid evidence.
    capture(evidence, observed, Source(watts=400))
    evidence.compare(observed, 1200, reported.timestamp(), CONTEXT, BINDING, 10000,
                     solar_elevation=20, solar_reported_at=reported.timestamp())
    assert len(target_rows(evidence)) == 3
    assert {row["actual_reported_at"] for row in target_rows(evidence)} == {reported.isoformat()}
    assert {row["actual_w"] for row in target_rows(evidence)} == {1200}


@pytest.mark.parametrize("phase", ["capture", "compare"])
def test_optional_cohort_failure_keeps_original_legacy_evidence_and_no_private_message(monkeypatch,phase):
    evidence = ForecastEvidence()
    def fail(*args, **kwargs):
        raise RuntimeError("private failure details must not be exported")
    monkeypatch.setattr(evidence, "_"+phase+"_cohorts", fail)
    capture(evidence)
    observe(evidence)
    assert evidence.snapshots and evidence.comparisons
    assert evidence.summary()["lead_cohort_evidence"]["research_errors"] == {phase: "RuntimeError"}
    assert "private failure" not in json.dumps(evidence.diagnostics(), allow_nan=False)
