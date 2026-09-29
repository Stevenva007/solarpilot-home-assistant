"""Admin-only read/export over authenticated Home Assistant WebSocket."""
from __future__ import annotations
import asyncio
import time
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import BASE_COMMAND_MESSAGE_SCHEMA
from homeassistant.core import callback
from .const import DOMAIN
from .analysis_export import serialize_report

if type(BASE_COMMAND_MESSAGE_SCHEMA).__module__.split('.', 1)[0] == 'probatio':
    import probatio as vol
else:
    import voluptuous as vol
COMMAND = 'solar_pilot/analysis_export'
_REGISTERED = DOMAIN + '_analysis_api'

@websocket_api.websocket_command({
    vol.Required('type'): COMMAND,
    vol.Required('config_entry_id'): str,
    vol.Optional('hours'): int,
    vol.Optional('include_names'): bool,
})
@websocket_api.async_response
async def websocket_analysis_export(hass, connection, msg):
    user = connection.user
    if user is None or not user.is_admin:
        connection.send_error(msg['id'], 'unauthorized', 'Alleen een Home Assistant-beheerder mag deze analyse exporteren')
        return
    hours = msg.get('hours', 24); names = msg.get('include_names', False)
    if type(hours) is not int or hours not in (1, 24, 168) or type(names) is not bool:
        connection.send_error(msg['id'], 'invalid_options', 'Kies 1 uur, 24 uur of 7 dagen')
        return
    entry = hass.config_entries.async_get_entry(msg['config_entry_id'])
    r = getattr(entry, 'runtime_data', None) if entry is not None and entry.domain == DOMAIN else None
    if r is None or r._closed:
        connection.send_error(msg['id'], 'not_loaded', 'SolarPilot is niet geladen')
        return
    recorder = r.analysis
    now = time.monotonic()
    if recorder.exporting or (recorder.last_export and now-recorder.last_export < 30):
        connection.send_error(msg['id'], 'busy', 'Wacht 30 seconden tussen analyse-exports')
        return
    recorder.exporting = True
    try:
        async with r._lock:
            # All HA-only reads and model copies happen on the HA thread.
            raw = recorder.prepare(hours)
        # Sanitization, pseudonyms and large JSON serialization run off the event loop.
        execute = getattr(hass, 'async_add_executor_job', None)
        task = lambda: serialize_report(recorder.finalize(raw, names))
        text = await execute(task) if execute else await asyncio.to_thread(task)
        recorder.last_export = time.monotonic()
        connection.send_result(msg['id'], {'filename': 'SolarPilot-analyse-' + raw['release'] + '-' + str(hours) + 'h.json', 'content': text, 'media_type': 'application/json'})
    except ValueError as err:
        connection.send_error(msg['id'], 'export_too_large', str(err))
    except Exception as err:
        recorder.error = 'Export onvolledig: ' + type(err).__name__
        connection.send_error(msg['id'], 'export_failed', 'Export mislukt: ' + type(err).__name__ + '. Er zijn geen apparaten bediend.')
    finally:
        recorder.exporting = False

@callback
def async_register_analysis_api(hass):
    if hass.data.get(_REGISTERED):
        return
    websocket_api.async_register_command(hass, websocket_analysis_export)
    hass.data[_REGISTERED] = True
