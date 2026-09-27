"""SolarPilot integration entry point."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .frontend import async_register_frontend, async_unregister_frontend
from .consumer_history_api import async_register_history_api
from .consumer_history_runtime import history_storage_key
from .private_bundle import build_private_import, delete_private_files_if_requested, load_private_bundle
from .historical import load_bundled_seed

from .const import DOMAIN, PLATFORMS
from .runtime import SolarRuntime
from .dhw import DHW_NUMBERS

SERVICE_SET_CLIMATE_SETTING = "set_climate_setting"
SERVICE_SET_PLANNER_SETTING = "set_planner_setting"


async def _handle_set_climate_setting(hass: HomeAssistant, call) -> None:
    entry_id = str(call.data.get("config_entry_id") or "")
    entries = list(hass.config_entries.async_entries(DOMAIN))
    entry = next((e for e in entries if not entry_id or e.entry_id == entry_id), None)
    if entry is None or getattr(entry, "runtime_data", None) is None:
        raise ValueError("SolarPilot-configuratie niet geladen")
    await entry.runtime_data.smart_climate.async_set_setting(call.data["setting"], call.data.get("value"))


async def _handle_set_planner_setting(hass: HomeAssistant, call) -> None:
    entry_id = str(call.data.get("config_entry_id") or "")
    entries = list(hass.config_entries.async_entries(DOMAIN))
    entry = next((e for e in entries if not entry_id or e.entry_id == entry_id), None)
    if entry is None or getattr(entry, "runtime_data", None) is None:
        raise ValueError("SolarPilot-configuratie niet geladen")
    await entry.runtime_data.async_set_planner_setting(call.data["setting"], call.data.get("value"))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Optional installation-specific data lives outside the public repository.
    # Importing it only fills still-empty settings and enables safe monitoring /
    # advisory modules. Physical control permissions remain off and the runtime
    # always starts in Observatie.
    private_bundle = await hass.async_add_executor_job(load_private_bundle)
    imported_options, import_result = build_private_import(
        hass, dict(entry.data), dict(entry.options), bundle=private_bundle
    )
    if import_result.get("changed"):
        hass.config_entries.async_update_entry(entry, options=imported_options)
    historical_seed = await hass.async_add_executor_job(load_bundled_seed, private_bundle)
    runtime = SolarRuntime(hass, entry, historical_seed=historical_seed)
    runtime.private_bundle_import = import_result
    entry.runtime_data = runtime
    # Remove only SolarPilot's orphaned virtual entities, never underlying devices.
    valid_prefixes = [f"{entry.entry_id}_{i}_" for i in runtime.configs]
    hub_suffixes = {"status", "grid", "surplus", "managed", "energy", "problem", "mode", "reset", "prepare_remove", "others_first", "learning", "reset_learning", "ems_status", "guide", "ems_solar_today", "ems_value_today", "ems_self_consumption", "battery_fleet_status", "battery_fleet_soc", "battery_fleet_power", "smart_climate_status", "smart_climate_confidence", "smart_climate_predicted_min", "smart_climate_predicted_max"}
    if runtime.capacity_settings["enabled"]:
        hub_suffixes.update({"capacity_status", "capacity_limit", "capacity_headroom"})
    if runtime.phase_settings["enabled"]:
        hub_suffixes.update({"phase_status", "phase_headroom"})
    if runtime.wallbox_settings["enabled"]:
        hub_suffixes.update({"wallbox_status", "wallbox_power"})
    if runtime.dhw.configured:
        hub_suffixes.update({"dhw_status", "dhw_temperature", "dhw_target", "dhw_enabled", "dhw_review", "dhw_takeover"})
        hub_suffixes.update("dhw_" + k for k in DHW_NUMBERS)
    registry = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(registry, entry.entry_id):
        hub = ent.unique_id.removeprefix(f"{entry.entry_id}_") in hub_suffixes
        if not hub and not any(ent.unique_id.startswith(prefix) for prefix in valid_prefixes):
            registry.async_remove(ent.entity_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await runtime.start()
    async_register_history_api(hass)
    try:
        await async_register_frontend(hass)
    except Exception:  # Frontend convenience must never disable the EMS core.
        import logging
        logging.getLogger(__name__).exception("SolarPilot frontend kon niet automatisch registreren")

    if not hass.services.has_service(DOMAIN, SERVICE_SET_CLIMATE_SETTING):
        async def handle_climate_setting(call):
            await _handle_set_climate_setting(hass, call)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_CLIMATE_SETTING,
            handle_climate_setting,
            schema=vol.Schema({
                vol.Optional("config_entry_id", default=""): str,
                vol.Required("setting"): str,
                vol.Required("value"): vol.Any(bool, int, float, str, [str]),
            }),
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_PLANNER_SETTING):
        async def handle_planner_setting(call):
            await _handle_set_planner_setting(hass, call)
        hass.services.async_register(
            DOMAIN, SERVICE_SET_PLANNER_SETTING, handle_planner_setting,
            schema=vol.Schema({
                vol.Optional("config_entry_id", default=""): str,
                vol.Required("setting"): str,
                vol.Required("value"): vol.Any(bool, int, float, str),
            }),
        )
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def _options_updated(hass, entry):
    runtime = getattr(entry, "runtime_data", None)
    if runtime is not None and getattr(runtime, "_skip_options_reload_once", False):
        runtime._skip_options_reload_once = False
        return
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    runtime = entry.runtime_data
    # Do not silently lose control of a running load on reload/removal.
    # Use the dedicated Prepare for removal action first.
    if not runtime.removal_overview()["ready"] and (
        runtime.dhw.busy or runtime.pending or runtime.battery_fleet.busy
        or any(s.owned for s in runtime.states.values())
        or runtime.smart_climate.removal_blocked()
        or runtime.battery_fleet.removal_blocked()
    ):
        return False
    await runtime.close()
    async_unregister_frontend(hass, final=False)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove SolarPilot-owned persistent data after the config entry is deleted."""
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()
    await Store(hass, 1, history_storage_key(entry.entry_id)).async_remove()
    # Remove SolarPilot-owned optional private profile/bootstrap when the private
    # bundle opted into deletion. Underlying Home Assistant integrations and
    # devices are never touched.
    await hass.async_add_executor_job(delete_private_files_if_requested)
    if hass.services.has_service("persistent_notification", "dismiss"):
        await hass.services.async_call(
            "persistent_notification", "dismiss",
            {"notification_id": f"{DOMAIN}_{entry.entry_id}"}, blocking=False,
        )
    # Config entry is already gone here. Keep the frontend only if another
    # SolarPilot entry still exists.
    if not hass.config_entries.async_entries(DOMAIN):
        async_unregister_frontend(hass, final=True)
        for service in (SERVICE_SET_CLIMATE_SETTING, SERVICE_SET_PLANNER_SETTING):
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)
