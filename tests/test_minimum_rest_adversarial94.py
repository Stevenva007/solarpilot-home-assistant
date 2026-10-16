"""Saved OFF time never bypasses current source, binding or command evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import math
from types import SimpleNamespace as NS

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot.engine import Action
from test_device_retry_audit90 import fresh, install_clock, physical, reports
from test_runtime import build


def registry(monkeypatch):
    rows = {
        "switch.load": NS(platform="shelly", config_entry_id="fictional_entry",
            device_id="fictional_device", unique_id="fictional_relay_0"),
        "sensor.load": NS(platform="shelly", config_entry_id="fictional_entry",
            device_id="fictional_device", unique_id="fictional_power_0"),
    }
    value = NS(entities=rows, async_get=rows.get, async_get_entity_id=lambda *_args: None)
    monkeypatch.setattr(er, "async_get", lambda _hass: value)
    return rows


def off_checkpoint(monkeypatch, *, elapsed=600):
    clock = install_clock(monkeypatch)
    rows = registry(monkeypatch)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": 1800})
    runtime.mode = "observe"
    runtime.device_modes["a"] = "auto"
    reports(hass, clock, active="on", grid=500)
    runtime._observe(clock.mono, runtime._local_now())
    clock.advance(1)
    reports(hass, clock, active="off", grid=500)
    runtime._observe(clock.mono, runtime._local_now())
    clock.advance(elapsed)
    reports(hass, clock, grid=500)
    runtime._observe(clock.mono, runtime._local_now())
    saved = runtime._snapshot()
    assert "a" in saved["minimum_rest"]["devices"]
    return runtime, hass, clock, rows, saved


def remaining(runtime, clock):
    requirements, _ = runtime._device_start_diagnostics(runtime.devices()[0],
        runtime.states["a"], runtime.configs["a"], clock.mono)
    return requirements["minimum_rest"]["remaining_s"]


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["unknown", "unavailable", "restored", "future", "zero_stamp", "bool_stamp"])
async def test_saved_off_time_requires_usable_nonrestored_current_source(monkeypatch, source):
    _old, _hass, clock, _rows, saved = off_checkpoint(monkeypatch)
    clock.advance(60)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": 1800})
    runtime.store.data = saved
    reports(hass, clock, grid=500)
    obj = hass.states.get("switch.load")
    if source in ("unknown", "unavailable"):
        fresh(hass, "switch.load", source, clock)
    elif source == "restored":
        obj.attributes["restored"] = True
    elif source == "future":
        obj.last_reported = obj.last_updated = datetime.fromtimestamp(clock.wall + 6, timezone.utc)
    else:
        obj.last_reported = NS(timestamp=lambda: 0 if source == "zero_stamp" else False)
    await runtime.start()
    try:
        assert remaining(runtime, clock) == 1800
        assert not physical(hass)
    finally:
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("identity", ["unique_id", "device_id", "config_entry_id", "platform", "control_entity"])
async def test_replaced_source_cannot_inherit_another_actuators_off_time(monkeypatch, identity):
    _old, _hass, clock, rows, saved = off_checkpoint(monkeypatch)
    clock.advance(60)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": 1800})
    if identity == "control_entity":
        runtime.configs["a"]["control_entity"] = "switch.fictional_replacement"
        fresh(hass, "switch.fictional_replacement", "off", clock)
    else:
        setattr(rows["switch.load"], identity, "fictional_replacement")
    runtime.store.data = saved
    reports(hass, clock, grid=500)
    await runtime.start()
    try:
        assert remaining(runtime, clock) == 1800
        assert not physical(hass)
    finally:
        await runtime.close()


@pytest.mark.parametrize("transaction", ["pending", "owned_target", "recovery", "command_wait", "handover"])
def test_off_planning_state_cannot_checkpoint_an_uncertain_or_owned_transaction(monkeypatch, transaction):
    runtime, hass, clock, _rows, _saved = off_checkpoint(monkeypatch)
    assert runtime.states["a"].on is False
    if transaction == "pending":
        runtime.pending = {"id": "a", "watts": 350}
    elif transaction == "owned_target":
        runtime.states["a"].owned, runtime.states["a"].target_w = True, 350
    elif transaction == "recovery":
        runtime.recovery["a"] = {"watts": 350}
    elif transaction == "command_wait":
        runtime.device_retry.begin("a", 350, clock.wall)
    else:
        runtime.handover = NS(device_id="a", overview=lambda _now: {"device_id": "a", "state": "waiting"})
    assert "a" not in runtime._snapshot()["minimum_rest"]["devices"]
    assert not physical(hass)


@pytest.mark.asyncio
async def test_old_off_checkpoint_cannot_override_a_saved_on_lease(monkeypatch):
    _old, _hass, clock, _rows, saved = off_checkpoint(monkeypatch)
    saved["leases"] = {"a": {"watts": 350, "name": "Fictional load"}}
    clock.advance(60)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": 1800})
    runtime.store.data = saved
    reports(hass, clock, grid=500)
    await runtime.start()
    try:
        assert not runtime.recovery
        assert remaining(runtime, clock) == 1800
        assert not physical(hass)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_unsent_start_rejected_after_durable_intent_preserves_original_off_time(monkeypatch):
    runtime, hass, clock, _rows, saved = off_checkpoint(monkeypatch, elapsed=1900)
    original_off = saved["minimum_rest"]["devices"]["a"]["off_since_wall"]
    runtime.mode = "solar"
    reports(hass, clock, grid=-2500)
    runtime._observe(clock.mono, runtime._local_now())
    save = runtime.store.async_save
    changed = False

    async def revoke_during_journal(data):
        nonlocal changed
        await save(data)
        if not changed and "a" in data.get("leases", {}):
            changed = True
            runtime.mode = "observe"

    monkeypatch.setattr(runtime.store, "async_save", revoke_during_journal)
    await runtime._send(Action("a", 350, "Fictional sufficient solar"), clock.mono)
    assert changed and not physical(hass)
    assert runtime.pending is None and not runtime.states["a"].owned
    assert remaining(runtime, clock) == 0
    after = runtime._snapshot()["minimum_rest"]["devices"]["a"]
    assert after["off_since_wall"] == original_off
    assert after["binding"] == saved["minimum_rest"]["devices"]["a"]["binding"]


@pytest.mark.asyncio
async def test_current_external_on_discards_checkpoint_without_adopting_control(monkeypatch):
    _old, _hass, clock, _rows, saved = off_checkpoint(monkeypatch)
    clock.advance(60)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": 1800})
    runtime.store.data = deepcopy(saved)
    reports(hass, clock, active="on", grid=500)
    await runtime.start()
    try:
        assert runtime.states["a"].on and not runtime.states["a"].owned
        assert "a" not in runtime._snapshot()["minimum_rest"]["devices"]
        assert not physical(hass)
    finally:
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["saved_at_wall", "off_since_wall"])
async def test_oversized_json_integer_checkpoint_is_ignored_without_failing_start(monkeypatch, field):
    _old, _hass, clock, _rows, saved = off_checkpoint(monkeypatch)
    if field == "saved_at_wall":
        saved["minimum_rest"][field] = 10**1000
    else:
        saved["minimum_rest"]["devices"]["a"][field] = 10**1000
    clock.advance(60)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": 1800})
    runtime.store.data = saved
    reports(hass, clock, grid=500)
    await runtime.start()
    try:
        assert remaining(runtime, clock) == 1800
        assert math.isfinite(runtime.states["a"].last_off)
        assert not physical(hass)
    finally:
        await runtime.close()


@pytest.mark.parametrize("wall", [
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="infinite"),
    pytest.param(-float("inf"), id="negative_infinite"),
    pytest.param(10**1000, id="oversized_integer"),
])
def test_invalid_current_wall_cannot_create_nonfinite_monotonic_rest(monkeypatch, wall):
    _old, _hass, clock, _rows, saved = off_checkpoint(monkeypatch)
    clock.advance(60)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": 1800})
    reports(hass, clock, grid=500)
    runtime.minimum_rest.restore(saved["minimum_rest"], clock.mono, clock.wall)
    original_last_off = runtime.states["a"].last_off
    runtime.minimum_rest.observe("a", False, clock.mono, wall)
    assert math.isfinite(runtime.states["a"].last_off)
    assert runtime.states["a"].last_off == original_last_off
    assert not physical(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("checkpoint_first", [False, True])
@pytest.mark.parametrize("identity", ["unique_id", "device_id", "config_entry_id"])
async def test_live_replaced_actuator_gets_its_own_full_rest_even_if_snapshotted_first(
        monkeypatch, checkpoint_first, identity):
    runtime, hass, clock, rows, _saved = off_checkpoint(monkeypatch, elapsed=1900)
    assert remaining(runtime, clock) == 0
    setattr(rows["switch.load"], identity, "fictional_replacement")
    if checkpoint_first:
        assert "a" not in runtime._snapshot()["minimum_rest"]["devices"]
    runtime.mode = "solar"
    reports(hass, clock, grid=-2500)
    await runtime.tick()
    assert remaining(runtime, clock) == 1800
    assert runtime.pending is None and not runtime.states["a"].owned
    assert not physical(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("grid,reason", [
    (500, "Wacht op vermogen / hogere prioriteit"),
    ("unavailable", "Geen betrouwbare energiemeting"),
])
async def test_elapsed_saved_rest_still_requires_current_site_power(monkeypatch, grid, reason):
    _old, _hass, clock, _rows, saved = off_checkpoint(monkeypatch, elapsed=1900)
    saved["mode"] = "solar"
    clock.advance(60)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": 1800})
    runtime.store.data = saved
    reports(hass, clock, grid=grid)
    await runtime.start()
    try:
        assert runtime.mode == "solar"
        assert remaining(runtime, clock) == 0
        assert runtime.result.reasons["a"] == reason
        assert runtime.pending is None and not runtime.states["a"].owned
        assert not physical(hass)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_registry_replacement_after_durable_start_intent_blocks_physical_on(monkeypatch):
    runtime, hass, clock, rows, _saved = off_checkpoint(monkeypatch, elapsed=1900)
    runtime.mode = "solar"
    reports(hass, clock, grid=-2500)
    runtime._observe(clock.mono, runtime._local_now())
    assert remaining(runtime, clock) == 0
    save = runtime.store.async_save
    changed = False

    async def replace_during_journal(data):
        nonlocal changed
        await save(data)
        if not changed and "a" in data.get("leases", {}):
            changed = True
            rows["switch.load"].unique_id = "fictional_replacement_during_save"

    monkeypatch.setattr(runtime.store, "async_save", replace_during_journal)
    await runtime._send(Action("a", 350, "Fictional sufficient solar"), clock.mono)
    assert changed and not physical(hass)
    assert runtime.pending is None and not runtime.states["a"].owned
    assert remaining(runtime, clock) == 1800


def test_read_only_views_leave_empty_checkpoint_snapshot_stable_as_time_passes(monkeypatch):
    clock = install_clock(monkeypatch)
    registry(monkeypatch)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": 1800})
    before = deepcopy(runtime._snapshot())
    assert before["minimum_rest"]["devices"] == {}
    clock.advance(60)
    runtime.overview()
    runtime._device_start_diagnostics(runtime.devices()[0], runtime.states["a"],
        runtime.configs["a"], clock.mono)
    assert runtime._snapshot() == before
    assert not physical(hass)


def test_read_only_views_leave_known_off_checkpoint_snapshot_stable_as_time_passes(monkeypatch):
    runtime, hass, clock, _rows, _saved = off_checkpoint(monkeypatch)
    before = deepcopy(runtime._snapshot())
    assert "a" in before["minimum_rest"]["devices"]
    # Only time passes: there is no new source report, observation or command.
    clock.advance(60)
    runtime.overview()
    runtime._device_start_diagnostics(runtime.devices()[0], runtime.states["a"],
        runtime.configs["a"], clock.mono)
    assert runtime._snapshot() == before
    assert not physical(hass)
