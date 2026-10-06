"""Recorder payloads stay small while live dashboard details remain available."""
import json
from copy import deepcopy

import pytest

from custom_components.solar_pilot.const import VERSION

from test_electricity_sensor import sensor_class
from test_runtime import build


RECORDER_ATTRIBUTE_LIMIT = 16_384


def sensor(runtime, suffix):
    cls = sensor_class()
    cls.extra_state_attributes.fget.__globals__["GUIDE_VERSION"] = VERSION
    entity = object.__new__(cls)
    entity.runtime, entity.suffix, entity.key = runtime, suffix, None
    return entity


def recorder_payload(entity, attributes):
    return {key: value for key, value in attributes.items()
            if key not in entity._unrecorded_attributes}


def payload_bytes(attributes):
    return len(json.dumps(attributes, ensure_ascii=False).encode("utf-8"))


def test_learning_sensor_retains_live_model_details_without_exceeding_recorder_limit():
    runtime, hass = build()
    entity = sensor(runtime, "learning")

    live = entity.extra_state_attributes
    recorded = recorder_payload(entity, live)

    # The real settings catalogue already exceeds Recorder's limit without a
    # large invented test string or any accumulated household observations.
    assert payload_bytes(live) > RECORDER_ATTRIBUTE_LIMIT
    assert live["thermal_model"]["settings_catalog"]
    assert "pv_model" in live and "phase_learning" in live
    assert payload_bytes(recorded) < RECORDER_ATTRIBUTE_LIMIT
    assert recorded["status"] == live["status"] == entity.native_value
    assert recorded["samples"] == live["samples"]
    assert not hass.services.calls


def test_ems_sensor_retains_live_forecast_and_savings_without_recording_bulk_details():
    runtime, hass = build()
    runtime.pv_forecast.cached = {
        "available": True,
        "horizon": [{"raw_w": 1500, "corrected_w": 1400} for _ in range(192)],
    }
    entity = sensor(runtime, "ems_status")

    live = entity.extra_state_attributes
    recorded = recorder_payload(entity, live)

    assert live["pv_forecast"] == runtime.pv_forecast.cached
    assert live["smart_climate"]["settings_catalog"]
    assert "savings" in live and "electricity_today" in live
    assert "pv_forecast" not in recorded and "savings" not in recorded
    assert payload_bytes(recorded) < RECORDER_ATTRIBUTE_LIMIT
    assert recorded["ready"] == live["ready"]
    assert not hass.services.calls


def test_nine_phase_sensors_reuse_one_ems_calculation_and_all_refresh_before_next_callbacks(monkeypatch):
    runtime, hass = build()
    runtime.phase_learning.accepted = 3
    entities = [sensor(runtime, suffix) for suffix in (
        "phase_status", "phase_headroom", "phase_learning_status",
        "phase_l1_known", "phase_l2_known", "phase_l3_known",
        "phase_l1_residual", "phase_l2_residual", "phase_l3_residual",
    )]
    real_overview = runtime.ems_overview
    calls = []
    inside_callback = False

    def counted_overview():
        calls.append(inside_callback)
        return real_overview()

    monkeypatch.setattr(runtime, "ems_overview", counted_overview)
    for entity in entities:
        entity.native_value
        assert entity.extra_state_attributes["phase_learning"]["accepted_events"] == 3
    assert calls == [False]

    # Publication prepares the next complete frame once, before HA callbacks;
    # none of the nine state writes recomputes the climate/planner models.
    frames = []

    def state_write():
        nonlocal inside_callback
        inside_callback = True
        try:
            frame = []
            for entity in entities:
                value = entity.native_value
                attributes = entity.extra_state_attributes
                frame.append((value, attributes["phase_learning"]["accepted_events"]))
            frames.append(frame)
        finally:
            inside_callback = False

    runtime.subscribe(state_write)
    runtime.phase_learning.accepted = 17
    runtime.publish()

    assert calls == [False, False]
    assert len(frames) == 1 and len(frames[0]) == 9
    assert all(accepted == 17 for _, accepted in frames[0])
    assert frames[0][2][0] == "17 bruikbare fasegebeurtenissen"
    assert not hass.services.calls


def test_global_status_and_learning_sensor_share_learning_snapshot_and_refresh_each_publication(monkeypatch):
    runtime, hass = build()
    status = sensor(runtime, "status")
    learning = sensor(runtime, "learning")
    real_overview = runtime.learning_overview
    calls = []

    def counted_overview():
        calls.append(runtime.learning.successes)
        return real_overview()

    monkeypatch.setattr(runtime, "learning_overview", counted_overview)
    first = status.extra_state_attributes["learning"]
    assert learning.extra_state_attributes is first
    assert learning.native_value == first["status"]
    assert calls == [0]

    observed = []
    runtime.subscribe(lambda: observed.append((status.extra_state_attributes["learning"],
                                              learning.extra_state_attributes, learning.native_value)))
    runtime.learning.successes = 8
    runtime.learning.responses = [40, 45, 50, 55, 60]
    runtime.publish()

    assert calls == [0, 8]
    status_frame, learning_frame, value = observed[0]
    assert status_frame is learning_frame and status_frame is not first
    assert status_frame["successes"] == 8 and status_frame["samples"] == 5
    assert value == status_frame["status"] == "Begrensde aanpassing actief"
    assert not hass.services.calls


def test_direct_ems_read_bypasses_sensor_cache_and_uses_current_model_data():
    runtime, hass = build()
    runtime.phase_learning.accepted = 4
    entity = sensor(runtime, "ems_status")
    cached = entity.extra_state_attributes
    runtime.phase_learning.accepted = 23

    current = runtime.ems_overview()

    assert current is not cached
    assert current["phase_learning"]["accepted_events"] == 23
    assert cached["phase_learning"]["accepted_events"] == 4
    assert entity.extra_state_attributes is cached
    runtime.publish()
    assert entity.extra_state_attributes["phase_learning"]["accepted_events"] == 23
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_recorder_exclusion_and_cached_sensors_preserve_stored_models_and_full_analysis():
    runtime, hass = build(power=True)
    runtime.learning.profiles["a"] = {"fingerprint": "example-profile", "watts": [200, 210, 220]}
    runtime.phase_learning.profiles["a"] = {"observations": [
        {"shares": [1.0, 0.0, 0.0], "device_delta_w": 200, "day": "2026-10-06",
         "source": "passive", "weight": 1.0},
    ]}
    hass.states.set("climate.zone", "off", {
        "current_temperature": 21, "temperature": 21, "temperature_unit": "°C",
        "hvac_action": "off", "hvac_modes": ["off", "auto"],
    })
    runtime.smart_climate.settings["zone_entities"] = ["climate.zone"]
    profile = runtime.smart_climate.state.profile("climate.zone")
    profile.passive_k = [0.015] * 6
    profile.days = {"2026-10-05", "2026-10-06"}
    profile.samples = 12
    configuration = deepcopy((runtime.entry.data, runtime.entry.options))
    before = deepcopy(runtime._snapshot())
    await runtime.store.async_save(before)

    for suffix in ("status", "learning", "phase_status", "ems_status"):
        entity = sensor(runtime, suffix)
        recorder_payload(entity, entity.extra_state_attributes)
        entity.native_value
    runtime.subscribe(lambda: sensor(runtime, "learning").extra_state_attributes)
    runtime.publish()
    report = runtime.analysis.prepare(hours=168)

    assert (runtime.entry.data, runtime.entry.options) == configuration
    assert runtime.store.data == before
    for key in ("learning", "phase_learning", "smart_climate", "pv_forecast", "local_pv"):
        assert runtime._snapshot()[key] == before[key]
        assert report["components"]["runtime_and_models"][key] == before[key]
    exported = report["components"]["energy_planning_climate"]
    assert exported["smart_climate"]["profiles"]["climate.zone"]["samples"] == 12
    assert exported["smart_climate"]["settings_catalog"]
    assert exported["phase_learning"]["devices"]["a"]["samples"] == 1
    assert "pv_forecast" in exported and "savings" in exported
    assert report["coverage"]["section_errors"] == {}
    assert not hass.services.calls
