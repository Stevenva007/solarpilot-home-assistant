"""Aquarea 1.7's additive AUTO side is never independent activity evidence."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.display_operation import classify_display_operation
from custom_components.solar_pilot.heatpump_learning import classify_heatpump_observation
from test_aquarea_display_snapshot86 import modern_setup, PumpDuty, DeviceDirection
from test_display_operation83 import NOW, contract_snapshot
from test_native_program56 import ExtendedOperationMode


MODES = [(ExtendedOperationMode.AUTO_HEAT, "heat", "heating"),
         (ExtendedOperationMode.AUTO_COOL, "cool", "cooling")]


def environment(monkeypatch, side):
    env = modern_setup(monkeypatch, version="1.7.0")
    env.clock[0] = NOW
    env.helper._display_metadata_checked = NOW
    for eid in env.sources["zone_entities"]:
        env.state(eid, "auto", {"hvac_action": "off", "auto_mode": side}, stamp=NOW-2)
    env.state(env.sources["pump_status_entity"], "Off", stamp=NOW-2)
    env.state(env.sources["direction_entity"], "IDLE", stamp=NOW-2)
    env.state(env.sources["tank_entity"], "idle", {"operation_mode": "idle"}, stamp=NOW-2)
    return env


@pytest.mark.parametrize("mode,side,selected", MODES)
def test_170_auto_side_keeps_typed_program_and_requires_original_new_poll(monkeypatch, mode, side, selected):
    env = environment(monkeypatch, side)
    eid = env.sources["zone_entities"][0]
    assert not env.helper.read(eid)["fresh"]
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"

    env.coordinator.poll(mode=mode, direction=DeviceDirection.IDLE, pump=PumpDuty.OFF, tank_on=False)
    contract = env.helper.read_source_contract(env.sources)
    program = env.helper.read(eid)
    assert contract["status"] == "verified"
    assert contract["provider"]["integration_version"] == "1.7.0"
    assert contract["raw_device_action"] == "OFF" and contract["pump"]["state"] == "off"
    assert contract["program"]["raw_mode"] == mode.name
    assert contract["program"]["state"] == program["program"] == selected
    assert program["fresh"] and contract["observed_at"] == NOW

    # An optimistic or contradictory optional attribute cannot replace typed
    # AUTO_HEAT/AUTO_COOL, nor change either adapter's existing proof.
    for zone in env.sources["zone_entities"]:
        env.state(zone, "auto", {"hvac_action": "off", "auto_mode": "cool" if side == "heat" else "heat"}, stamp=NOW-2)
    assert env.helper.read_source_contract(env.sources) == contract
    assert env.helper.read(eid) == program

    env.clock[0] = NOW+121
    for zone in env.sources["zone_entities"]:
        env.state(zone, "auto", {"hvac_action": "off", "auto_mode": side}, stamp=env.clock[0])
    stale = env.helper.read_source_contract(env.sources)
    assert stale["status"] == "unknown" and stale["observed_at"] == NOW
    assert not env.helper.read(eid)["fresh"]
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


@pytest.mark.parametrize("mode,side,selected", MODES)
def test_170_auto_side_cannot_supply_missing_loaded_semantic_proof(monkeypatch, mode, side, selected):
    env = environment(monkeypatch, side)
    env.helper._display_metadata["compatibility"] = None
    env.coordinator.poll(mode=mode)
    result = env.helper.read_source_contract(env.sources)
    assert result["status"] == "unknown" and result["compatibility"] is None
    assert result["reason_code"] == "provider_semantics_unavailable"
    assert result["contract_id"] is None and result["program"]["state"] is None
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


@pytest.mark.parametrize("mode,side,selected", MODES)
def test_170_idle_auto_side_does_not_create_running_task_or_learning_evidence(monkeypatch, mode, side, selected):
    env = environment(monkeypatch, side)
    env.helper.read_source_contract(env.sources)
    env.coordinator.poll(mode=mode, direction=DeviceDirection.IDLE, pump=PumpDuty.OFF, tank_on=False)
    contract = env.helper.read_source_contract(env.sources)
    assert contract["status"] == "verified" and contract["program"]["state"] == selected
    p = contract_snapshot(pump="off", main=0)
    p["source_contract"] = contract
    before = deepcopy(p)
    model = classify_heatpump_observation(p, now_wall=NOW)
    display = classify_display_operation(p, now_wall=NOW)
    assert display["function"] is None and display["active"] is False
    assert display["reason_code"] == "pump_not_on" and display["model_eligible"] is False
    assert model["model_eligible"] is False and model["tier"] == "unknown"
    assert classify_heatpump_observation(p, now_wall=NOW) == model and p == before
    assert env.helper._watches == {} and env.helper._tank_watches == {}
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []
