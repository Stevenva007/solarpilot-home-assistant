"""Synthetic proof boundaries for display-only thermal task recognition."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.display_operation import classify_display_operation
from custom_components.solar_pilot.heatpump_learning import classify_heatpump_observation

NOW = 1791960000.0


def snapshot(*, main=1300, heater=0, complete=True, task=None, selected="space_heating", tank="idle"):
    return {"configured": True, "source_stale_s": 120,
        "native_task": {"function": task, "source": "aquarea_poll", "observed_at": NOW-3,
                        "stale_s": 120, "inactive": not bool(task), "inactive_action": "idle"},
        "task_context": {"function": selected, "source": "aquarea_entity" if selected == "tapwater_heating" else "native_program",
                         "kind": "tank_route" if selected == "tapwater_heating" else "selected_program", "observed_at": NOW-7, "stale_s": 120},
        "display_tank": {"available": True, "observed_at": NOW-9, "mode": tank},
        "power_kind": "measured", "power_scope": "split", "power_complete": complete,
        "power_w": main+heater if complete else None, "power_observed_at": NOW-1,
        "power_activity": {"state": "active" if complete else "partial", "active": True,
            "complete": complete, "total_w": main+heater if complete else None,
            "observed_at": NOW-1, "threshold_w": 200, "stale_s": 120,
            "supplies": [{"number": 1, "role": "main", "watts": main, "valid": True, "observed_at": NOW-5},
                         {"number": 2, "role": "heater", "watts": heater, "valid": True, "observed_at": NOW-2}]}}


def classify(p):
    before = deepcopy(p)
    result = classify_display_operation(p, now_wall=NOW)
    assert p == before
    assert result["model_eligible"] is False and result["read_only"] is True
    return result


@pytest.mark.parametrize("task", ["space_heating", "space_cooling", "tapwater_heating"])
def test_native_task_survives_heater_only_and_incomplete_total(task):
    p = snapshot(main=50, heater=2200, complete=False, task=task)
    r = classify(p)
    assert r["function"] == task and r["tier"] == "confirmed"
    assert r["support"]["active"] is True and r["support"]["watts"] == 2200
    assert r["valid_until"] == NOW-3+120
    assert p["power_complete"] is False and p["power_w"] is None


@pytest.mark.parametrize("complete", [True, False])
def test_exact_fresh_tank_route_with_heater_is_derived_only(complete):
    p = snapshot(main=40, heater=2400, complete=complete, selected="tapwater_heating", tank="heating")
    r = classify(p)
    assert r["function"] == "tapwater_heating" and r["tier"] == "derived"
    assert r["support"]["active"] is True
    assert r["observed_at"] == NOW-7 and r["valid_until"] == NOW-7+120
    assert classify_heatpump_observation(p, now_wall=NOW)["tier"] == "unknown"


@pytest.mark.parametrize("selected", ["space_heating", "space_cooling"])
def test_fresh_main_partial_and_explicit_tank_idle_can_display_direction(selected):
    p = snapshot(complete=False, selected=selected)
    p["power_activity"]["supplies"][1].update(valid=False, watts=None)
    r = classify(p)
    assert r["function"] == selected and r["tier"] == "derived"
    assert r["observed_at"] == NOW-9 and r["valid_until"] == NOW-9+120
    assert r["support"]["active"] is None and p["power_w"] is None
    assert classify_heatpump_observation(p, now_wall=NOW)["tier"] == "unknown"


@pytest.mark.parametrize("condition", ["tank_missing", "tank_old", "tank_heating", "tank_unknown", "context_old", "main_old", "role_unknown", "heater_only"])
def test_selected_programme_never_invents_actual_direction(condition):
    p = snapshot()
    if condition == "tank_missing":p.pop("display_tank")
    if condition == "tank_old":p["display_tank"]["observed_at"] = NOW-121
    if condition == "tank_heating":p["display_tank"]["mode"] = "heating"
    if condition == "tank_unknown":p["display_tank"]["mode"] = "unknown"
    if condition == "context_old":p["task_context"]["observed_at"] = NOW-121
    if condition == "main_old":p["power_activity"]["supplies"][0]["observed_at"] = NOW-121
    if condition == "role_unknown":p["power_activity"]["supplies"][0]["role"] = "unconfirmed"
    if condition == "heater_only":p = snapshot(main=30, heater=2200)
    r = classify(p)
    assert r["function"] is None and r["tier"] == "unknown"


@pytest.mark.parametrize("condition", ["global_off", "conflict", "unscoped_off", "route_old", "route_wrong_source", "heater_old", "negative", "bool", "stamp_string"])
def test_tank_route_cannot_overcome_veto_or_bad_originals(condition):
    p = snapshot(main=30, heater=2400, selected="tapwater_heating", tank="heating")
    if condition == "global_off":p["native_task"].update(inactive_action="off", inactive_scope="global", verified_global_off=True)
    if condition == "conflict":p["native_task"]["conflict"] = True
    if condition == "unscoped_off":p["native_task"].update(inactive_action="off", inactive_scope="unknown")
    if condition == "route_old":p["task_context"]["observed_at"] = NOW-121
    if condition == "route_wrong_source":p["task_context"]["source"] = "native_mode"
    if condition == "heater_old":p["power_activity"]["supplies"][1]["observed_at"] = NOW-121
    if condition == "negative":p["power_activity"]["supplies"][1]["watts"] = -2400
    if condition == "bool":p["power_activity"]["supplies"][1]["watts"] = True
    if condition == "stamp_string":p["task_context"]["observed_at"] = str(NOW-7)
    assert classify(p)["function"] is None


def test_scoped_space_off_allows_only_tank_route_and_earliest_original_deadline():
    p = snapshot(main=30, heater=2400, selected="tapwater_heating", tank="heating")
    p["native_task"].update(inactive_action="off", inactive_scope="space_circuit", independent_tank_on=True, observed_at=NOW-110)
    r = classify(p)
    assert r["function"] == "tapwater_heating" and r["valid_until"] == NOW+10
    p["task_context"].update(function="space_heating", kind="selected_program", source="native_program")
    p["display_tank"]["mode"] = "idle"
    assert classify(p)["function"] is None


def test_defrost_wins_over_reported_heating_without_compressor_or_sg_claim():
    p = snapshot(task="space_heating")
    p["defrost"] = {"state": "active", "source": "aquarea_poll", "observed_at": NOW-30, "stale_s": 60}
    r = classify(p)
    assert r["function"] == "defrost" and r["label"] == "Ontdooien"
    assert r["valid_until"] == NOW+30
    assert "compressor_running" not in r and "sg_effect_confirmed" not in r


def test_native_direction_wins_over_opposite_selected_programme():
    assert classify(snapshot(task="space_cooling", selected="space_heating"))["function"] == "space_cooling"


def test_missing_feed_does_not_prove_support_off():
    p = snapshot(complete=False)
    p["power_activity"]["supplies"][1].update(watts=None, valid=False)
    assert classify(p)["support"]["active"] is None


def test_thermal_task_can_expire_while_support_remains_current():
    p = snapshot(main=40, heater=2400, task="tapwater_heating")
    p["native_task"]["observed_at"] = NOW-121
    p["task_context"]["observed_at"] = NOW-121
    r = classify(p)
    assert r["function"] is None and r["active"] is True and r["support"]["active"] is True


def test_activity_uses_latest_still_proving_feed_while_task_uses_oldest_required_context():
    p = snapshot(main=1400, heater=2400, selected="tapwater_heating", tank="heating")
    p["power_activity"]["supplies"][0]["observed_at"] = NOW-115
    r = classify(p)
    assert r["valid_until"] == NOW+5
    assert r["activity_observed_at"] == NOW-2 and r["activity_valid_until"] == NOW+118


def test_contradictory_global_off_cannot_claim_whole_device_off_without_meter():
    p = snapshot(main=0, heater=0, complete=False)
    p["native_task"].update(inactive_action="off", inactive_scope="global", verified_global_off=True, independent_tank_on=True)
    r = classify(p)
    assert r["active"] is None and r["tier"] == "unknown"


def test_one_unknown_assigned_heater_does_not_make_other_zero_a_complete_support_off():
    p = snapshot(main=0, heater=0, complete=False)
    p["power_activity"]["supplies"][0].update(role="heater", valid=False, watts=None)
    r = classify(p)
    assert r["support"]["active"] is None and r["support"]["watts"] is None
    p["power_activity"]["supplies"][1]["watts"] = 1000
    r = classify(p)
    assert r["support"]["active"] is True and r["support"]["watts"] is None


def test_duplicate_split_feeds_cannot_prove_complete_zero_or_direction():
    p = snapshot(main=0, heater=0)
    p["power_activity"].update(state="off", active=False)
    p["power_activity"]["supplies"].append(deepcopy(p["power_activity"]["supplies"][1]))
    r = classify(p)
    assert r["active"] is None and r["support"]["active"] is None


def test_real_monitor_publishes_same_display_classifier_without_device_commands():
    from test_runtime import build
    runtime, hass = build()
    runtime.panasonic.update_config({"tank_target_entity": "water_heater.synthetic_tank",
                                    "tank_temperature_entity": "water_heater.synthetic_tank"})
    hass.states.set("water_heater.synthetic_tank", "heating", {"current_temperature": 46, "temperature": 50,
                                                               "hvac_action": "heating", "operation_mode": "heating", "temperature_unit": "°C"})
    p = runtime.panasonic.overview()
    assert p["operation_display"]["function"] == "tapwater_heating"
    assert p["operation_display"]["tier"] == "confirmed"
    assert p["operation_display"]["model_eligible"] is False
    assert p["display_tank"]["temperature_c"] == 46 and p["display_tank"]["target_c"] == 50
    assert not hass.services.calls


def test_display_clock_is_live_but_excluded_from_recorder_attribute_copy():
    from test_runtime import build
    from test_sensor_recorder59 import sensor
    from test_switch_recorder60 import recorded
    runtime, _hass = build()
    entity = sensor(runtime, "panasonic_power")
    live = entity.extra_state_attributes
    assert "operation_display" in live
    assert "operation_display" not in recorded(entity, live)


@pytest.mark.parametrize("watts", [(0, 0), (150, 100)])
def test_aggregate_report_cannot_extend_zero_or_sum_only_activity_past_old_split_feed(watts):
    p = snapshot(main=watts[0], heater=watts[1])
    p["power_activity"]["supplies"][0]["observed_at"] = NOW-119
    r = classify(p)
    assert r["activity_valid_until"] == NOW+1
    assert r["active"] is (sum(watts) >= 200)
    if not r["active"]:assert r["valid_until"] == NOW+1


def test_sum_of_heater_watts_has_earliest_deadline_while_on_state_uses_latest_active_feed():
    p = snapshot(main=100, heater=2400)
    p["power_activity"]["supplies"][0].update(role="heater", observed_at=NOW-119)
    r = classify(p)
    assert r["support"]["watts"] == 2500
    assert r["support"]["watts_valid_until"] == NOW+1
    assert r["support"]["active"] is True and r["support"]["valid_until"] == NOW+118


def test_fresh_actual_compressor_frequency_proves_activity_without_guessing_direction():
    p = snapshot(main=0, heater=0, selected=None, tank="unknown")
    p.update(compressor_entity="sensor.synthetic_frequency", compressor_frequency_hz=40, compressor_frequency_observed_at=NOW-4)
    r = classify(p)
    assert r["active"] is True and r["function"] is None
    assert r["activity_valid_until"] == NOW+116
    p["compressor_frequency_observed_at"] = NOW-121
    assert classify(p)["active"] is False


def test_inconsistent_original_feed_and_display_summary_cannot_supply_direction_or_zero():
    p = snapshot(main=0, heater=0)
    p.update(power_supply1_w=1800, power_supply1_valid=True, power_supply1_observed_at=NOW-5)
    r = classify(p)
    assert r["active"] is None and r["function"] is None
