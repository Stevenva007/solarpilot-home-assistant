"""Synthetic task provenance and planning regressions; no household data."""
from copy import deepcopy
from datetime import datetime, timezone
import time

import pytest

from custom_components.solar_pilot.heatpump_learning import (
    CONTEXT_DHW, CONTEXT_HEATING, CONTEXT_NORMAL, CONTEXT_UNKNOWN,
    HeatPumpActivityModel, classify_heatpump_observation,
)
from test_learning_hub30 import metered


NOW = 1000


def observation(*, function=CONTEXT_DHW, kind="tank_route", active=True):
    source = "aquarea_entity" if kind == "tank_route" else "native_program"
    return {"configured": True, "source_stale_s": 120, "program": "heating",
        "context": CONTEXT_HEATING, "context_reliable": True, "context_stamp": 995,
        "native_task": {"function": None, "source": "aquarea_poll", "observed_at": 990,
                        "stale_s": 120, "inactive": True, "inactive_action": "idle"},
        "task_context": {"function": function, "kind": kind, "source": source,
                         "observed_at": 985, "stale_s": 120},
        "power_activity": {"function": function if active else None, "function_kind": kind if active else "none",
            "function_source": source, "complete": True, "active": active,
            "state": "active" if active else "off", "observed_at": 980,
            "context_observed_at": 985, "stale_s": 120, "total_w": 1800 if active else 0,
            "threshold_w": 200, "activity_kind": "main" if active else "unknown",
            "supplies": [{"role": "main", "valid": True, "watts": 1800 if active else 0,
                          "state": "active" if active else "off", "observed_at": 997},
                         {"role": "heater", "valid": True, "watts": 0, "state": "off", "observed_at": 999}]}}


def classify(view):
    before = deepcopy(view)
    result = classify_heatpump_observation(view, now_wall=NOW)
    assert view == before
    return result


def test_current_tank_route_never_learns_the_selected_space_programme():
    result = classify(observation())
    assert result["context"] == CONTEXT_DHW and result["tier"] == "derived"
    assert not result["model_eligible"]
    assert result["selected_program"] == "heating" and result["guard_context"] == CONTEXT_HEATING


def test_fresh_native_task_outweighs_selected_and_derived_direction():
    view = observation()
    view["native_task"].update(function="space_cooling", inactive=False, source="native_hvac_action")
    result = classify(view)
    assert result["context"] == "space_cooling" and result["tier"] == "confirmed"
    assert result["model_eligible"]


@pytest.mark.parametrize("kind,function", [("tank_route", CONTEXT_DHW), ("selected_program", CONTEXT_HEATING)])
def test_old_native_task_cannot_promote_independently_fresh_derived_task(kind, function):
    view = observation(function=function, kind=kind)
    view["native_task"].update(function=function, source="aquarea_poll", observed_at=879, inactive=False)
    assert classify(view)["tier"] == "derived"


@pytest.mark.parametrize("fault", ["conflict", "defrost"])
def test_actual_task_conflicts_and_defrost_interrupt_learning(fault):
    view = observation()
    if fault == "conflict":
        view["native_task"]["conflict"] = True
    else:
        view["defrost"] = {"state": "active", "source": "aquarea_entity", "observed_at": 990}
    result = classify(view)
    assert result["context"] == CONTEXT_UNKNOWN and result["tier"] == "unknown"


@pytest.mark.parametrize("case", ["global_off", "legacy_off", "legacy_inactive", "stale_context",
    "wrong_context", "missing_main", "old_supply", "old_power", "old_power_context", "unqualified_source"])
def test_invalid_or_vetoed_derived_proof_never_becomes_validated_or_normal(case):
    view = observation()
    if case in ("global_off", "legacy_off"):
        view["native_task"].update(inactive_action="off", inactive_scope="global" if case == "global_off" else "unknown")
    elif case == "legacy_inactive":
        view["native_task"].pop("inactive_action")
    elif case == "stale_context":
        view["task_context"]["observed_at"] = 879
    elif case == "wrong_context":
        view["task_context"]["function"] = CONTEXT_HEATING
    elif case == "missing_main":
        view["power_activity"]["supplies"][0]["role"] = "unconfirmed"
    elif case == "old_supply":
        view["power_activity"]["supplies"][1]["observed_at"] = 879
    elif case == "old_power":
        view["power_activity"]["observed_at"] = 879
    elif case == "old_power_context":
        view["power_activity"]["context_observed_at"] = 879
    elif case == "unqualified_source":
        view["task_context"]["source"] = view["power_activity"]["function_source"] = "none"
    result = classify(view)
    assert result["context"] == CONTEXT_UNKNOWN and not result["model_eligible"]


def test_scoped_space_off_with_independently_active_tank_can_be_diagnostic_only():
    view = observation()
    view["native_task"].update(inactive_action="off", inactive_scope="space_circuit", independent_tank_on=True)
    result = classify(view)
    assert result["context"] == CONTEXT_DHW and result["tier"] == "derived"
    view["native_task"]["independent_tank_on"] = False
    assert classify(view)["context"] == CONTEXT_UNKNOWN


@pytest.mark.parametrize("key,value", [("source", "none"), ("inactive_action", "mixed"),
                                      ("verified_global_off", True)])
def test_inconsistent_scoped_off_proof_does_not_bypass_global_veto(key, value):
    view = observation()
    view["native_task"].update(inactive_action="off", inactive_scope="space_circuit", independent_tank_on=True)
    view["native_task"][key] = value
    assert classify(view)["context"] == CONTEXT_UNKNOWN


@pytest.mark.parametrize("case", ["bad_threshold", "below_threshold_main", "heater_only", "below_threshold_total"])
def test_activity_flag_does_not_replace_real_active_main_watts(case):
    view = observation()
    power = view["power_activity"]
    if case == "bad_threshold":
        power["threshold_w"] = None
    elif case == "below_threshold_main":
        power["supplies"][0]["watts"] = 199
    elif case == "heater_only":
        power["activity_kind"] = "heater"
    else:
        power["total_w"] = 0
    assert classify(view)["context"] == CONTEXT_UNKNOWN


def test_selected_programme_without_electrical_task_proof_remains_unknown():
    view = observation(active=False)
    view["native_task"] = {"function": None, "source": "none", "observed_at": None}
    assert classify(view)["context"] == CONTEXT_UNKNOWN


def test_active_unresolved_or_partial_watts_never_train_normal_household_demand():
    view = observation()
    view.update(context=CONTEXT_NORMAL, context_reliable=True)
    view["power_activity"]["function"] = None
    assert classify(view)["context"] == CONTEXT_UNKNOWN
    view["power_activity"].update(state="partial", active=False, complete=False)
    assert classify(view)["context"] == CONTEXT_UNKNOWN


def test_confirmed_idle_and_complete_inactive_measurement_can_train_normal_context():
    result = classify(observation(active=False))
    assert result["context"] == CONTEXT_NORMAL and result["tier"] == "inactive"
    assert result["model_eligible"]


@pytest.mark.parametrize("stamp", [None, "bad", False, 879])
def test_bad_inactive_meter_timestamp_cannot_create_a_normal_episode(stamp):
    view = observation(active=False)
    view["power_activity"]["observed_at"] = stamp
    assert classify(view)["context"] == CONTEXT_UNKNOWN


def test_explicit_all_off_native_guard_keeps_household_learning_without_a_hp_meter():
    view = {"configured": True, "source_stale_s": 120, "context": CONTEXT_NORMAL,
            "context_reliable": True, "context_stamp": 990, "native_task": {}, "power_activity": {}}
    assert classify(view)["context"] == CONTEXT_NORMAL
    view["context_reliable"] = False
    assert classify(view)["context"] == CONTEXT_UNKNOWN


def test_unconfigured_heatpump_keeps_existing_household_sampling():
    assert classify({"configured": False})["context"] == CONTEXT_NORMAL


def feed(model, start, context, watts, *, day="2026-01-01", evidence="confirmed", count=5):
    return any([model.observe(start + i * 5, day, context, watts, evidence=evidence) for i in range(count)])


def test_old_samples_and_days_remain_archived_without_unverified_planning_weight():
    legacy = {"schema": 1, "samples": {CONTEXT_HEATING: [2400, 2450, 2380, 2430]},
              "days": {CONTEXT_HEATING: ["2026-01-01", "2026-01-02"]}, "unknown_observations": 17}
    model = HeatPumpActivityModel()
    assert model.restore(legacy)
    saved = model.snapshot()
    assert saved["samples"][CONTEXT_HEATING] == legacy["samples"][CONTEXT_HEATING]
    assert saved["days"][CONTEXT_HEATING] == legacy["days"][CONTEXT_HEATING]
    assert saved["unknown_observations"] == 17
    assert model.estimate(CONTEXT_HEATING).watts is None
    assert model.overview()["historical_samples"][CONTEXT_HEATING] == 4


def test_derived_examples_are_bounded_separate_and_cannot_create_planning_watts():
    model = HeatPumpActivityModel()
    for i in range(100):
        model.observe(i * 5, "2026-01-01", CONTEXT_DHW, 2500, evidence="derived",
                      detail={"source": "aquarea_entity", "kind": "tank_route", "observed_at": i * 5})
    assert model.derived_observations[CONTEXT_DHW] == 100
    assert len(model.derived_examples) == 40
    assert model.samples[CONTEXT_DHW] == model.confirmed_samples[CONTEXT_DHW] == []
    assert model.estimate(CONTEXT_DHW).watts is None
    assert model.unknown_observations == 0
    restored = HeatPumpActivityModel()
    assert restored.restore(model.snapshot())
    assert restored.snapshot() == model.snapshot()


@pytest.mark.parametrize("evidence", ["derived", "unknown"])
def test_derived_or_unknown_evidence_cannot_bridge_a_confirmed_start(evidence):
    model = HeatPumpActivityModel()
    feed(model, 0, CONTEXT_NORMAL, 600)
    model.observe(25, "2026-01-01", CONTEXT_HEATING, 3000)
    model.observe(30, "2026-01-01", CONTEXT_HEATING, 3000, evidence=evidence)
    assert not feed(model, 35, CONTEXT_HEATING, 3000)
    assert model.confirmed_samples[CONTEXT_HEATING] == []


def test_invalid_measured_power_interrupts_transition_evidence():
    model = HeatPumpActivityModel()
    feed(model, 0, CONTEXT_NORMAL, 600)
    model.observe(25, "2026-01-01", CONTEXT_HEATING, 3000)
    model.observe(30, "2026-01-01", CONTEXT_HEATING, None)
    assert not feed(model, 35, CONTEXT_HEATING, 3000)


def test_confirmed_transitions_still_gain_planning_weight_after_repeated_days():
    model = HeatPumpActivityModel()
    for n, day in enumerate(("2026-01-01", "2026-01-02")):
        start = n * 86400
        feed(model, start, CONTEXT_NORMAL, 600, day=day)
        assert feed(model, start + 25, CONTEXT_HEATING, 3000, day=day)
        assert feed(model, start + 50, CONTEXT_NORMAL, 600, day=day)
    assert model.estimate(CONTEXT_HEATING).watts == 2400
    restored = HeatPumpActivityModel()
    assert restored.restore(model.snapshot())
    assert restored.estimate(CONTEXT_HEATING) == model.estimate(CONTEXT_HEATING)
    assert not restored.overview()["realtime_headroom_uses_estimate"]


def test_optional_corrupt_provenance_does_not_erase_older_model_records():
    model = HeatPumpActivityModel()
    assert model.restore({"schema": 1, "samples": {CONTEXT_HEATING: [2400]},
        "days": {CONTEXT_HEATING: ["2026-01-01"]}, "confirmed_samples": 42,
        "confirmed_days": {CONTEXT_HEATING: None}, "derived_observations": "bad", "derived_examples": 42})
    assert model.samples[CONTEXT_HEATING] == [2400]
    assert model.days[CONTEXT_HEATING] == {"2026-01-01"}
    assert model.estimate(CONTEXT_HEATING).watts is None


def test_hub_records_derived_task_separately_and_never_trains_household_or_native_model():
    runtime, hass = metered()
    view = observation()
    delta = time.time() - NOW
    for item in (view["native_task"], view["task_context"], view["power_activity"], *view["power_activity"]["supplies"]):
        for key in ("observed_at", "context_observed_at"):
            if key in item:
                item[key] += delta
    view["context_stamp"] += delta
    runtime.panasonic.overview = lambda: deepcopy(view)
    settings = deepcopy(runtime.settings)
    sample = runtime.learning_hub.observe(datetime.now(timezone.utc), time.monotonic())
    assert sample["context"] == CONTEXT_DHW and sample["context_evidence"]["tier"] == "derived"
    assert runtime.unified_planner.base_load.accepted == 0
    assert runtime.heatpump_learning.derived_observations[CONTEXT_DHW] == 1
    assert runtime.heatpump_learning.confirmed_samples[CONTEXT_DHW] == []
    assert next(iter(runtime.learning_hub.days.values())) == {"heatpump_derived_tapwater_heating": 1}
    assert settings == runtime.settings and not hass.services.calls
