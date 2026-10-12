"""Dispatch race regressions using fictional HA states and services."""
import pytest

from test_runtime import build
from test_dishwasher import setup
from custom_components.solar_pilot.engine import Action
from test_dishwasher_app31 import configured, event, ready, stamp


def writes(h):
    return [call for call in h.services.calls if call[0] != "persistent_notification"]


@pytest.mark.asyncio
async def test_solar_dishwasher_rechecks_door_after_durable_intent(monkeypatch):
    r, h, _cfg = setup()
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    save = r.store.async_save

    async def door_changes(data):
        await save(data)
        if "a" in data.get("leases", {}):
            h.states.set("binary_sensor.dw_door", "on")

    monkeypatch.setattr(r.store, "async_save", door_changes)
    await r.arm_dishwasher("a")
    assert not [call for call in h.services.calls if call[0] == "button"]
    assert r.pending is None
    assert not r.states["a"].owned
    assert not r.dishwasher.tickets["a"]["attempted"]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["switch", "number", "script"])
@pytest.mark.parametrize("change", ["interlock", "demand", "external_start", "power", "config", "mode"])
async def test_ordinary_increase_rechecks_mutated_live_evidence(monkeypatch, kind, change):
    r, h = build(kind=kind, power=True,
        device={"interlock_entity": "input_boolean.interlock", "condition_entity": "input_boolean.condition"})
    h.states.set("input_boolean.interlock", "on")
    h.states.set("input_boolean.condition", "on")
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    original = r.store.async_save
    changed = False

    async def change_after_journal(data):
        nonlocal changed
        await original(data)
        if changed or "a" not in data.get("leases", {}):
            return
        changed = True
        if change in ("interlock", "demand"):
            key = "interlock_entity" if change == "interlock" else "condition_entity"
            h.states.set(r.configs["a"][key], "off")
        elif change == "external_start":
            h.states.set("binary_sensor.running" if kind == "script" else "switch.load", "on")
        elif change == "power":
            h.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
        elif change == "config":
            r.configs["a"]["control_entity"] = "switch.other_example"
            h.states.set("switch.other_example", "off")
        else:
            r.mode = "paused"

    monkeypatch.setattr(r.store, "async_save", change_after_journal)
    await r.tick()
    assert changed
    assert not writes(h)
    assert r.pending is None and not r.states["a"].owned
    assert "a" not in r.store.data["leases"]


@pytest.mark.asyncio
async def test_number_does_not_enable_when_grid_changes_during_setpoint_call():
    r, h = build(kind="number")
    r.mode = "solar"
    r.device_modes["a"] = "auto"

    def changed_after_setpoint(domain, service, data):
        if service == "set_value":
            h.states.set("sensor.grid", 3000, {"unit_of_measurement": "W"})

    h.services.on_call = changed_after_setpoint
    await r.tick()
    assert [call[1] for call in writes(h)] == ["set_value"]
    assert h.states.get("switch.load").state == "off"
    assert r.faults.get("a") and r.states["a"].owned
    assert r.pending is None and "a" in r.store.data["leases"]


@pytest.mark.asyncio
async def test_solar_app_cancellation_during_journal_is_never_rearmed(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    original = r.store.async_save
    changed = False

    async def cancel_during_journal(data):
        nonlocal changed
        await original(data)
        if not changed and "a" in data.get("leases", {}):
            changed = True
            event(r, h, c, wall, "dishwasher_remote_entity", "Disabled")

    monkeypatch.setattr(r.store, "async_save", cancel_during_journal)
    await r.tick()
    assert changed and not writes(h)
    assert not r.dishwasher_app.data["a"].get("request")
    assert not r.dishwasher.tickets["a"].get("armed")
    assert not r.dishwasher.tickets["a"].get("attempted")
    assert not r.states["a"].owned and r.pending is None


@pytest.mark.asyncio
async def test_owned_stop_still_works_without_solar_or_in_observe():
    import time
    r, h = build()
    h.states.set("switch.load", "on")
    h.states.set("sensor.grid", "unavailable", {"unit_of_measurement": "W"})
    r.states["a"].owned = r.states["a"].on = True
    r.states["a"].target_w = 1000
    await r._send(Action("a", 0, "Vrijgeven"), time.monotonic())
    assert [call[1] for call in writes(h)] == ["turn_off"]


@pytest.mark.asyncio
async def test_switch_rechecks_grid_after_durable_intent(monkeypatch):
    r, h = build()
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    save = r.store.async_save

    async def grid_changes(data):
        await save(data)
        if "a" in data.get("leases", {}):
            h.states.set("sensor.grid", 3000, {"unit_of_measurement": "W"})

    monkeypatch.setattr(r.store, "async_save", grid_changes)
    await r.tick()
    assert not [call for call in h.services.calls if call[0] == "switch"]
    assert r.pending is None
    assert not r.states["a"].owned


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["switch", "number", "script"])
@pytest.mark.parametrize("scope", ["observe", "disabled", "closed"])
async def test_direct_increase_never_creates_missing_runtime_permission(kind, scope):
    import time
    r, h = build(kind=kind)
    r.mode = "solar" if scope != "observe" else "observe"
    r.device_modes["a"] = "auto" if scope != "disabled" else "disabled"
    r._closed = scope == "closed"
    await r._send(Action("a", 1380 if kind == "number" else 1000, "Oude planactie"), time.monotonic())
    assert not writes(h)
    assert not r.pending and not r.states["a"].owned


def test_power_unit_conversion_cannot_turn_finite_input_into_infinite_power():
    r, h = build()
    h.states.set("sensor.grid", "1e308", {"unit_of_measurement": "kW"})
    power, _stamp = r._power("sensor.grid")
    assert power is None


@pytest.mark.asyncio
async def test_notification_transport_failure_cannot_abort_controller_work():
    r, h = build()
    h.services.fail = True
    await r.notify("Fictieve wijzigingsmelding")
    assert r.mode == "observe"


@pytest.mark.asyncio
async def test_deadline_start_is_cancelled_when_runtime_closes_during_journal(monkeypatch):
    r, h, c, wall = configured(monkeypatch, "2026-09-29T12:59:00")
    ready(r, h, c, wall)
    wall[0] = stamp("2026-09-29T13:00:00")
    # Fictional fresh heartbeat/P1 at the deadline, no solar requirement.
    h.states.set("sensor.dw_connection", "Connected")
    h.states.set("sensor.grid", 0, {"unit_of_measurement": "W"})
    original = r.store.async_save
    changed = False

    async def close_during_journal(data):
        nonlocal changed
        await original(data)
        if not changed and "a" in data.get("leases", {}):
            changed = r._closed = True

    monkeypatch.setattr(r.store, "async_save", close_during_journal)
    await r.tick()
    assert changed and not writes(h)
    assert r.pending is None and not r.states["a"].owned
    assert not r.dishwasher.tickets["a"].get("attempted")


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["phase", "capacity", "commitment"])
async def test_increase_cannot_spend_capacity_lost_during_journal(monkeypatch, change):
    import time
    from copy import deepcopy
    from custom_components.solar_pilot.engine import State
    r, h = build(power=True)
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    r.states["a"].manual_forced = True
    h.states.set("sensor.grid", 1500, {"unit_of_measurement": "W"})
    if change == "phase":
        r.phase_settings.update(enabled=True, control_starts=True, limit_w=4000, margin_w=0, start_headroom_w=0,
            phase_1_entity="sensor.phase1", phase_2_entity="sensor.phase2", phase_3_entity="sensor.phase3")
        for name in ("sensor.phase1", "sensor.phase2", "sensor.phase3"):
            h.states.set(name, 0, {"unit_of_measurement": "W"})
    elif change == "capacity":
        r.capacity_settings.update(enabled=True, average_demand_entity="sensor.average", monthly_peak_entity="sensor.peak")
        h.states.set("sensor.average", 0, {"unit_of_measurement": "W"})
        h.states.set("sensor.peak", 3500, {"unit_of_measurement": "W"})
    else:
        other = deepcopy(r.configs["a"])
        other.update(id="b", control_entity="switch.other", power_entity="sensor.other", nominal_w=2000)
        r.configs["b"] = other
        r.states["b"] = State(owned=True, on=True, target_w=2000, measured_w=2000)
        h.states.set("switch.other", "on")
        h.states.set("sensor.other", 2000, {"unit_of_measurement": "W"})
    original = r.store.async_save

    async def lose_room(data):
        await original(data)
        if "a" not in data.get("leases", {}):
            return
        if change == "phase":
            h.states.set("sensor.phase1", 3800, {"unit_of_measurement": "W"})
        elif change == "capacity":
            h.states.set("sensor.average", "unavailable", {"unit_of_measurement": "W"})
        else:
            h.states.set("sensor.other", 0, {"unit_of_measurement": "W", "estimated": True})

    monkeypatch.setattr(r.store, "async_save", lose_room)
    await r._send(Action("a", 1000, "Bewuste netstart"), time.monotonic())
    assert not writes(h)
    assert not r.states["a"].owned and r.pending is None


@pytest.mark.asyncio
async def test_deadline_notification_retries_delivery_and_dismiss_without_false_success(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    wall[0] = stamp("2026-09-29T13:01:00")
    info = r.dishwasher_app.data["a"]
    h.services.fail = True
    await r._update_dishwasher_deadline_notifications()
    assert "notified_deadline" not in info and r.mode == "solar"
    h.services.fail = False
    await r._update_dishwasher_deadline_notifications()
    created = info["request"]["created"]
    assert info["notified_deadline"] == created
    info["cycle"] = {"request_created": created, "start_confirmed_at": wall[0]}
    h.services.fail = True
    await r._update_dishwasher_deadline_notifications()
    assert info["notified_deadline"] == created and r.mode == "solar"
    h.services.fail = False
    await r._update_dishwasher_deadline_notifications()
    assert "notified_deadline" not in info


@pytest.mark.asyncio
async def test_notification_task_cancellation_still_propagates(monkeypatch):
    import asyncio
    r, h = build()
    async def cancelled(*args, **kwargs):
        raise asyncio.CancelledError
    monkeypatch.setattr(h.services, "async_call", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await r.notify("Fictieve melding")


@pytest.mark.asyncio
async def test_explicit_current_earlier_deadline_keeps_same_valid_request(monkeypatch):
    from copy import deepcopy
    r, h, c, wall = configured(monkeypatch, "2026-09-29T09:00:00")
    ready(r, h, c, wall)
    original = deepcopy(r.dishwasher_app.data["a"]["request"])
    before = deepcopy(r.entry.options)
    after = deepcopy(before)
    after["devices"][0]["dishwasher_start_deadline"] = "08:00:00"
    await r.live_options.submit(before, after, "current")
    updated = r.dishwasher_app.data["a"]["request"]
    assert r.dishwasher_app._valid_request(r.configs["a"], updated)
    assert updated["created"] == original["created"] and updated["planned_day"] == original["planned_day"]
    assert updated["not_before"] == original["not_before"]
    assert updated["source_signature"] == original["source_signature"]
    assert r.dishwasher_app.due(r.configs["a"], wall[0])
    assert not writes(h)


@pytest.mark.asyncio
async def test_central_ev_permission_revoked_during_journal_cannot_be_used(monkeypatch):
    from test_house_runtime import setup as house_setup, tick as house_tick
    r, h, clock = house_setup(monkeypatch)
    r.entry.options["priority_board"] = {"schema": 2, "order": ["device:a", "wallbox", "dhw_extra"],
        "wallbox_power": {"device:a": True}}
    original = r.store.async_save
    changed = False
    async def revoke_permission(data):
        nonlocal changed
        await original(data)
        if not changed and "a" in data.get("leases", {}):
            changed = True
            r.entry.options["priority_board"]["wallbox_power"]["device:a"] = False
    monkeypatch.setattr(r.store, "async_save", revoke_permission)
    for offset in range(0, 31, 5):
        await house_tick(r, h, clock, offset)
    assert changed and not writes(h)
    assert not r.states["a"].owned and r.pending is None and r.handover is None


def test_current_deadline_changes_are_atomic_when_another_request_is_expired(monkeypatch):
    from copy import deepcopy
    from homeassistant.exceptions import HomeAssistantError
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    original = deepcopy(r.dishwasher_app.data["a"]["request"])
    other = deepcopy(c)
    other["id"] = "b"
    r.dishwasher_app.data["b"] = {"request": {**deepcopy(original), "expires": wall[0]-1}}
    after = {"devices": [{**c, "dishwasher_start_deadline": "11:00:00"}, other]}
    with pytest.raises(HomeAssistantError):
        r.live_options._change_current_requests(r.entry.options, after, ["a", "b"])
    assert r.dishwasher_app.data["a"]["request"] == original
    assert not writes(h)


def test_malformed_optional_dishwasher_profiles_cannot_abort_valid_ticket_restore():
    from custom_components.solar_pilot.dishwasher import DishwasherControl
    control = DishwasherControl()
    control.restore({"tickets": {"a": {"attempted": True, "armed": False}}, "profiles": []})
    assert control.tickets["a"]["attempted"] is True
    assert control.profiles == {}
    assert control.snapshot()["quarantined_profiles"]["unreadable_profiles"] == []
    second = DishwasherControl()
    second.restore(control.snapshot())
    assert second.tickets["a"]["attempted"] is True
    assert second.snapshot()["quarantined_profiles"] == control.snapshot()["quarantined_profiles"]


@pytest.mark.parametrize("opaque", [None, [], {"tickets": []}, {"tickets": {"a": "uncertain"}},
    {"tickets": {"a": {"attempted": "unknown", "armed": True}}, "other_private_field": ["retained"]},
    {"tickets": {"a": {"attempted": True, "sent_at": 10**1000}}}])
def test_unreadable_start_permissions_keep_exact_payload_and_block_all_new_grants(monkeypatch, opaque):
    from copy import deepcopy
    from custom_components.solar_pilot.dishwasher import read
    r, h, c, wall = configured(monkeypatch)
    original = deepcopy(opaque)
    r.dishwasher.restore(opaque)
    assert r.dishwasher.storage_blocked
    ready(r, h, c, wall)
    r.dishwasher_app.prepare(c, read(h, c), wall[0])
    assert not r.dishwasher_app.data["a"].get("request")
    assert not r.dishwasher.permitted(c, read(h, c), wall[0])[0]
    with pytest.raises(ValueError):
        r.dishwasher.arm(c, read(h, c), wall[0])
    r.dishwasher.review("a")
    assert r.dishwasher.storage_blocked
    assert r.dishwasher.snapshot() == original
    assert r._snapshot()["dishwasher"] == original
    assert not writes(h)


@pytest.mark.asyncio
async def test_runtime_start_survives_unreadable_aeg_ticket_map_and_keeps_opaque_data(monkeypatch):
    r, h, c, wall = configured(monkeypatch)
    payload = {"tickets": ["unreadable-original-intent"], "profiles": {"a": []}}
    data = r._snapshot()
    data["dishwasher"] = payload
    r.store.data = data
    await r.start()
    assert r.dishwasher.storage_blocked
    assert r.mode == "solar"
    assert not [call for call in writes(h) if call[0] == "button"]
    assert r.store.data["dishwasher"] == payload
    ready(r, h, c, wall)
    await r.tick()
    assert not r.dishwasher_app.data["a"].get("request")
    await r.close()
    assert r.store.data["dishwasher"] == payload


@pytest.mark.asyncio
async def test_unreadable_aeg_permission_storage_does_not_disable_another_controller(monkeypatch):
    from copy import deepcopy
    from custom_components.solar_pilot.engine import State
    r, h, c, wall = configured(monkeypatch)
    ordinary, _other = build()
    cfg = deepcopy(ordinary.configs["a"])
    cfg.update(id="b", control_entity="switch.other_load")
    r.configs["b"] = cfg
    r.states["b"] = State(last_off=-1e12)
    r.device_modes["b"] = "auto"
    r.consumer_history.configs["b"] = cfg
    h.states.set("switch.other_load", "off")
    payload = {"tickets": ["unreadable-private-intent"], "profiles": {"a": []}}
    r.dishwasher.restore(payload)
    ready(r, h, c, wall)
    await r.tick()
    assert [call[:2] for call in writes(h)] == [("switch", "turn_on")]
    assert r.mode == "solar" and not r.faults
    assert r.dishwasher.snapshot() == payload
    assert not r.dishwasher_app.data["a"].get("request")


def test_valid_permission_restore_ends_quarantine_without_modifying_ticket():
    from copy import deepcopy
    from custom_components.solar_pilot.dishwasher import DishwasherControl
    control = DishwasherControl()
    control.restore({"tickets": []})
    original = {"tickets": {"a": {"attempted": True, "armed": False, "sent_at": 123.0}}, "profiles": {}}
    control.restore(deepcopy(original))
    assert not control.storage_blocked and control.snapshot() == original


@pytest.mark.asyncio
async def test_ordinary_nested_script_cannot_start_aeg_without_its_app_grant():
    from copy import deepcopy
    from types import SimpleNamespace
    from custom_components.solar_pilot.engine import State
    r, h, _cfg = setup()
    ordinary, _other = build(kind="script")
    cfg = deepcopy(ordinary.configs["a"])
    cfg["id"] = "b"
    r.configs["b"] = cfg
    r.consumer_history.configs["b"] = cfg
    r.states["b"] = State(last_off=-1e12)
    r.device_modes["b"] = "auto"
    r.mode = "solar"
    scripts = {
        "script.start": SimpleNamespace(script=SimpleNamespace(sequence=[{"action": "script.nested"}])),
        "script.nested": SimpleNamespace(script=SimpleNamespace(sequence=[
            {"action": "button.press", "target": {"entity_id": "button.dw_start"}}])),
        "script.stop": SimpleNamespace(script=SimpleNamespace(sequence=[
            {"action": "switch.turn_off", "target": {"entity_id": "switch.load"}}])),
    }
    h.data["script"] = SimpleNamespace(get_entity=scripts.get)
    assert not r.dishwasher.tickets.get("a", {}).get("armed")
    await r.tick()
    assert not [call for call in writes(h) if call[0] == "script"]


@pytest.mark.parametrize("timestamp", [10**1000, 1e308, -1e308])
def test_extreme_app_timestamp_is_rejected_without_aborting_restore(monkeypatch, timestamp):
    from copy import deepcopy
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    data = deepcopy(r.dishwasher_app.snapshot())
    data["a"]["request"]["deadline"] = timestamp
    r.dishwasher_app.restore(data)
    assert not r.dishwasher_app.data["a"].get("request")
    assert r.dishwasher_app.data["a"]["quarantined_request"] == data["a"]["request"]
    assert not r.dishwasher_app.due(c, wall[0])
    assert not writes(h)


@pytest.mark.parametrize("timestamp", [1e308, -1e308])
def test_unusable_completion_epoch_is_quarantined_before_runtime_observation(monkeypatch, timestamp):
    from copy import deepcopy
    import time
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    data = deepcopy(r.dishwasher_app.snapshot())
    completion = {"ended_at": timestamp, "state": "End Of Cycle", "confirmed": True}
    data["a"]["end_pending"] = completion
    valid_request = deepcopy(data["a"]["request"])
    r.dishwasher_app.restore(data)
    assert r.dishwasher_app.data["a"]["request"] == valid_request
    r._observe(time.monotonic(), r._local_now())
    restored = r.dishwasher_app.snapshot()["a"]
    assert "end_pending" not in restored
    assert restored["quarantined_end_pending"] == completion
    assert all(restored["request"][key] == value for key, value in valid_request.items())
    assert not writes(h)


@pytest.mark.asyncio
async def test_future_restored_running_report_cannot_confirm_an_actual_start_command(monkeypatch):
    from copy import deepcopy
    r, h, c, wall = configured(monkeypatch)
    ready(r, h, c, wall)
    await r.tick()
    assert r.pending and r.dishwasher.tickets["a"]["attempted"]
    restored = deepcopy(r.dishwasher_app.snapshot())
    restored["a"]["running_report"] = wall[0] + 86400
    r.dishwasher_app.restore(restored)
    await r._confirm_pending(r.pending["issued"] + 1)
    assert r.pending is not None
    assert r.dishwasher.tickets["a"]["attempted"]
    assert [call[:2] for call in writes(h)] == [("button", "press")]


@pytest.mark.asyncio
async def test_unmetered_running_cycle_peak_is_reserved_once_at_ordinary_dispatch():
    from copy import deepcopy
    from custom_components.solar_pilot.engine import State
    r, h, c = setup(nominal_w=1800)
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    h.states.set("sensor.dw_phase", "Running")
    h.states.set("sensor.grid", -3100, {"unit_of_measurement": "W"})
    r.settings["reserve_w"] = 120
    r.states["a"].owned = r.states["a"].on = True
    r.states["a"].target_w = 1800
    ordinary, _other = build(device={"nominal_w": 360, "start_margin_w": 80})
    cfg = deepcopy(ordinary.configs["a"])
    cfg.update(id="b", control_entity="switch.other_load")
    r.configs["b"] = r.consumer_history.configs["b"] = cfg
    r.states["b"] = State(last_off=-1e12)
    r.device_modes["b"] = "auto"
    h.states.set("switch.other_load", "off")
    await r.tick()
    assert r._dishwasher_unmetered_reserve == 1800
    assert r.result.start_power["b"]["available_w"] == 1180
    assert [call[:2] for call in writes(h)] == [("switch", "turn_on")]
    assert r.states["a"].owned and h.states.get("sensor.dw_phase").state == "Running"


@pytest.mark.asyncio
async def test_unavailable_unmetered_cycle_has_one_isolated_peak_reserve():
    from copy import deepcopy
    from custom_components.solar_pilot.engine import State
    r, h, _cfg = setup(nominal_w=1800)
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    h.states.set("sensor.dw_phase", "unavailable")
    h.states.set("sensor.grid", -3100, {"unit_of_measurement": "W"})
    r.settings["reserve_w"] = 120
    r.states["a"].owned = r.states["a"].on = True
    r.states["a"].target_w = 1800
    ordinary, _other = build(device={"nominal_w": 360, "start_margin_w": 80})
    cfg = deepcopy(ordinary.configs["a"])
    cfg.update(id="b", control_entity="switch.other_load")
    r.configs["b"] = r.consumer_history.configs["b"] = cfg
    r.states["b"] = State(last_off=-1e12)
    r.device_modes["b"] = "auto"
    h.states.set("switch.other_load", "off")
    await r.tick()
    assert r.isolated_reserve_w == 1800
    assert r._dishwasher_unmetered_reserve == 0
    allocation = r.result.start_power["b"]
    assert allocation["isolated_reserve_w"] == 1800
    assert allocation["protected_cycle_reserve_w"] == 0
    assert allocation["available_w"] == 1180
    assert [call[:2] for call in writes(h)] == [("switch", "turn_on")]
    assert r.states["a"].owned


def test_final_start_budget_reports_phase_limit_instead_of_missing_solar():
    from custom_components.solar_pilot.engine import Device, Site, State, plan
    d = Device("fictional", nominal_w=360, start_margin_w=80, start_delay_s=0, min_off_s=0)
    result = plan(Site(now=100, grid_w=-2400, filtered_grid_w=-2400,
        reserve_w=120, device_increase_limits={d.id: 200}), [d], {d.id: State()})
    assert result.action is None
    allocation = result.start_power[d.id]
    assert result.free_w == 2280 and allocation["remaining_solar_w"] == 2280
    assert allocation["available_w"] == allocation["electrical_headroom_w"] == 200
    assert allocation["required_w"] == 440 and not allocation["sufficient"]


@pytest.mark.asyncio
async def test_current_phase_start_budget_deducts_running_unmetered_cycle_once():
    from copy import deepcopy
    from custom_components.solar_pilot.engine import State
    r, h, _cfg = setup(nominal_w=1800)
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    r.settings["reserve_w"] = 120
    h.states.set("sensor.dw_phase", "Running")
    h.states.set("sensor.grid", -3100, {"unit_of_measurement": "W"})
    r.states["a"].owned = r.states["a"].on = True
    r.states["a"].target_w = 1800
    ordinary, _other = build(device={"nominal_w": 360, "start_margin_w": 80})
    cfg = deepcopy(ordinary.configs["a"])
    cfg.update(id="b", control_entity="switch.fixture_other")
    r.configs["b"] = r.consumer_history.configs["b"] = cfg
    r.states["b"] = State(last_off=-1e12)
    r.device_modes["b"] = "auto"
    h.states.set("switch.fixture_other", "off")
    r.phase_settings.update(enabled=True, control_starts=True, limit_w=4000,
        margin_w=0, start_headroom_w=0, phase_1_entity="sensor.fixture_p1",
        phase_2_entity="sensor.fixture_p2", phase_3_entity="sensor.fixture_p3")
    for entity, watts in (("sensor.fixture_p1", 2000), ("sensor.fixture_p2", -5100),
                          ("sensor.fixture_p3", 0)):
        h.states.set(entity, watts, {"unit_of_measurement": "W"})
    await r.tick()
    allocation = r.result.start_power["b"]
    assert r._dishwasher_unmetered_reserve == 1800
    assert allocation["available_w"] == allocation["electrical_headroom_w"] == 200
    assert not allocation["sufficient"] and "Fasegrens" in r.result.reasons["b"]
    assert not writes(h)


@pytest.mark.asyncio
@pytest.mark.parametrize("boundary", ["import", "solar"])
async def test_current_start_budget_reports_headroom_lost_during_journal(monkeypatch, boundary):
    r, h = build(device={"nominal_w": 360, "start_margin_w": 80})
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    original = r.store.async_save

    async def lose_headroom(data):
        await original(data)
        if "a" in data.get("leases", {}):
            h.states.set("sensor.grid", 3300 if boundary == "import" else -200,
                         {"unit_of_measurement": "W"})

    monkeypatch.setattr(r.store, "async_save", lose_headroom)
    await r.tick()
    allocation = r.result.start_power["a"]
    assert allocation["available_w"] == 200 and not allocation["sufficient"]
    if boundary == "import":
        assert allocation["electrical_headroom_w"] == 200
    assert not writes(h) and r.pending is None and not r.states["a"].owned


@pytest.mark.asyncio
async def test_current_start_budget_reports_wallbox_headroom_lost_during_journal(monkeypatch):
    from dataclasses import replace
    from test_house_runtime import setup as house_setup, tick as house_tick
    r, h, clock = house_setup(monkeypatch, device={"nominal_w": 360,
        "start_margin_w": 80, "allow_wallbox_reclaim": False})
    original_save = r.store.async_save
    original_update = type(r.wallbox_guard).update
    changed = False

    async def lose_headroom(data):
        nonlocal changed
        await original_save(data)
        if "a" in data.get("leases", {}):
            changed = True

    def current_guard(guard, *args, **kwargs):
        result = original_update(guard, *args, **kwargs)
        return replace(result, max_increase_w=200) if changed else result

    monkeypatch.setattr(r.store, "async_save", lose_headroom)
    monkeypatch.setattr(type(r.wallbox_guard), "update", current_guard)
    for offset in range(0, 31, 5):
        await house_tick(r, h, clock, offset, ev=4000, grid=-2500, status="Charging")
        if changed:
            break
    allocation = r.result.start_power["a"]
    assert changed and allocation["available_w"] == allocation["electrical_headroom_w"] == 200
    assert not allocation["sufficient"] and "Wallbox" in r.result.reasons["a"]
    assert not writes(h) and r.pending is None and not r.states["a"].owned
