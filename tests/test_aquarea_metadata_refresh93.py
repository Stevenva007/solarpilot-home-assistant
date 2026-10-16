"""Metadata refresh must not manufacture thermal-task gaps in fresh history."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import sys
from types import ModuleType

import pytest

from custom_components.solar_pilot.display_operation import classify_display_operation
from custom_components.solar_pilot.heatpump_history import HeatpumpHistory
from custom_components.solar_pilot import native_program
from test_aquarea_display_snapshot86 import modern_setup
from test_display_operation82 import snapshot


def fresh_poll(env, stamp):
    env.clock[0] = stamp
    env.coordinator.poll()
    env.state(env.sources["pump_status_entity"], "On", stamp=stamp)
    env.state(env.sources["direction_entity"], "PUMP", stamp=stamp)
    for entity in env.sources["zone_entities"]:
        env.state(entity, "heat", {"hvac_action": "off"}, stamp=stamp)
    env.state(env.sources["tank_entity"], "idle", {"operation_mode": "idle"}, stamp=stamp)


def pump_snapshot(env):
    stamp = env.clock[0]
    value = snapshot()
    contract = env.helper.read_source_contract(env.sources)
    for key in ("native_task", "task_context"):
        value[key]["observed_at"] = contract.get("observed_at")
    value["power_activity"]["observed_at"] = stamp
    value["power_observed_at"] = stamp
    for row in value["power_activity"]["supplies"]:
        row["observed_at"] = stamp
    value["display_tank"]["entity_id"] = env.sources["tank_entity"]
    value["display_tank"]["observed_at"] = env.helper.runtime.hass.states.get(
        env.sources["tank_entity"]).last_reported.timestamp()
    value["source_contract"] = contract
    return value


def background_refresh(monkeypatch, env, *, outcome="verified"):
    """A real pending task, with a deliberately controllable executor result."""
    gate, tasks = asyncio.Event(), []
    metadata = deepcopy(env.helper._display_metadata)
    if outcome == "unsupported":
        metadata.update(compatibility=None, compatibility_state="unknown")
    elif outcome == "incompatible":
        metadata.update(compatibility=None, compatibility_state="incompatible",
                        reason_code="provider_semantics_changed")
    elif outcome == "unloaded":
        metadata.update(integration_loaded=False, compatibility=None)
    module = ModuleType("custom_components.solar_pilot.analysis_export")
    module.installed_aquarea_metadata = lambda: metadata
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(native_program, "inspect_loaded_aquarea_semantics", lambda: {})

    async def executor(function):
        await gate.wait()
        if outcome == "failed":
            raise RuntimeError("Synthetic inspection failure")
        return function()

    def create(coroutine):
        task = asyncio.create_task(coroutine)
        tasks.append(task)
        return task

    env.helper.runtime.hass.async_add_executor_job = executor
    env.helper.runtime.hass.async_create_task = create
    return gate, tasks


@pytest.mark.asyncio
async def test_fresh_tasks_and_history_stay_continuous_before_at_and_after_metadata_ttl(monkeypatch):
    env = modern_setup(monkeypatch)
    env.helper.read_source_contract(env.sources)  # Subscribe before the next real provider poll.
    gate, tasks = background_refresh(monkeypatch, env)
    history = HeatpumpHistory()
    try:
        for stamp in (1295, 1299, 1300, 1301, 1305):
            fresh_poll(env, stamp)
            value = pump_snapshot(env)
            display = classify_display_operation(value, now_wall=stamp)
            assert display["function"] == "space_heating" and display["tier"] == "derived"
            history.observe(value, {}, datetime.fromtimestamp(stamp, timezone.utc))
        assert len(tasks) == 1  # Multiple renders/ticks share one executor inspection.
        detail = history.detail(None, datetime.fromtimestamp(1305, timezone.utc))
        assert [(row["task"], row["duration_s"]) for row in detail["task_sessions"]] == [("space_heating", 10)]
        assert detail["task_totals"] == [{"task": "space_heating", "label": "Verwarmen", "tier": "derived", "on_s": 10}]
        assert not env.helper._watches and not env.helper._tank_watches
        assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []
        gate.set()
        await tasks[0]
        fresh_poll(env, 1306)
        assert pump_snapshot(env)["source_contract"]["status"] == "verified"
        assert env.helper._display_metadata_checked == 1305
    finally:
        gate.set()
        await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_three_refresh_cycles_with_delayed_executor_keep_fresh_history_continuous(monkeypatch):
    env = modern_setup(monkeypatch)
    env.helper.read_source_contract(env.sources)
    gate, tasks = background_refresh(monkeypatch, env)
    history, pending_since = HeatpumpHistory(), None
    try:
        for stamp in range(1000, 1951, 5):
            fresh_poll(env, stamp-1)
            env.clock[0] = stamp  # Capture a second after the actual native report.
            value = pump_snapshot(env)
            display = classify_display_operation(value, now_wall=stamp)
            assert display["function"] == "space_heating"
            assert value["source_contract"]["observed_at"] == stamp-1
            assert display["observed_at"] == stamp-1
            assert display["valid_until"] == stamp-1+120
            history.observe(value, {}, datetime.fromtimestamp(stamp, timezone.utc))
            pending = env.helper._display_metadata_task
            if pending is not None:
                if pending_since is None:
                    pending_since = stamp
                if stamp-pending_since >= 10:
                    gate.set()
                    await pending
                    gate.clear()
                    pending_since = None
        assert len(tasks) == 3
        detail = history.detail(None, datetime.fromtimestamp(1950, timezone.utc))
        assert [(row["task"], row["duration_s"]) for row in detail["task_sessions"]] == [("space_heating", 950)]
        assert detail["on_s"] == 950
        assert detail["task_totals"] == [{"task": "space_heating", "label": "Verwarmen", "tier": "derived", "on_s": 950}]
        assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []
    finally:
        gate.set()
        await asyncio.gather(*tasks)


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["unsupported", "incompatible", "unloaded", "failed"])
async def test_completed_unusable_refresh_immediately_revokes_previous_proof(outcome, monkeypatch):
    env = modern_setup(monkeypatch)
    env.helper.read_source_contract(env.sources)
    gate, tasks = background_refresh(monkeypatch, env, outcome=outcome)
    fresh_poll(env, 1301)
    assert pump_snapshot(env)["source_contract"]["status"] == "verified"
    gate.set()
    await tasks[0]
    fresh_poll(env, 1302)
    value = pump_snapshot(env)
    assert value["source_contract"]["status"] == "unknown"
    assert classify_display_operation(value, now_wall=1302)["function"] is None
    assert env.helper._display_metadata_task is None


@pytest.mark.asyncio
async def test_pending_refresh_grace_is_bounded_and_does_not_renew_original_metadata_age(monkeypatch):
    env = modern_setup(monkeypatch)
    env.helper.read_source_contract(env.sources)
    gate, tasks = background_refresh(monkeypatch, env)
    try:
        fresh_poll(env, 1301)
        assert pump_snapshot(env)["source_contract"]["status"] == "verified"
        fresh_poll(env, 1330)
        assert pump_snapshot(env)["source_contract"]["status"] == "verified"
        fresh_poll(env, 1330.001)
        assert pump_snapshot(env)["source_contract"]["status"] == "unknown"
        assert env.helper._display_metadata_checked == 1000
        assert len(tasks) == 1
    finally:
        gate.set()
        await asyncio.gather(*tasks)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["provider_module", "sdk_identity", "registry_binding", "failed_poll", "old_poll", "old_source"])
async def test_refresh_grace_cannot_lend_proof_to_changed_or_stale_native_sources(change, monkeypatch):
    env = modern_setup(monkeypatch)
    env.helper.read_source_contract(env.sources)
    gate, tasks = background_refresh(monkeypatch, env)
    try:
        fresh_poll(env, 1301)
        assert pump_snapshot(env)["source_contract"]["status"] == "verified"
        if change == "provider_module":
            monkeypatch.setitem(sys.modules, "custom_components.aquarea", ModuleType("custom_components.aquarea"))
        elif change == "sdk_identity":
            monkeypatch.setattr(native_program, "loaded_semantic_identity", lambda: ("different loaded SDK",))
        elif change == "registry_binding":
            env.rows[env.sources["pump_status_entity"]].device_id = "another_device"
        elif change == "failed_poll":
            env.coordinator.notify(success=False)
        elif change == "old_poll":
            env.helper._display_contract_watches[id(env.coordinator)]["observed"] -= 121
        else:
            env.state(env.sources["pump_status_entity"], "On", stamp=1180)
        value = pump_snapshot(env)
        assert value["source_contract"]["status"] == "unknown"
        assert classify_display_operation(value, now_wall=1301)["function"] is None
        assert env.coordinator.api_calls == [] and env.helper.runtime.hass.services.calls == []
    finally:
        gate.set()
        await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_missing_executor_cannot_refresh_an_existing_compatibility_proof(monkeypatch):
    env = modern_setup(monkeypatch)
    await env.helper.async_prepare_display_metadata()
    assert env.helper._contract_metadata() == {}
