"""Exercise production entry setup against installed Home Assistant Core.

Run outside pytest: the normal unit suite intentionally provides HA doubles.
Only synthetic states and a disposable local configuration are used. HTTP
socket operations and source-IP discovery are replaced with offline no-ops;
no physical device is opened and all integration lifecycle code remains real.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from importlib.metadata import version
import json
import logging
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import MappingProxyType
from unittest.mock import patch


def fixture():
    """Generic protocol-shaped configuration, never household identifiers."""
    options = {
        "devices": [{"id": "synthetic_load", "name": "Synthetic load",
                     "kind": "switch", "control_entity": "switch.synthetic_load",
                     "nominal_w": 350, "priority": 61}],
        "settings": {"reserve_w": 275},
        "priority_board": {"schema": 2,
                           "order": ["wallbox", "dhw_extra", "device:synthetic_load"],
                           "wallbox_power": {"device:synthetic_load": False},
                           "source": "central_beta36"},
        "wallbox": {"enabled": False},
        "dhw": {"enabled": True, "target_entity": "water_heater.synthetic_tank",
                "temperature_entity": "sensor.synthetic_tank",
                "surplus_threshold_w": 3700},
        "smart_climate": {"enabled": True, "zone_entities": ["climate.synthetic_zone"]},
    }
    journal = {
        "mode": "observe", "auto_resume_after_restart": False,
        "device_modes": {"synthetic_load": "disabled"},
        "priorities": {"synthetic_load": 61}, "energy_kwh": 17.25,
        "dhw": {"owned_target": 60, "needs_review": True},
        "smart_climate": {"profiles": {"climate.synthetic_zone": {"samples": 633}}},
    }
    return options, journal


def current_sg_fixture():
    """Already migrated, disabled general SG with synthetic read-only roles."""
    options, journal = fixture()
    options.pop("dhw")
    options.pop("smart_climate")
    options["_panasonic_migration"] = 1
    options["retained_nested"] = {"source": {"values": [1, {"keep": True}]}}
    options["sg_boost"] = {
        "enabled": False, "entity_id": "switch.synthetic_sg",
        "commissioning_confirmed": False, "watchdog_confirmed": False,
        "profile": "general", "profile_confirmed": True,
        "cooling_protection_confirmed": False,
        "tank_temperature_entity": "sensor.synthetic_tank",
        "tank_target_entity": "water_heater.synthetic_tank",
        "activity_entity": "sensor.synthetic_activity",
        "zone_entities": ["climate.synthetic_zone"],
        "power_entity": "", "power_supply1_entity": "sensor.synthetic_supply1",
        "power_supply2_entity": "sensor.synthetic_supply2", "split_power_confirmed": True,
        "compressor_frequency_entity": "sensor.synthetic_frequency",
        "sg_status_entity": "binary_sensor.synthetic_sg_received",
    }
    journal.pop("dhw")
    journal.pop("smart_climate")
    journal["panasonic_archive"] = {
        "version": 1, "read_only": True,
        "backup_options": {"retired_options": {"values": [1, 2]}},
        "backup_store": {"retired_learning": {"samples": [3, 4]}},
        "assessment": {"changed": True, "retired_only_pause": False},
    }
    ended = time.time() - 3600
    journal["sg_boost"] = {
        "schema": 1, "relay_entity": "switch.synthetic_sg", "owned": False,
        "manual_hold": True, "completion_hold": True, "profile": "general",
        "hold_reason": "session_limit",
        "general_reference": {"schema": 1, "ended_at": ended,
            "signature": "synthetic_previous_context", "native_stamp": ended,
            "solar_stamp": ended, "solar_reset_stamp": None,
            "native_reset_stamp": None, "profile_transition": False,
            "native_rebase": False, "native_after": None},
    }
    return options, journal


def assert_current_sg(runtime, entry, expected_options, expected_journal):
    """Read-only assertions on real runtime data and immutable HA options."""
    assert dict(entry.options) == expected_options
    assert runtime.panasonic_archive == expected_journal["panasonic_archive"]
    assert runtime.sg_boost.manual_hold is True
    assert runtime.sg_boost.completion_hold is True
    assert runtime.sg_boost._general_reference == expected_journal["sg_boost"]["general_reference"]
    assert runtime.sg_boost.auto_enabled is False
    assert runtime.sg_boost.desired_on is False and runtime.sg_boost.owned is False
    overview = runtime.panasonic.overview()
    assert overview["context"] == "space_heating" and overview["context_reliable"] is True
    assert overview["power_scope"] == "split" and overview["power_complete"] is True
    assert overview["power_supply1_w"] == 1400 and overview["power_supply2_w"] == 250
    assert overview["power_w"] == 1650
    assert overview["compressor_running"] is True and overview["compressor_frequency_hz"] == 35
    assert overview["sg_status"] == "unknown" and overview["sg_status_confirmed"] is False
    assert overview["sg_effect_confirmed"] is False
    assert runtime.panasonic.settings["power_activity_threshold_w"] == 200
    assert runtime.panasonic.settings["power_supply1_role"] == "unconfirmed"
    assert runtime.panasonic.settings["power_supply2_role"] == "unconfirmed"
    assert overview["power_activity"]["active"] is True
    assert overview["power_activity"]["threshold_w"] == 200


class FailureEvidence(logging.Handler):
    def __init__(self):
        super().__init__()
        self.failures = []

    def emit(self, record):
        if record.exc_info:
            error = record.exc_info[1]
            self.failures.append((type(error).__name__, str(error)))


async def check(source: Path, expected_failure: bool, current_sg: bool = False):
    # Imports must be real Core modules; importing tests/conftest.py defeats this
    # check. In particular ConfigEntry itself provides immutable mappings.
    from homeassistant import auth, bootstrap, loader
    from homeassistant.components.http import server as http_server
    from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.storage import Store

    core_version = version("homeassistant")
    if not core_version.startswith("2026.10."):
        raise AssertionError(f"Expected Home Assistant 2026.10.x, found {core_version}")
    options, journal = current_sg_fixture() if current_sg else fixture()
    expected_options, expected_journal = deepcopy(options), deepcopy(journal)
    with tempfile.TemporaryDirectory(prefix="solarpilot-real-core-") as directory:
        config_dir = Path(directory)
        target = config_dir / "custom_components" / "solar_pilot"
        shutil.copytree(source / "custom_components" / "solar_pilot", target,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "userfiles"))
        sys.path.insert(0, str(config_dir))
        hass = HomeAssistant(str(config_dir))
        loader.async_setup(hass)
        hass.config_entries = ConfigEntries(hass, {})
        assert await bootstrap.async_load_base_functionality(hass)
        hass.auth = await auth.auth_manager_from_config(hass, [], [])
        entry = ConfigEntry(
            version=1, minor_version=1, domain="solar_pilot", title="SolarPilot smoke",
            source="user", unique_id="solar_pilot", options=options,
            data={"grid_entity": "sensor.synthetic_grid", "pv_entity": "sensor.synthetic_pv"},
            discovery_keys=MappingProxyType({}), subentries_data=None,
        )
        assert isinstance(entry.options, MappingProxyType)
        assert isinstance(entry.data, MappingProxyType)
        hass.states.async_set("sensor.synthetic_grid", "0", {"unit_of_measurement": "W"})
        hass.states.async_set("sensor.synthetic_pv", "0", {"unit_of_measurement": "W"})
        hass.states.async_set("switch.synthetic_load", "off")
        if current_sg:
            # No Shelly integration/device is configured: the relay cannot open
            # a physical transport. Every state below is local synthetic data.
            hass.states.async_set("switch.synthetic_sg", "off")
            hass.states.async_set("sensor.synthetic_tank", "48", {"unit_of_measurement": "°C"})
            hass.states.async_set("water_heater.synthetic_tank", "eco", {
                "temperature": 51, "current_temperature": 48, "temperature_unit": "°C"})
            hass.states.async_set("sensor.synthetic_activity", "WATER")
            hass.states.async_set("climate.synthetic_zone", "heat", {
                "hvac_action": "idle", "temperature": 20, "current_temperature": 20,
                "temperature_unit": "°C"})
            hass.states.async_set("sensor.synthetic_supply1", "1.4", {"unit_of_measurement": "kW"})
            hass.states.async_set("sensor.synthetic_supply2", "0", {"unit_of_measurement": "W"})
            hass.states.async_set("sensor.synthetic_frequency", "0", {"unit_of_measurement": "Hz"})
            hass.states.async_set("binary_sensor.synthetic_sg_received", "on")
        store = Store(hass, 1, f"solar_pilot.{entry.entry_id}")
        await store.async_save(journal)
        physical_calls = []

        def watch(event):
            if event.data.get("domain") in {"climate", "water_heater", "switch", "number", "button", "script"} or (
                    current_sg and event.data.get("domain") in {"homeassistant", "shelly"}):
                physical_calls.append(dict(event.data))

        remove_watch = hass.bus.async_listen("call_service", watch)
        evidence = FailureEvidence()
        logging.getLogger().addHandler(evidence)
        # Core 2026.10 binds the HTTP socket during dependency setup. Keep its
        # actual server/router/auth/registration APIs, but exercise them offline.
        # No SolarPilot constructor, migration, Store, platform or entity code
        # is patched. Source-IP discovery is irrelevant to this local check.
        async def no_http_io(*_args, **_kwargs):
            return None

        async def loopback_source(*_args, **_kwargs):
            return "127.0.0.1"

        patches = [patch.object(http_server.HomeAssistantHTTP, "async_bind", no_http_io),
                   patch.object(http_server.HomeAssistantHTTP, "start", no_http_io),
                   patch("homeassistant.components.http.async_get_source_ip", loopback_source)]
        for replacement in patches:
            replacement.start()
        try:
            await hass.config_entries.async_add(entry)
            await hass.async_block_till_done()
            if expected_failure:
                assert entry.state is ConfigEntryState.SETUP_ERROR, entry.state
                assert any(kind == "TypeError" and "mappingproxy" in message
                           for kind, message in evidence.failures), evidence.failures
                assert dict(entry.options) == expected_options
                assert await store.async_load() == expected_journal
                assert not physical_calls, physical_calls
                return {"core": core_version, "result": "expected beta.62 failure reproduced",
                        "error": "TypeError: cannot pickle 'mappingproxy' object",
                        "configuration_and_store_unchanged": True}
            assert entry.state is ConfigEntryState.LOADED, (entry.state, evidence.failures)
            assert not evidence.failures, evidence.failures
            runtime = entry.runtime_data
            assert runtime.data_loaded and not runtime._closed
            assert runtime.mode == "observe"
            assert runtime.configs["synthetic_load"]["control_entity"] == "switch.synthetic_load"
            assert runtime.device_modes["synthetic_load"] == "disabled"
            assert runtime.energy_kwh == 17.25
            assert entry.options["devices"] == expected_options["devices"]
            assert entry.options["priority_board"] == expected_options["priority_board"]
            assert entry.options["sg_boost"]["enabled"] is False
            assert entry.options["sg_boost"]["entity_id"] == ("switch.synthetic_sg" if current_sg else "")
            assert entry.options["sg_boost"]["tank_temperature_entity"] == "sensor.synthetic_tank"
            assert "dhw" not in entry.options and "smart_climate" not in entry.options
            archive = deepcopy(runtime.panasonic_archive)
            if current_sg:
                assert archive == expected_journal["panasonic_archive"]
                observed = runtime.panasonic.overview()
                assert observed["power_w"] == 1400 and observed["power_complete"] is True
                assert observed["power_supply1_w"] == 1400 and observed["power_supply2_w"] == 0
                assert observed["compressor_running"] is False and observed["compressor_frequency_hz"] == 0
                assert observed["sg_status"] == "active" and observed["sg_status_confirmed"] is True
                assert observed["sg_effect_confirmed"] is False
                hass.states.async_set("sensor.synthetic_frequency", "unknown", {"unit_of_measurement": "Hz"})
                observed = runtime.panasonic.overview()
                assert observed["compressor_running"] is None and observed["compressor_frequency_hz"] is None
                # WATER is only programme context, never compressor proof.
                assert observed["activity"] == "WATER" and observed["sg_effect_confirmed"] is False
                # Existing bindings automatically gain the default read-only
                # interpretation. No new role, threshold or helper entity is
                # entered into these immutable pre-upgrade options.
                assert not any(key in entry.options["sg_boost"] for key in (
                    "power_activity_threshold_w", "power_supply1_role", "power_supply2_role"))
                control_before = deepcopy(runtime.sg_boost.snapshot())
                display = observed["power_activity"]
                assert display["label"] == "Warmtepomp werkt" and display["active"] is True
                assert display["threshold_w"] == 200 and display["function"] is None
                hass.states.async_set("sensor.synthetic_supply1", "58", {"unit_of_measurement": "W"})
                low = runtime.panasonic.overview()["power_activity"]
                assert low["label"] == "Basisverbruik" and low["active"] is False
                assert [row["state"] for row in low["supplies"]] == ["basis", "off"]
                assert [row["watts"] for row in low["supplies"]] == [58, 0]
                hass.states.async_set("sensor.synthetic_supply1", "0", {"unit_of_measurement": "W"})
                off = runtime.panasonic.overview()["power_activity"]
                assert off["label"] == "Geen elektrisch verbruik" and off["active"] is False
                assert runtime.sg_boost.snapshot() == control_before
                assert dict(entry.options) == expected_options and not physical_calls
                hass.states.async_set("sensor.synthetic_supply1", "1.4", {"unit_of_measurement": "kW"})
                hass.states.async_set("sensor.synthetic_supply2", "unavailable", {"unit_of_measurement": "W"})
                observed = runtime.panasonic.overview()
                assert observed["power_w"] is None and observed["power_complete"] is False
                assert observed["power_supply1_w"] == 1400 and observed["power_supply2_w"] is None
                hass.states.async_set("sensor.synthetic_supply2", "250", {"unit_of_measurement": "W"})
                hass.states.async_set("sensor.synthetic_frequency", "35", {"unit_of_measurement": "Hz"})
                hass.states.async_set("binary_sensor.synthetic_sg_received", "unknown")
                assert_current_sg(runtime, entry, expected_options, expected_journal)
            else:
                assert archive["backup_options"] == expected_options
                assert archive["backup_store"] == expected_journal
            persisted = await store.async_load()
            assert persisted["panasonic_archive"] == archive
            registry = er.async_get(hass)
            rows = er.async_entries_for_config_entry(registry, entry.entry_id)
            domains = {row.entity_id.split(".", 1)[0] for row in rows}
            assert domains == {"sensor", "binary_sensor", "select", "number", "button", "switch"}, domains
            assert all(hass.states.get(row.entity_id) is not None for row in rows)
            assert not physical_calls, physical_calls
            assert await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED
            assert entry.runtime_data is not runtime
            assert runtime._closed
            assert entry.runtime_data.panasonic_archive == archive
            assert entry.options["devices"] == expected_options["devices"]
            if current_sg:
                assert_current_sg(entry.runtime_data, entry, expected_options, expected_journal)
            assert not physical_calls, physical_calls
            assert await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            assert not evidence.failures, evidence.failures
            assert not physical_calls, physical_calls
            if current_sg:
                persisted = await store.async_load()
                assert dict(entry.options) == expected_options
                assert persisted["panasonic_archive"] == expected_journal["panasonic_archive"]
                assert persisted["sg_boost"]["manual_hold"] is True
                assert persisted["sg_boost"]["completion_hold"] is True
                assert persisted["sg_boost"]["general_reference"] == expected_journal["sg_boost"]["general_reference"]
            return {"core": core_version, "result": "production setup, reload and unload passed",
                    "actual_platforms": sorted(domains), "registered_entities": len(rows),
                    "immutable_entry_mappings": True, "private_archive_exact": True,
                    "configuration_preserved": True, "physical_service_calls": 0,
                    **({"fixture": "current general SG with split read-only sources",
                        "immutable_nested_options_exact": True, "manual_and_completion_holds_preserved": True,
                        "split_units_zero_missing_and_sum": True, "compressor_and_sg_proof_separate": True,
                        "automatic_power_display_without_new_settings": True}
                       if current_sg else {})}
        finally:
            logging.getLogger().removeHandler(evidence)
            remove_watch()
            await hass.async_stop(force=True)
            for replacement in reversed(patches):
                replacement.stop()
            sys.path.remove(str(config_dir))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expect-mappingproxy-failure", action="store_true")
    parser.add_argument("--current-sg-fixture", action="store_true")
    args = parser.parse_args()
    if args.expect_mappingproxy_failure and args.current_sg_fixture:
        parser.error("The immutable beta.62 failure uses the unchanged legacy fixture")
    logging.basicConfig(level=logging.WARNING)
    result = asyncio.run(check(args.source_root.resolve(), args.expect_mappingproxy_failure,
                              args.current_sg_fixture))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
