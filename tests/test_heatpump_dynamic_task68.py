"""A live electrical task inference stays separate from native/controller proof."""
from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot.power_activity import POWER_NOTE, power_activity, task_observations


NOW = 1000
CONFIG = {"stale_s": 120, "power_activity_threshold_w": 200,
          "power_supply_profile": "panasonic_standard",
          "power_supply1_role": "main", "power_supply2_role": "heater"}
ZONE = "climate.test_room"
TANK = "water_heater.test_tank"


def metered(main=1360, heater=0, *, complete=True):
    return {"valid": True, "complete": complete, "watts": main + heater,
            "measured_wall": 999, "meter_scope": "total", "supplies": {
                "supply1": {"valid": True, "watts": main, "measured_wall": 995},
                "supply2": {"valid": True, "watts": heater, "measured_wall": 998}}}


def zone(*, mode="auto", action="off", stamp=990, available=True, action_valid=True):
    return {"entity_id": ZONE, "available": available, "action_valid": action_valid,
            "mode": mode, "action": action, "observed_at": stamp}


def proof(raw="IDLE", *, entity=ZONE, stamp=980):
    actions = {"IDLE": "idle", "OFF": "off", "HEATING": "space_heating",
               "COOLING": "space_cooling", "HEATING_WATER": "tapwater_heating"}
    return {"entity_id": entity, "source": "aquarea_poll", "fresh": True,
            "raw_action": raw, "action": actions[raw], "observed_at": stamp}


def programme(direction="heating", *, stamp=970, fresh=True):
    return {"program": direction, "fresh": fresh, "observed_at": stamp}


def render(*, power=None, config=None, zones=None, programs=None, actions=None,
           tank_action=None, route=None, defrost=None, native_override=None,
           selected_override=None, tank_state="idle", **controller):
    """Exercise the real observation builder and check every supplied input."""
    cfg = deepcopy(CONFIG if config is None else config)
    inputs = {"tank": NS(state=tank_state, attributes={"operation_mode": tank_state}),
              "tank_entity": TANK, "tank_stamp": 990,
              "zones": [zone()] if zones is None else zones,
              "native_programs": [programme()] if programs is None else programs,
              "device_actions": [proof()] if actions is None else actions,
              "tank_action": tank_action, "route_context": route, "defrost": defrost}
    watts = metered() if power is None else power
    original = deepcopy((cfg, inputs, watts, controller))
    actual, selected = task_observations(cfg, **inputs, now_wall=NOW)
    native = actual if native_override is None else native_override
    context = selected if selected_override is None else selected_override
    observations = deepcopy((native, context))
    view = power_activity(watts, cfg, **inputs, native_actual=native,
                          display_context=context, now_wall=NOW, **controller)
    assert (cfg, inputs, watts, controller) == original
    assert (native, context) == observations
    return view, native, context


@pytest.mark.parametrize("direction,function,label", [
    ("heating", "space_heating", "Ruimte verwarmen"),
    ("cooling", "space_cooling", "Ruimte koelen"),
])
def test_1360w_main_zero_heater_infers_selected_task_without_changing_native_idle(direction, function, label):
    view, native, selected = render(programs=[programme(direction)])
    assert view["active"] and view["complete"] and view["total_w"] == 1360
    assert view["activity_kind"] == "main"
    assert view["function"] == function and view["label"] == label
    assert view["function_kind"] == "selected_program" and view["function_source"] == "native_program"
    assert view["evidence"] == "metered_power_and_context"
    assert view["context_observed_at"] == view["observed_at"] == 970
    assert "gekozen Panasonic-stand" in view["note"] and "native terugmelding meldt nog rust" in view["note"]
    assert POWER_NOTE in view["note"]
    assert native["function"] is None and native["inactive"] and native["inactive_action"] == "idle"
    assert native["label"] == "Panasonic meldt rust" and native["source"] == "aquarea_poll"
    assert native["observed_at"] == 980 and selected["kind"] == "selected_program"
    assert view["supplies"][1]["watts"] == 0 and view["supplies"][1]["state"] == "off"


@pytest.mark.parametrize("mode,function", [("heat", "space_heating"), ("cool", "space_cooling")])
def test_fresh_explicit_native_mode_can_supply_display_context_without_programme_poll(mode, function):
    view, native, selected = render(zones=[zone(mode=mode)], programs=[])
    assert native["inactive_action"] == "idle" and selected["source"] == "native_mode"
    assert view["function"] == function and view["function_source"] == "native_mode"
    assert view["function_kind"] == "selected_program" and view["observed_at"] == 990


@pytest.mark.parametrize("direction", ["heating", "cooling"])
def test_strong_registered_tank_route_has_priority_over_selected_space_programme(direction):
    route = {"function": "tapwater_heating", "source": "aquarea_entity",
             "kind": "tank_route", "observed_at": 985}
    view, native, selected = render(programs=[programme(direction)], route=route, tank_state="heating")
    assert native["function"] is None and native["inactive_action"] == "idle"
    assert selected["kind"] == "tank_route" and view["function"] == "tapwater_heating"
    assert view["label"] == "Sanitair water opwarmen"
    assert view["function_kind"] == "tank_route" and view["function_source"] == "aquarea_entity"
    assert view["context_observed_at"] == view["observed_at"] == 985
    assert "hoofdcircuit en Panasonic-tankroute" in view["note"]


@pytest.mark.parametrize("raw,entity,direction,function", [
    ("HEATING_WATER", TANK, "cooling", "tapwater_heating"),
    ("COOLING", ZONE, "heating", "space_cooling"),
    ("HEATING", ZONE, "cooling", "space_heating"),
])
def test_actual_native_task_wins_controller_conflict_from_opposite_selected_programme(raw, entity, direction, function):
    action = proof(raw, entity=entity)
    view, native, _ = render(programs=[programme(direction)], actions=[] if entity == TANK else [action],
                             tank_action=action if entity == TANK else None, conflict=True)
    assert native["function"] == function and not native.get("conflict")
    assert view["function"] == function and view["function_kind"] == "native_action"
    assert view["function_source"] == "aquarea_poll" and view["observed_at"] == 980


def test_conflicting_actual_native_tasks_suppress_selected_task_inference():
    view, native, _ = render(zones=[zone(action="heating")], actions=[proof("COOLING")])
    assert native["function"] is None and native["conflict"]
    assert view["active"] and view["function"] is None
    assert view["function_kind"] == "none" and "niet eenduidig" in view["note"]


@pytest.mark.parametrize("source", ["aquarea_entity", "aquarea_poll"])
def test_fresh_defrost_veto_survives_a_cached_native_heating_object(source):
    cached = {"function": "space_heating", "source": "aquarea_poll", "observed_at": 980}
    view, native, _ = render(defrost={"state": "active", "source": source, "observed_at": 975},
                             native_override=cached)
    assert native == cached  # The cached native object itself is never rewritten.
    assert view["active"] and view["function"] is None
    assert view["function_kind"] == "none" and "Ontdooimelding" in view["note"]


def test_expired_defrost_does_not_block_independently_fresh_selected_context():
    view, native, _ = render(defrost={"state": "active", "source": "aquarea_poll", "observed_at": 879})
    assert native["inactive_action"] == "idle"
    assert view["function"] == "space_heating" and view["function_kind"] == "selected_program"


@pytest.mark.parametrize("programs", [[], [programme(stamp=879)], [programme(fresh=False)],
                                      [programme("off")], [programme(), programme("cooling")]])
def test_bare_auto_old_unknown_or_mixed_native_programmes_do_not_invent_a_direction(programs):
    view, native, selected = render(programs=programs)
    assert native["inactive_action"] == "idle" and selected["function"] is None
    assert view["active"] and view["function"] is None and view["function_kind"] == "none"


@pytest.mark.parametrize("bad_zone", [zone(mode="heat", stamp=879), zone(mode="heat", available=False),
                                       zone(mode="heat", action_valid=False)])
def test_old_missing_or_estimated_zone_mode_cannot_return_through_controller_context(bad_zone):
    view, _, selected = render(zones=[bad_zone], programs=[], context="space_heating",
                               context_reliable=True, context_stamp=990)
    assert selected["function"] is None and view["function"] is None


def test_controller_context_alone_without_display_sources_cannot_infer_space_heating():
    view, _, selected = render(zones=[], programs=[], actions=[], context="space_heating",
                               context_reliable=True, context_stamp=990)
    assert selected["function"] is None and view["function"] is None


@pytest.mark.parametrize("source,kind,stamp", [("native_program", "selected_program", 879),
    ("native_program", "selected_program", 1006), ("none", "selected_program", 970),
    ("native_program", "none", 970)])
def test_cached_selected_context_must_keep_its_own_freshness_and_qualified_source(source, kind, stamp):
    selected = {"function": "space_heating", "source": source, "kind": kind, "observed_at": stamp}
    view, _, _ = render(selected_override=selected)
    assert view["function"] is None and view["function_kind"] == "none"


def test_selected_context_disagreeing_with_fresh_programme_is_not_a_usable_fallback():
    selected = {"function": "space_heating", "source": "native_program",
                "kind": "selected_program", "observed_at": 970}
    view, _, _ = render(programs=[programme("cooling")], selected_override=selected)
    assert view["function"] is None


@pytest.mark.parametrize("bad", ["old_main", "old_heater", "invalid_heater", "partial", "old_total"])
def test_fresh_aggregate_cannot_refresh_stale_individual_feed_or_incomplete_coverage(bad):
    power = metered()
    if bad.startswith("old_") and bad != "old_total":
        power["supplies"]["supply1" if bad == "old_main" else "supply2"]["measured_wall"] = 879
    elif bad == "invalid_heater":
        power["supplies"]["supply2"]["valid"] = False
    elif bad == "old_total":
        power["measured_wall"] = 879
    else:
        power["complete"] = False
    view, native, _ = render(power=power)
    assert native["inactive_action"] == "idle"
    assert view["state"] == "partial" and view["function"] is None
    assert not view["complete"] and view["total_w"] is None and view["function_kind"] == "none"


@pytest.mark.parametrize("main,heater,state,kind", [(0, 0, "off", "unknown"),
    (58, 0, "basis", "unknown"), (199, 0, "basis", "unknown"),
    (58, 3000, "active", "heater"), (150, 100, "active", "unknown")])
def test_off_basis_heater_only_and_two_small_feeds_do_not_infer_a_space_task(main, heater, state, kind):
    view, _, _ = render(power=metered(main, heater))
    assert view["state"] == state and view["activity_kind"] == kind
    assert view["function"] is None and view["function_kind"] == "none"
    if kind == "heater":
        assert view["label"] == "Elektrische bijverwarming actief"


@pytest.mark.parametrize("role", ["unconfirmed", "invalid"])
def test_unconfirmed_main_feed_role_does_not_identify_a_selected_task(role):
    view, _, _ = render(config={**CONFIG, "power_supply1_role": role})
    assert view["active"] and view["function"] is None and view["activity_kind"] == "unknown"


@pytest.mark.parametrize("main,threshold,function", [(200, 200, "space_heating"),
    (1360, 1360, "space_heating"), (1360, 1361, None), (1360, 2500, None)])
def test_main_feed_uses_the_user_interpretation_threshold_inclusively(main, threshold, function):
    view, _, _ = render(power=metered(main, 0), config={**CONFIG, "power_activity_threshold_w": threshold})
    assert view["function"] == function and view["threshold_w"] == threshold
    assert view["active"] is (main >= threshold)


def test_active_main_with_active_heater_keeps_separate_support_and_inferred_space_task():
    view, native, _ = render(power=metered(1360, 3000))
    assert view["activity_kind"] == "mixed" and view["function"] == "space_heating"
    assert view["function_kind"] == "selected_program" and native["inactive_action"] == "idle"
    assert [row["watts"] for row in view["supplies"]] == [1360, 3000]


@pytest.mark.parametrize("case", ["off", "mixed", "legacy"])
def test_fresh_off_mixed_or_legacy_unknown_inactivity_remains_a_hard_veto(case):
    actions = [proof("OFF")] if case == "off" else [proof(), proof("OFF")] if case == "mixed" else [proof()]
    legacy = {"function": None, "source": "aquarea_poll", "observed_at": 980, "inactive": True}
    view, native, _ = render(actions=actions, native_override=legacy if case == "legacy" else None)
    assert native["inactive"] and view["active"] and view["function"] is None
    assert view["function_kind"] == "none"
    if case != "legacy":
        assert native["inactive_action"] == case


@pytest.mark.parametrize("stamp", [879, 1006])
def test_old_matching_native_action_cannot_relabel_fresh_selected_inference_as_actual(stamp):
    old_native = {"function": "space_heating", "source": "aquarea_poll", "observed_at": stamp}
    view, native, _ = render(native_override=old_native)
    assert native == old_native and view["function"] == "space_heating"
    assert view["function_kind"] == "selected_program" and view["function_source"] == "native_program"
    assert view["context_observed_at"] == view["observed_at"] == 970
    assert "gekozen Panasonic-stand" in view["note"]
