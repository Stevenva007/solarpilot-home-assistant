"""Exact 1.5.4/1.3.1 compatibility without changing native control proof."""
from copy import deepcopy
import json

import pytest

import test_aquarea_display_snapshot86 as fixture
from custom_components.solar_pilot.operation_source_evidence import contract_evidence, retained_contract_evidence
from test_display_operation83 import NOW, contract_snapshot, display


@pytest.mark.parametrize("raw,status_value", [("OFF", 0), ("HEATING", 1), ("HEATING", 2)])
def test_154_parser_specialstatus_values_keep_raw_action_and_native_read_only_boundaries(raw, status_value, monkeypatch):
    original = fixture.status
    def status(*args, **kwargs):
        value = original(*args, **kwargs)
        # SDK 1.3.1 maps specialStatus 0/1/2 through OperationStatus. Its
        # current_action returns OFF for 0 first; 1/2 then inspect direction.
        value.operation_status = fixture.OperationStatus(status_value)
        return value
    monkeypatch.setattr(fixture, "status", status)
    env = fixture.modern_setup(monkeypatch, version="1.5.4")
    assert env.helper.read_source_contract(env.sources)["reason_code"] == "native_poll_not_current"
    env.coordinator.poll()
    result = env.helper.read_source_contract(env.sources)
    assert result["status"] == "verified" and result["raw_device_action"] == raw
    assert result["program"]["state"] == "heating" and result["pump"]["state"] == "on"
    assert env.helper._legacy_status(env.coordinator, env.entries["native"]) is None
    assert env.helper._watches == {} and env.helper._tank_watches == {}
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


@pytest.mark.parametrize("change", ["missing_typed_pump", "missing_zone", "missing_tank", "wrong_entry",
    "pump_conflict", "direction_conflict", "zone_conflict", "missing_report", "old_report", "future_report",
    "failed_poll", "optimistic_mutation", "unloaded_metadata", "wrong_sdk"])
def test_154_contract_keeps_original_shape_binding_conflict_and_time_guards(change, monkeypatch):
    env = fixture.modern_setup(monkeypatch, version="1.5.4")
    env.helper.read_source_contract(env.sources)
    env.coordinator.poll()
    original_time = env.helper.read_source_contract(env.sources)["observed_at"]
    if change == "missing_typed_pump": env.coordinator.device._status.pump_duty = None
    elif change == "missing_zone": env.coordinator.device._status.zones.pop()
    elif change == "missing_tank": env.coordinator.device._status.tank_status.clear()
    elif change == "wrong_entry": env.entries["native"].runtime_data.clear()
    elif change == "pump_conflict": env.state(env.sources["pump_status_entity"], "Off")
    elif change == "direction_conflict": env.state(env.sources["direction_entity"], "WATER")
    elif change == "zone_conflict": env.state(env.sources["zone_entities"][0], "cool")
    elif change == "missing_report": env.state(env.sources["pump_status_entity"], "On", stamp=0)
    elif change == "old_report": env.state(env.sources["pump_status_entity"], "On", stamp=800)
    elif change == "future_report": env.state(env.sources["pump_status_entity"], "On", stamp=1006)
    elif change == "failed_poll": env.coordinator.notify(success=False)
    elif change == "optimistic_mutation": env.coordinator.device._status.direction = fixture.DeviceDirection.WATER
    elif change == "unloaded_metadata": env.helper._display_metadata["integration_loaded"] = False
    else: env.helper._display_metadata["library_version"] = "1.3.2"
    result = env.helper.read_source_contract(env.sources)
    assert result["status"] == "unknown" and result["reason_code"]
    assert result["observed_at"] in (None, original_time)
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


@pytest.mark.parametrize("skew,accepted", [(5, True), (5.001, False), (120, False)])
def test_154_display_keeps_existing_maximum_native_report_skew(skew, accepted):
    p = contract_snapshot()
    c = p["source_contract"]
    c["provider"]["integration_version"] = "1.5.4"
    for row in (c, c["pump"], c["direction"], c["program"], c["tank"], *c["zones"], p["display_tank"]):
        row["observed_at"] = NOW-1
    c["pump"]["observed_at"] -= skew
    result = display(p)
    assert (result["function"] == "space_heating") is accepted
    assert result["maximum_context_skew_s"] == 5
    if not accepted:
        assert result["reason_code"] in ("native_context_report_skew", "native_source_not_current")


def test_154_current_evidence_is_retained_but_old_unknown_contract_is_not_promoted():
    raw = contract_snapshot()["source_contract"]
    raw["provider"]["integration_version"] = "1.5.4"
    raw["reason_code"] = "known_special_status_action_mapping"
    clean = contract_evidence(raw, NOW, 120)
    assert clean["verified"] is True and clean["raw_device_action"] == "OFF"
    assert retained_contract_evidence(json.loads(json.dumps(clean)), NOW, 120) == clean
    previous = deepcopy(raw)
    previous.update(contract_id=None, action_semantics="unknown", status="unknown", reason_code="provider_contract_unverified")
    older = contract_evidence(previous, NOW, 120)
    assert older["verified"] is False and older["contract_id"] is None
    assert retained_contract_evidence(json.loads(json.dumps(older)), NOW, 120) == older


@pytest.mark.parametrize("change", ["schema_bool", "unloaded", "missing_loaded", "version_list", "version_dict"])
def test_154_display_refuses_malformed_or_missing_contract_flags_without_raising(change):
    p = contract_snapshot()
    c = p["source_contract"]
    c["provider"]["integration_version"] = "1.5.4"
    if change == "schema_bool": c["schema"] = True
    elif change == "unloaded": c["provider_loaded"] = False
    elif change == "missing_loaded": c.pop("provider_loaded")
    elif change == "version_list": c["provider"]["integration_version"] = ["1.5.4"]
    else: c["provider"]["integration_version"] = {"version": "1.5.4"}
    assert display(p)["function"] is None


def test_malformed_installed_version_is_unknown_even_before_native_binding_lookup(monkeypatch):
    env = fixture.modern_setup(monkeypatch, version=["1.5.4"])
    result = env.helper.read_source_contract(env.sources)
    assert result["status"] == "unknown" and result["reason_code"] == "provider_contract_unverified"
