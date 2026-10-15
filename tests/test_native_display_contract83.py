"""Actual-role, pinned-version, fresh provider snapshots using fictional data."""
from dataclasses import fields, make_dataclass
from enum import IntEnum
import sys
from types import SimpleNamespace as NS

import pytest

from test_cooling_native80 import (AquareaDataUpdateCoordinator as BaseCoordinator,
    DeviceImpl as BaseDevice, DeviceStatus as BaseStatus, OperationStatus)
from test_native_display_sources67 import display_setup
from test_native_tank_action66 import DeviceAction, DeviceDirection
from test_native_program56 import ExtendedOperationMode

PumpDuty = IntEnum("PumpDuty", {"OFF": 0, "ON": 1}, module="aioaquarea.data")
Status = make_dataclass("DeviceStatus", [field.name for field in fields(BaseStatus)]+["pump_duty"], module="aioaquarea.data")
Zone = type("DeviceZone", (), {"__module__": "aioaquarea.data", "operation_status": property(lambda self:self._status.operation_status)})


class DeviceImpl(BaseDevice):
    __module__ = "aioaquarea.core"

    def replace_status(self, mode=ExtendedOperationMode.HEAT, direction=DeviceDirection.PUMP, *, pump=PumpDuty.ON, preset=0):
        super().replace_status(mode, direction)
        old = self._status
        self._status = Status(*(getattr(old, field.name) for field in fields(BaseStatus)), pump)
        self._status.operation_status = OperationStatus.OFF if preset == 0 else OperationStatus.ON
        self.zones = {row.zone_id: Zone() for row in self._status.zones}
        for row in self._status.zones:
            row.operation_status = OperationStatus.ON
            zone = self.zones[row.zone_id]
            zone.zone_id, zone._status = row.zone_id, row
            zone._info = next(info for info in self._info.zones if info.zone_id == row.zone_id)

    pump_duty = property(lambda self:self._status.pump_duty)


class AquareaDataUpdateCoordinator(BaseCoordinator):
    __module__ = "custom_components.aquarea.coordinator"

    def __init__(self, hass, entry):
        super().__init__(hass, entry)
        self.device = DeviceImpl(self._device_info)

    def poll(self, *, pump=PumpDuty.ON, direction=DeviceDirection.PUMP, preset=0):
        self.device.replace_status(direction=direction, pump=pump, preset=preset)
        self.notify()


def setup_contract(monkeypatch, *, version="1.5.2"):
    env = display_setup(monkeypatch)
    entry = env.entries["native"]
    entry.runtime_data = None
    coordinator = AquareaDataUpdateCoordinator(env.helper.runtime.hass, entry)
    env.helper.runtime.hass.data = {"aquarea": {"native": {"devices": {"pump": coordinator}}}}
    pump_id = "sensor.synthetic_water_pump"
    env.rows[pump_id] = NS(entity_id=pump_id, unique_id="pump_pump_status", platform="aquarea",
                          config_entry_id="native", device_id="registry_pump", disabled_by=None)
    env.state(pump_id, "On")
    env.state(env.sources["direction_entity"], "PUMP")
    for eid in env.sources["zone_entities"]:
        env.state(eid, "heat", {"hvac_action": "off"})
    env.helper._display_metadata = {"integration_loaded": True, "integration_domain": "aquarea", "integration_version": version,
                                   "library_distribution": "aioaquarea-ng", "library_version": "1.3.1"}
    env.helper._display_metadata_checked = env.clock[0]
    env.helper._display_metadata_module = sys.modules.get("custom_components.aquarea")
    env.sources = env.helper.display_sources()
    env.coordinator = coordinator
    return env


@pytest.mark.parametrize("version", ["1.5.2", "1.5.3", "1.5.4"])
def test_exact_registered_pump_role_is_read_only_and_needs_real_successful_poll(version, monkeypatch):
    env = setup_contract(monkeypatch, version=version)
    assert env.sources["pump_status_entity"] == "sensor.synthetic_water_pump"
    first = env.helper.read_source_contract(env.sources)
    assert first["status"] == "unknown" and first["reason_code"] == "native_poll_not_current"
    env.coordinator.poll()
    result = env.helper.read_source_contract(env.sources)
    assert result["status"] == "verified" and result["action_semantics"] == "special_status"
    assert result["raw_device_action"] == "OFF"  # Native input is retained without rewriting.
    assert result["pump"]["state"] == "on" and result["pump"]["observed_at"] == 990
    assert result["direction"]["state"] == "PUMP" and result["direction"]["observed_at"] == 990
    assert result["observed_at"] == 1000 and result["tank"]["enabled"] is True
    assert all(row["enabled"] is True for row in result["zones"])
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []
    assert not env.helper._watches  # New display proof is never controller-programme permission.


@pytest.mark.parametrize("case", ["pump_uid", "pump_device", "pump_entry", "duplicate_role", "pump_disabled", "wrong_provider_version", "wrong_distribution", "wrong_library_version", "raw_duty", "duty_unknown_enum", "state_conflict", "direction_conflict", "old_pump"])
def test_unverified_mapping_version_or_actual_pump_identity_never_qualifies_display(case, monkeypatch):
    env = setup_contract(monkeypatch)
    pump = env.sources["pump_status_entity"]
    env.helper.read_source_contract(env.sources)
    env.coordinator.poll()
    if case == "pump_uid":env.rows[pump].unique_id = "pump_status_like_name"
    elif case == "pump_device":env.rows[pump].device_id = "other_device"
    elif case == "pump_entry":env.rows[pump].config_entry_id = "other_entry"
    elif case == "duplicate_role":
        env.rows["sensor.synthetic_duplicate"] = NS(**{**vars(env.rows[pump]), "entity_id": "sensor.synthetic_duplicate"})
        env.sources = env.helper.display_sources()
    elif case == "pump_disabled":env.rows[pump].disabled_by = "user"
    elif case == "wrong_provider_version":env.helper._display_metadata["integration_version"] = "1.5.5"
    elif case == "wrong_distribution":env.helper._display_metadata["library_distribution"] = "aioaquarea"
    elif case == "wrong_library_version":env.helper._display_metadata["library_version"] = "1.3.2"
    elif case == "raw_duty":env.coordinator.device._status.pump_duty = 1
    elif case == "duty_unknown_enum":env.coordinator.device._status.pump_duty = IntEnum("PumpDuty", {"ON":1}, module="unrelated.data").ON
    elif case == "state_conflict":env.state(pump, "Off")
    elif case == "direction_conflict":env.state(env.sources["direction_entity"], "WATER")
    else:env.state(pump, "On", stamp=800)
    result = env.helper.read_source_contract(env.sources)
    assert result["status"] == "unknown" and result["reason_code"]
    if case == "old_pump":assert result["pump"]["observed_at"] == 800


@pytest.mark.parametrize("field", ["pump", "direction", "zone", "tank", "mode"])
def test_unpolled_optimistic_native_inputs_revoke_composite_poll_proof(field, monkeypatch):
    env = setup_contract(monkeypatch)
    env.helper.read_source_contract(env.sources)
    env.coordinator.poll()
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"
    device = env.coordinator.device
    if field == "pump":device._status.pump_duty = PumpDuty.OFF
    elif field == "direction":device._status.direction = DeviceDirection.WATER
    elif field == "zone":device.zones[1]._status.operation_status = OperationStatus.OFF
    elif field == "tank":device.tank._status.operation_status = OperationStatus.OFF
    else:device._status.operation_mode = ExtendedOperationMode.COOL
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.poll()
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"


def test_metadata_age_or_loaded_module_change_is_unknown_until_new_executor_snapshot(monkeypatch):
    env = setup_contract(monkeypatch)
    env.helper.read_source_contract(env.sources)
    env.coordinator.poll()
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"
    env.clock[0] += 301
    expired = env.helper.read_source_contract(env.sources)
    assert expired["status"] == "unknown" and expired["native_device_registered"] is True
    env.helper._display_metadata_checked = env.clock[0]
    monkeypatch.setitem(sys.modules, "custom_components.aquarea", NS())
    changed = env.helper.read_source_contract(env.sources)
    assert changed["status"] == "unknown" and changed["native_device_registered"] is True


def test_close_clears_contract_and_poll_watches_without_device_fetch(monkeypatch):
    env = setup_contract(monkeypatch)
    env.helper.read_source_contract(env.sources)
    env.coordinator.poll()
    env.helper.close()
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    assert env.coordinator.listeners == [] and env.coordinator.api_calls == []
