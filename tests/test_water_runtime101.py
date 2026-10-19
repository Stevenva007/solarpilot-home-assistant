"""Runtime-hook tests: optional water recording cannot become controller work."""
from copy import deepcopy
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest

from custom_components.solar_pilot import runtime as runtime_module
from custom_components.solar_pilot.current_guide import CURRENT_GUIDE, GUIDE_HASH, GUIDE_VERSION, GUIDE_UPDATED
from custom_components.solar_pilot.water import source_reading
from test_runtime import build


BASE = datetime(2026, 10, 19, 10, tzinfo=timezone.utc)
FLOW = "sensor.fictional_water_flow"


def platform_classes():
    """Execute the shipped classes with isolated entity surfaces, as existing sensor tests do."""
    source = Path(__file__).resolve().parents[1]/"custom_components/solar_pilot/sensor.py"
    tree = ast.parse(source.read_text())
    nodes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in ("SolarSensor", "WaterSensor")
             or isinstance(node, ast.FunctionDef) and node.name == "energy_display"
             or isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "COST_SENSORS" for target in node.targets)]

    class Entity:
        def __init__(self, runtime, suffix, name, device_id=None):
            self.runtime, self.suffix, self.key = runtime, suffix, device_id

    class SensorEntity:
        pass

    namespace = dict(SolarEntity=Entity, SensorEntity=SensorEntity, datetime=datetime, timezone=timezone,
        SensorDeviceClass=NS(VOLUME_FLOW_RATE="volume_flow_rate", WATER="water"),
        SensorStateClass=NS(MEASUREMENT="measurement"), CURRENT_GUIDE=CURRENT_GUIDE,
        GUIDE_HASH=GUIDE_HASH, GUIDE_VERSION=GUIDE_VERSION, GUIDE_UPDATED=GUIDE_UPDATED)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["SolarSensor"], namespace["WaterSensor"]


def enabled_recorder(runtime, when=BASE):
    runtime.water.now = lambda: when
    runtime.water.update_config({"enabled": True, "flow_entity": FLOW,
                                 "continuous_flow_minutes": 1, "notifications": False})
    runtime.water.loaded = True
    return runtime.water


def original_flow(when, value=".2"):
    obj = NS(state=value, attributes={"unit_of_measurement": "L/min"},
             last_reported=when, last_updated=when)
    return source_reading(obj, "flow", when.timestamp(), 300)


def seed_partial_candidate(recorder):
    for seconds in (0, 50):
        when = BASE+timedelta(seconds=seconds)
        rows = {role: source_reading(None, role, when.timestamp(), 300, configured=False)
                for role in ("volume", "flow", "native_leak")}
        rows["flow"] = original_flow(when)
        recorder.model.observe(rows, when, binding="a"*64)
    assert recorder.model.overview(BASE+timedelta(seconds=50))["suspicion"]["elapsed_s"] == 50


@pytest.mark.parametrize("state", ["disabled", "unloaded", "closed"])
def test_water_hook_does_not_even_read_context_or_clock_when_recording_is_inactive(monkeypatch, state):
    runtime, hass = build();recorder = enabled_recorder(runtime)
    if state == "disabled":
        recorder.settings["enabled"] = False
    elif state == "unloaded":
        recorder.loaded = False
    else:
        recorder._closed = True

    def forbidden(*args, **kwargs):
        raise AssertionError("Inactive optional recorder must not sample")

    monkeypatch.setattr(runtime_module, "capture_water_context", forbidden)
    recorder.observe = recorder.now = forbidden
    before = recorder.model.snapshot()
    runtime._capture_water_history()
    assert recorder.model.snapshot() == before and not hass.services.calls


def test_water_hook_reuses_exact_heatpump_capture_without_new_panasonic_or_sg_overviews(monkeypatch):
    runtime, hass = build();recorder = enabled_recorder(runtime)
    runtime.heatpump_history.loaded = True
    runtime.heatpump_history.now = lambda: BASE
    snapshot = {"display_tank": {"temperature_c": 52}, "original_sample": object()}
    calls, samples, water = [], [], []
    runtime.panasonic.overview = lambda: calls.append("panasonic") or snapshot
    runtime.sg_boost.overview = lambda: calls.append("sg") or {"configured": False}
    runtime.heatpump_history.observe = lambda *args, **kwargs: samples.append((args, kwargs))
    monkeypatch.setattr(runtime_module, "history_binding", lambda *args: "a"*64)
    monkeypatch.setattr(runtime_module, "configured_history_sources", lambda *_: {"sensor.fictional_heatpump"})

    def capture(owner, sample, *, now):
        assert owner is runtime and sample is snapshot and now == BASE.timestamp()
        return {"boiler": {}}, {"sensor.fictional_tank"}, "b"*64

    monkeypatch.setattr(runtime_module, "capture_water_context", capture)
    recorder.observe = lambda *args, **kwargs: water.append((args, kwargs))
    runtime._capture_heatpump_history();runtime._capture_water_history()
    assert calls == ["panasonic", "sg"] and len(samples) == len(water) == 1
    assert water[0] == ((BASE,), {"context": {"boiler": {}}, "context_sources": {"sensor.fictional_tank"},
                                 "context_binding": "b"*64})
    assert not hass.services.calls


def test_water_hook_does_not_fetch_replacement_native_context_when_no_heatpump_sample_exists(monkeypatch):
    runtime, hass = build();recorder = enabled_recorder(runtime)
    runtime._water_panasonic_sample = None
    calls = []

    def forbidden():
        raise AssertionError("Water must not independently fetch native context")

    runtime.panasonic.overview = runtime.sg_boost.overview = forbidden
    monkeypatch.setattr(runtime_module, "capture_water_context", lambda owner, sample, **kwargs:
                        calls.append(sample) or ({}, set(), None))
    recorder.observe = lambda *args, **kwargs: None
    runtime._capture_water_history()
    assert calls == [None] and not recorder.error and not hass.services.calls


@pytest.mark.parametrize("failure", ["context", "observe", "clock"])
@pytest.mark.asyncio
async def test_optional_water_failure_in_real_tick_keeps_controller_state_and_breaks_candidate(monkeypatch, failure):
    runtime, hass = build();recorder = enabled_recorder(runtime)
    seed_partial_candidate(recorder)
    runtime.mode = "solar";runtime.problem = "existing advisory";runtime.problem_kind = "existing_kind"
    runtime.pause_cause = None
    before = (runtime.mode, runtime.problem, runtime.problem_kind, runtime.pause_cause, deepcopy(runtime.faults))
    runtime._tick = AsyncMock()
    runtime.learning_hub.tick = AsyncMock()
    runtime.analysis.capture = lambda *_: None
    runtime._capture_heatpump_history = lambda: None
    runtime.action_notifications.sync = AsyncMock()
    runtime.compatibility_notifications.sync = AsyncMock()
    runtime.water_notifications.sync = AsyncMock()
    runtime.publish = lambda: None
    when = BASE+timedelta(seconds=55)
    recorder.now = lambda: when

    def broken(*args, **kwargs):
        raise RuntimeError("Fictional optional water failure")

    monkeypatch.setattr(runtime_module, "capture_water_context", broken if failure == "context" else lambda *a, **k: ({}, set(), None))
    if failure == "observe":
        recorder.observe = broken
    elif failure == "clock":
        recorder.now = broken
    await runtime.tick()
    assert (runtime.mode, runtime.problem, runtime.problem_kind, runtime.pause_cause, runtime.faults) == before
    assert recorder.error and not hass.services.calls
    result = recorder.model.overview(when)
    assert result["suspicion"]["state"] == "unknown" and result["suspicion"]["elapsed_s"] == 0
    assert result["flow"]["fresh"] is False
    runtime._tick.assert_awaited_once()


def test_repeated_platform_getters_and_publication_do_not_capture_water_or_consume_sources(monkeypatch):
    runtime, hass = build();recorder = enabled_recorder(runtime)
    before = recorder.model.snapshot()

    def forbidden(*args, **kwargs):
        raise AssertionError("A property read must not capture water evidence")

    recorder.observe = runtime._capture_water_history = forbidden
    old_get = hass.states.get
    hass.states.get = lambda entity: forbidden() if entity == FLOW else old_get(entity)
    SolarSensor, WaterSensor = platform_classes()
    sensors = [WaterSensor(runtime, suffix, suffix) for suffix in ("water_status", "water_flow", "water_today")]
    status = SolarSensor(runtime, "status", "Status")
    for _ in range(5):
        for sensor in sensors:
            assert sensor.available is True
            sensor.native_value
            sensor.extra_state_attributes
        assert status.extra_state_attributes["water"]["read_only"] is True
        runtime.publish()
    assert recorder.model.snapshot() == before and not hass.services.calls


@pytest.mark.asyncio
async def test_tick_clears_previous_heatpump_sample_before_optional_water_context(monkeypatch):
    runtime, hass = build();recorder = enabled_recorder(runtime)
    runtime._water_panasonic_sample = {"temperature_c": 99, "stale_previous_tick": True}
    seen, observed = [], []
    runtime._tick = AsyncMock();runtime.learning_hub.tick = AsyncMock()
    runtime.analysis.capture = lambda *_: None
    runtime._capture_heatpump_history = lambda: None  # The source/history failure produced no new sample.
    runtime.action_notifications.sync = AsyncMock();runtime.compatibility_notifications.sync = AsyncMock()
    runtime.water_notifications.sync = AsyncMock();runtime.publish = lambda: None
    monkeypatch.setattr(runtime_module, "capture_water_context", lambda owner, sample, **kwargs:
                        seen.append(sample) or ({}, set(), None))
    recorder.observe = lambda *args, **kwargs: observed.append(kwargs)
    await runtime.tick()
    assert seen == [None] and observed == [{"context": {}, "context_sources": set(), "context_binding": None}]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_completed_real_controller_tick_samples_water_once_and_closed_tick_never_samples():
    runtime, hass = build();recorder = enabled_recorder(runtime)
    observed = []
    recorder.observe = lambda *args, **kwargs: observed.append((args, kwargs))
    await runtime.tick()
    assert len(observed) == 1 and runtime.mode == "observe" and not hass.services.calls
    await runtime.tick()
    assert len(observed) == 2 and not hass.services.calls
    runtime._closed = True
    await runtime.tick()
    assert len(observed) == 2 and not hass.services.calls
