"""Fictitious source evidence cannot alter meters, sessions or control rights."""
from copy import deepcopy
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace
import json
import sys
import time

import pytest

from custom_components.solar_pilot.investigation import LocalInvestigation, MAX_BALANCE_OBSERVATIONS
from custom_components.solar_pilot.source_diagnostics import (
    MAX_COMPARISON_SOURCES, runtime_solar_balance_proof, solar_balance_proof,
    source_report, wallbox_source_dossier,
)
from test_runtime import build


@pytest.fixture
def clock(monkeypatch):
    now = [datetime.now(timezone.utc).timestamp()]
    monkeypatch.setattr(time, "time", lambda: now[0])
    return now


def report(hass, entity, value, stamp, unit="W", **attrs):
    hass.states.set(entity, value, {"unit_of_measurement": unit, **attrs})
    obj = hass.states.get(entity)
    obj.last_reported = obj.last_updated = datetime.fromtimestamp(stamp, timezone.utc)
    return obj


def prepare_wallbox(runtime, hass, now):
    runtime.wallbox_settings.update(enabled=True, status_entity="sensor.ev_status",
                                   mode_entity="sensor.ev_mode", power_entity="sensor.ev_power",
                                   session_mode_entity="sensor.ev_session")
    for entity, value in (("sensor.ev_status", "Ready"), ("sensor.ev_mode", "full_solar"),
                          ("sensor.ev_session", "Laden gestopt"), ("sensor.ev_power", 0)):
        report(hass, entity, value, now)


def row(overview, topic):
    return next(item for item in overview["items"] if item["id"] == topic)


def test_stale_template_has_fresh_native_dossier_without_session_reassessment(clock):
    runtime, hass = build()
    prepare_wallbox(runtime, hass, clock[0])
    report(hass, "sensor.ev_session", "Laden gestopt", clock[0] - 19000)
    before = deepcopy(runtime.wallbox_settings)
    reading = runtime._wallbox_reading()
    result = row(runtime.learning_hub.investigation.refresh(clock[0]), "wallbox_source")
    dossier = result["metrics"]["source_dossier"]
    assert dossier["session"]["issue"] == "stale"
    assert dossier["session"]["age_s"] == 19000
    assert all(source["fresh"] for source in dossier["known_sources"])
    assert dossier["known_sources"][-1]["watts"] == 0
    assert dossier["dependency_relation"] == "unknown"
    assert dossier["template_formula"] == dossier["template_triggers"] == "unknown"
    assert reading.session_confirmed is False and reading.mode == "unknown"
    assert runtime._wallbox_reading() == reading
    assert runtime.wallbox_settings == before and not hass.services.calls
    assert "sensor.ev" not in json.dumps(dossier)


@pytest.mark.parametrize("role", ["session", "status", "mode", "power"])
def test_loss_of_each_selected_wallbox_source_is_explicit(clock, role):
    runtime, hass = build()
    prepare_wallbox(runtime, hass, clock[0])
    entity = {"session": "sensor.ev_session", "status": "sensor.ev_status", "mode": "sensor.ev_mode", "power": "sensor.ev_power"}[role]
    report(hass, entity, "unavailable", clock[0])
    dossier = wallbox_source_dossier(runtime, clock[0])
    selected = next(source for source in [dossier["session"], *dossier["known_sources"]] if source["role"] == role)
    assert selected["issue"] == "unavailable" and selected["usable"] is False
    assert dossier["reassessed_session"] is False and not hass.services.calls


@pytest.mark.parametrize("state", ["Zonne-auto · laden", "Manueel laden", "Laden gestopt"])
def test_dossier_does_not_change_solar_manual_or_stop_session(clock, state):
    runtime, hass = build()
    prepare_wallbox(runtime, hass, clock[0])
    report(hass, "sensor.ev_session", state, clock[0])
    report(hass, "sensor.ev_status", "Charging", clock[0])
    report(hass, "sensor.ev_power", 1500, clock[0])
    reading = runtime._wallbox_reading()
    wallbox_source_dossier(runtime, clock[0])
    assert runtime._wallbox_reading() == reading
    assert not hass.services.calls


def test_original_report_fallback_never_uses_capture_or_changed(clock):
    runtime, hass = build()
    obj = report(hass, "sensor.source", 50, clock[0] - 80)
    obj.last_changed = datetime.fromtimestamp(clock[0], timezone.utc)
    first = source_report(runtime, "sensor.source", "pv", clock[0], 120, power=True)
    assert first["reported_wall"] == clock[0] - 80 and first["report_time_basis"] == "last_reported"
    obj.last_reported = None
    assert source_report(runtime, "sensor.source", "pv", clock[0], 120)["report_time_basis"] == "last_updated"
    obj.last_updated = None
    final = source_report(runtime, "sensor.source", "pv", clock[0], 120)
    assert final["reported_wall"] is None and final["issue"] == "report_time_unknown"


def proof(runtime, hass, now, grid=-6000, pv=2500, grid_age=0, pv_age=0):
    runtime.settings["pv_entity"] = "sensor.pv"
    report(hass, "sensor.grid", grid, now - grid_age)
    report(hass, "sensor.pv", pv, now - pv_age)
    return runtime_solar_balance_proof(runtime, now)


def test_fresh_but_skewed_grid_pv_is_not_coherent_or_a_hardware_fault(clock):
    runtime, hass = build()
    result = proof(runtime, hass, clock[0], grid_age=2, pv_age=15)
    assert result["status"] == "reports_not_aligned"
    assert result["export_excess_w"] == 3500 and result["source_skew_s"] == 13
    assert result["time_aligned"] is False and result["remaining_excess_w"] is None
    assert all(source["fresh"] for source in result["source_reports"])
    assert result["coverage"]["producer_inventory"] == result["coverage"]["storage_inventory"] == "unknown"
    assert result["coverage"]["known_storage_count"] == 0 and not hass.services.calls


def test_same_time_excess_still_has_unknown_inventory(clock):
    runtime, hass = build()
    result = proof(runtime, hass, clock[0])
    assert result["time_aligned"] is True
    assert result["status"] == "unexplained_with_unknown_inventory"
    assert result["known_discharge_w"] is None
    assert result["control_effect"] == "none" and not hass.services.calls


def test_changing_pv_becomes_new_source_evidence_without_rewriting_old_moment(clock):
    runtime, hass = build()
    proof(runtime, hass, clock[0], pv_age=15)
    engine = runtime.learning_hub.investigation
    initial = row(engine.refresh(clock[0]), "solar_balance")
    old = deepcopy(initial["metrics"]["historical_observations"])
    for _ in range(5):
        engine.refresh(clock[0] + 10)
    assert engine.snapshot()["records"]["solar_balance"]["balance_observations"] == old
    clock[0] += 61
    proof(runtime, hass, clock[0], pv=7000)
    later = row(engine.refresh(clock[0]), "solar_balance")
    assert later["metrics"]["proof"]["status"] == "no_excess_observed"
    assert later["metrics"]["historical_observations"] == old
    assert not hass.services.calls


def test_configured_storage_can_explain_only_when_aligned(clock):
    runtime, hass = build(settings={"battery_power_entity": "sensor.storage", "battery_sign": "charge_positive"})
    proof(runtime, hass, clock[0])
    report(hass, "sensor.storage", -3500, clock[0])
    good = runtime_solar_balance_proof(runtime, clock[0])
    assert good["known_discharge_w"] == 3500 and good["remaining_excess_w"] == 0
    assert good["status"] == "known_sources_can_explain"
    assert good["coverage"]["storage_inventory"] == "unknown"
    report(hass, "sensor.storage", -3500, clock[0] - 12)
    bad = runtime_solar_balance_proof(runtime, clock[0])
    assert bad["known_discharge_w"] is None and bad["status"] == "unexplained_with_unknown_inventory"
    assert not hass.services.calls


def test_additional_non_overlapping_producer_prevents_false_mismatch(clock):
    runtime, hass = build()
    baseline = proof(runtime, hass, clock[0])
    report(hass, "sensor.other_producer", 3500, clock[0])
    additional = source_report(runtime, "sensor.other_producer", "producer_2", clock[0], 120, power=True)
    result = solar_balance_proof([baseline["source_reports"][0]], baseline["source_reports"][1], clock[0],
                                 "import_positive", additional_producers=[additional])
    assert result["status"] == "known_sources_can_explain"
    assert result["known_additional_production_w"] == 3500
    assert result["coverage"]["known_producer_count"] == 2
    assert result["coverage"]["producer_inventory"] == "unknown"


@pytest.mark.parametrize("grid_sign,grid,export", [("import_positive", -6000, None), ("export_positive", 6000, None), ("separate", 0, 6000)])
def test_only_explicit_existing_sign_convention_is_used(clock, grid_sign, grid, export):
    runtime, hass = build(settings={"grid_sign": grid_sign, "export_entity": "sensor.export"})
    proof(runtime, hass, clock[0], grid=grid)
    if export is not None:
        report(hass, "sensor.export", export, clock[0])
    before = deepcopy(runtime.settings)
    result = runtime_solar_balance_proof(runtime, clock[0])
    assert result["grid_w"] == -6000
    assert runtime.settings == before and not hass.services.calls


@pytest.mark.parametrize("entity", ["sensor.grid", "sensor.pv"])
@pytest.mark.parametrize("value,attrs", [(None, {}), ("unknown", {}), ("unavailable", {}), ("nan", {}),
                                       ("inf", {}), ("invalid", {}), ("True", {}), (100, {"restored": True}),
                                       (100, {"is_estimated": True}), (100, {"unit_of_measurement": "kWh"})])
def test_missing_or_invalid_balance_sources_stay_unknown(clock, entity, value, attrs):
    runtime, hass = build()
    proof(runtime, hass, clock[0])
    if value is None:
        hass.states.data.pop(entity)
    else:
        report(hass, entity, value, clock[0], **attrs)
    result = runtime_solar_balance_proof(runtime, clock[0])
    assert result["grid_w"] is None and result["export_excess_w"] is None
    assert result["status"] == "insufficient_sources" and not hass.services.calls


def test_legitimate_zero_pv_is_not_missing_and_negative_pv_is_invalid(clock):
    runtime, hass = build()
    result = proof(runtime, hass, clock[0], grid=0, pv=0)
    assert result["pv_w"] == result["grid_w"] == 0
    assert result["status"] == "no_excess_observed"
    assert proof(runtime, hass, clock[0], pv=-5)["pv_w"] is None


def test_balance_history_bounded_restore_is_historical_and_binding_specific(clock):
    runtime, hass = build()
    engine = runtime.learning_hub.investigation
    for _ in range(MAX_BALANCE_OBSERVATIONS + 3):
        proof(runtime, hass, clock[0])
        engine.refresh(clock[0])
        clock[0] += 61
    saved = engine.snapshot()
    assert len(saved["records"]["solar_balance"]["balance_observations"]) == MAX_BALANCE_OBSERVATIONS
    restored = LocalInvestigation(runtime)
    restored.restore(json.loads(json.dumps(saved)))
    assert restored.overview()["items"] == []
    result = row(restored.refresh(clock[0]), "solar_balance")
    assert len(result["metrics"]["historical_observations"]) == MAX_BALANCE_OBSERVATIONS
    runtime.settings["pv_entity"] = "sensor.new_pv"
    clock[0] += 61
    report(hass, "sensor.new_pv", 2000, clock[0])
    result = row(restored.refresh(clock[0]), "solar_balance")
    assert len(result["metrics"]["historical_observations"]) <= 1


@pytest.mark.parametrize("field,value", [("export_excess_w", 9999), ("source_skew_s", 0),
                                        ("observed_at", -1), ("observed_at", "too_old"),
                                        ("status", "known_sources_can_explain")])
def test_corrupted_balance_restore_never_presents_inconsistent_historical_proof(clock, field, value):
    runtime, hass = build()
    proof(runtime, hass, clock[0], grid_age=2, pv_age=15)
    engine = runtime.learning_hub.investigation
    engine.refresh(clock[0])
    saved = engine.snapshot()
    saved["records"]["solar_balance"]["balance_observations"][0][field] = value
    restored = LocalInvestigation(runtime)
    restored.restore(saved)
    assert restored.snapshot()["records"]["solar_balance"]["balance_observations"] == []
    assert restored.overview()["items"] == []


def test_unknown_configured_state_text_and_invalid_power_text_are_withheld(clock):
    runtime, hass = build()
    prepare_wallbox(runtime, hass, clock[0])
    for entity in ("sensor.ev_session", "sensor.ev_status", "sensor.ev_mode", "sensor.ev_power"):
        report(hass, entity, "Unrelated private text", clock[0])
    result = wallbox_source_dossier(runtime, clock[0])
    assert all(source["value"] is None and source["value_withheld"] for source in [result["session"], *result["known_sources"]])
    assert "Unrelated private text" not in json.dumps(result)


@pytest.mark.parametrize("sign,value", [("unknown", 3500), ("discharge_positive", "unavailable"), ("discharge_positive", "nan")])
def test_unknown_storage_sign_or_missing_power_is_not_an_explanation(clock, sign, value):
    runtime, hass = build(settings={"battery_power_entity": "sensor.storage", "battery_sign": sign})
    proof(runtime, hass, clock[0])
    report(hass, "sensor.storage", value, clock[0])
    result = runtime_solar_balance_proof(runtime, clock[0])
    assert result["known_discharge_w"] is None and result["status"] == "unexplained_with_unknown_inventory"


def test_storage_overlap_with_primary_pv_never_explains_export(clock):
    runtime, hass = build(settings={"battery_power_entity": "sensor.pv", "battery_sign": "discharge_positive"})
    result = proof(runtime, hass, clock[0], grid=-4000, pv=2500)
    assert result["known_discharge_w"] is None
    assert result["source_reports"][-1]["issue"] == "overlap_with_primary_source"
    assert result["status"] == "unexplained_with_unknown_inventory"


def template_contract(monkeypatch, runtime, dependencies, *, broad=False):
    """Shape faithful to Core2026.10.1; never use a real private formula."""
    classes = {name: type(name, (), {}) for name in ("TemplateEntity", "TrackTemplateResultInfo", "Template", "RenderInfo")}
    imports = (("homeassistant.components.sensor", {"DATA_COMPONENT": "sensor"}),
               ("homeassistant.components.template.template_entity", {"TemplateEntity": classes["TemplateEntity"]}),
               ("homeassistant.helpers.template.render_info", {"RenderInfo": classes["RenderInfo"]}))
    for name, values in imports:
        module = ModuleType(name)
        for key, value in values.items():
            setattr(module, key, value)
        monkeypatch.setitem(sys.modules, name, module)
    import homeassistant.helpers.event as event
    monkeypatch.setattr(event, "TrackTemplateResultInfo", classes["TrackTemplateResultInfo"], raising=False)
    template_module = ModuleType("homeassistant.helpers.template")
    template_module.Template = classes["Template"]
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.template", template_module)
    import homeassistant.helpers.entity_registry as er
    monkeypatch.setattr(er, "async_get", lambda _hass: SimpleNamespace(async_get=lambda entity: SimpleNamespace(platform="template")))
    template = classes["Template"]()
    entity = classes["TemplateEntity"]()
    entity.hass, entity.entity_id, entity._state_option = runtime.hass, "sensor.ev_session", "state"
    entity._config = {"state": template}
    info = classes["RenderInfo"]()
    info.template, info.entities, info.collecting, info.exception = template, frozenset(dependencies), False, None
    info.all_states, info.all_states_lifecycle, info.domains, info.domains_lifecycle = broad, False, frozenset(), frozenset()
    tracker = classes["TrackTemplateResultInfo"]()
    tracker.hass, tracker._info = runtime.hass, {template: info}
    entity._template_result_info = tracker
    runtime.hass.data["sensor"] = SimpleNamespace(get_entity=lambda entity_id: entity if entity_id == entity.entity_id else None)
    return entity, info


def test_exact_loaded_state_template_dependencies_are_proven_and_private_text_withheld(clock, monkeypatch):
    runtime, hass = build()
    prepare_wallbox(runtime, hass, clock[0])
    report(hass, "sensor.private_text", "Private text that must not leave the dependency source", clock[0])
    entity, info = template_contract(monkeypatch, runtime, {"sensor.ev_status", "sensor.private_text"})
    result = wallbox_source_dossier(runtime, clock[0])
    assert result["dependency_relation"] == "verified_state_template_dependencies"
    assert result["dependency_coverage"] == "last_successful_render_only"
    assert result["template_formula"] == "available_not_exported" and result["template_triggers"] == "unknown"
    assert result["dependencies"][0]["matches_configured_roles"] == ["status"]
    assert result["dependencies"][1]["value"] is None and result["dependencies"][1]["value_withheld"] is True
    assert "Private text" not in json.dumps(result) and "sensor.private" not in json.dumps(result)
    assert not hass.services.calls


@pytest.mark.parametrize("failure", ["wrong_hass", "wrong_entity", "render_error", "collecting", "tracker_missing", "trigger_or_other_entity"])
def test_unsupported_or_failed_template_runtime_does_not_guess_dependencies(clock, monkeypatch, failure):
    runtime, hass = build()
    prepare_wallbox(runtime, hass, clock[0])
    entity, info = template_contract(monkeypatch, runtime, {"sensor.ev_status"})
    if failure == "wrong_hass":
        entity.hass = object()
    elif failure == "wrong_entity":
        entity.entity_id = "sensor.other_session"
    elif failure == "render_error":
        info.exception = ValueError("Private error text")
    elif failure == "collecting":
        info.collecting = True
    elif failure == "tracker_missing":
        entity._template_result_info = None
    else:
        runtime.hass.data["sensor"] = SimpleNamespace(get_entity=lambda _id: SimpleNamespace(**entity.__dict__))
    result = wallbox_source_dossier(runtime, clock[0])
    assert result["dependency_relation"] == "unknown" and result["dependencies"] == []
    assert "Private error" not in json.dumps(result) and not hass.services.calls


def test_broad_dependencies_are_not_scanned_and_explicit_sources_are_bounded(clock, monkeypatch):
    runtime, hass = build()
    prepare_wallbox(runtime, hass, clock[0])
    dependencies = {f"sensor.source_{index}" for index in range(MAX_COMPARISON_SOURCES + 3)}
    template_contract(monkeypatch, runtime, dependencies, broad=True)
    result = wallbox_source_dossier(runtime, clock[0])
    assert result["dependency_coverage"] == "partial"
    assert len(result["dependencies"]) == MAX_COMPARISON_SOURCES
    assert all(source["value"] is None for source in result["dependencies"])
    assert not hass.services.calls
