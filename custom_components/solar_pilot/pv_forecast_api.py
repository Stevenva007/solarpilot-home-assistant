"""Authenticated admin-only PV diagnostics and explicitly confirmed PV-only reset."""
from __future__ import annotations
from copy import deepcopy
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import BASE_COMMAND_MESSAGE_SCHEMA
from homeassistant.core import callback
from .const import DOMAIN
if type(BASE_COMMAND_MESSAGE_SCHEMA).__module__.split('.',1)[0]=='probatio':
    import probatio as vol
else:
    import voluptuous as vol

@websocket_api.websocket_command({vol.Required('type'):'solar_pilot/pv_diagnostics',
    vol.Required('config_entry_id'):str, vol.Optional('reset_confirm'):bool})
@websocket_api.async_response
async def websocket_pv_diagnostics(hass, connection, msg):
    if connection.user is None or not connection.user.is_admin:
        connection.send_error(msg['id'],'unauthorized','PV-diagnose en reset zijn alleen voor beheerders')
        return
    entry=hass.config_entries.async_get_entry(msg['config_entry_id'])
    r=getattr(entry,'runtime_data',None) if entry is not None and entry.domain==DOMAIN else None
    if r is None or r._closed:
        connection.send_error(msg['id'],'not_loaded','SolarPilot niet geladen');return
    if 'reset_confirm' in msg and type(msg['reset_confirm']) is not bool:
        connection.send_error(msg['id'],'invalid_options','Reset vraagt expliciete bevestiging');return
    async with r._lock:
        if msg.get('reset_confirm') is True:
            old_model=deepcopy(r.pv_forecast.snapshot())
            old_legacy=deepcopy(r.local_pv.snapshot())
            old_cache=deepcopy(r.pv_forecast.cached)
            try:
                r.pv_forecast.reset()
                await r.store.async_save(r._snapshot())
            except Exception:
                r.pv_forecast.restore(old_model)
                r.local_pv.restore(old_legacy)
                r.pv_forecast.cached=old_cache
                connection.send_error(msg['id'],'save_failed','PV-profiel kon niet worden gewist; vorige gegevens hersteld')
                return
            r.note('Alleen het live PV-correctieprofiel gewist op uitdrukkelijk verzoek; andere leerdata behouden')
        result=r.pv_forecast.diagnostics()
    connection.send_result(msg['id'],result)

@callback
def async_register_pv_api(hass):
    key=DOMAIN+'_pv_api'
    if hass.data.get(key):return
    websocket_api.async_register_command(hass,websocket_pv_diagnostics);hass.data[key]=True
