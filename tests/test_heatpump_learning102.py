"""Synthetic enablement/physical-evidence boundaries; no private installation."""
from copy import deepcopy
from datetime import datetime, timezone
import math
import time

import pytest

from custom_components.solar_pilot.heatpump_learning import (
    ACTIVE_CONTEXTS, CONTEXT_NORMAL, CONTEXT_UNKNOWN, HeatPumpActivityModel,
    classify_heatpump_observation,
)
from custom_components.solar_pilot.operation_source_evidence import (
    OPERATION_CONTRACT_ID, OPERATION_SEMANTIC_CONTRACT_ID,
)
from test_display_operation83 import NOW, contract_snapshot
from test_learning_hub30 import metered


def enabled_snapshot(*, function="space_heating", pump="on", main=1300, heater=0):
    water = function == "tapwater_heating"
    cooling = function == "space_cooling"
    view = contract_snapshot(mode="cooling" if cooling else "heating", route="WATER" if water else "PUMP",
                             pump=pump, raw="HEATING", tank=water, main=main)
    contract = view["source_contract"]
    contract.update(contract_id=OPERATION_CONTRACT_ID, action_semantics="operation_status",
                    compatibility={"schema": 1, "contract": OPERATION_SEMANTIC_CONTRACT_ID,
                                   "verified": True, "basis": "loaded_source", "fingerprint": "b"*64},
                    device_operation_status="ON", status_data_mode="LIVE",
                    raw_device_action={"space_heating": "HEATING", "space_cooling": "COOLING",
                                       "tapwater_heating": "HEATING_WATER"}[function])
    contract["provider"].update(integration_version="1.8.0", library_version="1.4.0")
    contract["tank"]["entity_id"] = "water_heater.synthetic_tank"
    view["display_tank"]["entity_id"] = "water_heater.synthetic_tank"
    for row in [contract["pump"], contract["direction"], contract["program"], contract["tank"], *contract["zones"]]:
        row["native_observed_at"] = contract["observed_at"]
    view["native_task"].update(function=function, source="aquarea_poll", inactive=False,
                               inactive_action=None, inactive_scope=None, verified_global_off=False,
                               raw_evidence=[{"operation_status_scope": "device_enablement"}])
    view.update(configured=True, program="cooling" if cooling else "heating", context=function,
                context_reliable=True, context_stamp=NOW-3, power_w=main+heater)
    power = view["power_activity"]
    active = main+heater >= power["threshold_w"]
    power.update(total_w=main+heater, active=active, state="active" if active else "off")
    power["supplies"][1]["watts"] = heater
    for row in power["supplies"]:
        row["state"] = "active" if row["watts"] >= power["threshold_w"] else "off"
    return view


def classify(view):
    before = deepcopy(view)
    result = classify_heatpump_observation(view, now_wall=NOW)
    assert view == before
    assert result["model_eligible"] is False
    assert result["tier"] != "confirmed" and result["context"] != CONTEXT_NORMAL
    return result


@pytest.mark.parametrize("function", ["space_heating", "space_cooling", "tapwater_heating"])
def test_coherent_bound_live_execution_is_derived_only(function):
    result = classify(enabled_snapshot(function=function))
    assert result["context"] == function and result["tier"] == "derived"
    assert result["source"] == "aquarea_contract" and result["kind"] == "coherent_native_context"
    assert result["observed_at"] == NOW-5


@pytest.mark.parametrize("watts", [0, 43.8])
@pytest.mark.parametrize("pump", ["off", "unknown"])
def test_off_pump_and_inactive_meter_never_confirm_heat_or_accept_normal_base(watts, pump):
    view = enabled_snapshot(pump=pump, main=watts)
    view.update(context=CONTEXT_NORMAL, context_reliable=True, context_stamp=NOW-1)
    assert classify(view)["context"] == CONTEXT_UNKNOWN


@pytest.mark.parametrize("case", [
    "contract_missing", "proof_missing", "proof_wrong", "proof_false", "fingerprint", "schema_bool",
    "not_loaded", "not_registered", "not_verified", "not_readonly", "cached", "quality_missing",
    "poll_old", "poll_future", "native_old", "native_unqualified", "native_inactive", "global_off",
    "pump_off", "pump_missing", "pump_old", "route_idle", "raw_off", "status_unknown", "mode_mismatch",
    "tank_wrong_binding", "tank_active", "tank_old", "zone_disabled", "zone_wrong_direction",
    "context_skew", "conflict", "defrost", "native_wrong_function",
])
def test_missing_changed_stale_or_conflicting_original_evidence_remains_unknown(case):
    view = enabled_snapshot()
    contract, native = view["source_contract"], view["native_task"]
    if case == "contract_missing": view.pop("source_contract")
    elif case == "proof_missing": contract.pop("compatibility")
    elif case == "proof_wrong": contract["compatibility"]["contract"] = "unreviewed"
    elif case == "proof_false": contract["compatibility"]["verified"] = False
    elif case == "fingerprint": contract["compatibility"]["fingerprint"] = "wrong"
    elif case == "schema_bool": contract["schema"] = True
    elif case == "not_loaded": contract["provider_loaded"] = False
    elif case == "not_registered": contract["native_device_registered"] = False
    elif case == "not_verified": contract["status"] = "unknown"
    elif case == "not_readonly": contract["read_only"] = False
    elif case == "cached": contract["status_data_mode"] = "CACHED"
    elif case == "quality_missing": contract.pop("status_data_mode")
    elif case == "poll_old": contract["observed_at"] = NOW-121
    elif case == "poll_future": contract["observed_at"] = NOW+6
    elif case == "native_old": native["observed_at"] = NOW-121
    elif case == "native_unqualified": native["source"] = "native_hvac_action"
    elif case == "native_inactive": native["inactive"] = True
    elif case == "global_off": native["verified_global_off"] = True
    elif case == "pump_off": contract["pump"]["state"] = "off"
    elif case == "pump_missing": contract.pop("pump")
    elif case == "pump_old": contract["pump"]["observed_at"] = NOW-121
    elif case == "route_idle": contract["direction"]["state"] = "IDLE"
    elif case == "raw_off": contract["raw_device_action"] = "OFF"
    elif case == "status_unknown": contract["device_operation_status"] = "UNKNOWN"
    elif case == "mode_mismatch": contract["program"]["raw_mode"] = "COOL"
    elif case == "tank_wrong_binding": view["display_tank"]["entity_id"] = "water_heater.other_tank"
    elif case == "tank_active": view["display_tank"]["mode"] = "heating"
    elif case == "tank_old": view["display_tank"]["observed_at"] = NOW-121
    elif case == "zone_disabled": contract["zones"][0]["enabled"] = False
    elif case == "zone_wrong_direction": contract["zones"][0]["state"] = "cool"
    elif case == "context_skew": contract["pump"]["observed_at"] = NOW-20
    elif case == "conflict": native["conflict"] = True
    elif case == "defrost": view["defrost"] = {"state": "active", "source": "aquarea_poll", "observed_at": NOW-1}
    elif case == "native_wrong_function": native["function"] = "tapwater_heating"
    assert classify(view)["context"] == CONTEXT_UNKNOWN


@pytest.mark.parametrize("case", [
    "partial", "partial_flag", "no_rows", "one_feed", "duplicate", "number_bool", "feed_missing",
    "feed_old", "aux_old", "short_expiry", "meter_old", "meter_future", "meter_estimate", "scope_unknown",
    "wrong_total", "wrong_power_total", "wrong_individual", "wrong_individual_time", "invalid_individual",
    "negative", "bool", "nan", "inf", "huge", "string", "timestamp_bool", "timestamp_nan", "timestamp_huge",
])
def test_learning_keeps_complete_finite_current_consistent_whole_meter_boundary(case):
    view = enabled_snapshot()
    power = view["power_activity"]
    rows = power["supplies"]
    if case == "partial": view.update(power_complete=False, power_w=None); power.update(complete=False, total_w=None)
    elif case == "partial_flag": power["complete"] = False
    elif case == "no_rows": power["supplies"] = []
    elif case == "one_feed": power["supplies"] = rows[:1]
    elif case == "duplicate": rows[1]["number"] = 1
    elif case == "number_bool": rows[0]["number"] = True
    elif case == "feed_missing": rows[1].update(valid=False, watts=None)
    elif case == "feed_old": rows[0]["observed_at"] = NOW-121
    elif case == "aux_old": rows[1]["observed_at"] = NOW-121
    elif case == "short_expiry": power["stale_s"] = 1
    elif case == "meter_old": view["power_observed_at"] = NOW-121
    elif case == "meter_future": view["power_observed_at"] = NOW+6
    elif case == "meter_estimate": view["power_kind"] = "estimated"
    elif case == "scope_unknown": view["power_scope"] = "unconfirmed"
    elif case == "wrong_total": view["power_w"] = 1600; power["total_w"] = 1600
    elif case == "wrong_power_total": power["total_w"] = 1600
    elif case == "wrong_individual": view["power_supply2_w"] = 10
    elif case == "wrong_individual_time": view["power_supply2_observed_at"] = NOW-3
    elif case == "invalid_individual": view["power_supply2_valid"] = False
    elif case in ("negative", "bool", "nan", "inf", "huge", "string"):
        rows[0]["watts"] = {"negative": -1, "bool": True, "nan": math.nan, "inf": math.inf,
                            "huge": 10**1000, "string": "1300"}[case]
    elif case.startswith("timestamp_"):
        rows[0]["observed_at"] = {"timestamp_bool": True, "timestamp_nan": math.nan,
                                  "timestamp_huge": 10**1000}[case]
    assert classify(view)["context"] == CONTEXT_UNKNOWN


@pytest.mark.parametrize("clue", ["contract_id", "action_semantics", "capability", "raw_scope", "native_scope"])
def test_every_explicit_new_contract_clue_closes_legacy_fallback(clue):
    view = enabled_snapshot(pump="off", main=0)
    contract = view.pop("source_contract")
    view["native_task"].pop("raw_evidence")
    if clue in ("contract_id", "action_semantics"):
        view["source_contract"] = {clue: contract[clue]}
    elif clue == "capability": view["source_contract"] = {"compatibility": contract["compatibility"]}
    elif clue == "raw_scope": view["native_task"]["raw_evidence"] = [{"operation_status_scope": "device_enablement"}]
    else: view["native_task"]["operation_status_scope"] = "unverified"
    assert classify(view)["context"] == CONTEXT_UNKNOWN


def test_cached_display_metadata_cannot_grant_or_withhold_derived_evidence():
    view = enabled_snapshot(pump="off", main=0)
    view["operation_display"] = {"context": "space_heating", "function": "space_heating", "tier": "confirmed",
                                 "active": True, "model_eligible": True, "reason_code": "coherent_native_context"}
    assert classify(view)["context"] == CONTEXT_UNKNOWN
    view = enabled_snapshot()
    view["operation_display"] = {"context": CONTEXT_UNKNOWN, "active": False, "model_eligible": False}
    assert classify(view)["tier"] == "derived"


@pytest.mark.parametrize("stale", [True, None, 0, -1, math.inf, math.nan, 10**1000, "120"])
def test_invalid_original_freshness_policy_does_not_become_a_default_permission(stale):
    view = enabled_snapshot()
    view["source_stale_s"] = stale
    assert classify(view)["context"] == CONTEXT_UNKNOWN


@pytest.mark.parametrize("with_contract", [False, True])
@pytest.mark.parametrize("source", ["native_hvac_action", "aquarea_poll"])
def test_legacy_native_action_confirmation_stays_unchanged(with_contract, source):
    view = contract_snapshot(raw="HEATING", main=0, pump="off")
    view["native_task"].update(function="space_heating", source=source, inactive=False, verified_global_off=False)
    if not with_contract: view.pop("source_contract")
    result = classify_heatpump_observation(view, now_wall=NOW)
    assert result["context"] == "space_heating" and result["tier"] == "confirmed" and result["model_eligible"] is True


def test_diagnostic_derivation_never_creates_confirmed_power_steps_or_rewrites_restored_samples():
    model = HeatPumpActivityModel()
    old = {"samples": {"space_heating": [900]}, "days": {"space_heating": ["2026-10-01"]}}
    model.restore(old)
    saved = deepcopy(model.samples)
    result = classify(enabled_snapshot())
    for index in range(100):
        assert model.observe(NOW+index*5, "2026-10-20", result["context"], 1600,
                             evidence=result["tier"], detail=result) is False
    assert model.samples == saved and model.confirmed_samples["space_heating"] == []
    assert model.derived_observations["space_heating"] == 100


@pytest.mark.parametrize("active", [False, True])
def test_actual_learning_hub_keeps_base_excluded_and_controller_unchanged(active):
    runtime, hass = metered()
    view = enabled_snapshot(pump="on" if active else "off", main=1300 if active else 0)
    wall, delta = time.time(), time.time()-NOW
    def shift(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.endswith("observed_at") or key.endswith("_stamp"):
                    if isinstance(item, (int, float)) and not isinstance(item, bool): value[key] += delta
                else: shift(item)
        elif isinstance(value, list):
            for item in value: shift(item)
    shift(view)
    runtime.panasonic.overview = lambda: deepcopy(view)
    before = deepcopy((runtime.entry.options, runtime.sg_boost.snapshot(), runtime.heatpump_learning.samples))
    sampled = runtime.learning_hub.observe(datetime.fromtimestamp(wall, timezone.utc), time.monotonic())
    assert sampled["valid"] is True
    assert sampled["context"] == ("space_heating" if active else CONTEXT_UNKNOWN)
    assert sampled["context_evidence"]["tier"] == ("derived" if active else "unknown")
    assert sampled["context_evidence"]["model_eligible"] is False
    assert runtime.unified_planner.base_load.accepted == 0
    assert (runtime.entry.options, runtime.sg_boost.snapshot(), runtime.heatpump_learning.samples) == before
    assert not hass.services.calls
