"""Verify Marstek saving/reopening through real Home Assistant Core options.

Run outside pytest with Core 2026.10.x and Python 3.14. The ordinary unit suite
intentionally provides HA doubles. This check uses a disposable local config,
synthetic sensor states, actual options schemas/manager, Core entry persistence
and production setup/reload. Only HTTP socket/source-IP I/O is disabled; no
SolarPilot flow, transaction, runtime, selector or storage method is replaced.
No native battery integration, transport or physical device is configured.
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


def selected_value(form, name):
    """Read actual Core schema defaults/suggestions, as its frontend does."""
    import voluptuous as vol

    marker = next(key for key in form["data_schema"].schema
                  if getattr(key, "schema", key) == name)
    description = getattr(marker, "description", None) or {}
    if "suggested_value" in description:
        return description["suggested_value"]
    default = getattr(marker, "default", vol.UNDEFINED)
    return default() if default is not vol.UNDEFINED else None


async def monitor_menu(hass, entry):
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    assert result["type"] == "menu" and result["step_id"] == "init"
    flow_id = result["flow_id"]
    result = await manager.async_configure(flow_id, {"next_step_id": "storage_hub"})
    assert "battery" in result["menu_options"]
    result = await manager.async_configure(flow_id, {"next_step_id": "battery"})
    assert result["step_id"] == "battery" and "battery_marstek" in result["menu_options"]
    return flow_id, result


async def check(source):
    # Import Home Assistant before voluptuous, matching production Core's
    # supported schema implementation. Do not import tests/conftest.py.
    from homeassistant import auth, bootstrap, loader
    from homeassistant.components.http import server as http_server
    from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
    from homeassistant.core import HomeAssistant

    core_version = version("homeassistant")
    assert core_version.startswith("2026.10."), core_version
    with tempfile.TemporaryDirectory(prefix="solarpilot-battery-options-") as directory:
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
            version=1, minor_version=1, domain="solar_pilot", title="Synthetic battery save",
            source="user", unique_id="solar_pilot", options={"devices": [], "batteries": []},
            data={"grid_entity": "sensor.synthetic_grid", "pv_entity": "sensor.synthetic_pv"},
            discovery_keys=MappingProxyType({}), subentries_data=None,
        )
        for entity, value, unit in (
            ("sensor.synthetic_grid", "0", "W"), ("sensor.synthetic_pv", "1500", "W"),
            ("sensor.synthetic_battery_ac", "250", "W"), ("sensor.synthetic_battery_soc", "67", "%"),
        ):
            hass.states.async_set(entity, value, {"unit_of_measurement": unit})

        physical_calls = []
        service_call = type(hass.services).async_call

        async def observe_service(registry, domain, service, *args, **kwargs):
            if domain in {"climate", "water_heater", "switch", "number", "button", "script",
                          "homeassistant", "shelly", "marstek"}:
                physical_calls.append((domain, service))
            return await service_call(registry, domain, service, *args, **kwargs)

        async def no_http_io(*_args, **_kwargs):
            return None

        async def loopback_source(*_args, **_kwargs):
            return "127.0.0.1"

        patches = [patch.object(http_server.HomeAssistantHTTP, "async_bind", no_http_io),
                   patch.object(http_server.HomeAssistantHTTP, "start", no_http_io),
                   patch("homeassistant.components.http.async_get_source_ip", loopback_source),
                   patch.object(type(hass.services), "async_call", observe_service)]
        for replacement in patches:
            replacement.start()
        try:
            await hass.config_entries.async_add(entry)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED, entry.state
            assert isinstance(entry.options, MappingProxyType)
            original_data = deepcopy(dict(entry.data))
            baseline = deepcopy(dict(entry.options))
            runtime = entry.runtime_data
            manager = hass.config_entries.options
            flow_id, menu = await monitor_menu(hass, entry)
            assert "battery_marstek_add" not in menu["menu_options"]
            form = await manager.async_configure(flow_id, {"next_step_id": "battery_marstek"})
            assert form["step_id"] == "battery_marstek"
            assert not selected_value(form, "power_entity") and not selected_value(form, "power_sign")
            assert selected_value(form, "ac_power_confirmed") is False

            inputs = {"name": "Synthetic Venus", "power_entity": "sensor.synthetic_battery_ac",
                      "power_sign": "discharge_positive", "ac_power_confirmed": True,
                      "soc_entity": "sensor.synthetic_battery_soc", "phase_hint": "l2"}
            pending = await manager.async_configure(flow_id, inputs)
            assert pending["step_id"] == "apply_changes" and not pending["errors"]
            assert dict(entry.options) == baseline and not runtime.battery_fleet.configs
            unconfirmed = await manager.async_configure(flow_id, {"confirm": False})
            assert unconfirmed["errors"]["base"] == "live_change"
            assert dict(entry.options) == baseline
            final = await manager.async_configure(flow_id, {"confirm": True})
            assert final["type"] == "create_entry"
            await hass.async_block_till_done()
            assert len(entry.options["batteries"]) == 1
            saved = deepcopy(entry.options["batteries"][0])
            identity = saved["id"]
            assert all(saved[key] == value for key, value in inputs.items())
            assert saved["profile"] == "marstek_venus_e3" and saved["capacity_kwh"] == 5.12
            assert saved["control_kind"] == "read_only" and not saved["control_enabled"]
            assert not saved["exclusive_control_confirmed"]
            assert not {"number_entity", "number_sign", "charge_script", "discharge_script", "idle_script"} & saved.keys()
            assert entry.runtime_data is runtime
            assert runtime.battery_fleet.configs == {identity: saved}

            # A new flow starts from Core's saved entry, not the prior wizard's
            # in-memory draft. The main route must edit this exact monitor.
            flow_id, menu = await monitor_menu(hass, entry)
            assert "battery_marstek_add" in menu["menu_options"]
            form = await manager.async_configure(flow_id, {"next_step_id": "battery_marstek"})
            assert all(selected_value(form, key) == value for key, value in inputs.items())
            before_edit = deepcopy(dict(entry.options))
            changed = {**inputs, "name": "Updated synthetic Venus", "phase_hint": "l1"}
            pending = await manager.async_configure(flow_id, changed)
            assert pending["step_id"] == "apply_changes" and dict(entry.options) == before_edit
            final = await manager.async_configure(flow_id, {"confirm": True})
            assert final["type"] == "create_entry"
            await hass.async_block_till_done()
            assert len(entry.options["batteries"]) == 1
            saved = deepcopy(entry.options["batteries"][0])
            assert saved["id"] == identity
            assert all(saved[key] == value for key, value in changed.items())

            # Real unload/setup must reconstruct the monitor from the saved
            # options. It must not duplicate the profile or switch to a draft.
            assert await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED
            assert entry.runtime_data is not runtime and runtime._closed
            assert entry.runtime_data.battery_fleet.configs == {identity: saved}
            assert entry.options["batteries"] == [saved] and dict(entry.data) == original_data
            flow_id, _ = await monitor_menu(hass, entry)
            form = await manager.async_configure(flow_id, {"next_step_id": "battery_marstek"})
            assert all(selected_value(form, key) == value for key, value in changed.items())
            manager.async_abort(flow_id)

            # Adding another monitor is an explicit, cancellable choice. It
            # starts empty and cannot erase the existing monitor on opening.
            before_add = deepcopy(dict(entry.options))
            flow_id, _ = await monitor_menu(hass, entry)
            form = await manager.async_configure(flow_id, {"next_step_id": "battery_marstek_add"})
            assert form["step_id"] == "battery_marstek"
            assert not selected_value(form, "power_entity") and not selected_value(form, "power_sign")
            assert selected_value(form, "ac_power_confirmed") is False
            manager.async_abort(flow_id)
            assert dict(entry.options) == before_add and not physical_calls, physical_calls
            return {"core": core_version, "first_step_does_not_save": True,
                    "final_confirmation_persists_entry_options": True,
                    "reopened_form_prefilled": True, "same_id_after_edit": True,
                    "one_monitor_after_reload": True, "explicit_add_starts_empty": True,
                    "physical_service_calls": len(physical_calls)}
        finally:
            await hass.async_stop(force=True)
            for replacement in reversed(patches):
                replacement.stop()
            sys.path.remove(str(config_dir))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    print(json.dumps(asyncio.run(check(args.source_root.resolve())), sort_keys=True))


if __name__ == "__main__":
    main()
