"""Fictional verified legacy polls; no cloud request, config or actuator call."""
from dataclasses import make_dataclass
from enum import IntEnum
from types import SimpleNamespace as NS

import pytest

from test_native_program56 import ExtendedOperationMode, native_program, setup
from test_native_tank_action66 import DeviceAction, DeviceDirection
from test_runtime import States


OperationStatus = IntEnum("OperationStatus", {"OFF": 0, "ON": 1}, module="aioaquarea.data")
DeviceModeStatus = IntEnum("DeviceModeStatus", {"NORMAL": 0, "DEFROST": 1}, module="aioaquarea.data")
DeviceZoneInfo = make_dataclass("DeviceZoneInfo", ["zone_id"], module="aioaquarea.data")
DeviceZoneStatus = make_dataclass("DeviceZoneStatus", ["zone_id", "operation_status"], module="aioaquarea.data")
DeviceInfo = make_dataclass("DeviceInfo", ["device_id", "long_id", "zones", ("has_tank", bool, True)], module="aioaquarea.data")
TankStatus = make_dataclass("TankStatus", ["operation_status", "temperature"], module="aioaquarea.data")
DeviceStatus = make_dataclass("DeviceStatus", ["long_id", "operation_mode", "operation_status", "direction",
    "device_status", "zones", "tank_status"], module="aioaquarea.data")
DeviceZone = type("DeviceZone", (), {"__module__": "aioaquarea.data"})


class TankImpl:
    __module__ = "aioaquarea.core"

    def __init__(self, device, status):
        self._device, self._status = device, status

    operation_status = property(lambda self: self._status.operation_status)


class DeviceImpl:
    __module__ = "aioaquarea.core"

    def __init__(self, info, mode=ExtendedOperationMode.HEAT):
        self._info = info
        self.replace_status(mode)

    def replace_status(self, mode=ExtendedOperationMode.HEAT, direction=DeviceDirection.WATER):
        self._status = DeviceStatus(self.long_id, mode, OperationStatus.ON, direction,
            DeviceModeStatus.NORMAL, [DeviceZoneStatus(1, OperationStatus.OFF),
                                     DeviceZoneStatus(2, OperationStatus.OFF)],
            [TankStatus(OperationStatus.ON, 47)])
        self.zones = {}
        for row in self._status.zones:
            zone = DeviceZone()
            zone.zone_id = row.zone_id
            zone._info = next(info for info in self._info.zones if info.zone_id == row.zone_id)
            zone._status = row
            self.zones[row.zone_id] = zone
        self.tank = TankImpl(self, self._status.tank_status[0]) if self.has_tank else None

    device_id = property(lambda self: self._info.device_id)
    long_id = property(lambda self: self._info.long_id)
    mode = property(lambda self: self._status.operation_mode)
    operation_status = property(lambda self: self._status.operation_status)
    current_direction = property(lambda self: self._status.direction)
    device_mode_status = property(lambda self: self._status.device_status)
    has_tank = property(lambda self: self._info.has_tank)

    @property
    def current_action(self):
        if self.operation_status is OperationStatus.OFF:
            return DeviceAction.OFF
        if self.current_direction is DeviceDirection.WATER:
            return DeviceAction.HEATING_WATER
        if self.current_direction is DeviceDirection.IDLE:
            return DeviceAction.IDLE
        return (DeviceAction.COOLING if self.mode in (ExtendedOperationMode.COOL, ExtendedOperationMode.AUTO_COOL)
                else DeviceAction.HEATING)


class AquareaDataUpdateCoordinator:
    __module__ = "custom_components.aquarea.coordinator"

    def __init__(self, hass, entry):
        self.hass, self._entry = hass, entry
        self._device_info = DeviceInfo("pump", "opaque-long-id", [DeviceZoneInfo(1), DeviceZoneInfo(2)])
        self.device = DeviceImpl(self._device_info)
        self.last_update_success = True
        self.listeners, self.api_calls = [], []

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)

    def notify(self, success=True):
        self.last_update_success = success
        for listener in tuple(self.listeners):
            listener()

    def poll(self, mode=ExtendedOperationMode.HEAT, *, success=True, direction=DeviceDirection.WATER):
        self.device.replace_status(mode, direction)
        self.notify(success)


def legacy_setup(monkeypatch):
    helper, _unused, rows, entries, clock = setup(monkeypatch, stale_s=120)
    entry = entries["native"]
    entry.runtime_data = None
    coordinator = AquareaDataUpdateCoordinator(helper.runtime.hass, entry)
    helper.runtime.hass.data = {"aquarea": {"native": {"devices": {"pump": coordinator}}}}
    helper.runtime.hass.states = States()
    helper.runtime.hass.states.set("climate.salon", "off", {"hvac_action": "idle"})
    helper.runtime.hass.states.set("water_heater.tank", "heating")
    rows["water_heater.tank"] = NS(platform="aquarea", config_entry_id="native", unique_id="pump_tank")
    monkeypatch.setattr(native_program.time, "time", lambda: clock[0])
    return helper, coordinator, rows, entries, clock


def test_exact_legacy_startup_is_unknown_until_status_replacement_on_success(monkeypatch):
    helper, coordinator, *_ = legacy_setup(monkeypatch)
    old_device, old_status = coordinator.device, coordinator.device._status
    initial = helper.read("climate.salon")
    assert not initial["fresh"] and initial["reason_code"] == "awaiting_poll"
    coordinator.notify()
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll()
    result = helper.read("climate.salon")
    assert coordinator.device is old_device and coordinator.device._status is not old_status
    assert result["fresh"] and result["program"] == "heating" and result["raw_mode"] == "HEAT"
    assert result["reason_code"] == "confirmed" and result["stale_s"] == 120
    assert result["observed_at"] == 1000 and result["source"] == "aquarea_poll"
    assert not coordinator.api_calls


@pytest.mark.parametrize("mode,expected", [(ExtendedOperationMode.OFF, "off"),
    (ExtendedOperationMode.HEAT, "heating"), (ExtendedOperationMode.AUTO_HEAT, "heating"),
    (ExtendedOperationMode.COOL, "cooling"), (ExtendedOperationMode.AUTO_COOL, "cooling")])
def test_legacy_native_program_survives_off_zones_and_water_route(monkeypatch, mode, expected):
    helper, coordinator, *_ = legacy_setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll(mode)
    result = helper.read("climate.salon")
    assert result["fresh"] and result["program"] == expected
    assert helper.runtime.hass.states.get("climate.salon").state == "off"
    assert coordinator.device.current_action is DeviceAction.HEATING_WATER


@pytest.mark.parametrize("case", ["coordinator_module", "coordinator_class", "entry_object", "hass_object",
    "device_class", "device_module", "info_type", "device_info_type", "status_type", "mapping_key",
    "device_id", "long_id", "native_long_id", "status_long_id", "zone_key", "zone_bool", "zone_object",
    "zone_info", "zone_status", "zone_duplicate", "neighbor_zone_info", "neighbor_zone_status",
    "has_tank_bool", "tank_type", "tank_status_type", "tank_neighbor_status", "tank_neighbor_device",
    "wrong_entry_namespace", "wrong_zone", "disabled"])
def test_legacy_compatibility_is_narrow_and_never_guesses_identity(monkeypatch, case):
    helper, coordinator, rows, entries, _ = legacy_setup(monkeypatch)
    if case == "coordinator_module":
        coordinator.__class__ = type("AquareaDataUpdateCoordinator", (AquareaDataUpdateCoordinator,), {"__module__": "other.coordinator"})
    elif case == "coordinator_class":
        coordinator.__class__ = type("UnknownCoordinator", (AquareaDataUpdateCoordinator,), {"__module__": "custom_components.aquarea.coordinator"})
    elif case == "entry_object":
        coordinator._entry = NS(**vars(entries["native"]))
    elif case == "hass_object":
        coordinator.hass = NS()
    elif case in ("device_class", "device_module"):
        coordinator.device.__class__ = type("OtherDevice" if case == "device_class" else "DeviceImpl", (DeviceImpl,),
            {"__module__": "aioaquarea.core" if case == "device_class" else "other.core"})
    elif case == "info_type":
        coordinator._device_info = NS(**vars(coordinator._device_info))
    elif case == "device_info_type":
        coordinator.device._info = NS(**vars(coordinator.device._info))
    elif case == "status_type":
        coordinator.device._status = NS(**vars(coordinator.device._status))
    elif case == "mapping_key":
        helper.runtime.hass.data["aquarea"]["native"]["devices"] = {"other": coordinator}
    elif case == "device_id":
        coordinator.device._info.device_id = "other"
    elif case == "long_id":
        coordinator._device_info.long_id = "other"
    elif case == "native_long_id":
        coordinator.device._info = DeviceInfo("pump", "other", coordinator._device_info.zones)
    elif case == "status_long_id":
        coordinator.device._status.long_id = "other"
    elif case == "zone_key":
        coordinator.device.zones[3] = coordinator.device.zones.pop(2)
    elif case == "zone_bool":
        coordinator.device.zones = {True: coordinator.device.zones[1], 2: coordinator.device.zones[2]}
    elif case == "zone_object":
        coordinator.device.zones[2] = NS(zone_id=2)
    elif case == "zone_info":
        coordinator._device_info.zones[1] = NS(zone_id=2)
    elif case == "zone_status":
        coordinator.device._status.zones[1] = NS(zone_id=2)
    elif case == "zone_duplicate":
        coordinator.device._status.zones[1].zone_id = 1
    elif case == "neighbor_zone_info":
        coordinator.device.zones[2]._info = DeviceZoneInfo(2)
    elif case == "neighbor_zone_status":
        coordinator.device.zones[2]._status = DeviceZoneStatus(2, OperationStatus.OFF)
    elif case == "has_tank_bool":
        coordinator.device._info.has_tank = 1
    elif case == "tank_type":
        coordinator.device.tank = NS(_device=coordinator.device, _status=coordinator.device._status.tank_status[0])
    elif case == "tank_status_type":
        coordinator.device._status.tank_status[0] = NS(operation_status=OperationStatus.ON, temperature=47)
    elif case == "tank_neighbor_status":
        coordinator.device.tank._status = TankStatus(OperationStatus.ON, 47)
    elif case == "tank_neighbor_device":
        coordinator.device.tank._device = DeviceImpl(coordinator._device_info)
    elif case == "wrong_entry_namespace":
        helper.runtime.hass.data["aquarea"] = {"other": helper.runtime.hass.data["aquarea"]["native"]}
    elif case == "wrong_zone":
        rows["climate.salon"].unique_id = "pump_climate_3"
    else:
        rows["climate.salon"].disabled_by = "user"
    assert not helper.read("climate.salon")["fresh"]
    assert not coordinator.listeners and not coordinator.api_calls


def test_legacy_same_status_listener_cannot_renew_bounded_freshness(monkeypatch):
    helper, coordinator, _rows, _entries, clock = legacy_setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    clock[0] += 121
    coordinator.notify()
    result = helper.read("climate.salon")
    assert not result["fresh"] and result["reason_code"] == "stale_poll"
    coordinator.poll()
    assert helper.read("climate.salon")["fresh"]


@pytest.mark.parametrize("invalid", [1, "HEAT", NS(name="HEAT", value=1),
    IntEnum("OperationMode", {"HEAT": 1}, module="aioaquarea.data").HEAT,
    IntEnum("ExtendedOperationMode", {"HEAT": 8}, module="aioaquarea.data").HEAT,
    IntEnum("ExtendedOperationMode", {"HEAT": 1}, module="other.data").HEAT])
def test_legacy_typed_status_does_not_bypass_specific_programme_enum(monkeypatch, invalid):
    helper, coordinator, *_ = legacy_setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll(invalid)
    result = helper.read("climate.salon")
    assert not result["fresh"] and result["program"] == "unknown"


@pytest.mark.parametrize("field", ["operation_mode", "direction", "operation_status", "nested_zone", "tank_temperature"])
def test_legacy_optimistic_status_mutation_loses_proof_until_new_poll(monkeypatch, field):
    helper, coordinator, *_ = legacy_setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    status = coordinator.device._status
    if field == "nested_zone":
        target, key, value = status.zones[0], "operation_status", OperationStatus.ON
    elif field == "tank_temperature":
        target, key, value = status.tank_status[0], "temperature", 55
    else:
        target, key, value = status, field, {"operation_mode": ExtendedOperationMode.COOL,
            "direction": DeviceDirection.PUMP, "operation_status": OperationStatus.OFF}[field]
    old = getattr(target, key)
    setattr(target, key, value)
    coordinator.notify()
    assert not helper.read("climate.salon")["fresh"]
    setattr(target, key, old)
    coordinator.notify()
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll()
    assert helper.read("climate.salon")["fresh"]


@pytest.mark.parametrize("notified", [False, True])
def test_legacy_failure_never_revives_its_status_by_flipping_success(monkeypatch, notified):
    helper, coordinator, *_ = legacy_setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    coordinator.device.replace_status(ExtendedOperationMode.COOL)
    if notified:
        coordinator.notify(False)
    else:
        coordinator.last_update_success = False
    assert not helper.read("climate.salon")["fresh"]
    coordinator.notify(True)
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll(ExtendedOperationMode.AUTO_COOL)
    assert helper.read("climate.salon")["program"] == "cooling"


def test_legacy_unnotified_status_replacement_is_not_a_fresh_report(monkeypatch):
    helper, coordinator, *_ = legacy_setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    coordinator.device.replace_status(ExtendedOperationMode.COOL)
    assert not helper.read("climate.salon")["fresh"]
    coordinator.notify()
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll()
    assert helper.read("climate.salon")["fresh"]


def test_legacy_reload_and_unload_require_the_new_coordinator_poll(monkeypatch):
    helper, old, _rows, entries, _clock = legacy_setup(monkeypatch)
    helper.read("climate.salon")
    old.poll()
    binding = helper.read("climate.salon")["binding_key"]
    new = AquareaDataUpdateCoordinator(helper.runtime.hass, entries["native"])
    helper.runtime.hass.data["aquarea"]["native"]["devices"] = {"pump": new}
    assert not helper.read("climate.salon")["fresh"] and not old.listeners
    new.poll()
    assert helper.read("climate.salon")["binding_key"] == binding
    assert helper.read("climate.salon")["fresh"]
    helper.runtime.hass.data["aquarea"].pop("native")
    assert not helper.read("climate.salon")["fresh"] and not new.listeners


def test_legacy_unmatched_binding_discards_old_rights_without_choosing_neighbor(monkeypatch):
    helper, coordinator, rows, entries, *_ = legacy_setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    # A similar native device ID is not a substitute for the registered zone.
    second = AquareaDataUpdateCoordinator(helper.runtime.hass, entries["native"])
    second._device_info.device_id = "pump_climate"
    second.device.replace_status()
    helper.runtime.hass.data["aquarea"]["native"]["devices"]["pump_climate"] = second
    assert helper.read("climate.salon")["fresh"]
    rows["climate.salon"].unique_id = "unmatched"
    assert not helper.read("climate.salon")["fresh"] and not coordinator.listeners
    rows["climate.salon"].unique_id = "pump_climate_2"
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll()
    assert helper.read("climate.salon")["fresh"]


def test_legacy_tank_action_status_poll_is_separate_from_programme_proof(monkeypatch):
    helper, coordinator, *_ = legacy_setup(monkeypatch)
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    coordinator.poll(ExtendedOperationMode.AUTO_COOL)
    tank = helper.read_tank_action("water_heater.tank")
    assert tank["fresh"] and tank["action"] == "tapwater_heating" and tank["raw_mode"] == "AUTO_COOL"
    assert not helper.read("climate.salon")["fresh"]
    coordinator.notify()
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll(ExtendedOperationMode.AUTO_HEAT)
    assert helper.read("climate.salon")["program"] == "heating"
    coordinator.device._status.direction = DeviceDirection.PUMP
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    assert not coordinator.api_calls


def test_legacy_display_action_ignores_optimistic_and_failed_status_renewal(monkeypatch):
    helper, coordinator, *_ = legacy_setup(monkeypatch)
    helper.read_tank_action("water_heater.tank")
    coordinator.poll()
    assert helper.read_tank_action("water_heater.tank")["fresh"]
    coordinator.device.replace_status(direction=DeviceDirection.PUMP)
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    coordinator.notify()
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    coordinator.poll(success=False)
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    coordinator.notify(True)
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    coordinator.poll()
    assert helper.read_tank_action("water_heater.tank")["fresh"]


def test_verified_later_library_module_uses_the_same_status_contract(monkeypatch):
    helper, coordinator, *_ = legacy_setup(monkeypatch)
    coordinator.device.__class__ = type("DeviceImpl", (DeviceImpl,), {"__module__": "aioaquarea.entities"})
    helper.read("climate.salon")
    coordinator.poll()
    assert helper.read("climate.salon")["fresh"]


@pytest.mark.parametrize("case", ["neighbor_status", "neighbor_device", "same_value_status"])
def test_legacy_tank_display_cannot_use_a_neighbor_or_detached_snapshot(monkeypatch, case):
    helper, coordinator, *_ = legacy_setup(monkeypatch)
    helper.read_tank_action("water_heater.tank")
    coordinator.poll()
    assert helper.read_tank_action("water_heater.tank")["fresh"]
    if case == "neighbor_device":
        coordinator.device.tank._device = DeviceImpl(coordinator._device_info)
    elif case == "same_value_status":
        coordinator.device.tank._status = TankStatus(OperationStatus.ON, 47)
    else:
        neighbor = DeviceImpl(coordinator._device_info)
        coordinator.device.tank = neighbor.tank
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    assert not coordinator.listeners
