"""Current hard permission stays separate from timed user demand and waiting.

Fictional sources and a local expiring relay do not certify physical hardware.
"""
import time

import pytest

from test_sg_budget_priority62 import configured
from test_sg_controller62 import fixture, tick


def manual_on(runtime):
    manager = runtime.sg_boost
    manager._manual_control = {"mode": "on", "expires_at": time.time()+1800, "duration_s": 1800}
    manager._manual_deadline = time.monotonic()+1800


def current_runtime(*, export=0):
    runtime, hass = configured(export=export)
    runtime.settings["max_import_w"] = 4000
    runtime.entry.runtime_data = runtime
    hass.states.set("sensor.public_hp", 0, {"unit_of_measurement": "W"})
    return runtime, hass


def test_production_manual_demand_bypasses_only_solar_threshold():
    runtime, _hass = current_runtime()
    assert runtime.sg_dispatch_allowed() is False
    manual_on(runtime)
    assert runtime.sg_dispatch_allowed() is True


@pytest.mark.parametrize("failure", ["net", "missing_p1", "missing_pv", "pause", "priority"])
def test_production_manual_demand_retains_current_hard_guards(failure):
    runtime, hass = current_runtime()
    manual_on(runtime)
    if failure == "net":
        hass.states.set("sensor.grid", 900, {"unit_of_measurement": "W"})
    elif failure == "missing_p1":
        hass.states.set("sensor.grid", "unavailable", {"unit_of_measurement": "W"})
    elif failure == "missing_pv":
        hass.states.set("sensor.public_pv", "unavailable", {"unit_of_measurement": "W"})
    elif failure == "pause":
        runtime.mode = "paused"
    else:
        runtime.priority_board.sg_priority_allowed = lambda _now: False
    assert runtime.sg_dispatch_allowed() is False


@pytest.mark.parametrize("condition,kind", [
    ("cloud", "cloud"), ("missing_p1", "measurement_gap"),
    ("missing_pv", "measurement_gap"), ("known_net", None), ("pause", None),
])
def test_postawait_wait_classification_uses_current_proof(condition, kind):
    runtime, hass = current_runtime()
    if condition == "missing_p1":
        hass.states.set("sensor.grid", "unavailable", {"unit_of_measurement": "W"})
    elif condition == "missing_pv":
        hass.states.set("sensor.public_pv", "unavailable", {"unit_of_measurement": "W"})
    elif condition == "known_net":
        hass.states.set("sensor.grid", 900, {"unit_of_measurement": "W"})
    elif condition == "pause":
        runtime.mode = "paused"
    assert runtime.sg_start_wait_kind() == kind


@pytest.mark.asyncio
@pytest.mark.parametrize("delay,retained", [(299, True), (300, True), (301, False)])
async def test_start_cloud_clock_is_bounded_and_never_dispatches_without_current_solar(delay, retained):
    manager, adapter, clock, _runtime = fixture(start_delay_s=120)
    await tick(manager)
    origin = manager._stable_since
    clock.advance(60)
    await tick(manager, surplus=100)
    for _ in range(delay//60):
        clock.advance(60)
        await tick(manager, surplus=100)
    clock.advance(delay % 60)
    await tick(manager, surplus=100)
    assert not adapter.calls
    assert (manager._stable_since == origin) is retained
    await tick(manager)
    assert bool(adapter.calls) is retained


@pytest.mark.asyncio
async def test_start_source_rebind_does_not_inherit_old_waiting_clock():
    manager, adapter, clock, _runtime = fixture(start_delay_s=120)
    await tick(manager, solar_stamp=clock(), start_source_identity="fictional-source-A")
    clock.advance(60)
    await tick(manager, surplus=100, solar_stamp=clock(), start_source_identity="fictional-source-A")
    clock.advance(70)
    await tick(manager, solar_stamp=clock(), start_source_identity="fictional-source-B")
    assert not adapter.calls and manager.overview()["start_remaining_s"] == 120


@pytest.mark.asyncio
async def test_manual_expiry_with_current_automatic_permission_preserves_contact_without_pulse():
    manager, adapter, clock, _runtime = fixture(min_session_s=0, max_session_s=7200)
    await manager.set_manual_control("on", 1800)
    await tick(manager, surplus=0)
    origin = manager._session_started
    for _ in range(30):
        clock.advance(60)
        await tick(manager, surplus=0)
    assert manager.overview()["manual_control"]["mode"] == "auto"
    assert manager.owned and adapter.on and manager._session_started == origin
    assert all(command == "on" for command, _seconds in adapter.calls)
    assert all(0 < seconds <= 300 for _command, seconds in adapter.calls)


@pytest.mark.asyncio
async def test_explicit_off_names_current_manually_on_mapped_contact():
    manager, adapter, clock, _runtime = fixture()
    adapter.on = True
    adapter.start, adapter.duration, adapter.expiry = clock(), 300, clock()+300
    await manager.start()
    assert manager.external_control_overview()["active"] and not manager.owned
    await manager.set_manual_control("off", 1800)
    assert adapter.calls == [("off", None)] and adapter.on is False
    assert manager.overview()["manual_control"]["mode"] == "off"


@pytest.mark.asyncio
async def test_explicit_off_respects_a_later_external_timer_change_before_write():
    manager, adapter, clock, _runtime = fixture()
    adapter.on = True
    adapter.start, adapter.duration, adapter.expiry = clock(), 300, clock()+300
    await manager.start()
    adapter.before_off_status = None

    class Changed(Exception):
        code = "dispatch_changed"
        command_attempted = False

    async def external_change_before_write():
        adapter.expiry += 100
        assert adapter.before_off_status(adapter.status()) is False
        raise Changed()

    adapter.set_off = external_change_before_write
    await manager.set_manual_control("off", 1800)
    assert adapter.on and not adapter.calls and manager.manual_hold
    assert manager.overview()["manual_control"]["mode"] == "off"
