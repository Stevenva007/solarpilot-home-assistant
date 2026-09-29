"""Authenticated, read-only history query. Full sessions are never state attributes."""
from __future__ import annotations

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import BASE_COMMAND_MESSAGE_SCHEMA
from homeassistant.core import callback

from .const import DOMAIN

# Match the schema engine used by this HA version. Recent HA versions use
# probatio; older versions use voluptuous. Do not mix their Required markers
# merely because both libraries happen to be installed.
_SCHEMA_BACKEND = type(BASE_COMMAND_MESSAGE_SCHEMA).__module__.split(".", 1)[0]
if _SCHEMA_BACKEND == "probatio":
    import probatio as vol
else:
    import voluptuous as vol

COMMAND = "solar_pilot/consumer_history"
_REGISTERED = f"{DOMAIN}_consumer_history_api"


@websocket_api.websocket_command({
    vol.Required("type"): COMMAND,
    vol.Required("config_entry_id"): str,
    vol.Required("device_id"): str,
    vol.Optional("date"): str,
})
@callback
def websocket_consumer_history(hass, connection, msg):
    """Only this entry's configured consumers, with normal HA read permissions."""
    entry = hass.config_entries.async_get_entry(msg["config_entry_id"])
    runtime = getattr(entry, "runtime_data", None) if entry is not None and getattr(entry, "domain", "") == DOMAIN else None
    if runtime is None or getattr(runtime, "_closed", True):
        connection.send_error(msg["id"], "not_loaded", "SolarPilot is niet geladen")
        return
    device_id = msg["device_id"]
    if device_id not in runtime.configs:
        connection.send_error(msg["id"], "not_found", "Deze SolarPilot-verbruiker bestaat niet")
        return
    cfg = runtime.configs[device_id]
    entities = {cfg.get("control_entity"), cfg.get("active_entity"), cfg.get("power_entity"),
                cfg.get("dishwasher_state_entity"), cfg.get("cycle_program_entity"),
                runtime.entity_id("sensor", "status", device_id)} - {None, ""}
    user = connection.user
    if user is None or (not user.is_admin and (not entities or any(
        not user.permissions.check_entity(entity_id, POLICY_READ) for entity_id in entities
    ))):
        connection.send_error(msg["id"], "unauthorized", "Geen leestoegang tot deze verbruiker")
        return
    try:
        result = runtime.consumer_history.detail(device_id, msg.get("date"))
    except (ValueError, TypeError):
        connection.send_error(msg["id"], "invalid_date", "Kies een datum binnen de laatste 30 dagen")
        return
    # Only the selected consumer's live status is returned, never other entities.
    result["current_status"] = runtime.result.reasons.get(device_id, "Initialiseren")
    result["mode"] = runtime.device_modes.get(device_id, "disabled")
    connection.send_result(msg["id"], result)


@callback
def async_register_history_api(hass):
    if hass.data.get(_REGISTERED):
        return
    websocket_api.async_register_command(hass, websocket_consumer_history)
    hass.data[_REGISTERED] = True
