"""Unavailable loads reserve only unknown future power beside healthy managers."""
from copy import deepcopy
from types import SimpleNamespace
import time

import pytest

from custom_components.solar_pilot.engine import State
from custom_components.solar_pilot.runtime import SolarRuntime
from test_battery_runtime import setup_battery
from test_dhw_comfort27 import at, wb_context
from test_dhw_runtime import setup, tick
from test_priority_board35 import heat_context


def isolate(runtime, hass, device_id="a", watts=600, measured=None):
    """Represent retained ownership with unavailable control, using real sources."""
    cfg = runtime.configs[device_id]
    cfg["nominal_w"] = watts
    cfg["power_entity"] = cfg.get("power_entity") or f"sensor.isolated_{device_id}"
    state = runtime.states[device_id]
    state.owned = state.on = True
    state.available = False
    state.target_w = watts
    state.measured_w = 0 if measured is None else measured
    hass.states.set(cfg["power_entity"], "unavailable" if measured is None else measured,
                    {"unit_of_measurement": "W"})
    return state


@pytest.mark.parametrize("reserve_source", ["absent", "zero"])
def test_existing_dhw_readings_remain_identical_without_isolation(monkeypatch, reserve_source):
    runtime, hass = setup(config={"power_entity": "sensor.boiler_power"})
    hass.states.set("sensor.boiler_power", 1000, {"unit_of_measurement": "W"})
    runtime.capacity = SimpleNamespace(enabled=True, optional_headroom_w=3600)
    if reserve_source == "absent":
        monkeypatch.delattr(SolarRuntime, "isolated_reserve_w")
    else:
        assert runtime.isolated_reserve_w == 0

    reading = runtime.dhw.read(-4000, True, 500, at(12))

    assert reading.export_w == 3500
    assert reading.before_boiler_w == 4500
    assert reading.optional_import_headroom_w == 3600
    assert reading.grid_w == -4000
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("grid,target,export", [(-3900, 50, 3300), (-4100, 50, 3500), (-4200, 60, 3600)])
async def test_new_optional_dhw_target_requires_real_surplus_after_isolated_reserve(grid, target, export):
    runtime, hass = setup(config={"hygiene_schedule_enabled": False})
    isolate(runtime, hass)
    assert runtime.isolated_reserve_w == 600

    await tick(runtime, grid=grid)

    assert runtime.dhw.reading.export_w == export
    assert runtime.dhw.reading.grid_w == grid
    assert runtime.dhw.policy.result.target_c == target
    calls = [c for c in hass.services.calls if c[0] != "persistent_notification"]
    assert calls == ([] if target == 50 else [("water_heater", "set_temperature", {
        "entity_id": "water_heater.boiler", "temperature": 60.0,
    })])
    assert not any(c[0] == "switch" for c in hass.services.calls)


@pytest.mark.parametrize("measured,expected", [(None, 600), (0, 600), (400, 200), (800, 0)])
def test_dhw_own_meter_and_live_isolated_meter_are_not_reserved_twice(measured, expected):
    runtime, hass = setup(config={"power_entity": "sensor.boiler_power"})
    isolate(runtime, hass, measured=measured)
    hass.states.set("sensor.boiler_power", 3500, {"unit_of_measurement": "W"})
    runtime.capacity = SimpleNamespace(enabled=True, optional_headroom_w=3600)

    reading = runtime.dhw.read(-500, True, 0, at(12))

    assert runtime.isolated_reserve_w == expected
    assert reading.export_w == max(0, 500 - expected)
    assert reading.before_boiler_w == 4000 - expected
    assert reading.optional_import_headroom_w == 3600 - expected
    assert reading.grid_w == -500
    assert not hass.services.calls


def test_isolated_reserve_cannot_make_negative_capacity_or_export():
    runtime, hass = setup()
    isolate(runtime, hass, watts=2000)
    runtime.capacity = SimpleNamespace(enabled=True, optional_headroom_w=100)

    reading = runtime.dhw.read(-100, True, 0, at(12))

    assert reading.export_w == reading.optional_import_headroom_w == 0
    assert reading.grid_w == -100
    assert not hass.services.calls


@pytest.mark.parametrize("discharge,grid,pv", [(0, -6000, 5000), (1000, -7000, 5000), (0, -1000, 400)])
def test_dhw_isolation_reserve_survives_the_independent_pv_ceiling(discharge, grid, pv):
    runtime, hass = setup(config={"power_entity": "sensor.boiler_power"})
    isolate(runtime, hass)
    runtime.pv_w = pv
    hass.states.set("sensor.boiler_power", 2000, {"unit_of_measurement": "W"})

    reading = runtime.dhw.read(grid, True, discharge, at(12))

    expected = max(0, pv - 600)
    assert reading.export_w == expected
    assert reading.before_boiler_w == expected
    assert reading.grid_w == grid
    assert reading.battery_discharge_w == discharge
    assert not hass.services.calls


def test_evening_comfort_reclaims_only_confirmed_ev_power_after_isolated_reserve(monkeypatch):
    runtime, hass = setup(config={"evening_enabled": True, "hygiene_schedule_enabled": False})
    isolate(runtime, hass)
    wb_context(runtime, power=4000, status="Charging")
    runtime.pv_w = 6000
    captured = {}
    original = runtime.dhw.comfort.plan

    def record(**kwargs):
        captured.update(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(runtime.dhw.comfort, "plan", record)
    reading = runtime.dhw.read(-100, True, 0, at(16))
    runtime.dhw._prepare_comfort(at(16), reading)

    assert captured["before_ev_w"] == 3500
    assert captured["grid_w"] == -100
    assert reading.export_w == 0
    assert reading.battery_discharge_w == 0
    assert not hass.services.calls


def test_evening_ev_credit_cannot_hide_the_isolation_reserve_at_pv_ceiling(monkeypatch):
    runtime, hass = setup(config={"evening_enabled": True, "hygiene_schedule_enabled": False})
    isolate(runtime, hass)
    wb_context(runtime, power=6000, status="Charging")
    runtime.pv_w = 5000
    captured = {}
    original = runtime.dhw.comfort.plan

    def record(**kwargs):
        captured.update(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(runtime.dhw.comfort, "plan", record)
    reading = runtime.dhw.read(-1000, True, 0, at(16))
    runtime.dhw._prepare_comfort(at(16), reading)

    assert captured["before_ev_w"] == 4400
    assert captured["grid_w"] == -1000
    assert reading.export_w == 400
    assert not hass.services.calls


def preferred_context(*, unknown_preferred=False, headroom=None):
    runtime, hass = setup(config={"hygiene_schedule_enabled": False})
    isolate(runtime, hass)
    original = runtime.configs["a"]
    runtime.configs["preferred"] = {**original, "id": "preferred", "name": "Voorkeursafwas",
        "kind": "dishwasher", "non_interruptible": True, "nominal_w": 2000,
        "control_entity": "switch.preferred", "power_entity": "sensor.preferred",
        "active_entity": "binary_sensor.preferred_running"}
    runtime.states["preferred"] = State(owned=True, on=True,
        available=not unknown_preferred, target_w=2000, measured_w=2000)
    hass.states.set("sensor.preferred", "unavailable" if unknown_preferred else 2000,
                    {"unit_of_measurement": "W"})
    runtime.dishwasher_priority.view.active_ids = {"preferred"}
    runtime._dishwasher_unmetered_reserve = 0
    runtime.pv_w = 9000
    runtime.filtered = -5000
    if headroom is not None:
        runtime.capacity = SimpleNamespace(enabled=True, valid=True, optional_headroom_w=headroom)
    return runtime, hass


def test_unrelated_isolated_owned_load_does_not_veto_healthy_preferred_dhw_allocation():
    runtime, hass = preferred_context()
    reading = runtime.dhw.read(-5000, True, 0, at(12))

    runtime.dhw._prepare_comfort(at(12), reading)

    assert reading.luxury_allowed
    assert reading.export_w == 4400
    assert runtime.states["a"].owned and not runtime.states["a"].available
    assert not hass.services.calls


def test_active_protected_preferred_load_retains_strict_source_guard():
    runtime, hass = preferred_context(unknown_preferred=True)
    assert set(runtime.source_isolated_devices) == {"a", "preferred"}
    reading = runtime.dhw.read(-7000, True, 0, at(12))
    runtime.filtered = -7000

    runtime.dhw._prepare_comfort(at(12), reading)

    assert not reading.luxury_allowed
    assert "afwasstatus" in reading.luxury_reason
    assert runtime.states["preferred"].on and runtime.states["preferred"].owned
    assert not hass.services.calls


@pytest.mark.parametrize("headroom,allowed,remaining", [(3799, False, 3199), (3800, True, 3200)])
def test_preferred_dhw_capacity_budget_includes_isolated_future_load(headroom, allowed, remaining):
    runtime, hass = preferred_context(headroom=headroom)
    reading = runtime.dhw.read(-5000, True, 0, at(12))

    runtime.dhw._prepare_comfort(at(12), reading)

    assert reading.optional_import_headroom_w == remaining
    assert reading.luxury_allowed is allowed
    if not allowed:
        assert "kwartierpiekruimte" in reading.luxury_reason
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("grid,target", [(-1800, -1200), (-500, 0), (0, 0), (1200, 1100)])
async def test_battery_reservation_reduces_charge_room_without_inventing_import(grid, target):
    runtime, hass = setup_battery()
    isolate(runtime, hass)
    before_settings = deepcopy(runtime.battery_fleet.settings)
    before_options = deepcopy(runtime.entry.options)

    sent = await runtime.battery_fleet.tick(grid_w=grid, allow_command=True)

    assert not sent
    assert runtime.battery_fleet.recommendation.valid
    assert runtime.battery_fleet.recommendation.total_target_w == target
    assert runtime.battery_fleet.settings == before_settings
    assert runtime.entry.options == before_options
    assert not runtime.battery_fleet.state.pending
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("reserve_source", ["absent", "zero"])
async def test_existing_battery_allocation_without_isolation_is_unchanged(monkeypatch, reserve_source):
    runtime, hass = setup_battery()
    if reserve_source == "absent":
        monkeypatch.delattr(SolarRuntime, "isolated_reserve_w")

    await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)

    assert runtime.battery_fleet.recommendation.total_target_w == -1800
    assert runtime.battery_fleet.settings["charge_reserve_w"] == 0
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("grid", [None, float("nan"), "unavailable"])
async def test_isolated_reserve_cannot_authorize_battery_with_invalid_grid(grid):
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    isolate(runtime, hass)

    sent = await runtime.battery_fleet.tick(grid_w=grid, allow_command=True)

    assert not sent and not runtime.battery_fleet.recommendation.valid
    assert not runtime.battery_fleet.state.pending
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_peak_shaving_uses_real_import_without_extra_isolation_discharge():
    runtime, hass = setup_battery()
    isolate(runtime, hass, watts=2000)
    runtime.battery_fleet.settings["strategy"] = "peak_shaving"

    await runtime.battery_fleet.tick(grid_w=2000, capacity_allowed_grid_w=1000)

    assert runtime.battery_fleet.recommendation.total_target_w == 1000
    assert runtime.battery_fleet.settings["charge_reserve_w"] == 0
    assert not hass.services.calls


def test_isolation_reserve_excludes_nonfitting_higher_priority_start():
    runtime, hass = heat_context()
    higher = runtime.states["a"]
    higher.enabled = higher.available = higher.demand = higher.interlock = higher.cycle_armed = True
    isolate(runtime, hass, device_id="second_consumer", watts=800)
    runtime.grid_w = runtime.filtered = -1000
    reading = deepcopy(runtime.dhw.reading)

    runtime.priority_board.guard_extra(reading, time.monotonic())

    assert reading.luxury_allowed
    assert runtime.isolated_reserve_w == 800
    assert not hass.services.calls


def test_temporarily_isolated_higher_priority_device_does_not_claim_start_slot():
    runtime, hass = heat_context()
    runtime.recovery["a"] = {"watts": 350}
    higher = runtime.states["a"]
    higher.on = False
    higher.enabled = higher.available = higher.demand = higher.interlock = higher.cycle_armed = True
    reading = deepcopy(runtime.dhw.reading)

    runtime.priority_board.guard_extra(reading, time.monotonic())

    assert "a" in runtime.source_isolated_devices
    assert reading.luxury_allowed
    assert runtime.recovery["a"] == {"watts": 350}
    assert not hass.services.calls
