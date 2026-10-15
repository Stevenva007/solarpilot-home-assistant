"""Loaded code establishes read-only semantics; version labels do not."""
from copy import deepcopy
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

from custom_components.solar_pilot.operation_source_evidence import (
    contract_evidence, inspect_loaded_aquarea_semantics, loaded_semantic_identity,
    retained_contract_evidence, valid_semantic_contract,
)
from test_aquarea_display_snapshot86 import modern_setup
from test_cloud_energy_period91 import PROVIDER, evidence
from test_display_operation83 import NOW, contract_snapshot, display


DATA_SOURCE = '''
class DeviceStatus:
    pass
class OperationStatus:
    pass
class DeviceAction:
    pass
class DeviceDirection:
    pass
class ExtendedOperationMode:
    pass

class Device:
    @property
    def operation_status(self):
        """Read the parser's existing field."""
        return self._status.operation_status

    @property
    def current_action(self):
        """The current action, including preset-derived OFF."""
        if self.operation_status == OperationStatus.OFF:
            return DeviceAction.OFF
        direction = self.current_direction
        if direction == DeviceDirection.IDLE:
            return DeviceAction.IDLE
        if (self.has_tank and direction == DeviceDirection.WATER
                and self.tank.operation_status == OperationStatus.ON):
            return DeviceAction.HEATING_WATER
        mode = self.mode
        if direction == DeviceDirection.PUMP and mode != ExtendedOperationMode.OFF:
            return (DeviceAction.HEATING
                    if mode in (ExtendedOperationMode.HEAT, ExtendedOperationMode.AUTO_HEAT)
                    else DeviceAction.COOLING)
        return DeviceAction.IDLE
'''
PARSER_SOURCE = '''
class DeviceManager:
    async def get_device_status(self, device_info):
        json_response = await self._client.get_status(device_info)
        device = json_response.get("status")
        device_status = DeviceStatus(
            operation_status=OperationStatus(device.get("specialStatus")),
            direction=DeviceDirection(device.get("direction")),
            pump_duty=PumpDuty(device.get("pumpDuty")),
        )
        return device_status
'''


def loaded_sources(monkeypatch, tmp_path, *, data_source=DATA_SOURCE, parser_source=PARSER_SOURCE,
                   entities_source="class DeviceImpl(Device):\n    pass\n"):
    def load(name, source, values=None):
        path = tmp_path / (name.rsplit(".", 1)[-1]+".py")
        path.write_text(source, encoding="utf-8")
        module = ModuleType(name)
        module.__file__ = str(path)
        module.__dict__.update(values or {})
        monkeypatch.setitem(sys.modules, name, module)
        exec(compile(source, str(path), "exec"), module.__dict__)
        return module
    data = load("aioaquarea.data", data_source)
    globals_ = {name: getattr(data, name) for name in
                ("DeviceStatus", "OperationStatus", "DeviceAction", "DeviceDirection", "ExtendedOperationMode")}
    manager = load("aioaquarea.device_manager", parser_source, globals_)
    entities = load("aioaquarea.entities", entities_source, {"Device": data.Device})
    return data, manager, entities


def test_loaded_parser_and_inherited_actions_establish_semantics_without_calling_native_functions(monkeypatch, tmp_path):
    loaded_sources(monkeypatch, tmp_path)
    result = inspect_loaded_aquarea_semantics()
    assert result["compatibility_state"] == "compatible"
    assert valid_semantic_contract(result["compatibility"])
    assert result["reason_code"] == "known_special_status_action_mapping"
    # There is no API client and no enum members: native execution would fail.


def test_comments_formatting_and_unrelated_parser_fields_are_not_version_authority(monkeypatch, tmp_path):
    loaded_sources(monkeypatch, tmp_path, parser_source=PARSER_SOURCE.replace(
        'pump_duty=PumpDuty(device.get("pumpDuty")),', 'pump_duty=PumpDuty(device.get("pumpDuty")),\n            new_field=device.get("futureField"),'))
    assert inspect_loaded_aquarea_semantics()["compatibility_state"] == "compatible"


@pytest.mark.parametrize("change", ["global_status", "missing_parser_field", "unknown_mapping", "action_changed",
                                   "getter_changed", "implementation_override", "missing_source"])
def test_actual_changed_or_uninspectable_code_never_acquires_semantic_proof(change, monkeypatch, tmp_path):
    source, parser, entities = DATA_SOURCE, PARSER_SOURCE, "class DeviceImpl(Device):\n    pass\n"
    if change == "global_status": parser = parser.replace('device.get("specialStatus")', 'device.get("operationStatus")')
    elif change == "missing_parser_field": parser = parser.replace('operation_status=OperationStatus(device.get("specialStatus")),', '')
    elif change == "unknown_mapping": parser = parser.replace('device.get("specialStatus")', 'device.get("someNewStatus")')
    elif change == "action_changed": source = source.replace('return DeviceAction.OFF', 'return DeviceAction.HEATING')
    elif change == "getter_changed": source = source.replace('return self._status.operation_status', 'return self._status.other_status')
    elif change == "implementation_override": entities = "class DeviceImpl(Device):\n    @property\n    def current_action(self):\n        return None\n"
    else: parser = "class DeviceManager:\n    pass\n"
    loaded_sources(monkeypatch, tmp_path, data_source=source, parser_source=parser, entities_source=entities)
    result = inspect_loaded_aquarea_semantics()
    assert result["compatibility"] is None
    if change == "global_status":
        assert result["compatibility_state"] == "incompatible"
        assert result["reason_code"] == "provider_semantics_changed"
        assert result["compatibility_detail"] == "operation_status_no_longer_special_status"
    elif change in ("missing_parser_field", "unknown_mapping", "action_changed", "getter_changed"):
        assert result["compatibility_state"] == "incompatible"
        assert result["reason_code"] == "provider_semantics_changed"
        assert result["compatibility_detail"] in ("operation_status_mapping_changed", "action_or_status_getter_semantics_changed")
    else:
        assert result["compatibility_state"] == "unknown"
        assert result["reason_code"] == "provider_semantics_unavailable"


@pytest.mark.parametrize("change", ["decoy_factory", "unreachable_decoy", "local_constructor", "global_constructor",
                                   "local_enum", "default_getter", "changed_disk", "mutated_raw_status",
                                   "annotated_device", "named_device", "aliased_device", "passed_device"])
def test_decoys_aliases_shadowing_and_disk_source_mismatch_cannot_prove_loaded_semantics(change, monkeypatch, tmp_path):
    data_source, parser_source = DATA_SOURCE, PARSER_SOURCE
    if change == "decoy_factory":
        parser_source = parser_source.replace("return device_status", 'return OtherFactory(operation_status=device.get("operationStatus"))')
    elif change == "unreachable_decoy":
        parser_source = parser_source.replace("return device_status", 'return OtherFactory()\n        unused = DeviceStatus(operation_status=OperationStatus(device.get("specialStatus")))')
    elif change == "local_constructor":
        parser_source = parser_source.replace('device = json_response.get("status")', 'device = json_response.get("status")\n        DeviceStatus = OtherFactory')
    elif change == "local_enum":
        parser_source = parser_source.replace('device = json_response.get("status")', 'device = json_response.get("status")\n        OperationStatus = OtherEnum')
    elif change == "default_getter":
        data_source = data_source.replace("def current_action(self):", "def current_action(self, OperationStatus=None):")
    elif change == "mutated_raw_status":
        parser_source = parser_source.replace('device = json_response.get("status")', 'device = json_response.get("status")\n        device["specialStatus"] = device.get("operationStatus")')
    elif change == "annotated_device":
        parser_source = parser_source.replace('device = json_response.get("status")', 'device = json_response.get("status")\n        device: dict = {"specialStatus": device.get("operationStatus")}')
    elif change == "named_device":
        parser_source = parser_source.replace('device = json_response.get("status")', 'device = json_response.get("status")\n        (device := {"specialStatus": 1})')
    elif change == "aliased_device":
        parser_source = parser_source.replace('device = json_response.get("status")', 'device = json_response.get("status")\n        alias = device\n        alias["specialStatus"] = 1')
    elif change == "passed_device":
        parser_source = parser_source.replace('device = json_response.get("status")', 'device = json_response.get("status")\n        mutate_status(device)')
    data, manager, _ = loaded_sources(monkeypatch, tmp_path, data_source=data_source, parser_source=parser_source)
    if change == "global_constructor":
        manager.DeviceStatus = object()
    elif change == "changed_disk":
        Path(data.__file__).write_text(DATA_SOURCE.replace("return self._status.operation_status", "return self._status.other_status"), encoding="utf-8")
    result = inspect_loaded_aquarea_semantics()
    assert result["compatibility"] is None and result["compatibility_state"] == "unknown"


@pytest.mark.parametrize("integration", ["1.5.5", "1.6.0", "2.0.0"])
@pytest.mark.parametrize("sdk", ["1.3.2", "1.4.0", "2.0.0"])
def test_future_labels_with_same_loaded_capabilities_keep_native_display_and_evidence(integration, sdk, monkeypatch, tmp_path):
    loaded_sources(monkeypatch, tmp_path)
    inspection = inspect_loaded_aquarea_semantics()
    assert inspection["compatibility_state"] == "compatible"
    env = modern_setup(monkeypatch, version=integration)
    env.helper._display_metadata.update(inspection, library_version=sdk, _loaded_device_class=type(env.coordinator.device))
    env.helper.read_source_contract(env.sources)
    env.coordinator.poll()
    native = env.helper.read_source_contract(env.sources)
    assert native["status"] == "verified" and native["compatibility_state"] == "compatible"
    assert native["provider"]["integration_version"] == integration
    assert native["provider"]["library_version"] == sdk
    assert native["raw_device_action"] == "OFF"
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []
    assert env.helper._watches == {} and env.helper._tank_watches == {}

    p = contract_snapshot()
    c = p["source_contract"]
    c.update(inspection)
    c["provider"].update(integration_version=integration, library_version=sdk)
    assert display(p)["function"] == "space_heating"
    clean = contract_evidence(c, NOW, 120)
    assert clean["verified"] and clean["provider"]["integration_version"] == integration
    assert retained_contract_evidence(json.loads(json.dumps(clean)), NOW, 120) == clean


@pytest.mark.parametrize("integration,sdk", [("1.5.5", "1.3.2"), ("1.6.0", "1.4.0"), ("2.0.0", "2.0.0")])
def test_observed_native_cloud_period_keeps_working_independent_of_version(integration, sdk):
    provider = {**PROVIDER, "integration_version": integration, "library_version": sdk}
    start = datetime(2026, 10, 15, tzinfo=timezone.utc)
    result = evidence(start, start.replace(hour=12), provider=provider)
    assert result["status"] == "known_period" and result["period_start"] == start.isoformat()
    assert result["provider"]["library_version"] == sdk and result["coverage_complete"] is False


@pytest.mark.parametrize("version", ["1.5.4", "1.5.5", "2.0.0"])
def test_release_label_cannot_replace_missing_runtime_semantic_proof(version, monkeypatch):
    env = modern_setup(monkeypatch, version=version)
    env.helper._display_metadata["compatibility"] = None
    env.coordinator.poll()
    result = env.helper.read_source_contract(env.sources)
    assert result["status"] == "unknown" and result["contract_id"] is None
    assert result["reason_code"] == "provider_semantics_unavailable"


def test_old_unknown_future_version_is_not_promoted_by_contemporary_inspection(monkeypatch, tmp_path):
    loaded_sources(monkeypatch, tmp_path)
    assert inspect_loaded_aquarea_semantics()["compatibility_state"] == "compatible"
    raw = contract_snapshot()["source_contract"]
    raw["provider"].update(integration_version="1.5.5", library_version="1.3.2")
    raw.update(status="unknown", contract_id=None, action_semantics="unknown")
    clean = contract_evidence(raw, NOW, 120)
    assert clean["verified"] is False and clean["contract_id"] is None
    assert "compatibility" not in clean
    assert retained_contract_evidence(deepcopy(clean), NOW, 120) == clean


def test_stored_semantic_proof_stays_closed_and_bound_to_original_capture(monkeypatch, tmp_path):
    loaded_sources(monkeypatch, tmp_path)
    raw = contract_snapshot()["source_contract"]
    raw.update(inspect_loaded_aquarea_semantics())
    raw["provider"].update(integration_version="2.0.0", library_version="2.0.0")
    clean = contract_evidence(raw, NOW, 120)
    assert clean["verified"]
    for change in ("private_extra", "false_verified", "numeric_schema", "bad_fingerprint"):
        forged = deepcopy(clean)
        if change == "private_extra": forged["compatibility"]["device_id"] = "private"
        elif change == "false_verified": forged["compatibility"]["verified"] = False
        elif change == "numeric_schema": forged["compatibility"]["schema"] = True
        else: forged["compatibility"]["fingerprint"] = "not a digest"
        with pytest.raises(ValueError): retained_contract_evidence(forged, NOW, 120)
    stale = contract_evidence(raw, NOW+121, 120)
    assert stale["verified"] is False and stale["observed_at"] == clean["observed_at"]


def test_semantic_source_inspection_has_explicit_size_bound(monkeypatch, tmp_path):
    loaded_sources(monkeypatch, tmp_path)
    import custom_components.solar_pilot.operation_source_evidence as module
    monkeypatch.setattr(module.inspect, "getsource", lambda _: " "*131073)
    assert module.inspect_loaded_aquarea_semantics()["compatibility_state"] == "unknown"


def test_source_code_replacement_revokes_cached_proof_before_its_age_limit(monkeypatch, tmp_path):
    loaded_sources(monkeypatch, tmp_path)
    env = modern_setup(monkeypatch, version="2.0.0")
    assert env.helper._contract_metadata()["compatibility"]["verified"]
    module = sys.modules["aioaquarea.device_manager"]
    original = module.DeviceManager.get_device_status
    monkeypatch.setattr(module.DeviceManager, "get_device_status", lambda self, device_info: None)
    assert loaded_semantic_identity() != env.helper._display_semantic_identity
    assert env.helper._contract_metadata() == {}
    monkeypatch.setattr(module.DeviceManager, "get_device_status", original)


def test_semantic_mismatch_has_production_reason_and_action(monkeypatch):
    env = modern_setup(monkeypatch, version="2.0.0")
    env.helper._display_metadata.update(compatibility=None, compatibility_state="incompatible",
        reason_code="provider_semantics_changed", compatibility_detail="operation_status_no_longer_special_status")
    result = env.helper.read_source_contract(env.sources)
    assert result["native_device_registered"] is True and result["provider_loaded"] is True
    assert result["compatibility_state"] == "incompatible" and result["reason_code"] == "provider_semantics_changed"
    assert result["reason"] and result["action"] and len(result["reason"]) < 300 and len(result["action"]) < 300


def test_changed_loaded_exception_routing_cannot_match_unchanged_source(monkeypatch, tmp_path):
    _, manager, _ = loaded_sources(monkeypatch, tmp_path)
    function = manager.DeviceManager.get_device_status
    code = function.__code__
    function.__code__ = code.replace(co_exceptiontable=b"\x00")
    assert inspect_loaded_aquarea_semantics()["compatibility_state"] == "unknown"


def test_current_loaded_semantics_cannot_be_applied_to_superseded_active_device_class(monkeypatch):
    env = modern_setup(monkeypatch, version="2.0.0")
    env.helper.read_source_contract(env.sources)
    env.coordinator.poll()
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"
    old = type(env.coordinator.device)
    env.helper._display_metadata["_loaded_device_class"] = type(old.__name__, (), {"__module__": old.__module__})
    result = env.helper.read_source_contract(env.sources)
    assert result["status"] == "unknown" and result["reason_code"] == "native_loaded_device_type_changed"
    assert env.helper._watches == {} and env.helper._tank_watches == {}
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []
