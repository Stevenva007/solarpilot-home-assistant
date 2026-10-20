"""Planner findings and learning questions use the same observed daylight error."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from custom_components.solar_pilot.planner_quality import PlanQualityTracker
from test_runtime import build


def observations(*, daylight=12, error=1329.5, zero_pairs=24, other_warnings=False):
    """Use public observations; zero pairs carry no inferred daylight proof."""
    quality = PlanQualityTracker()
    start = datetime.now(timezone.utc)-timedelta(days=2)
    for index in range(zero_pairs+daylight):
        at = start+timedelta(seconds=301*index)
        actual = 0 if index < zero_pairs else 1000
        predicted = actual if index < zero_pairs else actual+error
        quality.observe(wall_ts=at.timestamp(), local_now=at,
                        predicted_pv_w=predicted, actual_pv_w=actual,
                        predicted_base_w=200 if other_warnings else None,
                        actual_base_w=800 if other_warnings else None,
                        execution_total=2 if other_warnings else 0,
                        execution_matches=0)
    return quality


def pv_warning(findings):
    return any("PV-voorspelling wijkt" in text for text in findings)


def unknown_pv(findings):
    return any("te weinig daglichtvergelijkingen" in text for text in findings)


def positive_summary(findings):
    return any("binnen de ingestelde waarschuwingsbanden" in text for text in findings)


def test_zero_pairs_cannot_hide_a_large_daylight_error_in_the_summary():
    overview = observations().overview()
    recent = overview["last_7d"]
    assert recent["pv_mae_w"] < 700 < recent["pv_daylight_mae_w"]
    assert recent["pv_daylight_samples"] == 12
    assert pv_warning(overview["findings"])
    assert not positive_summary(overview["findings"])


@pytest.mark.parametrize("daylight", [11, 12])
@pytest.mark.parametrize("error", [700, 700.1])
def test_daylight_warning_uses_the_same_strict_count_and_error_boundaries_as_questions(daylight, error):
    quality = observations(daylight=daylight, error=error)
    findings = quality.overview()["findings"]
    expected = daylight >= 12 and error > 700
    assert pv_warning(findings) is expected
    assert unknown_pv(findings) is (daylight < 12)
    assert positive_summary(findings) is (daylight >= 12 and error <= 700)


@pytest.mark.parametrize("source", ["zero_only", "few_daylight", "legacy"])
def test_missing_or_insufficient_daylight_is_unknown_even_with_many_overall_samples(source):
    if source == "legacy":
        quality = PlanQualityTracker()
        quality.restore({"days": {datetime.now(timezone.utc).date().isoformat(): {
            "count": 100, "pv_abs": 10000, "pv_bias": -10000}}})
    else:
        quality = observations(daylight=0 if source == "zero_only" else 11)
    overview = quality.overview()
    assert overview["last_7d"]["samples"] >= 12
    assert unknown_pv(overview["findings"])
    assert not positive_summary(overview["findings"])
    assert not pv_warning(overview["findings"])
    if source == "legacy":
        assert overview["last_7d"]["pv_daylight_mae_w"] is None
        assert overview["last_7d"]["covered_hours"] is None


def test_insufficient_pv_evidence_keeps_existing_base_and_execution_warnings():
    overview = observations(daylight=0, other_warnings=True).overview()
    findings = overview["findings"]
    assert unknown_pv(findings)
    assert any("basislastvoorspelling wijkt af" in text for text in findings)
    assert any("apparaatgedrag" in text for text in findings)
    assert not positive_summary(findings)


def test_summary_read_changes_no_observations_scores_or_existing_metrics():
    quality = observations()
    stored = deepcopy(quality.snapshot())
    before = deepcopy(quality._aggregate(7))
    first = quality.overview()
    second = quality.overview()
    assert quality.snapshot() == stored
    assert first == second and first["last_7d"] == before
    assert before["pv_mae_w"] == round(12*1329.5/36, 1)
    assert before["pv_daylight_mae_w"] == 1329.5
    assert before["pv_daylight_bias_w"] == -1329.5
    # An advisory finding does not silently clamp the independent quality score.
    assert before["quality_score"] == round(100*(1-(12*1329.5/36)/1800), 1)


def test_actual_learning_hub_question_and_quality_finding_agree_without_control_changes():
    runtime, hass = build()
    before = deepcopy((runtime.settings, runtime.planner_settings, runtime.mode,
                       runtime.faults, runtime.sg_boost.snapshot(), runtime.dishwasher.snapshot()))
    for daylight, error in ((11, 1329.5), (12, 700), (12, 700.1), (12, 1329.5)):
        runtime.unified_planner.quality = observations(daylight=daylight, error=error)
        overview = runtime.learning_hub.refresh(force=True)
        asked = any(question["id"] == "pv_error" for question in overview["questions"])
        assert asked is (daylight >= 12 and error > 700)
        assert pv_warning(overview["quality"]["findings"]) is asked
    after = (runtime.settings, runtime.planner_settings, runtime.mode,
             runtime.faults, runtime.sg_boost.snapshot(), runtime.dishwasher.snapshot())
    assert after == before
    assert not hass.services.calls

