"""Authenticated, read-only water history with complete source provenance."""
from __future__ import annotations

from datetime import date
import re

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import BASE_COMMAND_MESSAGE_SCHEMA
from homeassistant.core import callback

from .const import DOMAIN

if type(BASE_COMMAND_MESSAGE_SCHEMA).__module__.split(".", 1)[0] == "probatio":
    import probatio as vol
else:
    import voluptuous as vol

COMMAND = "solar_pilot/water_history"
_REGISTERED = f"{DOMAIN}_water_history_api"
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_ENTITY = re.compile(r"[a-z_]+\.[a-z0-9_]+\Z")
_MAX_ACCESS_SOURCES = 4096


def _runtime(hass, entry_id):
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or getattr(entry, "domain", None) != DOMAIN:
        return None
    state = getattr(entry, "state", None)
    if state is not None and getattr(state, "value", state) != "loaded":
        return None
    runtime = getattr(entry, "runtime_data", None)
    water = getattr(runtime, "water", None)
    if (runtime is None or getattr(runtime, "_closed", True) is not False
            or getattr(runtime, "entry", None) is not entry
            or getattr(entry, "entry_id", None) != entry_id
            or getattr(water, "loaded", False) is not True
            or getattr(water, "_closed", True) is not False):
        return None
    return runtime


def _source_set(value):
    if (not isinstance(value, (set, frozenset, tuple, list))
            or len(value) > _MAX_ACCESS_SOURCES):
        raise ValueError("Invalid source provenance")
    if any(not isinstance(entity, str) or not 0 < len(entity) <= 256
           or not _ENTITY.fullmatch(entity) for entity in value):
        raise ValueError("Invalid source provenance")
    return frozenset(value)


def _access_snapshot(water):
    """Current and retained water/context sources are one permission boundary."""
    return (_source_set(water.configured_sources()), _source_set(water.access_sources),
            water.access_sources_complete is True)


def _permitted(user, snapshot):
    current, retained, complete = snapshot
    sources = current | retained
    return complete and bool(sources) and all(
        user.permissions.check_entity(entity, POLICY_READ) is True for entity in sources)


@websocket_api.websocket_command({
    vol.Required("type"): COMMAND,
    vol.Required("config_entry_id"): str,
    vol.Optional("date"): str,
})
@callback
def websocket_water_history(hass, connection, msg):
    """Read one retained local day; never query arbitrary sources or actuation."""
    identifier = msg.get("id") if isinstance(msg, dict) else None
    user = getattr(connection, "user", None)
    if user is None:
        connection.send_error(identifier, "unauthorized", "Geen leestoegang tot deze waterhistoriek")
        return
    if (not isinstance(msg, dict) or set(msg)-{"id", "type", "config_entry_id", "date"}
            or type(identifier) is not int or identifier <= 0 or msg.get("type") != COMMAND
            or type(msg.get("config_entry_id")) is not str or not 0 < len(msg["config_entry_id"]) <= 200):
        connection.send_error(identifier, "invalid_format", "Ongeldige SolarPilot-waterhistoriekvraag")
        return
    runtime = _runtime(hass, msg["config_entry_id"])
    if runtime is None:
        connection.send_error(identifier, "not_loaded", "SolarPilot-waterhistoriek is niet geladen")
        return
    water = runtime.water
    admin = getattr(user, "is_admin", False) is True
    before = None
    if not admin:
        try:
            before = _access_snapshot(water)
            permitted = _permitted(user, before)
        except Exception:
            permitted = False
        if not permitted:
            connection.send_error(identifier, "unauthorized", "Geen leestoegang tot alle gebruikte water- en contextbronnen")
            return
    day = msg.get("date")
    try:
        if "date" in msg:
            if type(day) is not str or not _DATE.fullmatch(day):
                raise ValueError("Invalid history date")
            date.fromisoformat(day)
        result = water.detail(day)
        if not isinstance(result, dict):
            raise RuntimeError("Invalid water history result")
    except (ValueError, TypeError):
        connection.send_error(identifier, "invalid_date", "Kies een datum binnen de bewaarde waterhistoriek")
        return
    except Exception:
        connection.send_error(identifier, "history_failed", "Waterhistoriek tijdelijk niet beschikbaar; opgeslagen gegevens blijven behouden")
        return
    if (_runtime(hass, msg["config_entry_id"]) is not runtime
            or getattr(runtime, "water", None) is not water):
        connection.send_error(identifier, "not_loaded", "SolarPilot is herladen; open de waterhistoriek opnieuw")
        return
    if not admin:
        try:
            after = _access_snapshot(water)
            permitted = after == before and _permitted(user, after)
        except Exception:
            permitted = False
        if not permitted:
            connection.send_error(identifier, "unauthorized", "Waterbronnen of leesrechten zijn gewijzigd; open de historiek opnieuw")
            return
    if (_runtime(hass, msg["config_entry_id"]) is not runtime
            or getattr(runtime, "water", None) is not water):
        connection.send_error(identifier, "not_loaded", "SolarPilot is herladen; open de waterhistoriek opnieuw")
        return
    connection.send_result(identifier, result)


@callback
def async_register_water_history_api(hass):
    if hass.data.get(_REGISTERED):
        return
    websocket_api.async_register_command(hass, websocket_water_history)
    hass.data[_REGISTERED] = True
