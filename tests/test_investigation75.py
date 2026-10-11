"""Local research is source-backed, bounded, durable and has no control route."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import time

import pytest

from custom_components.solar_pilot.investigation import LocalInvestigation, MAX_NEGATIVE_REPORTS, MAX_SOURCES
from test_runtime import build


@pytest.fixture
def clock(monkeypatch):
    now = [datetime.now(timezone.utc).timestamp()]
    monkeypatch.setattr(time, "time", lambda: now[0])
    return now


def report(hass, entity, value, now, attrs=None):
    hass.states.set(entity, value, {"unit_of_measurement": "W", **(attrs or {})})
    obj = hass.states.get(entity)
    obj.last_reported = obj.last_updated = datetime.fromtimestamp(now, timezone.utc)


def heatpump(runtime):
    runtime.panasonic.settings.update(power_entity="sensor.hp_total", power_scope="total",
        power_supply1_entity="", power_supply2_entity="", stale_s=120)


def row(overview, topic):
    return next(item for item in overview["items"] if item["id"] == topic)


def test_initial_overview_and_snapshot_have_no_current_validity():
    runtime, hass = build()
    engine = LocalInvestigation(runtime)
    assert engine.overview()["items"] == []
    assert engine.overview()["read_only"] is True
    assert "updated_at" not in engine.snapshot()
    assert "items" not in engine.snapshot()
    assert not hass.services.calls


def test_current_complete_measurement_is_separate_from_diagnosis_repair(clock):
    runtime, hass = build()
    heatpump(runtime)
    report(hass, "sensor.hp_total", 2100, clock[0])
    result = row(runtime.learning_hub.investigation.refresh(clock[0]), "heatpump_meter")
    assert result["status"] == "observed_ok"
    assert result["metrics"]["current_w"] == 2100
    assert result["metrics"]["reports"] == 1
    assert "geen fysieke reparatie" in result["next_action"]
    assert not hass.services.calls


def test_counter_counts_new_source_reports_not_refreshes_or_changed_values(clock):
    runtime, hass = build()
    heatpump(runtime)
    report(hass, "sensor.hp_total", -7, clock[0])
    engine = runtime.learning_hub.investigation
    first = row(engine.refresh(clock[0]), "heatpump_meter")
    hass.states.get("sensor.hp_total").state = "-8"
    for _ in range(10):
        assert row(engine.refresh(clock[0] + 10), "heatpump_meter")["metrics"]["reports"] == 1
    clock[0] += 61
    assert row(engine.refresh(clock[0]), "heatpump_meter")["metrics"]["reports"] == 1
    assert not first["hypotheses"]
    report(hass, "sensor.hp_total", -7, clock[0])
    clock[0] += 61
    assert row(engine.refresh(clock[0]), "heatpump_meter")["metrics"]["reports"] == 2


def test_low_negative_pattern_proposes_comparison_without_credit_or_transformation(clock):
    runtime, hass = build()
    heatpump(runtime)
    before = deepcopy(runtime.settings)
    for value in (-6, -7, -8, -7, -6.5):
        report(hass, "sensor.hp_total", value, clock[0])
        result = row(runtime.learning_hub.investigation.refresh(clock[0]), "heatpump_meter")
        clock[0] += 61
    assert result["status"] == "check_needed"
    assert result["metrics"]["negative_min_w"] == -8
    assert result["metrics"]["current_w"] is None
    assert "mogelijk" in result["hypotheses"][0]
    assert "geen tekenomkering" in result["proposals"][0]["text"]
    assert runtime.settings == before and not hass.services.calls


def test_negative_pattern_no_longer_presented_as_current_when_source_is_healthy(clock):
    runtime, hass = build()
    heatpump(runtime)
    engine = runtime.learning_hub.investigation
    for _ in range(5):
        report(hass, "sensor.hp_total", -7, clock[0])
        engine.refresh(clock[0])
        clock[0] += 61
    report(hass, "sensor.hp_total", 2000, clock[0])
    healthy = row(engine.refresh(clock[0]), "heatpump_meter")
    assert healthy["status"] == "observed_ok"
    assert healthy["hypotheses"] == []
    assert healthy["metrics"]["negative_reports"] == 5


def test_binding_change_resets_prior_evidence_and_revokes_cache(clock):
    runtime, hass = build()
    heatpump(runtime)
    report(hass, "sensor.hp_total", 2000, clock[0])
    engine = runtime.learning_hub.investigation
    engine.refresh(clock[0])
    runtime.panasonic.settings["power_entity"] = "sensor.replacement"
    assert row(engine.overview(), "heatpump_meter")["status"] == "collecting"
    clock[0] += 61
    report(hass, "sensor.replacement", -7, clock[0])
    fresh = row(engine.refresh(clock[0]), "heatpump_meter")
    assert fresh["metrics"]["reports"] == 1
    assert fresh["metrics"]["valid_reports"] == 0


def test_restart_retains_counters_but_neither_current_proof_nor_duplicate_report(clock):
    runtime, hass = build()
    heatpump(runtime)
    report(hass, "sensor.hp_total", 2000, clock[0])
    engine = runtime.learning_hub.investigation
    engine.refresh(clock[0])
    saved = json.loads(json.dumps(engine.snapshot()))
    restored = LocalInvestigation(runtime)
    restored.restore(saved)
    assert restored.overview()["items"] == []
    assert restored.overview()["updated_at"] is None
    assert row(restored.refresh(clock[0]), "heatpump_meter")["metrics"]["reports"] == 1
    hass.states.get("sensor.hp_total").attributes["restored"] = True
    clock[0] += 61
    assert row(restored.refresh(clock[0]), "heatpump_meter")["status"] == "check_needed"


def test_cached_current_proof_expires_and_unavailable_invalidates_immediately(clock):
    runtime, hass = build()
    heatpump(runtime)
    report(hass, "sensor.hp_total", 2000, clock[0])
    engine = runtime.learning_hub.investigation
    engine.refresh(clock[0])
    hass.states.get("sensor.hp_total").state = "unavailable"
    assert row(engine.overview(), "heatpump_meter")["metrics"]["current_w"] is None
    hass.states.get("sensor.hp_total").state = "2000"
    clock[0] += 121
    assert row(engine.overview(), "heatpump_meter")["status"] == "collecting"


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -1, "invalid", None])
def test_malformed_refresh_never_changes_counters_or_revives_proof(clock, value):
    runtime, hass = build()
    engine = runtime.learning_hub.investigation
    engine.refresh(clock[0])
    saved = engine.snapshot()
    engine.refresh(value)
    assert engine.snapshot() == saved
    assert not hass.services.calls


def test_wallbox_source_current_success_is_scoped_to_one_session(clock):
    runtime, hass = build()
    runtime.wallbox_settings.update(enabled=True, power_entity="sensor.ev_power", status_entity="sensor.ev_status",
                                   mode_entity="sensor.ev_mode", session_mode_entity="sensor.ev_session")
    report(hass, "sensor.ev_power", 1400, clock[0])
    for entity, value in (("sensor.ev_status", "Charging"), ("sensor.ev_mode", "Full solar"), ("sensor.ev_session", "Zonne-auto · laden")):
        hass.states.set(entity, value)
        hass.states.get(entity).last_reported = datetime.fromtimestamp(clock[0], timezone.utc)
    engine = runtime.learning_hub.investigation
    good = row(engine.refresh(clock[0]), "wallbox_source")
    assert good["status"] == "observed_ok"
    assert good["metrics"]["valid_reports"] == 1
    assert "huidige sessiemelding" in good["next_action"]
    hass.states.get("sensor.ev_session").attributes["estimated"] = True
    assert row(engine.overview(), "wallbox_source")["status"] == "collecting"
    clock[0] += 61
    bad = row(engine.refresh(clock[0]), "wallbox_source")
    assert bad["metrics"]["cause"] == "estimated" and bad["status"] == "check_needed"
    assert bad["metrics"]["reports"] == 1
    assert not hass.services.calls


def test_pv_uses_existing_daylight_scores_without_causal_or_fixed_factor_claim(clock):
    runtime, hass = build(settings={"pv_entity": "sensor.pv"})
    report(hass, "sensor.pv", 3000, clock[0])
    runtime.pv_forecast.cached = {"model": {"accepted": 14, "rejected": 3}, "comparable_days": 2}
    quality = {"last_7d": {"pv_daylight_samples": 40, "pv_daylight_mae_w": 1600, "pv_daylight_bias_w": -1100}}
    result = row(runtime.learning_hub.investigation.refresh(clock[0], quality=quality), "pv_forecast")
    assert result["status"] == "check_needed"
    assert result["metrics"]["daylight_samples_7d"] == 40
    assert result["metrics"]["calibration_accepted"] == 14
    assert "onderscheidt hun oorzaak niet" in result["hypotheses"][0]
    assert "geen vaste factor" in result["next_action"]
    assert not hass.services.calls


def test_missing_consumer_meter_is_unknown_while_legitimate_zero_is_current(clock):
    runtime, hass = build(power=True)
    report(hass, "sensor.load", 0, clock[0])
    engine = runtime.learning_hub.investigation
    good = row(engine.refresh(clock[0]), "consumer_meters")
    assert good["status"] == "observed_ok" and good["metrics"]["valid_meters"] == 1
    runtime.configs["a"]["power_entity"] = ""
    assert row(engine.overview(), "consumer_meters")["status"] == "collecting"
    clock[0] += 61
    missing = row(engine.refresh(clock[0]), "consumer_meters")
    assert missing["status"] == "not_configured"
    assert missing["metrics"]["valid_reports"] == 0
    assert "nominaal vermogen is geen gemeten" in missing["proposals"][0]["text"]


def test_bounded_consumer_selection_cannot_claim_full_coverage(clock):
    runtime, hass = build(power=True)
    for i in range(MAX_SOURCES+1):
        runtime.configs[str(i)] = {"name": f"Load {i}", "power_entity": f"sensor.load_{i}"}
        report(hass, f"sensor.load_{i}", 1, clock[0])
    runtime.configs.pop("a")
    result = row(runtime.learning_hub.investigation.refresh(clock[0]), "consumer_meters")
    assert result["status"] == "collecting"
    assert result["metrics"]["unexamined_count"] == 1
    assert result["metrics"]["reports"] == MAX_SOURCES
    assert len(runtime.learning_hub.investigation.records["consumer_meters"]["cursors"]) == MAX_SOURCES


def test_negative_rows_and_restored_state_are_bounded(clock):
    runtime, hass = build()
    heatpump(runtime)
    engine = runtime.learning_hub.investigation
    for _ in range(MAX_NEGATIVE_REPORTS + 10):
        report(hass, "sensor.hp_total", -7, clock[0])
        engine.refresh(clock[0])
        clock[0] += 61
    assert len(engine.snapshot()["records"]["heatpump_meter"]["negatives"]) == MAX_NEGATIVE_REPORTS
    saved = engine.snapshot()
    saved["records"]["heatpump_meter"]["counts"] = {"reports": 10**12, "valid_reports": True, "negative_reports": float("inf")}
    saved["records"]["heatpump_meter"]["cursors"].update({"bad_bool": True, "bad_future": clock[0]+100, "bad_nan": float("nan")})
    restored = LocalInvestigation(runtime)
    restored.restore(saved)
    counters = restored.snapshot()["records"]["heatpump_meter"]
    assert counters["counts"] == {"reports": 1_000_000, "valid_reports": 0, "negative_reports": 0}
    assert "bad_bool" not in counters["cursors"] and "bad_future" not in counters["cursors"]


@pytest.mark.parametrize("data", [None, [], {"schema": True}, {"schema": 2}, {"schema": 1, "records": []}])
def test_bad_persistence_never_restores_live_proof(data):
    runtime, hass = build()
    engine = runtime.learning_hub.investigation
    engine.restore(data)
    assert engine.overview()["items"] == []
    assert not hass.services.calls


def test_learning_hub_exposes_private_export_and_persisted_research(clock):
    runtime, hass = build()
    heatpump(runtime)
    report(hass, "sensor.hp_total", -7, clock[0])
    before = deepcopy(runtime.sg_boost.settings)
    cached = runtime.learning_hub.refresh(force=True)
    assert cached["investigation"]["read_only"] is True
    assert runtime.learning_hub.summary()["investigation"] == cached["investigation"]
    saved = runtime.learning_hub.snapshot()
    assert saved["investigation"]["records"]["heatpump_meter"]["counts"]["negative_reports"] == 1
    export = runtime.analysis.build(include_names=True)
    assert export["components"]["learning_evidence_and_questions"]["investigation"]["read_only"] is True
    assert before == runtime.sg_boost.settings and not hass.services.calls
