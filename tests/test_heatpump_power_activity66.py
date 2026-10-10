"""Electrical/task presentation cannot become native or SG control evidence."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from custom_components.solar_pilot.power_activity import POWER_NOTE, power_activity
from test_sg_observations64 import observed, split


def complete(watts=1200, stamp=999):
    return {"valid": True, "complete": True, "watts": watts,
            "measured_wall": stamp, "meter_scope": "total", "supplies": {}}


def task_display(*, watts=1200, config=None, tank_state="idle", tank_attrs=None,
                 tank_stamp=990, tank_entity="water_heater.tank", **context):
    return power_activity(complete(watts), {"stale_s": 120, **(config or {})},
        tank=SimpleNamespace(state=tank_state, attributes=tank_attrs or {}),
        tank_entity=tank_entity, tank_stamp=tank_stamp, now_wall=1000, **context)


@pytest.mark.parametrize("watts,state,label", [(0, "off", "Geen elektrisch verbruik"),
    (0.01, "basis", "Basisverbruik"), (58, "basis", "Basisverbruik"),
    (199.99, "basis", "Basisverbruik"), (200, "active", "Warmtepomp werkt"),
    (5000, "active", "Warmtepomp werkt")])
def test_complete_power_inclusive_threshold_and_actual_zero(watts, state, label):
    view = power_activity(complete(watts), {}, now_wall=1000)
    assert view["state"] == state and view["label"] == label
    assert view["active"] is (state == "active")
    assert view["total_w"] == watts and view["complete"]
    assert view["threshold_w"] == 200 and view["observed_at"] == 999
    assert view["function"] is None and view["context_observed_at"] is None
    assert view["evidence"] == "metered_power" and view["note"] == POWER_NOTE


def test_user_interpretation_threshold_is_independent_from_sg_power_parameters():
    view = power_activity(complete(200), {"power_activity_threshold_w": 400,
        "threshold_w": 2500, "expected_power_w": 3000}, now_wall=1000)
    assert view["state"] == "basis" and view["threshold_w"] == 400
    assert not view["active"] and view["total_w"] == 200


@pytest.mark.parametrize("bad", ["missing", "stale", "unit", "estimated", "restored", "negative", "reserved"])
def test_partial_power_keeps_known_active_feed_without_total_or_task(bad):
    runtime, hass = split(tank_target_entity="water_heater.tank")
    hass.states.set("water_heater.tank", "heating", {"operation_mode": "heating"})
    attrs = {"unit_of_measurement": "A" if bad == "unit" else "W"}
    if bad in ("estimated", "restored"):
        attrs[bad] = True
    if bad == "missing":
        hass.states.data.pop("sensor.hp_supply_two")
    elif bad == "reserved":
        runtime.wallbox_settings["power_entity"] = "sensor.hp_supply_two"
    else:
        hass.states.set("sensor.hp_supply_two", -1 if bad == "negative" else 0,
            attrs, reported_age=121 if bad == "stale" else 0)
    view = runtime.panasonic.overview()["power_activity"]
    assert view["state"] == "partial" and view["active"]
    assert view["label"] == "Actief verbruik op voeding 1"
    assert view["total_w"] is None and not view["complete"]
    assert view["function"] is None and view["context_observed_at"] is None
    first, second = view["supplies"]
    assert first["watts"] == 1400 and first["state"] == "active" and first["valid"]
    assert second["watts"] is None and second["state"] == "unknown" and not second["valid"]
    assert view["observed_at"] == first["observed_at"] and not hass.services.calls


@pytest.mark.parametrize("watts,active", [(0, False), (58, False), (200, True)])
def test_partial_known_zero_or_basis_never_claims_overall_off(watts, active):
    runtime, hass = split()
    hass.states.set("sensor.hp_supply_one", watts, {"unit_of_measurement": "W"})
    hass.states.data.pop("sensor.hp_supply_two")
    view = runtime.panasonic.overview()["power_activity"]
    assert view["state"] == "partial" and view["active"] is active
    assert view["total_w"] is None and view["function"] is None
    assert view["supplies"][0]["state"] == ("active" if active else "off" if watts == 0 else "basis")


@pytest.mark.parametrize("first,second,active", [(120, 120, False), (200, 0, True), (0, 200, True)])
def test_unconfirmed_coverage_does_not_sum_parts_for_the_interpretation_threshold(first, second, active):
    runtime, hass = split()
    runtime.panasonic.settings["split_power_confirmed"] = False
    hass.states.set("sensor.hp_supply_one", first, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp_supply_two", second, {"unit_of_measurement": "W"})
    view = runtime.panasonic.overview()["power_activity"]
    assert view["state"] == "partial" and view["active"] is active
    assert view["total_w"] is None and not view["complete"]
    assert [row["watts"] for row in view["supplies"]] == [first, second]


def test_overlap_does_not_double_a_below_threshold_meter_into_activity_or_a_function():
    runtime, hass = split(tank_target_entity="water_heater.tank")
    runtime.panasonic.settings["power_supply2_entity"] = "sensor.hp_supply_one"
    hass.states.set("sensor.hp_supply_one", 120, {"unit_of_measurement": "W"})
    hass.states.set("water_heater.tank", "heating", {"operation_mode": "heating"})
    view = runtime.panasonic.overview()["power_activity"]
    assert view["state"] == "partial" and not view["active"]
    assert not view["complete"] and view["total_w"] is None and view["function"] is None


def test_kw_conversion_and_oldest_actual_supply_stamp_are_retained():
    runtime, hass = split()
    hass.states.set("sensor.hp_supply_one", 0.15, {"unit_of_measurement": "kW"}, reported_age=35)
    hass.states.set("sensor.hp_supply_two", 0.05, {"unit_of_measurement": "kW"}, reported_age=1)
    view = runtime.panasonic.overview()["power_activity"]
    assert view["total_w"] == 200 and view["active"]
    assert view["observed_at"] == view["supplies"][0]["observed_at"]
    assert [row["watts"] for row in view["supplies"]] == [150, 50]
    first = deepcopy(view)
    assert runtime.panasonic.overview()["power_activity"] == first
    hass.states.set("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"})
    assert runtime.panasonic.overview()["power_activity"]["observed_at"] == first["observed_at"]


@pytest.mark.parametrize("watts,label", [(0, "Elektrische ondersteuning uit (0 W)"),
    (100, "Elektrische ondersteuning verbruikt 100 W"),
    (3000, "Elektrische ondersteuning verbruikt 3000 W")])
def test_explicit_heater_role_describes_only_its_actual_electrical_draw(watts, label):
    runtime, hass = split(power_supply1_role="main", power_supply2_role="heater")
    hass.states.set("sensor.hp_supply_one", 58, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp_supply_two", watts, {"unit_of_measurement": "W"})
    view = runtime.panasonic.overview()
    first, second = view["power_activity"]["supplies"]
    assert first["role"] == "main" and "regeling/pompen" in first["label"]
    assert second["role"] == "heater" and second["label"] == label
    assert view["compressor_running"] is None and view["operation"]["state"] == "unknown"
    assert not view["sg_effect_confirmed"] and not hass.services.calls


def test_unconfirmed_feed_roles_do_not_invent_heater_or_compressor_from_large_watts():
    runtime, hass = split()
    hass.states.set("sensor.hp_supply_two", 3000, {"unit_of_measurement": "W"})
    view = runtime.panasonic.overview()["power_activity"]
    assert all(row["role"] == "unconfirmed" for row in view["supplies"])
    assert all("ondersteuning" not in row["label"] and "compressor" not in row["label"] for row in view["supplies"])


@pytest.mark.parametrize("attrs,state", [({"hvac_action": "heating"}, "on"),
    ({"hvac_action": "preheating"}, "on"), ({"hvac_action": "dhw"}, "on"),
    ({"hvac_action": "hot_water"}, "on")])
def test_fresh_native_tank_task_and_complete_active_power_are_explicitly_derived(attrs, state):
    view = task_display(tank_state=state, tank_attrs=attrs)
    assert view["function"] == "tapwater_heating" and view["label"] == "Sanitair water opwarmen"
    assert view["evidence"] == "metered_power_and_context"
    assert "Afgeleid uit gemeten verbruik en Panasonic-tankmelding" in view["note"]
    assert POWER_NOTE in view["note"]
    assert view["context_observed_at"] == view["observed_at"] == 990


@pytest.mark.parametrize("state,attrs", [("heating", {}), ("on", {"operation_mode": "heating"})])
def test_selected_tank_heating_without_actual_action_is_only_qualified_context(state, attrs):
    view = task_display(tank_state=state, tank_attrs=attrs)
    assert view["function"] is None and view["label"] == "Warmtepomp werkt"
    assert "Tank staat op verwarmen" in view["note"]
    assert view["context_observed_at"] == 990


@pytest.mark.parametrize("bad", [None, "wrong_entity", "stale", "unavailable", "restored", "estimated"])
def test_verified_aquarea_dhw_action_requires_its_exact_current_available_tank_binding(bad):
    proof = {"entity_id": "water_heater.tank", "source": "aquarea_poll", "fresh": True,
             "raw_action": "HEATING_WATER", "action": "tapwater_heating", "observed_at": 970}
    attrs = {"operation_mode": "heating"}
    if bad == "wrong_entity":
        proof["entity_id"] = "water_heater.other_tank"
    elif bad == "stale":
        proof["observed_at"] = 879
    elif bad in ("restored", "estimated"):
        attrs[bad] = True
    view = task_display(tank_state="unavailable" if bad == "unavailable" else "heating",
                        tank_attrs=attrs, tank_action=proof)
    assert view["function"] == ("tapwater_heating" if bad is None else None)
    if bad is None:
        assert view["context_observed_at"] == view["observed_at"] == 970


@pytest.mark.parametrize("raw_action,function,label", [("HEATING", "space_heating", "Ruimte verwarmen"),
    ("COOLING", "space_cooling", "Ruimte koelen")])
def test_whole_aquarea_space_action_is_used_automatically_even_with_idle_auto_zones(raw_action, function, label):
    proof = {"entity_id": "water_heater.tank", "source": "aquarea_poll", "fresh": True,
             "raw_action": raw_action, "action": function, "observed_at": 970}
    view = task_display(tank_state="heating", tank_attrs={"operation_mode": "heating"},
        tank_action=proof, zones=[{"available": True, "action": "off", "observed_at": 980}])
    assert view["function"] == function and view["label"] == label
    assert "Panasonic-bedrijfsactie" in view["note"]
    assert view["context_observed_at"] == view["observed_at"] == 970


@pytest.mark.parametrize("raw_action,action", [("HEATING", "space_cooling"), ("COOLING", "space_heating"),
    ("PUMP", "space_heating"), ("HEATING_WATER", "unknown")])
def test_unknown_or_mismatched_provider_action_cannot_promote_a_selected_tank_mode(raw_action, action):
    proof = {"entity_id": "water_heater.tank", "source": "aquarea_poll", "fresh": True,
             "raw_action": raw_action, "action": action, "observed_at": 970}
    view = task_display(tank_state="heating", tank_attrs={"operation_mode": "heating"}, tank_action=proof)
    assert view["function"] is None and view["label"] == "Warmtepomp werkt"
    assert "Tank staat op verwarmen" in view["note"]


@pytest.mark.parametrize("provider,explicit", [("space_heating", "cooling"), ("space_cooling", "heating")])
def test_verified_provider_space_action_does_not_override_conflicting_actual_zone_action(provider, explicit):
    proof = {"entity_id": "water_heater.tank", "source": "aquarea_poll", "fresh": True,
             "raw_action": "HEATING" if provider == "space_heating" else "COOLING",
             "action": provider, "observed_at": 970}
    view = task_display(tank_action=proof, zones=[{"available": True,
        "action": explicit, "observed_at": 980}])
    assert view["function"] is None and "niet eenduidig" in view["note"]


@pytest.mark.parametrize("case", ["target_only", "stale", "estimated", "restored", "not_native", "below_threshold"])
def test_tank_temperature_target_or_invalid_context_cannot_invent_dhw(case):
    attrs = {"hvac_action": "heating", "current_temperature": 49, "temperature": 50}
    if case in ("estimated", "restored"):
        attrs[case] = True
    if case == "target_only":
        attrs.pop("hvac_action")
    view = task_display(watts=58 if case == "below_threshold" else 1200,
        tank_state="idle", tank_attrs=attrs, tank_stamp=879 if case == "stale" else 990,
        tank_entity="sensor.tank_target" if case == "not_native" else "water_heater.tank")
    assert view["function"] is None and view["evidence"] == "metered_power"
    assert view["observed_at"] == 999 and view["context_observed_at"] is None


@pytest.mark.parametrize("action,function,label", [("heating", "space_heating", "Ruimte verwarmen"),
    ("cooling", "space_cooling", "Ruimte koelen")])
def test_space_action_interpretation_includes_its_own_and_used_tank_idle_stamps(action, function, label):
    view = task_display(tank_stamp=950, zones=[{"available": True,
        "action": action, "observed_at": 980}])
    assert view["function"] == function and view["label"] == label
    assert view["context_observed_at"] == view["observed_at"] == 950


@pytest.mark.parametrize("action,case", [("heating", "stale"), ("cooling", "estimated"), ("heating", "missing")])
def test_unreliable_space_action_falls_back_to_fresh_generic_power(action, case):
    view = task_display(zones=[{"available": case != "missing", "action": action,
        "observed_at": 879 if case == "stale" else 980, "action_valid": case != "estimated"}])
    assert view["function"] is None and view["label"] == "Warmtepomp werkt"
    assert view["observed_at"] == 999 and view["context_observed_at"] is None


@pytest.mark.parametrize("context", ["space_heating", "space_cooling"])
def test_native_programme_interpretation_requires_fresh_explicit_tank_idle_and_reliable_context(context):
    valid = dict(context=context, context_reliable=True, context_stamp=970)
    view = task_display(tank_state="off", **valid)
    assert view["function"] == context and view["observed_at"] == 970
    assert "programmacontext" in view["note"]
    assert task_display(tank_state="on", **valid)["function"] is None
    assert task_display(tank_stamp=879, **valid)["function"] is None
    assert task_display(**{**valid, "context_stamp": 879})["function"] is None
    assert task_display(**{**valid, "context_reliable": False})["function"] is None


@pytest.mark.parametrize("case", ["space_heating", "space_cooling", "programme_cooling", "conflict"])
def test_concurrent_or_conflicting_native_tasks_leave_function_generic(case):
    context = {}
    if case.startswith("space_"):
        context["zones"] = [{"available": True, "action": "heating" if case == "space_heating" else "cooling", "observed_at": 970}]
    elif case == "programme_cooling":
        context["native_programs"] = [{"fresh": True, "program": "cooling", "observed_at": 970}]
    else:
        context.update(conflict=True, context_reliable=True, context_stamp=960)
    view = task_display(tank_state="heating", tank_attrs={"hvac_action": "heating"}, **context)
    assert view["active"] and view["function"] is None and view["label"] == "Warmtepomp werkt"
    assert "niet eenduidig" in view["note"]
    assert view["observed_at"] == min(999, view["context_observed_at"])


def test_stale_task_cannot_be_refreshed_by_a_new_meter_report():
    initial = task_display(tank_state="heating", tank_attrs={"hvac_action": "heating"}, tank_stamp=881)
    assert initial["function"] == "tapwater_heating" and initial["observed_at"] == 881
    later = power_activity(complete(1200, stamp=1002), {}, now_wall=1002,
        tank=SimpleNamespace(state="heating", attributes={"hvac_action": "heating"}), tank_entity="water_heater.tank", tank_stamp=881)
    assert later["active"] and later["label"] == "Warmtepomp werkt"
    assert later["function"] is None and later["observed_at"] == 1002


def test_metered_activity_and_optimistic_tank_task_never_change_native_or_sg_contracts():
    runtime, hass = split(tank_target_entity="water_heater.tank", zone_entities=["climate.room"],
        compressor_frequency_entity="sensor.hp_frequency")
    hass.states.set("climate.room", "auto", {"hvac_action": "off"})
    hass.states.set("water_heater.tank", "idle", {"operation_mode": "idle", "current_temperature": 49, "temperature": 50})
    hass.states.set("sensor.hp_frequency", 0, {"unit_of_measurement": "Hz"})
    before = runtime.panasonic.overview()
    journal, budget = deepcopy(runtime._snapshot()), deepcopy(sg_solar_budget(runtime))
    # This provider field can be optimistic programme context. It is accepted
    # for derived presentation only, never copied into operation/cooling guards.
    hass.states.set("water_heater.tank", "heating", {"operation_mode": "heating", "current_temperature": 49, "temperature": 50})
    runtime.panasonic.settings.update(power_activity_threshold_w=200,
        power_supply1_role="main", power_supply2_role="heater")
    after = runtime.panasonic.overview()
    assert after["power_activity"]["function"] is None
    assert "Tank staat op verwarmen" in after["power_activity"]["note"]
    assert after["operation"] == before["operation"] and after["compressor_running"] is False
    for key in ("context", "context_reliable", "context_signature", "cooling_possible", "sg_status", "sg_effect_confirmed"):
        assert after[key] == before[key]
    assert runtime._snapshot() == journal and sg_solar_budget(runtime) == budget
    assert not hass.services.calls


def test_monitor_passes_display_only_native_action_without_changing_control_context(monkeypatch):
    runtime, hass = split(tank_target_entity="water_heater.tank", zone_entities=["climate.room"])
    hass.states.set("climate.room", "auto", {"hvac_action": "off"})
    hass.states.set("water_heater.tank", "heating", {"operation_mode": "heating"})
    before = runtime.panasonic.overview()
    stamp = hass.states.get("water_heater.tank").last_reported.timestamp()
    monkeypatch.setattr(runtime.panasonic.native_program, "read_tank_action", lambda eid: {
        "entity_id": eid, "source": "aquarea_poll", "fresh": True,
        "raw_action": "HEATING_WATER", "action": "tapwater_heating", "observed_at": stamp})
    after = runtime.panasonic.overview()
    assert after["power_activity"]["function"] == "tapwater_heating"
    for key in ("operation", "context", "context_reliable", "context_signature", "cooling_possible"):
        assert after[key] == before[key]
    assert not hass.services.calls


@pytest.mark.parametrize("scope", ["total", "supply1", "supply2", "unconfirmed"])
def test_existing_single_meter_coverage_is_preserved_without_inventing_total_or_function(scope):
    runtime, hass = observed(power_entity="sensor.hp_single", power_scope=scope)
    hass.states.set("sensor.hp_single", 2400, {"unit_of_measurement": "W"})
    view = runtime.panasonic.overview()["power_activity"]
    assert view["active"] and view["complete"] is (scope == "total")
    assert view["total_w"] == (2400 if scope == "total" else None)
    assert view["function"] is None
    if scope in ("supply1", "supply2"):
        assert view["supplies"][0]["number"] == int(scope[-1])
        assert view["label"] == f"Actief verbruik op voeding {scope[-1]}"
