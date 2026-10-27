"""Preserve original transfer decisions without countdown event spam or rights."""
from copy import deepcopy
import json
from types import SimpleNamespace
import time

import pytest

from custom_components.solar_pilot import analysis_export as ae
from test_analysis_fast107 import context
from test_sg_transfer_integration108 import running, sources, spike


def transfer_events(recorder):
    return [row for row in recorder.events if row["kind"] == "sg_wallbox_transfer"]


def capture_clock(monkeypatch, clock):
    monkeypatch.setattr(ae, "time", SimpleNamespace(time=clock, monotonic=clock))


@pytest.mark.asyncio
async def test_original_window_is_frozen_and_countdown_reads_do_not_create_events_or_authority(monkeypatch):
    runtime, hass, _manager, adapter, clock = await running(monkeypatch)
    capture_clock(monkeypatch, clock)
    runtime.analysis.capture(1)
    assert transfer_events(runtime.analysis) == []  # A ready baseline is no episode.
    clock.advance(5)
    await spike(runtime, hass, clock)
    before = deepcopy(runtime.sg_wallbox_transfer.snapshot())
    calls = list(adapter.calls)
    runtime.analysis.capture(1)
    first = transfer_events(runtime.analysis)[0]
    anchor = first["data"]["transfer"]
    assert anchor["state"] == "active" and anchor["remaining_s"] == 240
    assert anchor["started_at"] == clock() and anchor["expires_at"] == clock()+240
    assert first["data"]["electrical_context"]["sg_wallbox_transfer"] == anchor
    assert first["data"]["electrical_context"]["electrical_sources"]["grid"]["reported_at_wall"] == clock()
    assert runtime.sg_wallbox_transfer.snapshot() == before
    clock.advance(5)
    sources(runtime, hass, clock, grid=4200)
    runtime.analysis.capture(1)
    latest = runtime.analysis.fast[-1]["sg_wallbox_transfer"]
    assert latest["remaining_s"] == 235 and latest["expires_at"] == anchor["expires_at"]
    assert len(transfer_events(runtime.analysis)) == 1
    assert anchor["remaining_s"] == 240  # Earlier evidence is detached, not a live dict.
    assert adapter.calls == calls and not hass.services.calls


@pytest.mark.asyncio
async def test_sg_stop_retains_transfer_deadline_after_later_recovery_clears_current_episode(monkeypatch):
    runtime, hass, manager, _adapter, clock = await running(monkeypatch)
    capture_clock(monkeypatch, clock)
    runtime.analysis.capture(1)
    clock.advance(5)
    await spike(runtime, hass, clock)
    runtime.analysis.capture(1)
    deadline = runtime.sg_wallbox_transfer_overview()["expires_at"]
    for _ in range(4):
        clock.advance(60)
        await spike(runtime, hass, clock)
    assert not manager.owned
    runtime.analysis.capture(1)
    stops = [row for row in runtime.analysis.events if row["kind"] == "heatpump_change"
             and row["data"]["state"]["sg"]["relay_on"] is False]
    context_at_stop = stops[-1]["data"]["electrical_context"]
    saved = deepcopy(context_at_stop)
    assert saved["sg_wallbox_transfer"]["state"] == "exhausted"
    assert saved["sg_wallbox_transfer"]["expires_at"] == deadline
    clock.advance(5)
    await spike(runtime, hass, clock, grid=0, ev=2000)
    clock.advance(15)
    await spike(runtime, hass, clock, grid=0, ev=2000)
    runtime.analysis.capture(1)
    assert runtime.sg_wallbox_transfer_overview()["state"] == "ready"
    assert context_at_stop == saved
    stored = runtime.analysis.snapshot()
    assert "fast" not in stored
    assert any(row["kind"] == "sg_wallbox_transfer" and row["data"]["transfer"]["expires_at"] == deadline
               for row in stored["events"])
    assert not hass.services.calls


def test_new_transfer_event_uses_existing_export_aliases_and_privacy_filters(monkeypatch):
    runtime, hass = context()
    wall = time.time()
    view = {"state": "ready", "active": False, "remaining_s": 0,
            "started_at": None, "expires_at": None, "observed_at": wall}
    monkeypatch.setattr(runtime, "sg_wallbox_transfer_overview", lambda: dict(view))
    hass.states.get("sensor.ev_power").attributes.update(password="PRIVATE_PASSWORD", friendly_name="Private Charger")
    runtime.analysis.capture(1)
    view.update(state="active", active=True, remaining_s=240, started_at=wall, expires_at=wall+240)
    runtime.analysis.capture(1)
    report = runtime.analysis.build()
    raw = json.dumps(report)
    assert "sensor.ev_power" not in raw and "sensor.ev_session" not in raw
    assert "PRIVATE_PASSWORD" not in raw and "Private Charger" not in raw
    event = [row for row in report["telemetry"]["events"] if row["kind"] == "sg_wallbox_transfer"][0]
    alias = report["effective_configuration"]["wallbox"]["power_entity"]
    assert event["data"]["electrical_context"]["wallbox"]["sources"]["power"]["entity_id"] == alias
    assert event["data"]["transfer"]["expires_at"] == wall+240
    assert event["data"]["electrical_context"]["sg_wallbox_transfer"]["started_at"] == wall
    assert report["telemetry"]["fast"][-1]["sg_wallbox_transfer"]["state"] == "active"
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_old_stored_samples_are_not_backfilled_with_invented_transfer_deadlines():
    runtime, hass = context()
    recorder = runtime.analysis
    wall = time.time()
    old = {"ts": wall-300, "release": "1.0.0-beta.107", "grid_w": 0, "pv_w": 2000}
    recorder.store.data = {"schema_version": 1, "started": wall-600,
                           "samples": [old], "changes": [], "events": []}
    await recorder.start()
    try:
        assert recorder.loaded
        recorder.capture(1)
        old_rows = [row for row in recorder.snapshot()["samples"] if row["release"] == "1.0.0-beta.107"]
        assert old_rows == [old] and "sg_wallbox_transfer" not in old_rows[0]
        assert all(row["kind"] != "sg_wallbox_transfer" for row in recorder.events)
        assert not hass.services.calls
    finally:
        await recorder.close(persist=False)


@pytest.mark.parametrize("failure", ["missing", "failed"])
def test_unavailable_optional_overview_stays_unknown_without_affecting_other_evidence(monkeypatch, failure):
    runtime, hass = context()
    before = deepcopy(runtime.sg_wallbox_transfer.snapshot())
    if failure == "missing":
        reader = None
    else:
        def reader():
            raise RuntimeError("PRIVATE_DIAGNOSTIC_ERROR")
    monkeypatch.setattr(runtime, "sg_wallbox_transfer_overview", reader)
    runtime.analysis.capture(1)
    latest = runtime.analysis.fast[-1]
    assert latest["sg_wallbox_transfer"] is None
    assert latest["electrical_sources"]["grid"]["watts"] == 4200
    assert transfer_events(runtime.analysis) == []
    assert runtime.sg_wallbox_transfer.snapshot() == before
    assert "PRIVATE_DIAGNOSTIC_ERROR" not in json.dumps(runtime.analysis.snapshot())
    assert not hass.services.calls
