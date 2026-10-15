"""Pinned provider mapping composition: fictional contexts, no live controls."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.display_operation import classify_display_operation
from custom_components.solar_pilot.heatpump_learning import classify_heatpump_observation
from test_display_operation82 import NOW, snapshot


def contract_snapshot(*, mode="heating", route="PUMP", pump="on", zone=True, tank=False, raw="OFF", main=1300):
    p = snapshot(main=main, selected="space_heating" if mode == "heating" else "space_cooling", tank="idle" if route == "PUMP" else "heating")
    p["native_task"].update(inactive=True, inactive_action="off", inactive_scope="global", verified_global_off=True,
                            independent_tank_on=False, function=None)
    p["display_tank"]["observed_at"] = NOW-3
    p["source_contract"] = {"schema": 1, "read_only": True, "status": "verified", "provider_loaded": True,
        "native_device_registered": True, "contract_id": "aioaquarea_ng_1_3_1_special_status", "action_semantics": "special_status",
        "provider": {"integration_domain": "aquarea", "integration_version": "1.5.2", "library_distribution": "aioaquarea-ng", "library_version": "1.3.1"},
        "observed_at": NOW-1, "stale_s": 120, "raw_device_action": raw,
        "pump": {"state": pump, "observed_at": NOW-2},
        "direction": {"state": route, "observed_at": NOW-2},
        "program": {"state": mode, "raw_mode": "HEAT" if mode == "heating" else "COOL", "observed_at": NOW-1},
        "tank": {"enabled": tank, "observed_at": NOW-1},
        "zones": [{"enabled": zone, "state": "heat" if mode == "heating" else "cool", "observed_at": NOW-3}]}
    return p


def display(p):
    before = deepcopy(p)
    model_before = classify_heatpump_observation(p, now_wall=NOW)
    result = classify_display_operation(p, now_wall=NOW)
    assert p == before
    assert classify_heatpump_observation(p, now_wall=NOW) == model_before
    assert result["model_eligible"] is False and result["read_only"] is True
    return result


@pytest.mark.parametrize("mode,function", [("heating", "space_heating"), ("cooling", "space_cooling")])
@pytest.mark.parametrize("raw", ["OFF", "HEATING", "COOLING"])
@pytest.mark.parametrize("version", ["1.5.2", "1.5.3", "1.5.4"])
def test_known_specialstatus_mapping_has_same_derived_task_for_zero_eco_and_comfort(mode, function, raw, version):
    p = contract_snapshot(mode=mode, raw=raw)
    p["source_contract"]["provider"]["integration_version"] = version
    if raw != "OFF":
        p["native_task"].update(function=function, inactive=False, verified_global_off=False)
    result = display(p)
    assert result["function"] == function and result["tier"] == "derived"
    assert result["source"] == "aquarea_contract" and result["kind"] == "coherent_native_context"
    assert result["valid_until"] == NOW-5+120
    assert result["context_report_skew_s"] == 2
    assert p["native_task"] == deepcopy(p["native_task"])


@pytest.mark.parametrize("raw", ["OFF", "HEATING", "COOLING"])
def test_pump_off_cannot_become_confirmed_task_via_sdk_preset_action(raw):
    p = contract_snapshot(pump="off", raw=raw)
    if raw != "OFF":
        p["native_task"].update(function="space_heating", inactive=False, verified_global_off=False)
    result = display(p)
    assert result["function"] is None and result["reason_code"] == "pump_not_on"
    assert result["active"] is True  # The independent positive meter stays activity evidence.


@pytest.mark.parametrize("problem", ["tank_active", "tank_old", "pump_old", "zone_off", "zone_unknown", "zone_old", "zone_wrong_direction", "zone_malformed", "programme_auto", "route_idle", "missing_main", "skew", "native_conflict"])
def test_space_direction_requires_every_fresh_coherent_independent_component(problem):
    p = contract_snapshot()
    c = p["source_contract"]
    if problem == "tank_active":p["display_tank"]["mode"] = "heating"
    elif problem == "tank_old":p["display_tank"]["observed_at"] = NOW-121
    elif problem == "pump_old":c["pump"]["observed_at"] = NOW-121
    elif problem == "zone_off":c["zones"][0]["enabled"] = False
    elif problem == "zone_unknown":c["zones"][0]["enabled"] = None
    elif problem == "zone_old":c["zones"][0]["observed_at"] = NOW-121
    elif problem == "zone_wrong_direction":c["zones"][0]["state"] = "cool"
    elif problem == "zone_malformed":c["zones"].append("unexpected")
    elif problem == "programme_auto":c["program"]["state"] = "auto"
    elif problem == "route_idle":c["direction"]["state"] = "IDLE"
    elif problem == "missing_main":p["power_activity"]["supplies"][0]["role"] = "unconfirmed"
    elif problem == "skew":p["display_tank"]["observed_at"] = NOW-35
    else:p["native_task"]["conflict"] = True
    result = display(p)
    assert result["function"] is None and result["tier"] == "unknown"
    assert result["reason_code"] and result["action"]
    if problem == "skew":assert result["context_report_skew_s"] == 34


@pytest.mark.parametrize("problem", [None, "tank_off", "tank_old", "pump_off", "wrong_route", "no_active_feed"])
def test_dhw_requires_tank_own_on_water_and_pump_plus_assigned_active_feed(problem):
    p = contract_snapshot(route="WATER", tank=True)
    if problem == "tank_off":p["source_contract"]["tank"]["enabled"] = False
    elif problem == "tank_old":p["source_contract"]["tank"]["observed_at"] = NOW-121
    elif problem == "pump_off":p["source_contract"]["pump"]["state"] = "off"
    elif problem == "wrong_route":p["source_contract"]["direction"]["state"] = "PUMP"
    elif problem == "no_active_feed":p["power_activity"]["supplies"][0]["watts"] = 30
    result = display(p)
    assert result["function"] == ("tapwater_heating" if problem is None else None)
    assert result["tier"] == ("derived" if problem is None else "unknown")


@pytest.mark.parametrize("problem", ["unknown_version", "other_library", "old_library", "mapping_unknown", "metadata_refresh", "unknown_contract_id", "wrong_semantics", "not_read_only"])
def test_unknown_contract_never_lifts_correct_off_or_trusts_positive_sdk_action(problem):
    p = contract_snapshot(raw="HEATING")
    p["native_task"].update(function="space_heating", inactive=False, verified_global_off=False)
    c = p["source_contract"]
    if problem == "unknown_version":c["provider"]["integration_version"] = "1.5.5"
    elif problem == "other_library":c["provider"]["library_distribution"] = "aioaquarea"
    elif problem == "old_library":c["provider"]["library_version"] = "1.3.0"
    elif problem in ("mapping_unknown", "metadata_refresh"):
        c["status"] = "unknown"
        if problem == "metadata_refresh":c["provider"] = {}
    elif problem == "unknown_contract_id":c["contract_id"] = "unverified"
    elif problem == "wrong_semantics":c["action_semantics"] = "main_status"
    else:c["read_only"] = False
    result = display(p)
    assert result["function"] is None


def test_independently_correct_native_off_is_still_veto_without_suspect_contract():
    p = contract_snapshot()
    p.pop("source_contract")
    result = display(p)
    assert result["function"] is None and result["tier"] == "unknown"


def test_verified_defrost_keeps_priority_over_contract_mapping_or_heating():
    p = contract_snapshot()
    p["source_contract"]["status"] = "unknown"
    p["defrost"] = {"state": "active", "source": "aquarea_poll", "observed_at": NOW-5, "stale_s": 60}
    result = display(p)
    assert result["function"] == "defrost" and result["tier"] == "confirmed"


@pytest.mark.parametrize("watts", [0, 43.8])
def test_known_contract_unknown_thermal_task_keeps_independent_complete_inactivity(watts):
    p = contract_snapshot(pump="off", main=watts)
    result = display(p)
    assert result["function"] is None and result["active"] is False
    assert result["activity_observed_at"] == NOW-5
    assert result["activity_valid_until"] == NOW-5+120
    p["power_complete"] = False
    p["power_activity"]["supplies"][0].update(valid=False, watts=None)
    result = display(p)
    assert result["active"] is None and result["activity_valid_until"] is None


def test_coherent_sixty_second_provider_poll_stays_derived_with_newer_independent_meter():
    p = contract_snapshot()
    c = p["source_contract"]
    c["observed_at"] = NOW-60
    for row in (c["pump"], c["direction"], c["program"], c["tank"], *c["zones"]):
        row["observed_at"] = NOW-60
    p["display_tank"]["observed_at"] = NOW-60
    p["native_task"]["observed_at"] = NOW-60
    result = display(p)
    assert result["function"] == "space_heating" and result["tier"] == "derived"
    assert result["context_report_skew_s"] == 0
    assert result["measurement_context_skew_s"] == 55
    assert result["valid_until"] == NOW+60
    c["observed_at"] = NOW-121
    assert display(p)["function"] is None


def test_native_context_transition_cannot_mix_old_pump_and_new_direction_even_while_each_fresh():
    p = contract_snapshot()
    p["source_contract"]["pump"]["observed_at"] = NOW-20
    result = display(p)
    assert result["function"] is None and result["reason_code"] == "native_context_report_skew"
    assert result["context_report_skew_s"] == 19


def test_unrelated_tank_idle_cannot_supply_space_task_proof():
    p = contract_snapshot()
    p["source_contract"]["tank"]["entity_id"] = "water_heater.synthetic_aquarea_tank"
    p["display_tank"]["entity_id"] = "water_heater.synthetic_unrelated_tank"
    result = display(p)
    assert result["function"] is None and result["reason_code"] == "native_source_value_conflict"


def test_unrelated_loaded_aquarea_provider_does_not_veto_generic_actual_hvac_action():
    p = snapshot(task="tapwater_heating")
    p["native_task"]["source"] = "native_hvac_action"
    p["source_contract"] = {"schema": 1, "read_only": True, "status": "unknown",
                            "provider_loaded": True, "native_device_registered": False,
                            "reason_code": "native_source_mapping_unverified"}
    result = display(p)
    assert result["function"] == "tapwater_heating" and result["tier"] == "confirmed"
    assert result["source"] == "native_hvac_action"
