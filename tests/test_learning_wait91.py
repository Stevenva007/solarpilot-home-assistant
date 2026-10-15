"""Read-only learning waits remain separate from bad sources and missing context."""
from copy import deepcopy
from datetime import datetime, timezone
import time

import pytest

from test_learning_hub30 import metered
from custom_components.solar_pilot.learning_hub import measured_baseline


def _clock(monkeypatch, hass):
    wall = [round(time.time(), 6)]
    monkeypatch.setattr(time, "time", lambda: wall[0])

    def advance(seconds):
        wall[0] += seconds
        # New original meter reports, so elapsed settling is not confused with
        # stale metering at the 120-second boundary.
        for obj in hass.states.data.values():
            obj.last_reported = obj.last_updated = datetime.fromtimestamp(wall[0], timezone.utc)

    return wall, advance


def _observe(runtime, wall, mono):
    return runtime.learning_hub.observe(datetime.fromtimestamp(wall, timezone.utc), mono)


def test_settling_has_exact_start_end_and_no_source_attention(monkeypatch):
    r, h = metered()
    wall, _ = _clock(monkeypatch, h)
    mono = time.monotonic()
    r.states["a"].last_on = mono - 20
    before = deepcopy(r.settings)
    result = _observe(r, wall[0], mono)
    data = r.learning_hub.refresh(force=True)

    assert result["valid"] is False and result["watts"] is None
    status = data["sampling"]["status"]
    assert status["state"] == "transient_wait" and status["severity"] == "info"
    assert status["kind"] == "load_settling"
    assert status["started_at"] == pytest.approx(wall[0] - 20)
    assert status["ends_at"] == pytest.approx(wall[0] + 100)
    assert status["remaining_s"] == 100
    assert status["last_checked_at"] == wall[0]
    assert not any(q["id"] == "source_settling" for q in data["questions"])
    assert not any(q["id"] == "source_settling" for q in r.learning_hub.current_findings)
    assert r.unified_planner.base_load.accepted == 0
    assert r.settings == before and not h.services.calls


def test_wait_boundary_rechecks_source_without_forcing_quarter_hour_attempt(monkeypatch):
    r, h = metered()
    wall, advance = _clock(monkeypatch, h)
    mono = time.monotonic()
    r.states["a"].last_on = mono
    _observe(r, wall[0], mono)
    first_attempt = r.learning_hub.last_attempt
    r.learning_hub.refresh(force=True)

    advance(119)
    assert not _observe(r, wall[0], mono + 119)["valid"]
    assert r.learning_hub.refresh()["sampling"]["status"]["remaining_s"] == 1
    advance(1)
    assert _observe(r, wall[0], mono + 120)["valid"]
    status = r.learning_hub.refresh()["sampling"]["status"]
    assert status["state"] == "ready" and status["ends_at"] is None
    assert status["last_checked_at"] == wall[0]
    assert r.learning_hub.last_attempt == first_attempt
    assert r.unified_planner.base_load.accepted == 0
    assert next(iter(r.learning_hub.days.values())) == {"settling": 1}


def test_elapsed_timer_never_grants_learning_without_new_source_check(monkeypatch):
    r, h = metered()
    wall, advance = _clock(monkeypatch, h)
    mono = time.monotonic()
    r.states["a"].last_on = mono - 119
    _observe(r, wall[0], mono)
    r.learning_hub.refresh(force=True)
    advance(2)
    # Reading a presentation after expiry is not a new measurement.
    data = r.learning_hub.refresh()
    assert data["sampling"]["status"]["state"] == "transient_wait"
    assert data["sampling"]["status"]["remaining_s"] == 0
    assert data["sampling"]["last"]["watts"] is None
    assert r.unified_planner.base_load.accepted == 0


def test_command_feedback_does_not_promise_a_completion_deadline(monkeypatch):
    r, h = metered()
    wall, _ = _clock(monkeypatch, h)
    mono = time.monotonic()
    r.pending = {"issued": mono - 15, "issued_wall": wall[0] - 15}
    _observe(r, wall[0], mono)
    status = r.learning_hub.refresh(force=True)["sampling"]["status"]
    assert status["state"] == "transient_wait" and status["kind"] == "command_feedback"
    assert status["started_at"] == pytest.approx(wall[0] - 15)
    assert status["ends_at"] is None and status["remaining_s"] is None
    assert r.pending and not h.services.calls


def test_missing_meter_during_settling_remains_an_unknown_source(monkeypatch):
    r, h = metered()
    wall, _ = _clock(monkeypatch, h)
    mono = time.monotonic()
    r.states["a"].last_on = mono - 20
    h.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
    _observe(r, wall[0], mono)
    data = r.learning_hub.refresh(force=True)
    assert data["sampling"]["last"]["watts"] is None
    assert data["sampling"]["status"]["state"] == "source_unusable"
    assert any(q["id"] == "source_consumer_source" for q in data["questions"])
    assert not h.services.calls


def test_unknown_heatpump_after_wait_is_separate_and_never_zero_filled(monkeypatch):
    r, h = metered()
    wall, advance = _clock(monkeypatch, h)
    mono = time.monotonic()
    r.states["a"].last_on = mono - 119
    r.panasonic.overview = lambda: {"configured": True, "context": "heatpump_unknown"}
    day = datetime.fromtimestamp(wall[0], timezone.utc).date().isoformat()
    r.learning_hub.days = {day: {"heatpump_heatpump_unknown": 488, "settling": 3}}
    _observe(r, wall[0], mono)
    r.learning_hub.refresh(force=True)

    advance(1)
    result = _observe(r, wall[0], mono + 1)
    data = r.learning_hub.refresh()
    status = data["sampling"]["status"]
    assert result["valid"] is True and result["watts"] == 200
    assert status["state"] == "excluded" and status["scope"] == "heatpump_context"
    assert status["code"] == "heatpump_heatpump_unknown"
    assert status["ends_at"] is None and status["remaining_s"] is None
    assert data["sampling"]["exclusions_7d"]["heatpump_unknown_attempts"] == 488
    assert data["sampling"]["exclusions_7d"]["settling_attempts"] == 4
    assert r.unified_planner.base_load.accepted == 0
    assert not any(q["id"] == "source_settling" for q in data["questions"])
    assert not h.services.calls


def test_most_recent_load_transition_controls_stabilization_end(monkeypatch):
    r, h = metered()
    wall, _ = _clock(monkeypatch, h)
    mono = time.monotonic()
    r.states["a"].last_on = mono - 100
    r.configs["b"] = {**r.configs["a"], "id": "b", "power_entity": "sensor.second"}
    r.states["b"] = deepcopy(r.states["a"])
    r.states["b"].last_on = mono - 10
    h.states.set("sensor.second", 50, {"unit_of_measurement": "W"})
    result = measured_baseline(r, datetime.fromtimestamp(wall[0], timezone.utc), mono)
    assert result["code"] == "settling"
    assert result["settling"]["remaining_s"] == 110
    assert result["settling"]["ends_at"] == pytest.approx(wall[0] + 110)
    assert result["parts"]["owned_w"] == 350
