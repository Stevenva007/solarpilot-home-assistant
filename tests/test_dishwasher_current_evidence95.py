"""Current appliance proof is separate from a retained historical completion."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import time

import pytest

from test_dishwasher import setup
from test_dishwasher_app31 import configured, event, ready
from test_runtime import build
from custom_components.solar_pilot.analysis_export import consumer_evidence
from custom_components.solar_pilot.dishwasher import Reading, read


@pytest.mark.parametrize("connection", ["disconnected", "stale", "restored", "missing"])
def test_old_completed_off_never_replaces_unknown_current_read(monkeypatch, connection):
    r, h, cfg, wall = configured(monkeypatch)
    event(r, h, cfg, wall, "dishwasher_state_entity", "Running")
    wall[0] += 100
    event(r, h, cfg, wall, "dishwasher_state_entity", "End Of Cycle")
    ended = wall[0]
    wall[0] += 4
    event(r, h, cfg, wall, "dishwasher_state_entity", "Off")
    # Consume the original event first; the following checks concern an old
    # completion, rather than the one-shot historical end processing.
    r._observe(time.monotonic(), datetime.fromtimestamp(wall[0], timezone.utc))
    completion = deepcopy(r.dishwasher_app.data["a"]["completion"])
    if connection == "missing":
        h.states.data.pop("sensor.dw_connection")
    elif connection == "stale":
        h.states.set("sensor.dw_connection", "Connected", reported_age=3600)
    elif connection == "restored":
        h.states.set("sensor.dw_connection", "Connected", {"restored": True})
    else:
        h.states.set("sensor.dw_connection", "Disconnected")
    current = read(h, cfg, wall[0])
    assert current.active is None
    projected = r.dishwasher_app.overlay(cfg, current)
    assert projected.active is None and projected.stamp == 0
    r._observe(time.monotonic(), datetime.fromtimestamp(wall[0], timezone.utc))
    assert r.states["a"].available is False
    proof = consumer_evidence(r, "a", wall=wall[0])["observed"]["control"]
    assert proof["on"] is None and proof["valid"] is False
    # Off's original report remains available as source metadata; it is not a
    # newly confirmed OFF, an epoch-zero date or a refreshed observation.
    assert proof["reported_at_wall"] == wall[0]
    assert r.dishwasher_app.data["a"]["completion"] == completion
    assert completion["ended_at"] == ended
    assert not h.services.calls


@pytest.mark.asyncio
async def test_original_end_processed_once_then_restart_offline_and_reconnect_never_replay_start(monkeypatch):
    r, h, cfg, wall = configured(monkeypatch)
    ready(r, h, cfg, wall)
    await r.tick()
    wall[0] += 3
    event(r, h, cfg, wall, "dishwasher_state_entity", "Running")
    await r.tick()
    assert r.states["a"].on and r.states["a"].owned
    assert len([call for call in h.services.calls if call[0] == "button"]) == 1
    seen = []
    original_observe = r.consumer_history.observe

    def observe(device_id, active, local_now):
        seen.append((device_id, active, local_now.timestamp()))
        return original_observe(device_id, active, local_now)

    r.consumer_history.observe = observe
    wall[0] += 200
    ended = wall[0]
    event(r, h, cfg, wall, "dishwasher_state_entity", "End Of Cycle")
    wall[0] += 4
    event(r, h, cfg, wall, "dishwasher_state_entity", "Off")
    h.states.set("sensor.dw_connection", "Disconnected")
    # Before the first regular tick, retained event evidence must already be
    # excluded from the separate current physical-source export.
    r.dishwasher.readings["a"] = r.dishwasher_app.overlay(cfg, read(h, cfg, wall[0]))
    current = consumer_evidence(r, "a", wall=wall[0])["observed"]["control"]
    assert current["valid"] is False and current["on"] is None
    await r.tick()
    assert seen.count(("a", False, ended)) == 1
    assert not r.states["a"].on and not r.states["a"].owned
    assert "end_pending" not in r.dishwasher_app.data["a"]
    completion = deepcopy(r.dishwasher_app.data["a"]["completion"])
    await r.tick()
    assert r.states["a"].available is False
    assert seen.count(("a", False, ended)) == 1
    assert r.dishwasher_app.data["a"]["completion"] == completion
    assert len([call for call in h.services.calls if call[0] == "button"]) == 1
    saved = deepcopy(r._snapshot())

    r2, h2, cfg2, wall2 = configured(monkeypatch, when="2026-09-29T11:00")
    h2.states.set("sensor.dw_phase", "Off")
    h2.states.set("sensor.dw_connection", "Disconnected")
    r2.store.data = saved
    await r2.start()
    assert r2.states["a"].available is False
    assert r2.dishwasher_app.data["a"]["completion"] == completion
    assert not r2.dishwasher_app.data["a"].get("request")
    current = consumer_evidence(r2, "a", wall=wall2[0])["observed"]["control"]
    assert not current["valid"] and current["on"] is None
    h2.states.set("sensor.dw_connection", "Connected")
    await r2.tick()
    assert r2.states["a"].available is True and r2.states["a"].on is False
    current = consumer_evidence(r2, "a", wall=wall2[0])["observed"]["control"]
    assert current["valid"] is True and current["on"] is False
    assert current["reported_at_wall"] == wall2[0]
    assert r2.dishwasher_app.data["a"]["completion"] == completion
    assert r2.dishwasher_app.overview(cfg2, wall2[0])["cycle_status"] == "completed"
    assert not [call for call in h2.services.calls if call[0] == "button"]
    await r2.close()


def test_current_export_reads_actual_source_instead_of_saved_event_overlay():
    r, h, cfg = setup()
    h.states.set("sensor.dw_phase", "Running")
    stamp = h.states.get("sensor.dw_phase").last_reported.timestamp()
    historical = Reading(active=False, finished=True, raw="End Of Cycle", stamp=stamp-500)
    r.dishwasher.readings["a"] = historical
    proof = consumer_evidence(r, "a")["observed"]["control"]
    assert proof["valid"] is True and proof["on"] is True
    assert proof["reported_at_wall"] == stamp
    assert r.dishwasher.readings["a"] is historical
    assert not h.services.calls


INVALID_REPORTS = [None, False, True, 0, -1, "123", float("nan"), float("inf"),
                   -float("inf"), 1e100, 10**1000, 1+1j, [], {}]


@pytest.mark.parametrize("reported", INVALID_REPORTS)
@pytest.mark.parametrize("source", ["control", "power"])
def test_invalid_original_report_times_remain_unknown(reported, source):
    r, h = build(power=True)
    h.states.set("switch.load", "on")
    wall = time.time()
    r._reported_wall = lambda obj: reported if source == "control" else wall
    r._power = lambda entity_id: (280, reported if source == "power" else wall)
    proof = consumer_evidence(r, "a", wall=wall)["observed"][source]
    assert proof["valid"] is False
    assert proof["on" if source == "control" else "watts"] is None
    assert proof["reported_at_wall"] is None and proof["report_age_s"] is None
    assert not h.services.calls


@pytest.mark.parametrize("source", ["control", "power"])
def test_future_original_report_does_not_become_physical_evidence(source):
    r, h = build(power=True)
    h.states.set("switch.load", "on")
    wall = time.time()
    r._reported_wall = lambda obj: wall+6 if source == "control" else wall
    r._power = lambda entity_id: (280, wall+6 if source == "power" else wall)
    proof = consumer_evidence(r, "a", wall=wall)["observed"][source]
    assert proof["valid"] is False and proof["reported_at_wall"] is None


@pytest.mark.parametrize("reported", INVALID_REPORTS)
def test_dishwasher_original_state_time_is_not_replaced_with_a_fallback_now(reported):
    r, h, cfg = setup()
    h.states.set("sensor.dw_phase", "Off")
    h.states.get("sensor.dw_phase").last_reported = SimpleNamespace(timestamp=lambda: reported)
    r.dishwasher.readings["a"] = Reading(active=False, finished=True, stamp=time.time())
    proof = consumer_evidence(r, "a")["observed"]["control"]
    assert proof["valid"] is False and proof["on"] is None
    assert proof["reported_at_wall"] is None and proof["report_age_s"] is None
    assert not h.services.calls


def test_unchanged_appliance_state_retains_original_time_under_current_heartbeat():
    r, h, cfg = setup()
    h.states.set("sensor.dw_phase", "Off", reported_age=3600)
    original = h.states.get("sensor.dw_phase").last_reported.timestamp()
    proof = consumer_evidence(r, "a")["observed"]["control"]
    assert proof["valid"] is True and proof["on"] is False
    assert proof["reported_at_wall"] == original and proof["report_age_s"] >= 3600
    assert not h.services.calls
