"""Read-only evidence must distinguish absent times, night zeros and captures."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import time

import pytest

from custom_components.solar_pilot.pv_calibration import PVCalibration
from custom_components.solar_pilot.pv_forecast import PVForecast
from custom_components.solar_pilot.pv_forecast_evidence import ForecastEvidence
from test_pv_evidence81 import BINDING, CONTEXT, NOW, Source, capture
from test_pv_forecast33 import settings, source_fixture, quarter
from test_runtime import build
from test_source_diagnostics81 import prepare_wallbox, proof, report, row


@pytest.fixture
def clock(monkeypatch):
    now = [datetime.now(timezone.utc).timestamp()]
    monkeypatch.setattr(time, "time", lambda: now[0])
    return now


@pytest.mark.parametrize("bad,quality", [(None,"missing"),(0,"zero_sentinel"),(False,"invalid"),
                                        (True,"invalid"),("unknown","invalid"),(float("nan"),"invalid"),
                                        (-1,"invalid"),(32503680001,"invalid"),("1788440000","invalid")])
def test_unknown_original_time_never_enters_quarter_extrema(bad, quality):
    model = PVCalibration(settings()); model.started = NOW.timestamp()-1000
    for minute in range(16):
        at = NOW+timedelta(minutes=minute)
        model.observe(now=at,actual_w=None,raw_w=3000,meter_stamp=bad,binding=BINDING)
    recorded = model.history[-1]
    original = recorded["observation_evidence"]["original_reports"]
    assert original["distinct"] == 0
    assert all(original[key] is None for key in ("first_at","last_at","span_s","max_gap_s"))
    assert original["time_quality"]["unknown"] == original["time_quality"][quality] == 15
    assert not recorded["accepted"] and not model.bins and model.counts["rejected"] == 1
    restored = PVCalibration(settings()); restored.restore(json.loads(json.dumps(model.snapshot(),allow_nan=False)))
    assert restored.history[-1]["observation_evidence"] == recorded["observation_evidence"]


def test_valid_old_reports_stay_stale_evidence_while_zero_is_explicit_unknown():
    model = PVCalibration(settings()); model.started = NOW.timestamp()-1000
    for minute in range(16):
        at = NOW+timedelta(minutes=minute)
        ts = 0 if minute == 4 else at.timestamp()-600
        model.observe(now=at,actual_w=None if minute == 4 else 2400,raw_w=3000,meter_stamp=ts,binding=BINDING)
    original = model.history[-1]["observation_evidence"]["original_reports"]
    assert original["time_quality"] == {"valid":14,"unknown":1,"missing":0,"zero_sentinel":1,"invalid":0}
    assert original["distinct"] == 14 and original["stale"] == 15
    assert original["first_at"] == (NOW-timedelta(minutes=10)).isoformat()
    assert original["max_gap_s"] == 120 and original["span_s"] == 840
    assert not model.bins


def test_valid_quarter_learning_and_legacy_evidence_are_unchanged():
    model = PVCalibration(settings()); quarter(model,NOW)
    saved = model.snapshot(); history = saved["history"][0]
    assert history["accepted"] and model.counts["accepted"] == 1
    assert history["observation_evidence"]["original_reports"]["time_quality"]["unknown"] == 0
    old = deepcopy(saved)
    old["history"][0]["observation_evidence"]["original_reports"].pop("time_quality")
    restored = PVCalibration(settings()); restored.restore(old)
    assert restored.history[0]["observation_evidence"] == old["history"][0]["observation_evidence"]
    learned = lambda instance:{key:(entry["days"],entry["factor"]) for key,entry in instance.bins.items()}
    assert learned(restored) == learned(model) and restored.counts == model.counts
    corrupt = deepcopy(saved)
    corrupt["history"][0]["observation_evidence"]["original_reports"]["time_quality"]["unknown"] = True
    restored.restore(corrupt)
    assert learned(restored) == learned(model) and restored.history[0]["accepted"]
    assert "observation_evidence" not in restored.history[0]


def add_comparison(evidence, minute, watts, actual, elevation=None, sun_offset=0):
    # Each fixture creates a genuinely recorded future target; no hand-built rows.
    at = NOW+timedelta(minutes=minute)
    class OriginalSource(Source):
        def evidence(self,target,now):
            result=super().evidence(target,now)
            result.update(source_reported_at=datetime.fromtimestamp(now,timezone.utc).isoformat(),
                          local_data_observed_at=datetime.fromtimestamp(now,timezone.utc).isoformat())
            return result
    source = OriginalSource(watts=watts)
    capture(evidence,at-timedelta(minutes=30),source=source)
    evidence.compare(at,actual,at.timestamp(),CONTEXT,BINDING,10000,
                     solar_elevation=elevation,solar_reported_at=at.timestamp()+sun_offset if elevation is not None else None)


def conditions(evidence):
    bucket = evidence.summary()["by_recorded_lead"][0]
    return bucket, {entry["condition"]:entry for entry in bucket["conditions"]}


def test_night_zero_cannot_hide_daylight_error_and_zeros_do_not_prove_night():
    evidence = ForecastEvidence()
    # Each comparison was separately recorded 30 minutes ahead, avoiding a
    # later source revision of an earlier retained prediction.
    for minute,watts,actual,elevation in ((15,0,0,-10),(30,0,0,None),(45,0,0,10),(60,3000,1200,20)):
        point=ForecastEvidence(); add_comparison(point,minute,watts,actual,elevation=elevation)
        evidence.comparisons.extend(point.comparisons)
    bucket, groups = conditions(evidence)
    assert groups["night"]["samples"] == groups["other_zero"]["samples"] == 1
    assert groups["night"]["mae_w"] == groups["other_zero"]["mae_w"] == 0
    assert groups["daylight"]["samples"] == 2 and groups["daylight"]["mae_w"] == 600
    assert groups["daylight"]["bias_w"] == -600 and bucket["mae_w"] == 300
    assert groups["daylight"]["unique_targets"] == 2 and groups["daylight"]["distinct_days"] == 1
    assert evidence.summary()["planning_margin_comparison"]["applied"] is False
    assert evidence.summary()["known_original_issue_times"] == 0


@pytest.mark.parametrize("height,offset", [(20,-121),(20,6),(True,0),(float("nan"),0),(91,0),(0,0)])
def test_invalid_stale_future_or_horizon_sun_does_not_prove_daylight(height, offset):
    evidence = ForecastEvidence(); add_comparison(evidence,15,3000,1200,elevation=height,sun_offset=offset)
    _, groups = conditions(evidence)
    assert groups["daylight"]["samples"] == groups["night"]["samples"] == 0
    assert groups["unknown"]["samples"] == 1


def test_solar_context_roundtrip_validates_original_report_and_never_backfills_legacy():
    evidence = ForecastEvidence(); add_comparison(evidence,15,0,0,elevation=-10)
    saved = json.loads(json.dumps(evidence.snapshot(),allow_nan=False))
    restored = ForecastEvidence(); restored.restore(saved,now=NOW+timedelta(hours=1))
    assert restored.snapshot() == saved
    legacy = deepcopy(saved); legacy["comparisons"][0].pop("solar_context")
    restored.restore(legacy,now=NOW+timedelta(hours=1))
    assert "solar_context" not in restored.comparisons[0]
    assert conditions(restored)[1]["other_zero"]["samples"] == 1
    bad = deepcopy(saved); bad["comparisons"][0]["solar_context"]["elevation_deg"] = True
    restored.restore(bad,now=NOW+timedelta(hours=1))
    assert conditions(restored)[1]["other_zero"]["samples"] == 1


def test_orchestration_passes_original_sun_without_promoting_calculated_fallback(monkeypatch):
    runtime,hass,_,now = source_fixture(monkeypatch,at=NOW)
    hass.states.set("sun.sun","above_horizon",{"elevation":20,"azimuth":180})
    sun = hass.states.get("sun.sun"); sun.last_reported = sun.last_updated = now-timedelta(seconds=15)
    forecast = PVForecast(runtime)
    captured = []
    monkeypatch.setattr(forecast.forecast_evidence,"compare",lambda *args,**kwargs:captured.append(kwargs))
    forecast.update(now)
    assert captured[-1] == {"solar_elevation":20,"solar_reported_at":now.timestamp()-15}
    hass.states.data.pop("sun.sun")
    forecast.update(now+timedelta(minutes=1))
    assert captured[-1] == {"solar_elevation":None,"solar_reported_at":None}
    assert not hass.services.calls


def test_normal_new_solar_report_is_not_configuration_change_or_mixed_explanation(clock):
    runtime,hass = build(); proof(runtime,hass,clock[0],pv_age=15)
    engine = runtime.learning_hub.investigation
    initial = row(engine.refresh(clock[0]),"solar_balance")
    state = deepcopy(engine.snapshot()); old_proof = deepcopy(initial["metrics"]["proof"])
    clock[0] += 10; proof(runtime,hass,clock[0],pv=7000)
    current = row(engine.overview(clock[0]),"solar_balance")
    assert current["metrics"]["assessment_proof"] == old_proof
    assert current["metrics"]["proof"]["pv_w"] == 7000
    assert current["summary"] == initial["summary"] and current["evidence"] == initial["evidence"]
    assert current["assessment_observed_at"] == initial["assessment_observed_at"]
    assert current["current_observed_at"] == clock[0]
    assert current["observation_changed"] is True and current["context_changed"] is False
    assert engine.snapshot() == state and not hass.services.calls


def test_equal_value_with_new_original_reports_is_observation_not_identity(clock):
    runtime,hass = build(); proof(runtime,hass,clock[0])
    engine = runtime.learning_hub.investigation; engine.refresh(clock[0]); state=deepcopy(engine.snapshot())
    clock[0]+=5; proof(runtime,hass,clock[0])
    current=row(engine.overview(clock[0]),"solar_balance")
    assert current["observation_changed"] and not current["context_changed"]
    assert "broncontext is gewijzigd" not in current["summary"]
    assert engine.snapshot()==state


def test_actual_binding_change_and_expiry_are_distinct_from_observed_values(clock):
    runtime,hass = build(); proof(runtime,hass,clock[0])
    engine=runtime.learning_hub.investigation; engine.refresh(clock[0]); before=deepcopy(engine.snapshot())
    clock[0]+=121
    expired=row(engine.overview(clock[0]),"solar_balance")
    assert expired["metrics"]["proof"]["status"]=="insufficient_sources"
    assert expired["metrics"]["assessment_proof"]["grid_w"]==-6000
    assert expired["observation_changed"] and not expired["context_changed"]
    runtime.settings["pv_entity"]="sensor.other_pv"; report(hass,"sensor.other_pv",7000,clock[0])
    changed=row(engine.overview(clock[0]),"solar_balance")
    assert changed["context_changed"] and changed["observation_changed"]
    assert "broncontext is gewijzigd" in changed["summary"]
    assert engine.snapshot()==before and not hass.services.calls


def test_wallbox_cached_relative_age_stays_bound_to_its_assessment(clock):
    runtime,hass=build(); prepare_wallbox(runtime,hass,clock[0])
    report(hass,"sensor.ev_session","Laden gestopt",clock[0]-19000)
    engine=runtime.learning_hub.investigation; initial=row(engine.refresh(clock[0]),"wallbox_source")
    before=deepcopy(engine.snapshot()); clock[0]+=10
    current=row(engine.overview(clock[0]),"wallbox_source")
    assert current["metrics"]["assessment_source_dossier"]["session"]["age_s"]==19000
    assert current["metrics"]["source_dossier"]["session"]["age_s"]==19010
    assert current["evidence"]==initial["evidence"]
    assert not current["context_changed"] and not current["observation_changed"]
    assert engine.snapshot()==before and not hass.services.calls
