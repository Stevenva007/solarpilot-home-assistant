"""Authenticated, admin-only local learning decisions; no arbitrary writes."""
from __future__ import annotations

from copy import deepcopy
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import BASE_COMMAND_MESSAGE_SCHEMA
from homeassistant.core import callback
from .const import DOMAIN

if type(BASE_COMMAND_MESSAGE_SCHEMA).__module__.split('.', 1)[0] == 'probatio':
    import probatio as vol
else:
    import voluptuous as vol


@websocket_api.websocket_command({
    vol.Required('type'): 'solar_pilot/learning',
    vol.Required('config_entry_id'): str,
    vol.Optional('operation'): str,
    vol.Optional('question'): str,
    vol.Optional('revision'): str,
    vol.Optional('choice'): str,
    vol.Optional('setting'): str,
    vol.Optional('value'): object,
})
@websocket_api.async_response
async def websocket_learning(hass, connection, msg):
    user = connection.user
    if user is None or not user.is_admin:
        connection.send_error(msg['id'], 'unauthorized', 'Alleen een Home Assistant-beheerder mag leervragen beoordelen')
        return
    entry = hass.config_entries.async_get_entry(msg['config_entry_id'])
    r = getattr(entry, 'runtime_data', None) if entry is not None and entry.domain == DOMAIN else None
    if r is None or r._closed:
        connection.send_error(msg['id'], 'not_loaded', 'SolarPilot is niet geladen')
        return
    operation = msg.get('operation', 'read')
    if operation not in ('read', 'answer', 'policy'):
        connection.send_error(msg['id'], 'invalid_operation', 'Onbekende leerbewerking')
        return
    try:
        async with r._lock:
            if operation == 'answer':
                result = await r.learning_hub.answer(msg.get('question'), msg.get('revision'), msg.get('choice'))
            elif operation == 'policy':
                result = await r.learning_hub.set_policy(msg.get('setting'), msg.get('value'))
            else:
                result = deepcopy(r.learning_hub.refresh())
        connection.send_result(msg['id'], result)
    except ValueError as err:
        code = str(err)
        if code not in ('stale_question', 'invalid_choice', 'invalid_policy'):
            code = 'invalid_request'
        connection.send_error(msg['id'], code, 'Vraag of keuze is gewijzigd/ongeldig. Ververs en beoordeel opnieuw; niets toepassen op basis van een oude vraag.')
    except Exception:
        connection.send_error(msg['id'], 'learning_failed', 'Leerbewerking niet afgerond. Controleer de actuele keuze. Er is geen apparaatopdracht verstuurd.')


@callback
def async_register_learning_api(hass):
    key = DOMAIN + '_learning_api'
    if not hass.data.get(key):
        websocket_api.async_register_command(hass, websocket_learning)
        hass.data[key] = True
