"""Unavailable loads reserve only unknown future power beside healthy managers."""
from copy import deepcopy
from types import SimpleNamespace
import time

import pytest

from custom_components.solar_pilot.engine import State
from custom_components.solar_pilot.runtime import SolarRuntime
from test_battery_runtime import setup_battery

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
