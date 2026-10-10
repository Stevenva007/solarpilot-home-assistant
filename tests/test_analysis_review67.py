"""Final export, answer template and recorded review evidence contracts."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.metadata
import json
import sys
import threading
from types import ModuleType, SimpleNamespace as NS

import pytest

from custom_components.solar_pilot import analysis_export as ae
from custom_components.solar_pilot import analysis_review as review
from custom_components.solar_pilot.const import VERSION
from homeassistant.helpers import entity_registry as er
from test_analysis_export import report_context
from test_runtime import build


REVISION = "0123456789abcdef"


def questions(revision=REVISION):
    return [{"id": question_id, "revision": revision, "title": "Fictieve beoordelingsvraag",
             "message": "Alleen beoordeling; geen instelling toepassen.", "severity": "choice",
             "choices": [{"id": value, "label": "Fictieve keuze"}
                         for value in ("adaptation", "pv_source", "revision")]}
            for question_id in ("adaptation", "pv_source")]


def add_questions(raw, revision=REVISION):
    raw["components"]["learning_evidence_and_questions"] = {
        "questions": questions(revision), "quality": {"covered_days": 2},
        "sampling": {"sample_count": 3}}
    return raw


def package(samples=(), events=()):
    return {"schema": "solarpilot.analysis", "schema_version": 2, "release": VERSION,
            "requested_hours": 168, "telemetry": {"samples": list(samples), "events": list(events)},
            "coverage": {"sample_interval_s": 300, "collection_enabled": True},
            "coverage_summary": {}, "components": {"panasonic": {}, "sg_boost": {}},
            "effective_configuration": {}, "source_metadata": {}, "system": {}}


def electrical_sample(ts=1000):
    return {"ts": ts, "release": VERSION, "panasonic": {
        "power_supply1_w": 1500, "power_supply2_w": 0,
        "power_supply1_valid": True, "power_supply2_valid": True,
        "power_supply1_observed_at": ts, "power_supply2_observed_at": ts,
        "power_w": 1500, "power_complete": True, "power_kind": "measured",
        "power_scope": "split", "power_observed_at": ts, "source_stale_s": 120,
        "native_task": {}, "task_context": {}, "defrost": {},
        "display_tank": {}, "display_zones": [], "sg_status": "unknown", "sg_status_observed_at": None,
        "power_activity": {"state": "active", "active": True, "complete": True, "total_w": 1500,
            "evidence": "metered_power_and_context", "function": "tapwater_heating",
            "function_kind": "tank_route", "observed_at": ts, "context_observed_at": ts,
            "stale_s": 120, "threshold_w": 200,
            "supplies": [{"number": 1, "role": "main", "state": "active", "valid": True},
                         {"number": 2, "role": "heater", "state": "off", "valid": True}]}},
        "sg_boost": {"desired_on": False, "relay_on": False,
                     "relay_confirmed": True, "relay_observed_at": ts}}


@pytest.mark.parametrize("include_names", [False, True])
def test_final_hash_covers_the_actual_export_and_excludes_no_other_fields(include_names):
    runtime, hass = report_context()
    hass.states.get("sensor.grid").attributes["friendly_name"] = "Fictieve privémeter"
    raw = add_questions(runtime.analysis.prepare(hours=168))
    untouched = deepcopy(raw)
    report = ae.AnalysisRecorder.finalize(raw, include_names)
    canonical = deepcopy(report)
    canonical["export_provenance"].pop("export_sha256")
    digest = hashlib.sha256(json.dumps(canonical, ensure_ascii=False, allow_nan=False,
        sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    assert report["export_provenance"]["export_sha256"] == digest == review.export_digest(report)
    assert report["analysis_request"]["current"]["effective_settings"] == report["effective_configuration"]
    assert "feedback_template" not in report and "feedback_template" not in report["analysis_request"]
    assert raw == untouched
    json.dumps(report, allow_nan=False)
    if not include_names:
        assert "Fictieve privémeter" not in json.dumps(report, ensure_ascii=False)
        assert "sensor.grid" not in json.dumps(report)
    changed = deepcopy(report)
    changed["analysis_request"]["quality"]["sample_count"] += 1
    assert review.export_digest(changed) != digest


def test_feedback_template_is_pure_detached_and_binds_the_final_hash():
    runtime, _hass = report_context()
    report = ae.AnalysisRecorder.finalize(add_questions(runtime.analysis.prepare(hours=168)))
    before = deepcopy(report)
    template = review.feedback_template(report)
    assert template["schema"] == "solarpilot.analysis_feedback" and template["schema_version"] == 1
    assert template["source_export"] == {key: report["export_provenance"][key]
        for key in ("export_id", "export_sha256", "release", "created_at")}
    assert template["source_export"]["export_sha256"] == review.export_digest(report)
    assert report == before
    assert [(item["question_id"], item["revision"], item["outcome"])
            for item in template["question_answers"]] == [
                ("adaptation", REVISION, "needs_more_data"),
                ("pv_source", REVISION, "needs_more_data")]
    assert template["recommendations"] == []
    json.dumps(template, allow_nan=False)
    template["source_export"]["export_sha256"] = "0" * 64
    template["question_answers"][0]["revision"] = "edited"
    assert report == before
    assert review.feedback_template(report)["source_export"]["export_sha256"] == review.export_digest(report)


def test_feedback_template_without_questions_invents_no_answers_or_recommendations():
    runtime, _hass = build()
    raw = runtime.analysis.prepare(hours=168)
    raw["components"]["learning_evidence_and_questions"] = {"questions": []}
    report = ae.AnalysisRecorder.finalize(raw)
    template = review.feedback_template(report)
    assert template["question_answers"] == [] and template["recommendations"] == []
    assert template["source_export"]["export_sha256"] == report["export_provenance"]["export_sha256"]


@pytest.mark.parametrize("consumer_id", ["adaptation", "pv_source", "revision", REVISION])
def test_question_choice_and_revision_ids_survive_consumer_alias_collisions(consumer_id):
    runtime, _hass = report_context()
    raw = json.loads(json.dumps(runtime.analysis.prepare(hours=168)).replace('"a"', json.dumps(consumer_id)))
    add_questions(raw)
    report = ae.AnalysisRecorder.finalize(raw)
    alias = next(iter(report["effective_configuration"]["devices"]))
    assert alias.startswith("consumer_") and alias != consumer_id
    for exported_questions in (report["components"]["learning_evidence_and_questions"]["questions"],
                               report["analysis_request"]["pending_questions"]):
        assert [item["id"] for item in exported_questions] == ["adaptation", "pv_source"]
        assert all(item["revision"] == REVISION for item in exported_questions)
        assert all([choice["id"] for choice in item["choices"]] == ["adaptation", "pv_source", "revision"]
                   for item in exported_questions)
    answers = review.feedback_template(report)["question_answers"]
    assert [item["question_id"] for item in answers] == ["adaptation", "pv_source"]
    assert all(item["revision"] == REVISION and item["outcome"] == "needs_more_data" for item in answers)
    assert report["export_provenance"]["export_sha256"] == review.export_digest(report)


def test_legacy_missing_fields_and_settings_are_not_populated_from_current_component():
    old = {"ts": 1000, "panasonic": {"temperature_c": 39, "power_supply1_w": 0},
           "sg_boost": {"desired_on": False}}
    raw = package([old])
    raw["components"]["panasonic"] = deepcopy(electrical_sample()["panasonic"])
    raw["components"]["sg_boost"] = {"desired_on": True, "relay_on": True, "relay_observed_at": 2000}
    raw["effective_configuration"] = {"sg_boost": {"threshold_w": 3000, "power_supply2_role": "heater"}}
    before = deepcopy(raw)
    bundle = review.build_review_bundle(raw)
    row = bundle["history"]["samples"][0]
    assert row["release"] == "unknown" and row["record_quality"] == "legacy_partial"
    assert row["supplies"] == [{"number": 1, "watts": 0}, {"number": 2}]
    assert row["native_task"] == row["task_context"] == row["power_activity"] == row["defrost"] == {}
    assert row["legacy_tank"] == {"temperature_c": 39}
    assert row["sg"]["request_contact"] == {"desired_on": False}
    assert row["sg"]["received"] == {}
    assert "panasonic.native_task" in row["missing_fields"]
    assert bundle["history"]["settings_history_status"] == "missing"
    assert bundle["quality"]["regime_observation_counts"] == {"unknown": 1}
    assert raw == before


@pytest.mark.parametrize("feed", [1, 2])
@pytest.mark.parametrize("bad", ["stale", "future", "missing_stamp", "invalid", "negative", "bool"])
def test_each_feed_has_to_be_fresh_valid_and_numeric_in_its_own_record(feed, bad):
    row = electrical_sample()
    p = row["panasonic"]
    if bad == "stale":
        p[f"power_supply{feed}_observed_at"] = 879
    elif bad == "future":
        p[f"power_supply{feed}_observed_at"] = 1006
    elif bad == "missing_stamp":
        p.pop(f"power_supply{feed}_observed_at")
    elif bad == "invalid":
        p[f"power_supply{feed}_valid"] = False
    else:
        p[f"power_supply{feed}_w"] = -1 if bad == "negative" else True
    bundle = review.build_review_bundle(package([row]))
    quality = bundle["quality"]["feed_quality"]
    assert quality[f"supply{feed}"]["valid_fresh_sample_count"] == 0
    assert quality[f"supply{feed}"]["missing_or_unreliable_count"] == 1
    assert quality[f"supply{3-feed}"]["valid_fresh_sample_count"] == 1
    assert "tapwater_heating_inferred" not in bundle["quality"]["regime_observation_counts"]


def test_true_zero_feed_is_preserved_and_electric_context_does_not_create_thermal_metrics():
    raw = package([electrical_sample(1000), electrical_sample(1300)])
    bundle = review.build_review_bundle(raw)
    assert bundle["history"]["samples"][0]["supplies"][1]["watts"] == 0
    assert bundle["quality"]["feed_quality"]["supply2"]["valid_fresh_sample_count"] == 2
    assert any("no COP/SCOP" in item for item in bundle["limits"])
    assert any("correlation does not prove" in item for item in bundle["limits"])
    assert bundle["quality"]["point_observations_are_not_cycle_counts"] is True
    for metric in ("cop", "scop", "heat_kwh", "thermal_energy_kwh", "heat_output_w", "cycle_count"):
        assert metric not in bundle["quality"]
        assert all(metric not in interval for interval in bundle["history"]["regime_endpoint_intervals"])


def test_settings_history_contains_only_recorded_snapshots_and_retains_event_release():
    past_settings = {"sg_boost": {"threshold_w": 2500, "expected_power_w": 3000}}
    events = [{"ts": 1000, "kind": "settings_snapshot", "release": "1.0.0-beta.66",
               "data": {"effective_settings": past_settings, "baseline": True}},
              {"ts": 1500, "kind": "settings_change", "data": {"effective_settings": {"sg_boost": {"threshold_w": 2750}}}},
              {"ts": 1600, "kind": "decision_change", "data": {"mode": "observe"}}]
    raw = package(events=events)
    raw["effective_configuration"] = {"sg_boost": {"threshold_w": 4000}}
    before = deepcopy(raw)
    bundle = review.build_review_bundle(raw)
    assert bundle["history"]["settings_history"] == events[:2]
    assert bundle["history"]["settings_history_status"] == "recorded"
    assert bundle["history"]["decision_timeline"] == events[2:]
    assert raw == before


def test_recorder_baseline_and_meaningful_changes_exclude_receipt_clocks_and_continuous_measurements(monkeypatch):
    runtime, hass = build()
    clock = [1000.0]
    monkeypatch.setattr(ae, "time", NS(time=lambda: clock[0], monotonic=lambda: clock[0]))
    sample = electrical_sample()
    p, sg = sample["panasonic"], sample["sg_boost"]
    p["display_tank"] = {"mode": "idle", "action": None, "target_c": 50, "temperature_c": 49,
                         "available": True, "observed_at": clock[0]}
    monkeypatch.setattr(runtime.panasonic, "overview", lambda: deepcopy(p))
    monkeypatch.setattr(runtime.sg_boost, "overview", lambda: deepcopy(sg))
    before_calls = list(hass.services.calls)
    runtime.analysis.capture(1.0)
    baseline = [row for row in runtime.analysis.events if row["kind"] == "settings_snapshot"]
    changes = [row for row in runtime.analysis.events if row["kind"] == "heatpump_change"]
    assert len(baseline) == len(changes) == 1
    assert baseline[0]["data"]["baseline"] is True
    assert baseline[0]["data"]["not_a_retrospective_configuration"] is True
    original_settings = deepcopy(baseline[0]["data"]["effective_settings"])
    clock[0] += 5
    p["power_w"] = 1600
    p["power_supply1_w"] = 1600
    p["power_supply1_observed_at"] = clock[0]
    p["power_activity"]["observed_at"] = clock[0]
    p["power_activity"]["total_w"] = 1600
    p["display_tank"]["temperature_c"] = 49.1
    p["display_tank"]["observed_at"] = clock[0]
    sg["relay_observed_at"] = clock[0]
    runtime.analysis.capture(1.0)
    assert sum(row["kind"] == "heatpump_change" for row in runtime.analysis.events) == 1
    assert sum(row["kind"] == "settings_snapshot" for row in runtime.analysis.events) == 1
    assert not any(row["kind"] == "settings_change" for row in runtime.analysis.events)
    clock[0] += 5
    p["display_tank"]["target_c"] = 51
    runtime.analysis.capture(1.0)
    assert sum(row["kind"] == "heatpump_change" for row in runtime.analysis.events) == 2
    runtime.sg_boost.config["threshold_w"] = 2750
    clock[0] += 5
    runtime.analysis.capture(1.0)
    settings_changes = [row for row in runtime.analysis.events if row["kind"] == "settings_change"]
    assert len(settings_changes) == 1 and settings_changes[0]["data"]["baseline"] is False
    assert settings_changes[0]["data"]["effective_settings"]["sg_boost"]["threshold_w"] == 2750
    assert baseline[0]["data"]["effective_settings"] == original_settings
    assert hass.services.calls == before_calls


@pytest.mark.parametrize("distribution", ["aioaquarea-ng", "aioaquarea"])
def test_installed_provider_metadata_uses_fixed_loaded_manifest_and_local_distribution(monkeypatch, tmp_path, distribution):
    provider = ModuleType("custom_components.aquarea")
    provider.__file__ = str(tmp_path / "__init__.py")
    (tmp_path / "manifest.json").write_text(json.dumps({"domain": "aquarea", "version": "1.5.2"}), encoding="utf-8")
    monkeypatch.setitem(sys.modules, provider.__name__, provider)
    calls = []

    def version(name):
        calls.append(name)
        if name == distribution:
            return "2.3.4"
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", version)
    result = ae.installed_aquarea_metadata()
    assert result["integration_loaded"] is True and result["integration_domain"] == "aquarea"
    assert result["integration_version"] == "1.5.2"
    assert result["library_distribution"] == distribution and result["library_version"] == "2.3.4"
    assert calls == (["aioaquarea-ng"] if distribution == "aioaquarea-ng" else ["aioaquarea-ng", "aioaquarea"])
    assert str(tmp_path) not in json.dumps(result)
    assert "not historical" in result["scope"]


@pytest.mark.parametrize("manifest", [None, "invalid json", "[]", '{"version": 12}'])
def test_missing_or_invalid_local_manifest_never_guesses_provider_version(monkeypatch, tmp_path, manifest):
    provider = ModuleType("custom_components.aquarea")
    provider.__file__ = str(tmp_path / "__init__.py")
    monkeypatch.setitem(sys.modules, provider.__name__, provider)
    if manifest is not None:
        (tmp_path / "manifest.json").write_text(manifest, encoding="utf-8")
    monkeypatch.setattr(importlib.metadata, "version", lambda name: (_ for _ in ()).throw(
        importlib.metadata.PackageNotFoundError(name)))
    result = ae.installed_aquarea_metadata()
    assert result["integration_version"] is None
    assert result["library_distribution"] is None and result["library_version"] is None


def test_absent_native_provider_and_library_are_explicitly_unknown(monkeypatch):
    monkeypatch.delitem(sys.modules, "custom_components.aquarea", raising=False)
    monkeypatch.setattr(importlib.metadata, "version", lambda name: (_ for _ in ()).throw(
        importlib.metadata.PackageNotFoundError(name)))
    result = ae.installed_aquarea_metadata()
    assert result["integration_loaded"] is False
    assert result["integration_version"] is result["library_distribution"] is result["library_version"] is None


@pytest.mark.parametrize("requirement,distribution,version", [
    ("aioaquarea-ng>=1.3.1", "aioaquarea-ng", "1.3.1"),
    ("aioaquarea==0.7.6", "aioaquarea", "0.7.6"),
])
def test_installed_manifest_selects_the_exact_upstream_distribution_even_when_both_exist(
        monkeypatch, tmp_path, requirement, distribution, version):
    provider = ModuleType("custom_components.aquarea")
    provider.__file__ = str(tmp_path / "__init__.py")
    monkeypatch.setitem(sys.modules, provider.__name__, provider)
    (tmp_path / "manifest.json").write_text(json.dumps({"domain": "aquarea", "version": "1.5.2",
        "requirements": ["unrelated-package==9", requirement]}), encoding="utf-8")
    versions = {"aioaquarea-ng": "1.3.1", "aioaquarea": "0.7.6"}
    calls = []
    monkeypatch.setattr(importlib.metadata, "version", lambda name: calls.append(name) or versions[name])
    result = ae.installed_aquarea_metadata()
    assert calls == [distribution]
    assert result["library_distribution"] == distribution and result["library_version"] == version


def test_missing_declared_native_library_does_not_substitute_another_installed_library(monkeypatch, tmp_path):
    provider = ModuleType("custom_components.aquarea")
    provider.__file__ = str(tmp_path / "__init__.py")
    monkeypatch.setitem(sys.modules, provider.__name__, provider)
    (tmp_path / "manifest.json").write_text(json.dumps({"requirements": ["aioaquarea-ng>=1.3.1"]}), encoding="utf-8")
    calls = []

    def version(name):
        calls.append(name)
        if name == "aioaquarea":
            return "0.7.6"
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", version)
    result = ae.installed_aquarea_metadata()
    assert calls == ["aioaquarea-ng"]
    assert result["library_distribution"] is None and result["library_version"] is None


@pytest.mark.parametrize("question_id,valid", [
    (".prefix", False), (":prefix", False), ("-prefix", False),
    ("a" * 160, True), ("a" * 161, False), ("sensor.freshness", True), ("_finding:revision", True),
])
def test_feedback_template_question_ids_follow_the_import_contract(question_id, valid):
    from custom_components.solar_pilot.feedback_store import parse_feedback
    runtime, _hass = build()
    raw = runtime.analysis.prepare(hours=168)
    raw["components"]["learning_evidence_and_questions"] = {"questions": [
        {"id": question_id, "revision": REVISION}]}
    report = ae.AnalysisRecorder.finalize(raw)
    template = review.feedback_template(report)
    assert bool(template["question_answers"]) is valid
    assert parse_feedback(json.dumps(template)) == template


def test_trusted_implementation_protocol_fields_survive_household_alias_collisions():
    digest = "a" * 64
    original = {"installed_release": VERSION, "introduced_release": VERSION, "current_release": VERSION,
                "proposal_sha256": digest, "status": "pending", "proposal_id": "sensor.freshness",
                "question_id": "sensor.freshness", "evidence": ["sensor.freshness"],
                "text": f"pending {VERSION}"}
    result = ae.pseudonymize(original, {VERSION: "consumer_version", digest: "consumer_digest",
        "pending": "consumer_pending", "sensor.freshness": "sensor.source_public_collision"},
        {VERSION: "Verbruiker 1"})
    for field in ("installed_release", "introduced_release", "current_release", "proposal_sha256",
                  "status", "proposal_id", "question_id"):
        assert result[field] == original[field]
    assert result["evidence"] == ["sensor.source_public_collision"]
    assert result["text"] == "consumer_pending Verbruiker 1"


def test_status_prose_and_nested_status_details_redact_household_names_but_keep_protocol_codes():
    payload = {"status": "PrivateOldAppliance: direct toepassen zonder herladen",
               "details": {"status": {"message": "PrivateOldAppliance blijft wachten."}},
               "implementation": {"status": "pending"}, "cycle": {"status": "completed"}}
    result = ae.pseudonymize(payload, {"pending": "consumer_wait", "completed": "consumer_done"},
                            {"PrivateOldAppliance": "Verbruiker 1"})
    assert "PrivateOldAppliance" not in json.dumps(result)
    assert result["status"] == "Verbruiker 1: direct toepassen zonder herladen"
    assert result["details"]["status"]["message"] == "Verbruiker 1 blijft wachten."
    assert result["implementation"]["status"] == "pending" and result["cycle"]["status"] == "completed"


def test_prepare_does_not_read_package_files_and_finalize_reads_metadata_in_worker(monkeypatch):
    runtime, _hass = report_context()
    main_thread = threading.get_ident()
    calls = []
    metadata = {"integration_domain": "aquarea", "integration_version": "1.5.2",
                "library_distribution": "aioaquarea-ng", "library_version": "2.3.4"}

    def installed_metadata():
        calls.append(threading.get_ident())
        return deepcopy(metadata)

    monkeypatch.setattr(ae, "installed_aquarea_metadata", installed_metadata)
    raw = runtime.analysis.prepare(hours=168)
    assert calls == [] and "aquarea" not in raw["system"]
    with ThreadPoolExecutor(max_workers=1) as executor:
        report = executor.submit(ae.AnalysisRecorder.finalize, raw, False).result()
    assert len(calls) == 1 and calls[0] != main_thread
    assert report["system"]["aquarea"] == metadata
    assert report["analysis_request"]["current"]["installed_native_provider"] == metadata
    assert report["export_provenance"]["export_sha256"] == review.export_digest(report)


def test_source_cap_prioritizes_real_grid_feeds_and_exact_native_siblings(monkeypatch):
    runtime, _hass = build(settings={"grid_entity": "sensor.zz_grid", "pv_entity": "sensor.zz_pv"})
    feeds = {"power_supply1_entity": "sensor.zz_feed_1", "power_supply2_entity": "sensor.zz_feed_2"}
    runtime.entry.options["sg_boost"] = dict(feeds)
    runtime.panasonic.settings.update(feeds)
    bulk = [f"sensor.aa_extra_{number:03d}" for number in range(300)]
    runtime.entry.options["analysis"] = {"extra_entities": bulk}
    native = {"tank_entity": "water_heater.zz_native_tank", "zone_entities": ["climate.zz_native_zone"],
              "direction_entity": "sensor.zz_native_direction", "defrost_entity": "binary_sensor.zz_native_defrost"}
    monkeypatch.setattr(runtime.panasonic.native_program, "display_sources", lambda anchors=(): deepcopy(native))
    related = [NS(entity_id=f"sensor.related_{number:03d}", disabled_by=None) for number in range(300)]
    monkeypatch.setattr(er, "async_get", lambda _hass: NS(async_get=lambda eid: NS(device_id="fictitious_device")))
    monkeypatch.setattr(er, "async_entries_for_device", lambda registry, device_id: related, raising=False)
    before = deepcopy(runtime.entry.options)
    refs = runtime.analysis.refs()
    priority = {"sensor.zz_grid", "sensor.zz_pv", *feeds.values()}
    sibling_refs = ae.entity_refs(native)
    assert len(refs) == len(set(refs)) == 250
    assert priority | sibling_refs <= set(refs)
    assert max(refs.index(eid) for eid in priority) < min(refs.index(eid) for eid in sibling_refs)
    assert max(refs.index(eid) for eid in sibling_refs) < refs.index(bulk[0])
    expected_candidates = len(ae.entity_refs({"data": runtime.entry.data, "options": runtime.entry.options})
                              | sibling_refs | {row.entity_id for row in related})
    assert runtime.analysis.source_count == expected_candidates > 250
    report = runtime.analysis.prepare(hours=168)
    assert report["coverage"]["selected_entities"] == 250
    assert report["coverage"]["source_candidates"] == expected_candidates
    assert report["coverage"]["sources_omitted_by_cap"] == expected_candidates - 250
    assert runtime.entry.options == before


def test_five_second_native_discrete_changes_record_actions_and_targets_but_not_temperature_or_clocks(monkeypatch):
    runtime, hass = build()
    clock = [1000.0]
    monkeypatch.setattr(ae, "time", NS(time=lambda: clock[0], monotonic=lambda: clock[0]))
    eid = "climate.fictitious_native_zone"
    native = {"zone_entities": [eid]}
    monkeypatch.setattr(runtime.panasonic.native_program, "display_sources", lambda anchors=(): deepcopy(native))
    monkeypatch.setattr(runtime.panasonic, "overview", lambda: {"display_sources": deepcopy(native), "display_zones": []})

    def capture(*, action="idle", target=21, temperature=20):
        hass.states.set(eid, "heat", {"hvac_action": action, "temperature": target,
                                     "current_temperature": temperature, "temperature_unit": "°C"})
        runtime.analysis.capture(1)
        return [row for row in runtime.analysis.changes if row.get("capture_kind") == "native_discrete_change"]

    assert len(capture()) == 1
    clock[0] += 5
    assert len(capture(temperature=20.1)) == 1
    clock[0] += 5
    actions = capture(action="heating", temperature=20.2)
    assert len(actions) == 2 and actions[-1]["attributes"]["hvac_action"] == "heating"
    clock[0] += 5
    targets = capture(action="heating", target=22, temperature=20.3)
    assert len(targets) == 3 and targets[-1]["attributes"]["temperature"] == 22
    assert targets[-1]["ts"] == 1015 and targets[-1]["source_observed_at"]
    assert len(runtime.analysis.samples) == 1
    assert hass.services.calls == []


def test_prior_feedback_prose_and_evidence_are_private_while_source_and_question_refs_are_exact():
    runtime, _hass = report_context()
    runtime.configs["a"]["name"] = "Fictieve privékamer"
    source = {"export_id": "export_" + "a" * 32, "export_sha256": "b" * 64,
              "release": VERSION, "created_at": "2026-10-11T00:00:00Z"}
    answer = {"question_id": "adaptation", "revision": REVISION,
              "answer": "Fictieve privékamer vraagt aanvullende metingen.", "outcome": "needs_more_data"}
    feedback = {"schema": "solarpilot.analysis_feedback", "schema_version": 1,
        "source_export": deepcopy(source), "analyzed_at": "2026-10-11T01:00:00Z",
        "summary": "Fictieve privékamer heeft een deelmeting.",
        "recommendations": [{"category": "observation", "text": "Bekijk Fictieve privékamer.",
            "evidence": ["Fictieve privékamer gebruikt sensor.grid.", "adaptation bleef wachten."],
            "confidence": "low", "limitations": ["Fictieve privékamer heeft geen thermische meting."]}],
        "question_answers": [answer], "limitations": ["Geen bewezen SG-effect."]}
    runtime.analysis_feedback = NS(status=lambda: {"report": deepcopy(feedback),
        "association": {"source_export": deepcopy(source)}, "question_review": [deepcopy(answer)]})
    raw = json.loads(json.dumps(runtime.analysis.prepare(hours=168)).replace('"a"', '"adaptation"'))
    report = ae.AnalysisRecorder.finalize(raw)
    prior = report["components"]["analysis_feedback"]
    assert prior["report"]["source_export"] == prior["association"]["source_export"] == source
    assert prior["report"]["question_answers"][0]["question_id"] == "adaptation"
    assert prior["report"]["question_answers"][0]["revision"] == REVISION
    assert prior["question_review"][0]["question_id"] == "adaptation"
    assert prior["question_review"][0]["revision"] == REVISION
    encoded = json.dumps(prior, ensure_ascii=False)
    assert "Fictieve privékamer" not in encoded and "sensor.grid" not in encoded
    alias = next(iter(report["effective_configuration"]["devices"]))
    assert alias in prior["report"]["recommendations"][0]["evidence"][1]
    assert report["export_provenance"]["export_sha256"] == review.export_digest(report)


@pytest.mark.parametrize("invalid_field", ["grid_w", "pv_w"])
def test_boolean_electrical_values_do_not_count_as_usable_coverage(monkeypatch, invalid_field):
    runtime, _hass = build(settings={"pv_entity": "sensor.pv"})
    monkeypatch.setattr(ae, "time", NS(time=lambda: 1400, monotonic=lambda: 1400))
    for stamp in (1000, 1300):
        row = {"ts": stamp, "grid_w": -2500, "pv_w": 3500}
        row[invalid_field] = True
        runtime.analysis.samples.append(row)
    report = runtime.analysis.prepare(hours=1)
    quality = report["coverage_summary"]
    assert quality["covered_hours"] == 0 and quality["coverage_pct"] == 0
    assert quality["first_usable_sample"] is quality["last_usable_sample"] is None
    assert quality["unusable_sample_interval_hours"] > 0


def test_malformed_nullable_historical_blocks_remain_unknown_instead_of_crashing_or_backfilling():
    raw = package([{"ts": 1000, "panasonic": {"power_activity": None, "display_zones": None,
        "display_tank": None, "native_task": None, "task_context": None, "defrost": None},
        "sg_boost": None}])
    raw["components"]["panasonic"] = deepcopy(electrical_sample()["panasonic"])
    before = deepcopy(raw)
    bundle = review.build_review_bundle(raw)
    row = bundle["history"]["samples"][0]
    assert row["power_activity"] == row["native_task"] == row["task_context"] == row["defrost"] == row["tank"] == {}
    assert row["zones"] == []
    assert row["supplies"] == [{"number": 1}, {"number": 2}]
    assert bundle["quality"]["regime_observation_counts"] == {"unknown": 1}
    assert raw == before
