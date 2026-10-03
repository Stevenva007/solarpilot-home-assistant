"""Malformed climate journals cannot restore command ownership unsafely."""
from copy import deepcopy
import json

import pytest

from custom_components.solar_pilot.thermal_runtime import SmartClimateManager
from test_thermal_runtime import setup_climate
from test_thermal_runtime_beta48 import (
    QuietCloudServices, climate_calls, clock, forecast, report, tick,
)


def setup(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=19.5, target=21, mode="off")
    wall = clock(monkeypatch, hass)
    hass.services = QuietCloudServices(hass.states)
    forecast(hass, wall[0])
    return runtime, hass, wall


def journal(wall):
    return {
        "profiles": {"climate.home": {"samples": 633}},
        "expected_mode": {"climate.home": "auto"},
        "manual_off": ["climate.salon"],
        "zone_holds": {"climate.salon": wall + 3600},
        "zone_command_walls": {"climate.home": wall - 30},
        "command_faults": {},
        "cancelled_auto": {},
        "pending_commands": {"climate.home": {
            "mode": "auto", "issued_wall": wall - 30,
            "expires_wall": wall + 150, "context_id": "prior-command",
        }},
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [None, ["invalid journal"]])
async def test_whole_invalid_climate_journal_keeps_unowned_off_without_command(monkeypatch, invalid):
    runtime, hass, wall = setup(monkeypatch)
    manager = SmartClimateManager(runtime)

    manager.restore(invalid)
    await tick(manager, wall[0])

    assert not manager.pending_commands
    assert not manager.state.expected_mode
    assert set(manager.manual_off) == {"climate.home", "climate.salon"}
    assert not climate_calls(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("key", [
    "zone_holds", "zone_command_walls", "command_faults", "pending_commands",
    "cancelled_auto", "manual_off",
])
@pytest.mark.parametrize("invalid", [None, []])
async def test_malformed_manager_field_drops_invalid_shape_without_replaying_command(
        monkeypatch, key, invalid):
    runtime, hass, wall = setup(monkeypatch)
    saved = journal(wall[0])
    saved[key] = invalid
    manager = SmartClimateManager(runtime)

    manager.restore(saved)

    assert manager.state.profiles["climate.home"].samples == 633
    if key == "pending_commands":
        assert "climate.home" not in manager.state.expected_mode
        assert "climate.home" not in manager.pending_commands
        assert manager.zone_holds["climate.home"] > wall[0]
        assert manager.command_faults["climate.home"]
    else:
        assert manager.pending_commands["climate.home"]["mode"] == "auto"
        assert manager.pending_commands["climate.home"]["restart_wall"] == wall[0]
    await tick(manager, wall[0])
    wall[0] += 11
    await tick(manager, wall[0])

    assert not climate_calls(hass)
    assert hass.states.get("climate.home").state == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_row", [
    None, [], {"mode": "heat", "issued_wall": 1},
    {"mode": "off", "issued_wall": -1},
    {"mode": "off", "issued_wall": "invalid time"},
    {"mode": "off", "issued_wall": float("inf")},
])
async def test_invalid_pending_row_quarantines_only_its_zone_and_preserves_valid_siblings(
        monkeypatch, bad_row):
    runtime, hass, wall = setup(monkeypatch)
    manager = SmartClimateManager(runtime)
    manager.settings["zone_entities"].append("climate.bedroom")
    attrs = deepcopy(hass.states.get("climate.home").attributes)
    hass.states.set("climate.bedroom", "off", attrs)
    saved = journal(wall[0])
    valid = saved["pending_commands"]["climate.home"]
    saved["expected_mode"] = {"climate.home": "off", "climate.salon": "auto"}
    saved["pending_commands"] = {"climate.home": bad_row, "climate.salon": valid}
    saved["manual_off"] = ["climate.bedroom"]
    saved["zone_holds"] = {"climate.bedroom": wall[0] + 3600}

    manager.restore(saved)

    assert "climate.home" not in manager.pending_commands
    assert "climate.home" not in manager.state.expected_mode
    assert manager.command_faults["climate.home"]
    assert manager.zone_holds["climate.home"] > wall[0]
    assert "climate.home" in manager.manual_off
    assert "climate.bedroom" in manager.manual_off
    assert manager.zone_holds["climate.bedroom"] == wall[0] + 3600
    assert manager.state.profiles["climate.home"].samples == 633
    assert manager.pending_commands["climate.salon"]["mode"] == "auto"
    assert manager.state.expected_mode["climate.salon"] == "auto"
    await tick(manager, wall[0])

    assert not climate_calls(hass)
    assert manager.pending_commands["climate.salon"]["restart_wall"] == wall[0]


@pytest.mark.asyncio
async def test_valid_pending_restart_waits_for_new_report_without_replaying_auto(monkeypatch):
    runtime, hass, wall = setup(monkeypatch)
    manager = SmartClimateManager(runtime)
    manager.restore(journal(wall[0]))
    pending = manager.pending_commands["climate.home"]
    assert pending["restart_wall"] == wall[0]
    assert pending["expires_wall"] == wall[0] + manager.COMMAND_TIMEOUT_S
    assert pending["context_id"] == "prior-command"
    await tick(manager, wall[0])
    wall[0] += 9
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])
    assert "climate.home" in manager.pending_commands

    wall[0] += 1
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])

    assert "climate.home" not in manager.pending_commands
    assert manager.state.expected_mode["climate.home"] == "auto"
    assert "climate.salon" in manager.manual_off
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_pending_restart_discards_poisoned_extra_fields_and_accepts_later_ack(monkeypatch):
    runtime, hass, wall = setup(monkeypatch)
    saved = journal(wall[0])
    saved["pending_commands"]["climate.home"].update(
        feedback_group=["unhashable legacy group"], injected_metric=float("nan"))
    manager = SmartClimateManager(runtime)

    manager.restore(saved)
    json.dumps(manager.snapshot(), allow_nan=False)
    assert "feedback_group" not in manager.pending_commands["climate.home"]
    assert "injected_metric" not in manager.pending_commands["climate.home"]
    wall[0] += 10
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])

    assert "climate.home" not in manager.pending_commands
    assert not climate_calls(hass)
