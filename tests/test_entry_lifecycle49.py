"""Entry lifecycle against explicit HA doubles, not a Home Assistant Core server."""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot import dishwasher_app
from custom_components.solar_pilot import thermal_runtime
from custom_components.solar_pilot.analysis_export import AnalysisLogHandler
from custom_components.solar_pilot.const import DOMAIN, PLATFORMS
from homeassistant.helpers import event
from test_dishwasher_app31 import configured
from test_runtime import build
from test_thermal_runtime import setup_climate
from test_battery_runtime import setup_battery
from homeassistant.exceptions import HomeAssistantError


ENTRYPOINT = Path(__file__).parents[1] / "custom_components/solar_pilot/__init__.py"


def entry_functions(**overrides):
    """Load the production functions without importing unavailable HA modules."""
    tree = ast.parse(ENTRYPOINT.read_text(encoding="utf-8"))
    nodes = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
    nodes += [node for node in tree.body
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
              and node.name != "_async_setup_entry"]
    namespace = {
        "__name__": "test_entry_lifecycle49",
        "DOMAIN": DOMAIN,
        "PLATFORMS": PLATFORMS,
        "logging": logging,
        "_LOGGER": logging.getLogger("test_entry_lifecycle49"),
        "asyncio": asyncio,
        "async_unregister_frontend": lambda *_args, **_kwargs: None,
    }
    namespace.update(overrides)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 str(ENTRYPOINT), "exec"), namespace)
    return namespace


def install_timer_tracker(monkeypatch):
    active = set()

    def track(_hass, _callback, _interval):
        token = object()
        active.add(token)
        return lambda: active.discard(token)

    monkeypatch.setattr(event, "async_track_time_interval", track)
    return active, track


@pytest.mark.asyncio
async def test_actual_runtime_abort_cleans_all_resources_without_writing_any_of_three_stores(monkeypatch):
    runtime, hass, _, _ = configured(monkeypatch)
    timers, track_timer = install_timer_tracker(monkeypatch)
    states, services = set(), set()

    def track_states(_hass, _ids, _callback):
        token = object()
        states.add(token)
        return lambda: states.discard(token)

    def listen(_event, _callback):
        token = object()
        services.add(token)
        return lambda: services.discard(token)

    monkeypatch.setattr(dishwasher_app, "async_track_state_change_event", track_states)
    monkeypatch.setattr(thermal_runtime, "async_track_state_change_event", track_states)
    hass.bus = SimpleNamespace(async_listen=listen)
    runtime.dishwasher_app.start()
    runtime.smart_climate.settings["zone_entities"] = ["climate.home"]
    runtime.smart_climate.start()
    runtime._remove_timer = track_timer(hass, runtime.tick, None)
    runtime.consumer_history.loaded = runtime.analysis.loaded = True
    runtime.smart_climate.state.profile("climate.home").samples = 633
    runtime.smart_climate.manual_off.add("climate.home")
    runtime.states["a"].owned = runtime.states["a"].on = True
    runtime.consumer_history.model.event("a", runtime.configs["a"], "Existing history", runtime.consumer_history.now())
    runtime.analysis.samples.append({"ts": 633., "values": {"pv_w": 633.}})
    handler = AnalysisLogHandler(runtime.analysis)
    runtime.analysis.log_handler = handler
    logger = logging.getLogger("custom_components.solar_pilot")
    logger.addHandler(handler)
    stores = (runtime.store, runtime.consumer_history.store, runtime.analysis.store)
    snapshots = (runtime._snapshot(), runtime.consumer_history.model.snapshot(), runtime.analysis.snapshot())
    listeners = []
    for store, snapshot in zip(stores, snapshots):
        store.data = deepcopy(snapshot)
        pending = {"delayed": True, "final": True}
        listeners.append(pending)
        store._async_cleanup_delay_listener = lambda current=pending: current.update(delayed=False)
        store._async_cleanup_final_write_listener = lambda current=pending: current.update(final=False)
    saved = tuple(deepcopy(store.data) for store in stores)
    save_counts = tuple(len(store.saves) for store in stores)
    # A setup failure may happen while only part of the saved journal is restored.
    runtime.smart_climate.state.profiles.clear()
    runtime.smart_climate.manual_off.clear()
    runtime.states["a"].owned = False
    runtime.consumer_history.model.devices.clear()
    runtime.analysis.samples.clear()

    try:
        await runtime.close(persist=False)
    finally:
        logger.removeHandler(handler)

    assert tuple(store.data for store in stores) == saved
    assert tuple(len(store.saves) for store in stores) == save_counts
    assert all(current == {"delayed": False, "final": False} for current in listeners)
    assert not timers and not states and not services
    assert runtime.analysis.log_handler is None and handler not in logger.handlers
    assert runtime._closed and runtime._remove_timer is None
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_observe_cannot_abandon_an_owned_climate_coast():
    runtime, hass = setup_climate(control=True, mode="off")
    runtime.mode = "solar"
    runtime.smart_climate.state.expected_mode = {"climate.home": "off"}

    with pytest.raises(HomeAssistantError, match="Pauze"):
        await runtime.set_mode("observe")

    assert runtime.mode == "solar"
    assert runtime.smart_climate.state.expected_mode == {"climate.home": "off"}
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_observe_cannot_abandon_a_known_nonzero_battery_target():
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    runtime.mode = "solar"
    hass.states.set("number.bat_setpoint", -1800, {"unit_of_measurement": "W", "min": -5000, "max": 5000, "step": 50})
    hass.states.set("sensor.bat_power", -1700, {"unit_of_measurement": "W"})
    runtime.battery_fleet.state.expected_numbers = {
        "bat1": {"entity_id": "number.bat_setpoint", "target_w": -1800}}

    with pytest.raises(HomeAssistantError, match="Pauze"):
        await runtime.set_mode("observe")

    assert runtime.mode == "solar"
    assert runtime.battery_fleet.state.expected_numbers["bat1"]["target_w"] == -1800
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_options_waiting_for_dispatch_cannot_reopen_resources_after_close(monkeypatch):
    runtime, hass, _, _ = configured(monkeypatch)
    runtime.entry.runtime_data = runtime
    active_timers, track_timer = install_timer_tracker(monkeypatch)
    active_states = set()
    active_services = set()

    def track_states(_hass, _ids, _callback):
        token = object()
        active_states.add(token)
        return lambda: active_states.discard(token)

    def listen(_event, _callback):
        token = object()
        active_services.add(token)
        return lambda: active_services.discard(token)

    monkeypatch.setattr(dishwasher_app, "async_track_state_change_event", track_states)
    hass.bus = SimpleNamespace(async_listen=listen)
    runtime.dishwasher_app.start()
    runtime.smart_climate.start()
    runtime._remove_timer = track_timer(hass, runtime.tick, None)
    interval = runtime.settings["interval_s"]
    old_remote = runtime.configs["a"]["dishwasher_remote_entity"]
    runtime.entry.options = deepcopy(runtime.entry.options)
    runtime.entry.options["settings"] = {"interval_s": interval + 1}
    runtime.entry.options["devices"][0]["dishwasher_remote_entity"] = "sensor.changed_remote"
    functions = entry_functions()

    await runtime._lock.acquire()
    updating = asyncio.create_task(functions["_options_updated"](hass, runtime.entry))
    await asyncio.sleep(0)
    closing = asyncio.create_task(runtime.close())
    await asyncio.sleep(0)
    try:
        assert runtime._closed and not updating.done() and not closing.done()
        assert not active_timers and not active_states and not active_services
    finally:
        runtime._lock.release()
    await asyncio.gather(updating, closing)

    assert not active_timers and not active_states and not active_services
    assert runtime.settings["interval_s"] == interval
    assert runtime.configs["a"]["dishwasher_remote_entity"] == old_remote
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("platforms_unload", [False, True])
async def test_platform_unload_result_controls_runtime_retry_and_frontend(monkeypatch, platforms_unload):
    runtime, hass = build()
    runtime.entry.runtime_data = runtime
    active, track = install_timer_tracker(monkeypatch)
    runtime._remove_timer = track(hass, runtime.tick, None)
    retry = SimpleNamespace(closed=False)
    retry.close = lambda: setattr(retry, "closed", True)
    runtime.dishwasher_recovery_retry = retry
    frontend_calls = []
    unload_calls = []

    async def unload(entry, platforms):
        unload_calls.append((entry.entry_id, platforms))
        return platforms_unload

    hass.config_entries = SimpleNamespace(async_unload_platforms=unload)
    functions = entry_functions(
        async_unregister_frontend=lambda _hass, **kwargs: frontend_calls.append(kwargs),
    )

    result = await functions["async_unload_entry"](hass, runtime.entry)

    assert result is platforms_unload
    assert len(unload_calls) == 1
    assert runtime._closed is platforms_unload
    assert retry.closed is platforms_unload
    assert bool(frontend_calls) is platforms_unload
    assert bool(active) is not platforms_unload
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("platforms_unload", [False, True])
async def test_dispatch_cannot_start_a_new_lease_while_platform_unload_waits(platforms_unload):
    runtime, hass = build(settings={"settle_s": 0})
    runtime.entry.runtime_data = runtime
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    observed_locks = []

    async def unload(_entry, _platforms):
        observed_locks.append(runtime._lock.locked())
        # A timer fires while Home Assistant is awaiting entity removal.
        await runtime.tick()
        return platforms_unload

    hass.config_entries = SimpleNamespace(async_unload_platforms=unload)
    functions = entry_functions(async_unregister_frontend=lambda *_args, **_kwargs: None)

    result = await functions["async_unload_entry"](hass, runtime.entry)

    assert result is platforms_unload
    assert observed_locks == [True]
    assert not hass.services.calls and not runtime.pending
    assert not runtime.states["a"].owned
    assert hass.states.get("switch.load").state == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", ["_handle_set_climate_setting", "_handle_set_planner_setting"])
async def test_setting_services_reject_unloaded_runtime_without_mutation(handler):
    runtime, hass = build()
    runtime.entry.runtime_data = runtime
    await runtime.close()
    options = deepcopy(runtime.entry.options)
    stored = deepcopy(runtime.store.data)
    saves = len(runtime.store.saves)
    hass.config_entries = SimpleNamespace(async_entries=lambda _domain: [runtime.entry])
    call = SimpleNamespace(data={"config_entry_id": runtime.entry.entry_id,
                                "setting": "enabled", "value": False})

    with pytest.raises(ValueError, match="niet geladen"):
        await entry_functions()[handler](hass, call)

    assert runtime.entry.options == options
    assert runtime.store.data == stored and len(runtime.store.saves) == saves
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("cleanup_fails", [False, True])
@pytest.mark.parametrize("cancelled", [False, True])
async def test_failed_setup_closes_resources_without_overwriting_main_journal(cleanup_fails, cancelled):
    original_error = (asyncio.CancelledError("setup cancelled") if cancelled
                      else RuntimeError("original setup failure"))
    cleanup_error = RuntimeError("cleanup failure")
    journal = {"leases": {"a": {"watts": 633}},
               "smart_climate": {"manual_off": ["climate.living"]}}
    original_journal = deepcopy(journal)
    resources = {"timer": True, "listener": True, "retry": True}
    close_arguments = []
    unload_calls = []
    runtime = SimpleNamespace(_closed=False)
    retry = SimpleNamespace(close=lambda: resources.update(retry=False))
    runtime.dishwasher_recovery_retry = retry

    async def close(*, persist=True):
        close_arguments.append(persist)
        runtime._closed = True
        resources.update(timer=False, listener=False)
        if persist:
            journal.clear()  # A partial runtime snapshot would destroy valid leases.
        if cleanup_fails:
            raise cleanup_error

    runtime.close = close
    entry = SimpleNamespace(entry_id="lifecycle-test", runtime_data=None)

    async def internal_setup(_hass, target):
        target.runtime_data = runtime
        raise original_error

    async def unload(_entry, platforms):
        unload_calls.append(platforms)
        return True

    hass = SimpleNamespace(config_entries=SimpleNamespace(async_unload_platforms=unload))
    functions = entry_functions(_async_setup_entry=internal_setup)

    with pytest.raises(type(original_error)) as caught:
        await functions["async_setup_entry"](hass, entry)

    assert caught.value is original_error
    assert close_arguments == [False]
    assert resources == {"timer": False, "listener": False, "retry": False}
    assert unload_calls == [PLATFORMS]
    assert entry.runtime_data is None
    assert journal == original_journal
