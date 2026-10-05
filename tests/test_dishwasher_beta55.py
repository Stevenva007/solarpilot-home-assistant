"""Fresh APP requests after an unconfirmed previous cycle; fictitious appliance."""
from copy import deepcopy

import pytest

from test_dishwasher_app31 import configured, event, move, ready, stamp


@pytest.mark.asyncio
async def test_new_monday_loading_after_ready_without_end_starts_once_at_ten(monkeypatch):
    r, h, c, wall = configured(monkeypatch, "2026-10-02T09:00",
        dishwasher_monday_start_deadline="10:00:00")
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    move(h, wall, "2026-10-05T08:30")
    event(r, h, c, wall, "dishwasher_state_entity", "Ready To Start")
    h.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    await r.tick()
    assert not r.dishwasher_app.data["a"].get("request")
    assert not h.services.calls
    assert r.dishwasher_app.data["a"]["cycle"]["status"] == "end_unconfirmed"
    assert "Programma loopt" not in r.dishwasher_app.overview(c, wall[0])["app_message"]

    ready(r, h, c, wall)
    request = r.dishwasher_app.data["a"]["request"]
    assert request["created"] == stamp("2026-10-05T08:30")
    assert request["planned_day"] == "2026-10-05"
    assert request["deadline"] == stamp("2026-10-05T10:00")
    await r.tick()
    assert r.dishwasher.tickets["a"]["armed"]
    assert not h.services.calls
    move(h, wall, "2026-10-05T09:59")
    await r.tick()
    assert not h.services.calls
    move(h, wall, "2026-10-05T10:00")
    await r.tick()
    assert len([call for call in h.services.calls if call[0] == "button"]) == 1
    await r.tick()
    assert len([call for call in h.services.calls if call[0] == "button"]) == 1


@pytest.mark.asyncio
async def test_live_ready_resolves_saved_running_only_with_new_app_edge(monkeypatch):
    r, h, c, wall = configured(monkeypatch, "2026-10-05T08:30")
    r.dishwasher_app.data["a"].update(
        cycle={"status": "running", "started_at": stamp("2026-10-02T09:00")},
        message="Programma loopt; APP-aanvraag verbruikt")
    h.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    # The current appliance has returned to Ready; no Ready event was retained.
    ready(r, h, c, wall)
    assert r.dishwasher_app.data["a"].get("request")
    assert r.dishwasher_app.data["a"]["cycle"]["status"] == "waiting"
    await r.tick()
    assert not h.services.calls


@pytest.mark.asyncio
async def test_saved_running_and_already_enabled_ready_never_create_new_request(monkeypatch):
    r, h, c, wall = configured(monkeypatch, "2026-10-05T08:30")
    r.dishwasher_app.restore({"a": {
        "remote": "Enabled", "cycle": {"status": "running"},
        "message": "Programma loopt; APP-aanvraag verbruikt",
    }})
    h.states.set("sensor.dw_remote", "Enabled")
    h.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    await r.tick()
    ready(r, h, c, wall)
    assert r.dishwasher_app.data["a"]["cycle"]["status"] == "end_unconfirmed"
    assert not r.dishwasher_app.data["a"].get("request")
    assert not r.dishwasher_app.data["a"].get("completion")
    assert not h.services.calls


@pytest.mark.asyncio
async def test_old_running_with_stale_connection_cannot_use_ready_to_accept_app(monkeypatch):
    r, h, c, wall = configured(monkeypatch, "2026-10-05T08:30")
    r.dishwasher_app.data["a"]["cycle"] = {"status": "running"}
    h.states.set("sensor.dw_connection", "Connected", reported_age=301)
    ready(r, h, c, wall)
    assert r.dishwasher_app.data["a"]["cycle"]["status"] == "running"
    assert not r.dishwasher_app.data["a"].get("request")
    await r.tick()
    assert not h.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", ["Running", "Paused", "Ado Drying", "unknown"])
async def test_old_running_cannot_be_rearmed_without_live_ready(monkeypatch, raw):
    r, h, c, wall = configured(monkeypatch, "2026-10-05T08:30")
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    h.states.set("sensor.dw_phase", raw)
    ready(r, h, c, wall)
    assert not r.dishwasher_app.data["a"].get("request")
    await r.tick()
    assert not h.services.calls


@pytest.mark.asyncio
async def test_ready_after_sent_start_keeps_attempt_lock_and_no_second_command(monkeypatch):
    r, h, c, wall = configured(monkeypatch, "2026-10-05T08:30")
    ready(r, h, c, wall)
    await r.tick()
    assert r.dishwasher.tickets["a"]["attempted"]
    event(r, h, c, wall, "dishwasher_state_entity", "Paused")
    event(r, h, c, wall, "dishwasher_state_entity", "Ready To Start")
    event(r, h, c, wall, "dishwasher_remote_entity", "Not Safety Relevant Enabled")
    ready(r, h, c, wall)
    await r.tick()
    assert not r.dishwasher_app.data["a"].get("request")
    assert r.dishwasher.tickets["a"]["attempted"]
    assert len([call for call in h.services.calls if call[0] == "button"]) == 1


@pytest.mark.asyncio
async def test_ready_refresh_does_not_restore_genuine_cancelled_request(monkeypatch):
    r, h, c, wall = configured(monkeypatch, "2026-10-05T08:30")
    ready(r, h, c, wall)
    h.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    await r.tick()
    event(r, h, c, wall, "dishwasher_door_entity", "on")
    cancelled = deepcopy(r.dishwasher_app.data["a"]["last_request"])
    event(r, h, c, wall, "dishwasher_door_entity", "off")
    event(r, h, c, wall, "dishwasher_state_entity", "Ready To Start")
    ready(r, h, c, wall)  # Repeated Enabled is a report, not a fresh edge.
    await r.tick()
    assert not r.dishwasher_app.data["a"].get("request")
    assert r.dishwasher_app.data["a"]["last_request"] == cancelled
    assert not h.services.calls
