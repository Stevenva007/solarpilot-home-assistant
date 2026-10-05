"""Automatic read-only DHW restart reconciliation using HA doubles."""
from datetime import datetime, timezone
from types import SimpleNamespace as NS
import time

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot import dhw_runtime
from custom_components.solar_pilot.dhw_runtime import DHWManager
from test_dhw_runtime import setup, tick, updates


NOW = datetime(2026, 9, 22, 12)


def restart(runtime, *, owned=50, pending=None, **saved):
    data = {**runtime.dhw.snapshot(), "owned_target": owned, "pending": pending, **saved}
    manager = DHWManager(runtime)
    manager.restore(data)
    runtime.dhw = manager
    return manager


def report(hass, target=50, *, wall=None):
    updates(hass, "water_heater.boiler", temperature=target)
    if wall is not None:
        state = hass.states.get("water_heater.boiler")
        state.last_reported = state.last_updated = datetime.fromtimestamp(wall, timezone.utc)


@pytest.mark.asyncio
async def test_clean_confirmed_ownership_recovers_without_target_command():
    runtime, hass = setup()
    manager = restart(runtime)

    assert manager.restart_recovery and not manager.needs_review
    assert not manager.blocks_increase and not manager.pending and manager.owned_target is None
    assert await manager.reconcile_restart(NOW)
    assert manager.restart_recovery is None and manager.owned_target == 50
    assert not manager.needs_review and not manager.manual_hold
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_legacy_clean_review_without_ownership_automatically_recovers():
    runtime, hass = setup()
    manager = restart(runtime, owned=None, needs_review=True)

    assert manager.restart_recovery and not manager.needs_review
    assert await manager.reconcile_restart(NOW)
    assert manager.restart_recovery is None and manager.owned_target is None
    assert not manager.needs_review and not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("entity,state,attrs,age", [
    ("water_heater.boiler", "unavailable", {}, 0),
    ("sensor.water", "unavailable", {}, 0),
    ("water_heater.boiler", "heat_pump", {"restored": True}, 0),
    ("sensor.water", "44", {"restored": True}, 0),
    ("water_heater.boiler", "heat_pump", {}, 301),
    ("sensor.water", "44", {}, 301),
    ("binary_sensor.hygiene", "off", {"restored": True}, 0),
    ("switch.powerful", "off", {"restored": True}, 0),
    ("binary_sensor.hygiene", "unavailable", {}, 0),
    ("switch.powerful", "unavailable", {}, 0),
    ("water_heater.boiler", "heat_pump", {"supported_features": 0}, 0),
    ("water_heater.boiler", "heat_pump", {"target_temp_step": 0}, 0),
    ("sensor.water", "nan", {}, 0),
    ("sensor.water", "44", {"unit_of_measurement": "°F"}, 0),
])
async def test_missing_stale_restored_or_invalid_evidence_only_defers_boiler(
        entity, state, attrs, age):
    runtime, hass = setup()
    manager = restart(runtime)
    original = hass.states.get(entity)
    hass.states.set(entity, state, {**original.attributes, **attrs}, age=age)

    assert not await manager.reconcile_restart(NOW)
    assert manager.restart_recovery and not manager.needs_review
    assert not manager.blocks_increase and not hass.services.calls
    await tick(runtime)
    assert manager.restart_recovery and not hass.services.calls


@pytest.mark.asyncio
async def test_late_valid_target_retries_automatically_on_next_tick():
    runtime, hass = setup()
    manager = restart(runtime)
    attrs = hass.states.get("water_heater.boiler").attributes
    hass.states.set("water_heater.boiler", "unavailable", attrs)
    runtime.mode = "observe"
    await tick(runtime)
    assert manager.restart_recovery

    hass.states.set("water_heater.boiler", "heat_pump", attrs)
    await tick(runtime)

    assert manager.restart_recovery is None and manager.owned_target == 50
    assert not manager.needs_review and not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("saved", [
    {"manual_hold": True},
    {"fault": "Onzekere boileropdracht; controle vereist"},
    {"target_entity": "water_heater.other"},
    {"pending": {"target": "invalid", "issued_wall": 123}},
    {"pending": {"target": 50, "issued_wall": -1}},
    {"pending": {"target": 50, "issued_wall": 999999999999}},
    {"restart_recovery": {"schema": 2, "owned_target": 50}},
    {"restart_recovery": "corrupt journal"},
])
async def test_real_holds_faults_changed_bindings_and_bad_journals_require_review(saved):
    runtime, hass = setup()
    manager = restart(runtime, **saved)

    assert manager.restart_recovery is None and manager.needs_review
    assert not await manager.reconcile_restart(NOW)
    await tick(runtime)
    assert manager.needs_review and not hass.services.calls


@pytest.mark.asyncio
async def test_changed_owned_target_preserves_external_override_without_command():
    runtime, hass = setup()
    manager = restart(runtime, owned=60)

    assert await manager.reconcile_restart(NOW)
    assert manager.restart_recovery is None and manager.manual_hold
    assert manager.owned_target is None and not manager.needs_review
    await tick(runtime)
    assert manager.manual_hold and not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["binary_sensor.hygiene", "switch.powerful"])
async def test_active_manufacturer_or_powerful_guard_yields_without_dropping_protection(guard):
    runtime, hass = setup()
    manager = restart(runtime, owned=60)
    hass.states.set(guard, "on")
    if guard == "binary_sensor.hygiene":
        report(hass, 62)

    assert await manager.reconcile_restart(NOW)
    assert manager.restart_recovery is None and manager.owned_target is None
    assert not manager.manual_hold
    await tick(runtime)
    assert manager.reading.protected and not hass.services.calls


@pytest.mark.asyncio
async def test_native_off_is_not_enabled_by_restart_reconciliation():
    runtime, hass = setup()
    manager = restart(runtime)
    attrs = hass.states.get("water_heater.boiler").attributes
    hass.states.set("water_heater.boiler", "off", attrs)

    assert await manager.reconcile_restart(NOW)
    await tick(runtime)
    assert manager.reading.protected and manager.owned_target is None
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_future_weekly_hygiene_window_is_kept_without_temperature_write():
    runtime, hass = setup(config={'hygiene_schedule_enabled': True})
    manager = restart(runtime, owned=60)

    assert await manager.reconcile_restart(datetime(2026, 9, 21, 12))
    assert manager.restart_recovery is None and manager.owned_target is None
    assert "sterilisatie" in manager.status
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("release", [False, True])
async def test_pending_panasonic_command_requires_new_delayed_report_without_replay(
        monkeypatch, release):
    runtime, hass = setup()
    registry = NS(async_get=lambda entity_id: (
        NS(platform="aquarea") if entity_id == "water_heater.boiler" else None),
        async_get_entity_id=lambda *_args: None)
    monkeypatch.setattr(er, "async_get", lambda _hass: registry)
    stamp = time.time()
    clock = [stamp]
    monkeypatch.setattr(dhw_runtime.time, "time", lambda: clock[0])
    manager = restart(runtime, owned=50, pending={
        "target": 50, "issued": -999999, "issued_wall": stamp,
        "release": release, "ack_poll_min_s": 0,
    })
    # An optimistic matching echo, even aged past ten seconds, is not enough.
    report(hass, wall=stamp + .01)
    clock[0] = stamp + 11
    assert not await manager.reconcile_restart(NOW)
    assert manager.restart_recovery and not hass.services.calls

    report(hass, wall=stamp + 10.1)
    assert await manager.reconcile_restart(NOW)
    assert manager.restart_recovery is None
    assert manager.owned_target == (None if release else 50)
    assert manager.last_success["confirmation"] == "restart_delayed_ha_state"
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_pre_restart_later_echo_is_not_reused_as_pending_ack():
    runtime, hass = setup()
    stamp = time.time()
    report(hass, 50, wall=stamp - 1)
    manager = restart(runtime, owned=50, pending={
        "target": 50, "issued_wall": stamp - 20, "ack_poll_min_s": 10,
    })

    assert not await manager.reconcile_restart(NOW)
    assert manager.restart_recovery and manager.last_success is None
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_later_pending_mismatch_is_not_blindly_reissued():
    runtime, hass = setup()
    stamp = time.time()
    manager = restart(runtime, owned=60, pending={
        "target": 60, "issued_wall": stamp - 20, "ack_poll_min_s": 10,
    })
    report(hass, 50, wall=stamp + 1)

    assert await manager.reconcile_restart(NOW)
    assert manager.restart_recovery is None and manager.manual_hold
    assert manager.last_success is None
    await tick(runtime)
    assert manager.manual_hold and not hass.services.calls


@pytest.mark.asyncio
async def test_restart_journal_survives_another_restart_without_becoming_live_pending():
    runtime, hass = setup()
    manager = restart(runtime, owned=60)
    hass.states.set("sensor.water", "unavailable")
    assert not await manager.reconcile_restart(NOW)
    snapshot = manager.snapshot()
    assert snapshot["restart_recovery"]["owned_target"] == 60

    again = DHWManager(runtime)
    again.restore(snapshot)
    runtime.dhw = again
    assert again.restart_recovery["owned_target"] == 60
    assert again.owned_target is None and again.pending is None
    assert not again.blocks_increase and not again.needs_review
    assert again.overview()["restart_recovery_pending"]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_safe_removal_waits_for_unresolved_boiler_restart_without_global_increase_lock():
    runtime, hass = setup()
    manager = restart(runtime, owned=60)
    hass.states.set("sensor.water", "unavailable")

    assert manager.busy and not manager.blocks_increase
    await runtime.prepare_removal()

    assert manager.restart_recovery and manager.busy
    assert not runtime.removal_overview()["ready"]
    assert "Boilerdoel wordt nog veilig vrijgegeven" in runtime.removal_overview()["blockers"]
    assert not hass.services.calls
