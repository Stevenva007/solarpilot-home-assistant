"""Independent failure cases for current Aquarea display snapshots.

The fictional fixture reproduces the independently verified pinned shape;
these tests challenge lifetime, identity and conflicting status generations.
No cloud endpoint or device service is used.
"""
from copy import copy

import pytest

from test_aquarea_display_snapshot86 import modern_setup


def accepted(monkeypatch):
    env = modern_setup(monkeypatch)
    initial = env.helper.read_source_contract(env.sources)
    assert initial["status"] == "unknown"
    env.coordinator.poll()
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"
    return env


def test_unsupported_coordinator_without_verified_public_info_contract_stays_unknown(monkeypatch):
    env = modern_setup(monkeypatch)
    # Pinned provider 1.5.2 exposes device_info. An altered object lacking that
    # public property must not silently acquire the supported display contract.
    monkeypatch.delattr(type(env.coordinator), "device_info", raising=False)
    assert env.helper._legacy_status(env.coordinator, env.entries["native"]) is None
    first = env.helper.read_source_contract(env.sources)
    assert first["status"] == "unknown"
    env.coordinator.poll()
    result = env.helper.read_source_contract(env.sources)
    assert result["status"] == "unknown"
    assert env.helper._watches == {} and env.helper._tank_watches == {}


def test_invalid_read_revokes_old_proof_even_if_original_values_are_restored(monkeypatch):
    env = accepted(monkeypatch)
    status = env.coordinator.device._status
    duty = status.pump_duty
    status.pump_duty = object()
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    status.pump_duty = duty
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.notify()
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.poll()
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"


def test_invalid_listener_cannot_make_in_place_repair_a_fresh_network_generation(monkeypatch):
    env = accepted(monkeypatch)
    status = env.coordinator.device._status
    zones = status.zones
    status.zones = []
    env.coordinator.notify()
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    status.zones = zones
    env.coordinator.notify()
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.poll()
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"


def test_reentrant_poll_during_entity_read_does_not_combine_two_generations(monkeypatch):
    env = accepted(monkeypatch)
    states = env.helper.runtime.hass.states
    original = states.get
    fired = []

    def read(entity_id):
        if entity_id == env.sources["pump_status_entity"] and not fired:
            fired.append(True)
            env.coordinator.poll()
        return original(entity_id)

    monkeypatch.setattr(states, "get", read)
    result = env.helper.read_source_contract(env.sources)
    assert fired
    assert result["status"] == "unknown"
    monkeypatch.setattr(states, "get", original)
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"


def test_reentrant_entry_reload_cannot_return_old_entry_poll_proof(monkeypatch):
    env = accepted(monkeypatch)
    states = env.helper.runtime.hass.states
    original = states.get
    fired = []

    def read(entity_id):
        if entity_id == env.sources["pump_status_entity"] and not fired:
            fired.append(True)
            env.entries["native"] = copy(env.entries["native"])
        return original(entity_id)

    monkeypatch.setattr(states, "get", read)
    result = env.helper.read_source_contract(env.sources)
    assert fired and result["status"] == "unknown"


def test_reentrant_source_rebind_cannot_return_previous_device_contract(monkeypatch):
    env = accepted(monkeypatch)
    states = env.helper.runtime.hass.states
    original = states.get
    fired = []
    pump_id = env.sources["pump_status_entity"]

    def read(entity_id):
        if entity_id == pump_id and not fired:
            fired.append(True)
            env.rows[pump_id].device_id = "neighbor_registry_device"
        return original(entity_id)

    monkeypatch.setattr(states, "get", read)
    result = env.helper.read_source_contract(env.sources)
    assert fired and result["status"] == "unknown"


def test_class_shared_neighbor_zone_objects_cannot_establish_current_device_identity(monkeypatch):
    env = accepted(monkeypatch)
    info = copy(env.coordinator._device_info)
    info.device_id, info.long_id = "neighbor", "neighbor"
    info.zones = [copy(row) for row in info.zones]
    current = copy(env.coordinator.device._status)
    current.long_id = "neighbor"
    env.data.DeviceImpl(info, current)
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"


@pytest.mark.parametrize("case", ["duplicate", "missing", "boolean", "foreign_long_id", "opaque_status"])
def test_current_native_shape_cannot_borrow_a_verified_device_identity(case, monkeypatch):
    env = accepted(monkeypatch)
    device = env.coordinator.device
    if case == "duplicate":
        device._status.zones[1].zone_id = device._status.zones[0].zone_id
    elif case == "missing":
        device._status.zones.pop()
    elif case == "boolean":
        device._status.zones[0].zone_id = True
    elif case == "foreign_long_id":
        device._status.long_id = "neighbor"
    else:
        opaque = type("DeviceStatus", (), {"__module__": "aioaquarea.data"})()
        opaque.__dict__.update(vars(device._status))
        device._status = opaque
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"


@pytest.mark.parametrize("role,state", [
    ("pump_status_entity", "Off"),
    ("direction_entity", "WATER"),
    ("zone_entities", "cool"),
])
def test_fresh_entity_conflicts_cannot_borrow_current_native_snapshot(role, state, monkeypatch):
    env = accepted(monkeypatch)
    entity_id = env.sources[role][0] if role == "zone_entities" else env.sources[role]
    env.state(entity_id, state)
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"


@pytest.mark.parametrize("stamp", [0, 800, 1006])
def test_missing_old_or_future_pump_report_is_never_current(stamp, monkeypatch):
    env = accepted(monkeypatch)
    env.state(env.sources["pump_status_entity"], "On", stamp=stamp)
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"


@pytest.mark.parametrize("role", ["pump_status_entity", "direction_entity", "zone_entities"])
def test_neighbor_registry_device_cannot_reuse_current_snapshot(role, monkeypatch):
    env = accepted(monkeypatch)
    entity_id = env.sources[role][0] if role == "zone_entities" else env.sources[role]
    env.rows[entity_id].device_id = "unrelated_registry_device"
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"


def test_reload_entry_object_cannot_inherit_previous_poll_approval(monkeypatch):
    env = accepted(monkeypatch)
    env.entries["native"] = copy(env.entries["native"])
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"


def test_unchanged_listener_does_not_extend_snapshot_age(monkeypatch):
    env = accepted(monkeypatch)
    original = env.helper.read_source_contract(env.sources)["observed_at"]
    env.clock[0] += 100
    env.coordinator.notify()
    assert env.helper.read_source_contract(env.sources)["observed_at"] == original
    env.clock[0] += 21
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"


def test_failed_poll_cannot_become_fresh_after_flag_only_recovery(monkeypatch):
    env = accepted(monkeypatch)
    env.coordinator.notify(success=False)
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.notify(success=True)
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.poll()
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"


def test_returned_contract_cannot_mutate_following_read_or_gain_control_watches(monkeypatch):
    env = accepted(monkeypatch)
    first = env.helper.read_source_contract(env.sources)
    first["zones"][0]["enabled"] = False
    first["program"]["state"] = "cooling"
    next_read = env.helper.read_source_contract(env.sources)
    assert next_read["status"] == "verified"
    assert next_read["zones"][0]["enabled"] is True
    assert next_read["program"]["state"] == "heating"
    assert env.helper._watches == {}
    assert env.helper.runtime.hass.services.calls == []

