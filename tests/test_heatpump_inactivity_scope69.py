"""Independent native tank status bounds a read-only task despite main OFF."""
from copy import deepcopy
from enum import Enum, IntEnum
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot.power_activity import task_observations
from test_heatpump_dynamic_task68 import CONFIG, NOW, TANK, metered, proof, render
from test_heatpump_task67 import automatic_monitor
from test_native_tank_action66 import DeviceAction, DeviceDirection, TankCoordinator, tank_setup


OperationStatus = IntEnum("OperationStatus", {"OFF": 0, "ON": 1, "UNKNOWN": 2}, module="aioaquarea.data")


def independent_off(*, tank_status="ON", has_tank=True, direction="WATER", main_status="OFF"):
    return {**proof("OFF"), "operation_status": main_status, "has_tank": has_tank,
            "tank_operation_status": tank_status, "direction": direction}


def tank_route(stamp=985):
    return {"function": "tapwater_heating", "source": "aquarea_entity",
            "kind": "tank_route", "observed_at": stamp}


def typed_poll(coordinator, *, main=OperationStatus.OFF, tank=OperationStatus.ON,
               direction=DeviceDirection.WATER, has_tank=True):
    coordinator.poll(action=DeviceAction.OFF, direction=direction, notify=False)
    coordinator.device.operation_status = main
    coordinator.device.has_tank = has_tank
    coordinator.device.tank = NS(operation_status=tank) if has_tank else None
    for listener in tuple(coordinator.listeners):
        listener()


def test_independent_on_water_tank_can_be_inferred_while_raw_main_off_is_retained():
    view, native, context = render(actions=[independent_off()], route=tank_route(), tank_state="heating")
    assert native["function"] is None and native["inactive_action"] == "off"
    assert native["inactive_scope"] == "space_circuit" and native["independent_tank_on"] is True
    assert native["verified_global_off"] is False
    assert native["raw_evidence"][0]["raw_action"] == "OFF"
    assert native["inactive_zones"][0]["scope"] == "zone"
    assert context["kind"] == "tank_route"
    assert view["function"] == "tapwater_heating" and view["function_kind"] == "tank_route"
    assert view["function_source"] == "aquarea_entity" and view["observed_at"] == 980
    assert "onafhankelijk ON met WATER-route" in view["note"]


@pytest.mark.parametrize("has_tank,tank_status", [(False, None), (True, "OFF")])
def test_verified_global_off_still_vetoes_even_a_fresh_route_and_complete_active_main(has_tank, tank_status):
    view, native, _ = render(actions=[independent_off(has_tank=has_tank, tank_status=tank_status)],
                             route=tank_route(), tank_state="heating")
    assert native["inactive_scope"] == "global" and native["verified_global_off"] is True
    assert native["independent_tank_on"] is False
    assert view["active"] and view["function"] is None and view["function_kind"] == "none"


@pytest.mark.parametrize("change", [{"operation_status": None}, {"operation_status": "ON"},
    {"has_tank": None}, {"tank_operation_status": None}, {"tank_operation_status": "UNKNOWN"},
    {"direction": None}, {"direction": "PUMP"}, {"direction": "IDLE"}])
def test_incomplete_independent_status_is_unknown_off_and_cannot_enable_route_inference(change):
    view, native, _ = render(actions=[{**independent_off(), **change}], route=tank_route(), tank_state="heating")
    assert native["inactive_scope"] == "unknown" and native["independent_tank_on"] is False
    assert view["function"] is None


def test_main_off_with_independent_tank_never_becomes_selected_space_heating():
    view, native, context = render(actions=[independent_off()])
    assert native["inactive_scope"] == "space_circuit" and context["kind"] == "selected_program"
    assert view["function"] is None


@pytest.mark.parametrize("failure", ["old_route", "old_main", "old_heater", "partial", "heater_only"])
def test_independent_tank_inference_keeps_all_source_and_meter_guards(failure):
    power, route = metered(), tank_route()
    if failure == "old_route":
        route["observed_at"] = NOW - 121
    elif failure in ("old_main", "old_heater"):
        power["supplies"]["supply1" if failure == "old_main" else "supply2"]["measured_wall"] = NOW - 121
    elif failure == "partial":
        power["complete"] = False
    else:
        power = metered(main=58, heater=3000)
    view, _, _ = render(power=power, actions=[independent_off()], route=route, tank_state="heating")
    assert view["function"] is None and view["function_kind"] == "none"


def test_unknown_cached_scope_cannot_be_promoted_by_a_fresh_meter_or_route():
    cached = {"function": None, "source": "aquarea_poll", "observed_at": 980,
              "inactive": True, "inactive_action": "off", "inactive_scope": "space_circuit"}
    view, _, _ = render(actions=[independent_off()], route=tank_route(), tank_state="heating", native_override=cached)
    assert view["function"] is None


def test_conflicting_cached_global_off_boolean_keeps_its_veto():
    cached = {"function": None, "source": "aquarea_poll", "observed_at": 980,
              "inactive": True, "inactive_action": "off", "inactive_scope": "space_circuit",
              "independent_tank_on": True, "verified_global_off": True}
    view, _, _ = render(actions=[independent_off()], route=tank_route(), tank_state="heating", native_override=cached)
    assert view["function"] is None


@pytest.mark.parametrize("case", ["space_action", "global_off", "defrost"])
def test_real_native_conflicts_and_defrost_keep_priority(case):
    kwargs = {"actions": [independent_off()], "route": tank_route(), "tank_state": "heating"}
    if case == "space_action":
        kwargs["actions"].append(proof("HEATING"))
    elif case == "global_off":
        kwargs["actions"].append(independent_off(tank_status="OFF"))
    else:
        kwargs["defrost"] = {"state": "active", "source": "aquarea_poll", "observed_at": 975}
    view, native, _ = render(**kwargs)
    assert view["function"] is None
    if case != "global_off":
        assert native["conflict"]


def test_independent_tank_actual_action_is_not_conflicting_with_inactive_space_circuit():
    actual, _ = task_observations(CONFIG, tank=NS(state="heating", attributes={"hvac_action": "heating"}),
        tank_entity=TANK, tank_stamp=990,
        zones=[{"entity_id": "climate.test_room", "available": True, "observed_at": 990, "action": "off"}],
        device_actions=[independent_off()], now_wall=NOW)
    assert actual["function"] == "tapwater_heating" and actual["source"] == "native_hvac_action"
    assert not actual.get("conflict") and actual["raw_evidence"][0]["raw_action"] == "OFF"


def test_exact_provider_status_fields_need_the_same_fresh_poll_and_mutation_revokes_them(monkeypatch):
    helper, coordinator, _rows, _entries, clock = tank_setup(monkeypatch)
    assert helper.read_tank_action("water_heater.tank")["fresh"] is False
    typed_poll(coordinator)
    result = helper.read_tank_action("water_heater.tank")
    assert result["raw_action"] == "OFF" and result["fresh"] is True
    assert (result["operation_status"], result["tank_operation_status"], result["direction"]) == ("OFF", "ON", "WATER")
    assert result["has_tank"] is True
    coordinator.device.tank.operation_status = OperationStatus.OFF
    assert helper.read_tank_action("water_heater.tank")["fresh"] is False
    typed_poll(coordinator)
    clock[0] += 121
    expired = helper.read_tank_action("water_heater.tank")
    assert expired["fresh"] is False and "tank_operation_status" not in expired
    assert coordinator.api_calls == []


@pytest.mark.parametrize("invalid", [1, "ON", NS(name="ON", value=1),
    IntEnum("OperationStatus", {"ON": 1}, module="other.data").ON,
    IntEnum("OtherStatus", {"ON": 1}, module="aioaquarea.data").ON,
    IntEnum("OperationStatus", {"ON": 0}, module="aioaquarea.data").ON,
    Enum("OperationStatus", {"ON": True}, module="aioaquarea.data").ON])
def test_untyped_tank_status_is_retained_as_unknown_and_cannot_narrow_off_scope(monkeypatch, invalid):
    helper, coordinator, *_ = tank_setup(monkeypatch)
    helper.read_tank_action("water_heater.tank")
    typed_poll(coordinator, tank=invalid)
    result = helper.read_tank_action("water_heater.tank")
    assert result["fresh"] is True and result["raw_action"] == "OFF"
    assert result["tank_operation_status"] is None
    assert coordinator.api_calls == []


def test_real_monitor_read_only_inference_keeps_controller_context_and_sg_snapshot(monkeypatch):
    env, runtime, hass = automatic_monitor(monkeypatch)
    coordinator = TankCoordinator()
    env.entries["native"].runtime_data = {"pump": coordinator}
    before = deepcopy(runtime.panasonic.settings), deepcopy(runtime._snapshot())
    runtime.panasonic.overview()  # Observe the adapter; a cached snapshot is not a new poll.
    typed_poll(coordinator)
    view = runtime.panasonic.overview()
    assert view["native_task"]["inactive_scope"] == "space_circuit"
    assert view["native_task"]["raw_evidence"][0]["raw_action"] == "OFF"
    assert view["power_activity"]["function"] == "tapwater_heating"
    assert view["power_activity"]["function_kind"] == "tank_route"
    assert view["context"] == "normal" and view["cooling_possible"] is True
    assert (runtime.panasonic.settings, runtime._snapshot()) == before
    assert not hass.services.calls and not coordinator.api_calls
