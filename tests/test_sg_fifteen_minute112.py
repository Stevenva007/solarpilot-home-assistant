"""Fifteen-minute cloud episodes with short local leases and real fake time."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.panasonic_migration import ARCHIVE_KEY, MARKER, MIGRATION_VERSION, migrate_panasonic
from custom_components.solar_pilot.sg_boost import SGBoostManager
from test_sg_cloud_continuation112 import CLOUD, NIGHT, SUN, keep_running, started
from test_sg_live_solar_adversarial111 import site_step


@pytest.mark.asyncio
@pytest.mark.parametrize("cloud", [CLOUD, NIGHT])
async def test_fourteen_minute_cloud_recovers_without_a_contact_cycle(monkeypatch, cloud):
    site = await started(monkeypatch, stop_delay=900)
    _, _, manager, adapter, clock = site
    origin = manager._session_started
    command = manager._session_provenance["command_identity"]
    await keep_running(site, 1500, **SUN)
    for _ in range(2):
        await site_step(site, **cloud)
        cloud_start = clock()
        if cloud == NIGHT:
            assert "wolkenbuffer nog 900 s" in manager.reason
        await keep_running(site, 810, **cloud)
        assert clock() - cloud_start > 300  # The old five-minute limit passed.
        await site_step(site, advance=30, **SUN)
        assert clock() - cloud_start == 840
        assert manager.owned and adapter.on
        assert manager._import_since is None and manager._joint_solar_deficit is None
        await keep_running(site, 120, **SUN)
    assert manager._session_started == origin
    assert manager._session_provenance["command_identity"] == command
    assert manager._last_session is None
    assert len(adapter.calls) > 20
    assert all(action == "on" and 0 < lease <= 300 for action, lease in adapter.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("cloud", [CLOUD, NIGHT])
async def test_cloud_starting_in_minute_eighteen_runs_until_minute_thirty_three(monkeypatch, cloud):
    site = await started(monkeypatch, stop_delay=900)
    _, _, manager, adapter, clock = site
    origin = manager._session_started
    await keep_running(site, 1080, **SUN)
    await site_step(site, **cloud)
    cloud_start = clock()
    deadline = cloud_start + 900
    assert manager.minimum_hold_active
    await keep_running(site, 870, **cloud)
    assert clock() - origin == 1950
    assert not manager.minimum_hold_active
    assert manager._session_started == origin
    if cloud == NIGHT:
        assert manager._joint_solar_deficit["deadline"] == deadline
        # The local fallback reserves bounded transport delivery time. It may
        # expire within that final ACK margin, never later than cloud end.
        assert deadline - manager.settings["ack_timeout_s"] <= manager._lease_expiry <= deadline
    else:
        assert manager._import_since == cloud_start
    await site_step(site, advance=30, **cloud)
    assert clock() - origin == 1980
    assert not manager.owned and not adapter.on
    assert manager._last_session["duration_s"] <= 1980
    assert all(action != "on" or 0 < lease <= 300 for action, lease in adapter.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("cloud", [CLOUD, NIGHT])
async def test_reload_does_not_restart_a_fifteen_minute_cloud_episode(monkeypatch, cloud):
    site = await started(monkeypatch, stop_delay=900)
    runtime, hass, manager, adapter, clock = site
    origin = manager._session_started
    await keep_running(site, 1500, **SUN)
    await site_step(site, **cloud)
    cloud_start = clock()
    deadline = cloud_start + 900
    await keep_running(site, 600, **cloud)
    saved = manager.snapshot()
    before = list(adapter.calls)
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    restored.restore(saved)
    reloaded = (runtime, hass, restored, adapter, clock)
    await site_step(reloaded, advance=30, **cloud)
    assert restored.owned and restored._session_started == origin
    # Restore only adopts the still-current local lease; it does not write ON.
    assert adapter.calls == before
    if cloud == NIGHT:
        assert restored._joint_solar_deficit["deadline"] == deadline
        assert restored._joint_remaining() == 270
    else:
        assert restored._import_since == cloud_start
    await keep_running(reloaded, 240, **cloud)
    await site_step(reloaded, advance=30, **cloud)
    assert clock() == deadline
    assert not restored.owned and not adapter.on
    assert all(action != "on" or 0 < lease <= 300 for action, lease in adapter.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("cloud", [CLOUD, NIGHT])
async def test_default_upgrade_cannot_extend_an_already_running_old_five_minute_episode(monkeypatch, cloud):
    site = await started(monkeypatch, stop_delay=300)
    runtime, hass, manager, adapter, clock = site
    await keep_running(site, 1500, **SUN)
    await site_step(site, **cloud)
    old_deadline = clock() + 300
    await keep_running(site, 120, **cloud)
    saved = manager.snapshot()
    options = {**deepcopy(runtime.entry.options), MARKER: MIGRATION_VERSION}
    stored = {"sg_boost": deepcopy(saved), ARCHIVE_KEY: {
        "version": MIGRATION_VERSION, "read_only": True,
        "backup_options": {}, "backup_store": {}, "assessment": {}}}
    migrated_options, migrated_data, assessment = migrate_panasonic(options, stored)
    assert assessment["changed"]
    assert migrated_options["sg_boost"]["stop_delay_s"] == 900
    # Migration changes new policy, not the historical admission or expiry.
    assert migrated_data["sg_boost"] == saved
    assert options["sg_boost"]["stop_delay_s"] == 300
    if cloud == NIGHT:
        assert migrated_data["sg_boost"]["session_checkpoint"]["joint_solar_deficit"]["deadline"] == old_deadline
    before = len(adapter.calls)
    runtime.entry.options = migrated_options
    runtime.panasonic.update_config(migrated_options["sg_boost"])
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    restored.restore(migrated_data["sg_boost"])
    await site_step((runtime, hass, restored, adapter, clock), advance=30, **cloud)
    # The previous policy hash cannot authorize a longer lease. Reconciliation
    # conservatively releases this old contact; a later start needs fresh proof.
    assert not restored.owned and not adapter.on and clock() < old_deadline
    assert not any(action == "on" for action, _ in adapter.calls[before:])
