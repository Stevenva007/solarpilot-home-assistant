"""Real tick routes wait for battery feedback before new load commitments."""
import time

import pytest

from custom_components.solar_pilot.battery_runtime import BatteryFleetManager
from custom_components.solar_pilot import battery_runtime
from test_battery_runtime import setup_battery
from test_dishwasher_app31 import configured, move, ready
from test_house_runtime import setup as setup_house, tick as house_tick
from test_runtime import build
from test_thermal_runtime import setup_climate


def attach_battery(runtime, hass):
    source, source_hass = setup_battery(
        global_control=True, profile_control=True, exclusive=True)
    for key in ("battery_fleet", "batteries"):
        runtime.entry.options[key] = source.entry.options[key]
    for entity in ("sensor.bat_soc", "sensor.bat_power", "number.bat_setpoint"):
        obj = source_hass.states.get(entity)
        hass.states.set(entity, obj.state, obj.attributes)
    runtime.battery_fleet = BatteryFleetManager(runtime)
    # Timing delays have their own regression coverage. These cases isolate
    # serialization and require an actual newer grid report before resuming.
    runtime.settings["settle_s"] = 0


def refresh_grid(hass):
    obj = hass.states.get("sensor.grid")
    hass.states.set("sensor.grid", obj.state, obj.attributes)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["switch", "number"])
async def test_pending_battery_defers_new_ordinary_start_until_ack(kind):
    runtime, hass = build(kind=kind)
    attach_battery(runtime, hass)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    await runtime.battery_fleet._send("bat1", -1800)
    hass.services.calls.clear()

    await runtime.tick()

    assert runtime.battery_fleet.busy
    assert runtime.pending is None
    assert hass.states.get("switch.load").state == "off"
    assert hass.services.calls == []
    # Confirm only the battery command; the deferred load remains eligible.
    hass.states.set("sensor.bat_power", -1800, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert not runtime.battery_fleet.busy
    refresh_grid(hass)
    await runtime.tick()
    assert runtime.pending and runtime.pending["id"] == "a"
    assert hass.states.get("switch.load").state == "on"
    assert len([call for call in hass.services.calls if call[:2] == ("switch", "turn_on")]) == 1


@pytest.mark.asyncio
async def test_pending_battery_defers_existing_number_load_increase_until_ack():
    runtime, hass = build(kind="number")
    attach_battery(runtime, hass)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.load", 1380, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", -5000, {"unit_of_measurement": "W"})
    state = runtime.states["a"]
    state.owned = state.on = True
    state.target_w = 1380
    state.last_on = time.monotonic() - 60
    await runtime.battery_fleet._send("bat1", -1800)
    hass.services.calls.clear()

    await runtime.tick()

    assert runtime.battery_fleet.busy
    assert runtime.pending is None
    assert hass.states.get("number.amps").state == "6"
    assert hass.services.calls == []
    hass.states.set("sensor.bat_power", -1800, {"unit_of_measurement": "W"})
    await runtime.tick()
    refresh_grid(hass)
    await runtime.tick()
    writes = [call for call in hass.services.calls if call[:2] == ("number", "set_value")]
    assert len(writes) == 1
    assert writes[0][2]["entity_id"] == "number.amps"
    assert writes[0][2]["value"] > 6


@pytest.mark.asyncio
async def test_pending_battery_defers_due_aeg_start_and_preserves_one_shot_permission(monkeypatch):
    runtime, hass, cfg, wall = configured(monkeypatch)
    ready(runtime, hass, cfg, wall)
    attach_battery(runtime, hass)
    hass.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    move(hass, wall, "2026-09-29T13:00")
    request = dict(runtime.dishwasher_app.data["a"]["request"])
    await runtime.battery_fleet._send("bat1", -1800)
    hass.services.calls.clear()

    await runtime.tick()

    assert runtime.battery_fleet.busy
    assert runtime.pending is None
    saved_request = runtime.dishwasher_app.data["a"]["request"]
    assert {key: saved_request[key] for key in request} == request
    assert not runtime.dishwasher.tickets["a"].get("attempted")
    assert not [call for call in hass.services.calls if call[0] == "button"]
    wall[0] += 1
    hass.states.set("sensor.bat_power", -1800, {"unit_of_measurement": "W"})
    await runtime.tick()
    refresh_grid(hass)
    await runtime.tick()
    assert runtime.pending and "deadline" in runtime.pending["reason"]
    assert [call for call in hass.services.calls if call[0] == "button"] == [
        ("button", "press", {"entity_id": "button.dw_start"}),
    ]
    # A native Running report consumes this START; no battery ACK or later tick
    # can create a second START or interrupt the protected cycle.
    wall[0] += 1
    hass.states.set("sensor.dw_phase", "Running")
    await runtime.tick()
    await runtime.tick()
    assert len([call for call in hass.services.calls if call[0] == "button"]) == 1
    assert not [call for call in hass.services.calls if call[0] == "switch"]


@pytest.mark.asyncio
async def test_pending_battery_defers_new_wallbox_handover_until_ack(monkeypatch):
    runtime, hass, clock = setup_house(monkeypatch)
    # Battery intent and the house loop must share the simulated clock. A real
    # monotonic issue time cannot be compared with the house's fixed 10000 s
    # uptime; otherwise this scenario depends on the test machine's uptime.
    monkeypatch.setattr(battery_runtime, "time", clock)
    attach_battery(runtime, hass)
    await runtime.battery_fleet._send("bat1", -1800)
    hass.services.calls.clear()

    for second in range(0, 31, 5):
        await house_tick(runtime, hass, clock, second)

    assert runtime.battery_fleet.busy
    assert runtime.pending is None and runtime.handover is None
    assert hass.services.calls == []
    hass.states.set("sensor.bat_power", -1800, {"unit_of_measurement": "W"})
    await house_tick(runtime, hass, clock, 35)
    assert not runtime.battery_fleet.busy
    await house_tick(runtime, hass, clock, 40)
    assert runtime.pending and runtime.handover
    assert runtime.handover.borrowed_w == 1000
    assert hass.services.calls == [("switch", "turn_on", {"entity_id": "switch.load"})]
    assert not [call for call in hass.services.calls if call[2].get("entity_id", "").startswith(("select.ev", "number.ev"))]


@pytest.mark.asyncio
async def test_pending_battery_does_not_prevent_safe_flexible_load_reduction():
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    runtime.settings["settle_s"] = 0
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.grid", 2500, {"unit_of_measurement": "W"})
    state = runtime.states["a"]
    state.owned = state.on = True
    state.target_w = 1000
    state.last_on = time.monotonic() - 60
    await runtime.battery_fleet._send("bat1", -1800)
    hass.services.calls.clear()

    await runtime.tick()

    assert runtime.battery_fleet.busy
    assert runtime.pending and runtime.pending["watts"] == 0
    assert hass.services.calls == [("switch", "turn_off", {"entity_id": "switch.load"})]


@pytest.mark.asyncio
async def test_pending_battery_defers_climate_removal_release_until_ack():
    runtime, hass = setup_climate(control=True, mode="off")
    attach_battery(runtime, hass)
    runtime.smart_climate.state.expected_mode["climate.home"] = "off"
    await runtime.battery_fleet._send("bat1", -1800)
    hass.services.calls.clear()

    await runtime.prepare_removal()

    assert runtime.battery_fleet.busy
    assert not runtime.smart_climate.busy
    assert hass.states.get("climate.home").state == "off"
    assert not [call for call in hass.services.calls if call[0] == "climate"]
    hass.states.set("sensor.bat_power", -1800, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert not runtime.battery_fleet.busy
    await runtime.tick()
    await runtime.tick()
    assert runtime.smart_climate.busy
    assert [call for call in hass.services.calls if call[0] == "climate"] == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]
    assert hass.states.get("climate.salon").state == "off"


@pytest.mark.asyncio
async def test_battery_power_ack_does_not_reuse_grid_report_from_before_charge_command():
    runtime, hass = build()
    attach_battery(runtime, hass)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    grid_stamp = hass.states.get("sensor.grid").last_reported.timestamp()
    await runtime.battery_fleet._send("bat1", -1800)
    assert grid_stamp < runtime.battery_fleet.state.pending["issued_wall"]
    hass.services.calls.clear()
    await runtime.tick()
    hass.states.set("sensor.bat_power", -1800, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert not runtime.battery_fleet.busy

    await runtime.tick()

    # Battery consumption changed; its ACK does not update the P1 report or
    # prove that the former 2500 W export is still available for another load.
    assert hass.states.get("sensor.grid").last_reported.timestamp() == grid_stamp
    assert runtime.pending is None
    assert hass.services.calls == []
    refresh_grid(hass)
    await runtime.tick()
    assert hass.services.calls == [("switch", "turn_on", {"entity_id": "switch.load"})]
