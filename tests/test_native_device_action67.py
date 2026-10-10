"""Whole-device display action through native zones stays separate from policy."""
from enum import Enum, IntEnum
from types import SimpleNamespace as NS

import pytest

from test_native_program56 import ExtendedOperationMode, native_program, setup
from test_native_tank_action66 import DeviceAction, DeviceDirection, TankCoordinator
from test_runtime import Services, States


DeviceModeStatus = IntEnum("DeviceModeStatus", {"NORMAL": 0, "DEFROST": 1}, module="aioaquarea.data")


def action_setup(monkeypatch, *, legacy=False):
    helper, _unused, rows, entries, clock = setup(monkeypatch, stale_s=120)
    coordinator = TankCoordinator()
    helper.runtime.hass.states = States()
    helper.runtime.hass.states.set("climate.salon", "off", {"hvac_action": "off"})
    helper.runtime.hass.services = Services(helper.runtime.hass.states)
    monkeypatch.setattr(native_program.time, "time", lambda: clock[0])
    if legacy:
        entries["native"].runtime_data = None
        helper.runtime.hass.data = {"aquarea": {"native": {"devices": {"pump": coordinator}}}}
    else:
        entries["native"].runtime_data = {"pump": coordinator}

    def poll(*, action=DeviceAction.HEATING_WATER, mode=ExtendedOperationMode.OFF,
             device_mode_status=DeviceModeStatus.NORMAL, mode_status=DeviceModeStatus.NORMAL,
             has_tank=False, success=True, replace=True):
        coordinator.poll(mode=mode, action=action, direction=DeviceDirection.WATER,
                         success=success, replace=replace, notify=False)
        coordinator.device.has_tank = has_tank
        coordinator.device.tank = NS(operation_status=1) if has_tank else None
        coordinator.device.device_mode_status = device_mode_status
        coordinator.device.mode_status = mode_status
        for listener in tuple(coordinator.listeners):
            listener()

    return NS(helper=helper, coordinator=coordinator, rows=rows, entries=entries,
              clock=clock, poll=poll)


def assert_unknown(result):
    assert not result["fresh"] and result["action"] == "unknown"
    assert result["raw_action"] is None and result["observed_at"] is None
    assert result.get("defrost_active") is not True


@pytest.mark.parametrize("legacy", [False, True])
def test_device_action_needs_a_new_poll_and_never_fetches_one(monkeypatch, legacy):
    env = action_setup(monkeypatch, legacy=legacy)
    for _ in range(3):
        result = env.helper.read_device_action("climate.salon")
        assert_unknown(result)
        assert result["source"] == "aquarea_poll"
    assert len(env.coordinator.listeners) == 1
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []
    assert not env.helper._watches


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("action,expected", [(DeviceAction.HEATING, "space_heating"),
    (DeviceAction.COOLING, "space_cooling"), (DeviceAction.HEATING_WATER, "tapwater_heating")])
def test_off_zone_and_absent_water_heater_do_not_hide_typed_whole_device_task(monkeypatch, legacy, action, expected):
    env = action_setup(monkeypatch, legacy=legacy)
    env.helper.read_device_action("climate.salon")
    env.poll(action=action)
    result = env.helper.read_device_action("climate.salon")
    assert result["fresh"] and result["action"] == expected and result["raw_action"] == action.name
    assert result["entity_id"] == "climate.salon" and result["source"] == "aquarea_poll"
    assert result["program"] == "off" and result["raw_mode"] == "OFF"
    assert result["observed_at"] == 1000
    assert env.helper.runtime.hass.states.get("climate.salon").state == "off"
    assert not any(eid.startswith("water_heater.") for eid in env.helper.runtime.hass.states.data)
    assert env.coordinator.device.has_tank is False
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


@pytest.mark.parametrize("case", ["uid", "zone", "platform", "domain", "entry", "info_id",
    "device_id", "mapping_key", "disabled", "unavailable", "restored", "estimated", "is_estimated"])
def test_device_action_requires_exact_zone_entry_and_current_source(monkeypatch, case):
    env = action_setup(monkeypatch)
    row = env.rows["climate.salon"]
    if case == "uid":
        row.unique_id = "pump_climate_2_extra"
    elif case == "zone":
        row.unique_id = "pump_climate_3"
    elif case == "platform":
        row.platform = "unrelated"
    elif case == "domain":
        env.entries["native"].domain = "unrelated"
    elif case == "entry":
        row.config_entry_id = "missing"
    elif case == "info_id":
        env.coordinator.device_info.device_id = "other"
    elif case == "device_id":
        env.coordinator.device.device_id = "other"
    elif case == "mapping_key":
        env.entries["native"].runtime_data = {"other": env.coordinator}
    elif case == "disabled":
        row.disabled_by = "user"
    elif case == "unavailable":
        env.helper.runtime.hass.states.set("climate.salon", "unavailable")
    else:
        env.helper.runtime.hass.states.set("climate.salon", "off", {case: True})
    assert_unknown(env.helper.read_device_action("climate.salon"))
    assert env.coordinator.listeners == [] and env.coordinator.api_calls == []


@pytest.mark.parametrize("invalid", [2, "HEATING", NS(name="HEATING", value=2),
    IntEnum("DeviceAction", {"HEATING": 2}, module="other.data").HEATING,
    IntEnum("OtherAction", {"HEATING": 2}, module="aioaquarea.data").HEATING,
    IntEnum("DeviceAction", {"HEATING": 1}, module="aioaquarea.data").HEATING])
def test_only_exact_library_device_action_enum_is_accepted(monkeypatch, invalid):
    env = action_setup(monkeypatch)
    env.helper.read_device_action("climate.salon")
    env.poll(action=invalid)
    assert_unknown(env.helper.read_device_action("climate.salon"))
    assert env.coordinator.api_calls == []


@pytest.mark.parametrize("field", ["device_mode_status", "mode_status"])
def test_mode_status_mutation_revokes_action_proof_until_another_real_poll(monkeypatch, field):
    env = action_setup(monkeypatch)
    env.helper.read_device_action("climate.salon")
    env.poll(action=DeviceAction.HEATING)
    assert env.helper.read_device_action("climate.salon")["fresh"]
    previous = getattr(env.coordinator.device, field)
    setattr(env.coordinator.device, field, DeviceModeStatus.DEFROST)
    assert_unknown(env.helper.read_device_action("climate.salon"))
    setattr(env.coordinator.device, field, previous)
    assert_unknown(env.helper.read_device_action("climate.salon"))
    env.poll(action=DeviceAction.HEATING)
    assert env.helper.read_device_action("climate.salon")["fresh"]
    assert env.coordinator.api_calls == []


def test_exact_defrost_enum_is_reported_only_from_fresh_display_poll(monkeypatch):
    env = action_setup(monkeypatch)
    env.coordinator.device.device_mode_status = DeviceModeStatus.DEFROST
    assert_unknown(env.helper.read_device_action("climate.salon"))
    env.poll(action=DeviceAction.HEATING, device_mode_status=DeviceModeStatus.DEFROST)
    result = env.helper.read_device_action("climate.salon")
    assert result["fresh"] and result["defrost_active"] is True
    assert result["action"] == "space_heating" and result["program"] == "off"
    env.clock[0] += 121
    assert_unknown(env.helper.read_device_action("climate.salon"))


@pytest.mark.parametrize("invalid", [1, "DEFROST", NS(name="DEFROST", value=1),
    IntEnum("DeviceModeStatus", {"DEFROST": 1}, module="other.data").DEFROST,
    IntEnum("OtherModeStatus", {"DEFROST": 1}, module="aioaquarea.data").DEFROST,
    IntEnum("DeviceModeStatus", {"DEFROST": 2}, module="aioaquarea.data").DEFROST,
    IntEnum("DeviceModeStatus", {"NORMAL": 1}, module="aioaquarea.data").NORMAL,
    Enum("DeviceModeStatus", {"DEFROST": True}, module="aioaquarea.data").DEFROST])
def test_untyped_or_wrong_defrost_status_does_not_claim_defrost(monkeypatch, invalid):
    env = action_setup(monkeypatch)
    env.helper.read_device_action("climate.salon")
    env.poll(action=DeviceAction.HEATING, device_mode_status=invalid)
    result = env.helper.read_device_action("climate.salon")
    assert result["fresh"] and result["action"] == "space_heating"
    assert result.get("defrost_active") is not True


def test_legacy_display_metadata_cannot_enable_programme_reader(monkeypatch):
    env = action_setup(monkeypatch, legacy=True)
    env.helper.read_device_action("climate.salon")
    env.poll(action=DeviceAction.HEATING_WATER, mode=ExtendedOperationMode.AUTO_HEAT)
    display = env.helper.read_device_action("climate.salon")
    assert display["fresh"] and display["action"] == "tapwater_heating"
    assert display["program"] == "heating" and display["raw_mode"] == "AUTO_HEAT"
    for _ in range(3):
        assert not env.helper.read("climate.salon")["fresh"]
        assert env.helper.read_device_action("climate.salon")["fresh"]
    assert not env.helper._watches and len(env.coordinator.listeners) == 1
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


def test_display_poll_cannot_seed_programme_proof_or_replace_its_selected_mode(monkeypatch):
    env = action_setup(monkeypatch)
    env.helper.read_device_action("climate.salon")
    env.poll(action=DeviceAction.HEATING_WATER, mode=ExtendedOperationMode.COOL)
    assert env.helper.read_device_action("climate.salon")["action"] == "tapwater_heating"
    assert not env.helper.read("climate.salon")["fresh"]
    assert len(env.coordinator.listeners) == 2
    env.poll(action=DeviceAction.HEATING_WATER, mode=ExtendedOperationMode.OFF)
    assert env.helper.read("climate.salon")["program"] == "off"
    display = env.helper.read_device_action("climate.salon")
    assert display["action"] == "tapwater_heating" and display["program"] == "off"
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


def test_failed_poll_same_object_and_close_cannot_reuse_display_proof(monkeypatch):
    env = action_setup(monkeypatch)
    env.helper.read_device_action("climate.salon")
    env.poll(action=DeviceAction.COOLING)
    assert env.helper.read_device_action("climate.salon")["fresh"]
    env.clock[0] += 121
    env.poll(action=DeviceAction.COOLING, replace=False)
    assert_unknown(env.helper.read_device_action("climate.salon"))
    env.poll(action=DeviceAction.COOLING)
    env.poll(action=DeviceAction.COOLING, success=False)
    assert_unknown(env.helper.read_device_action("climate.salon"))
    env.coordinator.last_update_success = True
    assert_unknown(env.helper.read_device_action("climate.salon"))
    env.poll(action=DeviceAction.COOLING)
    assert env.helper.read_device_action("climate.salon")["fresh"]
    env.helper.close()
    assert env.coordinator.listeners == []
    assert_unknown(env.helper.read_device_action("climate.salon"))
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []
