"""Authenticated editor for the single allocation order. No actuator endpoint."""
from __future__ import annotations
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import BASE_COMMAND_MESSAGE_SCHEMA
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN

if type(BASE_COMMAND_MESSAGE_SCHEMA).__module__.split('.', 1)[0] == 'probatio':
    import probatio as vol
else:
    import voluptuous as vol


@websocket_api.websocket_command({vol.Required('type'): 'solar_pilot/priority_board',
    vol.Required('config_entry_id'): str, vol.Optional('save'): dict})
@websocket_api.async_response
async def websocket_priority_board(hass, connection, msg):
    if connection.user is None or not connection.user.is_admin:
        connection.send_error(msg['id'], 'unauthorized', 'Voorrang wijzigen is alleen voor beheerders.')
        return
    entry = hass.config_entries.async_get_entry(msg['config_entry_id'])
    r = getattr(entry, 'runtime_data', None) if entry is not None and entry.domain == DOMAIN else None
    if r is None or r._closed:
        connection.send_error(msg['id'], 'not_loaded', 'SolarPilot is niet geladen.')
        return
    async with r._lock:
        try:
            if 'save' in msg:
                data = msg['save']
                if not isinstance(data, dict) or set(data) != {'revision', 'order', 'wallbox_power', 'confirm'}:
                    raise HomeAssistantError('Onvolledige of onbekende wijziging; vernieuw de lijst.')
                result = await r.priority_board.save(data['revision'], data['order'], data['wallbox_power'], data['confirm'])
            else:
                result = r.priority_board.overview()
        except HomeAssistantError as err:
            connection.send_error(msg['id'], 'invalid_options', str(err))
            return
    connection.send_result(msg['id'], result)


@callback
def async_register_priority_api(hass):
    key = DOMAIN + '_priority_api'
    if hass.data.get(key):
        return
    websocket_api.async_register_command(hass, websocket_priority_board)
    hass.data[key] = True
