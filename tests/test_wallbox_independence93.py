"""Optional EV telemetry cannot veto independently metered ordinary loads."""
from dataclasses import replace
import time

import pytest

from custom_components.solar_pilot.consumer_wallbox import ConsumerWallboxPriority
from custom_components.solar_pilot.house_first import HouseFirstGuard
from custom_components.solar_pilot.runtime import SolarRuntime
from custom_components.solar_pilot.wallbox import Reading, WALLBOX_DEFAULTS
from test_runtime import build
from test_runtime_source_reports48 import actuators, invalidate


def setup(*, priority="house_first", failure="missing", device=None):
    config = {"nominal_w": 350, "allow_wallbox_reclaim": True, **(device or {})}
    if priority == "per_device":
        config["wallbox_precedence"] = "wallbox_first"
    old, hass = build(power=True, device=config, settings={"pv_entity": "sensor.pv"})
    old.entry.options["wallbox"] = {
        **WALLBOX_DEFAULTS, "enabled": True, "trust_solar_setting": True,
        "power_entity": "sensor.ev", "status_entity": "sensor.ev_status",
        "mode_entity": "select.ev_mode", "stable_s": 0,
    }
    hass.states.set("sensor.pv", 6000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.ev_status", "Charging")
    hass.states.set("select.ev_mode", "full_solar")
    if failure != "missing":
        value, unit, age = {
            "stale": (4000, "W", 301), "wrong_unit": (4, "kWh", 0),
            "negative": (-4000, "W", 0), "nan": ("nan", "W", 0),
            "unavailable": ("unavailable", "W", 0),
        }[failure]
        hass.states.set("sensor.ev", value, {"unit_of_measurement": unit}, age=age)
    runtime = SolarRuntime(hass, old.entry)
    runtime.others_first = priority != "wallbox_first"
    runtime.wallbox_guard = runtime._make_wallbox_guard()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    return runtime, hass


@pytest.mark.asyncio
@pytest.mark.parametrize("priority", ["house_first", "wallbox_first", "per_device"])
@pytest.mark.parametrize("failure", ["missing", "stale", "wrong_unit", "negative", "nan", "unavailable"])
async def test_actual_export_starts_an_ordinary_load_without_wallbox_telemetry(priority, failure):
    runtime, hass = setup(priority=priority, failure=failure)
    await runtime.tick()
    assert not runtime.wallbox_guard.reading.valid
    assert runtime.wallbox_guard.result.state == "unavailable"
    assert runtime.wallbox_guard.result.max_increase_w is None
    assert getattr(runtime.wallbox_guard, "reclaimable_w", 0) == 0
    assert runtime.result.free_w == 2500
    assert runtime.result.action and runtime.result.action.reclaimed_w == 0
    assert runtime.handover is None
    assert actuators(hass) == [("switch", "turn_on", {"entity_id": "switch.load"})]


@pytest.mark.asyncio
@pytest.mark.parametrize("block", ["no_export", "battery_discharge", "grid_stale", "grid_future", "grid_nan", "grid_bool", "phase", "quarter"])
async def test_unknown_wallbox_does_not_bypass_real_source_or_electrical_guards(block):
    runtime, hass = setup(priority="per_device")
    if block == "no_export":
        hass.states.set("sensor.grid", 50, {"unit_of_measurement": "W"})
    elif block == "battery_discharge":
        runtime.settings["battery_power_entity"] = "sensor.battery"
        hass.states.set("sensor.battery", 3000, {"unit_of_measurement": "W"})
    elif block == "grid_stale":
        hass.states.set("sensor.grid", -5000, {"unit_of_measurement": "W"}, age=runtime.settings["stale_s"]+1)
    elif block == "grid_future":
        invalidate(hass, "sensor.grid", "future")
    elif block in ("grid_nan", "grid_bool"):
        hass.states.set("sensor.grid", "nan" if block == "grid_nan" else True, {"unit_of_measurement": "W"})
    elif block == "phase":
        runtime.phase_settings.update(enabled=True, control_starts=True, limit_w=6000,
            margin_w=200, start_headroom_w=500, phase_1_entity="sensor.l1",
            phase_2_entity="sensor.l2", phase_3_entity="sensor.l3")
        for entity, watts in (("sensor.l1", 5900), ("sensor.l2", -8400), ("sensor.l3", 0)):
            hass.states.set(entity, watts, {"unit_of_measurement": "W"})
    else:
        runtime.capacity_settings.update(enabled=True, average_demand_entity="sensor.average")
        hass.states.set("sensor.average", "unknown", {"unit_of_measurement": "W"})
    await runtime.tick()
    assert not actuators(hass) and runtime.pending is None
    assert not runtime.problem.startswith("Interne fout")
    assert runtime.handover is None


@pytest.mark.parametrize("raw,filtered", [(None, -3000), (-3000, None), (float("nan"), -3000), (-3000, float("inf")), (True, -3000), (-3000, False)])
def test_per_device_guard_distinguishes_unknown_p1_from_unknown_ev(raw, filtered):
    guard = ConsumerWallboxPriority({"enabled": True})
    result = guard.update(now=10, reading=Reading(), grid_w=raw, filtered_grid_w=filtered,
        discharge_w=0, owned_lower={}, has_lower=True)
    assert result.state == "unknown" and result.block_starts
    assert not result.yield_loads and result.potential_w is None


@pytest.mark.asyncio
@pytest.mark.parametrize("protected", [False, True])
async def test_running_load_uses_actual_shortage_and_preserves_minimum_or_protected_cycle(protected):
    runtime, hass = setup(device={"min_on_s": 300, "non_interruptible": protected})
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.load", 350, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", 1000, {"unit_of_measurement": "W"})
    state = runtime.states["a"]
    state.owned = state.on = True
    state.target_w = 350
    state.last_on = time.monotonic()
    await runtime.tick()
    assert not actuators(hass)
    state.last_on = time.monotonic()-301
    await runtime.tick()
    expected = [] if protected else [("switch", "turn_off", {"entity_id": "switch.load"})]
    assert actuators(hass) == expected
    assert not runtime.wallbox_guard.result.release_flexible


def test_disappearing_ev_discards_credit_and_recovery_needs_a_new_full_observation_window():
    guard = HouseFirstGuard({"enabled": True, "stable_s": 10})
    reading = Reading(4000, 1000, True, "Charging", "full_solar", True)
    for stamp in (0, 5, 10):
        guard.update(stamp, reading, -100, 100)
    assert guard.reclaimable_w == 4000
    result = guard.update(15, Reading(), -2000, 100)
    assert guard.reclaimable_w == 0 and result.max_increase_w is None
    result = guard.update(20, replace(reading, power_w=2000, stamp=1020), -100, 100)
    assert result.block_increase and result.remaining_s == 10
    assert guard.reclaimable_w == 2000  # Current evidence only; never the old 4000 W.
    result = guard.update(30, replace(reading, power_w=2000, stamp=1030), -100, 100)
    assert not result.block_increase and result.max_increase_w == 2000
