"""Independent privacy, evidence and read-only advice contract regressions.

HA doubles and Node renderers here are not live HA/browser acceptance.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from custom_components.solar_pilot import analysis_review as review
from custom_components.solar_pilot import feedback_store as feedback
from custom_components.solar_pilot.const import VERSION
from test_analysis_export import report_context
from test_analysis_api import api
from test_consumer_history_api import context
from test_runtime import build
from test_overview_details60 import Markup


def source_export(seed="a"):
    return {"export_id": "export_" + seed * 32, "export_sha256": seed * 64,
            "release": VERSION, "created_at": "2026-10-11T00:00:00+00:00"}


def advice(source=None):
    return {"schema": "solarpilot.analysis_feedback", "schema_version": 1,
            "source_export": source or source_export(), "analyzed_at": "2026-10-11T01:00:00Z",
            "summary": "De voedingsmetingen zijn gedeeltelijk beschikbaar.",
            "recommendations": [{"category": "observation", "text": "Controleer de ontbrekende bron.",
                                  "evidence": ["Voeding 2 ontbreekt in het meetvenster."],
                                  "confidence": "low", "limitations": ["Geen thermische meting."]}],
            "limitations": ["Geen bewezen SG-effect."], "question_answers": []}


@pytest.mark.asyncio
async def test_post_commit_publication_failure_does_not_claim_feedback_was_rolled_back(api):
    runtime, hass, connection, results, errors = context()
    report = advice()
    before_options = deepcopy(runtime.entry.options)
    before_policy = deepcopy(runtime.learning_hub.policy)

    def broken_listener():
        raise RuntimeError("Synthetic sensor listener failure after successful feedback commit")

    runtime.listeners.add(broken_listener)
    await api.websocket_analysis_feedback(hass, connection, {
        "id": 1, "config_entry_id": "test", "action": "import", "content": json.dumps(report)})
    assert errors == []
    assert len(results) == 1 and results[0]["report"] == report
    assert runtime.analysis_feedback.report == report
    assert runtime.analysis_feedback.store.data["report"] == report
    assert runtime.entry.options == before_options and runtime.learning_hub.policy == before_policy
    assert hass.services.calls == []


def recorded(ts, *, function="space_heating"):
    return {"ts": ts, "release": VERSION,
            "panasonic": {"power_supply1_w": 1500, "power_supply2_w": 0,
                "power_supply1_valid": True, "power_supply2_valid": True,
                "power_supply1_observed_at": ts, "power_supply2_observed_at": ts,
                "power_w": 1500, "power_complete": True, "power_kind": "measured", "power_scope": "split",
                "power_observed_at": ts, "source_stale_s": 120,
                "power_activity": {"state": "active", "active": True, "complete": True, "total_w": 1500,
                    "observed_at": ts, "context_observed_at": ts, "stale_s": 120, "threshold_w": 200,
                    "evidence": "metered_power", "activity_kind": "main", "function": None,
                    "supplies": [{"number": 1, "role": "main", "valid": True, "watts": 1500, "observed_at": ts},
                                 {"number": 2, "role": "heater", "valid": True, "watts": 0, "observed_at": ts}]},
                "native_task": {"function": function, "source": "aquarea_poll", "observed_at": ts, "stale_s": 120},
                "task_context": {}, "defrost": {}, "display_tank": {}, "display_zones": [],
                "sg_status": "unknown", "sg_status_observed_at": None},
            "sg_boost": {"desired_on": False, "relay_on": False, "relay_confirmed": True,
                         "relay_observed_at": ts}}


def package(samples=()):
    return {"schema": "solarpilot.analysis", "schema_version": 2,
            "release": VERSION, "created_at": "2026-10-11T00:00:00+00:00", "requested_hours": 168,
            "export_provenance": source_export(), "coverage": {"sample_interval_s": 300, "collection_enabled": True},
            "coverage_summary": {"coverage_pct": 100}, "telemetry": {"samples": list(samples), "events": []},
            "components": {"panasonic": {}, "sg_boost": {}}, "effective_configuration": {},
            "source_metadata": {}, "system": {}}


def test_export_digest_is_canonical_and_ignores_only_its_own_hash():
    payload = review.finalize_review(package([recorded(1000)]))
    original = deepcopy(payload)
    expected = deepcopy(payload)
    expected["export_provenance"].pop("export_sha256")
    canonical = json.dumps(expected, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert payload["export_provenance"]["export_sha256"] == digest == review.export_digest(payload)
    payload["export_provenance"]["export_sha256"] = "f" * 64
    assert review.export_digest(payload) == digest
    payload["analysis_request"]["limits"].append("Andere inhoud")
    assert review.export_digest(payload) != digest
    assert review.export_digest(original) == digest
    assert review.export_digest(dict(reversed(list(original.items())))) == digest


def test_digest_and_analysis_request_bind_the_actual_pseudonymized_export():
    runtime, hass = report_context()
    hass.states.get("sensor.grid").attributes["friendly_name"] = "Fictieve privémeter"
    before_calls = list(hass.services.calls)
    payload = runtime.analysis.build(hours=168)
    assert payload["export_provenance"]["export_sha256"] == review.export_digest(payload)
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "sensor.grid" not in encoded and "Fictieve privémeter" not in encoded and "Testtoestel" not in encoded
    source = payload["configuration"]["site"]["grid_entity"]
    assert source.startswith("sensor.source_") and source in payload["entities"]
    assert payload["analysis_request"]["current"]["effective_settings"] == payload["effective_configuration"]
    assert hass.services.calls == before_calls


def test_public_proposal_id_that_resembles_an_entity_remains_stable_across_anonymized_exports():
    runtime, _hass = report_context()
    imported = advice()
    imported["recommendations"] = [{"category": "logic_update", "proposal_id": "sensor.freshness",
        "text": "Controleer de eigen klok van elke voedingsbron.", "evidence": [],
        "confidence": "medium", "limitations": []}]
    runtime.analysis_feedback.report = imported
    exported = [runtime.analysis.build(hours=168) for _ in range(2)]
    for payload in exported:
        row = payload["components"]["analysis_feedback"]["report"]["recommendations"][0]
        assert row["proposal_id"] == "sensor.freshness"
        assert row["text"] == imported["recommendations"][0]["text"]
        assert payload["export_provenance"]["export_sha256"] == review.export_digest(payload)


def test_old_partial_history_never_receives_current_task_meter_or_settings_values():
    old = {"ts": 1000, "panasonic": {"temperature_c": 39}}
    payload = package([old])
    payload["components"]["panasonic"] = {"native_task": {"function": "tapwater_heating"}, "power_supply2_w": 3000}
    payload["effective_configuration"] = {"sg_boost": {"power_supply2_role": "heater"}}
    before = deepcopy(payload)
    result = review.build_review_bundle(payload)
    row = result["history"]["samples"][0]
    assert row["release"] == "unknown" and row["record_quality"] == "legacy_partial"
    assert row["native_task"] == {} and row["power_activity"] == {}
    assert row["supplies"] == [{"number": 1}, {"number": 2}]
    assert result["history"]["settings_history"] == []
    assert result["history"]["settings_history_status"] == "missing"
    assert result["quality"]["regime_observation_counts"] == {"unknown": 1}
    assert result["quality"]["feed_quality"]["supply2"]["valid_fresh_sample_count"] == 0
    assert payload == before


def test_endpoint_intervals_are_bounded_observations_and_do_not_claim_cycles_or_energy():
    result = review.build_review_bundle(package([recorded(1000), recorded(1300), recorded(3300)]))
    assert result["quality"]["sample_count"] == 3
    assert result["quality"]["regime_observation_counts"] == {"space_heating_reported": 3}
    assert result["quality"]["endpoint_interval_seconds"] == 300
    assert result["quality"]["gap_seconds_between_samples"] == 2000
    assert result["quality"]["point_observations_are_not_cycle_counts"] is True
    intervals = result["history"]["regime_endpoint_intervals"]
    assert len(intervals) == 1 and intervals[0]["seconds"] == 300
    assert "not proof of uninterrupted physical operation" in intervals[0]["meaning"]
    assert "kwh" not in json.dumps(result["quality"]).lower()
    assert any("no COP/SCOP" in item for item in result["limits"])
    assert any("correlation does not prove" in item for item in result["limits"])


@pytest.mark.parametrize("stamp", [None, True, 800, 1006])
def test_new_snapshot_timestamp_cannot_refresh_an_invalid_native_task_stamp(stamp):
    row = recorded(1000)
    row["panasonic"]["native_task"]["observed_at"] = stamp
    result = review.build_review_bundle(package([row]))
    assert "space_heating_reported" not in result["quality"]["regime_observation_counts"]
    assert result["quality"]["regime_observation_counts"] == {"electrical_active": 1}


@pytest.mark.parametrize("field", ["conflict", "inactive"])
def test_inconsistent_native_task_flags_cannot_be_promoted_to_a_reported_heating_task(field):
    row = recorded(1000)
    row["panasonic"]["native_task"][field] = True
    result = review.build_review_bundle(package([row]))
    assert "space_heating_reported" not in result["quality"]["regime_observation_counts"]


@pytest.mark.parametrize("field", ["power_supply1_observed_at", "power_supply2_observed_at"])
def test_split_function_inference_requires_its_own_historical_feeds(field):
    row = recorded(1000, function=None)
    row["panasonic"]["native_task"] = {}
    row["panasonic"][field] = 800
    row["panasonic"]["power_activity"].update(function="tapwater_heating", evidence="metered_power_and_context")
    result = review.build_review_bundle(package([row]))
    assert "tapwater_heating_inferred" not in result["quality"]["regime_observation_counts"]
    feed = "supply1" if "1" in field else "supply2"
    assert result["quality"]["feed_quality"][feed]["valid_fresh_sample_count"] == 0


@pytest.mark.parametrize("where,key", [("root", "apply"), ("root", "code"), ("recommendation", "service"),
                                      ("recommendation", "patch"), ("source", "config_entry_id")])
def test_unknown_or_executable_fields_are_rejected_instead_of_partially_imported(where, key):
    report = advice()
    target = report if where == "root" else report["source_export"] if where == "source" else report["recommendations"][0]
    target[key] = "switch.turn_on"
    with pytest.raises(feedback.FeedbackValidationError):
        feedback.parse_feedback(json.dumps(report))


@pytest.mark.parametrize("content", ["NaN", "Infinity", "-Infinity", '[1,2]', 'null', '{"schema":"x","schema":"y"}',
                                     "[" * 65 + "0" + "]" * 65])
def test_ambiguous_nonfinite_or_deep_feedback_json_is_rejected(content):
    with pytest.raises(feedback.FeedbackValidationError):
        feedback.parse_feedback(content)


def test_utf8_byte_limit_is_applied_before_json_parsing(monkeypatch):
    calls = []
    monkeypatch.setattr(feedback.json, "loads", lambda *args, **kwargs: calls.append(True))
    content = '"' + "é" * (feedback.MAX_FEEDBACK_BYTES // 2 + 1) + '"'
    assert len(content) < feedback.MAX_FEEDBACK_BYTES
    with pytest.raises(feedback.FeedbackValidationError):
        feedback.parse_feedback(content)
    assert calls == []


def test_valid_plain_html_like_advice_is_preserved_as_data_and_detached():
    report = advice()
    report["summary"] = '<img src=x onerror="alert(1)"> & <script>malicious()</script>'
    parsed = feedback.parse_feedback(json.dumps(report))
    assert parsed == report
    parsed["recommendations"][0]["text"] = "Mutatie"
    assert report["recommendations"][0]["text"] == "Controleer de ontbrekende bron."


@pytest.mark.asyncio
async def test_same_source_can_match_only_the_entry_that_exported_it():
    first, first_hass = build()
    second, second_hass = build()
    second.entry.entry_id = "other_entry"
    first_store, second_store = feedback.AnalysisFeedbackStore(first), feedback.AnalysisFeedbackStore(second)
    calls = (list(first_hass.services.calls), list(second_hass.services.calls))
    options = (deepcopy(first.entry.options), deepcopy(second.entry.options))
    await first_store.note_export(source_export(), requested_hours=168, question_refs=[])
    content = json.dumps(advice())
    assert (await first_store.import_content(content))["association"]["state"] == "matched"
    assert (await second_store.import_content(content))["association"]["state"] == "unverified"
    assert first_hass.services.calls == calls[0] and second_hass.services.calls == calls[1]
    assert first.entry.options == options[0] and second.entry.options == options[1]


@pytest.mark.asyncio
async def test_failed_feedback_save_keeps_previous_report_and_export_ledger(monkeypatch):
    runtime, hass = build()
    store = feedback.AnalysisFeedbackStore(runtime)
    await store.note_export(source_export(), requested_hours=168, question_refs=[])
    await store.import_content(json.dumps(advice()))
    before = deepcopy(store.status())
    ledger = deepcopy(store.known_exports)
    async def fail_save(_data):
        raise OSError("Fictieve schijffout")
    monkeypatch.setattr(store.store, "async_save", fail_save)
    changed = advice()
    changed["summary"] = "Nieuw advies"
    with pytest.raises(OSError):
        await store.import_content(json.dumps(changed))
    assert store.status()["report"] == before["report"]
    assert store.known_exports == ledger
    assert hass.services.calls == []


@pytest.mark.asyncio
async def test_only_exact_exported_question_revision_is_read_only_reviewed():
    runtime, hass = build()
    store = feedback.AnalysisFeedbackStore(runtime)
    revision = "0123456789abcdef"
    runtime.learning_hub.current_findings = [{"id": "coverage_issue", "revision": revision}]
    await store.note_export(source_export(), requested_hours=168,
                            question_refs=[{"question_id": "coverage_issue", "revision": revision}])
    report = advice()
    report["question_answers"] = [{"question_id": "coverage_issue", "revision": revision,
                                   "answer": "Aanvullende actuele bronmetingen ontbreken.", "outcome": "reviewed"}]
    before_options = deepcopy(runtime.entry.options)
    await store.import_content(json.dumps(report))
    assert store.question_review("coverage_issue", revision) == report["question_answers"][0]
    assert store.question_review("coverage_issue", "fedcba9876543210") is None
    assert store.question_review("another_issue", revision) is None
    assert runtime.entry.options == before_options and hass.services.calls == []
    runtime.learning_hub.current_findings = [{"id": "coverage_issue", "revision": "fedcba9876543210"}]
    assert store.question_review("coverage_issue", revision) is None, "A new finding revision is pending again"
    await store.remove()
    assert store.question_review("coverage_issue", revision) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("hours,revision", [(24, "0123456789abcdef"), (168, "fedcba9876543210")])
async def test_question_review_rejects_short_exports_or_a_revision_not_in_the_export_without_partial_save(hours, revision):
    runtime, hass = build()
    store = feedback.AnalysisFeedbackStore(runtime)
    await store.note_export(source_export(), requested_hours=hours,
                            question_refs=[{"question_id": "coverage_issue", "revision": "0123456789abcdef"}])
    report = advice()
    report["question_answers"] = [{"question_id": "coverage_issue", "revision": revision,
                                   "answer": "Genoemde meetkwaliteit bekeken.", "outcome": "reviewed"}]
    ledger = deepcopy(store.known_exports)
    with pytest.raises(feedback.FeedbackValidationError):
        await store.import_content(json.dumps(report))
    assert store.status()["report"] is None
    assert store.known_exports == ledger and hass.services.calls == []


@pytest.mark.asyncio
async def test_foreign_question_answers_remain_informational_and_do_not_review_local_findings():
    runtime, hass = build()
    store = feedback.AnalysisFeedbackStore(runtime)
    revision = "0123456789abcdef"
    await store.note_export(source_export(), requested_hours=168,
                            question_refs=[{"question_id": "coverage_issue", "revision": revision}])
    report = advice(source_export("b"))
    report["question_answers"] = [{"question_id": "coverage_issue", "revision": revision,
                                   "answer": "Dit antwoord komt uit een andere export.", "outcome": "reviewed"}]
    result = await store.import_content(json.dumps(report))
    assert result["association"]["state"] == "unverified"
    assert result["report"]["question_answers"] == report["question_answers"]
    assert store.question_review("coverage_issue", revision) is None
    assert hass.services.calls == []


def test_feedback_renderer_escapes_all_uploaded_text_and_has_no_apply_controls():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the shipped feedback renderer")
    attack = '<img src=x onerror="alert(1)"><script>malicious()</script> & <svg onload="attack()">'
    report = advice()
    report["summary"] = attack
    report["limitations"] = [attack]
    report["recommendations"][0].update(text=attack, evidence=[attack], limitations=[attack])
    report["question_answers"] = [{"question_id": attack, "revision": "0123456789abcdef", "answer": attack, "outcome": "reviewed"}]
    status = {"report": report, "association": {"state": "unverified", "reason": attack}}
    card = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/frontend/solar-pilot-card.js"
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},input};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
process.stdout.write(vm.runInContext('SolarPilotCard.prototype._analysisFeedbackHtml(input)',sandbox));
"""
    result = subprocess.run([node, "-e", script, str(card)], input=json.dumps(status), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    root = Markup(result.stdout).root
    assert attack in root.text(), "The report remains legible as plain text"
    assert "&lt;img" in result.stdout and "&lt;script" in result.stdout and "&lt;svg" in result.stdout
    assert not any(item.tag in {"img", "script", "svg", "iframe", "button", "input", "a"}
                   or "data-action" in item.attributes for item in root.walk())
    assert "wijzigt geen instellingen" in root.text()
