"""Pending static-metadata checks cannot renew live proof or control authority."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.display_operation import classify_display_operation
from custom_components.solar_pilot.heatpump_learning import classify_heatpump_observation
from test_aquarea_display_snapshot86 import modern_setup
from test_display_operation83 import contract_snapshot


class PendingInspection:
    def done(self):
        return False

    def cancel(self):
        pass


def pending_refresh(monkeypatch, *, poll_at=1300):
    """Keep metadata inspection pending while independently reporting live data."""
    env = modern_setup(monkeypatch, version="1.5.4")
    env.inspections = []

    def create_task(coroutine):
        # This test exercises the synchronous consumer while the executor is
        # busy. Closing its unscheduled coroutine avoids a leaked coroutine.
        coroutine.close()
        task = PendingInspection()
        env.inspections.append(task)
        return task

    env.helper.runtime.hass.async_create_task = create_task
    assert env.helper.read_source_contract(env.sources)["reason_code"] == "native_poll_not_current"
    env.clock[0] = poll_at
    report_sources(env, poll_at)
    env.coordinator.poll()
    env.original_contract = env.helper.read_source_contract(env.sources)
    assert env.original_contract["status"] == "verified"
    env.settings_before = deepcopy(env.helper.runtime.panasonic.settings)
    return env


def report_sources(env, stamp):
    env.state(env.sources["pump_status_entity"], "On", stamp=stamp)
    env.state(env.sources["direction_entity"], "PUMP", stamp=stamp)
    for eid in env.sources["zone_entities"]:
        env.state(eid, "heat", {"hvac_action": "off"}, stamp=stamp)
    env.state(env.sources["tank_entity"], "idle", {"operation_mode": "idle"}, stamp=stamp)


def observation(contract, *, source_at=1300):
    p = contract_snapshot()
    p["source_contract"] = contract
    p["native_task"]["observed_at"] = source_at
    p["task_context"]["observed_at"] = source_at
    p["display_tank"]["observed_at"] = source_at
    p["power_observed_at"] = source_at
    p["power_activity"]["observed_at"] = source_at
    for row in p["power_activity"]["supplies"]:
        row["observed_at"] = source_at - (3 - row["number"])
    return p


def assert_no_new_authority(env):
    assert env.helper.runtime.panasonic.settings == env.settings_before
    assert env.helper._watches == {} and env.helper._tank_watches == {}
    assert env.helper._legacy_status(env.coordinator, env.entries["native"]) is None
    assert env.coordinator.api_calls == []
    assert env.helper.runtime.hass.services.calls == []


def assert_display_does_not_change_learning(p, now):
    original = deepcopy(p)
    learning = classify_heatpump_observation(p, now_wall=now)
    result = classify_display_operation(p, now_wall=now)
    assert result["model_eligible"] is False and result["read_only"] is True
    assert p == original
    assert classify_heatpump_observation(p, now_wall=now) == learning
    # Compatibility evidence and its refresh have no learning authority.
    without_contract = deepcopy(p)
    without_contract.pop("source_contract")
    assert classify_heatpump_observation(without_contract, now_wall=now) == learning
    assert learning["tier"] == "unknown"
    return result


def test_pending_metadata_refresh_preserves_original_live_timestamps_and_expiry(monkeypatch):
    env = pending_refresh(monkeypatch)
    before_p = observation(env.original_contract)
    before = assert_display_does_not_change_learning(before_p, 1300)
    assert before["function"] == "space_heating" and before["tier"] == "derived"
    assert before["observed_at"] == 1298 and before["valid_until"] == 1418

    env.clock[0] = 1301
    for _ in range(3):
        contract = env.helper.read_source_contract(env.sources)
        assert contract == env.original_contract
        result = assert_display_does_not_change_learning(observation(contract), env.clock[0])
        assert result == before
    assert len(env.inspections) == 1
    assert_no_new_authority(env)


@pytest.mark.parametrize("problem", [
    "stale_poll", "failed_poll", "unavailable_entity", "old_entity",
    "source_conflict", "missing_assigned_meter", "old_assigned_meter",
])
def test_pending_metadata_refresh_never_overcomes_missing_live_evidence(problem, monkeypatch):
    env = pending_refresh(monkeypatch, poll_at=1180 if problem == "stale_poll" else 1300)
    env.clock[0] = 1301
    if problem == "stale_poll":
        report_sources(env, 1300)
    elif problem == "failed_poll":
        env.coordinator.notify(success=False)
    elif problem == "unavailable_entity":
        env.state(env.sources["pump_status_entity"], "unavailable", stamp=1300)
    elif problem == "old_entity":
        env.state(env.sources["pump_status_entity"], "On", stamp=1180)
    elif problem == "source_conflict":
        env.state(env.sources["pump_status_entity"], "Off", stamp=1300)

    contract = env.helper.read_source_contract(env.sources)
    # Static provider compatibility remains known during its bounded check;
    # only the independent live-data guards decide whether it can be used.
    assert contract["provider_loaded"] is True
    assert contract["compatibility"]["verified"] is True
    p = observation(contract)
    if problem == "missing_assigned_meter":
        p["power_activity"]["supplies"][0]["role"] = "unconfirmed"
    elif problem == "old_assigned_meter":
        p["power_activity"]["supplies"][0]["observed_at"] = 1180
    result = assert_display_does_not_change_learning(p, env.clock[0])
    assert result["function"] is None and result["tier"] == "unknown"
    assert result["observed_at"] is None and result["valid_until"] is None
    assert len(env.inspections) == 1
    assert_no_new_authority(env)
