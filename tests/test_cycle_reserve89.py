"""Future dishwasher peaks stay electrical; flexible loads need real export."""
from copy import deepcopy
from dataclasses import replace
import time

import pytest

from custom_components.solar_pilot.engine import Device, Site, State, plan
from test_dishwasher import setup
from test_runtime import build


def engine_case(*, owned=False, flexible=None, **site_changes):
    wash = Device("wash", kind="dishwasher", nominal_w=2000,
                  non_interruptible=True, priority=1)
    wash_state = State(owned=owned, on=True, measured_w=2000, target_w=2000)
    dry = flexible or Device("dry", nominal_w=360, start_margin_w=40,
        min_on_s=0, min_off_s=0, start_delay_s=0, stop_delay_s=0)
    site = Site(now=1000, grid_w=-900, filtered_grid_w=-900, reserve_w=150,
        comfort_reserve_w=2000, protected_cycle_reserve_w=2000,
        cycle_solar_relief_w=2000, **site_changes)
    return site, [wash, dry], {"wash": wash_state, dry.id: State()}


def runtime_case(*, owned=False, flex_changes=None):
    """Fictional active unmetered dishwasher plus separately metered switch."""
    runtime, hass, _ = setup(nominal_w=2000)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    runtime.settings["reserve_w"] = 150
    hass.states.set("sensor.grid", -900, {"unit_of_measurement": "W"})
    hass.states.set("sensor.dw_phase", "Running")
    runtime.states["a"].on = True
    runtime.states["a"].owned = owned
    runtime.states["a"].target_w = 2000
    ordinary, _ = build(power=True, device={"nominal_w": 360, "start_margin_w": 40,
                                            **(flex_changes or {})})
    cfg = deepcopy(ordinary.configs["a"])
    cfg.update(id="b", name="Fictional flexible load", control_entity="switch.fixture_flexible")
    runtime.configs["b"] = runtime.consumer_history.configs["b"] = cfg
    runtime.states["b"] = State(last_off=-1e12)
    runtime.device_modes["b"] = "auto"
    hass.states.set("switch.fixture_flexible", "off")
    return runtime, hass


def writes(hass):
    return [call for call in hass.services.calls if call[0] != "persistent_notification"]


@pytest.mark.parametrize("owned", [False, True])
def test_real_remaining_solar_is_usable_while_full_peak_stays_electrical(owned):
    result = plan(*engine_case(owned=owned))
    allocation = result.start_power["dry"]
    assert result.action.id == "dry" and result.action.watts == 360
    assert allocation["available_w"] == 750 and allocation["required_w"] == 400
    assert allocation["protected_cycle_reserve_w"] == 2000
    assert allocation["solar_cycle_reserve_relief_w"] == 2000
    assert allocation["solar_cycle_reserve_w"] == allocation["solar_applied_reserve_w"] == 0
    assert allocation["remaining_solar_w"] == 750
    assert allocation["electrical_headroom_w"] == 2400


def test_two_flexible_loads_share_one_export_pool_instead_of_reusing_relief():
    site, devices, states = engine_case()
    devices.append(replace(devices[-1], id="second", priority=90))
    states["second"] = State()
    result = plan(site, devices, states)
    assert result.targets["dry"] == 360
    assert result.targets["second"] == 0
    assert result.start_power["second"]["available_w"] == 390
    assert result.action.id == "dry"


def test_future_full_peak_still_blocks_start_if_import_ceiling_cannot_fit_it():
    result = plan(*engine_case(max_import_w=1400))
    assert result.start_power["dry"]["available_w"] == 300
    assert not result.start_power["dry"]["sufficient"]
    assert result.action is None


@pytest.mark.parametrize("changes", [
    {"filtered_grid_w": -450}, {"grid_w": -450}, {"battery_discharge_w": 500},
    {"cycle_solar_relief_w": 0}, {"valid": False}, {"battery_ready": False},
])
def test_missing_real_export_or_trusted_cycle_evidence_cannot_create_a_start(changes):
    site, devices, states = engine_case()
    result = plan(replace(site, **changes), devices, states)
    assert result.action is None


@pytest.mark.parametrize("kind,protected", [("switch", True), ("number", True),
    ("script", True), ("dishwasher", True), ("other", False)])
def test_protected_or_unknown_device_does_not_reuse_cycle_solar_reserve(kind, protected):
    dry = Device("dry", kind=kind, non_interruptible=protected, nominal_w=400,
                 min_units=4, max_units=4, watts_per_unit=100,
                 min_off_s=0, start_delay_s=0, start_margin_w=10)
    result = plan(*engine_case(flexible=dry))
    assert result.action is None
    assert result.start_power["dry"]["solar_cycle_reserve_relief_w"] == 0
    assert result.start_power["dry"]["solar_cycle_reserve_w"] == 2000


def test_isolated_and_unconfirmed_reservations_are_never_relaxed():
    site, devices, states = engine_case()
    result = plan(replace(site, comfort_reserve_w=2500, isolated_reserve_w=300,
        sg_unconfirmed_reserve_w=200), devices, states)
    allocation = result.start_power["dry"]
    assert allocation["available_w"] == 250 and result.action is None
    assert allocation["solar_cycle_reserve_relief_w"] == 2000
    assert allocation["solar_applied_reserve_w"] == 500


def test_relief_cannot_outgrow_the_actual_cycle_reserve_component():
    site, devices, states = engine_case()
    result = plan(replace(site, comfort_reserve_w=2500, cycle_solar_relief_w=9000,
        isolated_reserve_w=300, sg_unconfirmed_reserve_w=200), devices, states)
    assert result.start_power["dry"]["solar_cycle_reserve_relief_w"] == 2000
    assert result.start_power["dry"]["solar_applied_reserve_w"] == 500
    assert result.start_power["dry"]["available_w"] == 250
    assert result.action is None


def test_locked_number_can_modulate_without_treating_cycle_peak_as_current_solar_use():
    dry = Device("dry", kind="number", min_units=1, max_units=8,
                 step_units=1, watts_per_unit=100, min_on_s=300)
    site, devices, states = engine_case(flexible=dry)
    states["dry"] = State(owned=True, on=True, measured_w=100, target_w=100, last_on=950)
    result = plan(site, devices, states)
    assert result.targets["dry"] == 800
    assert result.action.id == "dry" and result.action.watts == 800


@pytest.mark.asyncio
@pytest.mark.parametrize("owned", [False, True])
async def test_runtime_starts_flexible_load_and_leaves_running_dishwasher_untouched(owned):
    runtime, hass = runtime_case(owned=owned)
    await runtime.tick()
    assert [(call[0], call[1]) for call in writes(hass)] == [("switch", "turn_on")]
    assert runtime._dishwasher_unmetered_reserve == 0
    assert runtime._dishwasher_solar_cycle_relief_w == 0
    assert runtime.result.start_power["b"]["available_w"] == 750
    assert hass.states.get("sensor.dw_phase").state == "Running"
    assert runtime.states["a"].owned is owned


@pytest.mark.asyncio
async def test_five_minute_start_delay_is_not_shortened_by_solar_reserve_relief():
    runtime, hass = runtime_case(flex_changes={"start_delay_s": 300})
    await runtime.tick()
    assert not writes(hass)
    assert runtime.states["b"].start_since is not None
    assert "Startvertraging" in runtime.result.reasons["b"]
    runtime.states["b"].start_since = time.monotonic()-301
    await runtime.tick()
    assert [(call[0], call[1]) for call in writes(hass)] == [("switch", "turn_on")]


@pytest.mark.asyncio
async def test_returning_heater_load_respects_existing_minimum_runtime():
    runtime, hass = runtime_case(flex_changes={"min_on_s": 300, "stop_delay_s": 0})
    await runtime.tick()
    assert len(writes(hass)) == 1
    # Confirm the simulated switch and power, then report an actual import.
    hass.states.set("sensor.load", 360, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", 1500, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert len(writes(hass)) == 1 and runtime.states["b"].owned
    runtime.states["b"].last_on = time.monotonic()-301
    runtime.last_issued = time.monotonic()-runtime.settings["settle_s"]-1
    await runtime.tick()
    assert [(call[0], call[1]) for call in writes(hass)] == [
        ("switch", "turn_on"), ("switch", "turn_off")]
    assert hass.states.get("sensor.dw_phase").state == "Running"
