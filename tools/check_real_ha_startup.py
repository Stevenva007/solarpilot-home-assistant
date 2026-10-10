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


class FailureEvidence(logging.Handler):
    def __init__(self):
        super().__init__()
        self.failures = []

    def emit(self, record):
        if record.exc_info:
            error = record.exc_info[1]
            self.failures.append((type(error).__name__, str(error)))


async def check(source: Path, expected_failure: bool):
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
    options, journal = fixture()
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
        store = Store(hass, 1, f"solar_pilot.{entry.entry_id}")
        await store.async_save(journal)
        physical_calls = []

        def watch(event):
            if event.data.get("domain") in {"climate", "water_heater", "switch", "number", "button", "script"}:
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
            assert entry.options["sg_boost"]["entity_id"] == ""
            assert entry.options["sg_boost"]["tank_temperature_entity"] == "sensor.synthetic_tank"
            assert "dhw" not in entry.options and "smart_climate" not in entry.options
            archive = deepcopy(runtime.panasonic_archive)
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
            assert not physical_calls, physical_calls
            assert await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            assert not evidence.failures, evidence.failures
            assert not physical_calls, physical_calls
            return {"core": core_version, "result": "production setup, reload and unload passed",
                    "actual_platforms": sorted(domains), "registered_entities": len(rows),
                    "immutable_entry_mappings": True, "private_archive_exact": True,
                    "configuration_preserved": True, "physical_service_calls": 0}
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
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    result = asyncio.run(check(args.source_root.resolve(), args.expect_mappingproxy_failure))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
