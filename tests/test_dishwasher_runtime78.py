"""APP deadline regressions using HA doubles and fictional appliance data.

These verify controller commands and observed feedback, not an actual AEG cloud
session, Home Assistant Core, or a guarantee of physical operation at a cutoff.
"""
from copy import deepcopy
from dataclasses import replace
import time

import pytest

from custom_components.solar_pilot.const import DEVICE_DEFAULTS
from custom_components.solar_pilot.engine import State
from test_dishwasher_app31 import configured, event, move, ready


def prepare(monkeypatch, **options):
    clock = [10_000.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    runtime, hass, cfg, wall = configured(
        monkeypatch, "2026-09-28T09:59", dishwasher_monday_start_deadline="10:00:00",
        start_delay_s=300, start_margin_w=100, **options)
    runtime.settings.update(max_import_w=4000, pv_entity="sensor.example_pv")
    hass.states.set("sensor.example_pv", 0, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    ready(runtime, hass, cfg, wall)
    return runtime, hass, cfg, wall, clock


def advance(hass, wall, clock, when, seconds=60):
    clock[0] += seconds
    move(hass, wall, when)


def starts(hass):
    return [call for call in hass.services.calls if call[:2] == ("button", "press")]


def notifications(hass, operation):
    return [call for call in hass.services.calls
            if call[:2] == ("persistent_notification", operation)
            and call[2].get("notification_id", "").endswith("_deadline")]


def add_other(runtime, hass, clock, *, on=False, protected=False, watts=900,
              measured=None, min_on_s=0):
    cfg = {**DEVICE_DEFAULTS, "id": "other", "name": "Fictional secondary load",
           "kind": "switch", "control_entity": "switch.example_other",
           "power_entity": "sensor.example_other", "nominal_w": watts,
           "non_interruptible": protected, "min_on_s": min_on_s,
           "min_off_s": 0, "stop_delay_s": 0, "start_delay_s": 0,
           "start_margin_w": 0}
    runtime.configs["other"] = cfg
    runtime.consumer_history.configs["other"] = cfg
    runtime.states["other"] = State(
        owned=on, on=on, target_w=watts if on else 0,
        measured_w=watts if measured is None and on else measured or 0,
        last_on=clock[0], observed_once=True)
    runtime.device_modes["other"] = "auto"
    hass.states.set("switch.example_other", "on" if on else "off")
    hass.states.set("sensor.example_other", runtime.states["other"].measured_w,
                    {"unit_of_measurement": "W"})
    return cfg


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_false", [False, True])
async def test_grid_deadline_is_not_another_solar_wait_or_rebound_request(monkeypatch, legacy_false):
    r, h, c, w, clock = prepare(monkeypatch, dishwasher_deadline_grid_allowed=False)
    if legacy_false:
        r.dishwasher_app.data["a"]["request"]["grid_allowed"] = False
    before = deepcopy(r.dishwasher_app.data["a"]["request"])
    await r.tick()
    assert not starts(h)
    assert not r.dishwasher_app.due(c, w[0])
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    assert len(starts(h)) == 1
    assert r.pending["watts"] == 2000
    assert r.pending["issued_wall"] == before["deadline"]
    assert r.dishwasher_app.data["a"]["request"]["created"] == before["created"]
    assert r.dishwasher_app.data["a"]["request"]["deadline"] == before["deadline"]
    assert r.result.action.reclaimed_w == r.result.action.protected_ev_w == 0
    assert not [call for call in h.services.calls if call[0] in ("number", "switch", "script")]
    assert not notifications(h, "create")


@pytest.mark.asyncio
async def test_deadline_waives_solar_margin_and_stability_only_when_due(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    before = r.overview()[0]["start_diagnostics"]
    assert before["power"]["required_start_w"] == 2100
    assert before["stable_start"]["configured_s"] == 300
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    details = r.overview()[0]["start_diagnostics"]
    assert details["power"]["required_start_w"] == 2000
    assert details["power"]["allocation"]["required_w"] == 2000
    assert details["power"]["allocation"]["grid_allowed"] is True
    assert details["stable_start"]["configured_s"] == 0


@pytest.mark.asyncio
async def test_low_soc_cannot_postpone_authorized_grid_deadline(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    r.settings.update(battery_soc_entity="sensor.example_soc", battery_min_soc=30)
    h.states.set("sensor.example_soc", 12, {"unit_of_measurement": "%"})
    await r.tick()
    assert not starts(h)
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    assert len(starts(h)) == 1
    assert not [call for call in h.services.calls if call[0] in ("number", "switch")]


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["soc_unknown", "soc_wrong_unit", "power_stale", "power_unknown"])
async def test_deadline_does_not_invent_valid_battery_data(monkeypatch, invalid):
    r, h, c, w, clock = prepare(monkeypatch)
    r.settings.update(battery_soc_entity="sensor.example_soc", battery_min_soc=30,
                      battery_power_entity="sensor.example_battery")
    h.states.set("sensor.example_soc", 12, {"unit_of_measurement": "%"})
    h.states.set("sensor.example_battery", 0, {"unit_of_measurement": "W"})
    await r.tick()
    advance(h, w, clock, "2026-09-28T10:01")
    if invalid == "soc_unknown":
        h.states.set("sensor.example_soc", "unknown", {"unit_of_measurement": "%"})
    elif invalid == "soc_wrong_unit":
        h.states.set("sensor.example_soc", 12, {"unit_of_measurement": "W"})
    elif invalid == "power_stale":
        h.states.set("sensor.example_battery", 0, {"unit_of_measurement": "W"}, age=900)
    else:
        h.states.set("sensor.example_battery", "unknown", {"unit_of_measurement": "W"})
    await r.tick()
    assert not starts(h)
    assert not r.overview()[0]["start_requirements"]["reliable_energy_measurement"]["met"]


@pytest.mark.asyncio
async def test_real_import_block_is_specific_and_later_recovers_without_second_release(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    h.states.set("sensor.grid", 3100, {"unit_of_measurement": "W"})
    await r.tick()
    request = deepcopy(r.dishwasher_app.data["a"]["request"])
    advance(h, w, clock, "2026-09-28T10:01")
    await r.tick()
    assert not starts(h)
    reason = r.result.reasons["a"]
    assert "Startdeadline" in reason and "netafnamegrens" in reason
    assert "900" in reason and "2000" in reason
    details = r.overview()[0]
    allocation = details["start_diagnostics"]["power"]["allocation"]
    assert allocation["available_w"] == 900
    assert allocation["required_w"] == 2000
    assert allocation["grid_allowed"] is True
    assert not details["start_requirements"]["allocated_start_power"]["met"]
    assert len(notifications(h, "create")) == 1
    advance(h, w, clock, "2026-09-28T10:20", seconds=120)
    h.states.set("sensor.grid", 400, {"unit_of_measurement": "W"})
    await r.tick()
    assert len(starts(h)) == 1
    assert r.dishwasher_app.data["a"]["request"]["created"] == request["created"]
    assert not notifications(h, "dismiss")
    advance(h, w, clock, "2026-09-28T10:20:03", seconds=3)
    event(r, h, c, w, "dishwasher_state_entity", "Running")
    await r.tick()
    assert not r.pending
    assert len(notifications(h, "dismiss")) == 1
    assert len(starts(h)) == 1
    assert r.dishwasher_app.data["a"]["cycle"]["request_created"] == request["created"]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["global", "device_map", "unknown"])
async def test_phase_headroom_blocks_even_when_house_total_fits(monkeypatch, kind):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    r.phase_settings.update(enabled=True, control_starts=True, limit_w=6000,
                            margin_w=200, start_headroom_w=500,
                            use_learned_device_map=kind == "device_map",
                            phase_1_entity="sensor.example_l1", phase_2_entity="sensor.example_l2",
                            phase_3_entity="sensor.example_l3")
    advance(h, w, clock, "2026-09-28T10:01")
    for eid, watts in (("sensor.example_l1", 4900), ("sensor.example_l2", -4300), ("sensor.example_l3", 0)):
        h.states.set(eid, "unknown" if kind == "unknown" and eid.endswith("l1") else watts,
                     {"unit_of_measurement": "W"})
    await r.tick()
    assert not starts(h)
    assert "fase" in r.result.reasons["a"].lower()
    if kind != "unknown":
        assert "900" in r.result.reasons["a"]
        allocation = r.overview()[0]["start_diagnostics"]["power"]["allocation"]
        assert allocation["available_w"] == 900
        assert not allocation["sufficient"]


@pytest.mark.asyncio
async def test_existing_quarter_budget_still_limits_a_grid_deadline(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    r.capacity_settings.update(enabled=True, average_demand_entity="sensor.example_average",
                               target_peak_w=2400, margin_w=0, minimum_elapsed_s=0,
                               respect_billing_floor=False, adaptive_to_month_peak=False)
    advance(h, w, clock, "2026-09-28T10:06", seconds=420)
    h.states.set("sensor.example_average", 3000, {"unit_of_measurement": "W"})
    await r.tick()
    assert not starts(h)
    assert r.capacity.allowed_grid_w == 2000
    allocation = r.overview()[0]["start_diagnostics"]["power"]["allocation"]
    assert allocation["available_w"] == 1400
    assert not allocation["sufficient"]
    assert allocation["grid_allowed"]


@pytest.mark.asyncio
async def test_unknown_quarter_budget_is_not_reported_as_measured_zero_room(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    r.capacity_settings.update(enabled=True, average_demand_entity="sensor.example_average")
    advance(h, w, clock, "2026-09-28T10:01")
    h.states.set("sensor.example_average", "unknown", {"unit_of_measurement": "W"})
    await r.tick()
    assert not starts(h)
    assert not r.capacity.valid
    assert "kwartier" in r.result.reasons["a"].lower()
    assert any(word in r.result.reasons["a"].lower() for word in ("onbekend", "ontbreekt", "ongeldig"))


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked", ["paused", "disabled", "manual_hold", "door", "offline", "unmapped", "daily_max"])
async def test_deadline_keeps_appliance_authority_and_manual_guards(monkeypatch, blocked):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    advance(h, w, clock, "2026-09-28T10:01")
    if blocked == "paused":
        r.mode = "paused"
    elif blocked == "disabled":
        r.device_modes["a"] = "disabled"
    elif blocked == "manual_hold":
        r.states["a"].manual_until = clock[0] + 3600
    elif blocked == "door":
        h.states.set("binary_sensor.dw_door", "on")
    elif blocked == "offline":
        h.states.set("sensor.dw_connection", "Disconnected")
    elif blocked == "unmapped":
        c["dishwasher_mapping_confirmed"] = False
    else:
        c["max_daily_runtime_s"] = 120
        r.states["a"].daily_runtime_s = 120
    await r.tick()
    assert not starts(h)
    assert not [call for call in h.services.calls if call[0] in ("number", "switch")]


@pytest.mark.asyncio
async def test_deadline_cannot_overlap_an_unconfirmed_other_command(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    add_other(r, h, clock)
    advance(h, w, clock, "2026-09-28T10:00")
    r.pending = {"id": "other", "watts": 900, "issued": clock[0], "issued_wall": w[0],
                 "reason": "Fictional earlier command"}
    await r.tick()
    assert not starts(h)
    assert r.pending["id"] == "other"
    assert not r.overview()[0]["start_requirements"]["general_increase_permission"]["met"]


@pytest.mark.asyncio
async def test_deadline_uses_real_room_without_idle_protected_cycle_reserve(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    add_other(r, h, clock, on=True, protected=True, watts=2400, measured=0)
    advance(h, w, clock, "2026-09-28T10:01")
    await r.tick()
    assert len(starts(h)) == 1
    assert r.states["other"].on and r.states["other"].owned
    assert not [call for call in h.services.calls if call[:2] == ("switch", "turn_off")]
    assert r.overview()[0]["start_diagnostics"]["power"]["allocation"]["available_w"] >= 2000


@pytest.mark.asyncio
async def test_lower_load_reduction_is_confirmed_before_irreversible_start(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    add_other(r, h, clock, on=True, watts=900)
    h.states.set("sensor.grid", 2500, {"unit_of_measurement": "W"})
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    assert not starts(h)
    assert [call for call in h.services.calls if call[:2] == ("switch", "turn_off")]
    assert r.pending["id"] == "other"
    # A switch OFF alone must not create power while P1 still reports the old load.
    advance(h, w, clock, "2026-09-28T10:00:07", seconds=7)
    await r.tick()
    assert not starts(h)
    advance(h, w, clock, "2026-09-28T10:00:14", seconds=7)
    h.states.set("sensor.grid", 1600, {"unit_of_measurement": "W"})
    h.states.set("sensor.example_other", 0, {"unit_of_measurement": "W"})
    await r.tick()
    assert len(starts(h)) == 1


@pytest.mark.asyncio
async def test_minimum_run_of_lower_load_is_not_broken_for_deadline(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    add_other(r, h, clock, on=True, watts=900, min_on_s=600)
    h.states.set("sensor.grid", 2500, {"unit_of_measurement": "W"})
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    assert not starts(h)
    assert not [call for call in h.services.calls if call[:2] == ("switch", "turn_off")]
    assert r.states["other"].on


@pytest.mark.asyncio
async def test_deadline_result_and_diagnostics_replace_ev_preference_without_borrowing(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    original = r.wallbox_guard.update
    def block_ev(*args, **kwargs):
        result = replace(original(*args, **kwargs), block_increase=True, release_flexible=True,
                         max_increase_w=0, reason="Fictional EV solar preference")
        r.wallbox_guard.result = result
        r.wallbox_guard.reclaimable_w = 1500
        return result
    monkeypatch.setattr(r.wallbox_guard, "update", block_ev)
    await r.tick()
    assert not starts(h)
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    assert len(starts(h)) == 1
    assert r.result.action.protected_ev_w == r.result.action.reclaimed_w == 0
    assert "a" in r._start_context["deadline_devices"]
    details = r.overview()[0]
    assert details["start_requirements"]["wallbox_start_block"]["met"]
    assert details["start_requirements"]["general_increase_permission"]["met"]
    assert details["start_requirements"]["allocated_start_power"]["met"]
    assert details["start_diagnostics"]["power"]["allocation"]["grid_allowed"]
    assert details["start_diagnostics"]["power"]["required_start_w"] == 2000
    assert not [call for call in h.services.calls if call[0] in ("switch", "number")]


@pytest.mark.asyncio
async def test_same_tick_selected_start_does_not_create_false_missed_notification(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    advance(h, w, clock, "2026-09-28T10:01")
    await r.tick()
    assert len(starts(h)) == 1
    assert not notifications(h, "create")
    advance(h, w, clock, "2026-09-28T10:01:03", seconds=3)
    await r.tick()
    assert r.pending and len(starts(h)) == 1
    assert not notifications(h, "create")


@pytest.mark.asyncio
async def test_missed_alert_is_once_and_start_command_alone_does_not_resolve_it(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    h.states.set("sensor.grid", 3100, {"unit_of_measurement": "W"})
    await r.tick()
    advance(h, w, clock, "2026-09-28T10:01")
    await r.tick()
    await r.tick()
    assert len(notifications(h, "create")) == 1
    advance(h, w, clock, "2026-09-28T10:02")
    h.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    await r.tick()
    assert len(starts(h)) == 1 and r.pending
    assert not notifications(h, "dismiss")


@pytest.mark.asyncio
@pytest.mark.parametrize("feedback", ["Paused", "unknown", "Unavailable", "Ready To Start"])
async def test_uncertain_start_is_not_success_and_never_retried_blindly(monkeypatch, feedback):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    assert len(starts(h)) == 1
    advance(h, w, clock, "2026-09-28T10:00:03", seconds=3)
    event(r, h, c, w, "dishwasher_state_entity", feedback)
    await r.tick()
    assert r.pending
    assert not notifications(h, "dismiss")
    advance(h, w, clock, "2026-09-28T10:03", seconds=180)
    await r.tick()
    await r.tick()
    assert len(starts(h)) == 1
    assert r.device_retry.command_waiting("a") and "a" not in r.faults
    assert not r.restart_blocking and r.mode == "solar"
    assert r.dishwasher.tickets["a"]["attempted"]
    assert not r.dishwasher.tickets["a"].get("armed")
    assert not notifications(h, "dismiss")
    assert not notifications(h, "create")


@pytest.mark.asyncio
@pytest.mark.parametrize("proof", ["other_request", "unknown_start", "unlinked"])
async def test_unrelated_or_unknown_running_cycle_cannot_dismiss_missed_deadline(monkeypatch, proof):
    r, h, c, w, clock = prepare(monkeypatch)
    info = r.dishwasher_app.data["a"]
    created = info["request"]["created"]
    info["notified_deadline"] = created
    info["cycle"] = {"status": "running", "request_created": created,
                     "started_at": info["request"]["deadline"] + 10,
                     "start_confirmed_at": info["request"]["deadline"] + 10}
    if proof == "other_request":
        info["cycle"]["request_created"] = created - 300
    elif proof == "unknown_start":
        info["cycle"]["started_at"] = None
        info["cycle"]["start_confirmed_at"] = None
    else:
        info["cycle"].pop("request_created")
    advance(h, w, clock, "2026-09-28T10:01")
    await r._update_dishwasher_deadline_notifications()
    assert not notifications(h, "dismiss")
    assert info["notified_deadline"] == created


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [True, "unknown", float("nan"), float("inf"), "future", "before_request"])
async def test_malformed_or_impossible_confirmation_cannot_resolve_a_deadline_warning(monkeypatch, bad):
    r, h, c, w, clock = prepare(monkeypatch)
    info = r.dishwasher_app.data["a"]
    request = info["request"]
    info["notified_deadline"] = request["created"]
    advance(h, w, clock, "2026-09-28T10:01")
    if bad == "future":
        bad = w[0] + 60
    elif bad == "before_request":
        bad = request["created"] - 60
    info["cycle"] = {"status": "running", "request_created": request["created"],
                     "started_at": None, "start_confirmed_at": bad}
    await r._update_dishwasher_deadline_notifications()
    assert not notifications(h, "dismiss")
    assert info["notified_deadline"] == request["created"]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["grid", "door", "cancel", "paused"])
async def test_change_during_intent_save_blocks_native_press_and_rolls_back_known_unsent_start(monkeypatch, change):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    request = deepcopy(r.dishwasher_app.data["a"]["request"])
    previous_last_on = r.states["a"].last_on
    previous_issued = r.last_issued
    previous_ev_action = r.wallbox_guard.last_action
    previous_sg_ev_action = r.sg_wallbox_guard.last_action
    save = r.store.async_save
    triggered = []

    async def changed_while_saving(data):
        await save(data)
        if not triggered and r.pending and r.pending["id"] == "a":
            triggered.append(change)
            if change == "grid":
                h.states.set("sensor.grid", 3100, {"unit_of_measurement": "W"})
            elif change == "door":
                h.states.set("binary_sensor.dw_door", "on")
            elif change == "cancel":
                r.dishwasher_app.cancel(c, "Fictional user cancellation while saving")
                r.dishwasher.cancel("a")
            else:
                r.mode = "paused"

    monkeypatch.setattr(r.store, "async_save", changed_while_saving)
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    assert triggered == [change]
    assert not starts(h)
    assert not r.pending
    assert not r.states["a"].owned and not r.states["a"].on
    assert r.states["a"].target_w == 0
    assert r.states["a"].last_on == previous_last_on
    assert r.last_issued == previous_issued
    assert r.wallbox_guard.last_action == previous_ev_action
    assert r.sg_wallbox_guard.last_action == previous_sg_ev_action
    assert not r.dishwasher.tickets.get("a", {}).get("attempted")
    if change == "cancel":
        assert not r.dishwasher_app.data["a"].get("request")
        assert not r.dishwasher.tickets.get("a", {}).get("armed")
    else:
        assert r.dishwasher_app.data["a"]["request"]["created"] == request["created"]
    assert not r.store.data["leases"].get("a")
    assert not r.store.data["dishwasher"]["tickets"].get("a", {}).get("attempted")
    if change == "grid":
        # Only the explicitly known-unsent intent may be tried on a safe tick.
        advance(h, w, clock, "2026-09-28T10:03", seconds=180)
        h.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
        await r.tick()
        assert len(starts(h)) == 1
        assert r.dishwasher_app.data["a"]["request"]["created"] == request["created"]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["replace_door_binding", "in_place_power"])
async def test_intent_save_cannot_dispatch_from_an_obsolete_device_configuration(monkeypatch, change):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    save = r.store.async_save
    triggered = []

    async def reconfigured_while_saving(data):
        await save(data)
        if not triggered and r.pending and r.pending["id"] == "a":
            triggered.append(change)
            if change == "replace_door_binding":
                h.states.set("binary_sensor.example_rebound_door", "on")
                r.configs["a"] = {**c, "dishwasher_door_entity": "binary_sensor.example_rebound_door"}
            else:
                # The same mutable dictionary can change its power policy too.
                c["nominal_w"] = 2600

    monkeypatch.setattr(r.store, "async_save", reconfigured_while_saving)
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    assert triggered == [change]
    assert not starts(h)
    assert not r.pending
    assert not r.states["a"].owned and r.states["a"].target_w == 0
    assert not r.dishwasher.tickets["a"].get("attempted")
    assert "gewijzigd" in r.result.reasons["a"].lower()
    assert not r.store.data["leases"].get("a")


@pytest.mark.asyncio
async def test_safe_confirmed_phase_is_not_blocked_by_an_unrelated_busy_phase(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    c["phase_hint"] = "l2"
    r.phase_settings.update(enabled=True, control_starts=True, limit_w=6000,
                            margin_w=200, start_headroom_w=500,
                            use_learned_device_map=True,
                            phase_1_entity="sensor.example_l1", phase_2_entity="sensor.example_l2",
                            phase_3_entity="sensor.example_l3")
    advance(h, w, clock, "2026-09-28T10:00")
    for eid, watts in (("sensor.example_l1", 5700), ("sensor.example_l2", 0), ("sensor.example_l3", -5100)):
        h.states.set(eid, watts, {"unit_of_measurement": "W"})
    await r.tick()
    assert r.phase.block_increase and r.phase.headroom_w == 100
    assert r._phase_device_limits()["a"] == 5800
    assert len(starts(h)) == 1
    assert r.result.action.reclaimed_w == r.result.action.protected_ev_w == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["live_program", "request_identity"])
async def test_native_program_or_request_replacement_during_save_cannot_inherit_old_start(monkeypatch, change):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    before = deepcopy(r.dishwasher_app.data["a"]["request"])
    save = r.store.async_save
    triggered = []

    async def changed_while_saving(data):
        await save(data)
        if not triggered and r.pending and r.pending["id"] == "a":
            triggered.append(change)
            if change == "live_program":
                # Final source checks cannot assume the APP callback ran first.
                h.states.set("select.dw_program", "Intensive")
            else:
                r.dishwasher_app.data["a"]["request"] = {
                    **before, "created": before["created"] + 1,
                    "not_before": before["not_before"] + 1}

    monkeypatch.setattr(r.store, "async_save", changed_while_saving)
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    assert triggered == [change]
    assert not starts(h)
    assert not r.pending and not r.states["a"].owned
    assert not r.dishwasher.tickets["a"].get("attempted")
    assert not r.store.data["leases"].get("a")
    if change == "live_program":
        assert "programma" in r.result.reasons["a"].lower()
        assert r.dishwasher_app.data["a"]["request"]["program"] == "Eco"
    else:
        assert r.dishwasher_app.data["a"]["request"]["created"] != before["created"]
        assert not r.dishwasher.tickets["a"].get("armed")


@pytest.mark.asyncio
async def test_protected_load_zero_watt_phase_reserves_no_future_power_at_dispatch(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    add_other(r, h, clock, on=True, protected=True, watts=2400, measured=2400)
    save = r.store.async_save
    triggered = []

    async def loads_changed_while_saving(data):
        await save(data)
        if not triggered and r.pending and r.pending["id"] == "a":
            triggered.append(True)
            # Its heater pauses while another household load rises. Fresh P1
            # still leaves 2800 W; the possible later 2400 W step is not reserved.
            h.states.set("sensor.example_other", 0, {"unit_of_measurement": "W"})
            h.states.set("sensor.grid", 1200, {"unit_of_measurement": "W"})

    monkeypatch.setattr(r.store, "async_save", loads_changed_while_saving)
    advance(h, w, clock, "2026-09-28T10:00")
    await r.tick()
    assert triggered == [True]
    assert len(starts(h)) == 1
    assert r.pending and r.states["a"].owned
    assert r.states["other"].on and r.states["other"].owned
    assert not [call for call in h.services.calls if call[:2] == ("switch", "turn_off")]
    assert r.dishwasher.tickets["a"].get("attempted")
    allocation = r.overview()[0]["start_diagnostics"]["power"]["allocation"]
    assert allocation["available_w"] == 2800
    assert allocation["required_w"] == 2000 and allocation["sufficient"]


@pytest.mark.asyncio
async def test_repeated_last_boundary_blocks_do_not_hide_a_real_unissued_deadline_alert(monkeypatch):
    r, h, c, w, clock = prepare(monkeypatch)
    await r.tick()
    other = add_other(r, h, clock, on=True, protected=True, watts=2400, measured=2400)
    other.pop("power_entity")
    advance(h, w, clock, "2026-09-28T10:01")
    h.states.set("sensor.grid", 2500, {"unit_of_measurement": "W"})
    await r.tick()
    await r.tick()
    await r.tick()
    assert not starts(h)
    assert not r.pending and not r.states["a"].owned
    assert not r.result.action and r.result.targets["a"] == 0
    assert not r.dishwasher.tickets["a"].get("attempted")
    assert r.states["other"].on and r.states["other"].owned
    alerts = notifications(h, "create")
    assert len(alerts) == 1
    assert "1500" in alerts[0][2]["message"]
    assert "2000" in alerts[0][2]["message"]
    assert not notifications(h, "dismiss")
