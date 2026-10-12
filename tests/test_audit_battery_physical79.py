"""Fictitious native phase/quarter limits around battery command journalling."""
from datetime import datetime, timezone

import pytest

from test_battery_runtime import setup_battery


def phase_battery(hint="l1"):
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    runtime.mode = "solar"
    runtime.phase_settings.update(enabled=True, control_starts=True, limit_w=4000,
        margin_w=0, start_headroom_w=0, phase_1_entity="sensor.fixture_phase1",
        phase_2_entity="sensor.fixture_phase2", phase_3_entity="sensor.fixture_phase3")
    runtime.battery_fleet.configs["bat1"]["phase_hint"] = hint
    hass.states.set("sensor.grid", -1800, {"unit_of_measurement": "W"})
    for index in range(1, 4):
        hass.states.set(f"sensor.fixture_phase{index}", -600, {"unit_of_measurement": "W"})
    return runtime, hass


def crowded_phase(hass):
    # P1 remains -1800W: cross-phase export conceals the full L1 import.
    hass.states.set("sensor.fixture_phase1", 3900, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fixture_phase2", -5700, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fixture_phase3", 0, {"unit_of_measurement": "W"})


@pytest.mark.asyncio
@pytest.mark.parametrize("during_save", [False, True])
@pytest.mark.parametrize("hint", ["l1", "three_phase", "unknown"])
async def test_battery_charge_requires_current_phase_headroom_before_and_after_journal(hint, during_save):
    runtime, hass = phase_battery(hint)
    original = runtime.store.async_save
    changed = False

    async def save(payload):
        nonlocal changed
        await original(payload)
        if not changed:
            changed = True
            crowded_phase(hass)

    if during_save:
        runtime.store.async_save = save
    else:
        crowded_phase(hass)
    assert not await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    assert hass.services.calls == []
    assert runtime.battery_fleet.state.pending is None
    assert not runtime.battery_fleet.state.faults


@pytest.mark.asyncio
@pytest.mark.parametrize("during_save", [False, True])
async def test_battery_grid_charging_uses_current_quarter_allowance(during_save):
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    runtime.mode = "solar"
    runtime.battery_fleet.settings.update(allow_grid_charge=True, grid_target_w=2500)
    runtime._local_now = lambda: datetime(2026, 10, 12, 10, 5, tzinfo=timezone.utc)
    runtime.capacity_settings.update(enabled=True, target_peak_w=4000, margin_w=0,
        respect_billing_floor=False, adaptive_to_month_peak=False,
        average_demand_entity="sensor.fixture_quarter_average")
    hass.states.set("sensor.grid", 1000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fixture_quarter_average", 1000, {"unit_of_measurement": "W"})
    original = runtime.store.async_save
    changed = False

    async def save(payload):
        nonlocal changed
        await original(payload)
        if not changed:
            changed = True
            hass.states.set("sensor.fixture_quarter_average", 10000, {"unit_of_measurement": "W"})

    if during_save:
        runtime.store.async_save = save
    else:
        hass.states.set("sensor.fixture_quarter_average", 10000, {"unit_of_measurement": "W"})
    assert not await runtime.battery_fleet.tick(grid_w=1000, allow_command=True)
    assert not hass.services.calls and runtime.battery_fleet.state.pending is None


@pytest.mark.asyncio
async def test_configured_roomy_phase_allows_charge_beside_busy_other_phase():
    runtime, hass = phase_battery("l2")
    crowded_phase(hass)
    assert await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    assert hass.services.calls[-1][2]["value"] == -1800


@pytest.mark.asyncio
@pytest.mark.parametrize("hint", ["l1", "three_phase", "unknown", "auto"])
async def test_current_roomy_phases_allow_existing_battery_charge(hint):
    runtime, hass = phase_battery(hint)
    assert await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    assert hass.services.calls[-1][2]["value"] == -1800


@pytest.mark.asyncio
@pytest.mark.parametrize("during_save", [False, True])
@pytest.mark.parametrize("source", ["unavailable", "bad_unit", "restored", "stale"])
async def test_missing_phase_source_blocks_battery_import_increase(source, during_save):
    runtime, hass = phase_battery()
    original = runtime.store.async_save
    changed = False

    def lose_source():
        hass.states.set("sensor.fixture_phase1", "unavailable" if source == "unavailable" else -600,
            {"unit_of_measurement": "kWh" if source == "bad_unit" else "W",
             **({"restored": True} if source == "restored" else {})},
            age=180 if source == "stale" else 0)

    async def save(payload):
        nonlocal changed
        await original(payload)
        if not changed:
            changed = True
            lose_source()

    if during_save:
        runtime.store.async_save = save
    else:
        lose_source()
    assert not await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    assert not hass.services.calls and runtime.battery_fleet.state.pending is None
    assert "Fase" in runtime.battery_fleet.overview()["reason"]


@pytest.mark.asyncio
async def test_battery_charge_reserves_unmeasured_owned_future_device_demand_on_each_phase():
    runtime, hass = phase_battery()
    runtime.states["a"].on = runtime.states["a"].owned = True
    runtime.states["a"].target_w = 1000
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.fixture_phase1", 1500, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fixture_phase2", -3300, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fixture_phase3", 0, {"unit_of_measurement": "W"})
    assert not await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    assert not hass.services.calls and "Fasegrens" in runtime.battery_fleet.overview()["reason"]


@pytest.mark.asyncio
async def test_explicit_grid_charge_permission_never_raises_hard_import_ceiling():
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    runtime.battery_fleet.settings.update(allow_grid_charge=True, grid_target_w=4000)
    hass.states.set("sensor.grid", 2000, {"unit_of_measurement": "W"})
    assert not await runtime.battery_fleet.tick(grid_w=2000, allow_command=True)
    assert not hass.services.calls and "Netafnamegrens" in runtime.battery_fleet.overview()["reason"]


@pytest.mark.asyncio
async def test_neutral_release_keeps_working_with_missing_phase_and_quarter_sources():
    runtime, hass = phase_battery()
    runtime.capacity_settings.update(enabled=True, average_demand_entity="sensor.fixture_missing")
    del hass.states.data["sensor.fixture_phase1"]
    hass.states.set("sensor.grid", "unavailable", {"unit_of_measurement": "W"})
    assert await runtime.battery_fleet._send("bat1", 0)
    assert hass.services.calls[-1][2]["value"] == 0


@pytest.mark.asyncio
async def test_advisory_only_phase_setting_keeps_existing_charge_permission():
    runtime, hass = phase_battery()
    runtime.phase_settings["control_starts"] = False
    del hass.states.data["sensor.fixture_phase1"]
    assert await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    assert hass.services.calls[-1][2]["value"] == -1800


@pytest.mark.asyncio
@pytest.mark.parametrize("extra_latent_w,expected", [(0, True), (600, False)])
async def test_running_unmetered_aeg_future_peak_is_reserved_once_for_battery_charge(extra_latent_w, expected):
    from copy import deepcopy
    import time
    from test_dishwasher import setup
    from test_command_arbitration49 import attach_battery
    from test_runtime import build
    from custom_components.solar_pilot.engine import State

    runtime, hass, _cfg = setup(nominal_w=1800)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    attach_battery(runtime, hass)
    runtime.phase_settings.update(enabled=True, control_starts=True, limit_w=4000,
        margin_w=0, start_headroom_w=0, phase_1_entity="sensor.fixture_phase1",
        phase_2_entity="sensor.fixture_phase2", phase_3_entity="sensor.fixture_phase3")
    runtime.battery_fleet.configs["bat1"]["phase_hint"] = "l1"
    hass.states.set("sensor.fixture_phase1", -100, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fixture_phase2", -3000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fixture_phase3", 0, {"unit_of_measurement": "W"})
    hass.states.set("sensor.dw_phase", "Running")
    hass.states.set("sensor.grid", -3100, {"unit_of_measurement": "W"})
    runtime.states["a"].owned = runtime.states["a"].on = True
    runtime.states["a"].target_w = 1800
    if extra_latent_w:
        ordinary, _other = build(device={"nominal_w": extra_latent_w})
        cfg = deepcopy(ordinary.configs["a"])
        cfg.update(id="b", control_entity="switch.fixture_latent")
        runtime.configs["b"] = cfg
        runtime.states["b"] = State(on=True, owned=True, target_w=extra_latent_w)
        runtime.device_modes["b"] = "auto"
        hass.states.set("switch.fixture_latent", "on")
    runtime._observe(time.monotonic(), runtime._local_now())
    grid, valid, discharge, ready, _stamp = runtime._site_data()
    runtime._update_dishwasher_priority(time.monotonic(), runtime._local_now(), grid, valid,
                                        discharge, ready, runtime._wallbox_reading())
    assert runtime._dishwasher_unmetered_reserves == {"a": 1800}
    assert runtime._dishwasher_comfort_reserve == 1800
    assert await runtime.battery_fleet._send("bat1", -1800) is expected
    assert bool(hass.services.calls) is expected
    assert hass.states.get("sensor.dw_phase").state == "Running"
