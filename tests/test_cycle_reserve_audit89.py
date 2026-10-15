"""Independent future-cycle reservation audit with fictional meters and loads."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import time

import pytest

from custom_components.solar_pilot.engine import Action, Device, Site, State, plan
from custom_components.solar_pilot.runtime import SolarRuntime
from test_runtime import build
from test_dishwasher import setup as dishwasher_setup


def solar_site(**changes):
    # Fictional 900 W P1 export and 150 W reserve leave 750 W current solar.
    return Site(now=1000, grid_w=-900, filtered_grid_w=-900,
                reserve_w=150, max_import_w=3500,
                comfort_reserve_w=2000, protected_cycle_reserve_w=2000,
                cycle_solar_relief_w=2000, **changes)


def small_load(device_id="small", **changes):
    return Device(device_id, nominal_w=300, start_margin_w=100,
                  start_delay_s=0, min_on_s=0, min_off_s=0, **changes)


def runtime_with_running_cycle(*, kind="switch", meter=False, delay=0):
    old, hass = build(kind=kind, power=True,
        settings={"reserve_w": 150, "max_import_w": 3500},
        device={"nominal_w": 300, "start_margin_w": 100,
                "start_delay_s": delay, "min_units": 1, "max_units": 10,
                "watts_per_unit": 100, "control_unit": "A"})
    _, dishwasher_hass, cfg = dishwasher_setup()
    cfg = {**cfg, "id": "fictional_cycle", "name": "Fictional protected cycle"}
    if meter:
        cfg["power_entity"] = "sensor.fictional_cycle_w"
        hass.states.set(cfg["power_entity"], 0, {"unit_of_measurement": "W"})
    old.entry.options["devices"].append(cfg)
    for eid, obj in dishwasher_hass.states.data.items():
        if eid.startswith(("sensor.dw_", "binary_sensor.dw_", "button.dw_", "select.dw_")):
            hass.states.set(eid, obj.state, obj.attributes)
    hass.states.set("sensor.dw_phase", "Washing")
    hass.states.set("sensor.grid", -900, {"unit_of_measurement": "W"})
    if kind == "number":
        hass.states.set("number.amps", 1, {"min": 1, "max": 10, "step": 1,
                                           "unit_of_measurement": "A"})
    runtime = SolarRuntime(hass, old.entry)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    return runtime, hass


def writes(hass):
    return [row for row in hass.services.calls if row[0] != "persistent_notification"]


def test_fictional_export_budget_can_start_only_the_ordinary_flexible_load():
    device = small_load()
    states = {device.id: State()}
    result = plan(solar_site(), [device], states)
    assert result.action and result.action.id == device.id and result.action.watts == 300
    assert result.action.reclaimed_w == result.action.protected_ev_w == 0
    diagnostic = result.start_power[device.id]
    assert diagnostic["required_w"] == 400
    assert diagnostic["available_w"] == 750
    assert diagnostic["protected_cycle_reserve_w"] == 2000
    assert diagnostic["solar_cycle_reserve_relief_w"] == 2000
    assert diagnostic["solar_cycle_reserve_w"] == 0
    assert diagnostic["electrical_headroom_w"] == 2400


def test_only_one_shared_solar_pool_is_available_to_two_flexible_loads():
    devices = [Device(key, nominal_w=400, start_margin_w=10,
                      start_delay_s=0, min_on_s=0, min_off_s=0)
               for key in ("first", "second")]
    states = {device.id: State() for device in devices}
    result = plan(solar_site(), devices, states)
    assert result.targets == {"first": 400, "second": 0}
    assert result.action and result.action.id == "first"
    assert result.start_power["second"]["available_w"] == 350
    assert result.start_power["second"]["sufficient"] is False
    assert states["second"].start_since is None


def test_strict_cycle_between_flexible_loads_cannot_spend_the_soft_exception():
    devices = [replace(small_load("first"), nominal_w=250, start_margin_w=10, priority=10),
               replace(small_load("protected"), nominal_w=200, start_margin_w=10,
                       priority=20, non_interruptible=True),
               replace(small_load("last"), nominal_w=250, start_margin_w=10, priority=30)]
    result = plan(solar_site(), devices, {device.id: State() for device in devices})
    assert result.targets == {"first": 250, "protected": 0, "last": 250}
    assert result.start_power["protected"]["solar_cycle_reserve_relief_w"] == 0
    assert result.start_power["protected"]["solar_cycle_reserve_w"] == 2000


@pytest.mark.parametrize("kind,protected", [("switch", True), ("number", True),
                                            ("dishwasher", False)])
def test_new_protected_cycle_never_uses_optional_solar_headroom(kind, protected):
    device = replace(small_load(), kind=kind, non_interruptible=protected,
                     min_units=1, max_units=2, watts_per_unit=100)
    result = plan(solar_site(), [device], {device.id: State()})
    assert result.targets[device.id] == 0 and result.action is None
    assert result.start_power[device.id]["solar_cycle_reserve_relief_w"] == 0


@pytest.mark.parametrize("changed", [
    {"comfort_reserve_w": 2600, "isolated_reserve_w": 600},
    {"comfort_reserve_w": 2600, "sg_unconfirmed_reserve_w": 600},
    {"comfort_reserve_w": 2600},
])
def test_isolation_sg_and_other_commitments_are_never_relabelled_as_cycle_credit(changed):
    device = small_load()
    result = plan(replace(solar_site(), **changed), [device], {device.id: State()})
    assert result.action is None and result.targets[device.id] == 0
    diagnostic = result.start_power[device.id]
    assert diagnostic["solar_cycle_reserve_relief_w"] == 2000
    assert diagnostic["available_w"] == 150


@pytest.mark.parametrize("limit", [0, 299])
def test_actual_hard_import_room_is_never_freed_by_solar_relief(limit):
    device = small_load()
    # Raw P1 export itself adds 900 W room; subtract that when selecting the cap.
    site = replace(solar_site(), max_import_w=2000 + limit - 900)
    result = plan(site, [device], {device.id: State()})
    assert result.action is None and result.targets[device.id] == 0
    assert result.start_power[device.id]["electrical_headroom_w"] == limit


@pytest.mark.parametrize("limits", [{"max_increase_w": 299},
                                      {"device_increase_limits": {"small": 299}}])
def test_existing_phase_and_external_increase_limits_remain_binding(limits):
    device = small_load()
    result = plan(replace(solar_site(), **limits), [device], {device.id: State()})
    assert result.action is None
    assert result.start_power[device.id]["available_w"] <= 299


@pytest.mark.parametrize("change", [{"valid": False}, {"battery_ready": False},
                                    {"external_hold": True}, {"mode": "paused"}])
def test_solar_relief_never_bypasses_invalid_or_paused_site(change):
    device = small_load()
    result = plan(replace(solar_site(), **change), [device], {device.id: State()})
    assert result.action is None and result.targets[device.id] == 0


def test_full_start_delay_must_still_elapse_on_real_surplus():
    device = replace(small_load(), start_delay_s=300)
    state = State()
    first = plan(solar_site(), [device], {device.id: state})
    assert first.action is None and state.start_since == 1000
    assert plan(replace(solar_site(), now=1299), [device], {device.id: state}).action is None
    last = plan(replace(solar_site(), now=1300), [device], {device.id: state})
    assert last.action and last.action.watts == 300


def test_minimum_runtime_then_cloud_stop_buffer_and_minimum_rest_are_preserved():
    device = replace(small_load(), min_on_s=1200, min_off_s=600, stop_delay_s=300)
    state = State(owned=True, on=True, measured_w=300, target_w=300, last_on=0)
    cloudy = replace(solar_site(), now=1199, grid_w=1000, filtered_grid_w=1000)
    assert plan(cloudy, [device], {device.id: state}).action is None
    assert state.stop_since is None
    assert plan(replace(cloudy, now=1200), [device], {device.id: state}).action is None
    assert state.stop_since == 1200
    assert plan(replace(cloudy, now=1499), [device], {device.id: state}).action is None
    stopped = plan(replace(cloudy, now=1500), [device], {device.id: state})
    assert stopped.action and stopped.action.watts == 0
    state.on = False
    state.target_w = state.measured_w = 0
    state.last_off = 1500
    state.start_since = None
    assert plan(replace(solar_site(), now=2099), [device], {device.id: state}).action is None
    assert plan(replace(solar_site(), now=2100), [device], {device.id: state}).action


def test_optional_credit_does_not_become_an_ev_reclaim_permission():
    device = replace(small_load(), allow_wallbox_reclaim=False)
    result = plan(replace(solar_site(), grid_w=0, filtered_grid_w=0,
                          reclaimable_w=3000), [device], {device.id: State()})
    assert result.action is None and result.targets[device.id] == 0


@pytest.mark.parametrize("constraint", ["hold", "block", "external", "manual"])
def test_small_load_keeps_existing_wallbox_ownership_and_manual_participation_gates(constraint):
    device, state = small_load(), State()
    site = solar_site()
    if constraint == "hold":
        site = replace(site, device_holds={device.id: "Wallbox-voorrang: wacht"})
    elif constraint == "block":
        site = replace(site, device_start_blocks={device.id: "Wallbox wacht op laadkans"})
    elif constraint == "external":
        state.on = True
        state.owned = False
    else:
        state.manual_until = 1200
    result = plan(site, [device], {device.id: state})
    assert result.action is None and result.targets[device.id] == 0


@pytest.mark.asyncio
async def test_running_external_unmetered_cycle_stays_external_and_only_small_load_is_started():
    runtime, hass = runtime_with_running_cycle()
    original_options = deepcopy(runtime.entry.options)
    await runtime.tick()
    assert [row[:2] for row in writes(hass)] == [("switch", "turn_on")]
    assert runtime.states["a"].owned
    assert runtime.states["fictional_cycle"].on
    assert not runtime.states["fictional_cycle"].owned
    assert runtime.entry.options == original_options
    assert runtime.result.start_power["a"]["protected_cycle_reserve_w"] == 2000
    assert runtime.result.start_power["a"]["solar_cycle_reserve_relief_w"] == 2000


@pytest.mark.asyncio
@pytest.mark.parametrize("inspectable", [True, False])
async def test_script_route_only_uses_relief_with_existing_proven_control_authority(inspectable):
    runtime, hass = runtime_with_running_cycle(kind="script")
    if not inspectable:
        hass.data["script"].get_entity = lambda _entity: None
    await runtime.tick()
    calls = writes(hass)
    if inspectable:
        assert len(calls) == 1 and calls[0][0] == "script"
        assert runtime.states["a"].owned
    else:
        assert not calls and not runtime.states["a"].owned
        assert runtime.states["a"].fault


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["import", "grid_unavailable", "dishwasher_unavailable",
                                   "dishwasher_stale", "device_unavailable", "paused"])
async def test_fresh_evidence_is_rechecked_after_the_durable_intent(monkeypatch, change):
    runtime, hass = runtime_with_running_cycle()
    saved = runtime.store.async_save
    changed = False

    async def mutate_after_journal(data):
        nonlocal changed
        await saved(data)
        if changed or "a" not in data.get("leases", {}):
            return
        changed = True
        if change == "import":
            hass.states.set("sensor.grid", 3000, {"unit_of_measurement": "W"})
        elif change == "grid_unavailable":
            hass.states.set("sensor.grid", "unavailable", {"unit_of_measurement": "W"})
        elif change == "dishwasher_unavailable":
            hass.states.set("sensor.dw_phase", "unavailable")
        elif change == "dishwasher_stale":
            hass.states.set("sensor.dw_connection", "Connected", reported_age=301)
        elif change == "device_unavailable":
            hass.states.set("sensor.load", "unavailable", {"unit_of_measurement": "W"})
        else:
            runtime.mode = "paused"

    monkeypatch.setattr(runtime.store, "async_save", mutate_after_journal)
    await runtime.tick()
    assert changed
    if change in ("dishwasher_unavailable", "dishwasher_stale"):
        # A lost appliance source cannot invent either a future consumption
        # reserve or a solar credit. Actual P1 still has 750 W after reserve.
        assert [row[:2] for row in writes(hass)] == [("switch", "turn_on")]
        assert runtime.pending and runtime.states["a"].owned
        assert runtime._power("sensor.grid")[0] == -900
        await runtime.tick()
        assert runtime._dishwasher_unmetered_reserve == 0
        assert runtime._dishwasher_solar_cycle_relief_w == 0
        assert runtime.result.free_w == 750
        assert runtime.result.budget_w == 750
        assert len(writes(hass)) == 1
    else:
        # Current import, missing P1/device readings and Pause still revoke the
        # known-unsent ordinary command at the final boundary.
        assert not writes(hass)
        assert runtime.pending is None and not runtime.states["a"].owned
        assert "a" not in runtime.store.data["leases"]


@pytest.mark.asyncio
async def test_stale_cycle_uses_actual_surplus_without_estimated_peak_or_credit():
    runtime, hass = runtime_with_running_cycle()
    # Observe the real running state once, then retain it across a missing report.
    runtime._observe(time.monotonic(), runtime._local_now())
    hass.states.set("sensor.dw_connection", "Connected", reported_age=301)
    await runtime.tick()
    assert [row[:2] for row in writes(hass)] == [("switch", "turn_on")]
    assert runtime.states["a"].owned
    allocation = runtime.result.start_power["a"]
    assert allocation["solar_cycle_reserve_relief_w"] == 0
    assert allocation["protected_cycle_reserve_w"] == 0
    assert allocation["available_w"] == 750
    assert runtime.result.budget_w == 750


@pytest.mark.asyncio
async def test_full_hard_reservation_is_retained_when_grid_room_changes_during_journal(monkeypatch):
    runtime, hass = runtime_with_running_cycle()
    saved = runtime.store.async_save
    changed = False

    async def shrink_electrical_room(data):
        nonlocal changed
        await saved(data)
        if changed or "a" not in data.get("leases", {}):
            return
        changed = True
        # Without the full 2 kW reserve, 1,800 W P1 import would seem to permit
        # this 300 W start under 3,500 W. Its electrical envelope does not fit.
        hass.states.set("sensor.grid", 1800, {"unit_of_measurement": "W"})
        runtime.states["a"].manual_forced = True

    monkeypatch.setattr(runtime.store, "async_save", shrink_electrical_room)
    await runtime.tick()
    assert changed and not writes(hass)
    assert runtime.pending is None and not runtime.states["a"].owned


@pytest.mark.asyncio
async def test_new_external_cycle_during_journal_cannot_spend_the_previously_empty_reserve(monkeypatch):
    runtime, hass = runtime_with_running_cycle()
    hass.states.set("sensor.dw_phase", "Idle")
    hass.states.set("sensor.grid", 1800, {"unit_of_measurement": "W"})
    runtime.states["a"].manual_forced = True
    saved = runtime.store.async_save
    changed = False

    async def start_cycle_during_journal(data):
        nonlocal changed
        await saved(data)
        if changed or "a" not in data.get("leases", {}):
            return
        changed = True
        # An autonomous protected cycle starts after the small load's first
        # admission. Its full possible peak must enter the final hard envelope.
        hass.states.set("sensor.dw_phase", "Washing")

    monkeypatch.setattr(runtime.store, "async_save", start_cycle_during_journal)
    await runtime.tick()
    assert changed and not writes(hass)
    assert runtime.pending is None and not runtime.states["a"].owned
    assert "a" not in runtime.store.data["leases"]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["phase", "capacity"])
async def test_new_solar_relief_cannot_bypass_last_boundary_phase_or_capacity_loss(monkeypatch, change):
    runtime, hass = runtime_with_running_cycle()
    if change == "phase":
        runtime.phase_settings.update(enabled=True, control_starts=True, limit_w=5000,
            margin_w=0, start_headroom_w=0,
            phase_1_entity="sensor.audit_phase1", phase_2_entity="sensor.audit_phase2",
            phase_3_entity="sensor.audit_phase3")
        for suffix in ("1", "2", "3"):
            hass.states.set("sensor.audit_phase" + suffix, 0, {"unit_of_measurement": "W"})
    else:
        runtime.capacity_settings.update(enabled=True,
            average_demand_entity="sensor.audit_average", monthly_peak_entity="sensor.audit_peak")
        hass.states.set("sensor.audit_average", 0, {"unit_of_measurement": "W"})
        hass.states.set("sensor.audit_peak", 3500, {"unit_of_measurement": "W"})
    saved = runtime.store.async_save
    changed = False

    async def lose_other_room(data):
        nonlocal changed
        await saved(data)
        if changed or "a" not in data.get("leases", {}):
            return
        changed = True
        if change == "phase":
            hass.states.set("sensor.audit_phase1", 4900, {"unit_of_measurement": "W"})
        else:
            hass.states.set("sensor.audit_average", "unavailable", {"unit_of_measurement": "W"})

    monkeypatch.setattr(runtime.store, "async_save", lose_other_room)
    await runtime.tick()
    assert changed and not writes(hass)
    assert runtime.pending is None and not runtime.states["a"].owned


@pytest.mark.asyncio
async def test_real_cycle_meter_keeps_existing_metered_accounting_and_receives_no_exception():
    runtime, hass = runtime_with_running_cycle(meter=True)
    await runtime.tick()
    assert [row[:2] for row in writes(hass)] == [("switch", "turn_on")]
    diagnostic = runtime.result.start_power["a"]
    assert diagnostic["protected_cycle_reserve_w"] == 0
    assert diagnostic["solar_cycle_reserve_relief_w"] == 0
    assert diagnostic["available_w"] == 750
    assert not runtime.states["fictional_cycle"].owned


@pytest.mark.asyncio
async def test_restart_does_not_restore_a_stale_solar_exception_from_prior_observation():
    runtime, hass = runtime_with_running_cycle()
    runtime.mode = "observe"
    await runtime.tick()
    assert runtime.result.start_power["a"]["solar_cycle_reserve_relief_w"] == 2000
    saved = runtime._snapshot()
    hass.states.set("sensor.dw_connection", "Connected", reported_age=301)
    replacement = SolarRuntime(hass, runtime.entry)
    replacement.mode = "solar"
    replacement.device_modes["a"] = "auto"
    # Preserve the known running protected cycle as reconciliation does; old
    # telemetry must never restore the earlier fresh-source solar exemption.
    replacement.states["fictional_cycle"].on = True
    await replacement.tick()
    assert [row[:2] for row in writes(hass)] == [("switch", "turn_on")]
    allocation = replacement.result.start_power["a"]
    assert allocation["solar_cycle_reserve_relief_w"] == 0
    assert allocation["protected_cycle_reserve_w"] == 0
    assert allocation["available_w"] == 750
    assert replacement.result.budget_w == 750
    assert replacement.states["a"].owned
    assert "cycle_solar_relief_w" not in saved
