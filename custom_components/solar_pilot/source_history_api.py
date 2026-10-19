"""Permission-filtered current source links, without reading historical values."""
from __future__ import annotations

from collections.abc import Mapping
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

COMMAND = "solar_pilot/source_history"
_REGISTERED = f"{DOMAIN}_source_history_api"
_ENTITY = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
_ROLES = {
    "water": (("volume_entity", "Totale watermeterstand"),
              ("flow_entity", "Gemelde waterstroom"),
              ("leak_entity", "Gemelde lekdetectie")),
    "heatpump": (("tank_temperature_entity", "Boilertemperatuur"),
                 ("tank_target_entity", "Ingesteld boilerdoel")),
    "consumer": (
        ("power_entity", "Gemeten vermogen"), ("control_entity", "Aan-/uitstand"),
        ("active_entity", "Actieve toestand"), ("number_entity", "Ingestelde waarde"),
        ("condition_entity", "Toestelvoorwaarde"), ("interlock_entity", "Veiligheidsvoorwaarde"),
        ("dishwasher_state_entity", "Toestelstatus"), ("cycle_program_entity", "Gekozen programma"),
        ("start_button", "Startknop"), ("start_script", "Startscript"), ("stop_script", "Stopscript")),
    "battery": (
        ("soc_entity", "Laadniveau"), ("power_entity", "Gemeten batterijvermogen"),
        ("number_entity", "Ingestelde vermogenswaarde"), ("charge_script", "Laadscript"),
        ("discharge_script", "Ontlaadscript"), ("idle_script", "Rustscript")),
    "wallbox": (
        ("power_entity", "Gemeten laadvermogen"), ("status_entity", "Gemelde laadstatus"),
        ("demand_entity", "Laadvraag"), ("mode_entity", "Laadmodus"),
        ("session_mode_entity", "Sessiemodus"), ("connected_entity", "Verbinding met auto"),
        ("max_current_entity", "Gemelde stroomgrens"), ("phases_entity", "Gemeld fasegebruik")),
}


def _runtime(hass, entry_id):
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or getattr(entry, "domain", None) != DOMAIN:
        return None
    state = getattr(entry, "state", None)
    if state is not None and getattr(state, "value", state) != "loaded":
        return None
    runtime = getattr(entry, "runtime_data", None)
    if (runtime is None or getattr(runtime, "_closed", True) is not False
            or getattr(runtime, "entry", None) is not entry
            or getattr(entry, "entry_id", None) != entry_id):
        return None
    return runtime


def _heatpump_sources(runtime, source):
    """Mirror the displayed tank's registry route without reading its values."""
    monitor = getattr(runtime, "panasonic", None)
    settings = getattr(monitor, "settings", None)
    if not isinstance(settings, Mapping):
        return None
    if source == "configured":
        return {role: settings.get(role) for role, _label in _ROLES["heatpump"]}
    native = getattr(monitor, "native_program", None)
    discover = getattr(native, "display_sources", None)
    is_zone = getattr(native, "is_display_zone", None)
    if not callable(discover) or not callable(is_zone):
        return None
    temperature, target = settings.get("tank_temperature_entity", ""), settings.get("tank_target_entity", "")
    activity, zones = settings.get("activity_entity", ""), settings.get("zone_entities", [])
    if not all(isinstance(value, str) for value in (temperature, target, activity)) or not isinstance(zones, list):
        return None
    if any(not isinstance(entity, str) for entity in zones):
        return None
    try:
        sources = discover([target, temperature, activity, *zones])
        if not isinstance(sources, Mapping):
            return None
        tank = target if target.startswith(("water_heater.", "climate.")) else sources.get("tank_entity", "")
        if not isinstance(tank, str):
            return None
        zone = is_zone(tank)
        if type(zone) is not bool:
            return None
        if zone:
            tank = sources.get("tank_entity", "")
        if not isinstance(tank, str) or tank and not tank.startswith(("water_heater.", "climate.")):
            return None
        return {role: tank for role, _label in _ROLES["heatpump"]}
    except Exception:
        return None


def _configured_sources(runtime, kind, item_id, source=None):
    """Exact subject and closed roles; never discover through retained ACLs."""
    archived = False
    if kind == "water":
        config = getattr(getattr(runtime, "water", None), "settings", None)
    elif kind == "heatpump":
        config = _heatpump_sources(runtime, source)
    elif kind == "consumer":
        active = getattr(runtime, "configs", {})
        active = active if isinstance(active, Mapping) else {}
        if item_id in active:
            config = active[item_id]
        else:
            configured = getattr(getattr(runtime, "consumer_history", None), "configs", {})
            config = configured.get(item_id) if isinstance(configured, Mapping) else None
            archived = True
    elif kind == "battery":
        configured = getattr(getattr(runtime, "battery_fleet", None), "configs", {})
        config = configured.get(item_id) if isinstance(configured, Mapping) else None
    else:
        config = getattr(runtime, "wallbox_settings", None)
    if not isinstance(config, Mapping):
        return None
    fallback = {"consumer": "Toestel", "battery": "Batterij", "wallbox": "Wallbox",
                "heatpump": "Warmtepomp", "water": "Watermeter"}[kind]
    name = config.get("name")
    name = name[:120] if isinstance(name, str) and name else fallback
    rows, seen = [], set()
    for role, label in _ROLES[kind]:
        entity = config.get(role)
        if (not isinstance(entity, str) or len(entity) > 256
                or not _ENTITY.fullmatch(entity) or kind != "heatpump" and entity in seen):
            continue
        if kind == "water" and not entity.startswith("binary_sensor." if role == "leak_entity" else "sensor."):
            continue
        seen.add(entity)
        rows.append((role, label, entity))
    return name, tuple(rows), archived


@websocket_api.websocket_command({
    vol.Required("type"): COMMAND,
    vol.Required("config_entry_id"): str,
    vol.Required("kind"): str,
    vol.Optional("item_id"): str,
    vol.Optional("source"): str,
})
@callback
def websocket_source_history(hass, connection, msg):
    """Return links only; native HA history repeats its own entity READ checks."""
    identifier = msg.get("id") if isinstance(msg, dict) else None
    user = getattr(connection, "user", None)
    if user is None:
        connection.send_error(identifier, "unauthorized", "Geen leestoegang tot deze bronhistorie")
        return
    if (not isinstance(msg, dict) or set(msg)-{"id", "type", "config_entry_id", "kind", "item_id", "source"}
            or msg.get("type") != COMMAND
            or type(msg.get("config_entry_id")) is not str or not 0 < len(msg["config_entry_id"]) <= 200
            or type(msg.get("kind")) is not str or msg["kind"] not in _ROLES
            or (msg["kind"] in ("wallbox", "heatpump", "water") and "item_id" in msg)
            or (msg["kind"] in ("consumer", "battery") and (type(msg.get("item_id")) is not str
                or not 0 < len(msg["item_id"]) <= 200))
            or (msg["kind"] == "heatpump" and (type(msg.get("source")) is not str
                or msg["source"] not in ("display_tank", "configured")))
            or (msg["kind"] != "heatpump" and "source" in msg)):
        connection.send_error(identifier, "invalid_format", "Ongeldige SolarPilot-bronhistoriekvraag")
        return
    runtime = _runtime(hass, msg["config_entry_id"])
    if runtime is None:
        connection.send_error(identifier, "not_loaded", "SolarPilot is niet geladen")
        return
    kind, item_id, source = msg["kind"], msg.get("item_id"), msg.get("source")
    subject = _configured_sources(runtime, kind, item_id, source)
    if subject is None:
        connection.send_error(identifier, "not_found", "Deze SolarPilot-keuze bestaat niet")
        return
    name, rows, archived = subject
    permitted = []
    for role, label, entity in rows:
        try:
            allowed = getattr(user, "is_admin", False) is True or user.permissions.check_entity(entity, POLICY_READ) is True
        except Exception:
            allowed = False
        if allowed:
            permitted.append({"role": role, "label": label, "entity_id": entity})
    if _runtime(hass, msg["config_entry_id"]) is not runtime:
        connection.send_error(identifier, "not_loaded", "SolarPilot is herladen; open de bronhistorie opnieuw")
        return
    if _configured_sources(runtime, kind, item_id, source) != subject:
        connection.send_error(identifier, "sources_changed", "De bronkoppeling is gewijzigd; open de bronhistorie opnieuw")
        return
    if not permitted and getattr(user, "is_admin", False) is not True:
        connection.send_error(identifier, "unauthorized", "Geen leestoegang tot deze bronhistorie")
        return
    note = ("Bronnen uit de laatst bewaarde toestelkoppeling. " if archived else
            "Bronnen uit de huidige koppeling. ")
    result = {"schema": 1, "read_only": True, "scope": "current_configured_sources", "kind": kind,
              "name": name, "sources": permitted,
              "note": note + "Home Assistant toont alleen werkelijk bewaarde bronhistorie. Dit vult eerdere toestelkoppelingen niet in."}
    if item_id is not None:
        result["item_id"] = item_id
    connection.send_result(identifier, result)


@callback
def async_register_source_history_api(hass):
    if hass.data.get(_REGISTERED):
        return
    websocket_api.async_register_command(hass, websocket_source_history)
    hass.data[_REGISTERED] = True
