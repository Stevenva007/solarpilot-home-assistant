"""Synthetic evidence regressions: provenance is never actuator or learn proof."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot.pv_calibration import PVCalibration
from custom_components.solar_pilot.pv_forecast import PVForecast
from custom_components.solar_pilot.pv_forecast_evidence import ForecastEvidence, MAX_SNAPSHOTS
from custom_components.solar_pilot.pv_forecast_source import PowerSeries, ForecastSolarSource
from test_pv_forecast33 import settings, source_fixture, quarter

NOW = datetime(2026, 9, 3, 12, tzinfo=timezone.utc)
BINDING = "a" * 64
CONTEXT = "b" * 64


class Source:
    valid = True

    def __init__(self, watts=3000, identity=CONTEXT):
        self.watts = watts; self.identity = identity

    def raw_at(self, target, now):
        return self.watts

    def evidence(self, target, now):
        return {"source_context_id": self.identity, "provider": "forecast_solar",
                "issued_at": NOW.isoformat(), "issue_time_status": "known",
                "source_reported_at": NOW.isoformat(), "local_data_observed_at": NOW.isoformat(),
                "value_origin": "curve"}


def details(dt):
    return {"factor": .8, "confidence": .7, "days": 7, "validated_days": 7,
            "minimum_days_required": 5, "eligible": True, "applied": True,
            "fallback_used": False, "reason": "Synthetic validated quarter", "profile_kind": "clock"}


def capture(evidence, now=NOW, source=None, binding=BINDING):
    evidence.capture(now, source or Source(), lambda t, raw, tz: raw*.8, details, binding)


def compare(evidence, now, actual=2200, report=None, context=CONTEXT, binding=BINDING):
    evidence.compare(now, actual, now.timestamp() if report is None else report, context, binding, 10000.)


def test_quarter_finite_median_does_not_hide_invalid_part():
    model = PVCalibration(settings()); model.started = NOW.timestamp()-1000
    for minute in range(16):
        at = NOW+timedelta(minutes=minute)
        model.observe(now=at, actual_w=None if minute == 5 else 2400, raw_w=3000,
                      meter_stamp=at.timestamp(), binding=BINDING, forecast_context=Source().evidence(0,0))
    row = model.history[-1]; proof = row["observation_evidence"]
    assert row["actual_w"] == 2400 and not row["accepted"] and not model.bins
    assert proof["observations"] == 15 and proof["valid_observations"] == 14 and proof["rejected_observations"] == 1
    assert proof["rejection_reasons"] == [{"reason": "Ontbrekende of ongeldige PV-/forecastmeting", "count": 1}]
    assert proof["original_reports"]["distinct"] == 15
    assert proof["coverage"]["span_s"] == 840 and proof["coverage"]["max_gap_s"] == 60
    assert proof["forecast_contexts"][0]["issued_at"] is None


def test_stale_missing_duplicate_conflicting_and_out_of_order_reports_remain_rejected():
    model = PVCalibration(settings()); model.started = NOW.timestamp()-1000
    # All stamps and values are invented; each diagnostic category is distinct.
    reports = [NOW.timestamp(), NOW.timestamp(), NOW.timestamp(), None,
               NOW.timestamp()-600, (NOW+timedelta(minutes=5)).timestamp(),
               (NOW+timedelta(minutes=5, seconds=-1)).timestamp()]
    for minute in range(16):
        at = NOW+timedelta(minutes=minute)
        reported = reports[minute] if minute < len(reports) else at.timestamp()
        model.observe(now=at, actual_w=2500 if minute == 2 else 2400,
                      raw_w=3000, meter_stamp=reported, binding=BINDING)
    row = model.history[-1]; original = row["observation_evidence"]["original_reports"]
    assert not row["accepted"] and not model.bins
    assert {name:original[name] for name in ("missing","stale","duplicate","conflicting","out_of_order")} == {
        "missing":1,"stale":1,"duplicate":1,"conflicting":1,"out_of_order":1}
    restored = PVCalibration(settings()); restored.restore(json.loads(json.dumps(model.snapshot(), allow_nan=False)))
    assert restored.history[-1]["observation_evidence"] == row["observation_evidence"]


@pytest.mark.parametrize("bad", [True, "nan", float("inf"), [], None])
def test_invalid_original_report_times_do_not_gain_valid_counts(bad):
    model = PVCalibration(settings()); model.started = NOW.timestamp()-1000
    for minute in range(16):
        at = NOW+timedelta(minutes=minute)
        model.observe(now=at,actual_w=2400,raw_w=3000,meter_stamp=bad,binding=BINDING)
    proof = model.history[-1]["observation_evidence"]
    assert proof["valid_observations"] == 0 and proof["original_reports"]["missing"] == 15
    assert proof["original_reports"]["first_at"] is None
    json.dumps(model.snapshot(),allow_nan=False)


def test_legacy_history_does_not_invent_original_reports_and_bad_extension_isolated():
    model = PVCalibration(settings()); quarter(model, NOW)
    legacy = model.snapshot(); legacy["history"][0].pop("observation_evidence")
    restored = PVCalibration(settings()); restored.restore(legacy)
    assert "observation_evidence" not in restored.history[0]
    malformed = model.snapshot()
    malformed["history"][0]["observation_evidence"]["original_reports"]["distinct"] = True
    restored.restore(malformed)
    assert restored.history[0]["accepted"] and "observation_evidence" not in restored.history[0]
    assert {k:(v["days"],v["factor"]) for k,v in restored.bins.items()} == {k:(v["days"],v["factor"]) for k,v in model.bins.items()}


def test_source_report_and_local_scan_are_not_original_forecast_issue(monkeypatch):
    runtime,hass,entries,now = source_fixture(monkeypatch,at=NOW)
    # An arbitrary similarly named cache field is not a documented issue proof.
    entries[0].runtime_data.data.issued_at = NOW-timedelta(hours=8)
    source = ForecastSolarSource(hass,settings()); source.refresh(NOW.timestamp())
    proof = source.evidence(NOW.timestamp()+3600,NOW.timestamp())
    assert proof["source_reported_at"] == NOW.isoformat()
    assert proof["local_data_observed_at"] == NOW.isoformat()
    assert proof["issued_at"] is None and proof["original_issue_horizon_s"] is None
    assert proof["issue_time_status"] == "unknown" and proof["value_origin"] == "curve"
    assert proof["source_metadata"]["inverter_size"]==10000
    assert "api_key" not in json.dumps(proof) and "latitude" not in json.dumps(proof)
    assert not hass.services.calls


def test_later_revised_forecast_never_replaces_earlier_ahead_target():
    evidence = ForecastEvidence(); capture(evidence)
    capture(evidence,NOW+timedelta(minutes=15),Source(watts=2100))
    at = NOW+timedelta(hours=1)
    compare(evidence,at)
    row = evidence.comparisons[-1]
    assert row["raw_w"] == 3000 and row["corrected_w"] == 2400
    assert row["captured_at"] == NOW.isoformat() and row["recorded_ahead_s"] == 3600
    assert row["issued_at"] is None and row["original_issue_horizon_s"] is None
    compare(evidence,at+timedelta(seconds=30))
    assert len(evidence.comparisons) == 1  # one retained target gives one vote
    assert evidence.summary()["current_error_is_ahead_accuracy"] is False


@pytest.mark.parametrize("actual,report_offset", [(None,0),(True,0),(float("nan"),0),(12000,0),(2400,-300),(2400,10)])
def test_invalid_stale_future_and_outlier_reports_cannot_become_accuracy(actual,report_offset):
    evidence = ForecastEvidence(); capture(evidence)
    at = NOW+timedelta(hours=1)
    compare(evidence,at,actual=actual,report=at.timestamp()+report_offset)
    assert not evidence.comparisons


def test_changed_context_or_meter_binding_cannot_compare_old_profile():
    evidence = ForecastEvidence(); capture(evidence)
    at = NOW+timedelta(hours=1)
    compare(evidence,at,context="c"*64)
    compare(evidence,at+timedelta(seconds=1),binding="d"*64)
    assert not evidence.comparisons


def test_concurrent_capture_and_scalar_missing_horizon_do_not_fabricate_future_error():
    evidence = ForecastEvidence(); capture(evidence)
    compare(evidence,NOW)
    assert not evidence.comparisons
    class Scalar(Source):
        def raw_at(self,target,now): return 3000 if abs(target-now-3600)<1 else None
    scalar = ForecastEvidence(); capture(scalar,source=Scalar())
    assert len(scalar.snapshots[0]["predictions"]) == 1
    assert scalar.snapshots[0]["predictions"][0]["recorded_ahead_s"] == 3600


def test_evidence_storage_roundtrip_bounds_bad_fields_and_unknown_schema():
    evidence = ForecastEvidence(); capture(evidence)
    compare(evidence,NOW+timedelta(hours=1))
    saved = json.loads(json.dumps(evidence.snapshot(),allow_nan=False))
    restored = ForecastEvidence(); restored.restore(saved)
    assert restored.snapshot() == saved
    compare(restored,NOW+timedelta(hours=1))
    assert len(restored.comparisons) == 1
    malformed = deepcopy(saved)
    malformed["comparisons"][0]["corrected_error_w"] = float("nan")  # recomputed from original fields
    malformed["comparisons"][0]["issued_at"] = NOW.isoformat()
    malformed["snapshots"][0]["predictions"].append({"raw_w":True})
    restored.restore(malformed)
    assert len(restored.comparisons) == 1 and restored.comparisons[0]["issued_at"] is None
    assert restored.comparisons[0]["corrected_error_w"] == -200
    json.dumps(restored.snapshot(),allow_nan=False)
    future = {"version":99,"private_future":{ "keep": [1,2,3] }}
    restored.restore(future); capture(restored); compare(restored,NOW+timedelta(hours=1))
    assert restored.snapshot() == future and not restored.diagnostics()["comparisons"]
    assert restored.diagnostics()["storage_warning"]
    bounded = ForecastEvidence()
    for index in range(MAX_SNAPSHOTS+12): capture(bounded,NOW+timedelta(minutes=index*15))
    assert len(bounded.snapshots) == MAX_SNAPSHOTS and all(len(s["predictions"])<=48 for s in bounded.snapshots)


def test_future_storage_and_source_chronology_cannot_create_evidence():
    evidence=ForecastEvidence(); capture(evidence); compare(evidence,NOW+timedelta(hours=1))
    saved=evidence.snapshot(); restored=ForecastEvidence()
    restored.restore(saved,now=NOW-timedelta(days=1))
    assert not restored.snapshots and not restored.comparisons
    bad=deepcopy(saved)
    bad["snapshots"][0]["source_context"]["source_reported_at"]=(NOW+timedelta(hours=2)).isoformat()
    restored.restore(bad,now=NOW+timedelta(hours=3))
    assert not restored.snapshots
    bad=deepcopy(saved)
    bad["comparisons"][0]["source_reported_at"]=(NOW+timedelta(hours=2)).isoformat()
    restored.restore(bad,now=NOW+timedelta(hours=3))
    assert not restored.comparisons
    duplicated=deepcopy(saved)
    extra=deepcopy(duplicated["comparisons"][0])
    extra["actual_reported_at"]=(NOW+timedelta(hours=1,seconds=30)).isoformat()
    extra["observed_at"]=extra["actual_reported_at"]
    duplicated["comparisons"].append(extra)
    restored.restore(duplicated,now=NOW+timedelta(hours=3))
    assert len(restored.comparisons)==1


def test_runtime_archive_readonly_persistence_legacy_and_unknown_model(monkeypatch):
    runtime,hass,entries,now = source_fixture(monkeypatch,at=NOW)
    runtime.hass.config=NS(latitude=51,longitude=4,time_zone="Europe/Brussels")
    forecast=PVForecast(runtime); forecast.update(NOW)
    before=forecast.hourly(NOW,4)
    assert forecast.diagnostics()["forecast_evidence"]["snapshots"]
    assert all(h["forecast_provenance"]["issued_at"] is None for h in forecast.cached["horizon"])
    saved=forecast.snapshot(); restored=PVForecast(runtime); restored.restore(saved)
    assert restored.forecast_evidence.snapshot() == forecast.forecast_evidence.snapshot()
    assert forecast.hourly(NOW,4) == before and not hass.services.calls
    old=deepcopy(saved); old.pop("forecast_evidence")
    restored.restore(old); assert not restored.forecast_evidence.snapshots
    unknown={"version":99,"future_extension":{ "preserve":True }}
    restored.restore(unknown)
    assert restored.snapshot() == unknown


def test_margin_is_chronological_holdout_only_and_never_applied():
    evidence=ForecastEvidence()
    for day in range(4):
        dt=NOW+timedelta(days=day); capture(evidence,dt)
        for slot in range(8): compare(evidence,dt+timedelta(minutes=15*(slot+1)),actual=2200 if day<3 else 2300)
    summary=evidence.summary(); margin=summary["planning_margin_comparison"]
    assert margin["status"] == "comparison_only" and margin["margin_w"] == 200
    assert margin["training_samples"] == 24 and margin["holdout_samples"] == 8
    assert margin["baseline_mae_w"] == 100 and margin["hypothetical_mae_w"] == 100
    assert margin["applied"] is False and summary["known_original_issue_times"] == 0
    saved=evidence.snapshot()
    evidence.summary(); assert evidence.snapshot() == saved


def test_mixed_bindings_or_clipping_do_not_tune_margin_from_incomparable_population():
    evidence=ForecastEvidence()
    for day in range(4):
        dt=NOW+timedelta(days=day); binding=BINDING if day<3 else "c"*64
        capture(evidence,dt,binding=binding)
        for slot in range(8): compare(evidence,dt+timedelta(minutes=15*(slot+1)),binding=binding)
    assert evidence.summary()["planning_margin_comparison"]["status"] == "insufficient"


@pytest.mark.parametrize("failure", ["provenance","capture","summary","diagnostics","quarter_evidence"])
def test_optional_research_failure_preserves_forecast_learning_and_planner(monkeypatch,failure):
    runtime,hass,entries,now=source_fixture(monkeypatch,at=NOW)
    runtime.hass.config=NS(latitude=51,longitude=4,time_zone="Europe/Brussels")
    baseline=PVForecast(runtime);baseline.update(NOW);expected=baseline.hourly(NOW,4)
    forecast=PVForecast(runtime)
    def fail(*args,**kwargs):raise RuntimeError("private details must not leak")
    if failure=="provenance":monkeypatch.setattr(forecast.source,"evidence",fail)
    elif failure=="capture":monkeypatch.setattr(forecast.forecast_evidence,"capture",fail)
    elif failure=="summary":monkeypatch.setattr(forecast.forecast_evidence,"summary",fail)
    elif failure=="diagnostics":monkeypatch.setattr(forecast.forecast_evidence,"diagnostics",fail)
    else:monkeypatch.setattr(forecast.model,"_observation_evidence",fail)
    forecast.update(NOW)
    assert forecast.cached["available"] and forecast.source.valid
    assert forecast.hourly(NOW,4)==expected
    diagnostic=forecast.diagnostics()
    assert "private details" not in json.dumps(diagnostic,allow_nan=False)
    assert not hass.services.calls
    if failure=="quarter_evidence":
        model=PVCalibration(settings()); model.started=NOW.timestamp()-1000
        monkeypatch.setattr(model,"_observation_evidence",fail)
        quarter(model,NOW)
        assert model.history[-1]["accepted"] and model.counts["accepted"]==1 and model.bins
        assert model.history[-1]["observation_evidence_error"]=="RuntimeError"
