"""Pinned provider dual-fetch shape, using fictional device and source data.

Verified contracts: Aquarea v1.5.2 coordinator.get_device + refresh_data;
aioaquarea-ng v1.3.1 Device.__build_zones__ and DeviceImpl.refresh_data.
The latter replaces status/tank without rebuilding zone objects. An offline
reproduction with the actual upstream classes independently confirms this
shape; these fixtures keep the regression deterministic without dependencies.
"""
from dataclasses import fields, make_dataclass
from enum import IntEnum
import sys
from types import SimpleNamespace as NS

import pytest

from test_native_display_sources67 import display_setup
from test_native_program56 import ExtendedOperationMode
from test_native_tank_action66 import DeviceAction, DeviceDirection

def record(name, names):
    return make_dataclass(name, [(field, object, None) for field in names.split()], module="aioaquarea.data")

OperationStatus = IntEnum("OperationStatus", {"OFF": 0, "ON": 1, "UNKNOWN": 2}, module="aioaquarea.data")
PumpDuty = IntEnum("PumpDuty", {"OFF": 0, "ON": 1}, module="aioaquarea.data")
DeviceInfo = record("DeviceInfo", "device_id name long_id mode has_tank firmware_version model zones status_data_mode")
DeviceZoneInfo = record("DeviceZoneInfo", "zone_id name type cool_mode zone_sensor heat_sensor cool_sensor")
DeviceZoneStatus = record("DeviceZoneStatus", "zone_id temperature operation_status heat_max heat_min heat_set cool_max cool_min cool_set comfort_heat comfort_cool eco_heat eco_cool")
TankStatus = record("TankStatus", "operation_status temperature heat_max heat_min heat_set")
DeviceStatus = record("DeviceStatus", "long_id operation_status device_status temperature_outdoor operation_mode fault_status direction pump_duty tank_status zones quiet_mode force_dhw force_heater holiday_timer powerful_time special_status water_pressure")

class DeviceZone:
    __module__ = "aioaquarea.data"
    def __init__(self, info, status):
        self._info, self._status = info, status
    zone_id = property(lambda self: self._info.zone_id)
    operation_status = property(lambda self: self._status.operation_status)

class TankImpl:
    __module__ = "aioaquarea.entities"
    def __init__(self, device, status):
        self._device, self._status = device, status
    operation_status = property(lambda self: self._status.operation_status)

class DeviceImpl:
    __module__ = "aioaquarea.entities"
    _zones = {}
    def __init__(self, info, first):
        self._info, self._status = info, first
        for row in info.zones:
            self._zones[row.zone_id] = DeviceZone(row, next(status for status in first.zones if status.zone_id == row.zone_id))
        self._tank = TankImpl(self, first.tank_status[0]) if info.has_tank else None
    def second_fetch(self, latest):
        self._status = latest
        if self.has_tank:
            self._tank = TankImpl(self, latest.tank_status[0])
    device_id = property(lambda self: self._info.device_id)
    long_id = property(lambda self: self._info.long_id)
    mode = property(lambda self: self._status.operation_mode)
    operation_status = property(lambda self: self._status.operation_status)
    current_direction = property(lambda self: self._status.direction)
    pump_duty = property(lambda self: self._status.pump_duty)
    has_tank = property(lambda self: self._info.has_tank)
    tank = property(lambda self: self._tank)
    zones = property(lambda self: self._zones)
    device_mode_status = property(lambda self: self._status.device_status)
    @property
    def current_action(self):
        if self.operation_status == OperationStatus.OFF:
            return DeviceAction.OFF
        if self.current_direction == DeviceDirection.WATER and self.tank.operation_status == OperationStatus.ON:
            return DeviceAction.HEATING_WATER
        if self.current_direction == DeviceDirection.PUMP:
            return DeviceAction.HEATING if self.mode in (ExtendedOperationMode.HEAT, ExtendedOperationMode.AUTO_HEAT) else DeviceAction.COOLING
        return DeviceAction.IDLE

def status(info, *, mode=ExtendedOperationMode.HEAT, enabled=(True, True), pump=PumpDuty.ON,
           direction=DeviceDirection.PUMP, tank_on=True):
    return DeviceStatus(long_id=info.long_id, operation_status=OperationStatus.OFF, operation_mode=mode,
        direction=direction, pump_duty=pump, fault_status=[],
        zones=[DeviceZoneStatus(zone_id=row.zone_id, operation_status=OperationStatus.ON if on else OperationStatus.OFF)
               for row, on in zip(info.zones, enabled)],
        tank_status=[TankStatus(operation_status=OperationStatus.ON if tank_on else OperationStatus.OFF)] if info.has_tank else [])

class AquareaDataUpdateCoordinator:
    __module__ = "custom_components.aquarea.coordinator"
    def __init__(self, hass, entry):
        self.hass, self._entry = hass, entry
        self._device_info = DeviceInfo(device_id="pump", long_id="pump", has_tank=True,
                                      zones=[DeviceZoneInfo(zone_id=1), DeviceZoneInfo(zone_id=2)])
        self.listeners, self.api_calls = [], []
        self.last_update_success = True
        self.poll(notify=False)
    device_info = property(lambda self: self._device_info)
    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)
    def notify(self, *, success=True):
        self.last_update_success = success
        for listener in tuple(self.listeners):
            listener()
    def poll(self, *, mode=ExtendedOperationMode.HEAT, enabled=(True,True), pump=PumpDuty.ON,
             direction=DeviceDirection.PUMP, tank_on=True, first_mode=ExtendedOperationMode.COOL,
             first_enabled=(False,False), notify=True, success=True):
        first = status(self._device_info, mode=first_mode, enabled=first_enabled)
        self.device = DeviceImpl(self._device_info, first)
        latest = status(self._device_info, mode=mode, enabled=enabled, pump=pump, direction=direction, tank_on=tank_on)
        self.device.second_fetch(latest)
        if notify:
            self.notify(success=success)

def modern_setup(monkeypatch, *, version="1.5.2"):
    monkeypatch.setattr(DeviceImpl, "_zones", {})
    env = display_setup(monkeypatch)
    entry = env.entries["native"]
    env.coordinator = AquareaDataUpdateCoordinator(env.helper.runtime.hass, entry)
    entry.runtime_data = {"pump": env.coordinator}
    pump_id = "sensor.pump_pump_status"
    env.rows[pump_id] = NS(entity_id=pump_id, unique_id="pump_pump_status", platform="aquarea",
                          config_entry_id="native", device_id="registry_pump", disabled_by=None)
    env.state(pump_id,"On")
    env.state(env.sources["direction_entity"],"PUMP")
    for eid in env.sources["zone_entities"]:
        env.state(eid,"heat",{"hvac_action":"off"})
    env.state(env.sources["tank_entity"],"idle",{"operation_mode":"idle"})
    env.sources = env.helper.display_sources()
    env.helper._display_metadata = {"integration_loaded":True,"integration_domain":"aquarea",
        "integration_version":version,"library_distribution":"aioaquarea-ng","library_version":"1.3.1"}
    env.helper._display_metadata_checked = env.clock[0]
    env.helper._display_metadata_module = sys.modules.get("custom_components.aquarea")
    env.data = NS(OperationStatus=OperationStatus, PumpDuty=PumpDuty, ExtendedOperationMode=ExtendedOperationMode,
                  DeviceDirection=DeviceDirection, DeviceZoneInfo=DeviceZoneInfo, DeviceZoneStatus=DeviceZoneStatus,
                  DeviceStatus=DeviceStatus, DeviceInfo=DeviceInfo, DeviceImpl=DeviceImpl, TankStatus=TankStatus,
                  TankImpl=TankImpl, fields=fields)
    return env

@pytest.mark.parametrize("version",["1.5.2","1.5.3","1.5.4"])
def test_current_second_response_drives_display_without_repairing_old_zone_objects(version,monkeypatch):
    env=modern_setup(monkeypatch,version=version)
    assert env.helper.read_source_contract(env.sources)["reason_code"] == "native_poll_not_current"
    assert env.helper._legacy_status(env.coordinator,env.entries["native"]) is None
    env.coordinator.poll()
    result=env.helper.read_source_contract(env.sources)
    assert result["status"] == "verified" and result["program"]["raw_mode"] == "HEAT"
    assert all(row["enabled"] is True for row in result["zones"])
    assert all(row.operation_status == OperationStatus.ON for row in env.coordinator.device._status.zones)
    assert all(row.operation_status == OperationStatus.OFF for row in env.coordinator.device.zones.values())
    assert env.helper._legacy_status(env.coordinator,env.entries["native"]) is None
    assert env.helper._watches == {} and env.helper._tank_watches == {}
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []

def test_modern_control_programme_permission_uses_its_existing_own_watch(monkeypatch):
    env=modern_setup(monkeypatch)
    eid=env.sources["zone_entities"][0]
    assert not env.helper.read(eid)["fresh"]
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.poll(mode=ExtendedOperationMode.COOL)
    assert env.helper.read(eid)["fresh"] and env.helper.read(eid)["program"] == "cooling"
    # HA zone state still reports HEAT, so only the optional display is refused.
    assert env.helper.read_source_contract(env.sources)["reason_code"] == "native_zone_source_value_conflict"

def test_close_unsubscribes_display_journal_without_native_or_device_writes(monkeypatch):
    env=modern_setup(monkeypatch)
    env.helper.read_source_contract(env.sources)
    assert len(env.coordinator.listeners) == 1
    env.helper.close()
    assert not env.coordinator.listeners and env.helper._display_contract_watches == {}
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
