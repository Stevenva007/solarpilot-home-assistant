"""Adverse provider event ordering through the public read-only adapters."""
from copy import deepcopy

import pytest

from test_aquarea_semantics98 import split_setup
from test_cooling_native80 import legacy_setup


JOURNALS = ("display", "action", "programme")


def observation(env, journal):
    helper = env.helper
    if journal == "display":
        raw = helper.read_source_contract(env.sources)
        return raw["status"] == "verified", raw.get("observed_at")
    entity = env.sources["zone_entities"][0]
    raw = helper.read_device_action(entity) if journal == "action" else helper.read(entity)
    return raw["fresh"], raw.get("observed_at")


def accepted(monkeypatch, journal):
    env = split_setup(monkeypatch)
    assert observation(env, journal)[0] is False
    env.poll()
    assert observation(env, journal) == (True, env.clock[0])
    return env


def reuse_status_in_new_device(env, status):
    """A new wrapper is not a replacement for the rejected typed response."""
    env.poll(notify=False)
    device = env.coordinator.device
    zone_type = type(next(iter(device.zones.values())))
    device._status = status
    device._zones = {row.zone_id: zone_type(env.data.DeviceZoneInfo(zone_id=row.zone_id), row)
                     for row in status.zones}
    device._tank = env.data.TankImpl(device, status.tank_status[0]) if device.has_tank else None


@pytest.mark.parametrize("journal", JOURNALS)
def test_repeated_reads_before_real_callback_do_not_consume_or_date_the_valid_response(monkeypatch, journal):
    env = accepted(monkeypatch, journal)
    env.clock[0] += 1
    env.poll(notify=False)
    for _ in range(4):
        assert observation(env, journal)[0] is False
    env.clock[0] += 1
    env.coordinator.notify()
    fresh, original = observation(env, journal)
    assert fresh and original == env.clock[0]
    env.clock[0] += 1
    assert observation(env, journal) == (True, original)
    assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []


@pytest.mark.parametrize("journal", JOURNALS)
def test_pending_valid_response_recovers_after_a_previous_failed_callback(monkeypatch, journal):
    env = accepted(monkeypatch, journal)
    env.coordinator.notify(success=False)
    env.clock[0] += 1
    env.poll(notify=False)
    assert env.coordinator.last_update_success is False
    for _ in range(3):
        assert observation(env, journal)[0] is False
    env.clock[0] += 1
    env.coordinator.notify(success=True)
    assert observation(env, journal) == (True, env.clock[0])


@pytest.mark.parametrize("journal", JOURNALS)
def test_a_failure_callback_then_success_on_the_same_response_cannot_renew_proof(monkeypatch, journal):
    env = accepted(monkeypatch, journal)
    env.clock[0] += 1
    env.poll(notify=False)
    env.coordinator.notify(success=False)
    assert observation(env, journal)[0] is False
    env.clock[0] += 1
    env.coordinator.notify(success=True)
    assert observation(env, journal)[0] is False
    env.poll()
    assert observation(env, journal) == (True, env.clock[0])


@pytest.mark.parametrize("journal", JOURNALS)
@pytest.mark.parametrize("previous_failure", (False, True))
def test_cached_response_seen_before_callback_cannot_be_repaired_to_live(monkeypatch, journal, previous_failure):
    env = accepted(monkeypatch, journal)
    if previous_failure:
        env.coordinator.notify(success=False)
    env.poll(quality=env.quality.CACHED, notify=False)
    assert observation(env, journal)[0] is False
    env.coordinator.device._status.data_mode = env.quality.LIVE
    env.coordinator.notify(success=True)
    assert observation(env, journal)[0] is False
    env.poll()
    assert observation(env, journal)[0] is True


@pytest.mark.parametrize("journal", JOURNALS)
def test_rejected_cached_status_in_new_device_wrapper_is_still_rejected(monkeypatch, journal):
    env = accepted(monkeypatch, journal)
    env.poll(quality=env.quality.CACHED, notify=False)
    assert observation(env, journal)[0] is False
    rejected = env.coordinator.device._status
    rejected.data_mode = env.quality.LIVE
    reuse_status_in_new_device(env, rejected)
    assert observation(env, journal)[0] is False
    env.coordinator.notify()
    assert observation(env, journal)[0] is False
    env.poll()
    assert observation(env, journal)[0] is True


def test_temperature_quality_rejects_cached_status_across_device_wrappers(monkeypatch):
    env = split_setup(monkeypatch)
    entity = env.sources["tank_entity"]
    env.poll(quality=env.quality.CACHED)
    assert env.helper.source_is_live(entity) is False
    rejected = env.coordinator.device._status
    rejected.data_mode = env.quality.LIVE
    reuse_status_in_new_device(env, rejected)
    assert env.helper.source_is_live(entity) is False
    env.coordinator.notify()
    assert env.helper.source_is_live(entity) is False
    env.poll()
    assert env.helper.source_is_live(entity) is True


def test_display_same_device_new_status_waits_for_its_own_callback(monkeypatch):
    env = accepted(monkeypatch, "display")
    original_device = env.coordinator.device
    env.poll(notify=False)
    replacement = env.coordinator.device
    original_device._status = replacement._status
    original_device._zones = replacement._zones
    original_device._tank = env.data.TankImpl(original_device, replacement._status.tank_status[0])
    env.coordinator.device = original_device
    assert observation(env, "display")[0] is False
    env.coordinator.notify()
    assert observation(env, "display")[0] is True


def test_display_new_device_with_previously_good_status_keeps_existing_callback_policy(monkeypatch):
    env = accepted(monkeypatch, "display")
    previous = env.coordinator.device._status
    reuse_status_in_new_device(env, previous)
    assert observation(env, "display")[0] is False
    env.coordinator.notify()
    assert observation(env, "display")[0] is True


def test_in_place_zone_rebinding_cannot_be_confirmed_by_reads_or_unchanged_callbacks(monkeypatch):
    env = accepted(monkeypatch, "display")
    device = env.coordinator.device
    previous = device.zones[1]._status
    device.zones[1]._status = deepcopy(previous)
    assert observation(env, "display")[0] is False
    device.zones[1]._status = previous
    env.coordinator.notify()
    assert observation(env, "display")[0] is False
    env.poll()
    assert observation(env, "display")[0] is True


@pytest.mark.parametrize("intervening_failed_callback", (False, True))
def test_foreign_status_identity_cannot_be_repaired_and_repackaged_as_a_new_response(monkeypatch, intervening_failed_callback):
    env = accepted(monkeypatch, "display")
    env.poll(notify=False)
    rejected = env.coordinator.device._status
    original_identity = rejected.long_id
    rejected.long_id = "another_synthetic_device"
    assert observation(env, "display")[0] is False
    rejected.long_id = original_identity
    if intervening_failed_callback:
        env.poll(notify=False)
        env.coordinator.notify(success=False)
    reuse_status_in_new_device(env, rejected)
    assert observation(env, "display")[0] is False
    env.coordinator.notify()
    assert observation(env, "display")[0] is False
    env.poll()
    assert observation(env, "display")[0] is True


@pytest.mark.parametrize("journal", ("programme", "action"))
@pytest.mark.parametrize("failed_without_callback", (False, True))
def test_legacy_unnotified_status_only_replacement_keeps_its_conservative_rights(monkeypatch, journal, failed_without_callback):
    helper, coordinator, _rows, _entries, clock = legacy_setup(monkeypatch)
    reader, entity = ((helper.read, "climate.salon") if journal == "programme" else
                      (helper.read_tank_action, "water_heater.tank"))
    assert reader(entity)["fresh"] is False
    coordinator.poll()
    assert reader(entity)["fresh"] is True
    original_device = coordinator.device
    clock[0] += 1
    coordinator.device.replace_status()
    if failed_without_callback:
        coordinator.last_update_success = False
    # The legacy protocol cannot authenticate this status-only replacement as
    # a new poll merely because a successful callback is emitted afterward.
    assert reader(entity)["fresh"] is False
    coordinator.notify(True)
    assert coordinator.device is original_device
    assert reader(entity)["fresh"] is False
    clock[0] += 1
    coordinator.poll()
    assert coordinator.device is original_device
    restored = reader(entity)
    assert restored["fresh"] is True and restored["observed_at"] == clock[0]
    assert coordinator.api_calls == []
