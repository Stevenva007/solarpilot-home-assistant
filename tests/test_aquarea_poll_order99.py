"""Listener proof must survive read ordering without granting read freshness."""
from copy import deepcopy

import pytest

from test_aquarea_display_snapshot86 import modern_setup
from test_aquarea_semantics98 import split_setup
from test_aquarea_metadata_refresh93 import fresh_poll, pump_snapshot
from custom_components.solar_pilot.display_operation import classify_display_operation


@pytest.fixture(params=["modern_special_status", "modern_split_status"])
def env(request, monkeypatch):
    value = modern_setup(monkeypatch) if request.param == "modern_special_status" else split_setup(monkeypatch)
    value.helper.read_source_contract(value.sources)
    fresh_poll(value, 1000)
    assert value.helper.read_source_contract(value.sources)["status"] == "verified"
    return value


def test_new_valid_poll_read_before_notification_recovers_on_that_notification(env):
    previous = env.helper.read_source_contract(env.sources)
    env.clock[0] = 1005
    env.coordinator.poll(notify=False)
    changed = env.helper.read_source_contract(env.sources)
    assert changed["status"] == "unknown" and changed["reason_code"] == "native_display_snapshot_changed"
    for _ in range(3):
        pending = env.helper.read_source_contract(env.sources)
        assert pending["status"] == "unknown" and pending["observed_at"] is None
    # The same actual provider update is now reported by its real listener.
    env.coordinator.notify()
    accepted = env.helper.read_source_contract(env.sources)
    assert accepted["status"] == "verified" and accepted["observed_at"] == 1005
    assert accepted["observed_at"] > previous["observed_at"]
    result = classify_display_operation(pump_snapshot(env), now_wall=1005)
    assert result["function"] == "space_heating" and result["tier"] == "derived"
    env.clock[0] = 1009
    assert env.helper.read_source_contract(env.sources)["observed_at"] == 1005
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


def test_expired_proof_reads_cannot_consume_a_later_valid_unnotified_generation(env):
    env.clock[0] = 1121
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.poll(notify=False)
    for _ in range(3):
        assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    fresh_time = env.clock[0]
    for entity in (env.sources["pump_status_entity"], env.sources["direction_entity"],
                   env.sources["tank_entity"], *env.sources["zone_entities"]):
        state = env.helper.runtime.hass.states.get(entity)
        env.state(entity, state.state, deepcopy(state.attributes), stamp=fresh_time)
    env.coordinator.notify()
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"
    assert env.helper.read_source_contract(env.sources)["observed_at"] == fresh_time


@pytest.mark.parametrize("repair", [False, True])
def test_in_place_status_change_and_optional_repair_do_not_create_listener_proof(env, repair):
    device = env.coordinator.device
    before = device._status.direction
    device._status.direction = env.data.DeviceDirection.WATER
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    if repair:
        device._status.direction = before
    env.coordinator.notify()
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    fresh_poll(env, 1005)
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"


def test_failed_pending_poll_is_not_repaired_by_success_notification_on_same_generation(env):
    env.clock[0] = 1005
    env.coordinator.poll(notify=False)
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.notify(success=False)
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.notify(success=True)
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    fresh_poll(env, 1010)
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"


def test_cached_pending_generation_cannot_become_live_by_edit_then_notify(monkeypatch):
    env = split_setup(monkeypatch)
    env.helper.read_source_contract(env.sources)
    fresh_poll(env, 1000)
    env.clock[0] = 1005
    env.poll(quality=env.quality.CACHED, notify=False)
    assert env.helper.read_source_contract(env.sources)["reason_code"] == "native_status_not_live"
    env.coordinator.device._status.data_mode = env.quality.LIVE
    env.coordinator.notify()
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    fresh_poll(env, 1010)
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"


@pytest.mark.parametrize("route", ["programme", "action"])
@pytest.mark.parametrize("previous_failure", [False, True])
def test_programme_and_action_reads_leave_pending_valid_generation_for_its_actual_callback(env, route, previous_failure):
    entity = env.sources["zone_entities"][0]
    reader = env.helper.read if route == "programme" else env.helper.read_device_action
    reader(entity)
    fresh_poll(env, 1001)
    assert reader(entity)["fresh"] is True
    if previous_failure:
        env.coordinator.notify(success=False)
        assert reader(entity)["fresh"] is False
    env.clock[0] = 1005
    env.coordinator.poll(notify=False)
    for _ in range(3):
        assert reader(entity)["fresh"] is False
    env.coordinator.notify()
    assert reader(entity)["fresh"] is True and reader(entity)["observed_at"] == 1005
    env.clock[0] = 1010
    assert reader(entity)["observed_at"] == 1005
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


def test_rejected_display_status_identity_cannot_be_repaired_in_place_through_another_wrapper(env):
    env.clock[0] = 1005
    env.coordinator.poll(notify=False)
    device = env.coordinator.device
    status = device._status
    original = status.long_id
    status.long_id = "fictional-unmatched-native-device"
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    status.long_id = original
    env.coordinator.device = deepcopy(device)
    env.coordinator.device._status = status
    env.coordinator.notify()
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    fresh_poll(env, 1010)
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"


@pytest.mark.parametrize("route", ["programme", "action"])
def test_legacy_status_only_optimistic_change_still_requires_another_actual_poll(route, monkeypatch):
    from test_cooling_native80 import legacy_setup

    helper, coordinator, *_ = legacy_setup(monkeypatch)
    reader = helper.read if route == "programme" else helper.read_tank_action
    entity = "climate.salon" if route == "programme" else "water_heater.tank"
    reader(entity)
    coordinator.poll()
    assert reader(entity)["fresh"]
    coordinator.device.replace_status()
    assert not reader(entity)["fresh"]
    coordinator.notify()
    assert not reader(entity)["fresh"]
    coordinator.poll()
    assert reader(entity)["fresh"]
