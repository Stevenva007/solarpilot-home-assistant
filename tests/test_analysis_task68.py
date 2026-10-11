"""The analysis retains cloud reports alongside bounded display inference."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot import analysis_export as export
from custom_components.solar_pilot import analysis_review as review
from test_analysis_review67_audit import package, recorded


def active_idle(ts=1000, function="space_heating", kind="selected_program"):
    row = recorded(ts, function=None)
    p = row["panasonic"]
    p["native_task"].update(inactive=True, inactive_action="idle")
    source = "aquarea_entity" if kind == "tank_route" else "native_program"
    p["task_context"] = {"function": function, "kind": kind, "source": source,
                         "observed_at": ts, "stale_s": 120}
    p["power_activity"].update(function=function, function_kind=kind, function_source=source,
                               evidence="metered_power_and_context")
    return row


@pytest.mark.parametrize("function,kind", [("space_heating", "selected_program"),
    ("space_cooling", "selected_program"), ("tapwater_heating", "tank_route")])
def test_active_idle_is_exported_as_inferred_without_rewriting_native_report(function, kind):
    rows = [active_idle(ts, function, kind) for ts in (1000, 1300)]
    original = deepcopy(rows)
    bundle = review.build_review_bundle(package(rows))
    assert bundle["quality"]["regime_observation_counts"] == {function + "_inferred": 2}
    assert bundle["history"]["regime_endpoint_intervals"][0]["regime"] == function + "_inferred"
    for sample in bundle["history"]["samples"]:
        assert sample["native_task"]["inactive"] is True
        assert sample["native_task"]["inactive_action"] == "idle"
        assert sample["native_task"]["function"] is None
        assert sample["task_context"]["function"] == sample["power_activity"]["function"] == function
    assert rows == original


@pytest.mark.parametrize("mutation", ["off", "legacy_idle", "stale_context", "wrong_context",
    "missing_source", "heater_only", "main_below_threshold", "partial_feed", "conflict"])
def test_idle_cannot_justify_an_unbound_or_unsupported_exported_function(mutation):
    row = active_idle()
    p = row["panasonic"]
    if mutation == "off":
        p["native_task"]["inactive_action"] = "off"
    elif mutation == "legacy_idle":
        p["native_task"].pop("inactive_action")
    elif mutation == "stale_context":
        p["task_context"]["observed_at"] = 800
    elif mutation == "wrong_context":
        p["task_context"]["function"] = "space_cooling"
    elif mutation == "missing_source":
        p["power_activity"].pop("function_source")
    elif mutation == "heater_only":
        p["power_activity"]["activity_kind"] = "heater"
    elif mutation == "main_below_threshold":
        p["power_supply1_w"] = 58
    elif mutation == "partial_feed":
        p["power_supply2_valid"] = False
    else:
        p["native_task"]["conflict"] = True
    counts = review.build_review_bundle(package([row]))["quality"]["regime_observation_counts"]
    assert "space_heating_inferred" not in counts
    assert "space_heating_reported" not in counts


def test_idle_transition_to_off_is_a_recorded_change_even_if_watts_stay_active():
    row = active_idle()["panasonic"]
    idle = review.discrete_heatpump_state(row, {})
    row["native_task"]["inactive_action"] = "off"
    off = review.discrete_heatpump_state(row, {})
    assert idle != off
    assert idle["native_task"]["inactive_action"] == "idle"
    assert off["native_task"]["inactive_action"] == "off"


def test_unsupported_native_source_does_not_veto_a_valid_fresh_display_inference():
    row = active_idle()
    row["panasonic"]["native_task"].update(source="guessed", inactive_action="off", conflict=True)
    counts = review.build_review_bundle(package([row]))["quality"]["regime_observation_counts"]
    assert counts == {"space_heating_inferred": 1}


@pytest.mark.parametrize("native", [{}, {"source": "none", "function": None},
    {"source": "aquarea_poll", "inactive": True, "inactive_action": "idle", "observed_at": 800}])
@pytest.mark.parametrize("mutation", ["stale_context", "missing_context", "wrong_context", "main_below_threshold"])
def test_selected_inference_keeps_its_own_source_guards_when_native_report_is_absent_or_stale(native, mutation):
    row = active_idle()
    p = row["panasonic"]
    p["native_task"] = deepcopy(native)
    if mutation == "stale_context":
        p["task_context"]["observed_at"] = 800
    elif mutation == "missing_context":
        p["task_context"] = {}
    elif mutation == "wrong_context":
        p["task_context"]["function"] = "space_cooling"
    else:
        p["power_supply1_w"] = 58
    counts = review.build_review_bundle(package([row]))["quality"]["regime_observation_counts"]
    assert counts == {"electrical_active": 1}


def test_protocol_idle_survives_pseudonymization_while_household_prose_is_redacted():
    payload = {"native_task": {"inactive_action": "idle"}, "note": "idle"}
    result = export.pseudonymize(payload, {"idle": "consumer_1"}, {"idle": "Verbruiker 1"})
    assert result["native_task"]["inactive_action"] == "idle"
    assert result["note"] == "Verbruiker 1"
