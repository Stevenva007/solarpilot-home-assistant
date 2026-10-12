"""Frozen APP deadlines and consumed cycle context; fictitious appliance only."""
from copy import deepcopy
from datetime import datetime

import pytest

from custom_components.solar_pilot.dishwasher import read
from custom_components.solar_pilot.dishwasher_app import request_window
from test_dishwasher_app31 import configured, event, ready, stamp, ZONE


def local(value):
    return datetime.fromtimestamp(value, ZONE).isoformat()


@pytest.mark.parametrize("legacy_permission", [True, False])
def test_new_fixed_deadline_is_always_a_grid_fallback(legacy_permission):
    wall = stamp("2026-09-28T09:00")
    window = request_window(wall, {
        "dishwasher_start_deadline": "13:00:00",
        "dishwasher_monday_start_deadline": "10:00:00",
        "dishwasher_deadline_grid_allowed": legacy_permission,
    })
    assert window["deadline"] == stamp("2026-09-28T10:00")
    assert window["grid_allowed"] is True


@pytest.mark.parametrize("locked", [True, False])
@pytest.mark.parametrize("stored_permission", [True, False])
def test_legacy_permission_cannot_change_frozen_deadline(monkeypatch, locked, stored_permission):
    r, h, c, wall = configured(monkeypatch, "2026-09-27T18:00",
        dishwasher_monday_start_deadline="10:00:00", dishwasher_deadline_grid_allowed=False)
    ready(r, h, c, wall)
    request = r.dishwasher_app.data["a"]["request"]
    request.update(grid_allowed=stored_permission, policy_locked=locked)
    before = deepcopy(request)
    r.dishwasher_app.restore(r.dishwasher_app.snapshot())
    c["dishwasher_monday_start_deadline"] = "11:00:00"
    assert not r.dishwasher_app.due(c, stamp("2026-09-28T09:59:59"))
    assert r.dishwasher_app.due(c, stamp("2026-09-28T10:00:00"))
    assert r.dishwasher_app.data["a"]["request"] == before
    assert not h.services.calls
    assert not r.dishwasher.tickets.get("a", {}).get("armed")


def test_due_cannot_create_request_or_bypass_source_expiry_or_mode(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    due = stamp("2026-09-29T13:00")
    assert not r.dishwasher_app.due(c, due)
    ready(r, h, c, wall)
    request = r.dishwasher_app.data["a"]["request"]
    assert r.dishwasher_app.due(c, due)
    assert not r.dishwasher_app.due(c, request["expires"])
    c["dishwasher_arming_mode"] = "manual"
    assert not r.dishwasher_app.due(c, due)
    c["dishwasher_arming_mode"] = "app"
    c["start_button"] = "button.other_example"
    assert not r.dishwasher_app.due(c, due)
    assert not h.services.calls


@pytest.mark.parametrize("invalid", [True, "13:00", float("inf"), float("nan"), None])
def test_malformed_deadline_cannot_grant_grid_fallback(monkeypatch, invalid):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    r.dishwasher_app.data["a"]["request"]["deadline"] = invalid
    assert not r.dishwasher_app.due(c, stamp("2026-09-29T13:00"))
    assert not h.services.calls


@pytest.mark.parametrize("mutation", ["backwards_window", "future_creation", "bool_deadline", "expired"])
def test_invalid_or_expired_request_cannot_arm_a_ticket(monkeypatch, mutation):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    request = r.dishwasher_app.data["a"]["request"]
    if mutation == "backwards_window":
        request["not_before"] = request["deadline"] + 1
    elif mutation == "future_creation":
        request["created"] = request["not_before"] + 1
    elif mutation == "bool_deadline":
        request["deadline"] = True
    else:
        wall[0] = request["expires"]
    r.dishwasher_app.prepare(c, read(h, c), wall[0])
    assert not r.dishwasher.tickets.get("a", {}).get("armed")
    assert not r.dishwasher_app.data["a"].get("request")
    assert not h.services.calls


def test_running_retains_deadline_but_never_retains_start_permission(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    request = deepcopy(r.dishwasher_app.data["a"]["request"])
    wall[0] = stamp("2026-09-29T13:30")
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    info = r.dishwasher_app.overview(c, wall[0])
    assert not info["app_request"]
    assert info["request_context"] and info["request_status"] == "running"
    assert info["start_deadline"] == local(request["deadline"])
    assert info["planned_day"] == request["planned_day"]
    assert info["started_at"] == info["start_confirmed_at"] == local(wall[0])
    assert not r.dishwasher_app.due(c, wall[0])
    assert not r.dishwasher.tickets["a"]["armed"]
    assert not h.services.calls


def test_pending_start_has_same_frozen_context_after_remote_revokes(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    r.dishwasher_app.prepare(c, read(h, c), wall[0])
    request = deepcopy(r.dishwasher_app.data["a"]["request"])
    wall[0] += 3
    r.dishwasher.sent(c, wall[0])
    sent = wall[0]
    event(r, h, c, wall, "dishwasher_remote_entity", "Disabled")
    info = r.dishwasher_app.overview(c, wall[0])
    assert not info["app_request"] and info["request_context"]
    assert info["request_status"] == "start_requested"
    assert info["start_requested_at"] == local(sent)
    assert info["start_deadline"] == local(request["deadline"])
    assert info["start_confirmed_at"] is None
    wall[0] += 2
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    assert r.dishwasher_app.overview(c, wall[0])["request_status"] == "running"
    assert r.dishwasher_app.data["a"]["cycle"]["request_created"] == request["created"]
    assert r.dishwasher.tickets["a"]["attempted"]  # Only runtime may confirm it.


def test_runtime_confirmation_before_polling_keeps_same_revoked_context(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    r.dishwasher_app.prepare(c, read(h, c), wall[0])
    r.dishwasher.sent(c, wall[0])
    event(r, h, c, wall, "dishwasher_remote_entity", "Disabled")
    r.dishwasher.confirmed("a")
    wall[0] += 3
    h.states.set(c["dishwasher_state_entity"], "Running")
    r.dishwasher_app.prepare(c, read(h, c), wall[0])
    info = r.dishwasher_app.overview(c, wall[0])
    assert info["request_context"] and info["request_status"] == "running"
    assert info["started_at"] is None
    assert info["start_requested_at"]


def test_ready_and_paused_do_not_claim_native_start_confirmation(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    event(r, h, c, wall, "dishwasher_state_entity", "Paused")
    info = r.dishwasher_app.overview(c, wall[0])
    assert info["started_at"] is None and info["start_confirmed_at"] is None
    wall[0] += 60
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    info = r.dishwasher_app.overview(c, wall[0])
    assert info["started_at"] is None
    assert info["start_confirmed_at"] == local(wall[0])


def test_first_running_confirmation_is_immutable_on_reports_phases_and_restart(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    wall[0] += 3
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    cycle = deepcopy(r.dishwasher_app.data["a"]["cycle"])
    for state in ("Running", "Main wash", "Paused", "Running"):
        wall[0] += 60
        event(r, h, c, wall, "dishwasher_state_entity", state)
    r.dishwasher_app.restore(r.dishwasher_app.snapshot())
    r.dishwasher_app.seed(c)
    wall[0] += 60
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    current = r.dishwasher_app.data["a"]["cycle"]
    assert current["started_at"] == cycle["started_at"]
    assert current["start_confirmed_at"] == cycle["start_confirmed_at"]
    assert current["observed_at"] == cycle["observed_at"]
    assert current["request"] == cycle["request"]


def test_polling_running_knows_observation_but_does_not_invent_actual_start(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    wall[0] += 300
    h.states.set(c["dishwasher_state_entity"], "Running")
    r.dishwasher_app.prepare(c, read(h, c), wall[0])
    info = r.dishwasher_app.overview(c, wall[0])
    assert info["started_at"] is None
    assert info["start_observed_at"] == info["start_confirmed_at"] == local(wall[0])
    assert info["request_context"]


def test_completed_context_survives_but_independent_next_cycle_cannot_inherit_it(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    r.dishwasher_app.prepare(c, read(h, c), wall[0])
    r.dishwasher.sent(c, wall[0])
    wall[0] += 3
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    r.dishwasher.confirmed("a")
    wall[0] += 7200
    event(r, h, c, wall, "dishwasher_state_entity", "End Of Cycle")
    complete = r.dishwasher_app.overview(c, wall[0])
    assert complete["request_status"] == "completed" and complete["start_deadline"]
    r.dishwasher_app.restore(r.dishwasher_app.snapshot())
    assert r.dishwasher_app.overview(c, wall[0])["request_status"] == "completed"
    wall[0] += 100
    event(r, h, c, wall, "dishwasher_state_entity", "Ready To Start")
    wall[0] += 3
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    new = r.dishwasher_app.overview(c, wall[0])
    assert not new["request_context"] and not new["app_request"]
    assert new["start_deadline"] is None and new["planned_day"] is None
    assert new["start_requested_at"] is None


def test_unconfirmed_old_ticket_cannot_attach_to_next_independent_cycle(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    r.dishwasher_app.prepare(c, read(h, c), wall[0])
    r.dishwasher.sent(c, wall[0])
    wall[0] += 3
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    wall[0] += 7200
    event(r, h, c, wall, "dishwasher_state_entity", "End Of Cycle")
    event(r, h, c, wall, "dishwasher_state_entity", "Ready To Start")
    wall[0] += 3
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    info = r.dishwasher_app.overview(c, wall[0])
    assert r.dishwasher.tickets["a"]["attempted"]  # Ambiguity remains protected.
    assert not info["request_context"] and info["start_deadline"] is None
    assert not h.services.calls


def test_canceled_unsent_request_cannot_be_presented_as_manual_cycle_permission(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    r.dishwasher_app.prepare(c, read(h, c), wall[0])
    r.dishwasher_app.cancel(c)
    wall[0] += 3
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    info = r.dishwasher_app.overview(c, wall[0])
    assert not info["request_context"] and info["request_status"] == "none"
    assert info["start_deadline"] is None
    assert not h.services.calls


def test_new_loading_replaces_cycle_context_without_reusing_previous_confirmation(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    wall[0] += 7200
    event(r, h, c, wall, "dishwasher_state_entity", "End Of Cycle")
    event(r, h, c, wall, "dishwasher_remote_entity", "Disabled")
    event(r, h, c, wall, "dishwasher_state_entity", "Ready To Start")
    wall[0] += 3
    ready(r, h, c, wall)
    info = r.dishwasher_app.overview(c, wall[0])
    assert info["app_request"] and info["request_status"] == "waiting"
    assert info["started_at"] is None and info["start_confirmed_at"] is None
    assert not r.dishwasher.tickets.get("a", {}).get("attempted")
    assert info["completion"]["confirmed"]  # Earlier end remains historical data.


def test_changed_source_hides_retained_context_without_removing_history(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    previous = deepcopy(r.dishwasher_app.data["a"]["last_request"])
    c["start_button"] = "button.other_example"
    info = r.dishwasher_app.overview(c, wall[0])
    assert not info["request_context"] and info["start_deadline"] is None
    assert r.dishwasher_app.data["a"]["last_request"] == previous
    assert not h.services.calls


def legacy_running(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    r.dishwasher_app.prepare(c, read(h, c), wall[0])
    r.dishwasher.sent(c, wall[0])
    wall[0] += 3
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    r.dishwasher.confirmed("a")
    cycle = r.dishwasher_app.data["a"]["cycle"]
    for key in ("context_checked", "request", "request_created", "start_confirmed_at"):
        cycle.pop(key, None)
    r.dishwasher_app.restore(r.dishwasher_app.snapshot())
    return r, h, c, wall


def test_fresh_running_reconciles_proven_beta77_context_without_retro_start_time(monkeypatch):
    r, h, c, wall = legacy_running(monkeypatch)
    original = deepcopy(r.dishwasher_app.data["a"]["cycle"])
    assert r.dishwasher_app.overview(c, wall[0])["start_deadline"] is None
    r.dishwasher_app.seed(c)
    wall[0] += 1800
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    info = r.dishwasher_app.overview(c, wall[0])
    assert info["request_context"] and info["request_status"] == "running"
    assert info["start_deadline"] == local(stamp("2026-09-29T13:00"))
    assert info["started_at"] == local(original["started_at"])
    assert info["start_confirmed_at"] == local(wall[0])
    assert not info["app_request"] and not r.dishwasher.tickets["a"]["armed"]
    assert not h.services.calls


@pytest.mark.parametrize("invalid_proof", ["unrelated_ticket", "new_source", "later_completion", "late_first_report", "new_program"])
def test_legacy_running_cannot_recover_deadline_from_unproved_old_request(monkeypatch, invalid_proof):
    r, h, c, wall = legacy_running(monkeypatch)
    data = r.dishwasher_app.data["a"]
    if invalid_proof == "unrelated_ticket":
        r.dishwasher.tickets["a"]["created"] -= 1
    elif invalid_proof == "new_source":
        c["start_button"] = "button.other_example"
    elif invalid_proof == "later_completion":
        data["completion"] = {"confirmed": True, "ended_at": wall[0], "started_at": None}
    elif invalid_proof == "late_first_report":
        data["cycle"]["observed_at"] += 1800
    else:
        data["cycle"]["program"] = "Other example programme"
    wall[0] += 3600
    event(r, h, c, wall, "dishwasher_state_entity", "Running")
    info = r.dishwasher_app.overview(c, wall[0])
    assert not info["request_context"] and info["start_deadline"] is None
    assert not info["app_request"] and not r.dishwasher.tickets["a"]["armed"]
    assert not h.services.calls
