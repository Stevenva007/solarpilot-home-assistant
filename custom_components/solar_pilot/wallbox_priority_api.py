"""Scoped Wallbox priority preferences; this API never operates an appliance."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.core import Context, callback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

SERVICE_WALLBOX_PRIORITY_CONTROL = "wallbox_priority_control"
WALLBOX_PRIORITY_COMMAND = "solar_pilot/wallbox_priority"
WALLBOX_PRIORITY_OPTIONS = ("auto", "30m", "1h", "2h", "3h", "4h", "5h", "until_auto")


def validate_priority_choice(target, option):
    """Keep targets and the eight explicit choices exact, without coercion."""
    if (type(target) is not str or not target or len(target) > 200
            or target not in ("global", "dhw_extra")
            and (not target.startswith("device:") or not target[7:])):
        raise vol.Invalid("Kies een bestaande SolarPilot-voorrangsschakelaar.")
    if type(option) is not str or option not in WALLBOX_PRIORITY_OPTIONS:
        raise vol.Invalid("Kies automatisch, 30 minuten, 1 tot 5 uur of tot automatisch.")
    return target, option


def validate_service_data(data):
    if (not isinstance(data, dict)
            or set(data) - {"config_entry_id", "target", "option"}
            or not {"target", "option"} <= set(data)):
        raise vol.Invalid("Onvolledige of onbekende voorrangsopdracht.")
    if "config_entry_id" in data and (type(data["config_entry_id"]) is not str
                                      or not data["config_entry_id"]):
        raise vol.Invalid("Kies één geladen SolarPilot-configuratie.")
    validate_priority_choice(data["target"], data["option"])
    return data


WALLBOX_PRIORITY_SERVICE_SCHEMA = vol.All(vol.Schema({
    vol.Optional("config_entry_id"): str,
    vol.Required("target"): str,
    vol.Required("option"): str,
}), validate_service_data)


def _current_runtime(runtime):
    entry = getattr(runtime, "entry", None)
    if (getattr(runtime, "_closed", True) or entry is None
            or getattr(entry, "domain", None) != DOMAIN
            or getattr(entry, "runtime_data", None) is not runtime
            or getattr(runtime, "data_loaded", False) is not True):
        raise HomeAssistantError("SolarPilot-configuratie niet geladen; vernieuw de bediening.")
    current = runtime.hass.config_entries.async_get_entry(entry.entry_id)
    if current is not entry:
        raise HomeAssistantError("SolarPilot is herladen; vernieuw de bediening.")


def priority_choice_view(runtime, target):
    """Use only the manager's eligible current targets, never submitted entities."""
    manager = getattr(runtime, "wallbox_priority", None)
    overview = manager.overview() if manager is not None else {}
    if target == "global":
        result = overview.get("general")
    elif target == "dhw_extra":
        result = overview.get("sg_boost")
    elif type(target) is str and target.startswith("device:"):
        result = overview.get("devices", {}).get(target[7:])
    else:
        result = None
    return result if isinstance(result, dict) and result.get("eligible") is True else None


def _binding(runtime, target):
    """A permission lookup may await; do not silently adopt a changed profile."""
    _current_runtime(runtime)
    if priority_choice_view(runtime, target) is None:
        raise HomeAssistantError("Deze voorrangsschakelaar bestaat niet of geldt niet voor dit toestel.")
    return runtime.wallbox_priority.scope(target)


async def async_set_wallbox_priority(runtime, target, option, *, context=None):
    """One authorization path for native switches, selects, service and WS."""
    validate_priority_choice(target, option)
    binding = _binding(runtime, target)
    user_id = getattr(context, "user_id", None)
    if user_id is not None:
        if type(user_id) is not str or not user_id:
            raise HomeAssistantError("Alleen een Home Assistant-beheerder mag deze voorrang wijzigen.")
        user = await runtime.hass.auth.async_get_user(user_id)
        if user is None or user.is_admin is not True:
            raise HomeAssistantError("Alleen een Home Assistant-beheerder mag deze voorrang wijzigen.")
    if _binding(runtime, target) != binding:
        raise HomeAssistantError("De toestelkoppeling is veranderd; vernieuw de bediening.")
    # The runtime repeats epoch and binding checks after its own lock wait and
    # durably saves the preference. No immediate tick or device command follows.
    return await runtime.async_set_wallbox_priority(
        target, option, context=context, expected_scope=binding)


async def async_handle_wallbox_priority_control(hass, call):
    data = validate_service_data(call.data)
    entry_id = data.get("config_entry_id")
    entries = [entry for entry in hass.config_entries.async_entries(DOMAIN)
               if not entry_id or entry.entry_id == entry_id]
    if len(entries) != 1 or getattr(entries[0], "runtime_data", None) is None:
        raise HomeAssistantError("Kies één geladen SolarPilot-configuratie.")
    return await async_set_wallbox_priority(
        entries[0].runtime_data, data["target"], data["option"],
        context=getattr(call, "context", None))


async def websocket_wallbox_priority(hass, connection, msg):
    """Only the authenticated connection supplies a user identity."""
    user = connection.user
    if user is None or user.is_admin is not True or type(getattr(user, "id", None)) is not str:
        connection.send_error(msg["id"], "unauthorized", "Alleen beheerders mogen deze voorrang wijzigen.")
        return
    try:
        data = validate_service_data({key: value for key, value in msg.items() if key not in ("id", "type")})
        entry = hass.config_entries.async_get_entry(data.get("config_entry_id"))
        runtime = getattr(entry, "runtime_data", None) if getattr(entry, "domain", None) == DOMAIN else None
        if runtime is None:
            connection.send_error(msg["id"], "not_loaded", "SolarPilot is niet geladen.")
            return
        result = await async_set_wallbox_priority(
            runtime, data["target"], data["option"], context=Context(user_id=user.id))
    except (vol.Invalid, HomeAssistantError) as err:
        connection.send_error(msg["id"], "invalid_options", str(err))
        return
    connection.send_result(msg["id"], result)


@callback
def async_register_wallbox_priority_api(hass):
    """Register once; schema follows the active HA websocket schema engine."""
    from homeassistant.components import websocket_api
    from homeassistant.components.websocket_api.messages import BASE_COMMAND_MESSAGE_SCHEMA
    from homeassistant.helpers.service import async_register_admin_service

    if type(BASE_COMMAND_MESSAGE_SCHEMA).__module__.split(".", 1)[0] == "probatio":
        import probatio as ws_vol
    else:
        import voluptuous as ws_vol
    key = DOMAIN + "_wallbox_priority_api"
    if not hass.data.get(key):
        command = websocket_api.websocket_command({
            ws_vol.Required("type"): WALLBOX_PRIORITY_COMMAND,
            ws_vol.Required("config_entry_id"): str,
            ws_vol.Required("target"): str,
            ws_vol.Required("option"): str,
        })(websocket_api.async_response(websocket_wallbox_priority))
        websocket_api.async_register_command(hass, command)
        hass.data[key] = True
    if not hass.services.has_service(DOMAIN, SERVICE_WALLBOX_PRIORITY_CONTROL):
        async def handle(call):
            await async_handle_wallbox_priority_control(hass, call)
        async_register_admin_service(hass, DOMAIN, SERVICE_WALLBOX_PRIORITY_CONTROL, handle,
                                     schema=WALLBOX_PRIORITY_SERVICE_SCHEMA)
