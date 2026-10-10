"""Exercise HA Core's immutable ConfigEntry boundary, not mutable test options.

HA 2026.10 ConfigEntry stores data/options as top-level MappingProxyType values;
its nested payload remains ordinary JSON data. These tests retain that boundary
through startup and every config-entry update.
"""
from copy import deepcopy
from types import MappingProxyType, SimpleNamespace

import pytest

from custom_components.solar_pilot.panasonic_migration import (
    ARCHIVE_KEY, MARKER, migrate_panasonic,
)
from custom_components.solar_pilot.runtime import SolarRuntime
from test_runtime import build


def installation():
    base, hass = build()
    options = deepcopy(base.entry.options)
    options.update({
        "priority_board": {"schema": 2, "order": ["wallbox", "dhw_extra", "device:a"],
                           "source": "central_beta36", "wallbox_power": {"device:a": False}},
        "dhw": {"enabled": True, "target_entity": "water_heater.native_tank",
                "temperature_entity": "sensor.native_tank_temperature"},
        "smart_climate": {"control_enabled": True, "zone_entities": ["climate.native_zone"]},
        "unknown_legacy_options": {"nested": [{"unchanged": "retain exactly"}], "enabled": True},
    })
    entry = SimpleNamespace(entry_id="immutable-entry",
                            data=MappingProxyType(deepcopy(base.entry.data)),
                            options=MappingProxyType(deepcopy(options)))
    return hass, entry, options


def assert_no_physical_calls(hass):
    assert not [call for call in hass.services.calls if call[0] != "persistent_notification"]


def test_constructor_accepts_real_config_entry_mapping_and_detaches_exact_options():
    hass, entry, original = installation()
    runtime = SolarRuntime(hass, entry)
    assert runtime.panasonic_archive["backup_options"] == original
    assert runtime.configs["a"]["control_entity"] == "switch.load"
    assert runtime.panasonic.settings["tank_temperature_entity"] == "sensor.native_tank_temperature"
    assert runtime.sg_boost.auto_enabled is False
    runtime.panasonic_archive["backup_options"]["unknown_legacy_options"]["nested"][0]["unchanged"] = "changed copy"
    assert entry.options["unknown_legacy_options"] == original["unknown_legacy_options"]
    assert_no_physical_calls(hass)


def test_pure_migration_preserves_immutable_options_and_json_store_exactly():
    _, entry, original = installation()
    stored = {"mode": "observe", "dhw": {"pending": {"target": 60}},
              "smart_climate": {"expected_mode": {"climate.native_zone": "auto"}},
              "unknown_evidence": ["complete", {"value": 12}]}
    new, migrated, report = migrate_panasonic(entry.options, stored)
    assert report["changed"] is True
    assert migrated[ARCHIVE_KEY]["backup_options"] == original
    assert migrated[ARCHIVE_KEY]["backup_store"] == stored
    assert new["devices"] == original["devices"]
    assert new["priority_board"] == original["priority_board"]
    assert new["unknown_legacy_options"] == original["unknown_legacy_options"]
    assert entry.options == original
    assert new["sg_boost"]["entity_id"] == ""
    assert all(new["sg_boost"][key] is False for key in
               ("enabled", "commissioning_confirmed", "watchdog_confirmed"))
    again, repeated, repeat_report = migrate_panasonic(MappingProxyType(new), migrated)
    assert again == new and repeated == migrated
    assert repeat_report["changed"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("saved_mode", ["observe", "solar", "paused"])
async def test_full_start_commits_exact_private_archive_before_immutable_options_update(saved_mode):
    hass, entry, original = installation()
    runtime = SolarRuntime(hass, entry)
    stored = {"mode": saved_mode, "auto_resume_after_restart": False,
              "device_modes": {"a": "disabled"}, "energy_kwh": 17.25,
              "dhw": {"pending": {"target": 60}, "owned_target": 60},
              "smart_climate": {"expected_mode": {"climate.native_zone": "auto"}},
              "unknown_evidence": {"complete": [1, 2, 3]}}
    runtime.store.data = deepcopy(stored)
    events = []
    save = runtime.store.async_save

    async def save_checked(data):
        events.append("store")
        await save(data)

    def update(target, *, options):
        assert target is entry
        assert runtime.store.data[ARCHIVE_KEY]["backup_options"] == original
        assert runtime.store.data[ARCHIVE_KEY]["backup_store"] == stored
        events.append("options")
        target.options = MappingProxyType(deepcopy(options))

    runtime.store.async_save = save_checked
    hass.config_entries = SimpleNamespace(async_update_entry=update)
    await runtime.start()
    try:
        assert events[:2] == ["store", "options"]
        assert isinstance(entry.options, MappingProxyType)
        assert entry.options[MARKER] == 1
        assert entry.options["devices"] == original["devices"]
        assert entry.options["priority_board"] == original["priority_board"]
        assert entry.options["unknown_legacy_options"] == original["unknown_legacy_options"]
        assert runtime.panasonic_archive["backup_options"] == original
        assert runtime.panasonic_archive["backup_store"] == stored
        assert runtime.store.data[ARCHIVE_KEY] == runtime.panasonic_archive
        assert runtime.energy_kwh == 17.25
        assert runtime.mode == saved_mode
        assert runtime.sg_boost.auto_enabled is False
        assert runtime.sg_boost.settings["entity_id"] == ""
        assert "dhw" not in entry.options and "smart_climate" not in entry.options
        assert_no_physical_calls(hass)
        # Reload uses immutable updated options and must preserve the first
        # exact backup instead of nesting or replacing it with migrated data.
        reloaded = SolarRuntime(hass, entry)
        reloaded.store.data = deepcopy(runtime.store.data)
        await reloaded.start()
        try:
            assert reloaded.panasonic_archive == runtime.panasonic_archive
            assert reloaded.energy_kwh == 17.25
            assert reloaded.sg_boost.auto_enabled is False
            assert_no_physical_calls(hass)
        finally:
            await reloaded.close()
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_failed_private_archive_write_cannot_publish_migrated_or_empty_options():
    hass, entry, original = installation()
    runtime = SolarRuntime(hass, entry)
    stored = {"mode": "solar", "energy_kwh": 17.25, "dhw": {"pending": {"target": 60}}}
    runtime.store.data = deepcopy(stored)
    updates = []
    hass.config_entries = SimpleNamespace(async_update_entry=lambda *args, **kwargs: updates.append(kwargs))

    async def fail_save(_):
        raise OSError("private archive write failed")

    runtime.store.async_save = fail_save
    with pytest.raises(OSError, match="private archive write failed"):
        await runtime.start()
    await runtime.close(persist=False)
    assert updates == []
    assert entry.options == original
    assert runtime.store.data == stored
    assert runtime.store.saves == []
    assert_no_physical_calls(hass)
