"""Learning switch shares live details without duplicating them in Recorder."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_runtime import build
from test_sensor_recorder59 import sensor, archived_climate


RECORDER_ATTRIBUTE_LIMIT = 16_384


def switch(runtime, suffix="learning"):
    path = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/switch.py"
    nodes = [node for node in ast.parse(path.read_text()).body
             if isinstance(node, ast.ClassDef) and node.name == "SolarSwitch"]
    namespace = {"SolarEntity": type("SolarEntity", (), {}),
                 "SwitchEntity": type("SwitchEntity", (), {})}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    entity = object.__new__(namespace["SolarSwitch"])
    entity.runtime, entity.suffix, entity.key = runtime, suffix, None
    return entity


def payload_bytes(data):
    return len(json.dumps(data, ensure_ascii=False).encode("utf-8"))


def recorded(entity, live):
    return {key: value for key, value in live.items()
            if key not in entity._unrecorded_attributes}


def test_real_learning_switch_payload_stays_below_recorder_limit_with_all_live_models():
    runtime, hass = build()
    archived = archived_climate(runtime)
    entity = switch(runtime)

    live = entity.extra_state_attributes
    history = recorded(entity, live)

    # Archived observations remain private and lossless; HA receives only a
    # bounded availability summary on every policy-state publication.
    assert payload_bytes(archived) > RECORDER_ATTRIBUTE_LIMIT
    assert payload_bytes(live) < RECORDER_ATTRIBUTE_LIMIT
    assert live["thermal_model"]["archive_available"] is True
    assert live["thermal_model"]["read_only"] is True and "archived" not in live["thermal_model"]
    assert runtime._snapshot()["panasonic_archive"]["backup_store"]["smart_climate"] == archived
    assert runtime.analysis.prepare(hours=168)["components"]["runtime_and_models"]["panasonic_archive"]["backup_store"]["smart_climate"] == archived
    assert "pv_model" in live and "phase_learning" in live and "profiles" in live
    assert payload_bytes(history) < RECORDER_ATTRIBUTE_LIMIT
    assert history["status"] == live["status"]
    assert history["configured_stable_s"] == live["configured_stable_s"]
    assert entity.is_on == runtime.learning.enabled
    assert not hass.services.calls


def test_switch_and_sensors_share_one_model_frame_refreshed_before_each_publication(monkeypatch):
    runtime, hass = build()
    learning_switch = switch(runtime)
    learning_sensor = sensor(runtime, "learning")
    status_sensor = sensor(runtime, "status")
    real_overview = runtime.learning_overview
    calculations = []
    inside_callback = False

    def counted_overview():
        calculations.append(inside_callback)
        return real_overview()

    monkeypatch.setattr(runtime, "learning_overview", counted_overview)
    first = learning_switch.extra_state_attributes
    assert learning_sensor.extra_state_attributes is first
    assert status_sensor.extra_state_attributes["learning"] is first
    assert learning_switch.extra_state_attributes is first
    assert calculations == [False]

    frames = []

    def write_states():
        nonlocal inside_callback
        inside_callback = True
        try:
            frames.append((learning_switch.extra_state_attributes,
                           learning_sensor.extra_state_attributes,
                           status_sensor.extra_state_attributes["learning"]))
        finally:
            inside_callback = False

    runtime.subscribe(write_states)
    runtime.learning.successes = 9
    runtime.learning.responses = [30, 40, 50, 60, 70]
    runtime.publish()

    switch_frame, sensor_frame, status_frame = frames[0]
    assert switch_frame is sensor_frame is status_frame
    assert switch_frame is not first
    assert switch_frame["successes"] == 9 and switch_frame["samples"] == 5
    assert calculations == [False, False]
    assert not hass.services.calls


def test_learning_switch_retains_fallback_for_a_runtime_without_presentation_cache():
    details = {"status": "Leren", "profiles": {"example": {"samples": 7}},
               "thermal_model": {"samples": 12}}
    calls = []
    runtime = SimpleNamespace(data_loaded=True, learning=SimpleNamespace(enabled=True),
                              learning_overview=lambda: calls.append("learning") or details)
    entity = switch(runtime)

    assert entity.extra_state_attributes is details
    assert entity.available and entity.is_on
    assert calls == ["learning"]


@pytest.mark.parametrize("suffix", ["others_first", "auto_resume_after_restart", "sg_boost_enabled"])
def test_other_policy_switches_keep_their_current_attributes_and_avoid_learning_models(suffix, monkeypatch):
    runtime, hass = build()

    def unexpected(*args):
        raise AssertionError("Non-learning switches must not calculate a learning model")

    monkeypatch.setattr(runtime, "sensor_overview", unexpected)
    monkeypatch.setattr(runtime, "learning_overview", unexpected)
    entity = switch(runtime, suffix)

    live = entity.extra_state_attributes

    if suffix == "sg_boost_enabled":
        assert live == runtime.sg_boost.overview()
        assert live["configured"] == runtime.sg_boost.configured
        assert entity.is_on == runtime.sg_boost.auto_enabled
    elif suffix == "others_first":
        assert live["wallbox_read_only"] is True
        assert entity.is_on == runtime.others_first
    else:
        assert live["default"] == "on"
        assert entity.is_on == runtime.auto_resume_after_restart
    assert payload_bytes(recorded(entity, live)) < RECORDER_ATTRIBUTE_LIMIT
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_switch_recorder_filter_preserves_stored_profiles_and_complete_analysis_export():
    runtime, hass = build(power=True)
    runtime.learning.profiles["a"] = {"fingerprint": "example-profile", "watts": [200, 210, 220]}
    runtime.phase_learning.profiles["a"] = {"observations": [
        {"shares": [1.0, 0.0, 0.0], "device_delta_w": 200, "day": "2026-10-06",
         "source": "passive", "weight": 1.0},
    ]}
    archived = archived_climate(runtime)
    before = deepcopy(runtime._snapshot())
    configuration = deepcopy((runtime.entry.data, runtime.entry.options))
    await runtime.store.async_save(before)
    entity = switch(runtime)

    live = entity.extra_state_attributes
    assert "thermal_model" not in recorded(entity, live)
    runtime.subscribe(lambda: entity.extra_state_attributes)
    runtime.publish()
    report = runtime.analysis.prepare(hours=168)

    assert runtime.store.data == before
    assert (runtime.entry.data, runtime.entry.options) == configuration
    for key in ("learning", "phase_learning", "panasonic_archive", "pv_forecast", "local_pv"):
        assert runtime._snapshot()[key] == before[key]
        assert report["components"]["runtime_and_models"][key] == before[key]
    exported = report["components"]["energy_planning_climate"]
    assert report["components"]["runtime_and_models"]["panasonic_archive"]["backup_store"]["smart_climate"] == archived
    assert exported["panasonic"]["read_only"] is True
    assert "smart_climate" not in exported
    assert exported["phase_learning"]["devices"]["a"]["samples"] == 1
    assert report["coverage"]["section_errors"] == {}
    assert not hass.services.calls
