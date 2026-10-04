"""Queued entity addition/removal with explicit scheduler doubles, not HA Core."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

from test_runtime import build


@pytest.fixture
def queued_platform(monkeypatch):
    runtime, hass = build()
    runtime.configs.clear()
    queued, live, tasks = [], [], []
    entity_module = ModuleType("homeassistant.helpers.entity")

    class Entity:
        async def async_added_to_hass(self):
            pass

        def async_on_remove(self, callback):
            if not hasattr(self, "_remove_callbacks"):
                self._remove_callbacks = []
            self._remove_callbacks.append(callback)

        def async_write_ha_state(self):
            self.writes = getattr(self, "writes", 0) + 1

        async def async_remove(self, *_args, **_kwargs):
            # HA completes its ADDED transition after the integration hook.
            # Removing eagerly inside that hook must fail this double.
            assert self.lifecycle == "ADDED"
            for callback in getattr(self, "_remove_callbacks", []):
                callback()
            if self in live:
                live.remove(self)
            self.lifecycle = "REMOVED"
            self.removes = getattr(self, "removes", 0) + 1

    entity_module.Entity = Entity
    entity_module.DeviceInfo = dict
    monkeypatch.setitem(sys.modules, entity_module.__name__, entity_module)
    source = Path(__file__).parents[1] / "custom_components/solar_pilot/entity.py"
    spec = importlib.util.spec_from_file_location("custom_components.solar_pilot._entity_lifecycle49", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def schedule(coroutine, *_args, **_kwargs):
        task = asyncio.create_task(coroutine)
        tasks.append(task)
        return task

    def entry_task(target_hass, coroutine, _name, *, eager_start=True):
        assert target_hass is hass and eager_start is False
        return schedule(coroutine)

    runtime.entry.async_create_task = entry_task
    runtime.platforms.register(
        "sensor", lambda rows: queued.extend(rows),
        lambda: [module.SolarEntity(runtime, "state", "Status", key)
                 for key in runtime.configs],
    )

    async def finish_additions(before_cleanup=None):
        rows = list(queued)
        queued.clear()
        for entity in rows:
            # EntityPlatform rejects a duplicate unique ID before the add hook.
            assert not any(existing._attr_unique_id == entity._attr_unique_id
                           for existing in live), "queued addition collides with live entity"
            entity.hass = hass
            entity.entity_id = f"sensor.{entity.key}"
            entity.lifecycle = "ADDING"
            await entity.async_added_to_hass()
            entity.lifecycle = "ADDED"
            live.append(entity)
            # EntityPlatform performs the initial write after the hook returns.
            entity.async_write_ha_state()
        if before_cleanup is not None:
            await before_cleanup()
        if tasks:
            await asyncio.gather(*tasks)
            tasks.clear()
        return rows

    return runtime, queued, live, finish_additions


@pytest.mark.asyncio
async def test_profile_retired_before_queued_addition_leaves_no_entity_or_subscription(queued_platform):
    runtime, queued, live, finish = queued_platform
    runtime.configs["b"] = {"name": "Pending consumer"}
    await runtime.platforms.refresh()
    retired = queued[0]
    assert getattr(retired, "hass", None) is None

    runtime.configs.clear()
    await runtime.platforms.refresh()
    await finish()

    assert not live and not runtime.listeners
    assert not runtime.platforms.entities["sensor"]
    assert getattr(retired, "writes", 0) == 0
    assert retired.lifecycle == "REMOVED"


@pytest.mark.asyncio
async def test_queued_addition_after_runtime_close_cannot_subscribe_or_write(queued_platform):
    runtime, queued, live, finish = queued_platform
    runtime.configs["b"] = {"name": "Pending consumer"}
    await runtime.platforms.refresh()
    pending = queued[0]
    await runtime.close()

    await finish()

    assert not live and not runtime.listeners
    assert getattr(pending, "writes", 0) == 0
    assert pending.lifecycle == "REMOVED"


@pytest.mark.asyncio
async def test_normal_addition_and_later_retirement_remove_exact_subscription(queued_platform):
    runtime, _, live, finish = queued_platform
    runtime.configs["b"] = {"name": "Active consumer"}
    await runtime.platforms.refresh()
    added, = await finish()
    assert live == [added] and len(runtime.listeners) == 1
    assert added.writes == 1

    runtime.publish()
    assert added.writes == 2
    runtime.configs.clear()
    await runtime.platforms.refresh()

    assert not live and not runtime.listeners
    assert added.lifecycle == "REMOVED" and added.removes == 1


@pytest.mark.asyncio
async def test_retiring_then_readding_same_identity_reuses_single_pending_addition(queued_platform):
    runtime, queued, live, finish = queued_platform
    runtime.configs["b"] = {"name": "First consumer"}
    await runtime.platforms.refresh()
    old = queued[0]
    runtime.configs.clear()
    await runtime.platforms.refresh()
    runtime.configs["b"] = {"name": "Re-added consumer"}
    await runtime.platforms.refresh()
    assert queued == [old]

    await finish()

    assert live == [old]
    assert len(runtime.listeners) == 1
    assert runtime.platforms.entities["sensor"][old._attr_unique_id] is old
    assert old._attr_device_info["name"] == "Re-added consumer"
    assert old.writes == 1 and old.lifecycle == "ADDED"


@pytest.mark.asyncio
async def test_revival_after_add_hook_restores_publication_before_delayed_cleanup(queued_platform):
    runtime, queued, live, finish = queued_platform
    runtime.configs["b"] = {"name": "Initially pending"}
    await runtime.platforms.refresh()
    old = queued[0]
    runtime.configs.clear()
    await runtime.platforms.refresh()

    async def revive():
        # The inactive hook has run, but its non-eager removal task has not.
        assert old.lifecycle == "ADDED" and not runtime.listeners
        runtime.configs["b"] = {"name": "Revived after hook"}
        await runtime.platforms.refresh()

    await finish(before_cleanup=revive)

    assert live == [old] and old.lifecycle == "ADDED"
    assert not queued and len(runtime.listeners) == 1
    assert runtime.platforms.entities["sensor"][old._attr_unique_id] is old
    assert old._attr_device_info["name"] == "Revived after hook"
    writes = getattr(old, "writes", 0)
    runtime.publish()
    assert old.writes == writes + 1
