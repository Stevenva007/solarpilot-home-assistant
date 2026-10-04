"""SolarPilot integration entry point."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .frontend import async_register_frontend, async_unregister_frontend
from .consumer_history_api import async_register_history_api
from .analysis_api import async_register_analysis_api
from .learning_api import async_register_learning_api
from .pv_forecast_api import async_register_pv_api
from .priority_api import async_register_priority_api
from .pv_forecast import PV_SENSOR_DEFINITIONS
from .analysis_export import storage_key as analysis_storage_key
from .consumer_history_runtime import history_storage_key
from .private_bundle import build_private_import, delete_private_files_if_requested, load_private_bundle
from .historical import load_bundled_seed
from .dishwasher_recovery import LegacyDishwasherRecoveryRetry, recover_legacy_dishwasher

from .const import DOMAIN, PLATFORMS
from .runtime import SolarRuntime
from .dhw import DHW_NUMBERS

SERVICE_SET_CLIMATE_SETTING = "set_climate_setting"
SERVICE_SET_PLANNER_SETTING = "set_planner_setting"
_LOGGER = logging.getLogger(__name__)


async def _handle_set_climate_setting(hass: HomeAssistant, call) -> None:
    entry_id = str(call.data.get("config_entry_id") or "")
    entries = list(hass.config_entries.async_entries(DOMAIN))
    entry = next((e for e in entries if not entry_id or e.entry_id == entry_id), None)
    if entry is None or getattr(entry, "runtime_data", None) is None or entry.runtime_data._closed:
        raise ValueError("SolarPilot-configuratie niet geladen")
    await entry.runtime_data.smart_climate.async_set_setting(call.data["setting"], call.data.get("value"))


async def _handle_set_planner_setting(hass: HomeAssistant, call) -> None:
    entry_id = str(call.data.get("config_entry_id") or "")
    entries = list(hass.config_entries.async_entries(DOMAIN))
    entry = next((e for e in entries if not entry_id or e.entry_id == entry_id), None)
    if entry is None or getattr(entry, "runtime_data", None) is None or entry.runtime_data._closed:
        raise ValueError("SolarPilot-configuratie niet geladen")
    await entry.runtime_data.async_set_planner_setting(call.data["setting"], call.data.get("value"))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Roll back partial startup without flushing incompletely restored storage."""
    previous = getattr(entry, "runtime_data", None)
    try:
        return await _async_setup_entry(hass, entry)
    except BaseException:
        runtime = getattr(entry, "runtime_data", None)
        if runtime is not None and runtime is not previous:
            retry = getattr(runtime, "dishwasher_recovery_retry", None)
            try:
                if retry is not None:
                    retry.close()
            except Exception:
                _LOGGER.exception("SolarPilot herstel-listener kon na mislukte start niet sluiten")
            try:
                await runtime.close(persist=False)
            except Exception:
                _LOGGER.exception("SolarPilot kon na mislukte start niet volledig sluiten")
            try:
                await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
            except Exception:
                _LOGGER.exception("SolarPilot platforms konden na mislukte start niet sluiten")
            try:
                async_unregister_frontend(hass, final=False)
            except Exception:
                _LOGGER.exception("SolarPilot frontend kon na mislukte start niet sluiten")
            entry.runtime_data = None
        raise


async def _async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Optional installation-specific data lives outside the public repository.
    # Importing it only fills still-empty settings and enables safe monitoring /
    # advisory modules. Physical control permissions remain off and the runtime
    # always starts in Observatie.
    private_bundle = await hass.async_add_executor_job(load_private_bundle)
    imported_options, import_result = build_private_import(
        hass, dict(entry.data), dict(entry.options), bundle=private_bundle
    )
    recovered_options, dishwasher_recovery = recover_legacy_dishwasher(hass, imported_options)
    if import_result.get("changed") or dishwasher_recovery.get("changed"):
        hass.config_entries.async_update_entry(entry, options=recovered_options)
    historical_seed = await hass.async_add_executor_job(load_bundled_seed, private_bundle)
    runtime = SolarRuntime(hass, entry, historical_seed=historical_seed)
    runtime.private_bundle_import = import_result
    runtime.dishwasher_recovery_info = dishwasher_recovery
    entry.runtime_data = runtime
    # Remove only SolarPilot's orphaned virtual entities, never underlying devices.
    valid_prefixes = [f"{entry.entry_id}_{i}_" for i in runtime.configs]
    hub_suffixes = {"status", "grid", "surplus", "managed", "energy", "problem", "mode", "reset", "prepare_remove", "others_first", "learning", "reset_learning", "ems_status", "guide", "ems_solar_today", "ems_value_today", "ems_self_consumption", "battery_fleet_status", "battery_fleet_soc", "battery_fleet_power", "smart_climate_status", "smart_climate_confidence", "smart_climate_predicted_min", "smart_climate_predicted_max"}
    hub_suffixes.update(PV_SENSOR_DEFINITIONS)
    hub_suffixes.update({"electricity_cost_today", "electricity_import_cost_today", "electricity_export_revenue_today", "electricity_pv_avoided_today",
                        "local_pv_status", "local_pv_corrected_power", "local_pv_confidence", "battery_analysis_status", "battery_10_5_avoided", "phase_learning_status"})
    hub_suffixes.update(f"phase_{p}_{k}" for p in ("l1", "l2", "l3") for k in ("known", "residual"))
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
    # AEG/cloud entities can publish after SolarPilot's config-entry setup.  Keep
    # the beta.38 legacy migration alive for a short, targeted post-start window.
    # It cannot send START; a late profile is adopted through LiveOptions.
    runtime.dishwasher_recovery_retry = LegacyDishwasherRecoveryRetry(runtime)
    await runtime.dishwasher_recovery_retry.start()
    async_register_history_api(hass)
    async_register_analysis_api(hass)
    async_register_learning_api(hass)
    async_register_pv_api(hass)
    async_register_priority_api(hass)
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
    if runtime is not None and not runtime._closed:
        async with runtime._lock:
            if runtime._closed:
                return
            runtime._skip_options_reload_once = False
            await runtime.live_options.accept(dict(entry.options))
        runtime.publish()
    # No unconditional reload: ongoing leases, event listeners and timers survive.



async def async_unload_entry(hass, entry):
    runtime = entry.runtime_data
    # Do not silently lose control of a running load on reload/removal.
    # Use the dedicated Prepare for removal action first.
    async with runtime._lock:
        if not runtime.removal_overview()["ready"] and (
            runtime.dhw.busy or runtime.pending or runtime.battery_fleet.busy
            or any(s.owned for s in runtime.states.values())
            or runtime.smart_climate.removal_blocked()
            or runtime.battery_fleet.removal_blocked()
        ):
            return False
        if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
            return False
        # No tick or queued option update may reopen work after the successful
        # platform unload. close() performs recorder cleanup outside this lock.
        runtime._closed = True
    retry = getattr(runtime, "dishwasher_recovery_retry", None)
    if retry is not None:
        retry.close()
    await runtime.close()
    async_unregister_frontend(hass, final=False)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove SolarPilot-owned persistent data after the config entry is deleted."""
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()
    await Store(hass, 1, history_storage_key(entry.entry_id)).async_remove()
    await Store(hass, 1, analysis_storage_key(entry.entry_id)).async_remove()
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
