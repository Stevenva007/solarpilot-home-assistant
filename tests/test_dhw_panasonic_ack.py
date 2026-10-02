"""Regression coverage for delayed Panasonic target acknowledgement."""
from datetime import datetime, timezone
from types import SimpleNamespace
import time as system_time

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot import dhw_runtime
from test_dhw_runtime import setup, updates


NIGHT = datetime(2026, 9, 22, 2)


def _platform(monkeypatch, name, config_entry_id=None):
    registry = SimpleNamespace(
        async_get=lambda _entity_id: SimpleNamespace(
            platform=name, config_entry_id=config_entry_id),
        async_get_entity_id=lambda *_args: None,
    )
    monkeypatch.setattr(er, "async_get", lambda _hass: registry)


def _report(hass, target, wall):
    """Publish a target with a deterministic HA arrival timestamp."""
    updates(hass, "water_heater.boiler", temperature=target)
    state = hass.states.get("water_heater.boiler")
    stamp = datetime.fromtimestamp(wall, timezone.utc)
    state.last_updated = stamp
    state.last_reported = stamp


async def _tick_at(runtime, monotonic):
    return await runtime.dhw.tick(monotonic, 1000, True, 0, True, NIGHT)


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_domain", ["panasonic_cc", "aquarea"])
async def test_panasonic_optimistic_target_waits_for_later_observation(
        monkeypatch, adapter_domain):
    _platform(monkeypatch, adapter_domain)
    wall = [system_time.time()]
    monkeypatch.setattr(dhw_runtime.time, "time", lambda: wall[0])
    runtime, hass = setup()
    updates(hass, "water_heater.boiler", temperature=55)
    runtime.dhw.owned_target = 55

    await runtime.dhw._send(100, 50, False, "eigen terugval")
    issued_wall = runtime.dhw.pending["issued_wall"]
    assert runtime.dhw.pending["ack_poll_min_s"] == 10

    # The command-side/optimistic HA observation is not a device ACK.
    _report(hass, 50, issued_wall + 0.01)
    wall[0] = issued_wall + 1
    await _tick_at(runtime, 101)
    assert runtime.dhw.pending and runtime.dhw.last_success is None

    # Merely waiting ten seconds cannot turn that same old observation into an ACK.
    wall[0] = issued_wall + 11
    await _tick_at(runtime, 111)
    assert runtime.dhw.pending and runtime.dhw.last_success is None

    # A later poll that still reports the previous owned target remains ambiguous
    # and must neither ACK nor be called a manual override while a command is pending.
    _report(hass, 55, wall[0])
    await _tick_at(runtime, 111.1)
    assert runtime.dhw.pending and not runtime.dhw.manual_hold
    assert len(hass.services.calls) == 1

    # Only a later matching HA observation may complete the journalled command.
    wall[0] = issued_wall + 12
    _report(hass, 50, wall[0])
    await _tick_at(runtime, 112)
    assert runtime.dhw.pending is None and runtime.dhw.owned_target == 50
    assert runtime.dhw.last_success["confirmation"] == "delayed_ha_state"
    assert len(hass.services.calls) == 1


@pytest.mark.asyncio
async def test_panasonic_release_does_not_drop_ownership_on_optimistic_echo(monkeypatch):
    _platform(monkeypatch, "panasonic_cc")
    wall = [system_time.time()]
    monkeypatch.setattr(dhw_runtime.time, "time", lambda: wall[0])
    runtime, hass = setup()
    runtime.mode = "paused"
    updates(hass, "water_heater.boiler", temperature=55)
    runtime.dhw.owned_target = 55

    await runtime.dhw._send(200, 50, True, "vrijgave")
    issued_wall = runtime.dhw.pending["issued_wall"]
    _report(hass, 50, issued_wall + 0.01)
    wall[0] = issued_wall + 1
    await _tick_at(runtime, 201)
    assert runtime.dhw.pending and runtime.dhw.busy

    wall[0] = issued_wall + 11
    _report(hass, 55, wall[0])
    await _tick_at(runtime, 211)
    assert runtime.dhw.pending and runtime.dhw.busy
    assert not runtime.dhw.manual_hold and runtime.dhw.last_success is None

    wall[0] = issued_wall + 12
    _report(hass, 50, wall[0])
    await _tick_at(runtime, 212)
    assert runtime.dhw.pending is None and runtime.dhw.owned_target is None
    assert runtime.dhw.last_success["confirmation"] == "delayed_ha_state"


@pytest.mark.asyncio
async def test_non_panasonic_adapter_keeps_existing_single_report_ack(monkeypatch):
    _platform(monkeypatch, "other_water_heater")
    wall = [system_time.time()]
    monkeypatch.setattr(dhw_runtime.time, "time", lambda: wall[0])
    runtime, hass = setup()
    updates(hass, "water_heater.boiler", temperature=55)
    runtime.dhw.owned_target = 55

    await runtime.dhw._send(300, 50, False, "generieke terugval")
    assert runtime.dhw.pending["ack_poll_min_s"] == 0
    wall[0] += 1
    await _tick_at(runtime, 301)
    assert runtime.dhw.pending is None and runtime.dhw.owned_target == 50
    assert runtime.dhw.last_success["confirmation"] == "ha_state"


@pytest.mark.asyncio
async def test_aquarea_config_entry_domain_is_exact_adapter_fallback(monkeypatch):
    _platform(monkeypatch, "forwarded_water_heater", config_entry_id="aquarea-entry")
    runtime, hass = setup()
    hass.config_entries = SimpleNamespace(async_get_entry=lambda entry_id: (
        SimpleNamespace(domain="aquarea") if entry_id == "aquarea-entry" else None))

    await runtime.dhw._send(350, 50, False, "exact config-entry fallback")

    assert runtime.dhw.pending["ack_poll_min_s"] == 10
    overview = runtime.dhw.overview()
    assert overview["target_adapter_domains"] == ["aquarea", "forwarded_water_heater"]
    assert overview["ack_poll_min_s"] == 10
    assert overview["ack_poll_min_unit"] == "s"
    assert overview["ack_confirmation_contract"] == "later_ha_report_at_or_after_adapter_delay"


@pytest.mark.asyncio
async def test_generic_config_entry_domain_never_gets_panasonic_delay(monkeypatch):
    _platform(monkeypatch, "generic_water_heater", config_entry_id="generic-entry")
    runtime, hass = setup()
    hass.config_entries = SimpleNamespace(async_get_entry=lambda entry_id: (
        SimpleNamespace(domain="other_cloud") if entry_id == "generic-entry" else None))

    await runtime.dhw._send(360, 50, False, "generic adapter")

    assert runtime.dhw.pending["ack_poll_min_s"] == 0
    overview = runtime.dhw.overview()
    assert overview["target_adapter_domains"] == ["generic_water_heater", "other_cloud"]
    assert overview["ack_poll_min_s"] == 0
    assert overview["ack_poll_min_unit"] == "s"
    assert overview["ack_confirmation_contract"] == "fresh_ha_report_after_command"


def test_missing_registry_row_fails_to_generic_without_name_guessing(monkeypatch):
    registry = SimpleNamespace(async_get=lambda _entity_id: None)
    monkeypatch.setattr(er, "async_get", lambda _hass: registry)
    runtime, _hass = setup()

    assert runtime.dhw._entity_integration_domains("water_heater.boiler") == frozenset()
    assert runtime.dhw._ack_poll_min_s() == 0


@pytest.mark.parametrize("adapter_domain,delay,contract", [
    ("aquarea", 10, "later_ha_report_at_or_after_adapter_delay"),
    ("panasonic_cc", 10, "later_ha_report_at_or_after_adapter_delay"),
    ("other_cloud", 0, "fresh_ha_report_after_command"),
])
def test_overview_reports_exact_adapter_ack_contract(
        monkeypatch, adapter_domain, delay, contract):
    entry_id = f"{adapter_domain}-entry"
    _platform(monkeypatch, adapter_domain, config_entry_id=entry_id)
    runtime, hass = setup()
    hass.config_entries = SimpleNamespace(async_get_entry=lambda value: (
        SimpleNamespace(domain=adapter_domain) if value == entry_id else None))

    overview = runtime.dhw.overview()

    assert overview["target_adapter_domains"] == [adapter_domain]
    assert overview["ack_poll_min_s"] == delay
    assert overview["ack_poll_min_unit"] == "s"
    assert overview["ack_confirmation_contract"] == contract


@pytest.mark.asyncio
async def test_real_change_after_delayed_panasonic_ack_still_latches_hold(monkeypatch):
    _platform(monkeypatch, "panasonic_cc")
    wall = [system_time.time()]
    monkeypatch.setattr(dhw_runtime.time, "time", lambda: wall[0])
    runtime, hass = setup()

    await runtime.dhw._send(400, 50, False, "eigen doel")
    issued_wall = runtime.dhw.pending["issued_wall"]
    wall[0] = issued_wall + 11
    _report(hass, 50, wall[0])
    await _tick_at(runtime, 411)
    assert runtime.dhw.owned_target == 50 and not runtime.dhw.manual_hold

    wall[0] = issued_wall + 12
    _report(hass, 55, wall[0])
    await _tick_at(runtime, 412)
    assert runtime.dhw.owned_target is None and runtime.dhw.manual_hold
    assert "wijkt af" in runtime.dhw.status
    assert "handmatig" not in runtime.dhw.status.casefold()
    assert len(hass.services.calls) == 1

    await _tick_at(runtime, 413)
    assert "uit voorzorg" in runtime.dhw.status
    assert "handmatig" not in runtime.dhw.status.casefold()
    assert len(hass.services.calls) == 1

    # A matching value later does not silently clear a latched review/hold.
    wall[0] = issued_wall + 14
    _report(hass, 50, wall[0])
    await _tick_at(runtime, 414)
    assert runtime.dhw.manual_hold and runtime.dhw.owned_target is None
    assert len(hass.services.calls) == 1


@pytest.mark.asyncio
async def test_panasonic_without_later_matching_observation_faults_without_retry(monkeypatch):
    _platform(monkeypatch, "panasonic_cc")
    wall = [system_time.time()]
    monkeypatch.setattr(dhw_runtime.time, "time", lambda: wall[0])
    runtime, hass = setup()

    await runtime.dhw._send(500, 50, False, "eigen doel")
    issued_wall = runtime.dhw.pending["issued_wall"]
    _report(hass, 50, issued_wall + 0.01)
    wall[0] = issued_wall + runtime.dhw.settings["ack_timeout_s"] + 1
    await _tick_at(runtime, 500 + runtime.dhw.settings["ack_timeout_s"] + 1)
    assert runtime.dhw.pending is None and runtime.dhw.fault
    actuator_calls = [call for call in hass.services.calls if call[0] == "water_heater"]
    assert len(actuator_calls) == 1

    await _tick_at(runtime, 500 + runtime.dhw.settings["ack_timeout_s"] + 2)
    assert runtime.dhw.fault
    assert len([call for call in hass.services.calls if call[0] == "water_heater"]) == 1
