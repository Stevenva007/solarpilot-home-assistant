"""Loaded split-status semantics and live freshness, entirely offline.

MIT License; upstream excerpts from wpatrik14/aioaquarea
893065a81c014cb9aa1d3350446d61c01bccf3b9, data.py/device_manager.py.
Copyright (c) 2022 Carlos J. Aliaga

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from copy import deepcopy
from dataclasses import fields
from enum import Enum
from pathlib import Path
import sys
from types import ModuleType
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot.operation_source_evidence import (
    CONTRACT_ID, SEMANTIC_CONTRACT_ID, OPERATION_CONTRACT_ID, OPERATION_SEMANTIC_CONTRACT_ID,
    contract_evidence, retained_contract_evidence, inspect_loaded_aquarea_semantics,
    known_source_contract, loaded_semantic_identity, special_status_contract, valid_semantic_contract,
)
from test_aquarea_display_snapshot86 import modern_setup, record
from test_display_operation83 import NOW, contract_snapshot, display
from custom_components.solar_pilot.power_activity import task_observations


# Pinned upstream bodies; placeholder types deliberately cannot call the API.

DATA_SOURCE = '''
from __future__ import annotations
from enum import Enum
class DeviceStatus: pass
class DeviceModeStatus: pass
class ExtendedOperationMode: pass
class FaultError: pass
class DeviceDirection: pass
class PumpDuty: pass
class TankStatus: pass
class OperationStatus: pass
class QuietMode: pass
class ForceDHW: pass
class ForceHeater: pass
class HolidayTimer: pass
class PowerfulTime: pass
class SpecialStatus: pass
class DeviceZoneStatus: pass
class DeviceZoneInfo: pass
class ZoneSensor: pass
class ZoneType: pass
class SensorMode: pass
class DeviceZone: pass
class StatusDataMode(Enum):
    LIVE=0
    CACHED=1
ZONE_SENSOR_IDS={}

def parse_special_status(value: object) -> SpecialStatus | None:
    """Map a raw ``specialStatus`` value to ``SpecialStatus`` (0/unknown -> None)."""
    try:
        return SpecialStatus(value) if value else None
    except (ValueError, TypeError):
        return None

def merge_zone_infos(
    info_zones: list[DeviceZoneInfo], status: DeviceStatus
) -> list[DeviceZoneInfo]:
    """Zone descriptions for a device, with the device status as the source of truth.

    ``/device/group`` lists placeholder zones (a bare ``{"zoneId": 2}`` for an
    unconfigured zone 2) and has no names, types or sensors; the status
    ``zoneStatus[]`` lists only the configured zones, with ``zoneName``,
    ``zoneType`` and ``zoneSensor``. When the status has zones they decide which
    zones exist; otherwise the ``info_zones`` are kept as they are.

    Cooling: the status ``coolMode`` decides when present (non-zero = cooling
    capable; the meaning of the individual values is unverified). Without it the
    old heuristic is used: the device list said so, or the zone reports a
    cooling setpoint range.
    """
    status_zones = [z for z in status.zones if z.zone_id is not None]
    if not status_zones:
        return list(info_zones)

    by_id = {zone.zone_id: zone for zone in info_zones}
    merged: list[DeviceZoneInfo] = []
    for zone_status in status_zones:
        base = by_id.get(zone_status.zone_id)
        if status.cool_mode is not None:
            cool_mode = bool(status.cool_mode)
        else:
            cool_mode = bool(base and base.cool_mode) or (
                zone_status.cool_min is not None and zone_status.cool_max is not None
            )
        if zone_status.zone_sensor_id is not None:
            zone_sensor = ZONE_SENSOR_IDS.get(zone_status.zone_sensor_id, ZoneSensor.UNKNOWN)
        elif base is not None and isinstance(base.zone_sensor, ZoneSensor):
            zone_sensor = base.zone_sensor
        else:
            zone_sensor = ZoneSensor.UNKNOWN
        merged.append(
            DeviceZoneInfo(
                zone_id=zone_status.zone_id,
                name=zone_status.name
                or (base.name if base else None)
                or f"Zone {zone_status.zone_id}",
                type=base.type if base else ZoneType.UNKNOWN,
                cool_mode=cool_mode,
                zone_sensor=zone_sensor,
                heat_sensor=base.heat_sensor if base else SensorMode.DIRECT,
                cool_sensor=base.cool_sensor if base else SensorMode.DIRECT,
                zone_type_id=zone_status.zone_type_id,
                zone_sensor_id=zone_status.zone_sensor_id,
            )
        )
    return merged

class Device:
    @property
    def operation_status(self) -> OperationStatus:
            """The operation status of the device"""
            return self._status.operation_status

    @property
    def current_action(self) -> DeviceAction:
            """The current action the device is performing"""
            if self.operation_status == OperationStatus.OFF:
                return DeviceAction.OFF

            direction = self.current_direction
            if direction == DeviceDirection.IDLE:
                return DeviceAction.IDLE

            if (
                self.has_tank
                and direction == DeviceDirection.WATER
                and self.tank.operation_status == OperationStatus.ON
            ):
                return DeviceAction.HEATING_WATER

            mode = self.mode
            if direction == DeviceDirection.PUMP and mode != ExtendedOperationMode.OFF:
                return (
                    DeviceAction.HEATING
                    if mode in (ExtendedOperationMode.HEAT, ExtendedOperationMode.AUTO_HEAT)
                    else DeviceAction.COOLING
                )

            return DeviceAction.IDLE

    @property
    def status_data_mode(self) -> StatusDataMode:
            """LIVE, or CACHED when the live read failed and the cached status was used
            (the cached status has no water pressure)"""
            return self._status.data_mode

    def __build_zones__(self, zones_info: list[DeviceZoneInfo]) -> None:
            """(Re)build the zones from the device list zones and the current status."""
            zones: dict[int, DeviceZone] = {}
            for zone in merge_zone_infos(zones_info, self._status):
                zone_id = zone.zone_id
                # pylint: disable=cell-var-from-loop
                zone_status = next(
                    filter(lambda z: z.zone_id == zone_id, self._status.zones), None
                )
                zones[zone_id] = DeviceZone(zone, zone_status)
            self._zones = zones

class DeviceAction: pass
'''

MANAGER_SOURCE = '''
from __future__ import annotations
def _parse_zone_status(zone_status: Any) -> DeviceZoneStatus:
    return DeviceZoneStatus(
        zone_id=zone_status.get("zoneId"),
        temperature=zone_status.get("temperatureNow"),
        operation_status=OperationStatus(zone_status.get("operationStatus")),
        heat_max=zone_status.get("heatMax"),
        heat_min=zone_status.get("heatMin"),
        heat_set=zone_status.get("heatSet"),
        cool_max=zone_status.get("coolMax"),
        cool_min=zone_status.get("coolMin"),
        cool_set=zone_status.get("coolSet"),
        comfort_cool=zone_status.get("comfortCool"),
        comfort_heat=zone_status.get("comfortHeat"),
        eco_cool=zone_status.get("ecoCool"),
        eco_heat=zone_status.get("ecoHeat"),
        name=zone_status.get("zoneName") or None,
        zone_type_id=zone_status.get("zoneType"),
        zone_sensor_id=zone_status.get("zoneSensor"),
    )

def _device_operation_status(
    device: Any, zones: list[DeviceZoneStatus], tank: Any
) -> OperationStatus:
    """Whole-device on/off.

    The status has no device-level ``operationStatus`` (an explicit one is
    still honoured if present). ``operationMode`` stays at the last heat/cool
    mode while everything is off, so it cannot tell on from off either: the
    device is on while any zone or the tank is on. (``specialStatus`` is the
    eco/comfort preset, not the on/off state.)
    """
    if device.get("operationStatus") is not None:
        return OperationStatus(device["operationStatus"])
    on = any(zone.operation_status == OperationStatus.ON for zone in zones) or (
        tank.get("operationStatus") == OperationStatus.ON
    )
    return OperationStatus.ON if on else OperationStatus.OFF

def _optional_bool(value) -> bool | None:
    return None if value is None else bool(value)

def parse_device_status(
    long_id: str,
    json_response: Any,
    data_mode: StatusDataMode = StatusDataMode.LIVE,
) -> DeviceStatus:
    """Build a ``DeviceStatus`` from a ``/remote/v1/api/devices`` response.

    Raises AttributeError/KeyError/TypeError/ValueError on malformed data.
    """
    device: Any = json_response.get("status")
    operation_mode_value = device.get("operationMode")
    tank_json: Any = device.get("tankStatus") or {}
    zones = [
        _parse_zone_status(zone_status)
        for zone_status in device.get("zoneStatus") or []
        if isinstance(zone_status, dict)
    ]

    return DeviceStatus(
        long_id=long_id,
        operation_status=_device_operation_status(device, zones, tank_json),
        device_status=DeviceModeStatus(device.get("deiceStatus")),
        temperature_outdoor=device.get("outdoorNow"),
        operation_mode=(
            ExtendedOperationMode.OFF
            if operation_mode_value == 99
            else ExtendedOperationMode(operation_mode_value)
        ),
        fault_status=[
            FaultError(fault_status["errorMessage"], fault_status["errorCode"])
            for fault_status in device.get("faultStatus") or []
        ],
        direction=DeviceDirection(device.get("direction")),
        pump_duty=PumpDuty(device.get("pumpDuty")),
        tank_status=(
            [
                TankStatus(
                    OperationStatus(tank_json.get("operationStatus")),
                    tank_json.get("temperatureNow"),
                    tank_json.get("heatMax"),
                    tank_json.get("heatMin"),
                    tank_json.get("heatSet"),
                )
            ]
            if tank_json
            else []
        ),
        zones=zones,
        quiet_mode=QuietMode(device.get("quietMode", 0)),
        force_dhw=ForceDHW(device.get("forceDHW", 0)),
        force_heater=ForceHeater(device.get("forceHeater", 0)),
        holiday_timer=HolidayTimer(device.get("holidayTimer", 0)),
        powerful_time=PowerfulTime(device.get("powerful", 0)),
        special_status=parse_special_status(device.get("specialStatus")),
        water_pressure=device.get("waterPressure"),
        data_mode=data_mode,
        cool_mode=device.get("coolMode"),
        tank_flag=device.get("tank"),
        bivalent=device.get("bivalent"),
        bivalent_actual=device.get("bivalentActual"),
        external_heater=device.get("externalHeater"),
        electric_anode=device.get("electricAnode"),
        control_box=device.get("controlBox"),
        uncontrollable=_optional_bool(device.get("uncontrollableTaw1Flg")),
        service_type=device.get("serviceType"),
        multi_od_connection=device.get("multiOdConnection"),
        model_series_selection=device.get("modelSeriesSelection"),
        stand_alone=device.get("standAlone"),
    )

class DeviceManager:
    async def get_device_status(self, device_info: DeviceInfo) -> DeviceStatus:
            """Retrieve the device status.

            Reads the live status (``deviceDirect=1``) and falls back to the cloud's
            cached status (``deviceDirect=0``) when that fails. The cached status
            has no ``waterPressure`` (``water_pressure`` is None then) and its
            ``direction`` can differ from the live one; ``DeviceStatus.data_mode``
            says which one was used.
            """
            json_response = None
            data_mode = StatusDataMode.LIVE
            try:
                payload = {
                    "apiName": f"/remote/v1/api/devices?gwid={device_info.device_id}&deviceDirect=1",
                    "requestMethod": "GET",
                }
                response = await self._client._api_client.request(
                    "POST",
                    url="remote/v1/app/common/transfer",
                    json=payload,
                    throw_on_error=True,
                )
                json_response = await response.json()
                self._logger.debug(
                    "get_device_status (live): response for device %s has keys %s",
                    device_info.device_id,
                    sorted(json_response) if isinstance(json_response, dict) else type(json_response).__name__,
                )
            except (AuthenticationError, AgreementNotAcceptedError):
                raise
            except Exception as e:
                self._logger.warning(
                    "Failed to get live status for device {}: {}".format(
                        device_info.device_id, e
                    )
                )
                # If live data fails, try cached data as a fallback
                try:
                    payload = {
                        "apiName": f"/remote/v1/api/devices?gwid={device_info.device_id}&deviceDirect=0",
                        "requestMethod": "GET",
                    }
                    response = await self._client._api_client.request(
                        "POST",
                        url="remote/v1/app/common/transfer",
                        json=payload,
                        throw_on_error=True,
                    )
                    json_response = await response.json()
                    data_mode = StatusDataMode.CACHED
                    self._logger.debug(
                        "Retrieved cached status for device %s after live data failure "
                        "(no water pressure in cached data)",
                        device_info.device_id,
                    )
                except (AuthenticationError, AgreementNotAcceptedError):
                    raise
                except Exception as e_cached:
                    self._logger.error(
                        "Failed to get cached status for device {}: {}".format(
                            device_info.device_id, e_cached
                        )
                    )
                    raise RequestFailedError(
                        "Failed to retrieve device status after multiple attempts."
                    ) from e_cached

            if json_response is None:
                raise RequestFailedError(
                    "Failed to retrieve device status after multiple attempts."
                )

            try:
                return parse_device_status(device_info.device_id, json_response, data_mode)
            except (AttributeError, KeyError, TypeError, ValueError) as err:
                raise InvalidData(json_response) from err
'''


def loaded_split(monkeypatch, tmp_path, *, data_source=None, manager_source=None):
    def load(name, source, namespace=None):
        path = tmp_path / (name.rsplit(".", 1)[-1] + ".py")
        path.write_text(source, encoding="utf-8")
        module = ModuleType(name)
        module.__file__ = str(path)
        module.__dict__.update(namespace or {})
        monkeypatch.setitem(sys.modules, name, module)
        exec(compile(source, str(path), "exec"), module.__dict__)
        return module
    data = load("aioaquarea.data", data_source or DATA_SOURCE)
    manager = load("aioaquarea.device_manager", manager_source or MANAGER_SOURCE,
                   {name: value for name, value in vars(data).items() if not name.startswith("__")})
    entities = load("aioaquarea.entities", "class DeviceImpl(Device):\n    pass\n", {"Device": data.Device})
    return data, manager, entities


def split_snapshot(**kwargs):
    p = contract_snapshot(raw="HEATING", **kwargs)
    p["source_contract"].update(contract_id=OPERATION_CONTRACT_ID, action_semantics="operation_status",
        compatibility={"schema": 1, "contract": OPERATION_SEMANTIC_CONTRACT_ID, "verified": True,
                       "basis": "loaded_source", "fingerprint": "b" * 64},
        device_operation_status="ON", status_data_mode="LIVE")
    return p


def test_actual_loaded_split_parser_helper_chain_and_inherited_getters_are_a_new_capability(monkeypatch, tmp_path):
    loaded_split(monkeypatch, tmp_path)
    result = inspect_loaded_aquarea_semantics()
    assert result["compatibility_state"] == "compatible"
    assert result["compatibility"]["contract"] == OPERATION_SEMANTIC_CONTRACT_ID
    assert result["reason_code"] == "known_operation_status_action_mapping"
    assert valid_semantic_contract(result["compatibility"])
    # The placeholder enums and absent client cannot execute provider methods.


@pytest.mark.parametrize("change", ["special_status", "helper", "delegate", "quality", "zones", "getter", "shadow", "source"])
def test_changed_split_mapping_or_actual_binding_never_borrows_the_old_proof(change, monkeypatch, tmp_path):
    source, manager_source = DATA_SOURCE, MANAGER_SOURCE
    if change == "special_status":
        manager_source = manager_source.replace('operation_status=_device_operation_status(device, zones, tank_json)', 'operation_status=OperationStatus(device.get("specialStatus"))')
    elif change == "helper":
        manager_source = manager_source.replace('return OperationStatus.ON if on else OperationStatus.OFF', 'return OperationStatus.ON')
    elif change == "delegate":
        manager_source = manager_source.replace('return parse_device_status(device_info.device_id, json_response, data_mode)', 'return parse_device_status(device_info.device_id, json_response, StatusDataMode.LIVE)')
    elif change == "quality":
        manager_source = manager_source.replace('data_mode=data_mode,', 'data_mode=StatusDataMode.LIVE,')
    elif change == "zones":
        source = source.replace('zones[zone_id] = DeviceZone(zone, zone_status)', 'zones[zone_id] = DeviceZone(zone, None)')
    elif change == "getter":
        source = source.replace('return self._status.operation_status', 'return self._status.special_status')
    data, manager, _ = loaded_split(monkeypatch, tmp_path, data_source=source, manager_source=manager_source)
    if change == "shadow":
        manager._device_operation_status = lambda *_: None
    elif change == "source":
        Path(manager.__file__).write_text(MANAGER_SOURCE.replace('data_mode=data_mode,', 'data_mode=None,'), encoding="utf-8")
    assert inspect_loaded_aquarea_semantics()["compatibility"] is None


def test_actual_helper_rebinding_invalidates_cached_capability_immediately(monkeypatch, tmp_path):
    _, manager, _ = loaded_split(monkeypatch, tmp_path)
    before = loaded_semantic_identity()
    manager._device_operation_status = lambda *_: None
    assert loaded_semantic_identity() != before
    assert inspect_loaded_aquarea_semantics()["compatibility"] is None


def test_implementation_zone_rebuild_override_invalidates_cached_capability(monkeypatch, tmp_path):
    _, _, entities = loaded_split(monkeypatch, tmp_path)
    before = loaded_semantic_identity()
    entities.DeviceImpl.__build_zones__ = lambda *_: None
    assert loaded_semantic_identity() != before
    assert inspect_loaded_aquarea_semantics()["compatibility"] is None


def test_original_historical_shape_and_meaning_stay_intact_and_proof_types_cannot_be_swapped():
    old = contract_snapshot()["source_contract"]
    clean = contract_evidence(old, NOW, 120)
    assert clean["contract_id"] == CONTRACT_ID and clean["action_semantics"] == "special_status"
    assert "status_data_mode" not in clean and "device_operation_status" not in clean
    assert retained_contract_evidence(deepcopy(clean), NOW, 120) == clean
    new = split_snapshot()["source_contract"]
    clean_new = contract_evidence(new, NOW, 120)
    assert clean_new["verified"] and clean_new["status_data_mode"] == "LIVE"
    assert retained_contract_evidence(deepcopy(clean_new), NOW, 120) == clean_new
    cached = deepcopy(new)
    cached["status_data_mode"] = "CACHED"
    cached_clean = contract_evidence(cached, NOW, 120)
    assert not cached_clean["verified"] and cached_clean["status_data_mode"] == "CACHED"
    assert cached_clean["observed_at"] == clean_new["observed_at"]
    assert not special_status_contract(new)
    for contract_id, semantics, proof in ((CONTRACT_ID, "special_status", OPERATION_SEMANTIC_CONTRACT_ID),
                                          (OPERATION_CONTRACT_ID, "operation_status", SEMANTIC_CONTRACT_ID),
                                          (OPERATION_CONTRACT_ID, "special_status", OPERATION_SEMANTIC_CONTRACT_ID)):
        forged = deepcopy(new)
        forged.update(contract_id=contract_id, action_semantics=semantics)
        forged["compatibility"]["contract"] = proof
        assert not known_source_contract(forged)
        assert not contract_evidence(forged, NOW, 120)["verified"]


@pytest.mark.parametrize("change,reason", [(None, "coherent_native_context"), ("off", "native_source_value_conflict"),
    ("unknown", "native_source_value_conflict"), ("cached", "native_status_not_live"),
    ("zones_off", "zone_enabled_not_current"), ("wrong_task", "native_source_value_conflict"),
    ("missing_meter", "assigned_active_feed_missing")])
def test_new_status_never_uses_preset_off_override_or_bypasses_independent_context(change, reason):
    p = split_snapshot()
    c = p["source_contract"]
    if change == "off": c.update(device_operation_status="OFF", raw_device_action="OFF")
    elif change == "unknown": c.update(device_operation_status="UNKNOWN", raw_device_action="IDLE")
    elif change == "cached": c["status_data_mode"] = "CACHED"
    elif change == "zones_off": c["zones"][0]["enabled"] = False
    elif change == "wrong_task": c["raw_device_action"] = "HEATING_WATER"
    elif change == "missing_meter": p["power_activity"]["supplies"][0]["role"] = "unconfirmed"
    result = display(p)
    assert result["reason_code"] == reason
    assert result["function"] == ("space_heating" if change is None else None)
    assert not result["model_eligible"]


def split_setup(monkeypatch):
    """Fictional coordinator with the current SDK's merged, owned zone rows."""
    env = modern_setup(monkeypatch, version="42.0.0")
    mode_type = Enum("StatusDataMode", {"LIVE": 0, "CACHED": 1}, module="aioaquarea.data")
    module = ModuleType("aioaquarea.data")
    module.StatusDataMode = mode_type
    monkeypatch.setitem(sys.modules, "aioaquarea.data", module)
    old_fields = [field.name for field in fields(env.data.DeviceStatus)]
    new_fields = "data_mode cool_mode tank_flag bivalent bivalent_actual external_heater electric_anode control_box uncontrollable service_type multi_od_connection model_series_selection stand_alone".split()
    typed_status = record("DeviceStatus", " ".join(old_fields + new_fields))
    original_poll = env.coordinator.poll
    def poll(*, quality=mode_type.LIVE, operation="ON", notify=True, **kwargs):
        original_poll(notify=False, **kwargs)
        device = env.coordinator.device
        previous = device._status
        device._status = typed_status(**{field: getattr(previous, field) for field in old_fields}, data_mode=quality)
        device._status.operation_status = getattr(env.data.OperationStatus, operation)
        device._zones = {}
        for row in device._status.zones:
            info = env.data.DeviceZoneInfo(zone_id=row.zone_id)
            device._zones[row.zone_id] = type(next(iter(type(device)._zones.values())))(info, row)
        if device.has_tank:
            device._tank = env.data.TankImpl(device, device._status.tank_status[0])
        if notify:
            env.coordinator.notify()
    env.coordinator.poll = poll
    env.poll = poll
    env.quality = mode_type
    env.helper._display_metadata.update(library_version="42.0.0",
        compatibility={"schema": 1, "contract": OPERATION_SEMANTIC_CONTRACT_ID, "verified": True,
                       "basis": "loaded_source", "fingerprint": "b" * 64})
    env.helper._display_semantic_identity = loaded_semantic_identity()
    poll(notify=False)
    return env


def test_merged_zone_current_live_snapshot_is_read_only_and_keeps_zone_guard(monkeypatch):
    env = split_setup(monkeypatch)
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.poll()
    native = env.helper.read_source_contract(env.sources)
    assert native["status"] == "verified" and native["contract_id"] == OPERATION_CONTRACT_ID
    assert native["device_operation_status"] == "ON" and native["status_data_mode"] == "LIVE"
    assert native["raw_device_action"] == "HEATING" and all(row["enabled"] for row in native["zones"])
    assert env.helper._watches == {} and env.helper._tank_watches == {}
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []
    env.coordinator.device._zones[1]._status = deepcopy(env.coordinator.device._status.zones[0])
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"


def test_native_quality_veto_resolves_sensor_tank_and_zone_without_affecting_independent_sources(monkeypatch):
    env = split_setup(monkeypatch)
    sensor = "sensor.pump_water_temperature"
    env.rows[sensor] = deepcopy(env.rows[env.sources["zone_entities"][0]])
    env.rows[sensor].entity_id = sensor
    env.rows[sensor].unique_id = "pump_water_temperature"
    ids = [sensor, env.sources["tank_entity"], *env.sources["zone_entities"]]
    assert all(env.helper.source_is_live(eid) for eid in ids)
    env.poll(quality=env.quality.CACHED)
    assert all(not env.helper.source_is_live(eid) for eid in ids)
    assert env.helper.source_is_live("sensor.independent_tank_thermometer")
    env.rows["sensor.other"] = deepcopy(env.rows[sensor])
    env.rows["sensor.other"].platform = "shelly"
    assert env.helper.source_is_live("sensor.other")
    env.poll()
    env.rows[sensor].device_id = "wrong_registry_device"
    assert not env.helper.source_is_live(sensor)
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


def test_source_quality_rejected_generation_cannot_revive_from_an_attribute_edit(monkeypatch):
    env = split_setup(monkeypatch)
    eid = env.sources["tank_entity"]
    assert env.helper.source_is_live(eid)
    env.poll(quality=env.quality.CACHED)
    assert not env.helper.source_is_live(eid)
    env.coordinator.device._status.data_mode = env.quality.LIVE
    assert not env.helper.source_is_live(eid)
    env.coordinator.notify()
    assert not env.helper.source_is_live(eid)
    env.poll()
    assert env.helper.source_is_live(eid)
    env.helper.close()
    assert env.helper._source_quality_rejected == {}


def test_new_unknown_zone_fallback_off_keeps_raw_value_without_physical_global_off(monkeypatch, tmp_path):
    data, manager, _ = loaded_split(monkeypatch, tmp_path)
    # Execute only the pinned pure parser helper with fictional permissions.
    statuses = Enum("OperationStatus", {"ON": 1, "OFF": 0, "UNKNOWN": 2}, module="aioaquarea.data")
    manager.OperationStatus = data.OperationStatus = statuses
    assert manager._device_operation_status({}, [NS(operation_status=statuses.UNKNOWN)], {}) == statuses.OFF
    env = split_setup(monkeypatch)
    eid = env.sources["zone_entities"][0]
    env.helper.read_device_action(eid)
    env.poll(operation="OFF", tank_on=False, enabled=(False, False))
    proof = env.helper.read_device_action(eid)
    assert proof["fresh"] and proof["raw_action"] == "OFF" and proof["operation_status"] == "OFF"
    assert proof["operation_status_scope"] == "device_enablement"
    zones = [{"entity_id": eid, "available": True, "action": "off", "observed_at": 990}]
    native, _context = task_observations({"stale_s": 120}, device_actions=[proof], zones=zones, now_wall=1000)
    assert native["inactive"] and native["inactive_scope"] == "unknown" and not native["verified_global_off"]
    assert native["raw_evidence"][0]["operation_status_scope"] == "device_enablement"
    old = dict(proof)
    old.pop("operation_status_scope")
    legacy, _context = task_observations({"stale_s": 120}, device_actions=[old], zones=zones, now_wall=1000)
    assert legacy["verified_global_off"] and legacy["inactive_scope"] == "global"
    env.helper._display_metadata["compatibility"] = None
    pending = env.helper.read_device_action(eid)
    assert pending["operation_status_scope"] == "unverified"
    pending_task, _context = task_observations({"stale_s": 120}, device_actions=[pending], zones=zones, now_wall=1000)
    assert not pending_task["verified_global_off"]


@pytest.mark.parametrize("quality", ["CACHED", None, True, False, 0, 1, "LIVE"])
def test_cached_success_and_untyped_quality_do_not_refresh_display_programme_or_action(quality, monkeypatch):
    env = split_setup(monkeypatch)
    eid = env.sources["zone_entities"][0]
    env.helper.read_source_contract(env.sources)
    env.helper.read(eid)
    env.helper.read_device_action(eid)
    env.poll()
    assert env.helper.read(eid)["fresh"] and env.helper.read_device_action(eid)["fresh"]
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"
    value = env.quality.CACHED if quality == "CACHED" else quality
    env.poll(quality=value)
    assert env.coordinator.last_update_success is True
    assert not env.helper.read(eid)["fresh"] and not env.helper.read_device_action(eid)["fresh"]
    cached = env.helper.read_source_contract(env.sources)
    assert cached["status"] == "unknown" and cached["reason_code"] == "native_status_not_live"
    assert cached["compatibility_state"] == "compatible"
    # Editing the cached attribute to LIVE is no new successful poll.
    env.coordinator.device._status.data_mode = env.quality.LIVE
    env.coordinator.notify()
    assert not env.helper.read(eid)["fresh"] and not env.helper.read_device_action(eid)["fresh"]
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.poll()
    assert env.helper.read(eid)["fresh"] and env.helper.read_device_action(eid)["fresh"]
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"
