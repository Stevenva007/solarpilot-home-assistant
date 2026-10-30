"""A running SG request follows actual solar consumption, not startup watts.

All meter/contact data below are fictitious. The real runtime, original meter
timestamps and expiring local relay are exercised together.
"""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from test_sg_live_solar_adversarial111 import live_site, site_step
from test_sg_transfer_integration108 import report, sources


SUN = {"grid": -100, "pv": 1600, "hp": 1300, "ev": 0}
CLOUD = {"grid": 900, "pv": 1200, "hp": 1800, "ev": 0}
NIGHT = {"grid": 100, "pv": 0, "hp": 0, "ev": 0}


async def started(monkeypatch, *, minimum=1200, stop_delay=300):
    site = live_site(monkeypatch)
    runtime, _, manager, _, _ = site
    config = {**manager.settings, "min_session_s": minimum, "stop_delay_s": stop_delay}
    runtime.entry.options["sg_boost"] = deepcopy(config)
    manager.update_config(config)
    runtime.panasonic.update_config(config)
    await site_step(site)
    for _ in range(5):
        await site_step(site, advance=30)
        if manager.owned:
            break
    assert manager.owned and site[3].on
    return site


async def keep_running(site, seconds, **reading):
    manager, adapter = site[2:4]
    origin = manager._session_started
    for _ in range(seconds // 30):
        await site_step(site, advance=30, **reading)
        assert manager.owned and adapter.on
        assert manager._session_started == origin


@pytest.mark.asyncio
@pytest.mark.parametrize("hp", [400, 1300, 2100])
async def test_modulating_heatpump_keeps_one_request_past_minimum_and_old_hour_limit(monkeypatch, hp):
    site = await started(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    origin = manager._session_started
    command = manager._session_provenance["command_identity"]
    # Current heat-pump draw is supplied by solar; there is also real export.
    # Startup required 2500 W, but maintaining this request adds no new load.
    reading = {"grid": -100, "pv": hp + 300, "hp": hp, "ev": 0}
    await keep_running(site, 4200, **reading)
    budget = sg_solar_budget(runtime)
    assert 0 < budget["eligible_w"] < manager.settings["threshold_w"] - manager.settings["hysteresis_w"]
    assert budget["grid_w"] == -100
    assert clock() - origin > manager.settings["max_session_s"]
    assert manager._session_provenance["command_identity"] == command
    assert manager._joint_solar_deficit is None and manager._last_session is None
    assert all(action == "on" and 0 < lease <= 300 for action, lease in adapter.calls)
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_separate_short_clouds_recover_without_a_new_sg_session(monkeypatch):
    site = await started(monkeypatch)
    _, _, manager, adapter, clock = site
    origin = manager._session_started
    await keep_running(site, 1500, **SUN)
    for _ in range(2):
        await site_step(site, **CLOUD)
        first_deficit = manager._import_since
        assert first_deficit == clock()
        await keep_running(site, 240, **CLOUD)
        assert manager._import_since == first_deficit
        await site_step(site, advance=30, **SUN)
        assert manager.owned and manager._import_since is None
        await keep_running(site, 120, **SUN)
    assert manager._session_started == origin and manager._last_session is None
    assert all(action == "on" for action, _ in adapter.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("before_cloud", [30, 1500])
async def test_continuous_net_import_stops_after_original_minimum_and_cloud_buffer(monkeypatch, before_cloud):
    site = await started(monkeypatch)
    runtime, _, manager, adapter, clock = site
    origin = manager._session_started
    await keep_running(site, before_cloud, **SUN)
    await site_step(site, **CLOUD)
    deficit_start = clock()
    deadline = max(origin + manager.settings["min_session_s"],
                   deficit_start + manager.settings["stop_delay_s"])
    assert sg_solar_budget(runtime)["eligible_w"] > 0
    while clock() + 30 < deadline:
        await site_step(site, advance=30, **CLOUD)
        assert manager.owned and adapter.on
        assert manager._session_started == origin
        assert manager._import_since == deficit_start
    await site_step(site, advance=deadline - clock(), **CLOUD)
    assert not manager.owned and not adapter.on
    assert manager._last_session["duration_s"] >= manager.settings["min_session_s"]
    assert "netafname" in manager._last_session["reason"].casefold()


@pytest.mark.asyncio
@pytest.mark.parametrize("reading", [NIGHT, {"grid": 100, "pv": 100, "hp": 100, "ev": 0}])
async def test_night_and_unusable_solar_below_the_house_margin_end_after_buffer(monkeypatch, reading):
    site = await started(monkeypatch, minimum=0)
    runtime, _, manager, adapter, clock = site
    await site_step(site, **reading)
    assert sg_solar_budget(runtime)["eligible_w"] == 0
    assert manager._joint_solar_deficit is not None
    start = clock()
    await keep_running(site, 270, **reading)
    await site_step(site, advance=30, **reading)
    assert clock() - start == manager.settings["stop_delay_s"]
    assert not manager.owned and not adapter.on


@pytest.mark.asyncio
async def test_short_loss_of_solar_recovers_while_heatpump_modulates_below_start_threshold(monkeypatch):
    site = await started(monkeypatch, minimum=0)
    _, _, manager, adapter, _ = site
    origin = manager._session_started
    await site_step(site, **NIGHT)
    await keep_running(site, 240, **NIGHT)
    await site_step(site, advance=30, **SUN)
    assert manager.owned and manager._joint_solar_deficit is None
    await keep_running(site, 900, **SUN)
    assert manager._session_started == origin
    assert all(action == "on" for action, _ in adapter.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("minimum", [0, 1200])
async def test_shortage_explanation_and_original_countdowns_survive_lease_renewal(monkeypatch, minimum):
    site = await started(monkeypatch, minimum=minimum)
    _, _, manager, adapter, clock = site
    origin = manager._session_started
    minimum_origin = manager._minimum_started
    await keep_running(site, 30, **SUN)
    await site_step(site, **NIGHT)
    deadline = manager._joint_solar_deficit["deadline"]
    before = len(adapter.calls)
    assert "wolkenbuffer nog 300 s" in manager.reason
    if minimum:
        assert "minimumduur nog 1170 s" in manager.reason
    await keep_running(site, 120, **NIGHT)
    assert len(adapter.calls) > before  # A real local timer renewal occurred.
    assert "wolkenbuffer nog 180 s" in manager.reason
    if minimum:
        assert "minimumduur nog 1050 s" in manager.reason
    assert manager._joint_solar_deficit["deadline"] == deadline
    assert manager._joint_remaining() == deadline - clock() == 180
    assert manager._session_started == origin and manager._minimum_started == minimum_origin
    checkpoint = manager.snapshot()["session_checkpoint"]
    assert checkpoint["joint_solar_deficit"]["deadline"] == deadline
    assert checkpoint["started_at"] == origin
    assert all(action == "on" for action, _ in adapter.calls)


@pytest.mark.asyncio
async def test_small_current_solar_respects_the_configured_actual_import_tolerance(monkeypatch):
    site = await started(monkeypatch, minimum=0)
    runtime, _, manager, adapter, _ = site
    # 50 W remains after actual site import and the explicit 150 W margin.
    # Exactly the configured 600 W import tolerance remains permitted.
    reading = {"grid": 600, "pv": 500, "hp": 800, "ev": 0}
    await keep_running(site, 900, **reading)
    assert sg_solar_budget(runtime)["eligible_w"] == 50
    assert manager._import_since is None
    # A little more import does not remove solar credit, but the independent
    # import buffer must still expire. The small solar pool cannot bypass it.
    reading["grid"] = 601
    await site_step(site, **reading)
    assert sg_solar_budget(runtime)["eligible_w"] == 49
    await keep_running(site, 270, **reading)
    await site_step(site, advance=30, **reading)
    assert not manager.owned and not adapter.on
    assert "netafname" in manager._last_session["reason"].casefold()


@pytest.mark.asyncio
async def test_stale_heatpump_power_cannot_supply_fictitious_continuation_credit(monkeypatch):
    site = await started(monkeypatch, minimum=0)
    runtime, hass, manager, adapter, clock = site
    before = clock()
    for index in range(11):
        if index:
            clock.advance(30)
        sources(runtime, hass, clock, **SUN)
        report(hass, clock, "sensor.public_hp", 1300, {"unit_of_measurement": "W"}, age=121)
        await runtime._tick()
        budget = sg_solar_budget(runtime)
        assert budget["valid"] and not budget["hp_power_complete"]
        assert budget["eligible_w"] == 0
        if index < 10:
            assert manager.owned
    assert clock() - before == 300
    assert not manager.owned and not adapter.on


@pytest.mark.asyncio
@pytest.mark.parametrize("violation", ["net", "phase", "battery"])
async def test_actual_hard_protection_overrides_modulation_and_minimum(monkeypatch, violation):
    site = await started(monkeypatch)
    runtime, hass, manager, adapter, clock = site
    await keep_running(site, 30, **SUN)
    assert manager.minimum_hold_active
    clock.advance(5)
    sources(runtime, hass, clock, **SUN)
    if violation == "net":
        report(hass, clock, "sensor.grid", 4500, {"unit_of_measurement": "W"})
    elif violation == "phase":
        runtime.phase_settings.update(enabled=True, control_starts=True, limit_w=4000,
            phase_1_entity="sensor.fictional_phase1", phase_2_entity="sensor.fictional_phase2",
            phase_3_entity="sensor.fictional_phase3")
        for index in (1, 2, 3):
            report(hass, clock, f"sensor.fictional_phase{index}", 4500, {"unit_of_measurement": "W"})
    else:
        runtime.settings["battery_power_entity"] = "sensor.fictional_battery"
        report(hass, clock, "sensor.fictional_battery", 500, {"unit_of_measurement": "W"})
    await runtime._tick()
    assert not manager.owned and not adapter.on
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_explicit_manual_off_is_preserved_despite_current_solar(monkeypatch):
    site = await started(monkeypatch)
    _, _, manager, adapter, clock = site
    await keep_running(site, 60, **SUN)
    await manager.set_manual_control("off", 1800)
    assert not manager.owned and not adapter.on
    before = list(adapter.calls)
    for _ in range(10):
        await site_step(site, advance=30, **SUN)
        assert manager.manual_mode == "off" and not manager.owned and not adapter.on
    assert adapter.calls == before and clock() < manager._manual_deadline
