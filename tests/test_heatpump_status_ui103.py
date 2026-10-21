"""Actual backend-to-card task recognition with fictional, original evidence."""
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from custom_components.solar_pilot.display_operation import classify_display_operation
from custom_components.solar_pilot.heatpump_learning import classify_heatpump_observation
from custom_components.solar_pilot.heatpump_history import HeatpumpHistory
from custom_components.solar_pilot.operation_source_evidence import CONTRACT_ID, SEMANTIC_CONTRACT_ID
from test_heatpump_learning102 import NOW, enabled_snapshot
from test_heatpump_ui65 import business_tile, metered_sample, parsed, provenance
from test_heatpump_history_ui70 import render_history


def status_snapshot(*, function="space_heating", mapping="operation", now=NOW):
    """Use the real classifier, not a hand-approved presentation result."""
    data = metered_sample(1300, roles=("main", "heater"))
    p = enabled_snapshot(function=function)
    if mapping == "special":
        contract = p["source_contract"]
        contract.update(contract_id=CONTRACT_ID, action_semantics="special_status",
                        compatibility={"schema": 1, "contract": SEMANTIC_CONTRACT_ID,
                                       "verified": True, "basis": "loaded_source", "fingerprint": "a"*64})
        contract.pop("status_data_mode")
        contract.pop("device_operation_status")
    # Keep every relative original source time; browser callers use their own
    # capture clock. This never makes one channel's report another's report.
    def shifted(value):
        if isinstance(value, dict):
            return {key: shifted(item) for key, item in value.items()}
        if isinstance(value, list):
            return [shifted(item) for item in value]
        return value + now - NOW if type(value) in (int, float) and NOW-1000 < value < NOW+1000 else value
    p = shifted(p)
    for row in p["power_activity"]["supplies"]:
        number = row["number"]
        p.update({f"power_supply{number}_w": row["watts"],
                  f"power_supply{number}_valid": row["valid"],
                  f"power_supply{number}_observed_at": row["observed_at"]})
    p["operation_display"] = classify_display_operation(p, now_wall=now)
    data.update(_test_clock=now, panasonic=p)
    return data


def status_history(*, function="space_heating", now=NOW):
    """A real recorder output: current task needs no second client inference."""
    history = HeatpumpHistory("Europe/Brussels")
    for offset in (-20, -10, 0):
        tick = now+offset
        history.observe(status_snapshot(function=function, now=tick)["panasonic"], {},
                        datetime.fromtimestamp(tick, timezone.utc), binding="synthetic_bound_heatpump")
    when = datetime.fromtimestamp(now, timezone.utc)
    return history.detail(when.astimezone(history.lanes.zone).date().isoformat(), when)


@pytest.mark.parametrize("view", ["board", "comfort"])
@pytest.mark.parametrize("mapping", ["special", "operation"])
@pytest.mark.parametrize("function,label", [("space_heating", "Verwarmen"),
                                           ("space_cooling", "Koelen"),
                                           ("tapwater_heating", "Boiler opwarmen")])
def test_real_coherent_backend_task_is_visible_in_both_card_views(view, mapping, function, label):
    data = status_snapshot(function=function, mapping=mapping)
    before = deepcopy(data)
    display = data["panasonic"]["operation_display"]
    assert display["function"] == function and display["tier"] == "derived"
    assert display["source"] == "aquarea_contract" and display["kind"] == "coherent_native_context"
    assert display["active"] is True and display["model_eligible"] is False
    _, root = parsed(data, view)
    task = business_tile(root, "data-heatpump-task")
    assert task.attributes["data-heatpump-task"] == "inferred"
    assert label in task.text() and "onbekend" not in task.text().lower()
    assert "afgeleid uit verbruik en Panasonic-context" in provenance(root).text()
    assert data == before, "Rendering cannot rewrite source, learner or SG evidence"
    learning = classify_heatpump_observation(data["panasonic"], now_wall=NOW)
    assert learning["model_eligible"] is False


@pytest.mark.parametrize("version,library", [("1.8.0", "1.4.0"), ("9.0.0", "8.0.0"), ("future", "future")])
def test_verified_semantics_accept_future_release_labels_without_version_allowlist(version, library):
    data = status_snapshot()
    data["panasonic"]["source_contract"]["provider"].update(integration_version=version, library_version=library)
    _, root = parsed(data)
    assert "Verwarmen" in business_tile(root, "data-heatpump-task").text()


@pytest.mark.parametrize("mapping", ["special", "operation"])
@pytest.mark.parametrize("problem", ["contract_id", "semantics", "cross_marker", "missing_marker", "false_marker",
    "marker_schema", "extra_marker", "basis", "fingerprint", "provider_domain", "library", "unloaded",
    "unregistered", "schema", "not_readonly", "unverified", "result_binding", "result_old"])
def test_unverified_mismatched_or_expired_cached_task_stays_unknown(mapping, problem):
    data = status_snapshot(mapping=mapping)
    p, contract = data["panasonic"], data["panasonic"]["source_contract"]
    marker = contract["compatibility"]
    if problem == "contract_id": contract["contract_id"] = "unknown"
    elif problem == "semantics": contract["action_semantics"] = "unreviewed"
    elif problem == "cross_marker": marker["contract"] = "aquarea_special_status_action_v1" if mapping == "operation" else "aquarea_operation_status_action_v1"
    elif problem == "missing_marker": contract.pop("compatibility")
    elif problem == "false_marker": marker["verified"] = False
    elif problem == "marker_schema": marker["schema"] = True
    elif problem == "extra_marker": marker["future_authority"] = True
    elif problem == "basis": marker["basis"] = "version_label"
    elif problem == "fingerprint": marker["fingerprint"] = "B"*64
    elif problem == "provider_domain": contract["provider"]["integration_domain"] = "other"
    elif problem == "library": contract["provider"]["library_distribution"] = "other"
    elif problem == "unloaded": contract["provider_loaded"] = False
    elif problem == "unregistered": contract["native_device_registered"] = False
    elif problem == "schema": contract["schema"] = True
    elif problem == "not_readonly": contract["read_only"] = False
    elif problem == "unverified": contract["status"] = "unknown"
    elif problem == "result_binding": p["operation_display"]["source_contract_id"] = "other"
    else: p["operation_display"].update(observed_at=NOW-121, valid_until=NOW-1)
    _, root = parsed(data)
    task = business_tile(root, "data-heatpump-task").text()
    assert "Actief · taak onbekend" in task and "Verwarmen" not in task


@pytest.mark.parametrize("field,value", [("status_data_mode", "CACHED"), ("status_data_mode", None),
                                        ("device_operation_status", "OFF"), ("device_operation_status", "UNKNOWN")])
def test_split_cached_or_disabled_source_cannot_reuse_a_previous_derived_presentation(field, value):
    data = status_snapshot()
    data["panasonic"]["source_contract"][field] = value
    _, root = parsed(data)
    assert "Actief · taak onbekend" in business_tile(root, "data-heatpump-task").text()


@pytest.mark.parametrize("problem", ["pump_off", "tank_active", "main_unknown", "meter_old", "context_skew", "cached"])
def test_backend_execution_guards_still_prevent_direction_from_enablement_only(problem):
    data = status_snapshot()
    p, contract = data["panasonic"], data["panasonic"]["source_contract"]
    if problem == "pump_off": contract["pump"]["state"] = "off"
    elif problem == "tank_active": p["display_tank"]["mode"] = "heating"
    elif problem == "main_unknown": p["power_activity"]["supplies"][0]["role"] = "unconfirmed"
    elif problem == "meter_old": p["power_activity"]["supplies"][0]["observed_at"] = NOW-121
    elif problem == "context_skew": contract["pump"]["observed_at"] = NOW-20
    else: contract["status_data_mode"] = "CACHED"
    p["operation_display"] = classify_display_operation(p, now_wall=NOW)
    assert p["operation_display"]["function"] is None
    _, root = parsed(data)
    tasks = [node for node in root.walk() if "data-heatpump-task" in node.attributes]
    assert all("Verwarmen" not in node.text() for node in tasks)
    assert classify_heatpump_observation(p, now_wall=NOW)["model_eligible"] is False


def test_split_provenance_labels_enablement_and_live_status_without_claiming_compressor_proof():
    _, root = parsed(status_snapshot())
    proof = next(node for node in root.walk() if "data-panasonic-source-contract" in node.attributes).text()
    assert "Hoofdtoestel ingeschakeld Ja" in proof
    assert "Herkomst native terugmelding Live" in proof
    assert "Oorspronkelijke Panasonic-bronstatus HEATING" in proof
    assert "geen zelfstandig bewijs van warmteproductie" in proof
    assert "Oorspronkelijke speciale status" not in proof


@pytest.mark.parametrize("function,label", [("space_heating", "Verwarmen"),
                                           ("space_cooling", "Koelen"),
                                           ("tapwater_heating", "Boiler opwarmen")])
def test_real_recorded_derived_task_keeps_its_capture_contract_and_history_label(function, label):
    day = status_history(function=function)
    assert day["task_sessions"] and all(row["task"] == function and row["tier"] == "derived" for row in day["task_sessions"])
    assert day["energy_kwh"] > 0 and day["energy_known_s"] == 20
    original = deepcopy(day)
    html = render_history(day)["html"]
    assert label in html and "Panasonic-bronstatus:" in html
    assert "Bronmapping bij vastlegging bevestigd" in html
    assert day == original
