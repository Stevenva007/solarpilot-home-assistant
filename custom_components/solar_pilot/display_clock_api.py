"""Authenticated, read-only time reference for presentation deadlines.

Browser wall clocks are not source clocks. This endpoint neither reads a
device nor refreshes source evidence, and never calls a controller or service.
"""
from __future__ import annotations

import time

from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import BASE_COMMAND_MESSAGE_SCHEMA
from homeassistant.core import callback

from .const import DOMAIN

if type(BASE_COMMAND_MESSAGE_SCHEMA).__module__.split('.', 1)[0] == 'probatio':
    import probatio as vol
else:
    import voluptuous as vol

COMMAND = 'solar_pilot/display_clock'


@websocket_api.websocket_command({
    vol.Required('type'): COMMAND,
    vol.Required('config_entry_id'): str,
})
@callback
def websocket_display_clock(hass, connection, msg):
    """Return only the loaded entry's server time to an authenticated viewer."""
    if connection.user is None:
        connection.send_error(msg['id'], 'unauthorized', 'Aanmelden bij Home Assistant is nodig.')
        return
    if (set(msg) != {'id', 'type', 'config_entry_id'} or msg.get('type') != COMMAND
            or type(msg.get('config_entry_id')) is not str or not msg['config_entry_id']):
        connection.send_error(msg['id'], 'invalid_format', 'Ongeldige tijdsaanvraag.')
        return
    entry = hass.config_entries.async_get_entry(msg['config_entry_id'])
    runtime = getattr(entry, 'runtime_data', None) if entry is not None and entry.domain == DOMAIN else None
    if runtime is None or runtime._closed:
        connection.send_error(msg['id'], 'not_loaded', 'SolarPilot is niet geladen.')
        return
    connection.send_result(msg['id'], {
        'schema': 1, 'read_only': True,
        'config_entry_id': msg['config_entry_id'], 'server_time': time.time(),
    })


@callback
def async_register_display_clock_api(hass):
    key = DOMAIN + '_display_clock_api'
    if hass.data.get(key):
        return
    websocket_api.async_register_command(hass, websocket_display_clock)
    hass.data[key] = True
