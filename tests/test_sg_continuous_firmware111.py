"""Real firmware OFF interrupts a solar episode without reviving its old cap."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_sg_live_solar_adversarial111 import live_site, site_step
from test_sg_commissioning_evidence110 import reboot_relay


async def solar_with_boot(monkeypatch):
    site = live_site(monkeypatch, maximum=300)
    runtime, hass, manager, adapter, clock = site
    boot = [clock()-10_000]
    status = adapter.status
    adapter.status = lambda: {**status(), "device_unixtime": clock(),
                              "device_uptime_s": clock()-boot[0]}
    await site_step(site)
    for _ in range(45):
        await site_step(site, advance=30)
    assert manager.owned and clock()-manager._session_started > 3*manager.settings["max_session_s"]
    return site, boot


@pytest.mark.asyncio
async def test_firmware_reboot_after_three_old_caps_earns_a_fresh_solar_request(monkeypatch):
    site, boot = await solar_with_boot(monkeypatch)
    _, _, manager, adapter, clock = site
    old_origin = manager._session_started
    calls = len(adapter.calls)
    clock.advance(5)
    reboot_relay(adapter, clock, boot)
    await site_step(site)
    assert not manager.owned and not manager.manual_hold and not manager.completion_hold
    assert manager._firmware_reboot is None and manager._session_started is None
    assert manager._last_session["duration_s"] > 900
    assert len(adapter.calls) == calls
    for _ in range(3):
        await site_step(site, advance=30)
    assert not manager.owned and len(adapter.calls) == calls
    await site_step(site, advance=30)
    assert manager.owned and manager._session_started == clock() > old_origin
    assert adapter.calls[-1] == ("on", 300) and not manager.fault


@pytest.mark.asyncio
async def test_plain_user_off_after_hours_keeps_its_manual_stop_protection(monkeypatch):
    site, _ = await solar_with_boot(monkeypatch)
    _, _, manager, adapter, _ = site
    calls = len(adapter.calls)
    adapter.on = False
    adapter.start = adapter.duration = adapter.expiry = None
    await site_step(site, advance=5)
    assert manager.manual_hold and not manager.owned
    for _ in range(6):
        await site_step(site, advance=30)
    assert manager.manual_hold and len(adapter.calls) == calls


@pytest.mark.asyncio
async def test_legacy_automatic_firmware_wait_retires_only_after_current_off(monkeypatch):
    site, _ = await solar_with_boot(monkeypatch)
    runtime, _, manager, adapter, clock = site
    manager._record_session_end("SG-contact uit na bewezen firmwareherstart; actuele zonnebeoordeling volgt")
    manager.owned = manager.desired_on = False
    manager._session_started = manager._minimum_started = None
    manager._lease_expiry = manager._lease_deadline = None
    adapter.on = False
    adapter.start = adapter.duration = adapter.expiry = None
    end = clock()
    record = {"schema": 1, "state": "waiting", "detected_at": end,
        "started_at": end-200, "minimum_started_at": end-200,
        "deadline": end+100, "control_identity": manager._control_identity(),
        "remaining_cap_s": 100, "observed_at": end}
    manager._firmware_reboot = record
    manager._firmware_reboot_anchor = {"origin": end-200, "minimum": end-200, "deadline": end+100}
    snapshot = deepcopy(manager.snapshot())
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    restored.restore(snapshot)
    changed = (runtime, site[1], restored, adapter, clock)
    await site_step(changed, advance=5)
    assert restored._firmware_reboot is None and not restored.manual_hold and not restored.owned
    for _ in range(4):
        await site_step(changed, advance=30)
    assert restored.owned and not restored.fault
