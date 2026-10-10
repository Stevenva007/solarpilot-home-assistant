"""Verified native tank action is display context, without fetching or writes."""
from enum import IntEnum
from types import SimpleNamespace as NS

import pytest

from test_native_program56 import Coordinator, ExtendedOperationMode, device, setup
from test_runtime import States


DeviceAction = IntEnum("DeviceAction", {"OFF": 0, "IDLE": 1, "HEATING": 2,
    "COOLING": 3, "HEATING_WATER": 4}, module="aioaquarea.data")
DeviceDirection = IntEnum("DeviceDirection", {"IDLE": 0, "PUMP": 1, "WATER": 2}, module="aioaquarea.data")


class TankCoordinator(Coordinator):
    def __init__(self, device_id="pump"):
        super().__init__(device_id)
        self.poll(notify=False)

    def poll(self, mode=ExtendedOperationMode.HEAT, *, action=DeviceAction.HEATING_WATER,
             direction=DeviceDirection.WATER, success=True, replace=True, notify=True):
        if replace:
            self.device = device(self.device_info.device_id, mode)
        else:
            self.device.mode = mode
        self.device.has_tank = True
        self.device.tank = NS(operation_status=1)
        self.device.operation_status = 1
        self.device.current_direction = direction
        self.device.current_action = action
        self.last_update_success = success
        if notify:
            for listener in tuple(self.listeners):
                listener()


def tank_setup(monkeypatch, *, legacy=False, stale_s=120):
    helper, _unused, rows, entries, clock = setup(monkeypatch, stale_s=stale_s)
    coordinator = TankCoordinator()
    rows["water_heater.tank"] = NS(platform="aquarea", config_entry_id="native", unique_id="pump_tank")
    helper.runtime.hass.states = States()
    helper.runtime.hass.states.set("water_heater.tank", "heating")
    if legacy:
        entries["native"].runtime_data = None
        helper.runtime.hass.data = {"aquarea": {"native": {"devices": {"pump": coordinator}}}}
    else:
        entries["native"].runtime_data = {"pump": coordinator}
    return helper, coordinator, rows, entries, clock


@pytest.mark.parametrize("legacy", [False, True])
def test_tank_binding_requires_its_own_new_successful_poll_without_requests(monkeypatch, legacy):
    helper, coordinator, _rows, _entries, _clock = tank_setup(monkeypatch, legacy=legacy)
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    assert len(coordinator.listeners) == 1 and not coordinator.api_calls
    coordinator.poll()
    result = helper.read_tank_action("water_heater.tank")
    assert result["fresh"] and result["action"] == "tapwater_heating"
    assert result["raw_action"] == "HEATING_WATER" and result["source"] == "aquarea_poll"
    assert result["observed_at"] is not None and not coordinator.api_calls
    assert not helper.runtime.hass.states.get("water_heater.tank").attributes


@pytest.mark.parametrize("invalid", [4, "HEATING_WATER", NS(name="HEATING_WATER", value=4),
    IntEnum("DeviceAction", {"HEATING_WATER": 4}, module="other.data").HEATING_WATER,
    IntEnum("OtherAction", {"HEATING_WATER": 4}, module="aioaquarea.data").HEATING_WATER,
    IntEnum("DeviceAction", {"HEATING_WATER": 1}, module="aioaquarea.data").HEATING_WATER])
def test_tank_action_enum_name_module_and_value_are_exact(monkeypatch, invalid):
    helper, coordinator, *_ = tank_setup(monkeypatch)
    helper.read_tank_action("water_heater.tank")
    coordinator.poll(action=invalid)
    assert not helper.read_tank_action("water_heater.tank")["fresh"]


@pytest.mark.parametrize("action,function", [(DeviceAction.OFF, "off"), (DeviceAction.IDLE, "idle"),
    (DeviceAction.HEATING, "space_heating"), (DeviceAction.COOLING, "space_cooling"),
    (DeviceAction.HEATING_WATER, "tapwater_heating")])
def test_verified_provider_actions_are_separate_display_tasks(monkeypatch, action, function):
    helper, coordinator, *_ = tank_setup(monkeypatch)
    helper.read_tank_action("water_heater.tank")
    coordinator.poll(action=action)
    result = helper.read_tank_action("water_heater.tank")
    assert result["fresh"] and result["action"] == function and result["raw_action"] == action.name
    assert not coordinator.api_calls


@pytest.mark.parametrize("case", ["wrong_uid", "wrong_platform", "wrong_domain", "wrong_entry",
    "device_info", "device_id", "mapping_key", "no_tank", "disabled", "unavailable", "restored", "estimated"])
def test_tank_registry_device_and_current_availability_cannot_be_guessed(monkeypatch, case):
    helper, coordinator, rows, entries, _clock = tank_setup(monkeypatch)
    row = rows["water_heater.tank"]
    if case == "wrong_uid":
        row.unique_id = "pump_tank_suffix"
    elif case == "wrong_platform":
        row.platform = "unrelated"
    elif case == "wrong_domain":
        entries["native"].domain = "unrelated"
    elif case == "wrong_entry":
        row.config_entry_id = "missing"
    elif case == "device_info":
        coordinator.device_info.device_id = "other"
    elif case == "device_id":
        coordinator.device.device_id = "other"
    elif case == "mapping_key":
        entries["native"].runtime_data = {"other": coordinator}
    elif case == "no_tank":
        coordinator.device.has_tank = False
    elif case == "disabled":
        row.disabled_by = "user"
    elif case == "unavailable":
        helper.runtime.hass.states.set("water_heater.tank", "unavailable")
    else:
        helper.runtime.hass.states.set("water_heater.tank", "heating", {case: True})
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    assert not coordinator.listeners and not coordinator.api_calls


@pytest.mark.parametrize("field", ["current_action", "current_direction", "mode", "operation_status", "tank"])
def test_optimistic_action_or_its_mutable_inputs_cannot_reuse_the_previous_poll(monkeypatch, field):
    helper, coordinator, *_ = tank_setup(monkeypatch)
    helper.read_tank_action("water_heater.tank")
    coordinator.poll()
    assert helper.read_tank_action("water_heater.tank")["fresh"]
    previous = getattr(coordinator.device, field)
    value = {"current_action": DeviceAction.IDLE, "current_direction": DeviceDirection.PUMP,
             "mode": ExtendedOperationMode.COOL, "operation_status": 0, "tank": NS(operation_status=0)}[field]
    setattr(coordinator.device, field, value)
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    setattr(coordinator.device, field, previous)
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    coordinator.poll()
    assert helper.read_tank_action("water_heater.tank")["fresh"]


def test_same_object_notifications_failed_poll_and_reload_never_refresh_tank_proof(monkeypatch):
    helper, coordinator, _rows, _entries, clock = tank_setup(monkeypatch)
    helper.read_tank_action("water_heater.tank")
    coordinator.poll()
    first = helper.read_tank_action("water_heater.tank")
    clock[0] += 121
    coordinator.poll(replace=False)
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    coordinator.poll()
    coordinator.last_update_success = False
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    coordinator.last_update_success = True
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    coordinator.poll()
    assert helper.read_tank_action("water_heater.tank")["fresh"]
    helper.close()
    assert coordinator.listeners == []
    assert not helper.read_tank_action("water_heater.tank")["fresh"]
    assert first["fresh"] and not coordinator.api_calls


def test_legacy_tank_display_watch_never_changes_or_revives_programme_permission(monkeypatch):
    helper, coordinator, *_ = tank_setup(monkeypatch, legacy=True)
    helper.read_tank_action("water_heater.tank")
    coordinator.poll()
    assert helper.read_tank_action("water_heater.tank")["fresh"]
    for _ in range(3):
        assert not helper.read("climate.salon")["fresh"]  # original runtime_data contract
        assert helper.read_tank_action("water_heater.tank")["fresh"]
    assert len(coordinator.listeners) == 1 and not coordinator.api_calls


def test_display_tank_action_does_not_replace_selected_native_programme(monkeypatch):
    helper, coordinator, *_ = tank_setup(monkeypatch)
    helper.read("climate.salon")
    helper.read_tank_action("water_heater.tank")
    coordinator.poll(mode=ExtendedOperationMode.OFF)
    assert helper.read_tank_action("water_heater.tank")["action"] == "tapwater_heating"
    assert helper.read("climate.salon")["program"] == "off"
    assert not coordinator.api_calls
