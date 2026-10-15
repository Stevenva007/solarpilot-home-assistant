"""Use the shipped renderer with fictional source-bound calculations only."""
from copy import deepcopy
from datetime import datetime
import time

import pytest

from test_heatpump_history_ui70 import history_fixture, render_history
from test_heatpump_history_ui82 import display, point
from test_heatpump_ui65 import metered_sample, parsed, business_tile, provenance
from test_investigation_ui75 import investigation, execute, NOW
from test_overview_details60 import Markup
from test_research_ui81 import render_pv


def goal(at=None, *, percent=115, contact="on"):
    at = time.time() if at is None else at
    return {"normal_target_c": 50, "calculated_c": 50*percent/100, "profile_percent": percent,
        "profile_confirmed_at": at-60, "normal_target_reported_at": at-3,
        "valid_until": at+117, "stale_s": 120, "reason": "calculated",
        "source": "local_confirmed_profile", "read_only": True,
        "contact_state": contact, "contact_reported_at": at-2,
        "contact_valid_until": at+118, "contact_stale_s": 120}


def set_goal(data, row):
    data["panasonic"].update(sg_tank_goal=row, display_tank={"available": True,
        "temperature_c": 49, "temperature_stamp": time.time(), "target_c": row["normal_target_c"],
        "target_stamp": row["normal_target_reported_at"]})


def boiler_strip(root):
    return next(n for n in root.walk() if "data-boiler-temperatures" in n.attributes)


@pytest.mark.parametrize("on,label", [(True, "SG-doel · berekend"), (False, "SG-doel bij AAN · berekend")])
def test_goal_uses_confirmed_actual_contact_and_never_request_as_contact(on, label):
    data = metered_sample()
    set_goal(data, goal())
    data["sg_boost"].update(desired_on=not on, relay_on=on, relay_confirmed=True)
    _, root = parsed(data)
    strip = boiler_strip(root)
    assert label in strip.text() and "57,5 °C" in strip.text()
    assert "Ingesteld boilerdoel" in strip.text() and "50 °C" in strip.text()
    assert "effectief" not in strip.text().lower() and "ontvangen" not in strip.text().lower()


def test_unknown_contact_keeps_conditional_calculation_without_claiming_contact_on():
    data = metered_sample()
    set_goal(data, goal(contact="unknown"))
    data["sg_boost"].update(desired_on=True, relay_on=True, relay_confirmed=False)
    _, root = parsed(data)
    assert "57,5 °C" in boiler_strip(root).text()
    assert "SG-doel bij AAN · berekend" in boiler_strip(root).text()
    assert "SG-doel · berekend" not in boiler_strip(root).text()
    assert "SG-doel bij AAN · berekend" in provenance(root).text()
    assert "57,5 °C" in provenance(root).text()


@pytest.mark.parametrize("change", ["unconfirmed", "missing_normal", "stale", "future_confirmation", "boolean", "out_of_range"])
def test_unknown_or_expired_input_never_yields_a_calculated_goal(change):
    data = metered_sample()
    row = goal()
    if change == "unconfirmed":
        row.update(calculated_c=None, source="none", reason="profile_unconfirmed")
    elif change == "missing_normal":
        row["normal_target_reported_at"] = None
    elif change == "stale":
        row.update(normal_target_reported_at=time.time()-1000, valid_until=time.time()-880)
    elif change == "future_confirmation":
        row["profile_confirmed_at"] = time.time()+1000
    elif change == "boolean":
        row["profile_percent"] = True
    else:
        row["calculated_c"] = 150
    set_goal(data, row)
    data["sg_boost"].update(relay_on=True, relay_confirmed=True)
    _, root = parsed(data)
    assert "SG-doel · berekend" not in boiler_strip(root).text()
    assert "57,5 °C" not in provenance(root).text()


def test_historical_calculation_keeps_its_factor_and_unknown_contact_is_conditional():
    data = history_fixture()
    data["today"] = "2026-10-13"
    historical = point("2026-10-12T06:55:00+02:00", 49, 50)
    historical["sg_goal"] = goal(historical["captured_at"], contact="unknown")
    historical["sg_goal"].update(contact_reported_at=None, contact_valid_until=None)
    data["tank_temperature"] = {"schema": 1, "current": {"current": True,
        "captured_at": time.time(), "sg_goal": goal(percent=150)}, "points": [historical]}
    data["native_evidence"] = {"schema": 1, "read_only": True, "points": [{
        "captured_at": historical["captured_at"], "source_stale_s": 120, "tank": historical,
        "sg_goal": historical["sg_goal"]}]}
    root = Markup(render_history(data)["html"]).root
    table = next(n for n in root.walk() if "data-history-sg-calculation" in n.attributes)
    assert "57,5 °C" in table.text() and "115%" in table.text()
    assert "SG-doel bij AAN · berekend" in table.text()
    assert "75 °C" not in root.text(), "Today's later confirmation must not repaint historical metadata"
    concise = next(n for n in root.walk() if "data-tank-sg-target" in n.attributes)
    assert "57,5 °C" in concise.text(), "A recorded conditional comparison keeps its original percentage"


def test_legacy_points_do_not_inherit_a_new_confirmed_profile():
    data = history_fixture()
    legacy = point("2026-10-12T06:55:00+02:00", 49, 50)
    data["native_evidence"] = {"schema": 1, "read_only": True, "points": [
        {"captured_at": legacy["captured_at"], "tank": legacy}]}
    root = Markup(render_history(data)["html"]).root
    assert next(n for n in root.walk() if "data-history-sg-calculation" in n.attributes).text() == "—"
    assert "Effectief doel" in root.text()


def contract():
    return {"schema": 1, "read_only": True, "status": "verified",
        "provider_loaded": True, "native_device_registered": True,
        "contract_id": "aioaquarea_ng_1_3_1_special_status", "action_semantics": "special_status",
        "compatibility": {"schema": 1, "contract": "aquarea_special_status_action_v1",
                          "verified": True, "basis": "loaded_source", "fingerprint": "a"*64},
        "provider": {"integration_domain": "aquarea", "integration_version": "1.5.3",
                     "library_distribution": "aioaquarea-ng", "library_version": "1.3.1"},
        "raw_device_action": "OFF", "pump": {"state": "on", "observed_at": time.time()},
        "direction": {"state": "PUMP", "observed_at": time.time()},
        "program": {"state": "heating", "observed_at": time.time()},
        "tank": {"enabled": True, "observed_at": time.time()},
        "zones": [{"enabled": True, "state": "heat", "observed_at": time.time()}]}


@pytest.mark.parametrize("verified", [True, False])
def test_verified_semantic_contract_bounds_new_heating_interpretation(verified):
    data = metered_sample(1700, complete=False, roles=("main", "unconfirmed"))
    row = display("space_heating", source="aquarea_contract", kind="coherent_native_context",
                  source_contract_id="aioaquarea_ng_1_3_1_special_status", reason="Samengestelde verse broncontext")
    data["panasonic"].update(operation_display=row, source_contract=contract())
    if not verified:
        data["panasonic"]["source_contract"]["compatibility"]["verified"] = False
    _, root = parsed(data)
    task = business_tile(root, "data-heatpump-task")
    assert ("Verwarmen" in task.text()) is verified
    assert "Actief · taak onbekend" in task.text() if not verified else True
    details = next(n for n in root.walk() if "data-panasonic-source-contract" in n.attributes)
    assert "Waterpomp" in details.text() and "Ruimtebedrijf" in details.text()
    assert "Zone 1 ingeschakeld" in details.text() and "Ja" in details.text()
    assert "OFF" in details.text()


@pytest.mark.parametrize("provider_version,library_version", [
    ("1.5.4", "1.3.1"), ("1.5.5", "1.3.2"), ("2.0.0", "2.0.0"),
])
def test_verified_future_provider_context_uses_capability_marker_without_version_gate(provider_version, library_version):
    data = metered_sample(1700, complete=False, roles=("main", "unconfirmed"))
    row = display("space_heating", source="aquarea_contract", kind="coherent_native_context",
                  source_contract_id="aioaquarea_ng_1_3_1_special_status", reason="Verse samenhangende broncontext")
    evidence = contract()
    evidence["provider"]["integration_version"] = provider_version
    evidence["provider"]["library_version"] = library_version
    data["panasonic"].update(operation_display=row, source_contract=evidence)
    _, root = parsed(data)
    task = business_tile(root, "data-heatpump-task").text()
    assert "Verwarmen" in task
    assert "Actief · taak onbekend" not in task


@pytest.mark.parametrize("problem", [
    "missing", "unverified", "schema", "semantics", "basis", "fingerprint",
    "fingerprint_case", "provider_unloaded", "status", "action_semantics", "contract_id",
])
def test_unknown_or_mismatched_semantic_marker_never_confirms_future_task(problem):
    data = metered_sample(1700, complete=False, roles=("main", "unconfirmed"))
    row = display("space_heating", source="aquarea_contract", kind="coherent_native_context",
                  source_contract_id="aioaquarea_ng_1_3_1_special_status", reason="Verse samenhangende broncontext")
    evidence = contract()
    evidence["provider"].update(integration_version="2.0.0", library_version="2.0.0")
    if problem == "missing":evidence.pop("compatibility")
    elif problem == "unverified":evidence["compatibility"]["verified"] = False
    elif problem == "schema":evidence["compatibility"]["schema"] = 2
    elif problem == "semantics":evidence["compatibility"]["contract"] = "main_status_action"
    elif problem == "basis":evidence["compatibility"]["basis"] = "version_label"
    elif problem == "fingerprint":evidence["compatibility"]["fingerprint"] = "a"*63
    elif problem == "fingerprint_case":evidence["compatibility"]["fingerprint"] = "A"*64
    elif problem == "provider_unloaded":evidence["provider_loaded"] = False
    elif problem == "status":evidence["status"] = "unknown"
    elif problem == "action_semantics":evidence["action_semantics"] = "main_status"
    else:evidence["contract_id"] = "different_contract"
    data["panasonic"].update(operation_display=row, source_contract=evidence)
    _, root = parsed(data)
    task = business_tile(root, "data-heatpump-task").text()
    assert "Verwarmen" not in task
    assert "Actief · taak onbekend" in task


@pytest.mark.parametrize("reason_code", ["provider_semantics_unavailable", "provider_semantics_changed"])
def test_incompatible_or_unverified_source_explains_reason_and_action_without_html(reason_code):
    data = metered_sample(1700, complete=False, roles=("main", "unconfirmed"))
    evidence = contract()
    evidence.update(status="unknown", reason_code=reason_code,
                    reason='Aquarea-statusformaat niet bevestigd <img src=x onerror="bad()">',
                    action="Laat de compatibiliteit controleren; actuele netmeting blijft leidend.")
    evidence["compatibility"]["verified"] = False
    data["panasonic"].update(source_contract=evidence, operation_display=display(
        None, context="heatpump_unknown", tier="unknown", reason_code=reason_code,
        reason=evidence["reason"], action=evidence["action"]))
    _, root = parsed(data)
    details = next(n for n in root.walk() if "data-panasonic-source-contract" in n.attributes)
    assert "Aquarea-statusformaat niet bevestigd" in details.text()
    assert "Laat de compatibiliteit controleren" in details.text()
    assert not any(n.tag == "img" for n in details.walk())
    assert "Actief · taak onbekend" in business_tile(root, "data-heatpump-task").text()


def test_actionable_unknown_reason_remains_escaped_and_does_not_claim_task():
    data = metered_sample(1700, complete=False, roles=("main", "unconfirmed"))
    payload = '<img src=x onerror="window.bad=true">'
    data["panasonic"]["operation_display"] = display(None, context="heatpump_unknown", tier="unknown",
        reason_code="native_context_report_skew", reason="Rapporttijden niet gelijk "+payload,
        action="Wacht op nieuwe bronrapporten "+payload)
    _, root = parsed(data)
    assert "Actief · taak onbekend" in business_tile(root, "data-heatpump-task").text()
    assert "Wacht op nieuwe bronrapporten" in provenance(root).text()
    assert payload in provenance(root).text()
    assert not any(n.tag == "img" for n in root.walk())


def test_cached_and_current_proof_keep_their_own_skew_and_timestamps():
    data = investigation()
    item = data["items"][0]
    item.update(id="solar_balance", assessment_observed_at=NOW-30, current_observed_at=NOW,
                assessment_summary="Rapportafstand toen 25 s", assessment_evidence=["Oorspronkelijk bewijs"],
                metrics={"assessment_proof": {"grid_w": 900, "pv_w": 0, "source_skew_s": 25, "time_aligned": False},
                         "proof": {"grid_w": 800, "pv_w": 0, "source_skew_s": 4, "time_aligned": True}})
    _, root = execute(data)
    eras = {n.attributes["data-proof-era"]: n.text() for n in root.walk() if "data-proof-era" in n.attributes}
    assert "25 s" in eras["assessment"] and "Rapportafstand toen 25 s" in eras["assessment"]
    assert "4 s" in eras["current"] and "25 s" not in eras["current"]
    assert "Meetbasis beoordeling" in eras["assessment"] and "Actuele broncontrole" in eras["current"]


def test_pv_daylight_error_and_zero_without_night_proof_remain_visible():
    root = render_pv({"forecast_evidence": {"version": 1, "summary": {"ahead_comparisons": 100,
        "unique_targets": 20, "distinct_days": 3, "by_recorded_lead": [{"label": "1–3 uur",
            "samples": 100, "unique_targets": 20, "mae_w": 90, "bias_w": -20, "distinct_days": 3,
            "conditions": [{"condition": "daylight", "samples": 10, "unique_targets": 5, "mae_w": 900,
                            "bias_w": -200, "distinct_days": 2},
                           {"condition": "night", "samples": 80, "unique_targets": 13, "mae_w": 0},
                           {"condition": "other_zero", "samples": 10, "unique_targets": 2, "mae_w": 0}]}]}}})
    rows = {n.attributes["data-pv-condition"]: n.text() for n in root.walk() if "data-pv-condition" in n.attributes}
    assert "Totaal" in rows["total"] and "90 W" in rows["total"]
    assert "Daglicht" in rows["daylight"] and "900 W" in rows["daylight"]
    assert "dag/nacht niet bevestigd" in rows["other_zero"]
    assert "unieke kwartieren" in root.text() and "0 W" in rows["night"]


@pytest.mark.parametrize("contract_known,source", [(True, "aquarea_poll"), (False, "aquarea_poll"), (False, "native_hvac_action")])
def test_new_source_metadata_qualifies_sdk_profile_without_rewriting_legacy_native(contract_known, source):
    data = history_fixture()
    capture = datetime.fromisoformat("2026-10-12T06:55:00+02:00").timestamp()
    native = {"source": source, "inactive_reported": True, "global_off": True, "confirmed": False,
              "reported_at": capture-3, "fresh": True, "start_observed": True}
    metadata = {"schema": 1, "read_only": True, "verified": False, "raw_device_action": "OFF",
                "contract_id": "aioaquarea_ng_1_3_1_special_status" if contract_known else None,
                "action_semantics": "special_status" if contract_known else "unknown"}
    data["native_evidence"] = {"schema": 1, "read_only": True,
        "points": [{"captured_at": capture, "native": native, "source_contract": metadata}]}
    root = Markup(render_history(data)["html"]).root
    details = next(n for n in root.walk() if n.attributes.get("data-history-key") == "native")
    if source == "aquarea_poll":
        assert "Native globaal UIT" not in details.text()
        assert "Native start waargenomen" not in details.text()
        assert ("SDK-profielstatus: OFF" if contract_known else "Panasonic-bronstatus: OFF") in details.text()
        assert "Bronmapping bij vastlegging onvolledig" in details.text()
    else:
        assert "Native globaal UIT" in details.text() and "Native start waargenomen" in details.text()
    assert native["global_off"] is True and native["start_observed"] is True


def test_new_current_goal_must_match_authoritative_normal_target_and_original_stamp():
    data = metered_sample()
    set_goal(data, goal())
    data["sg_boost"].update(relay_on=True, relay_confirmed=True)
    data["panasonic"]["display_tank"]["target_c"] = 51
    _, root = parsed(data)
    assert "57,5 °C" not in boiler_strip(root).text()
    assert "57,5 °C" not in provenance(root).text()
    data["panasonic"]["display_tank"]["target_c"] = 50
    data["panasonic"]["display_tank"]["target_stamp"] += 1
    _, root = parsed(data)
    assert "57,5 °C" not in boiler_strip(root).text()
