"""Current-site load admission, without a speculative appliance peak reserve."""
from dataclasses import replace

import pytest

from custom_components.solar_pilot.engine import Device, Site, State, plan
from test_cycle_reserve_audit89 import runtime_with_running_cycle, writes
from test_dishwasher_priority32 import inputs
from custom_components.solar_pilot.dishwasher_priority import DishwasherPriority


def case(*, locked=False, measured=0, grid=-1000, cap=3500):
    running = Device("running", nominal_w=2000, min_on_s=600 if locked else 0,
                     min_off_s=0, stop_delay_s=0, priority=1)
    candidate = Device("candidate", nominal_w=500, start_margin_w=0,
                       min_on_s=0, min_off_s=0, start_delay_s=0, priority=2)
    return (Site(now=1000, grid_w=grid, filtered_grid_w=grid, max_import_w=cap),
            [running, candidate],
            {"running": State(owned=True, on=True, measured_w=measured,
                              target_w=2000, last_on=900), "candidate": State()})


@pytest.mark.parametrize("locked", [False, True])
@pytest.mark.parametrize("measured", [0, 50, 300, 2000])
def test_nominal_thermostat_target_does_not_reserve_real_export(locked, measured):
    result = plan(*case(locked=locked, measured=measured))
    assert result.action and result.action.id == "candidate"
    assert result.action.watts == 500
    assert result.targets["running"] == 2000
    assert result.start_power["candidate"]["available_w"] == 850


@pytest.mark.parametrize("limits", [{"max_import_w": -501},
                                      {"max_increase_w": 499},
                                      {"device_increase_limits": {"candidate": 499}}])
def test_real_import_phase_and_individual_limits_remain_binding(limits):
    site, devices, states = case(locked=True)
    result = plan(replace(site, **limits), devices, states)
    assert result.action is None
    assert result.start_power["candidate"]["available_w"] <= 499


def test_actual_heater_step_can_release_flexible_request_without_stopping_cycle():
    site, devices, states = case(locked=True, measured=2000, grid=500)
    devices[0] = replace(devices[0], kind="dishwasher", non_interruptible=True)
    result = plan(site, devices, states)
    assert result.targets["running"] == 2000
    assert result.action is None
    assert result.targets["candidate"] == 0


def test_actual_heater_step_releases_only_the_active_flexible_load():
    site, devices, states = case(locked=True, measured=2000, grid=500)
    devices[0] = replace(devices[0], kind="dishwasher", non_interruptible=True)
    devices[1] = replace(devices[1], stop_delay_s=0)
    states["candidate"] = State(owned=True, on=True, measured_w=500, target_w=500,
                                last_on=900)
    result = plan(site, devices, states)
    assert result.targets["running"] == 2000
    assert result.action and result.action.id == "candidate" and result.action.watts == 0


@pytest.mark.parametrize("patch", [{"valid": False}, {"battery_discharge_w": 500}])
def test_removed_future_reserve_never_creates_source_or_battery_solar(patch):
    site, devices, states = case(locked=True)
    result = plan(replace(site, **patch), devices, states)
    assert result.action is None


def test_afwas_start_pool_ignores_an_idle_higher_nominal_request():
    data = inputs(actual_grid=-2500, filtered_grid=-2500, lower_measured={})
    data["states"]["low"].target_w = 3000
    data["states"]["low"].measured_w = 0
    result = DishwasherPriority().evaluate(**data)
    assert result.start_power["dw"]["available_solar_w"] == 2350
    assert result.start_power["dw"]["unconsumed_commitment_w"] == 0
    assert "dw" in result.fitting_ids


@pytest.mark.asyncio
async def test_runtime_cycle_peak_is_neither_a_deduction_nor_solar_credit():
    runtime, hass = runtime_with_running_cycle()
    await runtime.tick()
    allocation = runtime.result.start_power["a"]
    assert allocation["available_w"] == 750
    for key in ("protected_cycle_reserve_w", "solar_cycle_reserve_relief_w",
                "solar_cycle_reserve_w", "solar_applied_reserve_w"):
        assert allocation[key] == 0
    assert runtime._dishwasher_unmetered_reserves == {}
    assert hass.states.get("sensor.dw_phase").state == "Washing"
    assert not runtime.states["fictional_cycle"].owned


@pytest.mark.asyncio
@pytest.mark.parametrize("grid", [3300, 4000])
async def test_actual_p1_heater_increase_during_journal_rejects_the_unsent_start(monkeypatch, grid):
    runtime, hass = runtime_with_running_cycle()
    runtime.states["a"].manual_forced = True
    saved = runtime.store.async_save
    changed = False

    async def actual_heater_step(data):
        nonlocal changed
        await saved(data)
        if changed or "a" not in data.get("leases", {}):
            return
        changed = True
        hass.states.set("sensor.grid", grid, {"unit_of_measurement": "W"})

    monkeypatch.setattr(runtime.store, "async_save", actual_heater_step)
    await runtime.tick()
    assert changed and not writes(hass)
    assert not runtime.pending and not runtime.states["a"].owned
    assert hass.states.get("sensor.dw_phase").state == "Washing"
    assert "a" not in runtime.store.data["leases"]


def waiting_candidates():
    high = Device("high", nominal_w=2000, start_margin_w=0, priority=1,
                  min_on_s=0, min_off_s=0, start_delay_s=300)
    low = Device("low", nominal_w=310, start_margin_w=0, priority=2,
                 min_on_s=0, min_off_s=0, start_delay_s=0)
    return (Site(now=1000, grid_w=-2100, filtered_grid_w=-2100, reserve_w=0),
            [high, low], {"high": State(), "low": State()})


def test_waiting_higher_start_does_not_reserve_current_power_from_ready_small_load():
    result = plan(*waiting_candidates())
    assert result.action and result.action.id == "low" and result.action.watts == 310
    assert result.targets["high"] == 2000
    assert result.reasons["high"] == "Startvertraging: 300 s"
    assert result.start_power["low"]["available_w"] == 2100
    assert result.start_power["low"]["higher_allocated_w"] == 0


def test_mature_higher_candidate_gets_the_next_serialized_start():
    site, devices, states = waiting_candidates()
    first = plan(site, devices, states)
    assert first.action.id == "low"
    # No start command is fabricated here: the next actual opportunity can
    # occur after the higher candidate has proved its full start buffer.
    result = plan(replace(site, now=1300), devices, states)
    assert result.action and result.action.id == "high" and result.action.watts == 2000
    assert result.targets["low"] == 0
    assert result.start_power["low"]["higher_allocated_w"] == 2000


def test_real_consumption_can_reset_the_waiting_candidates_start_evidence():
    site, devices, states = waiting_candidates()
    plan(site, devices, states)
    assert states["high"].start_since == 1000
    # The low start was followed by actual P1: current free export is now
    # below2kW. This remains a site report, never fabricated load telemetry.
    result = plan(replace(site, now=1005, grid_w=-1790, filtered_grid_w=-1790),
                  devices, states)
    assert states["high"].start_since is None
    assert result.targets["high"] == 0
    assert result.action and result.action.id == "low"


@pytest.mark.asyncio
async def test_unknown_own_sg_command_is_not_relabelled_as_an_idle_device_peak():
    from test_audit_battery_physical79 import phase_battery

    runtime, hass = phase_battery()
    runtime.sg_boost.owned = True
    runtime.sg_boost.relay_on = None
    assert runtime.sg_unconfirmed_reserve_w > 0
    assert not await runtime.battery_fleet._send("bat1", -1800)
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("during_save", [False, True])
async def test_battery_charge_rechecks_actual_p1_after_removing_future_device_reserves(during_save):
    from test_audit_battery_physical79 import phase_battery

    runtime, hass = phase_battery()
    runtime.states["a"].on = runtime.states["a"].owned = True
    runtime.states["a"].target_w = 2000
    hass.states.set("switch.load", "on")
    saved = runtime.store.async_save
    changed = False

    async def actual_load_step(data):
        nonlocal changed
        await saved(data)
        if not changed:
            changed = True
            hass.states.set("sensor.grid", 3300, {"unit_of_measurement": "W"})

    if during_save:
        runtime.store.async_save = actual_load_step
    else:
        hass.states.set("sensor.grid", 3300, {"unit_of_measurement": "W"})
    assert not await runtime.battery_fleet._send("bat1", -1800)
    assert not hass.services.calls
    assert runtime.battery_fleet.state.pending is None
    assert hass.states.get("switch.load").state == "on"
