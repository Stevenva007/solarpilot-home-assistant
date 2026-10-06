"""Full-runtime shared-HP integration and physical OFF/measurement sequencing."""
from types import SimpleNamespace as NS
import time

import pytest

from custom_components.solar_pilot.heatpump_budget import heatpump_power
from test_heatpump_budget57 import setup as budget_setup
from test_priority_dhw57 import reclaim_context, sample


def actuator_calls(hass):
    return [call for call in hass.services.calls if call[0] != "persistent_notification"]


@pytest.mark.asyncio
async def test_owned_normal50_can_release_flexible_load_then_requires_actual_new_export():
    runtime, hass = reclaim_context()
    runtime.settings.update(settle_s=0, filter_s=0)
    runtime.dhw.settings.update(night_enabled=False)
    runtime.dhw.owned_target = 50
    runtime.dhw.policy.current = 50
    runtime.states["a"].last_on = time.monotonic() - 1000
    assert runtime.dhw.busy  # Ownership is not an unresolved command.

    await runtime._tick()
    assert actuator_calls(hass) == []
    assert runtime.priority_board.extra_reclaim["state"] == "stability"
    sample(hass)
    await runtime._tick()
    assert actuator_calls(hass) == [("switch", "turn_off", {"entity_id": "switch.load"})]
    assert runtime.pending and runtime.pending["watts"] == 0
    assert runtime.dhw.owned_target == 50 and not runtime.dhw.pending

    # A successful OFF command and its state echo are still not 300 W of solar
    # credit. There must be a genuinely newer P1 report showing that release.
    await runtime._tick()
    assert runtime.pending is None
    assert len(actuator_calls(hass)) == 1
    assert runtime.dhw.reading.actual_target_c == 50
    hass.states.set("sensor.load", 0, {"unit_of_measurement": "W"})
    sample(hass, -3000)
    await runtime._tick()
    assert actuator_calls(hass)[-1] == (
        "water_heater", "set_temperature", {"entity_id": "water_heater.boiler", "temperature": 60})
    assert len(actuator_calls(hass)) == 2


@pytest.mark.asyncio
async def test_own50_does_not_make_the_requested_off_watts_available():
    runtime, hass = reclaim_context()
    runtime.settings.update(settle_s=0, filter_s=0)
    runtime.dhw.settings.update(night_enabled=False)
    runtime.dhw.owned_target = runtime.dhw.policy.current = 50
    runtime.states["a"].last_on = time.monotonic() - 1000
    hass.services.respond = False
    await runtime._tick()
    sample(hass)
    await runtime._tick()
    assert runtime.pending and runtime.pending["watts"] == 0
    # Even a larger PV reading cannot replace an unconfirmed controlled OFF.
    hass.states.set("sensor.pv", 7000, {"unit_of_measurement": "W"})
    sample(hass, -3000)
    await runtime._tick()
    assert len(actuator_calls(hass)) == 1
    assert not runtime.dhw.pending
    assert runtime.dhw.owned_target == 50


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["manual_boost", "lost_solar", "space_heat", "lost_control"])
async def test_reclaim_off_rechecks_inputs_after_durable_journal_await(change):
    runtime, hass = reclaim_context()
    runtime.settings.update(settle_s=0, filter_s=0)
    runtime.dhw.settings.update(night_enabled=False)
    runtime.dhw.owned_target = runtime.dhw.policy.current = 50
    runtime.states["a"].last_on = time.monotonic() - 1000
    saved = runtime.store.async_save
    changed = False

    async def change_during_store(data):
        nonlocal changed
        await saved(data)
        if changed or not runtime.pending or runtime.pending.get("watts") != 0:
            return
        changed = True
        if change == "manual_boost":
            runtime.states["a"].boost_until = time.monotonic() + 600
        elif change == "lost_solar":
            sample(hass, -1500)
        elif change == "space_heat":
            hass.states.set("climate.home", "heat", {"hvac_action": "heating"})
        else:
            hass.states.set("switch.load", "unavailable")

    runtime.store.async_save = change_during_store
    await runtime._tick()
    sample(hass)
    await runtime._tick()
    assert changed
    assert actuator_calls(hass) == []
    assert runtime.pending is None
    assert runtime.states["a"].target_w == 300
    assert not runtime.dhw.pending


def test_runtime_comfort_reserves_shared_hp_shortfall_only_once():
    runtime, hass = budget_setup(grid=-4000, hp=2000, reserve=0)
    runtime.mode = "solar"
    runtime.dhw.reading.temperature_c = 40
    runtime.dhw.reading.actual_target_c = 50
    hass.states.set("water_heater.tank", "heat_pump", {
        "temperature": 50, "current_temperature": 40, "hvac_action": "idle"})
    reserve, reason = runtime._dishwasher_comfort_context()
    assert not reason and reserve == 1200
    # A shared HP meter can reserve physical watts, never claim tank activity.
    assert runtime.heat_pump_shared()
    assert heatpump_power(runtime)["watts"] == 2000
    runtime._dishwasher_comfort_reserve = reserve
    runtime._shared_heatpump_comfort_reserve_w = reserve
    assert runtime.climate_solar_budget()["compensated_w"] == 5000


def test_runtime_duplicate_or_estimated_hp_meter_keeps_full_future_envelope():
    runtime, hass = budget_setup(hp=2000)
    runtime.dhw.reading.temperature_c = 40
    runtime.dhw.reading.actual_target_c = 50
    hass.states.set("water_heater.tank", "heat_pump", {
        "temperature": 50, "current_temperature": 40, "hvac_action": "idle"})
    for invalid in ("duplicate", "estimated", "scope"):
        runtime.battery_fleet.configs.clear()
        runtime.dhw.config["power_meter_scope"] = "heat_pump"
        hass.states.get("sensor.hp").attributes.pop("estimated", None)
        if invalid == "duplicate":
            runtime.battery_fleet.configs["b"] = {"power_entity": "sensor.hp"}
        elif invalid == "estimated":
            hass.states.get("sensor.hp").attributes["estimated"] = True
        else:
            runtime.dhw.config["power_meter_scope"] = "tank"
        assert runtime._dishwasher_comfort_context()[0] == 3200


@pytest.mark.parametrize("guard", ["old_p1", "stale_pv", "pending", "settling", "phase", "import", "quarter"])
def test_runtime_final_hp_gate_preserves_physical_sources_and_capacity(guard):
    runtime, hass = budget_setup(grid=-2500, hp=0)
    runtime.mode = "solar"
    assert runtime.heat_pump_increase_allowed()[0]
    if guard in ("old_p1", "stale_pv"):
        runtime.last_issued_wall = time.time() - 5
        source = "sensor.grid" if guard == "old_p1" else "sensor.pv"
        hass.states.set(source, -2500 if source == "sensor.grid" else 5000,
                        {"unit_of_measurement": "W"}, reported_age=10 if guard == "old_p1" else 1000)
    elif guard == "pending":
        runtime.pending = {"id": "a", "watts": 0}
    elif guard == "settling":
        runtime.last_issued = time.monotonic()
    elif guard == "phase":
        runtime.phase_settings.update(enabled=True, control_starts=True)
        runtime.phase = NS(valid=True, block_increase=False, headroom_w=3199, reason="")
    elif guard == "import":
        runtime.settings["max_import_w"] = 699
    else:
        runtime.capacity_settings["enabled"] = True
        runtime.capacity = NS(valid=True, allowed_grid_w=699)
    assert not runtime.heat_pump_increase_allowed()[0]


def test_final_gate_reuses_one_shared_physical_hp_draw():
    runtime, _ = budget_setup(grid=0, hp=2500)
    runtime.mode = "solar"
    runtime.settings["max_import_w"] = 700
    assert runtime.heat_pump_increase_allowed()[0]
    runtime.settings["max_import_w"] = 699
    assert not runtime.heat_pump_increase_allowed()[0]


@pytest.mark.parametrize("commitment", ["isolated", "unconsumed"])
def test_final_phase_gate_reserves_other_possible_draw(monkeypatch, commitment):
    runtime, _ = budget_setup(grid=-5000, hp=0)
    runtime.mode = "solar"
    runtime.phase_settings.update(enabled=True, control_starts=True)
    runtime.phase = NS(valid=True, block_increase=False, headroom_w=3200, reason="")
    assert runtime.heat_pump_increase_allowed()[0]
    if commitment == "isolated":
        monkeypatch.setattr(type(runtime), "isolated_reserve_w", property(lambda _self: 1000.0))
    else:
        runtime.states["a"].owned = runtime.states["a"].on = True
        runtime.states["a"].target_w = 500
        runtime.states["a"].measured_w = 0
    assert not runtime.heat_pump_increase_allowed()[0]
