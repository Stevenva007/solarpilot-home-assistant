"""SG continuation follows original source clocks through asynchronous reports."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from test_sg_live_solar_adversarial111 import live_site, site_step
from test_sg_transfer_integration108 import report, sources


async def started(monkeypatch, *, minimum=1200):
    site = live_site(monkeypatch)
    runtime, _hass, manager, _adapter, _clock = site
    config = {**manager.settings, "min_session_s": minimum}
    runtime.entry.options["sg_boost"] = deepcopy(config)
    manager.update_config(config)
    await site_step(site)
    for _ in range(5):
        await site_step(site, advance=30)
        if manager.owned:
            break
    assert manager.owned
    return site


@pytest.mark.asyncio
@pytest.mark.parametrize("contributor", ["hp", "ev"])
async def test_fresh_slower_contributor_rejoins_without_an_off_pulse(monkeypatch, contributor):
    runtime, hass, manager, adapter, clock = await started(monkeypatch)
    origin = manager._session_started
    clock.advance(60)
    hp, ev = (2590, 0) if contributor == "hp" else (0, 2590)
    sources(runtime, hass, clock, grid=-39, pv=2000, hp=hp, ev=ev)
    entity = "sensor.public_hp" if contributor == "hp" else "sensor.public_ev_power"
    report(hass, clock, entity, 2590, {"unit_of_measurement": "W"}, age=30)
    await runtime._tick()
    first = deepcopy(manager._joint_solar_deficit)
    assert first is not None and manager.minimum_hold_active and manager.owned

    clock.advance(5)
    # P1/PV now agree with the original, still-fresh slower HP/EV report.
    report(hass, clock, "sensor.grid", -39, {"unit_of_measurement": "W"})
    report(hass, clock, "sensor.public_pv", 4890, {"unit_of_measurement": "W"})
    budget = sg_solar_budget(runtime)
    assert budget["eligible_w"] == 2479 and budget["stamp"] < first["stamp"]
    assert runtime.sg_usable_solar_observation()["source_reports"][contributor] == clock()-35
    await runtime._tick()
    assert manager.owned and adapter.on and manager.minimum_hold_active
    assert manager._joint_solar_deficit is None and manager._session_started == origin
    assert all(command == "on" for command, _lease in adapter.calls)


@pytest.mark.asyncio
async def test_changing_oldest_source_cannot_extend_an_actual_shortage(monkeypatch):
    runtime, hass, manager, adapter, clock = await started(monkeypatch, minimum=0)
    clock.advance(60)
    sources(runtime, hass, clock, grid=1000, pv=1200, hp=2590, ev=0)
    report(hass, clock, "sensor.public_hp", 2590, {"unit_of_measurement": "W"}, age=30)
    await runtime._tick()
    first = deepcopy(manager._joint_solar_deficit)
    assert first is not None and manager.owned
    clock.advance(5)
    # A slower lower HP report becomes coherent, but there is still no usable
    # solar after present consumption and the configured house margin.
    sources(runtime, hass, clock, grid=1000, pv=1200, hp=1000, ev=0)
    report(hass, clock, "sensor.public_hp", 1000, {"unit_of_measurement": "W"}, age=30)
    assert sg_solar_budget(runtime)["stamp"] < first["stamp"]
    await runtime._tick()
    assert manager.owned and manager._joint_solar_deficit["deadline"] == first["deadline"]
    protected_until = first["deadline"]-manager.settings["ack_timeout_s"]
    while clock() < protected_until-1:
        clock.advance(min(30, protected_until-1-clock()))
        sources(runtime, hass, clock, grid=1000, pv=1200, hp=1000, ev=0)
        await runtime._tick()
        assert manager.owned and manager._joint_solar_deficit["deadline"] == first["deadline"]
    clock.advance(first["deadline"]-clock())
    sources(runtime, hass, clock, grid=1000, pv=1200, hp=1000, ev=0)
    await runtime._tick()
    assert not manager.owned and not adapter.on
    assert manager._last_session["ended_at"] <= first["deadline"]


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["hp", "pv", "p1", "battery"])
async def test_new_p1_does_not_hide_an_actual_source_clock_rollback(monkeypatch, source):
    runtime, hass, manager, _adapter, clock = await started(monkeypatch)
    clock.advance(60)
    if source == "battery":
        runtime.settings["battery_power_entity"] = "sensor.fictional_battery"
        report(hass, clock, "sensor.fictional_battery", 0, {"unit_of_measurement": "W"})
    sources(runtime, hass, clock, grid=1000, pv=2200, hp=1000, ev=0)
    await runtime._tick()
    first = deepcopy(manager._joint_solar_deficit)
    assert first is not None
    clock.advance(5)
    sources(runtime, hass, clock, grid=-39, pv=4890, hp=2590, ev=0)
    entity, watts = {"hp": ("sensor.public_hp", 2590),
        "pv": ("sensor.public_pv", 4890), "p1": ("sensor.grid", -39),
        "battery": ("sensor.fictional_battery", 0)}[source]
    report(hass, clock, entity, watts, {"unit_of_measurement": "W"}, age=10)
    assert sg_solar_budget(runtime)["eligible_w"] > 0
    await runtime._tick()
    assert not manager.owned or manager._joint_solar_deficit is not None
    if manager._joint_solar_deficit is not None:
        assert manager._joint_solar_deficit["deadline"] == first["deadline"]


@pytest.mark.asyncio
async def test_legacy_deficit_gains_separate_clocks_without_new_grace(monkeypatch):
    runtime, hass, manager, _adapter, clock = await started(monkeypatch)
    clock.advance(60)
    sources(runtime, hass, clock, grid=1000, pv=1200, hp=1000, ev=0)
    await runtime._tick()
    previous = deepcopy(manager._joint_solar_deficit)
    previous.pop("source_reports")  # A genuine beta.111 journal has this shape.
    clock.advance(20)
    manager._restore_joint_deficit(previous, manager._session_provenance["started_at"])
    sources(runtime, hass, clock, grid=1000, pv=1200, hp=1000, ev=0)
    await runtime._tick()
    current = manager._joint_solar_deficit
    assert manager.owned and current["deadline"] == previous["deadline"]
    assert current["source_reports"]["p1"] == clock()
    assert manager._joint_remaining() == 280


@pytest.mark.asyncio
async def test_complete_zero_hp_report_prevents_older_positive_replay(monkeypatch):
    runtime, hass, manager, _adapter, clock = await started(monkeypatch)
    clock.advance(60)
    sources(runtime, hass, clock, grid=-39, pv=4890, hp=0, ev=0)
    await runtime._tick()
    deficit = deepcopy(manager._joint_solar_deficit)
    assert deficit["source_reports"]["hp"] == clock()
    clock.advance(5)
    sources(runtime, hass, clock, grid=-39, pv=4890, hp=2590, ev=0)
    report(hass, clock, "sensor.public_hp", 2590, {"unit_of_measurement": "W"}, age=10)
    await runtime._tick()
    assert not manager.owned or manager._joint_solar_deficit is not None
    if manager._joint_solar_deficit is not None:
        assert manager._joint_solar_deficit["deadline"] == deficit["deadline"]


@pytest.mark.asyncio
@pytest.mark.parametrize("reports", [{}, {"p1": True}, {"p1": float("nan")}, {"other": 1}])
async def test_malformed_per_source_evidence_is_not_a_current_observation(monkeypatch, reports):
    runtime, _hass, manager, _adapter, _clock = await started(monkeypatch)
    observation = runtime.sg_usable_solar_observation()
    observation["source_reports"] = reports
    assert manager._usable_solar(observation) is None
