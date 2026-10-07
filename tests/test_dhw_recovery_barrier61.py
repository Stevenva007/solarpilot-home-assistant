"""Fresh P1 after automatic boiler reconciliation protects every new start.

Uses the real EMS, planners and controller managers with fictitious HA API
doubles. Neither reconciliation nor an unchanged P1 report is a power lease.
"""
from datetime import datetime, timezone
from copy import deepcopy
from types import SimpleNamespace
import time

import pytest

from custom_components.solar_pilot.dhw import DHW_DEFAULTS
from custom_components.solar_pilot.dhw_runtime import DHWManager
from test_runtime import build
from test_battery_runtime import setup_battery
from test_dishwasher_app31 import configured, ready, move
from test_automatic_climate_runtime54 import automatic


def freeze_reports(monkeypatch, hass):
    wall = [float(int(time.time()))]
    monkeypatch.setattr(time, "time", lambda: wall[0])
    original = hass.states.set

    def report(entity_id, state, attrs=None, age=0, reported_age=None):
        original(entity_id, state, attrs, age, reported_age)
        obj = hass.states.get(entity_id)
        obj.last_updated = datetime.fromtimestamp(wall[0] - age, timezone.utc)
        obj.last_reported = datetime.fromtimestamp(
            wall[0] - (age if reported_age is None else reported_age), timezone.utc)

    hass.states.set = report
    for entity_id, obj in list(hass.states.data.items()):
        report(entity_id, obj.state, obj.attributes)
    return wall


def attach_dhw(runtime, hass):
    if not getattr(hass, "config", None):
        hass.config = SimpleNamespace(time_zone="Europe/Brussels")
    hass.config.units = SimpleNamespace(temperature_unit="°C")
    runtime.entry.options["dhw"] = {
        **DHW_DEFAULTS, "enabled": True, "safety_confirmed": True,
        "target_entity": "water_heater.tank", "temperature_entity": "sensor.tank",
        "hygiene_schedule_enabled": False, "night_enabled": False,
        "surplus_threshold_w": 10000, "rise_delay_s": 0,
    }
    hass.states.set("water_heater.tank", "heat_pump", {
        "temperature": 50, "current_temperature": 50, "temperature_unit": "°C",
        "min_temp": 30, "max_temp": 65, "target_temp_step": .5,
        "supported_features": 1, "hvac_action": "idle",
    })
    hass.states.set("sensor.tank", 50, {"unit_of_measurement": "°C"})
    hass.states.set("sensor.pv", 5000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", -2000, {"unit_of_measurement": "W"})
    runtime.settings.update(pv_entity="sensor.pv", settle_s=0, filter_s=0)
    runtime.dhw = DHWManager(runtime)
    runtime.mode = "solar"


def physical_calls(hass):
    return [call for call in hass.services.calls if call[0] not in (
        "persistent_notification", "weather")]


def claimant(monkeypatch, kind):
    if kind == "dishwasher":
        runtime, hass, config, wall = configured(monkeypatch, "2026-10-07T12:59")
        ready(runtime, hass, config, wall)
        move(hass, wall, "2026-10-07T13:00")
        assert runtime.dishwasher_app.due(config, wall[0])
    elif kind == "climate":
        runtime, hass, _manager, wall = automatic(
            monkeypatch, temp=19.5, outside=14, zones=["climate.home"])
    elif kind == "battery":
        runtime, hass = setup_battery(
            global_control=True, profile_control=True, exclusive=True)
        wall = freeze_reports(monkeypatch, hass)
    else:
        runtime, hass = build()
        runtime.device_modes["a"] = "auto"
        wall = freeze_reports(monkeypatch, hass)
    attach_dhw(runtime, hass)
    return runtime, hass, wall


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["ordinary", "dishwasher", "climate", "battery"])
async def test_reconciliation_and_old_p1_do_not_start_but_new_p1_releases_each_claimant(
        monkeypatch, kind):
    runtime, hass, wall = claimant(monkeypatch, kind)
    runtime.dhw.pending = {
        "target": 50, "issued": time.monotonic() - 181,
        "issued_wall": wall[0] - 181, "ack_poll_min_s": 10, "release": False,
    }
    await runtime.dhw._mark_fault(
        "Boileropdracht nog niet bevestigd; automatische controle loopt",
        now=time.monotonic())
    hass.services.calls.clear()
    original_command_clock = runtime.last_issued, runtime.last_issued_wall

    # A genuinely later target report can settle the failed command. The P1
    # report still precedes that reconciliation, so it cannot fund a new start.
    wall[0] += 1
    obj = hass.states.get("water_heater.tank")
    hass.states.set("water_heater.tank", obj.state, obj.attributes)
    await runtime._tick()
    assert not runtime.dhw.fault and runtime.dhw.automatic_recovery is None
    assert runtime.dhw.recovery_barrier and runtime.dhw.blocks_increase
    assert physical_calls(hass) == []
    assert (runtime.last_issued, runtime.last_issued_wall) == original_command_clock

    await runtime._tick()
    assert runtime.dhw.recovery_barrier
    assert physical_calls(hass) == []

    wall[0] += 1
    hass.states.set("sensor.grid", -2000, {"unit_of_measurement": "W"})
    await runtime._tick()
    assert not runtime.dhw.recovery_barrier
    assert not runtime.dhw.blocks_increase
    calls = physical_calls(hass)
    expected_domain = {
        "ordinary": "switch", "dishwasher": "button",
        "climate": "climate", "battery": "number",
    }[kind]
    assert calls and all(call[0] == expected_domain for call in calls)
    assert not any(call[0] == "water_heater" for call in calls)


@pytest.mark.asyncio
async def test_recovery_p1_barrier_does_not_prevent_safe_release_of_an_owned_load(monkeypatch):
    runtime, hass, wall = claimant(monkeypatch, "ordinary")
    hass.states.set("switch.load", "on")
    state = runtime.states["a"]
    state.on = state.owned = True
    state.target_w = 1000
    state.last_on = time.monotonic() - 1000
    runtime.dhw._recovery_settled_wall = wall[0]
    runtime.mode = "paused"

    await runtime._tick()

    assert runtime.dhw.recovery_barrier
    assert physical_calls(hass) == [
        ("switch", "turn_off", {"entity_id": "switch.load"})]
    assert runtime.pending and runtime.pending["watts"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["unavailable", "restored", "wrong_unit", "stale"])
async def test_unreliable_new_p1_does_not_release_the_reconciliation_barrier(monkeypatch, bad):
    runtime, hass, wall = claimant(monkeypatch, "ordinary")
    runtime.dhw._recovery_settled_wall = wall[0]
    wall[0] += 1
    attrs = {"unit_of_measurement": "W"}
    state, age = -2000, 0
    if bad == "unavailable":
        state = "unavailable"
    elif bad == "restored":
        attrs["restored"] = True
    elif bad == "wrong_unit":
        attrs["unit_of_measurement"] = "kWh"
    else:
        age = 3600
    hass.states.set("sensor.grid", state, attrs, age=age)

    await runtime._tick()

    assert runtime.dhw.recovery_barrier
    assert physical_calls(hass) == []


@pytest.mark.asyncio
async def test_restored_uncertain_release_prevents_removal_until_later_confirmation(monkeypatch):
    runtime, hass, wall = claimant(monkeypatch, "ordinary")
    runtime.dhw.pending = {
        "target": 50, "issued": time.monotonic() - 181,
        "issued_wall": wall[0] - 181, "ack_poll_min_s": 10, "release": True,
    }
    await runtime.dhw._mark_fault(
        "Boileropdracht nog niet bevestigd; automatische controle loopt",
        now=time.monotonic())
    saved = runtime.dhw.snapshot()
    restored = DHWManager(runtime)
    restored.restore(saved)
    runtime.dhw = restored
    runtime.mode = "paused"
    hass.services.calls.clear()

    assert restored.pending is None and restored.owned_target is None
    assert restored.automatic_recovery
    assert restored.busy
    assert not runtime.editable
    assert not runtime.removal_overview()["ready"]

    wall[0] += 1
    obj = hass.states.get("water_heater.tank")
    hass.states.set("water_heater.tank", obj.state, obj.attributes)
    await restored.tick(time.monotonic(), -2000, True, 0)

    assert not restored.busy and not restored.fault
    assert runtime.removal_overview()["ready"]
    assert physical_calls(hass) == []


@pytest.mark.asyncio
async def test_saved_user_pause_with_recoverable_boiler_fault_resumes_without_manual_ack(monkeypatch):
    runtime, hass, wall = claimant(monkeypatch, "ordinary")
    runtime.entry.options["_beta37_activation_profile"] = 1
    runtime.dhw.pending = {
        "target": 50, "issued": time.monotonic() - 181,
        "issued_wall": wall[0] - 181, "ack_poll_min_s": 10, "release": False,
    }
    await runtime.dhw._mark_fault(
        "Boileropdracht nog niet bevestigd; automatische controle loopt",
        now=time.monotonic())
    saved = deepcopy(runtime._snapshot())
    saved.update(mode="paused", pause_cause="user", auto_resume_after_restart=True)
    runtime.store.data = saved
    hass.services.calls.clear()

    await runtime.start()

    assert runtime.mode == "solar" and runtime.pause_cause == ""
    assert runtime.dhw.automatic_recovery and runtime.dhw.blocks_increase
    assert physical_calls(hass) == []

    wall[0] += 1
    obj = hass.states.get("water_heater.tank")
    hass.states.set("water_heater.tank", obj.state, obj.attributes)
    await runtime.tick()
    assert not runtime.dhw.fault and runtime.dhw.recovery_barrier
    assert runtime.mode == "solar" and runtime.pause_cause != "command_fault"
    assert physical_calls(hass) == []

    wall[0] += 1
    hass.states.set("sensor.grid", -2000, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert physical_calls(hass) == [
        ("switch", "turn_on", {"entity_id": "switch.load"})]


@pytest.mark.asyncio
async def test_saved_pause_with_unrecognised_boiler_fault_keeps_protected_pause(monkeypatch):
    runtime, hass, wall = claimant(monkeypatch, "ordinary")
    runtime.entry.options["_beta37_activation_profile"] = 1
    runtime.dhw.fault = "Onbekende fout in boilerregeling"
    saved = deepcopy(runtime._snapshot())
    saved.update(mode="paused", pause_cause="user", auto_resume_after_restart=True)
    runtime.store.data = saved

    await runtime.start()
    assert runtime.mode == "paused" and runtime.pause_cause == "command_fault"
    assert runtime.dhw.fault and runtime.dhw.automatic_recovery is None

    wall[0] += 1
    obj = hass.states.get("water_heater.tank")
    hass.states.set("water_heater.tank", obj.state, obj.attributes)
    hass.states.set("sensor.grid", -2000, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.mode == "paused" and runtime.pause_cause == "command_fault"
    assert physical_calls(hass) == []
