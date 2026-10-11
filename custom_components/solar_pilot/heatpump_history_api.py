"""Authenticated read-only heat-pump history, isolated per SolarPilot entry."""
from __future__ import annotations

from datetime import date
import re

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import BASE_COMMAND_MESSAGE_SCHEMA
from homeassistant.core import callback

from .const import DOMAIN
from .heatpump_history_runtime import configured_history_sources

if type(BASE_COMMAND_MESSAGE_SCHEMA).__module__.split(".", 1)[0] == "probatio":
    import probatio as vol
else:
    import voluptuous as vol

COMMAND = "solar_pilot/heatpump_history"
_REGISTERED = f"{DOMAIN}_heatpump_history_api"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _runtime(hass, entry_id):
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or getattr(entry, "domain", "") != DOMAIN:
        return None
    state = getattr(entry, "state", None)
    if state is not None and getattr(state, "value", state) != "loaded":
        return None
    runtime = getattr(entry, "runtime_data", None)
    if (runtime is None or getattr(runtime, "_closed", True)
            or getattr(getattr(runtime, "entry", None), "entry_id", None) != entry_id
            or not getattr(getattr(runtime, "heatpump_history", None), "loaded", False)):
        return None
    return runtime


@websocket_api.websocket_command({
    vol.Required("type"): COMMAND,
    vol.Required("config_entry_id"): str,
    vol.Optional("date"): str,
})
@callback
def websocket_heatpump_history(hass, connection, msg):
    """No settings, replay, service call, ownership or apply operation."""
    user = getattr(connection, "user", None)
    if user is None:
        connection.send_error(msg["id"], "unauthorized", "Geen leestoegang tot deze warmtepomphistoriek")
        return
    if (type(msg.get("config_entry_id")) is not str or not msg["config_entry_id"]
            or set(msg)-{"id", "type", "config_entry_id", "date"}
            or msg.get("type", COMMAND) != COMMAND):
        connection.send_error(msg["id"], "invalid_format", "Ongeldige SolarPilot-historiekvraag")
        return
    runtime = _runtime(hass, msg["config_entry_id"])
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "SolarPilot is niet geladen")
        return
    recorder = runtime.heatpump_history
    if not getattr(user, "is_admin", False):
        sources = configured_history_sources(runtime) | recorder.access_sources
        try:
            permitted = (bool(sources) and recorder.access_sources_complete and all(
                user.permissions.check_entity(entity, POLICY_READ) for entity in sources))
        except Exception:
            permitted = False
        if not permitted:
            connection.send_error(msg["id"], "unauthorized", "Geen leestoegang tot alle gebruikte warmtepomp- en SG-bronnen")
            return
    day = msg.get("date")
    try:
        if day is not None:
            if type(day) is not str or not _DATE.fullmatch(day):
                raise ValueError("Invalid history date")
            date.fromisoformat(day)
        result = recorder.detail(day)
    except (ValueError, TypeError):
        connection.send_error(msg["id"], "invalid_date", "Kies een datum binnen de bewaarde warmtepomphistoriek")
        return
    except Exception:
        connection.send_error(msg["id"], "history_failed", "Warmtepomphistoriek tijdelijk niet beschikbaar; opgeslagen gegevens blijven behouden")
        return
    if _runtime(hass, msg["config_entry_id"]) is not runtime:
        connection.send_error(msg["id"], "not_loaded", "SolarPilot is herladen; open de historiek opnieuw")
        return
    connection.send_result(msg["id"], result)


@callback
def async_register_heatpump_history_api(hass):
    if hass.data.get(_REGISTERED):
        return
    websocket_api.async_register_command(hass, websocket_heatpump_history)
    hass.data[_REGISTERED] = True
