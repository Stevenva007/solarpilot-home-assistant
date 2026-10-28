"""Unknown EV telemetry neither blocks measured residual solar nor credits it."""
from copy import deepcopy
from dataclasses import replace
import time

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from test_sg_budget_priority62 import configured


def unknown_wallbox(*, issue="missing_power", export=5000):
    r, h = configured(export=export)
    r.wallbox_settings.update(enabled=True, power_entity="sensor.public_ev_power",
        status_entity="sensor.public_ev_status", mode_entity="select.public_ev_solar")
    r.wallbox_guard = r._make_wallbox_guard()
    r.sg_wallbox_guard = r._make_sg_wallbox_guard()
    h.states.set("sensor.public_ev_status", "Charging")
    h.states.set("select.public_ev_solar", "full_solar")
    h.states.set("sensor.public_hp", "unavailable", {"unit_of_measurement": "W"})
    if issue == "stale_power":
        h.states.set("sensor.public_ev_power", 9000, {"unit_of_measurement": "W"}, age=301)
    elif issue == "unknown_demand":
        h.states.set("sensor.public_ev_power", 2200, {"unit_of_measurement": "W"})
        h.states.set("sensor.public_ev_status", "Unrecognised native status")
    elif issue == "stale_status":
        h.states.set("sensor.public_ev_power", 2200, {"unit_of_measurement": "W"})
        h.states.set("sensor.public_ev_status", "Charging", age=301)
    elif issue != "missing_power":
        raise AssertionError(issue)
    return r, h


@pytest.mark.parametrize("issue", ["missing_power", "stale_power", "unknown_demand", "stale_status"])
def test_sg_uses_actual_site_export_when_wallbox_telemetry_is_unknown(issue):
    r, h = unknown_wallbox(issue=issue)
    settings = deepcopy(r.wallbox_settings)
    reading = r._wallbox_reading()
    assert reading.valid is False
    if issue in ("missing_power", "stale_power"):
        assert reading.power_w is None  # Missing EV power is never measured zero.
    r.wallbox_guard.update(time.monotonic(), reading, -5000, 150)
    # Reproduce a remembered zero allowance from an earlier charging wait.
    r.sg_wallbox_guard.result = replace(r.sg_wallbox_guard.result,
        state="unavailable", block_increase=True, max_increase_w=0)

    budget = sg_solar_budget(r)
    assert budget["valid"] and budget["available_w"] == 4850
    assert budget["eligible_w"] == 4850 and budget["hp_solar_w"] == 0
    assert budget["hp_power_w"] is None
    assert r.heat_pump_increase_allowed()[0]
    assert r.priority_board.sg_priority_allowed(time.monotonic())
    assert r.sg_dispatch_allowed(automatic=True)
    assert r.sg_wallbox_guard.result.state == "unavailable"
    assert r.sg_wallbox_guard.result.max_increase_w is None
    assert not r.sg_wallbox_guard.result.block_increase
    assert not r.sg_wallbox_guard.result.release_flexible
    current_reading = r.sg_wallbox_guard.reading
    assert current_reading == replace(reading, age_s=current_reading.age_s)
    assert r.wallbox_settings == settings and h.services.calls == []


def test_unknown_ev_cannot_turn_its_old_watts_into_solar_credit_or_physical_room():
    r, h = unknown_wallbox(issue="stale_power", export=2000)
    budget = sg_solar_budget(r)
    assert budget["available_w"] == budget["eligible_w"] == 1850
    assert not r.heat_pump_increase_allowed()[0]
    assert not r.sg_dispatch_allowed(automatic=True)
    # A vanished old EV report cannot create a hypothetical 9 kW takeover.
    h.states.set("sensor.public_ev_power", "unavailable", {"unit_of_measurement": "W"})
    assert sg_solar_budget(r) == budget
    assert not r.sg_dispatch_allowed(automatic=True)
    assert h.services.calls == []


@pytest.mark.parametrize("guard", ["grid_stale", "pv_stale", "battery_discharge",
    "phase_limit", "quarter_unknown", "cooling_unconfirmed", "actuator_conflict"])
def test_wallbox_independence_preserves_real_sg_safety_guards(guard):
    r, h = unknown_wallbox()
    if guard in ("grid_stale", "pv_stale"):
        entity = "sensor.grid" if guard == "grid_stale" else "sensor.public_pv"
        obj = h.states.get(entity)
        h.states.set(entity, obj.state, obj.attributes, age=121)
    elif guard == "battery_discharge":
        r.settings["battery_power_entity"] = "sensor.public_battery"
        h.states.set("sensor.public_battery", 1000, {"unit_of_measurement": "W"})
    elif guard == "phase_limit":
        r.phase_settings.update(enabled=True, control_starts=True, limit_w=3200,
            phase_1_entity="sensor.public_phase1", phase_2_entity="sensor.public_phase2",
            phase_3_entity="sensor.public_phase3")
        for entity in ("sensor.public_phase1", "sensor.public_phase2", "sensor.public_phase3"):
            h.states.set(entity, 1000, {"unit_of_measurement": "W"})
    elif guard == "quarter_unknown":
        r.capacity_settings.update(enabled=True, average_demand_entity="sensor.public_quarter")
    elif guard == "cooling_unconfirmed":
        r.sg_boost.settings.update(profile="general", profile_confirmed=True,
            zone_entities=["climate.public_room"], cooling_protection_confirmed=False)
        h.states.set("climate.public_room", "cool", {"hvac_action": "cooling"})
    elif guard == "actuator_conflict":
        r.configs["a"]["control_entity"] = r.sg_boost.settings["entity_id"]
    assert not r.sg_dispatch_allowed(automatic=True)
    assert h.services.calls == []


def test_waiting_ev_with_zero_draw_does_not_reserve_actual_solar_export():
    r, h = unknown_wallbox()
    h.states.set("sensor.public_ev_power", 0, {"unit_of_measurement": "W"})
    h.states.set("sensor.public_ev_status", "Waiting for green energy")
    reading = r._wallbox_reading()
    assert reading.valid and reading.demand is True
    r.learning.effective_stable_s = lambda _seconds: 0
    assert r.heat_pump_increase_allowed()[0]
    assert r.sg_dispatch_allowed(automatic=True)
    assert r.sg_wallbox_guard.result.state == "unknown"
    assert sg_solar_budget(r)["ev_solar_w"] == 0
    assert h.services.calls == []


@pytest.mark.asyncio
async def test_unknown_wallbox_remains_read_only_even_when_sg_has_solar_room():
    r, h = unknown_wallbox()
    assert r.heat_pump_increase_allowed()[0]
    with pytest.raises(HomeAssistantError, match="alleen-lezen"):
        await r._call("select.public_ev_solar", "select_option", {"option": "eco_mode"})
    assert h.services.calls == []
