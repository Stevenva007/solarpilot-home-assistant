"""Dashboard intent routing through the real entry-point handler and its lock."""
import asyncio
from types import SimpleNamespace

import pytest

from test_entry_lifecycle49 import entry_functions


def entry(entry_id, *, zones=("climate.room",), closed=False):
    events = []
    runtime = SimpleNamespace(_lock=asyncio.Lock(), _closed=closed)

    async def set_override(entity_id, mode):
        assert runtime._lock.locked()
        events.append(("intent", entity_id, mode))

    async def tick():
        assert not runtime._lock.locked()
        events.append(("tick",))

    runtime.smart_climate = SimpleNamespace(
        settings={"zone_entities": list(zones)}, async_set_override=set_override)
    runtime.tick = tick
    return SimpleNamespace(entry_id=entry_id, runtime_data=runtime), events


async def invoke(entries, *, entry_id="", entity_id="climate.room", mode="off"):
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_entries=lambda _domain: entries))
    call = SimpleNamespace(data={"config_entry_id": entry_id, "entity_id": entity_id, "mode": mode})
    await entry_functions()["_handle_set_climate_override"](hass, call)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["automatic", "auto", "off", "review"])
async def test_dashboard_switch_persists_intent_under_lock_then_uses_normal_tick(mode):
    selected, events = entry("selected")
    await invoke([selected], mode=mode)
    assert events == [("intent", "climate.room", mode)] + ([] if mode == "review" else [("tick",)])


@pytest.mark.asyncio
async def test_without_entry_id_routes_by_selected_zone_instead_of_first_entry():
    other, other_events = entry("other", zones=("climate.other",))
    selected, events = entry("selected")
    await invoke([other, selected])
    assert not other_events
    assert events == [("intent", "climate.room", "off"), ("tick",)]


@pytest.mark.asyncio
async def test_explicit_entry_resolves_shared_zone_without_touching_other_entry():
    other, other_events = entry("other")
    selected, events = entry("selected")
    await invoke([other, selected], entry_id="selected", mode="auto")
    assert not other_events
    assert events == [("intent", "climate.room", "auto"), ("tick",)]


@pytest.mark.asyncio
@pytest.mark.parametrize("entry_id,entity_id", [("", "climate.room"), ("missing", "climate.room"), ("one", "climate.not_selected")])
async def test_ambiguous_missing_or_wrong_entry_never_picks_an_arbitrary_runtime(entry_id, entity_id):
    one, first_events = entry("one")
    two, second_events = entry("two")
    with pytest.raises(ValueError, match="Kies één"):
        await invoke([one, two], entry_id=entry_id, entity_id=entity_id)
    assert not first_events and not second_events


@pytest.mark.asyncio
async def test_unloaded_entry_rejects_without_dashboard_or_climate_mutation():
    selected, events = entry("selected", closed=True)
    with pytest.raises(ValueError, match="niet geladen"):
        await invoke([selected])
    assert not events


@pytest.mark.asyncio
async def test_close_while_dashboard_waits_for_lock_is_rechecked_before_persisting():
    selected, events = entry("selected")
    await selected.runtime_data._lock.acquire()
    request = asyncio.create_task(invoke([selected]))
    await asyncio.sleep(0)
    selected.runtime_data._closed = True
    selected.runtime_data._lock.release()
    with pytest.raises(ValueError, match="niet geladen"):
        await request
    assert not events
