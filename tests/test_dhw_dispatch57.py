"""Final optional-write checks and one physical heat-pump meter accounting."""
from datetime import datetime
import time

import pytest

from custom_components.solar_pilot.dhw import normalized_settings, validate_settings
from custom_components.solar_pilot.dishwasher_priority import DHWLuxuryAllocation
from test_dhw_runtime import setup, updates


DAY = datetime(2026, 10, 6, 12)


async def tick(runtime):
    return await runtime.dhw.tick(time.monotonic(), -4000, True, 0, local_now=DAY)


def test_meter_scope_defaults_to_whole_heat_pump_and_rejects_unknown_scopes():
    assert normalized_settings({})["power_meter_scope"] == "heat_pump"
    assert normalized_settings({"power_meter_scope": "tank"})["power_meter_scope"] == "tank"
    assert validate_settings({"power_meter_scope": "guessed"})["power_meter_scope"] == "dhw_range"


@pytest.mark.asyncio
async def test_final_power_gate_refuses_new_optional_goal_without_intent_or_call(monkeypatch):
    runtime, hass = setup()
    monkeypatch.setattr(runtime, "heat_pump_increase_allowed",
                        lambda: (False, "Wacht op een nieuwe P1-meting"), raising=False)

    assert not await tick(runtime)

    assert not hass.services.calls and not runtime.store.saves
    assert runtime.dhw.pending is None and runtime.dhw.owned_target is None
    assert runtime.dhw.execution["reason"] == "Wacht op een nieuwe P1-meting"
    assert runtime.dhw.execution["code"] == "live_power"
    assert runtime.dhw.policy.candidate == 60


@pytest.mark.asyncio
async def test_power_changed_during_journal_save_cancels_unsent_intent(monkeypatch):
    runtime, hass = setup()
    live = [True]
    issued = runtime.last_issued, runtime.last_issued_wall
    monkeypatch.setattr(runtime, "heat_pump_increase_allowed",
                        lambda: (live[0], "Overschot verdwenen vóór uitvoering"), raising=False)
    save = runtime.store.async_save

    async def change_during_save(data):
        await save(data)
        live[0] = False

    monkeypatch.setattr(runtime.store, "async_save", change_during_save)

    assert not await tick(runtime)

    assert not hass.services.calls
    assert runtime.dhw.pending is None and runtime.dhw.owned_target is None
    assert not runtime.dhw.fault and not runtime.dhw.manual_hold
    assert runtime.dhw.last_command_wall == 0
    assert (runtime.last_issued, runtime.last_issued_wall) == issued
    assert runtime.store.saves[0]["dhw"]["pending"]["target"] == 60
    assert runtime.store.saves[-1]["dhw"]["pending"] is None
    assert runtime.dhw.execution["code"] == "live_power"


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["target", "powerful", "space", "cooling", "mode", "source", "capability"])
async def test_intervening_native_or_source_change_before_physical_write_is_cancelled(monkeypatch, change):
    runtime, hass = setup()
    monkeypatch.setattr(runtime, "heat_pump_increase_allowed", lambda: (True, ""), raising=False)
    save = runtime.store.async_save

    async def change_during_save(data):
        await save(data)
        if change == "target":
            updates(hass, "water_heater.boiler", temperature=55)
        elif change == "powerful":
            hass.states.set("switch.powerful", "on")
        elif change == "space":
            hass.states.set("climate.home", "auto", {"hvac_action": "heating"})
        elif change == "cooling":
            hass.states.set("climate.home", "auto", {"hvac_action": "cooling"})
        elif change == "mode":
            runtime.mode = "observe"
        elif change == "capability":
            updates(hass, "water_heater.boiler", max_temp=55)
        else:
            hass.states.set("sensor.water", "unavailable", {"unit_of_measurement": "°C"})

    monkeypatch.setattr(runtime.store, "async_save", change_during_save)

    assert not await tick(runtime)

    assert not hass.services.calls
    assert runtime.dhw.pending is None and runtime.dhw.owned_target is None
    assert not runtime.dhw.fault and not runtime.dhw.manual_hold
    assert runtime.dhw.policy.candidate == 60
    assert runtime.dhw.execution["code"] == "live_power"


@pytest.mark.asyncio
async def test_power_gate_does_not_prevent_safe_lowering_to_normal_target(monkeypatch):
    runtime, hass = setup()
    updates(hass, "water_heater.boiler", temperature=60)
    runtime.dhw.owned_target = 60
    runtime.dhw.policy.current = 60
    monkeypatch.setattr(runtime, "heat_pump_increase_allowed",
                        lambda: (False, "Netmeting ontbreekt"), raising=False)

    assert await runtime.dhw.tick(time.monotonic(), None, False, 0, local_now=DAY)

    assert hass.services.calls[-1][2]["temperature"] == 50


@pytest.mark.asyncio
@pytest.mark.parametrize("source,value", [("sensor.grid", -1500), ("sensor.pv", 2000),
                                         ("sensor.battery", -1200), ("sensor.boiler_power", 800)])
async def test_changed_power_values_during_save_require_reassessment_even_if_capacity_still_fits(
        monkeypatch, source, value):
    runtime, hass = setup(config={"power_entity": "sensor.boiler_power"})
    runtime.settings["battery_power_entity"] = "sensor.battery"
    hass.states.set("sensor.battery", 0, {"unit_of_measurement": "W"})
    monkeypatch.setattr(runtime, "heat_pump_increase_allowed", lambda: (True, ""), raising=False)
    save = runtime.store.async_save

    async def change_during_save(data):
        await save(data)
        hass.states.set(source, value, {"unit_of_measurement": "W"})

    monkeypatch.setattr(runtime.store, "async_save", change_during_save)

    assert not await tick(runtime)

    assert not hass.services.calls and runtime.dhw.pending is None
    assert runtime.dhw.owned_target is None and not runtime.dhw.fault
    assert "meting gewijzigd" in runtime.dhw.execution["reason"]


@pytest.mark.asyncio
async def test_unchanged_electrical_heartbeat_during_save_keeps_valid_proposal(monkeypatch):
    runtime, hass = setup()
    monkeypatch.setattr(runtime, "heat_pump_increase_allowed", lambda: (True, ""), raising=False)
    save = runtime.store.async_save

    async def heartbeat_during_save(data):
        await save(data)
        for entity_id in ("sensor.grid", "sensor.pv"):
            obj = hass.states.get(entity_id)
            hass.states.set(entity_id, obj.state, obj.attributes)

    monkeypatch.setattr(runtime.store, "async_save", heartbeat_during_save)

    assert await tick(runtime)
    assert hass.services.calls[-1][2]["temperature"] == 60


@pytest.mark.asyncio
async def test_changed_measurement_during_previous_ack_save_invalidates_earlier60_proposal(monkeypatch):
    runtime, hass = setup()
    hass.states.set("sensor.grid", -4000, {"unit_of_measurement": "W"})
    issued = time.monotonic() - 1
    runtime.dhw.pending = {"target": 50, "issued": issued, "issued_wall": time.time() - 1,
                           "release": False, "ack_poll_min_s": 0}
    runtime.dhw.owned_target = 50
    monkeypatch.setattr(runtime, "heat_pump_increase_allowed", lambda: (True, ""), raising=False)
    save = runtime.store.async_save

    async def change_during_ack_save(data):
        await save(data)
        hass.states.set("sensor.grid", -1500, {"unit_of_measurement": "W"})

    monkeypatch.setattr(runtime.store, "async_save", change_during_ack_save)

    assert not await tick(runtime)

    assert not hass.services.calls
    assert runtime.dhw.pending is None and runtime.dhw.owned_target == 50
    assert runtime.dhw.last_success["target_c"] == 50
    assert len(runtime.store.saves) == 1  # ACK only; no new60 intent exists
    assert "sinds beoordeling" in runtime.dhw.execution["reason"]


@pytest.mark.asyncio
async def test_restart_reconcile_save_cannot_spend_the_grid_read_before_its_await(monkeypatch):
    from test_dhw_restart47 import restart

    runtime, hass = setup()
    hass.states.set("sensor.grid", -4000, {"unit_of_measurement": "W"})
    manager = restart(runtime, owned=50)
    monkeypatch.setattr(runtime, "heat_pump_increase_allowed", lambda: (True, ""), raising=False)
    save = runtime.store.async_save

    async def change_during_reconcile_save(data):
        await save(data)
        hass.states.set("sensor.grid", -1500, {"unit_of_measurement": "W"})

    monkeypatch.setattr(runtime.store, "async_save", change_during_reconcile_save)

    assert not await tick(runtime)

    assert not hass.services.calls
    assert manager.restart_recovery is None and manager.owned_target == 50
    assert manager.pending is None and not manager.fault
    assert len(runtime.store.saves) == 1
    assert "sinds beoordeling" in manager.execution["reason"]


@pytest.mark.parametrize("scope,action,restart_required", [
    ("heat_pump", "idle", True), ("tank", "idle", False),
    ("heat_pump", "heating", False),
])
def test_shared_meter_draw_does_not_prove_tank_heat_but_explicit_tank_action_does(
        monkeypatch, scope, action, restart_required):
    runtime, hass = setup(config={"power_entity": "sensor.boiler_power", "power_meter_scope": scope})
    runtime.smart_climate.settings["zone_entities"] = ["climate.home"]
    updates(hass, "water_heater.boiler", temperature=60, hvac_action=action)
    hass.states.set("sensor.boiler_power", 1200, {"unit_of_measurement": "W"})
    runtime.dhw.owned_target = 60
    captured = {}
    runtime.dishwasher_priority.view.active_ids = {"a"}

    def allocation(**kwargs):
        captured.update(kwargs)
        return DHWLuxuryAllocation(True, "Past naast beschermde cyclus")

    monkeypatch.setattr(runtime.dishwasher_priority, "dhw_luxury_allocation", allocation)
    reading = runtime.dhw.read(-4000, True, 0, DAY)
    runtime.dhw._prepare_comfort(DAY, reading)

    assert captured["restart_proof_required"] is restart_required
    assert reading.export_w == 4000
    assert reading.before_boiler_w == 5000  # capped to real PV; one meter once
    assert not hass.services.calls


@pytest.mark.parametrize("action", ["heating", "cooling", "unknown"])
def test_shared_meter_is_not_boiler_hold_credit_while_sibling_zone_is_active_or_unknown(action):
    runtime, hass = setup(config={"power_entity": "sensor.boiler_power"})
    runtime.smart_climate.settings["zone_entities"] = ["climate.extra"]
    hass.states.set("climate.extra", "auto", {"hvac_action": action})
    hass.states.set("sensor.boiler_power", 3500, {"unit_of_measurement": "W"})

    reading = runtime.dhw.read(-500, True, 0, DAY)

    assert reading.before_boiler_w is None
    assert reading.export_w == 500
    assert reading.space_climate_busy is (None if action == "unknown" else True)
    if action == "cooling":
        assert reading.cooling is True


def test_duplicate_battery_fleet_meter_is_not_heat_pump_credit():
    runtime, _ = setup(config={"power_entity": "sensor.boiler_power"})
    runtime.battery_fleet.configs["battery"] = {"power_entity": "sensor.boiler_power"}
    assert not runtime.dhw.exclusive_meter()


def test_disabled_wallbox_meter_is_still_not_heat_pump_credit():
    runtime, _ = setup(config={"power_entity": "sensor.boiler_power"})
    runtime.wallbox_settings.update(enabled=False, power_entity="sensor.boiler_power")
    assert not runtime.dhw.exclusive_meter()


@pytest.mark.parametrize("estimated", [{"estimated": True}, {"is_estimated": True},
                                       {"friendly_name": "Geschat warmtepompvermogen"}])
@pytest.mark.parametrize("scope", ["heat_pump", "tank"])
def test_estimated_meter_cannot_supply_solar_hold_or_tank_activity_proof(estimated, scope):
    runtime, hass = setup(config={"power_entity": "sensor.boiler_power", "power_meter_scope": scope})
    hass.states.set("sensor.boiler_power", 3500, {"unit_of_measurement": "W", **estimated})
    reading = runtime.dhw.read(-500, True, 0, DAY)
    assert runtime.dhw._metered_power() is None
    assert reading.before_boiler_w is None and reading.export_w == 500


@pytest.mark.asyncio
@pytest.mark.parametrize("grid,allowed", [(-5149, False), (-5150, True), (-6000, True)])
@pytest.mark.parametrize("owned", [False, True])
async def test_nonpreferred_running_wash_keeps_future_heater_reserve_before60(monkeypatch, grid, allowed, owned):
    runtime, hass = setup()
    runtime.pv_w = 9000
    hass.states.set("sensor.pv", 9000, {"unit_of_measurement": "W"})
    runtime.filtered = grid
    runtime.settings["reserve_w"] = 150
    runtime.configs["a"]["kind"] = "dishwasher"
    runtime.configs["a"]["dishwasher_priority_enabled"] = False
    runtime.configs["a"].update(dishwasher_state_entity="sensor.wash_state",
                                dishwasher_connection_entity="sensor.wash_connection")
    hass.states.set("sensor.wash_state", "Running")
    hass.states.set("sensor.wash_connection", "Connected")
    state = runtime.states["a"]
    state.on, state.owned, state.available = True, owned, True
    state.target_w = state.measured_w = 2000
    runtime._dishwasher_unmetered_reserve = 2000
    assert not runtime.dishwasher_priority.view.active_ids
    monkeypatch.setattr(runtime, "heat_pump_increase_allowed", lambda: (True, ""), raising=False)

    sent = await runtime.dhw.tick(time.monotonic(), grid, True, 0, local_now=DAY)

    assert sent is allowed
    assert runtime.dhw.reading.luxury_allowed is allowed
    allocation = runtime.dhw.execution["priority_allocation"]
    assert allocation["unmetered_aeg_reserve_w"] == 2000
    assert allocation["usable_surplus_w"] == -grid - 2150
    assert all(call[1] == "set_temperature" for call in hass.services.calls)
    if allowed:
        assert hass.services.calls[-1][2]["temperature"] == 60


@pytest.mark.asyncio
async def test_nonpreferred_unknown_running_wash_blocks_extra_without_stopping_cycle(monkeypatch):
    runtime, hass = setup()
    runtime.configs["a"]["kind"] = "dishwasher"
    state = runtime.states["a"]
    state.on, state.owned, state.available = True, False, False
    runtime.source_isolated_devices["a"] = {"reserve_w": 2000, "reason": "Bron ontbreekt"}
    monkeypatch.setattr(runtime, "heat_pump_increase_allowed", lambda: (True, ""), raising=False)

    assert not await tick(runtime)

    assert not runtime.dhw.reading.luxury_allowed
    assert "lopende afwascyclus" in runtime.dhw.reading.luxury_reason
    assert not hass.services.calls and state.on
